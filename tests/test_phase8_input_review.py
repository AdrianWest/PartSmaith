"""@package tests.test_phase8_input_review
@brief Tests immutable Phase 8 evidence and inventory input review.
@details Covers review before artifacts, stale heads, authentication,
immutable proposals, rejection, and atomic rollback.
"""

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.ir import ComponentIR, canonical_json
from partsmith.persistence import (
    ImmutableStore,
    Repository,
    StaleHeadError,
    database,
)
from partsmith.release import AuthenticatedPrincipal
from partsmith.release.input_review import (
    NO_HEAD_HASH,
    InputApprovalRequest,
    InputRejectionRequest,
    InputReviewProposal,
    InputReviewService,
    OverrideProposalRequest,
)

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "ir" / "v1.2" / "valid" / "0402.json"


def _inventory(data: dict) -> dict:
    """@brief Builds the complete acquisition inventory for a revision.
    @param data Component IR mapping.
    @return Matching source hashes and evidence identities.
    @details Ordering follows the retained revision arrays.
    """
    return {
        "source_hashes": [
            document["sha256"] for document in data["source"]["documents"]
        ],
        "evidence_ids": [record["id"] for record in data["evidence"]],
    }


def _root_revision(component_id: str) -> dict:
    """@brief Loads an unreviewed root revision for one component.
    @param component_id Persisted component identity.
    @return Detached valid IR 1.2 root mapping.
    @details Existing synthetic approval metadata is removed for service tests.
    """
    data = json.loads(IR_PATH.read_text(encoding="utf-8"))
    data["identity"]["component_id"] = component_id
    data["revision"]["evidence_review"] = None
    return data


def _candidate(base: dict, revision_id: str = "candidate-1") -> dict:
    """@brief Creates an evidence-review-only child revision.
    @param base Exact base revision.
    @param revision_id New candidate revision identity.
    @return Detached unreviewed child mapping.
    @details Engineering content and decision history remain unchanged.
    """
    data = copy.deepcopy(base)
    data["revision"]["id"] = revision_id
    data["revision"]["parent_id"] = base["revision"]["id"]
    data["revision"]["description"] = "Pending evidence review"
    data["revision"]["evidence_review"] = None
    return data


def _proposal_fixture(connection):
    """@brief Persists one root, inventory, candidate, and proposal.
    @param connection Active migrated SQLite connection.
    @return Component, proposal request, and persisted proposal result.
    @details No build or generated artifact is created by this fixture.
    """
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    store = ImmutableStore(connection)
    root = _root_revision(component.id)
    inventory = _inventory(root)
    inventory_hash = store.put_inventory(inventory)
    stored_root = store.put_revision(
        root,
        inventory_sha256=inventory_hash,
        reviewed=False,
    )
    candidate = _candidate(root)
    candidate_hash = ComponentIR(candidate).sha256
    request = InputReviewProposal(
        component_id=component.id,
        base_revision_id=stored_root.revision_id,
        base_revision_hash=stored_root.canonical_sha256,
        expected_head_hash=NO_HEAD_HASH,
        candidate_revision_id=candidate["revision"]["id"],
        candidate_revision_hash=candidate_hash,
        inventory_sha256=inventory_hash,
        reason="Review retained source and evidence inventory",
    )
    result = InputReviewService(connection).propose(request, candidate)
    return component, request, result


def _approval_request(component, request, result) -> InputApprovalRequest:
    """@brief Builds an exact approval request for one proposal.
    @param component Persisted component record.
    @param request Original proposal request.
    @param result Persisted proposal result.
    @return Closed exact-hash input approval request.
    @details Reviewer identity is later checked against authentication.
    """
    return InputApprovalRequest(
        proposal_id=result.proposal_id,
        proposal_hash=result.proposal_hash,
        component_id=component.id,
        candidate_revision_id=result.candidate_revision_id,
        candidate_revision_hash=result.candidate_revision_hash,
        expected_head_hash=request.expected_head_hash,
        inventory_sha256=request.inventory_sha256,
        reviewer="reviewer-1",
        reason="Evidence inventory is complete and correct",
    )


def _reviewed_head_fixture(connection):
    """@brief Persists one reviewed current IR head for override tests.
    @param connection Active migrated SQLite connection.
    @return Component, reviewed revision, inventory hash, and review service.
    @details The retained synthetic review and inventory are exact and valid.
    """
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    data = json.loads(IR_PATH.read_text(encoding="utf-8"))
    data["identity"]["component_id"] = component.id
    store = ImmutableStore(connection)
    inventory_hash = store.put_inventory(_inventory(data))
    assert (
        data["revision"]["evidence_review"]["inventory_sha256"]
        == inventory_hash
    )
    stored = store.put_revision(
        data,
        inventory_sha256=inventory_hash,
        reviewed=True,
    )
    store.compare_and_swap_head(component.id, stored.revision_id, None)
    return component, stored, inventory_hash, InputReviewService(connection)


