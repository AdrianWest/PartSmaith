"""@package partsmith.persistence.immutable
@brief Immutable SQLite revision and acquisition-inventory storage.
@details Implements exact-byte retrieval, identity conflict detection, and
compare-and-swap component heads without committing caller transactions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.ir.history import as_data
from partsmith.ir.schema import fragment_valid


class IdentityConflictError(ValueError):
    """@brief Reports reuse of an immutable identity with different bytes.
    @details Callers must create a new identity instead of replacing history.
    """


class StaleHeadError(RuntimeError):
    """@brief Reports a failed component-head compare-and-swap.
    @details The caller must reread and review the new immutable head.
    """


@dataclass(frozen=True)
class StoredRevision:
    """@brief Identifies one stored immutable IR revision.
    @details Canonical bytes remain in SQLite and are returned detached.
    """

    revision_id: str
    component_id: str
    canonical_sha256: str
    inventory_sha256: str | None
    reviewed: bool


class ImmutableStore:
    """@brief Stores immutable revisions and acquisition inventories.
    @details Methods participate in the caller's transaction and never commit.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the immutable store.
        @param connection Migrated SQLite connection with foreign keys enabled.
        @return None.
        @details The caller owns transactions, rollback, and connection
        lifetime.
        """
        self.connection = connection

    def put_inventory(self, inventory: dict) -> str:
        """@brief Inserts or verifies one canonical acquisition inventory.
        @param inventory Acquisition inventory matching the IR 1.2 definition.
        @return SHA-256 digest of the exact canonical bytes.
        @details Equal bytes are idempotent; hash collisions or invalid content
        fail explicitly.
        """
        if not fragment_valid(inventory, {"$ref": "#/$defs/inventory"}):
            raise ValueError("Invalid acquisition inventory")
        blob = canonical_json(inventory)
        digest = sha256(blob).hexdigest()
        existing = self.connection.execute(
            "SELECT canonical_bytes FROM acquisition_inventories "
            "WHERE sha256 = ?",
            (digest,),
        ).fetchone()
        if existing is not None:
            if bytes(existing["canonical_bytes"]) != blob:
                raise IdentityConflictError(
                    "Inventory digest is bound to different bytes"
                )
            return digest
        now = datetime.now(UTC).isoformat()
        self.connection.execute(
            "INSERT INTO acquisition_inventories VALUES (?, ?, ?, ?)",
            (digest, blob, now, now),
        )
        return digest

    def put_revision(
        self,
        revision: dict,
        *,
        inventory_sha256: str | None,
        reviewed: bool,
    ) -> StoredRevision:
        """@brief Inserts or verifies one immutable IR revision.
        @param revision Complete normalized Component IR revision.
        @param inventory_sha256 Bound acquisition inventory digest.
        @param reviewed Whether input review approved this revision.
        @return Stored immutable revision identity and hashes.
        @details Reviewed revisions require a resolving inventory. Parent
        revisions must already exist and belong to the same component.
        """
        data = as_data(revision)
        revision_id = data["revision"]["id"]
        component_id = data["identity"]["component_id"]
        parent_id = data["revision"]["parent_id"]
        blob = canonical_json(data)
        digest = sha256(blob).hexdigest()
        existing = self.connection.execute(
            "SELECT * FROM ir_revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if existing is not None:
            if (
                bytes(existing["canonical_bytes"]) != blob
                or existing["canonical_sha256"] != digest
                or existing["component_id"] != component_id
            ):
                raise IdentityConflictError(
                    "Revision identity is bound to different bytes"
                )
            return StoredRevision(
                revision_id=revision_id,
                component_id=component_id,
                canonical_sha256=digest,
                inventory_sha256=existing["inventory_sha256"],
                reviewed=bool(existing["reviewed"]),
            )
        if reviewed and inventory_sha256 is None:
            raise ValueError("Reviewed revision requires an inventory")
        if inventory_sha256 is not None:
            inventory = self.connection.execute(
                "SELECT 1 FROM acquisition_inventories WHERE sha256 = ?",
                (inventory_sha256,),
            ).fetchone()
            if inventory is None:
                raise ValueError("Revision inventory does not resolve")
        if parent_id is not None:
            parent = self.connection.execute(
                "SELECT component_id FROM ir_revisions WHERE id = ?",
                (parent_id,),
            ).fetchone()
            if parent is None:
                raise ValueError("Revision parent does not resolve")
            if parent["component_id"] != component_id:
                raise ValueError(
                    "Revision parent belongs to another component"
                )
        now = datetime.now(UTC).isoformat()
        self.connection.execute(
            "INSERT INTO ir_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                revision_id,
                component_id,
                parent_id,
                digest,
                blob,
                inventory_sha256,
                int(reviewed),
                now,
                now,
            ),
        )
        return StoredRevision(
            revision_id=revision_id,
            component_id=component_id,
            canonical_sha256=digest,
            inventory_sha256=inventory_sha256,
            reviewed=reviewed,
        )

    def get_revision(self, revision_id: str) -> dict:
        """@brief Retrieves one immutable revision by identity.
        @param revision_id Revision identity to retrieve.
        @return Detached exact revision mapping.
        @details Raises KeyError when the identity is absent.
        """
        row = self.connection.execute(
            "SELECT canonical_sha256, canonical_bytes FROM ir_revisions "
            "WHERE id = ?",
            (revision_id,),
        ).fetchone()
        if row is None:
            raise KeyError(revision_id)
        blob = bytes(row["canonical_bytes"])
        if sha256(blob).hexdigest() != row["canonical_sha256"]:
            raise RuntimeError("Stored revision hash mismatch")
        return parse_json(blob)

    def get_inventory(self, digest: str) -> dict:
        """@brief Retrieves one immutable inventory by content digest.
        @param digest Inventory SHA-256 digest.
        @return Detached exact inventory mapping.
        @details Raises KeyError when absent and RuntimeError on corruption.
        """
        row = self.connection.execute(
            "SELECT canonical_bytes FROM acquisition_inventories "
            "WHERE sha256 = ?",
            (digest,),
        ).fetchone()
        if row is None:
            raise KeyError(digest)
        blob = bytes(row["canonical_bytes"])
        if sha256(blob).hexdigest() != digest:
            raise RuntimeError("Stored inventory hash mismatch")
        return parse_json(blob)

    def compare_and_swap_head(
        self,
        component_id: str,
        revision_id: str,
        expected_head_hash: str | None,
    ) -> None:
        """@brief Atomically advances a component's reviewed revision head.
        @param component_id Component whose current head is updated.
        @param revision_id Reviewed revision that becomes current.
        @param expected_head_hash Expected current head digest, or None.
        @return None.
        @details A stale head raises StaleHeadError without silently rebasing.
        """
        revision = self.connection.execute(
            "SELECT component_id, canonical_sha256, reviewed, "
            "inventory_sha256 FROM ir_revisions WHERE id = ?",
            (revision_id,),
        ).fetchone()
        if revision is None:
            raise ValueError("Head revision does not resolve")
        if revision["component_id"] != component_id:
            raise ValueError("Head revision belongs to another component")
        if not revision["reviewed"] or revision["inventory_sha256"] is None:
            raise ValueError("Current head must be a reviewed revision")
        now = datetime.now(UTC).isoformat()
        if expected_head_hash is None:
            try:
                self.connection.execute(
                    "INSERT INTO component_heads VALUES (?, ?, ?, ?)",
                    (
                        component_id,
                        revision_id,
                        revision["canonical_sha256"],
                        now,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise StaleHeadError(
                    "Component head already exists"
                ) from error
            return
        cursor = self.connection.execute(
            "UPDATE component_heads SET revision_id = ?, revision_hash = ?, "
            "updated_at = ? WHERE component_id = ? AND revision_hash = ?",
            (
                revision_id,
                revision["canonical_sha256"],
                now,
                component_id,
                expected_head_hash,
            ),
        )
        if cursor.rowcount != 1:
            raise StaleHeadError("Component head changed")
