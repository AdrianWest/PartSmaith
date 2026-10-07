"""@package tests.test_release_contracts
@brief Tests the shared Phase 8 deterministic release contracts.
@details Verifies closed schemas, exact hash bindings, audit separation, and
strict review identities before persistence and orchestration are added.
"""

import copy

import pytest

from partsmith.release import (
    ApprovalBinding,
    AuthenticatedPrincipal,
    BuildState,
    EngineeringManifest,
    NotGeneratableDetail,
    ReleaseReport,
    ReviewStage,
    ValidationStage,
    WarningPolicy,
)

DIGEST = "a" * 64


def _manifest() -> dict:
    """@brief Builds a minimal valid engineering manifest.
    @return A complete manifest mapping.
    @details Uses deterministic placeholder hashes for contract tests.
    """
    artifact = {"path": "generated/item", "sha256": DIGEST}
    return {
        "schema_version": "2.0",
        "component_identity": {"manufacturer": "Synthetic", "mpn": "0402"},
        "source": {"documents": [{"id": "doc-1"}], "hashes": [DIGEST]},
        "evidence": {"package": [{"id": "evidence-1"}], "hashes": [DIGEST]},
        "component_ir": {
            "schema_version": "1.2",
            "input_snapshot_hash": DIGEST,
        },
        "pdl": {"id": "synthetic-0402", "revision": "1.0", "hash": DIGEST},
        "generators": {
            "symbol": {"version": "1.0"},
            "footprint": {"version": "1.0"},
            "model_3d": {"version": "1.0"},
        },
        "outputs": {
            "symbol": artifact,
            "footprint": artifact,
            "model_3d": artifact,
        },
        "validation": {
            "overall": "PASS",
            "results": [
                {
                    "rule_id": "rule-1",
                    "stage": "FINAL_ARTIFACT",
                    "status": "PASS",
                    "applicability": "APPLICABLE",
                }
            ],
        },
        "compatibility": {"kicad": {"major_version": "10"}},
        "overrides": {"active_content_hashes": []},
        "reproducibility": {
            "build_inputs_hash": DIGEST,
            "dependency_hashes": {"symbol": DIGEST},
        },
    }


def _release_report() -> dict:
    """@brief Builds a minimal valid machine-readable release report.
    @return A complete release report mapping.
    @details Includes a null-status declared exclusion as required.
    """
    exclusion = {
        "rule_id": "no-exposed-pad",
        "stage": "FINAL_ARTIFACT",
        "status": None,
        "applicability": "NOT_APPLICABLE",
    }
    return {
        "schema_version": "1.0",
        "summary": {
            "status": "APPROVED",
            "errors": [],
            "warnings": [],
            "review_items": [],
            "declared_exclusions": [exclusion],
        },
        "artifacts": [],
        "validation": [exclusion],
        "evidence": [],
        "mapping": {},
        "compatibility": {},
        "reproducibility": {},
    }


def test_workflow_enums_separate_review_and_validation_states():
    """@brief Verifies persisted and result state vocabularies are distinct.
    @return None.
    @details HUMAN_REVIEW is a validation status, not a build state.
    """
    assert BuildState.HUMAN_REVIEW_REQUIRED.value == "HUMAN_REVIEW_REQUIRED"
    assert "HUMAN_REVIEW" not in {state.value for state in BuildState}
    assert ReviewStage.INPUT.value == "INPUT"
    assert ValidationStage.POST_MANIFEST.value == "POST_MANIFEST"


def test_authenticated_principal_rejects_reviewer_mismatch():
    """@brief Verifies reviewer names cannot substitute for authentication.
    @return None.
    @details Only the authenticated principal subject may make the decision.
    """
    principal = AuthenticatedPrincipal("reviewer-1", "local-test")
    principal.require_reviewer("reviewer-1")
    with pytest.raises(PermissionError):
        principal.require_reviewer("reviewer-2")


def test_not_generatable_requires_all_four_statements():
    """@brief Verifies section 194 explanations cannot be incomplete.
    @return None.
    @details Empty unblocking evidence is rejected by the closed schema.
    """
    valid = NotGeneratableDetail(
        "body height",
        "CLASS_A geometry cannot be validated",
        "model_3d",
        "a dimensioned mechanical drawing",
    )
    assert valid.to_dict()["blocked_artifact"] == "model_3d"
    with pytest.raises(ValueError):
        NotGeneratableDetail("body height", "required", "model_3d", "")


def test_warning_policy_hash_is_content_deterministic():
    """@brief Verifies warning policies have stable content identity.
    @return None.
    @details Reviewer identity and timestamps are not policy fields.
    """
    first = WarningPolicy(
        "1.0",
        "policy-1",
        "rule-1",
        "GOLD-0402-001",
        "Reviewed bootstrap warning",
        "ACCEPT_WARNING",
    )
    second = WarningPolicy(**first.__dict__)
    assert first.sha256 == second.sha256


def test_approval_binding_requires_complete_lowercase_hashes():
    """@brief Verifies release approval binds every required content hash.
    @return None.
    @details Empty post-manifest checks and malformed hashes are rejected.
    """
    binding = ApprovalBinding(DIGEST, DIGEST, DIGEST, (DIGEST,), (DIGEST,))
    assert binding.to_dict()["artifact_hashes"] == [DIGEST]
    with pytest.raises(ValueError):
        ApprovalBinding(DIGEST, DIGEST, DIGEST, (DIGEST,), ())
    with pytest.raises(ValueError):
        ApprovalBinding(DIGEST.upper(), DIGEST, DIGEST, (DIGEST,), (DIGEST,))


def test_manifest_is_closed_immutable_and_has_no_self_hash():
    """@brief Verifies deterministic manifest closure and frozen bytes.
    @return None.
    @details Mutating caller or returned data cannot change manifest identity.
    """
    data = _manifest()
    manifest = EngineeringManifest(data)
    original_hash = manifest.sha256
    data["component_identity"]["mpn"] = "changed"
    detached = manifest.data
    detached["component_identity"]["mpn"] = "also-changed"
    assert manifest.data["component_identity"]["mpn"] == "0402"
    assert manifest.sha256 == original_hash
    invalid = copy.deepcopy(_manifest())
    invalid["engineering_manifest_hash"] = DIGEST
    with pytest.raises(ValueError):
        EngineeringManifest(invalid)


def test_release_report_preserves_null_declared_exclusion_status():
    """@brief Verifies declared exclusions stay separate and null-status.
    @return None.
    @details NOT_APPLICABLE is never serialized as PASS.
    """
    report = ReleaseReport(_release_report())
    exclusion = report.data["summary"]["declared_exclusions"][0]
    assert exclusion["status"] is None
    invalid = _release_report()
    invalid["summary"]["declared_exclusions"][0]["status"] = "PASS"
    with pytest.raises(ValueError):
        ReleaseReport(invalid)
