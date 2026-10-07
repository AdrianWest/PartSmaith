"""@package partsmith.integration.planner
@brief Freezes approved-source dry runs against exact project inventories.
@details Planning never writes a database, target, table or component state.
Publication requires a separately registered owned target and fresh review.
"""

import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

from partsmith.integration.bindings import verify_files
from partsmith.integration.contracts import (
    REQUIRED_RULES,
    InstallationManifest,
    IntegrationPlan,
    _paths,
    portable_path,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.sexpr import children, table_entries
from partsmith.integration.sources import (
    ApprovedSource,
    _require_inventory_sizes,
    resolve_approved_source,
)
from partsmith.integration.store import IntegrationStore
from partsmith.ir.canonical import canonical_json, parse_json

TABLES = {"sym-lib-table": "sym_lib_table", "fp-lib-table": "fp_lib_table"}
OWNED_NAMES = {
    "sym-lib-table": "BFT_Symbols",
    "fp-lib-table": "BFT_Footprints",
}
MANAGED_ROOTS = {
    "BFT_Symbols.kicad_sym",
    "BFT_Footprints.pretty",
    "BFT_3DSTEP",
}


def file_inventory(objects: dict[str, bytes]) -> list[dict]:
    """@brief Computes exact sorted file identities without semantic changes.
    @param objects Portable relative path to exact byte mapping.
    @return Complete path, SHA-256 and byte-length records.
    @details Bounds cumulative bytes and rejects path/case aliases first.
    """
    _paths(list(objects))
    ResourcePolicy().require_sizes([len(blob) for blob in objects.values()])
    return [
        {
            "path": name,
            "sha256": sha256(blob).hexdigest(),
            "byte_length": len(blob),
        }
        for name, blob in sorted(objects.items())
    ]


def read_project(root: Path) -> tuple[dict[str, bytes], tuple[str, ...]]:
    """@brief Reads a bounded ordinary project root without following reparses.
    @param root Explicit physical project directory.
    @return Detached file bytes and sorted directory names.
    @details Owned publication adapters must resolve their junction themselves.
    Changing files, unsafe aliases and nested links fail before copying.
    """
    root = root.absolute()
    initial = root.lstat()
    if (
        not stat.S_ISDIR(initial.st_mode)
        or (getattr(initial, "st_file_attributes", 0) & 0x400)
        or root.is_symlink()
    ):
        raise IntegrationError(FailureCode.PATH_CONFLICT)
    objects, directories, sizes = {}, [], []
    policy = ResourcePolicy()

    def visit(folder: Path, depth: int) -> None:
        """@brief Traverses one bounded, reparse-free physical directory.
        @param folder Current physical directory.
        @param depth Current directory nesting depth.
        @return None.
        @details Checks identities and limits before reading each file.
        """
        if depth > 64:
            raise IntegrationError(FailureCode.RESOURCE_LIMIT)
        with os.scandir(folder) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                path = Path(entry.path)
                name = path.relative_to(root).as_posix()
                try:
                    portable_path(name)
                except ValueError as error:
                    raise IntegrationError(
                        FailureCode.PATH_CONFLICT
                    ) from error
                before = path.lstat()
                if entry.is_symlink() or (
                    getattr(before, "st_file_attributes", 0) & 0x400
                ):
                    raise IntegrationError(FailureCode.PATH_CONFLICT)
                if stat.S_ISDIR(before.st_mode):
                    directories.append(name)
                    if len(directories) > policy.object_count:
                        raise IntegrationError(FailureCode.RESOURCE_LIMIT)
                    visit(path, depth + 1)
                elif stat.S_ISREG(before.st_mode):
                    sizes.append(before.st_size)
                    policy.require_sizes(sizes)
                    with path.open("rb") as source:
                        blob = source.read(before.st_size + 1)
                        after = os.fstat(source.fileno())
                    final = path.lstat()
                    identity = (
                        before.st_dev,
                        before.st_ino,
                        before.st_size,
                        before.st_mtime_ns,
                    )
                    if len(blob) != before.st_size or any(
                        (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
                        != identity
                        for s in (after, final)
                    ):
                        raise IntegrationError(FailureCode.STALE_BASE)
                    objects[name] = blob
                else:
                    raise IntegrationError(FailureCode.PATH_CONFLICT)

    visit(root, 0)
    try:
        _paths(list(objects) + [name + "/.directory" for name in directories])
    except ValueError as error:
        raise IntegrationError(FailureCode.PATH_CONFLICT) from error
    final = root.lstat()
    if (initial.st_dev, initial.st_ino) != (final.st_dev, final.st_ino):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    return objects, tuple(sorted(directories))


@dataclass(frozen=True)
class TargetSnapshot:
    """@brief Retains whole-project bytes separately from managed base content.
    @details Root paths are operational and excluded from canonical plans.
    Mutable board/project bytes are preserved by later complete-slot copying.
    """

    root: Path
    target_bytes: bytes
    objects: tuple[tuple[str, bytes], ...]
    directories: tuple[str, ...]
    manifest: InstallationManifest | None

    @property
    def target(self) -> dict:
        """@brief Returns detached portable target identity.
        @return Project, library and project-local scope mapping.
        @details The root path is never included in this contract identity.
        """
        return parse_json(self.target_bytes)

    @property
    def document(self) -> dict:
        """@brief Returns the versioned whole-target operational snapshot.
        @return Closed snapshot with complete file/directory inventory.
        @details Hashes support stale-project checks without authority.
        """
        return {
            "schema_version": "partsmith-target-snapshot-1.0",
            "target": self.target,
            "generation_hash": self.manifest.sha256 if self.manifest else None,
            "files": file_inventory(dict(self.objects)),
            "directories": list(self.directories),
        }

    def base(self, proposed: set[str]) -> dict:
        """@brief Binds all managed files/tables and intended path absences.
        @param proposed Complete intended managed paths.
        @return Exact schema-version-1.0 expected base.
        @details Whole-project mutable data stays in the separate snapshot.
        """
        objects = dict(self.objects)
        names = proposed | (set(objects) & TABLES.keys())
        if self.manifest:
            names |= {entry["path"] for entry in self.manifest.data["files"]}
        head = self.manifest.sha256 if self.manifest else None
        return {
            "generation_hash": head,
            "manifest_hash": head,
            "files": [
                {
                    "path": name,
                    "sha256": sha256(objects[name]).hexdigest()
                    if name in objects
                    else None,
                    "byte_length": len(objects[name])
                    if name in objects
                    else None,
                }
                for name in sorted(names)
            ],
        }

    def recheck(self) -> None:
        """@brief Rejects any whole-project edit after this snapshot.
        @return None.
        @details Does not overwrite files or refresh the frozen base silently.
        """
        objects, directories = read_project(self.root)
        if objects != dict(self.objects) or directories != self.directories:
            raise IntegrationError(FailureCode.STALE_BASE)


def snapshot_target(
    root: Path, target: dict, manifest: InstallationManifest | None
) -> TargetSnapshot:
    """@brief Verifies owned namespace and exact previously installed content.
    @param root Explicit physical project directory.
    @param target Portable target identity.
    @param manifest Trusted current head, resolved by the application store.
    @return Frozen complete target snapshot.
    @details Unmanaged BFT paths/nicknames and changed installed bytes fail.
    Global table mutation is never included in this project-local scope.
    """
    if set(target) != {"project_id", "library_id", "scope"} or (
        target["scope"] != "project-local"
    ):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    objects, directories = read_project(root)
    declared = set()
    if manifest:
        if manifest.data["target"] != target:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        declared = {entry["path"] for entry in manifest.data["files"]}
        try:
            verify_files(
                manifest.data["files"],
                {name: objects[name] for name in declared if name in objects},
            )
        except IntegrationError as error:
            raise IntegrationError(FailureCode.STALE_BASE) from error
    if not manifest and any(
        directory.split("/")[0].casefold()
        in {value.casefold() for value in MANAGED_ROOTS}
        for directory in directories
    ):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    for name in objects:
        if name.casefold() in TABLES and name not in TABLES:
            raise IntegrationError(FailureCode.PATH_CONFLICT)
        if (
            name.split("/")[0].casefold()
            in {value.casefold() for value in MANAGED_ROOTS}
            and name not in declared
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
    for name, kind in TABLES.items():
        if name not in objects:
            continue
        try:
            entries = table_entries(objects[name], kind)
        except ValueError as error:
            raise IntegrationError(FailureCode.NAMESPACE_CONFLICT) from error
        for nickname, entry in entries.items():
            if nickname.casefold() == OWNED_NAMES[name].casefold() and (
                manifest is None or name not in declared
            ):
                raise IntegrationError(FailureCode.NAMESPACE_CONFLICT)
            uri = children(entry, "uri")[0][1].replace("\\", "/")
            relative = uri.removeprefix("${KIPRJMOD}/")
            if nickname != OWNED_NAMES[name] and relative.split("/")[
                0
            ].casefold() in {value.casefold() for value in MANAGED_ROOTS}:
                raise IntegrationError(FailureCode.NAMESPACE_CONFLICT)
    return TargetSnapshot(
        root.absolute(),
        canonical_json(target),
        tuple(sorted(objects.items())),
        directories,
        manifest,
    )


def source_mapping(source: ApprovedSource) -> dict:
    """@brief Allocates stable portable names from immutable component IDs.
    @param source Complete verified approved source.
    @return Project-local symbol, footprint and model mapping.
    @details Entry identity survives revision updates and relocation.
    """
    if not re.fullmatch(
        r"[A-Za-z0-9_][A-Za-z0-9_-]{0,127}", source.component_id
    ):
        raise IntegrationError(FailureCode.PATH_CONFLICT)
    name = "P_" + source.component_id.replace("-", "_")
    return {
        "component_id": source.component_id,
        "symbol_nickname": "BFT_Symbols",
        "symbol_name": name,
        "symbol_path": "BFT_Symbols.kicad_sym",
        "footprint_nickname": "BFT_Footprints",
        "footprint_name": name,
        "footprint_path": f"BFT_Footprints.pretty/{name}.kicad_mod",
        "model_path": f"BFT_3DSTEP/{name}.step",
    }


@dataclass(frozen=True)
class PlanningResult:
    """@brief Retains a frozen plan, verified sources and target snapshot.
    @details An exact no-op resolves the existing generation without staging
    or duplicating installation approval.
    """

    plan: IntegrationPlan
    snapshot: TargetSnapshot
    sources: tuple[ApprovedSource, ...]
    no_op: bool

    def dry_run(self) -> dict:
        """@brief Returns deterministic review information without persistence.
        @return Frozen plan fields, identity, no-op and snapshot hash.
        @details Does not alter target bytes, approvals, heads or BuildState.
        """
        return {
            "plan": self.plan.data,
            "plan_hash": self.plan.sha256,
            "no_op": self.no_op,
            "snapshot_hash": sha256(
                canonical_json(self.snapshot.document)
            ).hexdigest(),
        }


class Planner:
    """@brief Resolves trusted approved releases before producing a dry run.
    @details Complete source sets make retention and removal explicit.
    """

    def __init__(self, connection: sqlite3.Connection, source_connection=None):
        """@brief Binds read-only planning to the trusted application database.
        @param connection Migrated authoritative component/integration store.
        @param source_connection Separate trusted component source catalog.
        @return None.
        @details Construction creates no records or transactions.
        """
        self.connection = connection
        self.source_connection = source_connection or connection
        self.store = IntegrationStore(connection)

    def plan(
        self, root: Path, target: dict, build_ids: tuple[str, ...]
    ) -> PlanningResult:
        """@brief Freezes the desired installation against the exact base.
        @param root Explicit physical project root to inspect.
        @param target Project/library/scope identity.
        @param build_ids Exact complete desired approved release build IDs.
        @return Frozen deterministic dry-run result and verified source bytes.
        @details Refuses duplicates, unmanaged collisions and changed heads;
        no target file, table, approval or database record is written.
        """
        if (
            not isinstance(target, dict)
            or set(target) != {"project_id", "library_id", "scope"}
            or target.get("scope") != "project-local"
            or any(
                not isinstance(target[key], str)
                or not 0 < len(target[key]) <= 1024
                for key in ("project_id", "library_id")
            )
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if not isinstance(build_ids, tuple | list) or any(
            not isinstance(build, str) or not 0 < len(build) <= 1024
            for build in build_ids
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        policy = ResourcePolicy()
        policy.require_sizes([0] * len(build_ids))
        sizes = []
        for build in build_ids:
            sizes.extend(
                _require_inventory_sizes(self.source_connection, build)
            )
            policy.require_sizes(sizes)
        sources = tuple(
            sorted(
                (
                    resolve_approved_source(self.source_connection, build)
                    for build in build_ids
                ),
                key=lambda source: source.component_id,
            )
        )
        if len({s.component_id.casefold() for s in sources}) != len(sources):
            raise IntegrationError(FailureCode.NAMESPACE_CONFLICT)
        from partsmith.integration.target import registered_root

        registered = registered_root(self.connection, target)
        if registered and registered.absolute() != root.absolute():
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        head = self.store.head(target)
        snapshot = snapshot_target(root, target, head)
        mappings = [source_mapping(source) for source in sources]
        bindings = [source.binding() for source in sources]
        versions = {
            "adapter": "1.0",
            "serializer": "1.0",
            "comparator": "1.0",
            "kicad": "10.0.6",
            "runtime_lock_hash": sha256(
                files("partsmith.release")
                .joinpath("runtime-lock-1.0.json")
                .read_bytes()
            ).hexdigest(),
        }
        old = head.data if head else {"sources": [], "mappings": []}
        no_op = bool(
            head
            and old["sources"] == bindings
            and (old["mappings"] == mappings and old["versions"] == versions)
        )
        old_sources = {s["component_id"]: s for s in old["sources"]}
        old_mappings = {m["component_id"]: m for m in old["mappings"]}
        retained = {s.component_id for s in sources}
        removals = sorted(set(old_sources) - retained)
        proposed = set(TABLES)
        if sources:
            proposed.add("BFT_Symbols.kicad_sym")
        proposed.update(
            m[key]
            for m in mappings
            for key in ("footprint_path", "model_path")
        )
        base = snapshot.base(proposed)
        previous = {f["path"]: f for f in base["files"]}
        operations = {}

        def operation(path: str, kind: str, basis: list[str], delete=False):
            """@brief Adds one deterministic intended file operation.
            @param path Portable target-relative file.
            @param kind Closed semantic file role.
            @param basis Exact affected components or preserved table basis.
            @param delete Whether to remove the existing owned file.
            @return None.
            @details Does not render content or change the target.
            """
            operations[path] = {
                "path": path,
                "kind": kind,
                "basis": sorted(set(basis)),
                "action": "DELETE"
                if delete
                else (
                    "CREATE" if previous[path]["sha256"] is None else "MODIFY"
                ),
            }

        if not no_op:
            for source, mapping in zip(sources, mappings, strict=True):
                original = old_sources.get(source.component_id)
                old_mapping = old_mappings.get(source.component_id)
                for role, key, kind in (
                    ("footprint", "footprint_path", "FOOTPRINT"),
                    ("model_3d", "model_path", "MODEL_3D"),
                ):
                    artifact = next(
                        a
                        for a in source.binding()["artifacts"]
                        if a["role"] == role
                    )
                    prior = (
                        next(
                            (
                                a
                                for a in original["artifacts"]
                                if a["role"] == role
                            ),
                            None,
                        )
                        if original
                        else None
                    )
                    if prior != artifact or old_mapping != mapping:
                        operation(mapping[key], kind, [source.component_id])
            if sources:
                operation(
                    "BFT_Symbols.kicad_sym",
                    "SYMBOL_LIBRARY",
                    sorted(retained | set(removals)),
                )
            for component_id in removals:
                mapping = old_mappings[component_id]
                for key, kind in (
                    ("footprint_path", "FOOTPRINT"),
                    ("model_path", "MODEL_3D"),
                ):
                    operation(mapping[key], kind, [component_id], True)
            if not sources and head:
                operation(
                    "BFT_Symbols.kicad_sym", "SYMBOL_LIBRARY", removals, True
                )
            if head is None or bool(sources) != bool(old["sources"]):
                for path, kind in (
                    ("sym-lib-table", "SYMBOL_TABLE"),
                    ("fp-lib-table", "FOOTPRINT_TABLE"),
                ):
                    operation(
                        path,
                        kind,
                        sorted(retained | set(removals)) + ["PRESERVED_TABLE"],
                    )
        plan = IntegrationPlan(
            {
                "schema_version": "1.0",
                "canonical_profile": "1.0",
                "resource_policy": "1.0",
                "target": target,
                "expected_base": base,
                "versions": versions,
                "sources": bindings,
                "mappings": mappings,
                "removals": removals,
                "operations": [
                    operations[name] for name in sorted(operations)
                ],
                "required_rules": list(REQUIRED_RULES),
            }
        )
        return PlanningResult(plan, snapshot, sources, no_op)
