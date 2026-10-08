"""@file test_phase9.py
@brief Checks selective invalidation and materialized offline replay.
@details Independent builds run with explicit noninteractive child streams.
"""

import copy
import json
import os
import socket
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.ir import ComponentIR, canonical_json
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release import AuthenticatedPrincipal
from partsmith.release import pipeline as pipeline_module
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.replay import OfflineReplayService, ReplayBundle
from partsmith.release.reproducibility import (
    BuildConfiguration,
    build_hashes,
    comparison_report,
)
from partsmith.release.workflow import ReviewService

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "fixtures/ir/source/synthetic-0402.txt").read_bytes()


def seed(connection):
    repository = Repository(connection)
    component = repository.create_component("Synthetic", "0402", "0402")
    data = json.loads((ROOT / "fixtures/ir/v1.2/valid/0402.json").read_bytes())
    data["identity"]["component_id"] = component.id
    store = ImmutableStore(connection)
    inventory = store.put_inventory(
        {
            "source_hashes": [
                d["sha256"] for d in data["source"]["documents"]
            ],
            "evidence_ids": [e["id"] for e in data["evidence"]],
        }
    )
    root = store.put_revision(data, inventory_sha256=inventory, reviewed=True)
    store.compare_and_swap_head(component.id, root.revision_id, None)
    child = copy.deepcopy(data)
    child["revision"]["id"] = "phase9-reviewed-child"
    child["revision"]["parent_id"] = root.revision_id
    child["revision"]["description"] = "Retained reviewed ancestry"
    revision = store.put_revision(
        child, inventory_sha256=inventory, reviewed=True
    )
    store.compare_and_swap_head(
        component.id, revision.revision_id, root.canonical_sha256
    )
    return component.id, child, inventory


def actions(connection, candidate):
    return {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT node_kind, action FROM build_dependencies "
            "WHERE build_id = ?",
            (candidate.build_id,),
        )
    }


def approve(connection, candidate):
    ReviewService(connection).approve(
        candidate.build_id,
        "fixture-reviewer",
        "Explicit fixture approval",
        candidate.binding,
        AuthenticatedPrincipal("fixture-reviewer", "local-test"),
    )


def test_reuse_skips_producers_and_validator_only_change(
    tmp_path, monkeypatch
):
    with database(tmp_path / "reuse.db") as connection:
        component, ir, _ = seed(connection)
        pipeline = KnownGoodReleasePipeline(connection)
        pdl = load_pdl("synthetic-0402")
        first = pipeline.run(component, ir["revision"]["id"], pdl)

        def forbidden(*args):
            raise AssertionError("Unchanged generator executed")

        for name in (
            "serialize_symbol",
            "serialize_footprint",
            "generate_model_3d",
        ):
            monkeypatch.setattr(pipeline_module, name, forbidden)
        second = pipeline.run(component, ir["revision"]["id"], pdl)
        assert set(actions(connection, second).values()) == {"REUSE"}
        assert build_hashes(connection, first.build_id) == build_hashes(
            connection, second.build_id
        )
        changed = pipeline.run(
            component,
            ir["revision"]["id"],
            pdl,
            configuration=BuildConfiguration(measurement_decimal_places=9),
        )
        assert actions(connection, changed) == {
            "SYMBOL": "REUSE",
            "FOOTPRINT": "REUSE",
            "MODEL_3D": "REUSE",
            "ASSOCIATION": "REUSE",
            "VALIDATION": "REVALIDATE",
        }
        assert changed.binding.artifact_hashes == first.binding.artifact_hashes
        assert (
            changed.binding.input_snapshot_hash
            != first.binding.input_snapshot_hash
        )
        with pytest.raises(ValueError):
            ReviewService(connection).approve(
                changed.build_id,
                "fixture-reviewer",
                "Stale binding",
                first.binding,
                AuthenticatedPrincipal("fixture-reviewer", "local-test"),
            )


def test_cad_only_and_placement_only_invalidation(tmp_path):
    with database(tmp_path / "cad.db") as connection:
        component, ir, inventory = seed(connection)
        pipeline = KnownGoodReleasePipeline(connection)
        pdl = load_pdl("synthetic-0402")
        first = pipeline.run(component, ir["revision"]["id"], pdl)
        changed = pipeline.run(
            component,
            ir["revision"]["id"],
            pdl,
            configuration=BuildConfiguration(step_precision_mode=1),
        )
        recorded = actions(connection, changed)
        assert recorded["SYMBOL"] == recorded["FOOTPRINT"] == "REUSE"
        assert recorded["MODEL_3D"] == recorded["ASSOCIATION"] == "GENERATE"
        # A portable association-path change affects only finalization/checks.
        placed = pipeline.run(
            component,
            ir["revision"]["id"],
            pdl,
            model_logical_path="3d/relocated.step",
        )
        assert actions(connection, placed) == {
            "SYMBOL": "REUSE",
            "FOOTPRINT": "REUSE",
            "MODEL_3D": "REUSE",
            "ASSOCIATION": "GENERATE",
            "VALIDATION": "REVALIDATE",
        }
        assert (
            first.binding.artifact_hashes[0]
            == placed.binding.artifact_hashes[0]
        )
        child = copy.deepcopy(ir)
        child["revision"]["id"] = "audit-child"
        child["revision"]["parent_id"] = ir["revision"]["id"]
        child["revision"]["description"] = "Only audit changed"
        store = ImmutableStore(connection)
        revision = store.put_revision(
            child, inventory_sha256=inventory, reviewed=True
        )
        store.compare_and_swap_head(
            component, revision.revision_id, ComponentIR(ir).sha256
        )
        audit = pipeline.run(component, revision.revision_id, pdl)
        assert set(actions(connection, audit).values()) == {"REUSE"}
        assert build_hashes(connection, first.build_id) == build_hashes(
            connection, audit.build_id
        )


