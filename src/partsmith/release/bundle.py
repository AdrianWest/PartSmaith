"""@package partsmith.release.bundle
@brief History-complete Phase 8 revision bundle export and import.
@details Builds deterministic indexes, verifies every declared object, and
publishes complete revision ancestry transactionally.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import PurePosixPath
from uuid import uuid4

from partsmith.ir import ComponentIR, canonical_json
from partsmith.ir.canonical import parse_json
from partsmith.persistence.immutable import (
    IdentityConflictError,
    ImmutableStore,
)
from partsmith.release.contracts import BundleIndex


def _now() -> str:
    """@brief Returns one UTC bundle audit timestamp.
    @return ISO 8601 UTC timestamp.
    @details Audit timestamps are not included in deterministic indexes.
    """
    return datetime.now(UTC).isoformat()


@contextmanager
def _savepoint(connection: sqlite3.Connection, name: str) -> Iterator[None]:
    """@brief Protects bundle publication with a SQLite savepoint.
    @param connection Active SQLite connection.
    @param name Trusted internal savepoint name.
    @return Iterator yielding control inside the savepoint.
    @details Verification failures leave no component, object, or revision.
    """
    connection.execute(f"SAVEPOINT {name}")
    try:
        yield
    except BaseException:
        connection.execute(f"ROLLBACK TO {name}")
        connection.execute(f"RELEASE {name}")
        raise
    else:
        connection.execute(f"RELEASE {name}")


def _safe_path(value: str) -> str:
    """@brief Validates one portable bundle-relative object path.
    @param value Proposed relative path.
    @return Normalized POSIX relative path.
    @details Absolute, parent-relative, drive, and backslash paths fail.
    """
    if not value or "\\" in value or ":" in value:
        raise ValueError("Bundle object path is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) == ".":
        raise ValueError("Bundle object path is unsafe")
    return str(path)


@dataclass(frozen=True)
class RevisionBundle:
    """@brief Contains one frozen bundle index and exact object bytes.
    @details Object mappings are keyed by the paths declared in the index.
    """

    index: BundleIndex
    objects: dict[str, bytes]


class RevisionBundleService:
    """@brief Exports and imports complete immutable revision histories.
    @details Current Phase 8 support is OFFLINE_COMPLETE and materializes every
    referenced revision and acquisition inventory locally.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the revision bundle service.
        @param connection Migrated SQLite connection.
        @return None.
        @details The caller owns the outer transaction and connection.
        """
        self.connection = connection
        self.store = ImmutableStore(connection)

    def _revision_row(self, revision_id: str) -> sqlite3.Row:
        """@brief Resolves one immutable revision storage row.
        @param revision_id Revision identity.
        @return Complete persisted revision row.
        @details Missing revisions fail rather than creating partial bundles.
        """
        row = self.connection.execute(
            "SELECT * FROM ir_revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            raise KeyError(revision_id)
        return row

    def export_revisions(
        self, bundle_id: str, head_revision_id: str
    ) -> RevisionBundle:
        """@brief Exports one complete reviewed revision ancestry.
        @param bundle_id Stable transport-independent bundle identity.
        @param head_revision_id Reviewed current revision to export.
        @return Frozen index and exact materialized object bytes.
        @details Every parent and referenced inventory is included exactly
        once.
        """
        if not bundle_id:
            raise ValueError("bundle_id must not be empty")
        head = self._revision_row(head_revision_id)
        if not head["reviewed"]:
            raise ValueError("Bundle head must be reviewed")
        component = self.connection.execute(
            "SELECT * FROM components WHERE id = ?",
            (head["component_id"],),
        ).fetchone()
        if component is None:
            raise RuntimeError("Revision component does not resolve")
        chain = []
        seen = set()
        current = head
        while current is not None:
            if current["id"] in seen:
                raise ValueError("Revision ancestry is cyclic")
            seen.add(current["id"])
            chain.append(current)
            parent_id = current["parent_id"]
            current = (
                None if parent_id is None else self._revision_row(parent_id)
            )
        chain.reverse()
        entries = []
        objects = {}
        inventories = set()
        for row in chain:
            blob = bytes(row["canonical_bytes"])
            if sha256(blob).hexdigest() != row["canonical_sha256"]:
                raise RuntimeError("Stored revision hash mismatch")
            path = _safe_path(f"ir/{row['id']}.json")
            objects[path] = blob
            entries.append(
                {
                    "identity": f"ir:{row['id']}",
                    "kind": "IR_REVISION",
                    "schema_version": parse_json(blob)["schema_version"],
                    "path": path,
                    "byte_length": len(blob),
                    "sha256": row["canonical_sha256"],
                    "metadata": {
                        "revision_id": row["id"],
                        "component_id": row["component_id"],
                        "parent_id": row["parent_id"],
                        "inventory_sha256": row["inventory_sha256"],
                        "reviewed": bool(row["reviewed"]),
                    },
                }
            )
            if row["inventory_sha256"] is not None:
                inventories.add(row["inventory_sha256"])
        for digest in sorted(inventories):
            data = self.store.get_inventory(digest)
            blob = canonical_json(data)
            path = _safe_path(f"inventory/{digest}.json")
            objects[path] = blob
            entries.append(
                {
                    "identity": f"inventory:{digest}",
                    "kind": "ACQUISITION_INVENTORY",
                    "schema_version": "1.0",
                    "path": path,
                    "byte_length": len(blob),
                    "sha256": digest,
                    "metadata": {},
                }
            )
        entries.sort(key=lambda entry: entry["identity"])
        index = BundleIndex(
            {
                "schema_version": "1.0",
                "bundle_id": bundle_id,
                "availability": "OFFLINE_COMPLETE",
                "component": {
                    "id": component["id"],
                    "manufacturer": component["manufacturer"],
                    "mpn": component["mpn"],
                    "package_variant": component["package_variant"],
                },
                "head_revision_id": head_revision_id,
                "objects": entries,
            }
        )
        return RevisionBundle(index, objects)

    def _verified_objects(
        self, bundle: RevisionBundle
    ) -> dict[str, tuple[dict, bytes]]:
        """@brief Verifies all declared object paths, lengths, and hashes.
        @param bundle Bundle index and supplied object mapping.
        @return Verified entries and bytes keyed by object identity.
        @details Missing, extra, duplicate, unsafe, or tampered objects fail.
        """
        entries = {}
        paths = set()
        declared_paths = set()
        for entry in bundle.index.data["objects"]:
            identity = entry["identity"]
            path = _safe_path(entry["path"])
            if identity in entries or path in paths:
                raise ValueError("Bundle contains duplicate object identity")
            paths.add(path)
            declared_paths.add(path)
            blob = bundle.objects.get(path)
            if blob is None:
                raise ValueError("Bundle object is missing")
            if not isinstance(blob, bytes):
                raise TypeError("Bundle object content must be bytes")
            if (
                len(blob) != entry["byte_length"]
                or sha256(blob).hexdigest() != entry["sha256"]
            ):
                raise ValueError("Bundle object hash mismatch")
            entries[identity] = (entry, blob)
        if set(bundle.objects) != declared_paths:
            raise ValueError("Bundle contains undeclared objects")
        return entries

    def import_bundle(self, bundle: RevisionBundle) -> str:
        """@brief Verifies and transactionally imports one complete bundle.
        @param bundle Frozen index and supplied object bytes.
        @return Bundle import audit identity.
        @details Entire ancestry and inventories are staged before publication.
        """
        with _savepoint(self.connection, "revision_bundle_import"):
            entries = self._verified_objects(bundle)
            revisions = {}
            inventories = {}
            for entry, blob in entries.values():
                if entry["kind"] == "IR_REVISION":
                    data = ComponentIR(parse_json(blob)).data
                    metadata = entry["metadata"]
                    if (
                        data["revision"]["id"] != metadata["revision_id"]
                        or data["identity"]["component_id"]
                        != metadata["component_id"]
                        or data["revision"]["parent_id"]
                        != metadata["parent_id"]
                    ):
                        raise ValueError("Bundle revision metadata mismatch")
                    revisions[data["revision"]["id"]] = (
                        data,
                        metadata,
                        entry["sha256"],
                    )
                else:
                    inventories[entry["sha256"]] = parse_json(blob)
            head_id = bundle.index.data["head_revision_id"]
            if head_id not in revisions:
                raise ValueError("Bundle head revision is missing")
            order = []
            seen = set()
            current_id = head_id
            while current_id is not None:
                if current_id in seen or current_id not in revisions:
                    raise ValueError("Bundle revision ancestry is incomplete")
                seen.add(current_id)
                order.append(current_id)
                current_id = revisions[current_id][0]["revision"]["parent_id"]
            if seen != set(revisions):
                raise ValueError("Bundle contains unreachable revisions")
            order.reverse()
            required_inventories = {
                metadata["inventory_sha256"]
                for _, metadata, _ in revisions.values()
                if metadata["inventory_sha256"] is not None
            }
            if required_inventories != set(inventories):
                raise ValueError("Bundle inventory closure is incomplete")
            component_data = bundle.index.data["component"]
            existing = self.connection.execute(
                "SELECT * FROM components WHERE id = ?",
                (component_data["id"],),
            ).fetchone()
            if existing is None:
                now = _now()
                self.connection.execute(
                    "INSERT INTO components VALUES (?, NULL, ?, ?, ?, ?, ?)",
                    (
                        component_data["id"],
                        component_data["manufacturer"],
                        component_data["mpn"],
                        component_data["package_variant"],
                        now,
                        now,
                    ),
                )
            elif any(
                existing[key] != component_data[key]
                for key in ("manufacturer", "mpn", "package_variant")
            ):
                raise IdentityConflictError(
                    "Component identity is bound to different content"
                )
            for digest in sorted(inventories):
                if self.store.put_inventory(inventories[digest]) != digest:
                    raise ValueError("Bundle inventory identity mismatch")
            stored = {}
            for revision_id in order:
                data, metadata, digest = revisions[revision_id]
                result = self.store.put_revision(
                    data,
                    inventory_sha256=metadata["inventory_sha256"],
                    reviewed=metadata["reviewed"],
                )
                if result.canonical_sha256 != digest:
                    raise ValueError("Bundle revision identity mismatch")
                stored[revision_id] = result
            head = stored[head_id]
            self.store.compare_and_swap_head(
                component_data["id"], head.revision_id, None
            )
            now = _now()
            for entry, blob in entries.values():
                self.connection.execute(
                    "INSERT INTO bundle_objects VALUES "
                    "(?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                    (
                        bundle.index.data["bundle_id"],
                        entry["identity"],
                        entry["kind"],
                        entry["schema_version"],
                        entry["path"],
                        int(entry["byte_length"]),
                        entry["sha256"],
                        blob,
                        now,
                        now,
                    ),
                )
            import_id = str(uuid4())
            self.connection.execute(
                "INSERT INTO bundle_imports VALUES "
                "(?, ?, ?, 'OFFLINE_COMPLETE', 'IMPORTED', ?, ?, ?)",
                (
                    import_id,
                    bundle.index.data["bundle_id"],
                    bundle.index.sha256,
                    bundle.index.canonical_bytes,
                    now,
                    now,
                ),
            )
            return import_id
