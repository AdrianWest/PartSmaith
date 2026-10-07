"""@package tests.test_phase8_release_workflow
@brief Tests persisted Phase 8 release state and exact-hash approval.
@details Covers valid approval, stale bindings, blockers, authentication,
transition validation, and atomic rollback.
"""

from hashlib import sha256

import pytest

from partsmith.ir import canonical_json
from partsmith.persistence import ReleaseStore, Repository, database
from partsmith.release import (
    ApprovalBinding,
    AuthenticatedPrincipal,
    BuildState,
    EngineeringManifest,
    PostManifestReport,
    ReviewStage,
)
from partsmith.release.workflow import BuildOrchestrator, ReviewService

DIGEST = "a" * 64


def _result(
    status: str | None = "PASS",
    *,
    stage: str = "FINAL_ARTIFACT",
    rule_id: str = "release-rule",
) -> dict:
    """@brief Builds one strict validation result mapping.
    @param status Applicable result status, or None for non-applicability.
    @param stage Validation stage.
    @param rule_id Stable rule identity.
    @return Complete validation result mapping.
    @details The result includes semantic fields used by the release hash.
    """
    applicable = status is not None
    return {
        "id": f"{rule_id}-result",
        "category": "cross_artifact",
        "rule_id": rule_id,
        "status": status,
        "severity": "INFO" if status in {"PASS", None} else "ERROR",
        "message": "Synthetic release validation",
        "evidence_ids": [],
        "artifact_ids": [],
        "measured": True if applicable else None,
        "expected": True if applicable else None,
        "tolerance": None,
        "stage": stage,
        "applicability": "APPLICABLE" if applicable else "NOT_APPLICABLE",
        "applicability_reason": (
            None if applicable else "Pinned feature is absent"
        ),
        "applicability_basis": (
            None
            if applicable
            else {
                "kind": "PDL",
                "id": "synthetic",
                "revision": "1.0",
                "sha256": DIGEST,
                "feature_id": "absent-feature",
            }
        ),
        "measurement_mode": "MEASURED" if applicable else "NONE",
        "validator": {"id": "synthetic", "version": "1.0"},
    }


def _manifest(
    snapshot_hash: str,
    artifact_hashes: dict[str, str],
    result: dict,
) -> EngineeringManifest:
    """@brief Builds a manifest bound to one persisted release fixture.
    @param snapshot_hash Frozen build-input snapshot digest.
    @param artifact_hashes Final artifact hashes keyed by manifest name.
    @param result Retained validation result.
    @return Frozen engineering manifest.
    @details Every output path matches the persisted logical artifact path.
    """
    return EngineeringManifest(
        {
            "schema_version": "2.0",
            "component_identity": {
                "manufacturer": "Synthetic",
                "mpn": "0402",
            },
            "source": {
                "documents": [{"id": "doc-1"}],
                "hashes": [DIGEST],
            },
            "evidence": {
                "package": [{"id": "evidence-1"}],
                "hashes": [DIGEST],
            },
            "component_ir": {
                "schema_version": "1.2",
                "input_snapshot_hash": snapshot_hash,
            },
            "pdl": {
                "id": "synthetic",
                "revision": "1.0",
                "hash": DIGEST,
            },
            "generators": {
                "symbol": {"version": "1.0"},
                "footprint": {"version": "1.0"},
                "model_3d": {"version": "1.0"},
            },
            "outputs": {
                name: {
                    "path": f"generated/item.{extension}",
                    "sha256": artifact_hashes[name],
                }
                for name, extension in (
                    ("symbol", "kicad_sym"),
                    ("footprint", "kicad_mod"),
                    ("model_3d", "step"),
                )
            },
            "validation": {
                "overall": "PASS" if result["status"] == "PASS" else "FAIL",
                "results": [result],
            },
            "compatibility": {"kicad": {"major_version": "10"}},
            "overrides": {"active_content_hashes": []},
            "reproducibility": {
                "build_inputs_hash": snapshot_hash,
                "dependency_hashes": {
                    "symbol": DIGEST,
                    "footprint": DIGEST,
                    "model_3d": DIGEST,
                },
            },
        }
    )