def test_corrupt_cache_fails_closed(tmp_path):
    with database(tmp_path / "cache.db") as connection:
        component, ir, _ = seed(connection)
        pipeline = KnownGoodReleasePipeline(connection)
        pdl = load_pdl("synthetic-0402")
        pipeline.run(component, ir["revision"]["id"], pdl)
        connection.execute(
            "UPDATE node_cache SET canonical_bytes = X'7B7D' "
            "WHERE node_kind = 'SYMBOL'"
        )
        with pytest.raises(RuntimeError, match="content hash mismatch"):
            pipeline.run(component, ir["revision"]["id"], pdl)


def make_bundle(connection):
    component, ir, _ = seed(connection)
    service = OfflineReplayService(connection)
    candidate = service.pipeline.run(
        component, ir["revision"]["id"], load_pdl("synthetic-0402")
    )
    approve(connection, candidate)
    bundle = service.export(
        candidate.build_id,
        "phase9-offline",
        source_objects={sha256(SOURCE).hexdigest(): SOURCE},
    )
    return bundle


def test_offline_history_rebuild_and_missing_closure(tmp_path, monkeypatch):
    with database(tmp_path / "original.db") as connection:
        bundle = make_bundle(connection)

    def forbidden(*args, **kwargs):
        raise AssertionError("Network disabled during replay")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    with database(tmp_path / "imported.db") as connection:
        candidate, report = OfflineReplayService(connection).rebuild(bundle)
        assert report["status"] == "PASS"
        assert report["audit"]["left_run"] != report["audit"]["right_run"]
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == 2
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM approval_bindings"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM reproducibility_reports"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT state FROM builds WHERE id = ?", (candidate.build_id,)
            ).fetchone()[0]
            == "HUMAN_REVIEW_REQUIRED"
        )
    # A rehashed index omitting a required source must fail pre-execution.
    path = "source/" + sha256(SOURCE).hexdigest()
    objects = dict(bundle.objects)
    objects.pop(path)
    index = copy.deepcopy(bundle.index)
    index["objects"] = [e for e in index["objects"] if e["path"] != path]
    with database(tmp_path / "missing.db") as connection:
        with pytest.raises(
            ValueError, match="source inspection closure missing"
        ):
            OfflineReplayService(connection).rebuild(
                ReplayBundle(index, objects)
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM components").fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "path",
    [
        "history/index.json",
        "inputs/pdl.json",
        "schemas/ir.json",
        "runtime/lock.json",
    ],
)
def test_replay_tampering_prevents_execution(tmp_path, path):
    with database(tmp_path / "source.db") as connection:
        bundle = make_bundle(connection)
    objects = dict(bundle.objects)
    objects[path] += b"tampered"
    with database(tmp_path / "target.db") as connection:
        with pytest.raises(ValueError, match="hash mismatch"):
            OfflineReplayService(connection).rebuild(
                ReplayBundle(bundle.index, objects)
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
            == 0
        )


def test_independent_clean_processes_and_offline_replay(tmp_path):
    """@brief Compares two clean processes and their offline replay results.
    @param tmp_path Disposable independent worker directories.
    @return None.
    @details Child failures retain diagnostics on KiCad's Windows Python.
    """
    outcomes = []
    for seed_value in (11, 97):
        directory = tmp_path / str(seed_value)
        directory.mkdir()
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed_value)
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), str(directory)],
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        outcomes.append(json.loads((directory / "outcome.json").read_bytes()))
    report = comparison_report(
        outcomes[0]["hashes"],
        outcomes[1]["hashes"],
        left_run=outcomes[0]["run"],
        right_run=outcomes[1]["run"],
    )
    assert report["status"] == "PASS"
    assert outcomes[0]["run"] != outcomes[1]["run"]
    assert all(outcome["replay"]["status"] == "PASS" for outcome in outcomes)


def worker(directory):
    def prohibit_network(event, args):
        if event in {
            "socket.connect",
            "socket.getaddrinfo",
            "socket.gethostbyname",
        }:
            raise RuntimeError(
                "Network disabled for clean build/offline replay"
            )

    sys.addaudithook(prohibit_network)
    with pytest.raises(RuntimeError, match="Network disabled"):
        socket.create_connection(("example.invalid", 80))
    with database(directory / "clean.db") as connection:
        bundle = make_bundle(connection)
        hashes = bundle.index["expected"]
    with database(directory / "replay.db") as connection:
        _, replay = OfflineReplayService(connection).rebuild(bundle)
    (directory / "outcome.json").write_bytes(
        canonical_json(
            {
                "hashes": hashes,
                "run": bundle.index["original_run"],
                "replay": replay,
                "network": "Python socket/DNS APIs denied by audit hook",
            }
        )
    )


if __name__ == "__main__":
    worker(Path(sys.argv[1]))