def _override_approval_request(
    component,
    base_hash: str,
    inventory_hash: str,
    result,
) -> InputApprovalRequest:
    """@brief Builds an approval request for one override proposal.
    @param component Persisted component record.
    @param base_hash Expected current reviewed head hash.
    @param inventory_hash Retained acquisition inventory digest.
    @param result Persisted override proposal result.
    @return Closed exact-hash approval request.
    @details The request cannot alter captured override content.
    """
    return InputApprovalRequest(
        proposal_id=result.proposal_id,
        proposal_hash=result.proposal_hash,
        component_id=component.id,
        candidate_revision_id=result.candidate_revision_id,
        candidate_revision_hash=result.candidate_revision_hash,
        expected_head_hash=base_hash,
        inventory_sha256=inventory_hash,
        reviewer="reviewer-1",
        reason="Approve typed engineering override",
    )


def test_input_review_approves_before_any_artifact_exists(tmp_path):
    """@brief Verifies input approval is independent of generated artifacts.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Approval creates a reviewed child, event, and current head only.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        revision = InputReviewService(connection).approve_inputs(
            _approval_request(component, proposal, result),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        head = connection.execute(
            "SELECT * FROM component_heads WHERE component_id = ?",
            (component.id,),
        ).fetchone()
        assert head["revision_id"] == revision.revision_id
        assert head["revision_hash"] == revision.revision_hash
        approved = ImmutableStore(connection).get_revision(
            revision.revision_id
        )
        review = approved["revision"]["evidence_review"]
        assert review["approval_state"] == "APPROVED"
        assert review["reviewer"] == "reviewer-1"
        assert approved["revision"]["parent_id"] == (
            result.candidate_revision_id
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT status FROM review_proposals WHERE id = ?",
                (result.proposal_id,),
            ).fetchone()[0]
            == "PENDING"
        )


def test_stale_head_rejects_approval_without_partial_records(tmp_path):
    """@brief Verifies concurrent head advancement requires rereview.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details No approval event or reviewed proposal child survives failure.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        store = ImmutableStore(connection)
        candidate = store.get_revision(result.candidate_revision_id)
        inventory = store.get_inventory(proposal.inventory_sha256)
        competing = copy.deepcopy(candidate)
        competing["revision"]["id"] = "competing-reviewed"
        competing["revision"]["parent_id"] = result.candidate_revision_id
        competing["revision"]["evidence_review"] = {
            "inventory_sha256": proposal.inventory_sha256,
            "reviewed_evidence_ids": inventory["evidence_ids"],
            "reviewer": "reviewer-2",
            "timestamp": "2026-10-02T20:00:00Z",
            "approval_state": "APPROVED",
        }
        stored = store.put_revision(
            competing,
            inventory_sha256=proposal.inventory_sha256,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, stored.revision_id, None)
        before_count = connection.execute(
            "SELECT COUNT(*) FROM ir_revisions"
        ).fetchone()[0]
        with pytest.raises(StaleHeadError):
            InputReviewService(connection).approve_inputs(
                _approval_request(component, proposal, result),
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == before_count
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 0
        )


