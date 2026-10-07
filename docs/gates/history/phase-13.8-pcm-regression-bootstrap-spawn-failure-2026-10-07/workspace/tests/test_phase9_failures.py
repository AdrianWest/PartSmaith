"""Configuration and replay preflight failures cannot authorize a release."""

import copy
from hashlib import sha256

import pytest
from test_phase9 import SOURCE, actions, approve, make_bundle, seed

from partsmith.ir import ComponentIR
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, database
from partsmith.release import replay as replay_module
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.replay import OfflineReplayService, ReplayBundle
from partsmith.release.reproducibility import BuildConfiguration


def test_placement_change_reuses_geometry_but_revalidates(tmp_path):
    with database(tmp_path / "placement.db") as connection:
        component, ir, inventory = seed(connection)
        pipeline = KnownGoodReleasePipeline(connection)
        pdl = load_pdl("synthetic-0402")
        pipeline.run(component, ir["revision"]["id"], pdl)
        child = copy.deepcopy(ir)
        child["revision"]["id"] = "placement-child"
        child["revision"]["parent_id"] = ir["revision"]["id"]
        child["model_3d"]["placement"]["translation_mm"][0] = 2
        store = ImmutableStore(connection)
        revision = store.put_revision(
            child, inventory_sha256=inventory, reviewed=True
        )
        store.compare_and_swap_head(
            component, revision.revision_id, ComponentIR(ir).sha256
        )
        with pytest.raises(ValueError, match="final-byte validation failed"):
            pipeline.run(component, revision.revision_id, pdl)
        row = connection.execute(
            "SELECT id FROM builds ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        recorded = actions(
            connection, type("Candidate", (), {"build_id": row[0]})
        )
        assert recorded == {
            "SYMBOL": "REUSE",
            "FOOTPRINT": "REUSE",
            "MODEL_3D": "REUSE",
            "ASSOCIATION": "GENERATE",
            "VALIDATION": "REVALIDATE",
        }


def test_offline_export_requires_sources_and_explicit_approval(tmp_path):
    with database(tmp_path / "closure.db") as connection:
        component, ir, _ = seed(connection)
        service = OfflineReplayService(connection)
        candidate = service.pipeline.run(
            component, ir["revision"]["id"], load_pdl("synthetic-0402")
        )
        with pytest.raises(ValueError, match="explicit approval"):
            service.export(
                candidate.build_id, "no-approval", source_objects={}
            )
        approve(connection, candidate)
        with pytest.raises(ValueError, match="source object unavailable"):
            service.export(candidate.build_id, "no-source", source_objects={})
        with pytest.raises(ValueError, match="source object unavailable"):
            service.export(
                candidate.build_id,
                "bad-source",
                source_objects={
                    sha256(SOURCE).hexdigest(): b"changed source",
                },
            )


def test_runtime_mismatch_rejected_before_import(tmp_path, monkeypatch):
    with database(tmp_path / "source.db") as connection:
        bundle = make_bundle(connection)
    monkeypatch.setattr(
        replay_module,
        "runtime_configuration",
        lambda runtime: {"occt": "unreviewed"},
    )
    with database(tmp_path / "target.db") as connection:
        with pytest.raises(ValueError, match="runtime mismatch"):
            OfflineReplayService(connection).rebuild(bundle)
        assert (
            connection.execute("SELECT COUNT(*) FROM components").fetchone()[0]
            == 0
        )


def test_incompatible_schema_with_self_consistent_index_is_rejected(tmp_path):
    with database(tmp_path / "source.db") as connection:
        bundle = make_bundle(connection)
    objects = dict(bundle.objects)
    objects["schemas/ir.json"] = b"{}"
    index = copy.deepcopy(bundle.index)
    for entry in index["objects"]:
        if entry["path"] == "schemas/ir.json":
            entry["byte_length"] = 2
            entry["sha256"] = sha256(b"{}").hexdigest()
    with database(tmp_path / "target.db") as connection:
        with pytest.raises(
            ValueError, match="schema or runtime lock incompatible"
        ):
            OfflineReplayService(connection).rebuild(
                ReplayBundle(index, objects)
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM components").fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "settings",
    [
        {"step_precision_mode": 2},
        {"step_precision_mode": True},
        {"measurement_decimal_places": 5},
        {"measurement_decimal_places": 16},
    ],
)
def test_unsupported_configuration_rejected(settings):
    with pytest.raises(ValueError):
        BuildConfiguration(**settings)
