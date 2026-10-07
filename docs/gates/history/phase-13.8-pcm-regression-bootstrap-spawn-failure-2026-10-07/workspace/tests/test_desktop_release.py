"""@package tests.test_desktop_release
@brief Verifies explicit release decisions and hostile approval restoration.
@details Actual CAD/KiCad artifacts are generated once and loaded into fresh
operational sessions; approvals cannot be inherited by changed content.
"""

from threading import Event

import pytest
from test_desktop_generation import ready_session

from partsmith.gui.actions import ActionController
from partsmith.gui.generation import generate_session
from partsmith.gui.identity import authenticated_principal
from partsmith.gui.release_review import decide_release, release_report
from partsmith.gui.review_service import DesktopReview
from partsmith.gui.session import Session


@pytest.fixture(scope="module")
def release_archive(tmp_path_factory):
    """@brief Generates a real validated, unapproved offline fixture archive.
    @param tmp_path_factory Module-isolated operational storage factory.
    @return Archive path containing exact artifacts and validation content.
    @details Initial input approval does not approve the generated release.
    """
    root = tmp_path_factory.mktemp("desktop-release")
    session = ready_session(root)
    generate_session(session, Event(), lambda *args, **kwargs: None)
    archive = root / "candidate.partsmith"
    session.save(archive)
    return archive


@pytest.mark.parametrize("late_cancel", [False, True])
def test_committed_release_survives_checkpoint_failure(
    release_archive, tmp_path, monkeypatch, late_cancel
):
    """@brief Preserves a real release decision despite recovery failure.
    @param release_archive Native validated unapproved fixture transport.
    @param tmp_path Fresh operational and restored session storage.
    @param monkeypatch Scoped recovery-storage failure adapter.
    @param late_cancel Whether cancellation arrives after committed approval.
    @return None.
    @details Approval bindings remain exact; restoration creates no decision.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    controller = ActionController()

    def operation(current, cancel, emit):
        """@brief Commits exact-byte approval through the real service.
        @param current Isolated validated component session.
        @param cancel Cooperative action cancellation signal.
        @param emit Unused redacted progress callback.
        @return Immutable committed release decision ID.
        @details Cancellation cannot undo the completed atomic transaction.
        """
        result = decide_release(current, True, "Inspect exact released bytes")
        if late_cancel:
            cancel.set()
        return result

    def fail_checkpoint():
        """@brief Fails recovery archive storage after release approval.
        @return None.
        @details Leaves the working approval and last good checkpoint intact.
        """
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(session, "checkpoint", fail_checkpoint)
    controller.start(session, "release review", operation)
    controller.thread.join(10)
    assert not controller.thread.is_alive()
    events = controller.drain()
    decision = session.state["release"]["decision_id"]
    assert events[-1].outcome == "success"
    assert events[-1].payload == decision
    assert any(event.code == "CHECKPOINT_ERROR" for event in events)
    assert not any(
        event.outcome in {"cancelled", "failed"} for event in events
    )
    session.refresh()
    assert session.state["status"] == "release-approved"
    assert release_report(session)["blockers"] == []
    archive = tmp_path / "approved.partsmith"
    session.save(archive)
    restored = Session.load(archive, root=tmp_path / "restored")
    assert restored.state["release"]["decision_id"] == decision
    assert restored.state["history"] == session.state["history"]
    with restored.connection() as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM release_decisions WHERE id=?",
                (decision,),
            ).fetchone()[0]
            == 1
        )


def test_changed_setup_identity_blocks_release_and_restore(
    release_archive, tmp_path
):
    """@brief Rejects approval and loading after an ordering-number mismatch.
    @param release_archive Native validated unapproved fixture transport.
    @param tmp_path Isolated forged-setup transport and working sessions.
    @return None.
    @details Matching database/CAS hashes cannot authorize a different part.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    session.update(setup={"part_number": "ANOTHER-PACKAGE-SUFFIX"})
    with pytest.raises(ValueError, match="part number differs"):
        decide_release(session, True, "Try mismatched setup identity")
    assert not session.state["release"]["approved"]
    archive = tmp_path / "mismatched.partsmith"
    session.save(archive)
    with pytest.raises(ValueError, match="part number differs"):
        Session.load(archive, root=tmp_path / "restored")