def test_rejection_retains_immutable_pending_proposal(tmp_path):
    """@brief Verifies rejection appends an event without editing proposal.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details A decided proposal cannot receive a second decision.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        row = connection.execute(
            "SELECT canonical_bytes FROM review_proposals WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        original = bytes(row["canonical_bytes"])
        request = InputRejectionRequest(
            proposal_id=result.proposal_id,
            proposal_hash=result.proposal_hash,
            component_id=component.id,
            candidate_revision_id=result.candidate_revision_id,
            candidate_revision_hash=result.candidate_revision_hash,
            expected_head_hash=proposal.expected_head_hash,
            reviewer="reviewer-1",
            reason="Evidence needs reacquisition",
        )
        rejected = InputReviewService(connection).reject_inputs(
            request,
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        assert rejected.decision == "REJECT"
        persisted = connection.execute(
            "SELECT status, canonical_bytes FROM review_proposals "
            "WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        assert persisted["status"] == "PENDING"
        assert bytes(persisted["canonical_bytes"]) == original
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM component_heads"
            ).fetchone()[0]
            == 0
        )
        with pytest.raises(ValueError, match="already has a decision"):
            InputReviewService(connection).reject_inputs(
                request,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )


def test_engineering_change_is_not_an_evidence_review_action(tmp_path):
    """@brief Verifies evidence review cannot smuggle engineering edits.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Invalid proposal writes roll back candidate and proposal records.
    """
    with database(tmp_path / "db") as connection:
        component = Repository(connection).create_component("X", "Y", "Z")
        store = ImmutableStore(connection)
        root = _root_revision(component.id)
        inventory_hash = store.put_inventory(_inventory(root))
        stored_root = store.put_revision(
            root,
            inventory_sha256=inventory_hash,
            reviewed=False,
        )
        candidate = _candidate(root)
        candidate["electrical"]["resistance"]["value"] = 22000
        candidate_hash = ComponentIR(candidate).sha256
        request = InputReviewProposal(
            component_id=component.id,
            base_revision_id=stored_root.revision_id,
            base_revision_hash=stored_root.canonical_sha256,
            expected_head_hash=NO_HEAD_HASH,
            candidate_revision_id=candidate["revision"]["id"],
            candidate_revision_hash=candidate_hash,
            inventory_sha256=inventory_hash,
            reason="Attempt engineering edit",
        )
        with pytest.raises(ValueError, match="engineering content"):
            InputReviewService(connection).propose(request, candidate)
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_proposals"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == 1
        )


def test_authentication_and_proposal_hash_fail_atomically(tmp_path):
    """@brief Verifies identity and exact proposal hashes are mandatory.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Failed attempts leave the proposal undecided and head absent.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        request = _approval_request(component, proposal, result)
        service = InputReviewService(connection)
        with pytest.raises(PermissionError):
            service.approve_inputs(
                request,
                AuthenticatedPrincipal("another-reviewer", "local-test"),
            )
        stale = InputApprovalRequest(
            **(request.to_dict() | {"proposal_hash": "f" * 64})
        )
        with pytest.raises(ValueError, match="proposal hash"):
            service.approve_inputs(
                stale,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM component_heads"
            ).fetchone()[0]
            == 0
        )


def test_proposal_hash_binds_generated_identity(tmp_path):
    """@brief Verifies proposal identity participates in immutable bytes.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Persisted canonical bytes hash to the returned proposal digest.
    """
    with database(tmp_path / "db") as connection:
        _, _, result = _proposal_fixture(connection)
        row = connection.execute(
            "SELECT canonical_sha256, canonical_bytes "
            "FROM review_proposals WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        assert sha256(bytes(row["canonical_bytes"])).hexdigest() == (
            result.proposal_hash
        )
        assert row["canonical_sha256"] == result.proposal_hash
        data = json.loads(bytes(row["canonical_bytes"]))
        assert data["proposal_id"] == result.proposal_id
        assert canonical_json(data) == bytes(row["canonical_bytes"])


