"""@package tests.test_phase8_pipeline
@brief Tests the deterministic Phase 8 known-good release path.
@details Covers generation, final validation, approval, and exact-byte export.
"""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release import AuthenticatedPrincipal
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.workflow import ReviewService

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "ir" / "v1.2" / "valid" / "0402.json"


def test_known_good_component_approves_and_exports_exact_bytes(tmp_path):
    """@brief Proves the complete deterministic release path succeeds.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Exported artifacts are byte-identical to approved database bytes.
    """
    destination = tmp_path / "approved-package"
    with database(tmp_path / "phase8.sqlite3") as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        data["identity"]["component_id"] = component.id
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(
            {
                "source_hashes": [
                    item["sha256"] for item in data["source"]["documents"]
                ],
                "evidence_ids": [item["id"] for item in data["evidence"]],
            }
        )
        revision = store.put_revision(
            data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, revision.revision_id, None)
        pipeline = KnownGoodReleasePipeline(connection)
        candidate = pipeline.run(
            component.id,
            revision.revision_id,
            load_pdl("synthetic-0402"),
        )
        compatibility = connection.execute(
            "SELECT canonical_bytes FROM validation_results "
            "WHERE build_id = ? AND rule_id = "
            "'kicad-native-compatibility'",
            (candidate.build_id,),
        ).fetchone()
        assert compatibility is not None
        compatibility_data = json.loads(
            bytes(compatibility["canonical_bytes"])
        )
        assert compatibility_data["status"] == "PASS"
        assert compatibility_data["validator"]["id"] == "kicad-cli"
        assert compatibility_data["validator"]["version"].startswith("10.")
        ReviewService(connection).approve(
            candidate.build_id,
            "reviewer-1",
            "Known-good deterministic release passes",
            candidate.binding,
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        approved = {
            row["logical_path"]: (
                row["sha256"],
                bytes(row["content"]),
            )
            for row in connection.execute(
                "SELECT logical_path, sha256, content FROM artifacts "
                "WHERE build_id = ? AND stage = 'FINAL'",
                (candidate.build_id,),
            )
        }
        footprint_path = next(
            path for path in approved if path.endswith(".kicad_mod")
        )
        connection.execute(
            "UPDATE artifacts SET content = ? "
            "WHERE build_id = ? AND stage = 'FINAL' AND logical_path = ?",
            (b"tampered after approval", candidate.build_id, footprint_path),
        )
        with pytest.raises(RuntimeError, match="artifact hash mismatch"):
            pipeline.export_approved(candidate.build_id, destination)
        assert not destination.exists()
        connection.execute(
            "UPDATE artifacts SET content = ? "
            "WHERE build_id = ? AND stage = 'FINAL' AND logical_path = ?",
            (
                approved[footprint_path][1],
                candidate.build_id,
                footprint_path,
            ),
        )
        pipeline.export_approved(candidate.build_id, destination)
        assert Repository(connection).get_build(candidate.build_id).state == (
            "EXPORTED"
        )
        for relative_path, (digest, expected) in approved.items():
            content = (destination / relative_path).read_bytes()
            assert content == expected
            assert sha256(content).hexdigest() == digest
        assert (destination / "manifest" / "engineering.json").is_file()


def test_silkscreen_only_revision_preserves_step_and_invalidates_approval(
    tmp_path,
):
    """@brief Proves footprint-only edits invalidate bound release content.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details STEP bytes remain stable while footprint, snapshot, and approval
    bindings change.
    """
    with database(tmp_path / "phase8-invalidation.sqlite3") as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        data["identity"]["component_id"] = component.id
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(
            {
                "source_hashes": [
                    item["sha256"] for item in data["source"]["documents"]
                ],
                "evidence_ids": [item["id"] for item in data["evidence"]],
            }
        )
        root = store.put_revision(
            data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, root.revision_id, None)
        pipeline = KnownGoodReleasePipeline(connection)
        baseline = pipeline.run(
            component.id,
            root.revision_id,
            load_pdl("synthetic-0402"),
        )
        changed = json.loads(json.dumps(data))
        changed["footprint"]["properties"]["silkscreen_line_width"] = {
            "source_value": 0.12,
            "source_unit": "mm",
            "normalized_value": 0.12,
            "normalized_unit": "mm",
            "status": "DIRECT",
            "evidence_ids": ["E-001"],
        }
        changed["revision"]["id"] = "IR12-silkscreen"
        changed["revision"]["parent_id"] = root.revision_id
        changed["revision"]["description"] = "Silkscreen-only revision"
        child = store.put_revision(
            changed,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(
            component.id, child.revision_id, root.canonical_sha256
        )
        revised = pipeline.run(
            component.id,
            child.revision_id,
            load_pdl("synthetic-0402"),
        )

        def artifact(
            build_id: str,
            artifact_type: str,
            stage: str = "FINAL",
        ) -> bytes:
            """@brief Reads exact final bytes for one generated artifact.
            @param build_id Persisted build identity.
            @param artifact_type SYMBOL, FOOTPRINT, or MODEL_3D.
            @param stage PRELIMINARY or FINAL artifact stage.
            @return Exact artifact bytes.
            @details The nested helper keeps comparison queries explicit.
            """
            row = connection.execute(
                "SELECT content FROM artifacts WHERE build_id = ? "
                "AND artifact_type = ? AND stage = ?",
                (build_id, artifact_type, stage),
            ).fetchone()
            assert row is not None
            return bytes(row["content"])

        def dependency(build_id: str) -> str:
            """@brief Reads the final footprint dependency digest.
            @param build_id Persisted build identity.
            @return Final footprint dependency hash.
            @details The digest binds geometry, placement, and model path.
            """
            row = connection.execute(
                "SELECT dependency_hash FROM artifacts WHERE build_id = ? "
                "AND artifact_type = 'FOOTPRINT' AND stage = 'FINAL'",
                (build_id,),
            ).fetchone()
            assert row is not None
            return row["dependency_hash"]

        assert artifact(baseline.build_id, "MODEL_3D") == artifact(
            revised.build_id, "MODEL_3D"
        )
        assert artifact(baseline.build_id, "FOOTPRINT") != artifact(
            revised.build_id, "FOOTPRINT"
        )
        assert (
            baseline.binding.input_snapshot_hash
            != revised.binding.input_snapshot_hash
        )
        assert set(baseline.binding.artifact_hashes) != set(
            revised.binding.artifact_hashes
        )
        with pytest.raises(ValueError, match="snapshot binding"):
            ReviewService(connection).approve(
                revised.build_id,
                "reviewer-1",
                "Attempt stale approval replay",
                baseline.binding,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert Repository(connection).get_build(revised.build_id).state == (
            "HUMAN_REVIEW_REQUIRED"
        )
        alternate_path = pipeline.run(
            component.id,
            child.revision_id,
            load_pdl("synthetic-0402"),
            model_logical_path="models/alternate-0402.step",
        )
        assert artifact(revised.build_id, "MODEL_3D") == artifact(
            alternate_path.build_id, "MODEL_3D"
        )
        assert artifact(revised.build_id, "FOOTPRINT") != artifact(
            alternate_path.build_id, "FOOTPRINT"
        )
        assert dependency(revised.build_id) != dependency(
            alternate_path.build_id
        )
        assert revised.manifest_hash != alternate_path.manifest_hash
        assert (
            revised.binding.input_snapshot_hash
            != alternate_path.binding.input_snapshot_hash
        )
        with pytest.raises(ValueError, match="snapshot binding"):
            ReviewService(connection).approve(
                alternate_path.build_id,
                "reviewer-1",
                "Attempt approval after association path change",
                revised.binding,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )

        placed_data = json.loads(json.dumps(changed))
        placed_data["model_3d"]["placement"]["translation_mm"][0] = 0.1
        placed_data["revision"]["id"] = "IR12-placement"
        placed_data["revision"]["parent_id"] = child.revision_id
        placed_data["revision"]["description"] = "Placement-only revision"
        placed_revision = store.put_revision(
            placed_data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(
            component.id,
            placed_revision.revision_id,
            child.canonical_sha256,
        )
        with pytest.raises(ValueError, match="final-byte validation failed"):
            pipeline.run(
                component.id,
                placed_revision.revision_id,
                load_pdl("synthetic-0402"),
            )
        failed = connection.execute(
            "SELECT build_id FROM build_state_transitions "
            "WHERE to_state = 'ARTIFACT_VALIDATION_FAILED' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert failed is not None
        placed_build_id = failed["build_id"]
        assert artifact(revised.build_id, "MODEL_3D") == artifact(
            placed_build_id, "MODEL_3D"
        )
        assert artifact(
            revised.build_id, "FOOTPRINT", "PRELIMINARY"
        ) == artifact(placed_build_id, "FOOTPRINT", "PRELIMINARY")
        assert artifact(revised.build_id, "FOOTPRINT") != artifact(
            placed_build_id, "FOOTPRINT"
        )
        assert dependency(revised.build_id) != dependency(placed_build_id)
        assert Repository(connection).get_build(placed_build_id).state == (
            "ARTIFACT_VALIDATION_FAILED"
        )
