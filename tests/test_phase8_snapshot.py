"""@file test_phase8_snapshot.py
@brief Verifies frozen engineering snapshots and runtime identities.
@details Checks the running Python baseline without rewriting old receipts.
"""

import copy
import json
import platform
from pathlib import Path
from types import SimpleNamespace

import pytest

from partsmith.ir import ComponentIR
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release import pipeline as pipeline_module
from partsmith.release import runtime as runtime_module
from partsmith.release.pipeline import KnownGoodReleasePipeline

ROOT = Path(__file__).resolve().parents[1]


def _seed(connection):
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    data = json.loads(
        (ROOT / "fixtures/ir/v1.2/valid/0402.json").read_text(encoding="utf-8")
    )
    data["identity"]["component_id"] = component.id
    store = ImmutableStore(connection)
    inventory = store.put_inventory(
        {
            "source_hashes": [
                x["sha256"] for x in data["source"]["documents"]
            ],
            "evidence_ids": [x["id"] for x in data["evidence"]],
        }
    )
    revision = store.put_revision(
        data, inventory_sha256=inventory, reviewed=True
    )
    store.compare_and_swap_head(component.id, revision.revision_id, None)
    return component.id, data, inventory


def test_snapshot_is_complete_and_frozen_before_any_generator(
    tmp_path, monkeypatch
):
    """@brief Requires a complete snapshot before any generator executes.
    @param tmp_path Disposable snapshot database directory.
    @param monkeypatch Generator interception helper.
    @return None.
    @details Runtime identities must match the executing Python baseline.
    """
    with database(tmp_path / "snapshot.db") as connection:
        component, data, _ = _seed(connection)

        def before_symbol(*args):
            """@brief Inspects the frozen runtime at the generator boundary.
            @param args Unused symbol generator arguments.
            @return Never returns; terminates after checking the snapshot.
            @details No generated artifact may exist at this point.
            """
            row = connection.execute(
                "SELECT canonical_bytes FROM build_snapshots"
            ).fetchone()
            assert row is not None
            snapshot = json.loads(bytes(row[0]))
            assert snapshot["snapshot_profile"] == "1.2"
            assert "component_id" not in snapshot["inputs"]["/identity"]
            assert "revision_id" not in snapshot
            config = snapshot["configuration"]
            runtime = config["runtime"]
            assert runtime["python"] == platform.python_version()
            assert runtime["python_baseline"] == ".".join(
                platform.python_version_tuple()[:2]
            )
            assert runtime["occt"] == "7.9.3.1"
            assert runtime["archives"]
            assert all(len(x["sha256"]) == 64 for x in runtime["archives"])
            assert runtime["validators"]["rules"]
            assert config["release_profile"]["content"]
            assert config["exporter"]["precision_mode"] == 0
            assert len(snapshot["dependencies"]) == 4
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM artifacts"
                ).fetchone()[0]
                == 0
            )
            raise RuntimeError("stop after verifying frozen snapshot")

        monkeypatch.setattr(pipeline_module, "serialize_symbol", before_symbol)
        with pytest.raises(RuntimeError, match="stop after verifying"):
            KnownGoodReleasePipeline(connection).run(
                component, data["revision"]["id"], load_pdl("synthetic-0402")
            )


def test_rebuild_and_audit_only_revision_preserve_manifest(tmp_path):
    with database(tmp_path / "rebuild.db") as connection:
        component, data, inventory = _seed(connection)
        pipeline = KnownGoodReleasePipeline(connection)
        pdl = load_pdl("synthetic-0402")
        first = pipeline.run(component, data["revision"]["id"], pdl)
        second = pipeline.run(component, data["revision"]["id"], pdl)
        changed = copy.deepcopy(data)
        changed["revision"]["id"] = "audit-only-child"
        changed["revision"]["parent_id"] = data["revision"]["id"]
        changed["revision"]["description"] = "Audit description changed"
        changed["revision"]["evidence_review"]["reviewer"] = "reviewer-2"
        changed["revision"]["evidence_review"]["timestamp"] = (
            "2026-10-03T12:00:00Z"
        )
        store = ImmutableStore(connection)
        child = store.put_revision(
            changed, inventory_sha256=inventory, reviewed=True
        )
        store.compare_and_swap_head(
            component, child.revision_id, ComponentIR(data).sha256
        )
        third = pipeline.run(component, child.revision_id, pdl)
        assert len({first.build_id, second.build_id, third.build_id}) == 3
        assert (
            first.manifest_hash == second.manifest_hash == third.manifest_hash
        )
        assert first.binding.input_snapshot_hash == (
            third.binding.input_snapshot_hash
        )
        assert first.binding.validation_semantics_hash == (
            third.binding.validation_semantics_hash
        )
        assert first.binding.artifact_hashes == third.binding.artifact_hashes
        assert first.binding.post_manifest_report_hashes != (
            second.binding.post_manifest_report_hashes
        )
        manifest = connection.execute(
            "SELECT canonical_bytes FROM engineering_manifests "
            "WHERE build_id = ?",
            (first.build_id,),
        ).fetchone()[0]
        assert first.build_id.encode() not in manifest
        assert all(
            "id" not in result
            for result in json.loads(bytes(manifest))["validation"]["results"]
        )
        snapshots = connection.execute(
            "SELECT ir_record_hash, canonical_bytes FROM build_snapshots"
        ).fetchall()
        assert snapshots[0]["ir_record_hash"] != snapshots[2]["ir_record_hash"]
        assert (
            snapshots[0]["canonical_bytes"] == snapshots[2]["canonical_bytes"]
        )


def test_runtime_rejects_wrong_cad_version(tmp_path, monkeypatch):
    with database(tmp_path / "runtime-version.db") as connection:
        kicad = KnownGoodReleasePipeline(connection).kicad_runtime
        monkeypatch.setattr(
            runtime_module,
            "distribution",
            lambda name: SimpleNamespace(version="unreviewed"),
        )
        with pytest.raises(RuntimeError, match="distribution differs"):
            runtime_module.runtime_configuration(kicad)


def test_runtime_rejects_tampered_installed_cad_bytes(tmp_path, monkeypatch):
    corrupted = tmp_path / "cadquery.py"
    corrupted.write_bytes(b"changed installed runtime")
    with database(tmp_path / "runtime-bytes.db") as connection:
        kicad = KnownGoodReleasePipeline(connection).kicad_runtime
        monkeypatch.setattr(
            runtime_module,
            "distribution",
            lambda name: SimpleNamespace(
                version="2.8.0", locate_file=lambda name: corrupted
            ),
        )
        with pytest.raises(RuntimeError, match="runtime content mismatch"):
            runtime_module.runtime_configuration(kicad)


def test_runtime_mismatch_blocks_before_generation(tmp_path, monkeypatch):
    with database(tmp_path / "runtime.db") as connection:
        component, data, _ = _seed(connection)

        def invalid_runtime(*args):
            raise RuntimeError("CAD runtime content mismatch")

        monkeypatch.setattr(
            pipeline_module, "runtime_configuration", invalid_runtime
        )
        with pytest.raises(RuntimeError, match="runtime content mismatch"):
            KnownGoodReleasePipeline(connection).run(
                component, data["revision"]["id"], load_pdl("synthetic-0402")
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM build_snapshots"
            ).fetchone()[0]
            == 0
        )
