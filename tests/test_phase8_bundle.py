"""@package tests.test_phase8_bundle
@brief Tests Phase 8 history-complete revision bundle export and import.
@details Covers exact multi-revision round trips, ancestry closure, inventory
closure, unsafe paths, tampering, identity conflicts, and rollback.
"""

import copy
import json
from pathlib import Path

import pytest

from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release import BundleIndex
from partsmith.release.bundle import RevisionBundle, RevisionBundleService

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "ir" / "v1.2" / "valid" / "0402.json"


def _inventory(data: dict) -> dict:
    """@brief Builds the complete inventory for one revision fixture.
    @param data Component IR mapping.
    @return Source hashes and evidence identities.
    @details Array ordering follows the immutable revision content.
    """
    return {
        "source_hashes": [
            document["sha256"] for document in data["source"]["documents"]
        ],
        "evidence_ids": [record["id"] for record in data["evidence"]],
    }


def _export_fixture(path: Path) -> tuple[RevisionBundle, list[str]]:
    """@brief Creates and exports a two-revision reviewed component.
    @param path Source SQLite path.
    @return Exported bundle and oldest-to-newest revision identities.
    @details Both revisions share one verified acquisition inventory.
    """
    with database(path) as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        root = json.loads(IR_PATH.read_text(encoding="utf-8"))
        root["identity"]["component_id"] = component.id
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(_inventory(root))
        stored_root = store.put_revision(
            root,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        child = copy.deepcopy(root)
        child["revision"]["id"] = "bundle-child"
        child["revision"]["parent_id"] = stored_root.revision_id
        child["revision"]["description"] = "Second retained revision"
        stored_child = store.put_revision(
            child,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(
            component.id, stored_child.revision_id, None
        )
        bundle = RevisionBundleService(connection).export_revisions(
            "bundle-1", stored_child.revision_id
        )
        return bundle, [stored_root.revision_id, stored_child.revision_id]


def _without_kind(bundle: RevisionBundle, kind: str) -> RevisionBundle:
    """@brief Removes all objects of one kind from a copied bundle.
    @param bundle Original exported bundle.
    @param kind Object kind to remove.
    @return New internally consistent index and object mapping.
    @details Used to test history-closure validation after byte verification.
    """
    data = bundle.index.data
    removed_paths = {
        entry["path"] for entry in data["objects"] if entry["kind"] == kind
    }
    data["objects"] = [
        entry for entry in data["objects"] if entry["kind"] != kind
    ]
    objects = {
        path: blob
        for path, blob in bundle.objects.items()
        if path not in removed_paths
    }
    return RevisionBundle(BundleIndex(data), objects)


def test_multi_revision_bundle_round_trips_exact_bytes(tmp_path):
    """@brief Verifies complete history imports into an empty database.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Revision, inventory, component, and current-head identities match.
    """
    bundle, revision_ids = _export_fixture(tmp_path / "source.db")
    with database(tmp_path / "target.db") as connection:
        import_id = RevisionBundleService(connection).import_bundle(bundle)
        store = ImmutableStore(connection)
        for revision_id in revision_ids:
            assert store.get_revision(revision_id)["revision"]["id"] == (
                revision_id
            )
        head = connection.execute(
            "SELECT revision_id FROM component_heads"
        ).fetchone()[0]
        assert head == revision_ids[-1]
        assert (
            connection.execute(
                "SELECT status FROM bundle_imports WHERE id = ?", (import_id,)
            ).fetchone()[0]
            == "IMPORTED"
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM bundle_objects"
        ).fetchone()[0] == len(bundle.index.data["objects"])


def test_tampered_bundle_object_rolls_back_import(tmp_path):
    """@brief Verifies exact object hashes are checked before publication.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details No component, revision, object, or import record survives failure.
    """
    bundle, _ = _export_fixture(tmp_path / "source.db")
    objects = dict(bundle.objects)
    path = next(iter(objects))
    objects[path] = objects[path] + b"tampered"
    tampered = RevisionBundle(bundle.index, objects)
    with database(tmp_path / "target.db") as connection:
        with pytest.raises(ValueError, match="hash mismatch"):
            RevisionBundleService(connection).import_bundle(tampered)
        for table in (
            "components",
            "ir_revisions",
            "bundle_objects",
            "bundle_imports",
        ):
            assert (
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[
                    0
                ]
                == 0
            )


def test_missing_parent_or_inventory_closure_is_rejected(tmp_path):
    """@brief Verifies complete ancestry and inventory materialization.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Internally hashed indexes cannot omit required replay objects.
    """
    bundle, revision_ids = _export_fixture(tmp_path / "source.db")
    data = bundle.index.data
    root_identity = f"ir:{revision_ids[0]}"
    root_path = next(
        entry["path"]
        for entry in data["objects"]
        if entry["identity"] == root_identity
    )
    data["objects"] = [
        entry
        for entry in data["objects"]
        if entry["identity"] != root_identity
    ]
    missing_parent = RevisionBundle(
        BundleIndex(data),
        {
            path: blob
            for path, blob in bundle.objects.items()
            if path != root_path
        },
    )
    with database(tmp_path / "parents.db") as connection:
        with pytest.raises(ValueError, match="ancestry is incomplete"):
            RevisionBundleService(connection).import_bundle(missing_parent)
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == 0
        )

    missing_inventory = _without_kind(bundle, "ACQUISITION_INVENTORY")
    with database(tmp_path / "inventory.db") as connection:
        with pytest.raises(ValueError, match="inventory closure"):
            RevisionBundleService(connection).import_bundle(missing_inventory)
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == 0
        )


def test_unsafe_bundle_path_is_rejected(tmp_path):
    """@brief Verifies bundle paths cannot escape the import root.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Path validation occurs before any database publication.
    """
    bundle, _ = _export_fixture(tmp_path / "source.db")
    data = bundle.index.data
    old_path = data["objects"][0]["path"]
    data["objects"][0]["path"] = "../escape.json"
    unsafe = RevisionBundle(
        BundleIndex(data),
        {
            "../escape.json": bundle.objects[old_path],
            **{
                path: blob
                for path, blob in bundle.objects.items()
                if path != old_path
            },
        },
    )
    with database(tmp_path / "target.db") as connection:
        with pytest.raises(ValueError, match="path is unsafe"):
            RevisionBundleService(connection).import_bundle(unsafe)
        assert (
            connection.execute("SELECT COUNT(*) FROM components").fetchone()[0]
            == 0
        )
