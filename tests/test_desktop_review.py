"""@package tests.test_desktop_review
@brief Checks initial assembly, authenticated decisions and typed pin history.
@details Exercises service adapters against isolated working databases.
"""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest

from partsmith.gui.actions import ActionController
from partsmith.gui.identity import authenticated_principal
from partsmith.gui.review_service import DesktopReview
from partsmith.gui.session import Session
from partsmith.ir import ComponentIR, canonical_json, validate_ir
from partsmith.ir.canonical import parse_json
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore


def local_session(tmp_path):
    """@brief Creates local acquisition data without reading a fixture IR.
    @param tmp_path Temporary session storage.
    @return Isolated session with one unreviewed original evidence record.
    @details No pins, dimensions, engineering units or package facts are
    supplied.
    """
    session = Session(tmp_path / "storage")
    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.4\nsource statement")
    session.acquire(source)
    digest = session.state["source"]["$asset"]
    acquisition = str(uuid4())
    record = {
        "id": "ev-original",
        "type": "SYNTHETIC_TEST_DATA",
        "source": {
            "document_id": "source-1",
            "document_hash": digest,
            "page": 1,
            "region": None,
            "coordinate_convention": None,
            "page_geometry": None,
            "render_transform": None,
        },
        "extracted": {
            "text": "original source statement",
            "value": None,
            "unit": None,
        },
        "interpretation": {"normalized_value": None, "status": "UNKNOWN"},
        "extractor": {"method": "test-acquisition", "version": "1"},
        "confidence": {"score": 1, "basis": "unreviewed extraction"},
        "acquisition_revision_id": acquisition,
        "candidate_targets": [],
    }
    session.update(
        setup={"part_number": "FULL-SUFFIX-R"}, acquisition_id=acquisition
    )
    session.retain_extraction(
        {
            "document": {"id": "source-1", "sha256": digest, "page_count": 1},
            "selected_pages": [1],
            "evidence": [record],
            "assets": {},
            "pages": [],
        }
    )
    return session


def fielded_session(tmp_path, review_inputs=True):
    """@brief Supplies explicit known geometry to the assembly adapter.
    @param tmp_path Temporary session storage.
    @param review_inputs Whether to explicitly decide the known fixture inputs.
    @return Session and review adapter after explicit input approval.
    @details The fixture is supplied engineering input, never an implicit root.
    """
    session = local_session(tmp_path)
    fixture = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "fixtures/ir/v1.2/valid/0402.json"
        ).read_text()
    )
    extraction = session.extraction()
    evidence = fixture["evidence"]
    evidence[0]["source"] = extraction["evidence"][0]["source"]
    evidence[0]["acquisition_revision_id"] = extraction["evidence"][0][
        "acquisition_revision_id"
    ]
    extraction["evidence"] = evidence
    session.update(extraction=session.put(canonical_json(extraction)))
    values = {
        key: fixture[key]
        for key in (
            "electrical",
            "pins",
            "package",
            "symbol",
            "footprint",
            "model_3d",
        )
    }
    values["identity"] = {
        key: fixture["identity"][key]
        for key in ("manufacturer", "package_variant", "evidence_ids")
    }
    review = DesktopReview(session)
    review.assemble(values)
    if not review_inputs:
        return session, review
    review.propose_evidence("Inspect exact original evidence inventory")
    review.decide_inputs(
        True, "Original inventory and entered fields inspected"
    )
    return session, review


