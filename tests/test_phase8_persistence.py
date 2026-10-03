"""@package tests.test_phase8_persistence
@brief Tests immutable Phase 8 revision and inventory persistence.
@details Covers exact-byte retrieval, identity conflicts, reviewed heads,
stale compare-and-swap rejection, reopening, and transaction rollback.
"""

import copy
import json
from pathlib import Path

import pytest

from partsmith.ir import ComponentIR, canonical_json
from partsmith.persistence import (
    IdentityConflictError,
    ImmutableStore,
    Repository,
    StaleHeadError,
    database,
)

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "ir" / "v1.2" / "valid" / "0402.json"


def _inventory(data: dict) -> dict:
    """@brief Builds the canonical inventory for one fixture revision.
    @param data Component IR fixture mapping.
    @return Acquisition inventory matching the IR 1.2 schema.
    @details Inventory ordering follows the reviewed fixture arrays.
    """
    return {
        "source_hashes": [
            document["sha256"] for document in data["source"]["documents"]
        ],
        "evidence_ids": [evidence["id"] for evidence in data["evidence"]],
    }


def _revision(component_id: str) -> dict:
    """@brief Loads a detached fixture revision for one persisted component.
    @param component_id Persisted component identity.
    @return Updated Component IR fixture mapping.
    @details Only the local component identity changes for these store tests.
    """
    data = json.loads(IR_PATH.read_text(encoding="utf-8"))
    data["identity"]["component_id"] = component_id
    return data


def test_immutable_store_reopens_exact_revision_and_inventory(tmp_path):
    """@brief Verifies exact immutable content survives database reopening.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Canonical bytes and hashes remain stable across connections.
    """
    path = tmp_path / "phase8.sqlite3"
    with database(path) as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        data = _revision(component.id)
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(_inventory(data))
        stored = store.put_revision(
            data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, stored.revision_id, None)
        expected_bytes = ComponentIR(data).canonical_bytes

    with database(path) as connection:
        store = ImmutableStore(connection)
        assert canonical_json(store.get_revision(stored.revision_id)) == (
            expected_bytes
        )
        assert store.get_inventory(inventory_hash) == _inventory(data)


def test_revision_identity_conflict_and_missing_parent_fail(tmp_path):
    """@brief Verifies immutable identities and ancestry cannot be rewritten.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Different bytes under one ID and unresolved parents fail.
    """
    with database(tmp_path / "db") as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        data = _revision(component.id)
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(_inventory(data))
        store.put_revision(
            data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        changed = copy.deepcopy(data)
        changed["identity"]["mpn"] = "changed"
        with pytest.raises(IdentityConflictError):
            store.put_revision(
                changed,
                inventory_sha256=inventory_hash,
                reviewed=True,
            )
        child = copy.deepcopy(data)
        child["revision"]["id"] = "missing-parent-child"
        child["revision"]["parent_id"] = "missing"
        with pytest.raises(ValueError, match="parent"):
            store.put_revision(
                child,
                inventory_sha256=inventory_hash,
                reviewed=True,
            )


def test_stale_head_rejection_and_rollback_are_atomic(tmp_path):
    """@brief Verifies stale heads and caller rollback leave no partial data.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Failed compare-and-swap never advances the current head.
    """
    path = tmp_path / "db"
    with database(path) as connection:
        component = Repository(connection).create_component(
            "Synthetic", "0402", "0402"
        )
        data = _revision(component.id)
        store = ImmutableStore(connection)
        inventory_hash = store.put_inventory(_inventory(data))
        root = store.put_revision(
            data,
            inventory_sha256=inventory_hash,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, root.revision_id, None)
        with pytest.raises(StaleHeadError):
            store.compare_and_swap_head(
                component.id,
                root.revision_id,
                "0" * 64,
            )

    with pytest.raises(RuntimeError, match="abort"):
        with database(path) as connection:
            store = ImmutableStore(connection)
            candidate = _revision(component.id)
            candidate["revision"]["id"] = "rolled-back"
            candidate["revision"]["parent_id"] = root.revision_id
            store.put_revision(
                candidate,
                inventory_sha256=inventory_hash,
                reviewed=False,
            )
            raise RuntimeError("abort")

    with database(path) as connection:
        store = ImmutableStore(connection)
        with pytest.raises(KeyError):
            store.get_revision("rolled-back")
