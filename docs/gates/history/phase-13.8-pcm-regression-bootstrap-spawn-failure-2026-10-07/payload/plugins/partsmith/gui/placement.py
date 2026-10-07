"""@package partsmith.gui.placement
@brief Maintains exact, unapproved engineering placement drafts.
@details Drafts cannot alter canonical STEP, reviewed IR or release bindings;
only the existing typed review service can advance the engineering head.
"""

import copy
from decimal import Decimal, InvalidOperation

from .review_service import DesktopReview
from .scene import validate_placement


def decimal_vector(values):
    """@brief Parses three finite exact decimal editor values.
    @param values Three deliberately entered coordinate strings.
    @return Three Decimal values without float conversion.
    @details Invalid, nonfinite or excessively long entries fail explicitly.
    """
    if len(values) != 3 or any(len(value) > 128 for value in values):
        raise ValueError("Placement requires three bounded decimal values")
    try:
        result = [Decimal(value) for value in values]
    except InvalidOperation as error:
        raise ValueError("Placement requires decimal numbers") from error
    if not all(value.is_finite() for value in result):
        raise ValueError("Placement requires finite decimal numbers")
    return result


class PlacementDraft:
    """@brief Binds a persistent placement draft to the exact reviewed head.
    @details Scale is preserved read only, including nonuniform/nonunit values.
    """

    def __init__(self, session):
        """@brief Reads current reviewed placement and matching saved draft.
        @param session Current isolated operational session.
        @return None.
        @details Stale drafts are retained as audit/display state but cannot
        be previewed or proposed against a different engineering head.
        """
        self.session = session
        ir = DesktopReview(session).snapshot()
        if ir is None or ir.data["model_3d"]["placement"] is None:
            raise ValueError("Explicit reviewed placement is unavailable")
        self.revision_id, self.revision_hash = (
            ir.data["revision"]["id"],
            ir.sha256,
        )
        self.reviewed = ir.data["model_3d"]["placement"]
        validate_placement(self.reviewed)
        saved = session.state.get("viewer", {}).get("placement_draft", {})
        self.value = copy.deepcopy(self.reviewed)
        self.stale = bool(saved) and (
            saved.get("base_revision_id"),
            saved.get("base_revision_hash"),
        ) != (self.revision_id, self.revision_hash)
        if saved and not self.stale:
            candidate = saved["placement"]
            if candidate["scale"] != self.reviewed["scale"]:
                raise ValueError(
                    "Saved placement draft changed read-only scale"
                )
            validate_placement(candidate)
            self.value = copy.deepcopy(candidate)

    def edit(self, translation, rotation, mirrors):
        """@brief Retains an exact unapproved supported transform draft.
        @param translation Three position editor strings in millimetres.
        @param rotation Three angle editor strings in degrees.
        @param mirrors Explicit XYZ mirror flags.
        @return Detached supported placement draft.
        @details Does not write IR, build artifacts, decisions or scale.
        """
        self.value = {
            **copy.deepcopy(self.reviewed),
            "translation_mm": decimal_vector(translation),
            "rotation_deg": decimal_vector(rotation),
            "mirror": dict(mirrors),
        }
        validate_placement(self.value)
        self.stale = False
        self.retain()
        return copy.deepcopy(self.value)

    def retain(self):
        """@brief Persists the draft with its exact immutable base identity.
        @return None.
        @details The draft has no implicit approval or generation authority.
        """
        self.session.update(
            viewer={
                **self.session.state.get("viewer", {}),
                "placement_draft": {
                    "base_revision_id": self.revision_id,
                    "base_revision_hash": self.revision_hash,
                    "placement": self.value,
                },
            }
        )

    def discard(self):
        """@brief Restores actual reviewed values rather than zero defaults.
        @return Detached reviewed placement.
        @details Preserves all XYZ scale values and supported mirror flags.
        """
        self.value = copy.deepcopy(self.reviewed)
        self.stale = False
        self.retain()
        return copy.deepcopy(self.value)

    def diagnostics(self):
        """@brief Reports draft discrepancies against the reviewed placement.
        @return Diagnostic codes with explicit units and review-only authority.
        @details Accepted revisions must rerun authoritative association and
        exact-final-byte checks; these discrepancies do not certify geometry.
        """
        findings = []
        if (
            self.value["translation_mm"][:2]
            != self.reviewed["translation_mm"][:2]
        ):
            findings.append("XY_OFFSET: draft position differs (mm)")
        if (
            self.value["translation_mm"][2]
            != self.reviewed["translation_mm"][2]
        ):
            findings.append("HEIGHT: draft board clearance differs (mm)")
        if self.value["rotation_deg"] != self.reviewed["rotation_deg"]:
            findings.append("ROTATION: draft orientation differs (deg)")
        if self.value["mirror"] != self.reviewed["mirror"]:
            findings.append("MIRROR: draft handedness differs")
        return findings or ["Draft matches reviewed placement"]

    def propose(self, reason, evidence_reference):
        """@brief Submits a typed placement override for explicit input review.
        @param reason Deliberate engineering rationale.
        @param evidence_reference Retained evidence or allowed audit reference.
        @return Existing immutable input proposal result.
        @details Exact base/hash comparison rejects stale editors, and scale
        remains identical to the reviewed transform.
        """
        review = DesktopReview(self.session)
        current = review.snapshot()
        if current.sha256 != self.revision_hash or self.stale:
            raise ValueError(
                "Placement draft base is stale; reopen the viewer"
            )
        if self.value["scale"] != self.reviewed["scale"]:
            raise ValueError("Scale editing is unsupported")
        return review.propose(
            "override",
            {
                "path": "/model_3d/placement",
                "new_value": self.value,
                "evidence_reference": evidence_reference,
            },
            reason,
        )