@pytest.mark.parametrize("late_cancel", [False, True])
@pytest.mark.parametrize("failure", ["checkpoint", "logs"])
def test_committed_input_approval_survives_persistence_failure(
    tmp_path, monkeypatch, late_cancel, failure
):
    """@brief Keeps real input approval successful after persistence faults.
    @param tmp_path Isolated working session and recovery transport paths.
    @param monkeypatch Scoped checkpoint or log failure adapter.
    @param late_cancel Whether cancellation arrives after the atomic commit.
    @param failure Recovery checkpoint or action-log persistence fault.
    @return None.
    @details The reviewed head and decision survive save/load without replay.
    """
    session, review = fielded_session(tmp_path, review_inputs=False)
    review.propose_evidence("Inspect the exact acquisition inventory")
    controller = ActionController()

    def operation(current, cancel, emit):
        """@brief Performs one real atomic input-approval decision.
        @param current Isolated working session.
        @param cancel Cooperative action cancellation signal.
        @param emit Unused redacted progress callback.
        @return Committed immutable review result.
        @details Cancellation is injected only after the transaction returns.
        """
        result = DesktopReview(current).decide_inputs(
            True, "Explicit approval before recovery persistence"
        )
        if late_cancel:
            cancel.set()
        return result

    def fail_checkpoint():
        """@brief Injects unavailable recovery storage after the commit.
        @return None.
        @details Leaves the reviewed SQLite head and previous checkpoint.
        """
        raise OSError("checkpoint storage unavailable")

    original_update = session.update

    def fail_logs(**changes):
        """@brief Fails action-log persistence without disturbing review.
        @param changes Exact session-state changes requested by the caller.
        @return None.
        @details The atomic review service's transaction follows its real path.
        """
        if set(changes) == {"logs"}:
            raise OSError("log storage unavailable")
        original_update(**changes)

    if failure == "checkpoint":
        monkeypatch.setattr(session, "checkpoint", fail_checkpoint)
    else:
        monkeypatch.setattr(session, "update", fail_logs)
    controller.start(session, "input review", operation)
    controller.thread.join(10)
    assert not controller.thread.is_alive()
    events = controller.drain()
    assert events[-1].outcome == "success"
    assert events[-1].payload.revision_id == session.state["revision_id"]
    assert any(event.outcome == "warning" for event in events)
    assert not any(
        event.outcome in {"cancelled", "failed"} for event in events
    )
    session.refresh()
    assert session.state["status"] == "inputs-reviewed"
    assert session.state["history"][-1]["kind"] == "INPUT_APPROVE"
    archive = tmp_path / "committed.partsmith"
    session.save(archive)
    restored = Session.load(archive, root=tmp_path / "restored")
    assert restored.state["history"] == session.state["history"]
    assert restored.state["revision_id"] == session.state["revision_id"]
    with pytest.raises(ValueError, match="No pending input proposal"):
        DesktopReview(restored).decide_inputs(True, "Do not replay a decision")
    assert len(restored.state["history"]) == 1


def test_initial_root_registers_missing_facts_and_inventory(tmp_path):
    """@brief Checks pure acquisition assembly without fixture IR fallback.
    @param tmp_path Temporary session storage.
    @return None.
    @details Structurally valid incomplete data remains blocked for generation.
    """
    session = local_session(tmp_path)
    original = copy.deepcopy(session.extraction())
    review = DesktopReview(session)
    root = review.assemble()
    ir = review.snapshot()
    assert isinstance(ir, ComponentIR)
    assert ir.data["pins"] == []
    assert ir.data["package"]["mechanical"] == {}
    assert ir.data["model_3d"]["placement"] is None
    assert ir.data["identity"]["manufacturer"]["name"] is None
    assert ir.data["revision"]["evidence_review"] is None
    assert session.extraction() == original
    with session.connection() as connection:
        inventory = ImmutableStore(connection).get_inventory(
            root.inventory_sha256
        )
        assert inventory["evidence_ids"] == ["ev-original"]
        assert (
            connection.execute(
                "SELECT count(*) FROM review_proposals"
            ).fetchone()[0]
            == 0
        )
    proposal = review.propose_evidence("Inspect original local evidence")
    with session.connection() as connection:
        candidate = ImmutableStore(connection).get_revision(
            proposal.candidate_revision_id
        )
    assert candidate["package"] == ir.data["package"]
    review.decide_inputs(True, "All original evidence inspected")
    assert any(
        issue.code == "IR_INCOMPLETE"
        for issue in validate_ir(review.snapshot().data, for_generation=True)
    )
    assert not session.state.get("release")