def _advance_to_release_review(
    orchestrator: BuildOrchestrator, build_id: str
) -> None:
    """@brief Advances one supplied-input build to release review.
    @param orchestrator State owner used for every transition.
    @param build_id Build identity to advance.
    @return None.
    @details Uses the complete Phase 8 progress-state sequence.
    """
    for state in (
        BuildState.PACKAGE_IDENTIFIED,
        BuildState.IR_VALIDATED,
        BuildState.SYMBOL_GENERATED,
        BuildState.FOOTPRINT_GENERATED,
        BuildState.MODEL_3D_GENERATED,
        BuildState.ARTIFACT_VALIDATION,
        BuildState.CROSS_VALIDATION,
    ):
        orchestrator.advance(build_id, state, f"Entered {state.value}")
    orchestrator.advance(
        build_id,
        BuildState.HUMAN_REVIEW_REQUIRED,
        "Release checks complete",
        review_stage=ReviewStage.RELEASE,
    )


def _release_fixture(
    connection, *, validation_status: str = "PASS"
) -> tuple[str, ApprovalBinding]:
    """@brief Persists one complete synthetic release-review fixture.
    @param connection Active migrated SQLite connection.
    @param validation_status Retained final validation status.
    @return Build identity and exact approval binding.
    @details The fixture uses all three final artifact types and one
    post-manifest check.
    """
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    orchestrator = BuildOrchestrator(connection)
    build = orchestrator.start(
        component.id,
        supplied_reviewed_inputs=True,
    )
    store = ReleaseStore(connection)
    snapshot_hash = store.put_snapshot(
        build.id,
        {
            "schema_version": "1.0",
            "component": {"manufacturer": "Synthetic", "mpn": "0402"},
        },
        ir_record_hash=DIGEST,
        pdl_id="synthetic",
        pdl_revision="1.0",
        pdl_hash=DIGEST,
    )
    artifact_hashes = {}
    for artifact_type, name, extension in (
        ("SYMBOL", "symbol", "kicad_sym"),
        ("FOOTPRINT", "footprint", "kicad_mod"),
        ("MODEL_3D", "model_3d", "step"),
    ):
        artifact_hashes[name] = store.put_artifact(
            build.id,
            artifact_type,
            "FINAL",
            f"generated/item.{extension}",
            f"{artifact_type} bytes".encode(),
            dependency_hash=DIGEST,
            generator=f"synthetic-{name}",
            generator_version="1.0",
        )
    result = _result(validation_status)
    store.put_validation_result(build.id, "component-release", result)
    manifest = _manifest(snapshot_hash, artifact_hashes, result)
    store.put_manifest(build.id, manifest)
    report = PostManifestReport(
        {
            "schema_version": "1.0",
            "manifest_hash": manifest.sha256,
            "results": [
                _result(
                    "PASS",
                    stage="POST_MANIFEST",
                    rule_id="manifest-integrity",
                )
            ],
        }
    )
    store.put_post_manifest_report(build.id, report)
    _advance_to_release_review(orchestrator, build.id)
    return build.id, ApprovalBinding(
        input_snapshot_hash=snapshot_hash,
        engineering_manifest_hash=manifest.sha256,
        validation_semantics_hash=store.validation_semantics_hash(build.id),
        artifact_hashes=tuple(artifact_hashes.values()),
        post_manifest_report_hashes=(report.sha256,),
    )


def test_exact_release_binding_is_approved_atomically(tmp_path):
    """@brief Verifies a complete exact-hash release can be approved.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Decision, binding, and state transition persist together.
    """
    with database(tmp_path / "db") as connection:
        build_id, binding = _release_fixture(connection)
        decision_id = ReviewService(connection).approve(
            build_id,
            "reviewer-1",
            "All required release checks pass",
            binding,
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        assert Repository(connection).get_build(build_id).state == "APPROVED"
        decision = connection.execute(
            "SELECT * FROM release_decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        assert decision["decision"] == "APPROVE"
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM approval_bindings WHERE build_id = ?",
                (build_id,),
            ).fetchone()[0]
            == 1
        )


