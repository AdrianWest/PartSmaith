"""@package partsmith.integration.target
@brief Registers owned complete project copies and one stable NTFS boundary.
@details Original projects stay unchanged. Immutable database metadata and
native file IDs reject foreign/replaced containers, junctions and generations.
Only explicitly quiesced, exclusively edited local NTFS targets are supported.
"""

import ctypes
import os
import re
import sqlite3
import stat
import unicodedata
from contextlib import ExitStack, contextmanager
from pathlib import Path
from uuid import uuid4

from partsmith.integration.atomic_target import (
    WindowsFiles,
    _ordinary_ancestors,
    junction_buffer,
)
from partsmith.integration.bindings import verify_files
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.planner import (
    TABLES,
    file_inventory,
    read_project,
    snapshot_target,
)
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.schema import validate_shape
from partsmith.integration.sexpr import Atom, serialize
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence.database import utc_timestamp


def durable_file(path: Path, blob: bytes) -> None:
    """@brief Writes and flushes one new exclusively owned file.
    @param path Absent file inside a verified owned ordinary directory.
    @param blob Exact already bounded immutable content.
    @return None.
    @details Exclusive creation refuses replacement; fsync flushes data.
    """
    with path.open("xb") as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())


def canonical_directory(api: WindowsFiles, path: Path) -> Path:
    """@brief Resolves an ordinary directory's actual native canonical path.
    @param api Verified native Windows filesystem adapter.
    @param path Existing explicit ordinary directory.
    @return Full normalized native directory path.
    @details Rejects foreign reparse ancestors before following a handle;
    normalizes short-name aliases for source/destination containment checks.
    """
    _ordinary_ancestors(path.absolute())
    with api.directory(path.absolute()) as handle:
        return api.final_path(handle)


def write_slot(root: Path, objects: dict, directories: tuple) -> None:
    """@brief Writes and verifies a new complete physical generation.
    @param root Absent owned physical slot.
    @param objects Complete bounded project file mapping.
    @param directories Exact sorted ordinary directory inventory.
    @return None.
    @details The active junction is never touched by slot creation.
    """
    inventory = file_inventory(objects)
    root.mkdir()
    for name in directories:
        (root / name).mkdir(parents=True, exist_ok=True)
    for name, blob in sorted(objects.items()):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        durable_file(path, blob)
    actual, actual_directories = read_project(root)
    verify_files(inventory, actual)
    if actual_directories != directories:
        raise IntegrationError(FailureCode.TAMPERED_SOURCE)


