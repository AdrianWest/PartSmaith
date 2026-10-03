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
        store.compare_and_swap_head(
            component.id, revision.revision_id, None
        )
        pipeline = KnownGoodReleasePipeline(connection)
        candidate = pipeline.run(
            component.id,
            revision.revision_id,
            load_pdl("synthetic-0402"),
        )
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