def test_stale_binding_and_reviewer_mismatch_leave_no_partial_decision(
    tmp_path,
):
    """@brief Verifies failed approval rolls back all service writes.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Both stale content and unauthenticated reviewer names are
    rejected.
    """
    with database(tmp_path / "db") as connection:
        build_id, binding = _release_fixture(connection)
        service = ReviewService(connection)
        stale = ApprovalBinding(
            binding.input_snapshot_hash,
            "b" * 64,
            binding.validation_semantics_hash,
            binding.artifact_hashes,
            binding.post_manifest_report_hashes,
        )
        with pytest.raises(ValueError, match="manifest binding"):
            service.approve(
                build_id,
                "reviewer-1",
                "Approve stale bytes",
                stale,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        with pytest.raises(PermissionError):
            service.approve(
                build_id,
                "reviewer-2",
                "Mismatched principal",
                binding,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert Repository(connection).get_build(build_id).state == (
            "HUMAN_REVIEW_REQUIRED"
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM release_decisions WHERE build_id = ?",
                (build_id,),
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM approval_bindings WHERE build_id = ?",
                (build_id,),
            ).fetchone()[0]
            == 0
        )


def test_tampered_final_bytes_cannot_be_approved(tmp_path):
    """@brief Verifies approval rehashes persisted final artifact bytes.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details A stale recorded hash cannot conceal modified release content.
    """
    with database(tmp_path / "db") as connection:
        build_id, binding = _release_fixture(connection)
        connection.execute(
            "UPDATE artifacts SET content = ? "
            "WHERE build_id = ? AND artifact_type = 'FOOTPRINT' "
            "AND stage = 'FINAL'",
            (b"tampered footprint bytes", build_id),
        )
        with pytest.raises(RuntimeError, match="artifact hash mismatch"):
            ReviewService(connection).approve(
                build_id,
                "reviewer-1",
                "Attempt approval after byte tampering",
                binding,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert Repository(connection).get_build(build_id).state == (
            "HUMAN_REVIEW_REQUIRED"
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM release_decisions"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "status",
    ["FAIL", "WARN", "HUMAN_REVIEW", "NOT_GENERATABLE"],
)
def test_blocking_final_result_cannot_be_approved(tmp_path, status):
    """@brief Verifies every non-PASS applicable result blocks approval.
    @param tmp_path Pytest temporary directory.
    @param status Blocking validation status.
    @return None.
    @details WARN remains blocking until an explicit warning policy is added.
    """
    with database(tmp_path / status) as connection:
        build_id, binding = _release_fixture(
            connection, validation_status=status
        )
        with pytest.raises(ValueError, match="Blocking validation"):
            ReviewService(connection).approve(
                build_id,
                "reviewer-1",
                "Attempt blocked approval",
                binding,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert Repository(connection).get_build(build_id).state == (
            "HUMAN_REVIEW_REQUIRED"
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM release_decisions"
            ).fetchone()[0]
            == 0
        )


def test_release_rejection_is_authenticated_and_terminal(tmp_path):
    """@brief Verifies authenticated rejection records a terminal state.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Rejection does not create an approval binding.
    """
    with database(tmp_path / "db") as connection:
        build_id, _ = _release_fixture(connection)
        decision_id = ReviewService(connection).reject(
            build_id,
            "reviewer-1",
            "Release evidence needs correction",
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        build = Repository(connection).get_build(build_id)
        assert build.state == "REJECTED"
        assert build.completed_at is not None
        assert (
            connection.execute(
                "SELECT decision FROM release_decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()[0]
            == "REJECT"
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM approval_bindings"
            ).fetchone()[0]
            == 0
        )


def test_state_machine_rejects_skips_and_unstaged_review(tmp_path):
    """@brief Verifies invalid progress edges cannot mutate build state.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Review waiting states require an explicit INPUT or RELEASE stage.
    """
    with database(tmp_path / "db") as connection:
        component = Repository(connection).create_component("X", "Y", "Z")
        orchestrator = BuildOrchestrator(connection)
        build = orchestrator.start(component.id)
        with pytest.raises(ValueError, match="Invalid build transition"):
            orchestrator.advance(
                build.id,
                BuildState.APPROVED,
                "Skip required release checks",
            )
        assert Repository(connection).get_build(build.id).state == (
            "SOURCE_RECEIVED"
        )
        supplied = orchestrator.start(
            component.id,
            supplied_reviewed_inputs=True,
        )
        with pytest.raises(ValueError, match="review stage"):
            orchestrator.advance(
                supplied.id,
                BuildState.HUMAN_REVIEW_REQUIRED,
                "Missing input decision",
            )


def test_validation_semantics_ignore_result_identity(tmp_path):
    """@brief Verifies result IDs do not alter validation semantics.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Engineering changes still alter the deterministic digest.
    """
    first = _result()
    second = _result()
    second["id"] = "another-run-result"
    first_hash = sha256(
        canonical_json(
            [{key: value for key, value in first.items() if key != "id"}]
        )
    ).hexdigest()
    with database(tmp_path / "db") as connection:
        component = Repository(connection).create_component("X", "Y", "Z")
        build = BuildOrchestrator(connection).start(
            component.id,
            supplied_reviewed_inputs=True,
        )
        store = ReleaseStore(connection)
        store.put_validation_result(build.id, "subject", second)
        assert store.validation_semantics_hash(build.id) == first_hash