def test_typed_override_captures_previous_value_and_retains_pending(tmp_path):
    """@brief Verifies typed scalar override proposal and approval behavior.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details The target changes only in the reviewed child, while the pending
    decision remains immutable history.
    """
    with database(tmp_path / "db") as connection:
        component, base, inventory_hash, service = _reviewed_head_fixture(
            connection
        )
        result = service.propose_override(
            OverrideProposalRequest(
                component_id=component.id,
                base_revision_id=base.revision_id,
                base_revision_hash=base.canonical_sha256,
                expected_head_hash=base.canonical_sha256,
                path="/pins/0/electrical_type",
                new_value="input",
                evidence_reference="E-001",
                reason="Reviewed pin electrical behavior",
            ),
            AuthenticatedPrincipal("proposer-1", "local-test"),
        )
        store = ImmutableStore(connection)
        candidate = store.get_revision(result.candidate_revision_id)
        assert candidate["pins"][0]["electrical_type"] == "passive"
        pending = candidate["overrides"][-1]
        assert pending["approval_state"] == "PENDING"
        assert pending["previous_value"] == "passive"
        assert pending["new_value"] == "input"
        assert pending["value_type"] == "STRING"
        assert candidate["revision"]["active_override_ids"] == []

        approved = service.approve_inputs(
            _override_approval_request(
                component,
                base.canonical_sha256,
                inventory_hash,
                result,
            ),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        data = store.get_revision(approved.revision_id)
        assert data["pins"][0]["electrical_type"] == "input"
        assert data["overrides"][-2] == pending
        decision = data["overrides"][-1]
        assert decision["id"] != pending["id"]
        assert decision["approval_state"] == "APPROVED"
        assert decision["user"] == "reviewer-1"
        assert data["revision"]["active_override_ids"] == [decision["id"]]


def test_quantity_override_gets_server_owned_self_binding(tmp_path):
    """@brief Verifies record overrides receive trusted approval bindings.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Callers do not supply decision IDs or USER_OVERRIDE metadata.
    """
    with database(tmp_path / "db") as connection:
        component, base, inventory_hash, service = _reviewed_head_fixture(
            connection
        )
        current = ImmutableStore(connection).get_revision(base.revision_id)
        value = copy.deepcopy(current["package"]["mechanical"]["body_width"])
        value["source_value"] = 550
        value.pop("normalized_value")
        value.pop("normalized_unit")
        result = service.propose_override(
            OverrideProposalRequest(
                component_id=component.id,
                base_revision_id=base.revision_id,
                base_revision_hash=base.canonical_sha256,
                expected_head_hash=base.canonical_sha256,
                path="/package/mechanical/body_width",
                new_value=value,
                evidence_reference="E-001",
                reason="Reviewed corrected package width",
            ),
            AuthenticatedPrincipal("proposer-1", "local-test"),
        )
        approved = service.approve_inputs(
            _override_approval_request(
                component,
                base.canonical_sha256,
                inventory_hash,
                result,
            ),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        data = ImmutableStore(connection).get_revision(approved.revision_id)
        target = data["package"]["mechanical"]["body_width"]
        decision = data["overrides"][-1]
        assert target["source_value"] == 550
        assert target["status"] == "USER_OVERRIDE"
        assert target["override_id"] == decision["id"]
        assert decision["new_value"] == target


def test_replacing_override_preserves_history_and_supersedes_active(tmp_path):
    """@brief Verifies an approved override can be explicitly replaced.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Earlier pending and approved records remain byte-for-byte present.
    """
    with database(tmp_path / "db") as connection:
        component, base, inventory_hash, service = _reviewed_head_fixture(
            connection
        )
        first_proposal = service.propose_override(
            OverrideProposalRequest(
                component_id=component.id,
                base_revision_id=base.revision_id,
                base_revision_hash=base.canonical_sha256,
                expected_head_hash=base.canonical_sha256,
                path="/pins/0/electrical_type",
                new_value="input",
                evidence_reference="E-001",
                reason="First reviewed pin override",
            ),
            AuthenticatedPrincipal("proposer-1", "local-test"),
        )
        first = service.approve_inputs(
            _override_approval_request(
                component,
                base.canonical_sha256,
                inventory_hash,
                first_proposal,
            ),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        store = ImmutableStore(connection)
        first_data = store.get_revision(first.revision_id)
        first_active = first_data["revision"]["active_override_ids"][0]
        retained = copy.deepcopy(first_data["overrides"])

        second_proposal = service.propose_override(
            OverrideProposalRequest(
                component_id=component.id,
                base_revision_id=first.revision_id,
                base_revision_hash=first.revision_hash,
                expected_head_hash=first.revision_hash,
                path="/pins/0/electrical_type",
                new_value="output",
                evidence_reference="E-001",
                reason="Replace reviewed pin override",
            ),
            AuthenticatedPrincipal("proposer-2", "local-test"),
        )
        second = service.approve_inputs(
            _override_approval_request(
                component,
                first.revision_hash,
                inventory_hash,
                second_proposal,
            ),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        data = store.get_revision(second.revision_id)
        assert data["overrides"][: len(retained)] == retained
        assert data["pins"][0]["electrical_type"] == "output"
        new_active = data["revision"]["active_override_ids"][0]
        assert new_active != first_active
        approved_record = next(
            record
            for record in data["overrides"]
            if record["id"] == new_active
        )
        assert approved_record["supersedes_override_id"] == first_active


@pytest.mark.parametrize(
    "path",
    ["/revision/description", "/footprint/land_pattern_source"],
)
def test_override_rejects_paths_outside_trusted_registry(tmp_path, path):
    """@brief Verifies metadata and land-source edits are not overrides.
    @param tmp_path Pytest temporary directory.
    @param path Disallowed proposed target path.
    @return None.
    @details Invalid requests leave no candidate or proposal records.
    """
    with database(tmp_path / "db") as connection:
        component, base, _, service = _reviewed_head_fixture(connection)
        before = connection.execute(
            "SELECT COUNT(*) FROM ir_revisions"
        ).fetchone()[0]
        with pytest.raises(ValueError, match="editable registry"):
            service.propose_override(
                OverrideProposalRequest(
                    component_id=component.id,
                    base_revision_id=base.revision_id,
                    base_revision_hash=base.canonical_sha256,
                    expected_head_hash=base.canonical_sha256,
                    path=path,
                    new_value="changed",
                    evidence_reference="E-001",
                    reason="Attempt disallowed edit",
                ),
                AuthenticatedPrincipal("proposer-1", "local-test"),
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == before
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_proposals"
            ).fetchone()[0]
            == 0
        )