def test_release_requires_separate_os_decision_and_restores_exactly(
    release_archive, tmp_path
):
    """@brief Approves a validated release and rechecks it after offline load.
    @param release_archive Actual native validated fixture transport.
    @param tmp_path Fresh operational storage and approved transport.
    @return None.
    @details Saved display actors never replace the current authenticated SID.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    assert session.state["release"]["approved"] is False
    assert release_report(session)["blockers"] == []
    session.update(
        history=[*session.state["history"], {"actor": "forged-saved-reviewer"}]
    )
    decision = decide_release(
        session, True, "Inspected exact final artifact bytes"
    )
    assert (
        session.state["history"][-1]["actor"]
        == authenticated_principal().subject
    )
    assert session.state["release"]["decision_id"] == decision
    archive = tmp_path / "approved.partsmith"
    session.save(archive)
    restored = Session.load(archive, root=tmp_path / "sessions")
    assert restored.state["release"] == session.state["release"]
    assert release_report(restored)["blockers"] == []


def test_forged_approval_label_and_changed_artifact_are_rejected(
    release_archive, tmp_path
):
    """@brief Rejects self-consistent transport hashes carrying stale approval.
    @param release_archive Actual validated unapproved fixture transport.
    @param tmp_path Fresh sessions and hostile transport files.
    @return None.
    @details Database and exact service bindings are independently rechecked.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    session.update(release={**session.state["release"], "approved": True})
    archive = tmp_path / "forged.partsmith"
    session.save(archive)
    with pytest.raises(ValueError, match="approved label"):
        Session.load(archive, root=tmp_path / "loaded")
    session = Session.load(release_archive, root=tmp_path / "sessions")
    artifacts = session.state["drafts"]["artifacts"]
    item = next(item for item in artifacts if item["stage"] == "FINAL")
    item["reference"] = session.put(b"changed engineering artifact")
    item["sha256"] = item["reference"]["$asset"]
    session.update(drafts={**session.state["drafts"], "artifacts": artifacts})
    assert release_report(session)["blockers"]
    with pytest.raises(ValueError, match="artifact differs"):
        decide_release(session, True, "Attempt changed bytes")
    session.save(archive)
    with pytest.raises(ValueError, match="artifact"):
        Session.load(archive, root=tmp_path / "loaded")


def test_accepted_fault_reruns_final_checks_and_reuses_geometry(
    release_archive, tmp_path
):
    """@brief Validates actual metadata-only placement regeneration behavior.
    @param release_archive Actual validated candidate with declared node cache.
    @param tmp_path Fresh operational session storage.
    @return None.
    @details A large offset fails association checks; canonical STEP reuse
    requires unchanged declared geometry dependencies.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    original = next(
        item["sha256"]
        for item in session.state["drafts"]["artifacts"]
        if item["type"] == "MODEL_3D" and item["stage"] == "FINAL"
    )
    review = DesktopReview(session)
    review.propose(
        "override",
        {
            "path": "/model_3d/placement/translation_mm/0",
            "new_value": 1,
            "evidence_reference": "E-001",
        },
        "Injected diagnostic offset for review",
    )
    review.decide_inputs(True, "Inspect offset proposal")
    with pytest.raises(RuntimeError, match="Generation worker failed"):
        generate_session(session, Event(), lambda *args, **kwargs: None)
    assert session.state["release"] is None
    current = next(
        item["sha256"]
        for item in session.state["drafts"]["artifacts"]
        if item["type"] == "MODEL_3D" and item["stage"] == "FINAL"
    )
    assert current == original
    with session.connection() as connection:
        decisions = {
            row["node_kind"]: row["action"]
            for row in connection.execute(
                "SELECT node_kind,action FROM build_dependencies "
                "WHERE build_id=?",
                (session.state["build_id"],),
            )
        }
        assert decisions["MODEL_3D"] == "REUSE"
        assert decisions["ASSOCIATION"] != "REUSE"
    report = release_report(session)
    assert any(result["status"] == "FAIL" for result in report["validation"])
    from partsmith.gui.artifact_scene import session_scene

    _source, binding = session_scene(session)
    assert binding["stage"] == "FINAL" and binding["status"] == "failed"


def test_release_rejection_and_missing_identity(release_archive, tmp_path):
    """@brief Checks explicit rejection and unavailable OS authentication.
    @param release_archive Actual validated unapproved fixture transport.
    @param tmp_path Fresh operational sessions and rejected archive.
    @return None.
    @details Rejected artifacts remain available for diagnostic inspection.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")

    def unavailable():
        """@brief Injects unavailable trusted OS identity.
        @return None.
        @details No decision can commit without an authenticated principal.
        """
        raise PermissionError("OS identity unavailable")

    with pytest.raises(PermissionError):
        decide_release(session, True, "Review", identity=unavailable)
    assert not session.state["release"]["approved"]
    decide_release(
        session, False, "Reject after inspecting actual native previews"
    )
    assert session.state["status"] == "release-rejected"
    archive = tmp_path / "rejected.partsmith"
    session.save(archive)
    assert (
        Session.load(archive, root=tmp_path / "sessions").state["status"]
        == "release-rejected"
    )


def test_changed_reviewed_input_invalidates_current_release(
    release_archive, tmp_path
):
    """@brief Applies an explicit placement input revision after generation.
    @param release_archive Actual validated candidate transport.
    @param tmp_path Fresh operational session storage.
    @return None.
    @details Retained historical artifacts remain stale and unapproved.
    """
    session = Session.load(release_archive, root=tmp_path / "sessions")
    review = DesktopReview(session)
    review.propose(
        "override",
        {
            "path": "/model_3d/placement/translation_mm/0",
            "new_value": 1,
            "evidence_reference": "E-001",
        },
        "Explicitly move the placement",
    )
    review.decide_inputs(True, "Checked proposed source and offset")
    assert session.state["release"] is None
    assert release_report(session)["blockers"]
