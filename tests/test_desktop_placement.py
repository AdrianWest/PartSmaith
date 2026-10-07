"""@package tests.test_desktop_placement
@brief Verifies exact decimal drafts and normal typed review integration.
@details Unapproved drafts preserve STEP and release identities; accepted
placement revisions invalidate current release state and retain history.
"""

from decimal import Decimal

import pytest
from test_desktop_generation import ready_session

from partsmith.gui.placement import PlacementDraft, decimal_vector
from partsmith.gui.review_service import DesktopReview
from partsmith.gui.session import Session
from partsmith.ir.canonical import canonical_json


def test_exact_draft_feedback_discard_and_source_independent_restore(tmp_path):
    """@brief Exercises offsets, rotations, mirrors and exact draft transport.
    @param tmp_path Temporary operational sessions and transport archive.
    @return None.
    @details Review authority and canonical source geometry remain unchanged.
    """
    session = ready_session(tmp_path)
    original = canonical_json(session.state["drafts"]["ir"])
    draft = PlacementDraft(session)
    precise = "0.12345678901234567890123456789"
    draft.edit(
        [precise, "2", "3"],
        ["0", "0", "90"],
        {"x": True, "y": False, "z": False},
    )
    assert draft.value["translation_mm"][0] == Decimal(precise)
    assert {finding.split(":")[0] for finding in draft.diagnostics()} == {
        "XY_OFFSET",
        "HEIGHT",
        "ROTATION",
        "MIRROR",
    }
    assert canonical_json(session.state["drafts"]["ir"]) == original
    archive = tmp_path / "draft.partsmith"
    session.save(archive)
    loaded = Session.load(archive, root=tmp_path / "loaded")
    restored = PlacementDraft(loaded)
    assert restored.value == draft.value
    assert restored.discard() == restored.reviewed
    assert restored.value["scale"] == draft.reviewed["scale"]
    assert canonical_json(loaded.state["drafts"]["ir"]) == original


def test_placement_override_has_separate_decision_and_rejects_stale(tmp_path):
    """@brief Checks typed draft proposal, explicit input decision and
    staleness.
    @param tmp_path Temporary operational session root.
    @return None.
    @details Current release state is invalidated only on accepted inputs.
    """
    session = ready_session(tmp_path)
    draft = PlacementDraft(session)
    draft.edit(["0.1", "0", "0"], ["0", "0", "0"], draft.reviewed["mirror"])
    old_revision = session.state["revision_id"]
    draft.propose("Align actual end-cap and pad centres", "E-001")
    assert session.state["revision_id"] == old_revision
    DesktopReview(session).decide_inputs(
        True, "Checked source and coordinates"
    )
    assert session.state["revision_id"] != old_revision
    assert session.state["release"] is None
    current = DesktopReview(session).snapshot().data
    assert current["model_3d"]["placement"]["translation_mm"][0] == Decimal(
        "0.1"
    )
    assert current["model_3d"]["placement"]["scale"] == draft.reviewed["scale"]
    assert current["overrides"]
    assert session.state["history"][-1]["kind"] == "INPUT_APPROVE"
    with pytest.raises(ValueError, match="stale"):
        draft.propose("Old editor cannot advance head", "E-001")


@pytest.mark.parametrize(
    "values",
    [
        ["NaN", "0", "0"],
        ["Infinity", "0", "0"],
        ["invalid", "0", "0"],
        ["0", "0"],
    ],
)
def test_invalid_editor_values_fail(values):
    """@brief Rejects unsupported placement numbers before native preview.
    @param values Deliberately invalid coordinate strings.
    @return None.
    @details No engineering service or display worker is invoked.
    """
    with pytest.raises(ValueError):
        decimal_vector(values)


def test_nonuniform_scale_and_nonzero_reviewed_discard(tmp_path):
    """@brief Preserves exact nonuniform scale, offsets and mirrors on discard.
    @param tmp_path Fresh operational session storage.
    @return None.
    @details Scale changes require the normal typed service outside this
    editor.
    """
    session = ready_session(tmp_path)
    review = DesktopReview(session)
    pose = review.snapshot().data["model_3d"]["placement"]
    pose.update(
        scale=[Decimal("1.25"), Decimal("0.75"), Decimal("2")],
        translation_mm=[Decimal("2"), Decimal("3"), Decimal("4")],
        mirror={"x": False, "y": True, "z": False},
    )
    review.propose(
        "override",
        {
            "path": "/model_3d/placement",
            "new_value": pose,
            "evidence_reference": "E-001",
        },
        "Supported exact transform",
    )
    review.decide_inputs(True, "Inspect full transform including scale")
    draft = PlacementDraft(session)
    draft.edit(
        ["0", "0", "0"], ["90", "0", "0"], {"x": True, "y": False, "z": False}
    )
    assert draft.value["scale"] == pose["scale"]
    assert draft.discard() == draft.reviewed
    for key in ("translation_mm", "rotation_deg", "scale", "mirror"):
        assert draft.value[key] == pose[key]