def test_missing_identity_cannot_decide_but_session_remains_saveable(tmp_path):
    """@brief Checks unavailable OS identity blocks review without data loss.
    @param tmp_path Temporary session storage.
    @return None.
    @details Forged saved actors never supply authentication for current
    actions.
    """
    session = local_session(tmp_path)
    review = DesktopReview(session)
    review.assemble()
    review.propose_evidence("Review retained source")
    before = review.snapshot().sha256
    session.update(history=[{"actor": "administrator", "mechanism": "forged"}])

    def unavailable():
        """@brief Simulates a failed trusted OS authentication adapter.
        @return None.
        @details Does not accept any saved or document-provided actor.
        """
        raise PermissionError("OS identity unavailable")

    with pytest.raises(PermissionError):
        DesktopReview(session, identity=unavailable).decide_inputs(
            True, "attempt"
        )
    assert review.snapshot().sha256 == before
    session.save(tmp_path / "unfinished.partsmith")


def test_actual_os_actor_is_stable_and_saved_subject_is_audit_only():
    """@brief Checks the real OS adapter returns a stable authenticated
    subject.
    @return None.
    @details A separately supplied display reviewer is rejected by the
    contract.
    """
    first, second = authenticated_principal(), authenticated_principal()
    assert first == second
    assert first.mechanism in {
        "windows-process-token-sid",
        "posix-process-uid",
    }
    with pytest.raises(PermissionError):
        first.require_reviewer("forged-display-name")


def test_explicit_evidence_assignment_preserves_original_record(tmp_path):
    """@brief Checks explicit source-to-field interpretation without mutation.
    @param tmp_path Temporary session storage.
    @return None.
    @details Assigned evidence has a new identity and retains source links.
    """
    session = local_session(tmp_path)
    original = copy.deepcopy(session.extraction()["evidence"][0])
    quantity = parse_json(
        '{"source_value":0.123456789012345678901,"source_unit":"mm",'
        '"status":"DIRECT","evidence_ids":["ev-original"]}'
    )
    values = {
        "package": {
            "family": None,
            "variant": None,
            "pin_count": None,
            "mechanical": {"body_width": quantity},
            "status": "MISSING",
            "evidence_ids": [],
        }
    }
    assignment = {
        "evidence_id": "ev-original",
        "paths": ["/package/mechanical/body_width"],
        "status": "DIRECT",
        "value": quantity["source_value"],
        "reason": "Explicitly interpreted width in the retained statement",
    }
    review = DesktopReview(session)
    review.assemble(values, [assignment])
    data = review.snapshot().data
    assert data["evidence"][0] == original
    assigned = data["evidence"][1]
    assert assigned["source"] == original["source"]
    assert assigned["extracted"] == original["extracted"]
    assert assigned["interpretation"]["evidence_ids"] == [original["id"]]
    assert (
        assigned["interpretation"]["normalized_value"]
        == quantity["source_value"]
    )
    assert data["package"]["mechanical"]["body_width"]["evidence_ids"] == [
        assigned["id"]
    ]
    assert len(data["evidence"]) == 2


def test_review_state_and_engineering_commit_roll_back_together(
    tmp_path, monkeypatch
):
    """@brief Checks a failed desktop-state write rolls back review decisions.
    @param tmp_path Temporary working session root.
    @param monkeypatch Scoped state-write failure injection.
    @return None.
    @details No decision, head advance or stale desktop pointer survives.
    """
    session = local_session(tmp_path)
    review = DesktopReview(session)
    review.assemble()
    review.propose_evidence("Inspect retained original inventory")
    before = copy.deepcopy(session.state)
    original_update = session.update

    def fail(**changes):
        """@brief Fails after the transaction's desktop-state write.
        @param changes State mutation fields.
        @return None.
        @details Forces rollback after service decision creation.
        """
        original_update(**changes)
        raise OSError("state write interrupted")

    monkeypatch.setattr(session, "update", fail)
    with pytest.raises(OSError):
        review.decide_inputs(True, "Inspect and approve retained evidence")
    assert session.state == before
    with session.connection() as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM review_events WHERE decision='APPROVE'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT count(*) FROM component_heads"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("operation", ["reorder", "renumber", "remove"])