class OwnedTarget:
    """@brief Resolves a trusted container and current physical slot.
    @details A matching imported path/marker alone cannot register a target.
    """

    def __init__(self, connection: sqlite3.Connection, target: dict):
        """@brief Opens trusted ownership metadata without modifying files.
        @param connection Authoritative migrated application integration store.
        @param target Exact independently selected logical identity.
        @return None.
        @details Every resolution rechecks raw junction/container identity.
        """
        self.connection = connection
        self.target = dict(target)
        validate_shape("target", self.target)
        row = connection.execute(
            "SELECT * FROM integration_targets WHERE project_id=?",
            (target["project_id"],),
        ).fetchone()
        if (
            row is None
            or (row["library_id"], row["scope"])
            != (target["library_id"], "project-local")
            or target["scope"] != "project-local"
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        self.metadata = parse_json(bytes(row["ownership_bytes"]))
        if (
            set(self.metadata)
            != {
                "schema_version",
                "owner",
                "workspace",
                "container_identity",
                "link_identity",
                "volume",
                "initial_slot",
                "initial_identity",
                "slots_identity",
                "lock_identity",
            }
            or self.metadata["schema_version"] != "partsmith-owned-target-1.0"
        ):
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        self.workspace = Path(self.metadata["workspace"])
        self.link = Path(row["root"])
        if (
            not self.workspace.is_absolute()
            or self.link != self.workspace / "active"
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        self.api = WindowsFiles()
        self.current()

    @classmethod
    def create(
        cls,
        connection: sqlite3.Connection,
        target: dict,
        original: Path,
        workspace: Path,
        closed: ClosedProject,
    ):
        """@brief Registers a complete owned copy of a closed project.
        @param connection Idle authoritative application integration database.
        @param target New exact project-local logical identity.
        @param original Ordinary source project to preserve unchanged.
        @param workspace Absent managed container on fixed local NTFS.
        @param closed Fresh explicit closed/exclusive-writer confirmation.
        @return Newly registered verified owned target.
        @details Missing paired project tables are established as empty tables
        in the copy. Registration is explicit and owns its idle transaction.
        """
        if (
            connection.in_transaction
            or connection.execute(
                "SELECT 1 FROM integration_targets WHERE project_id=?",
                (target["project_id"],),
            ).fetchone()
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        validate_shape("target", target)
        closed.require(target)
        api = WindowsFiles()
        original = canonical_directory(api, original)
        parent = canonical_directory(api, workspace.absolute().parent)
        from partsmith.integration.contracts import portable_path

        portable_path(workspace.name)
        if unicodedata.normalize("NFC", str(parent)) != str(parent):
            raise IntegrationError(FailureCode.PATH_CONFLICT)
        workspace = parent / workspace.name
        if workspace.exists() or workspace.is_relative_to(original):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        volume = api.volume(workspace.parent)
        api.volume(original)
        snapshot = snapshot_target(original, target, None)
        objects, directories = dict(snapshot.objects), snapshot.directories
        if (
            len(
                [
                    name
                    for name in objects
                    if "/" not in name and name.endswith(".kicad_pro")
                ]
            )
            != 1
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        for name, kind in TABLES.items():
            objects.setdefault(
                name, serialize([Atom(kind), [Atom("version"), Atom("7")]])
            )
        workspace.mkdir()
        owner, slot = uuid4().hex, "slot-" + uuid4().hex
        durable_file(
            workspace / "owner.json",
            canonical_json(
                {
                    "schema_version": "partsmith-owned-marker-1.0",
                    "owner": owner,
                    "target": target,
                }
            ),
        )
        durable_file(workspace / "lock.bin", b"PartSmith publication lock\n")
        (workspace / "slots").mkdir()
        write_slot(workspace / "slots" / slot, objects, directories)
        with api.directory(workspace / "slots") as handle:
            slots_identity = list(api.identity(handle))
        with api.directory(workspace / "slots" / slot) as handle:
            initial_identity = list(api.identity(handle))
        with api.directory(workspace / "lock.bin", reparse=True) as handle:
            lock_identity = list(api.identity(handle))
        link = workspace / "active"
        link.mkdir()
        with api.directory(link, reparse=True, write=True) as handle:
            api.reparse(handle, junction_buffer(workspace / "slots" / slot))
            link_identity = list(api.identity(handle))
        with api.directory(workspace) as handle:
            identity = list(api.identity(handle))
        metadata = {
            "schema_version": "partsmith-owned-target-1.0",
            "owner": owner,
            "workspace": str(workspace),
            "container_identity": identity,
            "link_identity": link_identity,
            "volume": volume,
            "initial_slot": slot,
            "initial_identity": initial_identity,
            "slots_identity": slots_identity,
            "lock_identity": lock_identity,
        }
        snapshot.recheck()
        closed.require(target)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO integration_targets VALUES (?, ?, ?, ?, ?, ?)",
                (
                    target["project_id"],
                    target["library_id"],
                    target["scope"],
                    str(link),
                    canonical_json(metadata),
                    utc_timestamp(),
                ),
            )
            connection.execute(
                "INSERT INTO integration_heads VALUES (?, NULL)",
                (target["project_id"],),
            )
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        return cls(connection, target)

    def _ownership(self) -> None:
        """@brief Rechecks the immutable container, volume and marker.
        @return None.
        @details Does not adopt a renamed/replaced foreign directory or marker.
        """
        _ordinary_ancestors(self.workspace)
        _ordinary_ancestors(self.workspace / "slots")
        with self.api.directory(self.workspace / "slots") as handle:
            if (
                list(self.api.identity(handle))
                != self.metadata["slots_identity"]
            ):
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if self.api.volume(self.workspace) != self.metadata["volume"]:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        with self.api.directory(self.workspace) as handle:
            if (
                list(self.api.identity(handle))
                != self.metadata["container_identity"]
            ):
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
        marker = self.workspace / "owner.json"
        for path in (marker, self.workspace / "lock.bin"):
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or (
                getattr(info, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if marker.read_bytes() != canonical_json(
            {
                "schema_version": "partsmith-owned-marker-1.0",
                "owner": self.metadata["owner"],
                "target": self.target,
            }
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)

    def current(self) -> Path:
        """@brief Resolves the exact current trusted physical generation.
        @return Ordinary owned current slot path.
        @details Raw junction bytes and stable file ID must agree with the
        followed root; external targets, aliases and replaced roots fail.
        """
        self._ownership()
        with self.api.directory(self.link, reparse=True) as raw:
            if list(self.api.identity(raw)) != self.metadata["link_identity"]:
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            payload = self.api.reparse(raw)
        with self.api.directory(self.link) as followed:
            root = self.api.final_path(followed)
        if (
            root.parent != self.workspace / "slots"
            or not re.fullmatch(r"slot-[0-9a-f]{32}", root.name)
            or payload != junction_buffer(root)
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        _ordinary_ancestors(root)
        with self.api.directory(root) as handle:
            identity = list(self.api.identity(handle))
        if root.name == self.metadata["initial_slot"]:
            head = self.connection.execute(
                "SELECT manifest_hash FROM integration_heads "
                "WHERE project_id=?",
                (self.target["project_id"],),
            ).fetchone()
            if head and head[0] is not None:
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            if identity != self.metadata["initial_identity"]:
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
        else:
            self._known_slot(root, identity)
        return root

    def _known_slot(self, root: Path, identity: list) -> None:
        """@brief Resolves a physical slot against a trusted prepared intent.
        @param root Actual followed current physical generation.
        @param identity Independently observed native directory file ID.
        @return None.
        @details Imported raw intent objects alone cannot establish this event.
        Publication/recovery additionally resolves checks and authorization.
        """
        from partsmith.integration.policy import ResourcePolicy
        from partsmith.integration.store import IntegrationStore

        rows = self.connection.execute(
            "SELECT DISTINCT child.sha256 FROM integration_events e "
            "JOIN integration_attempts a ON a.id=e.attempt_id "
            "JOIN integration_object_refs r ON r.owner_hash=e.object_hash "
            "JOIN integration_objects child ON child.sha256=r.child_hash "
            "WHERE a.project_id=? AND e.state='PREPARED' "
            "AND child.kind='execution_intent' AND ("
            "EXISTS(SELECT 1 FROM integration_publications p "
            "JOIN integration_heads h ON h.project_id=a.project_id "
            "WHERE p.attempt_id=a.id AND p.manifest_hash=h.manifest_hash "
            "AND p.rowid=(SELECT max(p2.rowid) "
            "FROM integration_publications p2 JOIN integration_attempts a2 "
            "ON a2.id=p2.attempt_id WHERE a2.project_id=a.project_id)) "
            "OR (NOT EXISTS(SELECT 1 FROM integration_publications p "
            "WHERE p.attempt_id=a.id) AND e.sequence=(SELECT max(sequence) "
            "FROM integration_events WHERE attempt_id=a.id "
            "AND state='PREPARED') "
            "AND (SELECT state FROM integration_events WHERE attempt_id=a.id "
            "ORDER BY sequence DESC LIMIT 1) "
            "IN ('PREPARED','RECOVERY_REQUIRED'))) "
            "LIMIT 10001",
            (self.target["project_id"],),
        ).fetchall()
        ResourcePolicy().require_sizes([0] * len(rows))
        store = IntegrationStore(self.connection)
        for row in rows:
            intent = parse_json(store.get(row[0], "execution_intent"))
            if (
                intent.get("schema_version"),
                intent.get("owner"),
                intent.get("target"),
            ) != (
                "partsmith-publication-intent-1.0",
                self.metadata["owner"],
                self.target,
            ):
                continue
            if (
                intent.get("new_slot") == str(root)
                and intent.get("new_slot_identity") == identity
            ):
                return
        raise IntegrationError(FailureCode.TARGET_CONFLICT)

    def require_reconciled(self) -> None:
        """@brief Blocks planning and publication pending recovery.
        @return None.
        @details Explicit recovery must resolve the recorded old/new boundary
        before another action can use the trusted current generation head.
        """
        pending = self.connection.execute(
            "SELECT 1 FROM integration_attempts a WHERE a.project_id=? "
            "AND NOT EXISTS(SELECT 1 FROM integration_publications p "
            "WHERE p.attempt_id=a.id) AND "
            "(SELECT state FROM integration_events "
            "WHERE attempt_id=a.id ORDER BY sequence DESC LIMIT 1) "
            "IN ('PREPARED','RECOVERY_REQUIRED') LIMIT 1",
            (self.target["project_id"],),
        ).fetchone()
        if pending:
            raise IntegrationError(FailureCode.RECOVERY_REQUIRED)

    @contextmanager
    def lock(self, closed: ClosedProject):
        """@brief Exclusively locks one registered publication boundary.
        @param closed Fresh explicit caller writer-exclusion confirmation.
        @return Context-managed raw junction handle and selected old slot.
        @details The lock lives outside the junction. Windows sharing denies
        concurrent publishers and replacement of the selected reparse object.
        """
        closed.require(self.target)
        self._ownership()
        handle = self.api.kernel.CreateFileW(
            str(self.workspace / "lock.bin"), 0xC0000000, 0, None, 3, 0, None
        )
        if handle == ctypes.c_void_p(-1).value:
            raise IntegrationError(FailureCode.TARGET_CONFLICT, action="lock")
        try:
            if (
                list(self.api.identity(handle))
                != self.metadata["lock_identity"]
            ):
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            with self.api.directory(
                self.link, reparse=True, write=True, share=3
            ) as raw:
                current = self.current()
                yield raw, current
        finally:
            self.api.kernel.CloseHandle(handle)

    @contextmanager
    def freeze_files(self, root: Path, objects: dict):
        """@brief Denies concurrent writes/deletion to existing project files.
        @param root Verified current owned physical generation.
        @param objects Complete just-rechecked file inventory.
        @return Context-managed native file handles retaining exact content.
        @details External creation/editing is additionally excluded by the
        declared closed/exclusive managed-project policy and base rechecks.
        """
        with ExitStack() as stack:
            for name in sorted(objects):
                handle = self.api.kernel.CreateFileW(
                    str(root / name),
                    0x80000000,
                    1,
                    None,
                    3,
                    0x00200000,
                    None,
                )
                if handle == ctypes.c_void_p(-1).value:
                    raise IntegrationError(
                        FailureCode.TARGET_CONFLICT, action="freeze-project"
                    )
                stack.callback(self.api.kernel.CloseHandle, handle)
            yield


def registered_root(
    connection: sqlite3.Connection, target: dict
) -> Path | None:
    """@brief Resolves a trusted ordinary fixture or owned physical root.
    @param connection Authoritative current integration database.
    @param target Independently selected exact logical identity.
    @return Current registered physical root, or None before registration.
    @details Production ownership schema requires all native target checks.
    Ordinary synthetic planner fixtures retain their original test scope.
    """
    row = connection.execute(
        "SELECT root, ownership_bytes FROM integration_targets "
        "WHERE project_id=?",
        (target["project_id"],),
    ).fetchone()
    if row is None:
        return None
    metadata = parse_json(bytes(row["ownership_bytes"]))
    if metadata.get("schema_version") == "partsmith-owned-target-1.0":
        owned = OwnedTarget(connection, target)
        owned.require_reconciled()
        return owned.current()
    return Path(row["root"])