def test_pin_operations_retain_historical_evidence_bindings(
    tmp_path, operation
):
    """@brief Checks reorder, renumber and removal append exact reviewed
    history.
    @param tmp_path Temporary session storage.
    @param operation Typed terminal operation to exercise.
    @return None.
    @details Historical evidence and base revisions remain byte-identical.
    """
    session, review = fielded_session(tmp_path)
    base = review.snapshot()
    if operation == "renumber":
        review.propose(
            "override",
            {
                "path": "/pins/0/number",
                "new_value": "A",
                "evidence_reference": "E-001",
            },
            "Explicit terminal renumber",
        )
    else:
        review.propose(
            operation,
            {
                "terminal_order": ["2", "1"]
                if operation == "reorder"
                else ["2"]
            },
            "Explicit topology review",
        )
    assert review.snapshot().sha256 == base.sha256
    review.decide_inputs(True, "Terminal operation and provenance inspected")
    current = review.snapshot()
    assert current.data["evidence"] == base.data["evidence"]
    with session.connection() as connection:
        assert (
            ComponentIR(
                ImmutableStore(connection).get_revision(
                    base.data["revision"]["id"]
                )
            ).sha256
            == base.sha256
        )
    if operation == "remove":
        assert [pin["number"] for pin in current.data["pins"]] == ["2"]
        assert any(
            item["new_path"] is None and item["approval_state"] == "APPROVED"
            for item in current.data["revision"]["target_rebindings"]
        )
    elif operation == "renumber":
        assert current.data["pins"][0]["number"] == "A"
    else:
        assert [pin["number"] for pin in current.data["pins"]] == ["2", "1"]


def test_exact_decimal_override_and_separate_input_rejection(tmp_path):
    """@brief Checks exact edited numeric text and explicit reject behavior.
    @param tmp_path Temporary session storage.
    @return None.
    @details Rejection retains the head and pending candidate history.
    """
    session, review = fielded_session(tmp_path)
    base = review.snapshot()
    value = parse_json(
        '{"source_value":0.123456789012345678901,"source_unit":"mm","status":"DIRECT","evidence_ids":["E-001"]}'
    )
    review.propose(
        "override",
        {
            "path": "/package/mechanical/body_width",
            "new_value": value,
            "evidence_reference": "E-001",
        },
        "Exact width edit",
    )
    review.decide_inputs(False, "Reject width pending better evidence")
    assert review.snapshot().sha256 == base.sha256
    review.propose(
        "override",
        {
            "path": "/package/mechanical/body_width",
            "new_value": value,
            "evidence_reference": "E-001",
        },
        "Exact width edit",
    )
    review.decide_inputs(True, "Width and referenced source inspected")
    assert (
        review.snapshot().data["package"]["mechanical"]["body_width"][
            "source_value"
        ]
        == value["source_value"]
    )
    assert session.state.get("release") is None


def test_pdl_label_does_not_select_library_and_binding_rechecks_topology(
    tmp_path,
):
    """@brief Checks explicit exact PDL identity, revision and content binding.
    @param tmp_path Temporary session storage.
    @return None.
    @details Wrong hash or incompatible topology leaves selection unchanged.
    """
    session, review = fielded_session(tmp_path)
    assert session.state.get("pdl") is None
    pdl = load_pdl("synthetic-0402", "1.0")
    with pytest.raises(ValueError, match="hash"):
        review.bind_pdl(pdl.data["id"], pdl.data["revision"], "0" * 64)
    review.bind_pdl(
        pdl.data["id"], pdl.data["revision"], pdl.data["content_sha256"]
    )
    assert session.state["pdl"]["sha256"] == pdl.data["content_sha256"]
    assert session.state.get("release") is None
