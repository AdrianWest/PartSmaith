"""@package partsmith.integration.contracts
@brief Defines immutable, canonical version 1.0 integration documents.
@details Deterministic objects exclude actor, time, local roots and IPC data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any, ClassVar

from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.schema import validate_shape
from partsmith.ir.canonical import canonical_json, parse_json

REQUIRED_RULES = (
    "MAPPING",
    "NATIVE_PARSE",
    "PATH_RESOLUTION",
    "SEMANTIC_PRESERVATION",
)
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{number}"
    for prefix in ("COM", "LPT")
    for number in (*range(1, 10), "¹", "²", "³")
}


def portable_path(value: str) -> str:
    """@brief Validates a normalized portable target-relative path.
    @param value Declared path spelling.
    @return The unchanged safe path.
    @details Rejects Windows aliases, traversal, controls and digest cycles.
    Filesystem reparse resolution remains a separate adapter check.
    """
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or str(path) != value
        or unicodedata.normalize("NFC", value) != value
        or any(character in value for character in '\\:<>"|?*')
        or any(unicodedata.category(character) == "Cc" for character in value)
        or any(
            part in {".", ".."}
            or part.endswith((".", " "))
            or part.split(".")[0].rstrip(" ").upper() in _RESERVED
            for part in path.parts
        )
        or re.search(r"[0-9a-fA-F]{64}", value)
    ):
        raise ValueError("Unsafe or cyclic integration path")
    return value


def _paths(paths: list[str]) -> None:
    """@brief Checks file and directory spelling across a path inventory.
    @param paths Unique portable relative file paths.
    @return None.
    @details Rejects aliases in directory components and files used as parents.
    """
    spellings = {}
    files = set(paths)
    for value in paths:
        path = PurePosixPath(portable_path(value))
        for index in range(1, len(path.parts) + 1):
            prefix = "/".join(path.parts[:index])
            alias = prefix.casefold()
            if alias in spellings and spellings[alias] != prefix:
                raise ValueError("Integration file or directory aliases")
            spellings[alias] = prefix
            if index < len(path.parts) and prefix in files:
                raise ValueError("Integration file also used as a directory")


def _ordered(values: list, key: str | None = None) -> None:
    """@brief Requires sorted unique identities without case/Unicode aliases.
    @param values Declared ordered array.
    @param key Optional object field identifying each entry.
    @return None.
    @details Identical or aliased entries fail instead of being deduplicated.
    """
    names = [value[key] if key else value for value in values]
    aliases = [unicodedata.normalize("NFC", name).casefold() for name in names]
    if names != sorted(names) or len(set(aliases)) != len(names):
        raise ValueError("Integration identities must be sorted and unique")


def _base(data: dict) -> None:
    """@brief Checks paired generation identity and exact base inventory.
    @param data Expected base content.
    @return None.
    @details Generation equals manifest identity; absence uses paired nulls.
    """
    if data["generation_hash"] != data["manifest_hash"]:
        raise ValueError("Base generation must equal its manifest identity")
    _ordered(data["files"], "path")
    _paths([entry["path"] for entry in data["files"]])
    sizes = []
    for entry in data["files"]:
        if (entry["sha256"] is None) != (entry["byte_length"] is None):
            raise ValueError("Expected absence requires paired nulls")
        sizes.append(int(entry["byte_length"] or 0))
    ResourcePolicy().require_sizes(sizes)


def _files(files: list[dict]) -> None:
    """@brief Checks final path inventory ordering and cumulative limits.
    @param files Declared final file inventory.
    @return None.
    @details Case aliases and expanded-data overflow are rejected.
    """
    _ordered(files, "path")
    _paths([entry["path"] for entry in files])
    ResourcePolicy().require_sizes([int(e["byte_length"]) for e in files])


def _sources(sources: list[dict]) -> None:
    """@brief Requires one complete three-artifact source per component.
    @param sources Ordered source-component bindings.
    @return None.
    @details A hash declaration does not prove release approval or existence.
    """
    _ordered(sources, "component_id")
    sizes = []
    for source in sources:
        artifacts = source["artifacts"]
        _ordered(artifacts, "role")
        if [a["role"] for a in artifacts] != [
            "footprint",
            "model_3d",
            "symbol",
        ]:
            raise ValueError("Source requires all three final artifacts")
        _ordered(sorted(artifacts, key=lambda a: a["path"]), "path")
        _paths([artifact["path"] for artifact in artifacts])
        for artifact in artifacts:
            sizes.append(int(artifact["byte_length"]))
    ResourcePolicy().require_sizes(sizes)


def _mappings(data: dict) -> None:
    """@brief Checks component coverage, namespaces and relocation inventory.
    @param data Document containing source and mapping arrays.
    @return None.
    @details Packed symbol paths may be shared; entry names cannot collide.
    """
    mappings = data["mappings"]
    _ordered(mappings, "component_id")
    if [m["component_id"] for m in mappings] != [
        s["component_id"] for s in data["sources"]
    ]:
        raise ValueError("Mappings must cover the exact source set")
    for field in ("symbol", "footprint"):
        names = []
        for mapping in mappings:
            nickname = mapping[f"{field}_nickname"]
            name = mapping[f"{field}_name"]
            if any(c in nickname + name for c in ':\\/"') or any(
                unicodedata.category(c) == "Cc" for c in nickname + name
            ):
                raise ValueError("Invalid library nickname or entry name")
            names.append(f"{nickname}:{name}")
        _ordered(sorted(names))
    for field in ("symbol_path", "footprint_path", "model_path"):
        paths = [portable_path(m[field]) for m in mappings]
        if field != "symbol_path":
            _ordered(sorted(paths))
    all_paths = [
        m[field]
        for m in mappings
        for field in ("symbol_path", "footprint_path", "model_path")
    ]
    symbol_paths = {m["symbol_path"] for m in mappings}
    if len(all_paths) - len(mappings) + len(symbol_paths) != len(
        set(all_paths)
    ):
        raise ValueError("Mapped file roles collide")
    _paths(list(set(all_paths)))
    for field in ("symbol", "footprint"):
        namespace = {}
        for mapping in mappings:
            nickname = mapping[f"{field}_nickname"]
            location = mapping[f"{field}_path"]
            if field == "footprint":
                location = str(PurePosixPath(location).parent)
            alias = unicodedata.normalize("NFC", nickname).casefold()
            if alias in namespace and namespace[alias] != (nickname, location):
                raise ValueError("Nickname aliases or library paths collide")
            namespace[alias] = (nickname, location)


def _operation_basis(operation: dict, data: dict) -> None:
    """@brief Resolves intended operation roles against declared source basis.
    @param operation One intended file operation.
    @param data Integration plan document.
    @return None.
    @details Removed sources may justify deletion or packed-library updates;
    preserved table content cannot justify new engineering artifact paths.
    """
    retained = {s["component_id"] for s in data["sources"]}
    removed = set(data["removals"])
    basis = set(operation["basis"])
    if not basis <= retained | removed | {"PRESERVED_TABLE"}:
        raise ValueError("Operation lacks a declared source basis")
    kind = operation["kind"]
    if kind in {"SYMBOL_TABLE", "FOOTPRINT_TABLE"}:
        expected = (
            "sym-lib-table" if kind == "SYMBOL_TABLE" else "fp-lib-table"
        )
        if operation["path"] != expected:
            raise ValueError("Table operation has an invalid target path")
        return
    if "PRESERVED_TABLE" in basis:
        raise ValueError("Preserved table cannot justify an artifact")
    if operation["action"] == "DELETE":
        return
    field = {
        "SYMBOL_LIBRARY": "symbol_path",
        "FOOTPRINT": "footprint_path",
        "MODEL_3D": "model_path",
    }[kind]
    mapped = {
        m["component_id"]
        for m in data["mappings"]
        if m[field] == operation["path"]
    }
    allowed = mapped
    if kind == "SYMBOL_LIBRARY" and operation["action"] == "MODIFY":
        allowed = mapped | removed
    if not mapped or not mapped <= basis or not basis <= allowed:
        raise ValueError("Operation role and mapped source basis disagree")


def _checks(checks: list[dict]) -> None:
    """@brief Requires an exact nonempty required-rule hash inventory.
    @param checks Ordered deterministic check references.
    @return None.
    @details Unknown, duplicate or missing native/semantic rules fail.
    """
    _ordered(checks, "rule_id")
    if tuple(c["rule_id"] for c in checks) != REQUIRED_RULES:
        raise ValueError("Every required integration rule must be bound")


def _semantics(kind: str, data: dict) -> None:
    """@brief Enforces invariants not expressible by closed JSON shapes.
    @param kind Named integration contract.
    @param data Schema-valid normalized document.
    @return None.
    @details Cross-object byte resolution is deliberately a separate operation.
    """
    if "expected_base" in data:
        _base(data["expected_base"])
    if "sources" in data:
        _sources(data["sources"])
        _mappings(data)
    if "files" in data:
        _files(data["files"])
        required = {
            m[field]
            for m in data["mappings"]
            for field in ("symbol_path", "footprint_path", "model_path")
        }
        if not required <= {entry["path"] for entry in data["files"]}:
            raise ValueError("Final inventory omits mapped source artifacts")
    if "required_checks" in data:
        _checks(data["required_checks"])
    if kind == "installation_manifest" and data[
        "semantic_validation_hash"
    ] != next(
        c["report_hash"]
        for c in data["required_checks"]
        if c["rule_id"] == "SEMANTIC_PRESERVATION"
    ):
        raise ValueError("Semantic validation identity disagrees with checks")
    if kind == "integration_plan":
        if tuple(data["required_rules"]) != REQUIRED_RULES:
            raise ValueError("Plan must declare every required rule")
        _ordered(data["removals"])
        source_ids = {s["component_id"] for s in data["sources"]}
        if source_ids.intersection(data["removals"]):
            raise ValueError("Retained source cannot also be removed")
        _ordered(data["operations"], "path")
        _paths([o["path"] for o in data["operations"]])
        base = {f["path"]: f for f in data["expected_base"]["files"]}
        for operation in data["operations"]:
            portable_path(operation["path"])
            _ordered(operation["basis"])
            _operation_basis(operation, data)
            previous = base.get(operation["path"])
            if previous is None or (
                (operation["action"] == "CREATE")
                != (previous["sha256"] is None)
            ):
                raise ValueError("Operation violates its base precondition")
    elif kind == "integration_validation_report":
        if (data["phase"] == "PRE_MANIFEST") != (
            data["manifest_hash"] is None
        ):
            raise ValueError("Validation hash dependency order is invalid")
        _ordered(data["results"], "rule_id")
        if tuple(r["rule_id"] for r in data["results"]) != REQUIRED_RULES:
            raise ValueError("Validation must include every required rule")
        for result in data["results"]:
            _ordered(result["measurements"], "name")
            if (result["applicability"] == "NOT_APPLICABLE") != (
                result["status"] is None
            ):
                raise ValueError("Rule applicability and status disagree")
    elif kind == "integration_journal":
        if data["new_generation_hash"] != data["new_manifest_hash"]:
            raise ValueError("Generation must identify the complete manifest")
    elif kind == "integration_audit_envelope":
        datetime.fromisoformat(data["timestamp"])
        _ordered(data["references"]["check_hashes"])
        if data["decision"] == "APPROVE" and (
            data["outcome"] != "AUTHORIZED"
            or data["references"]["authorization_hash"] is None
            or data["references"]["manifest_hash"] is None
        ):
            raise ValueError("Approval audit lacks exact authorization")
        if (data["decision"] == "REJECT") != (data["outcome"] == "REJECTED"):
            raise ValueError("Rejection decision and outcome disagree")


@dataclass(frozen=True, init=False)
class CanonicalContract:
    """@brief Stores an integration contract as immutable canonical bytes.
    @details Construction validates both shape and within-object invariants.
    """

    _bytes: bytes
    kind: ClassVar[str]

    def __init__(self, data: dict[str, Any]):
        """@brief Freezes a validated independent copy of a document.
        @param data Closed versioned document mapping.
        @return None.
        @details Invalid shapes fail before canonicalization; caller mutations
        and property mutations cannot alter the stored document.
        """
        try:
            validate_shape(self.kind, data)
            _semantics(self.kind, data)
            blob = canonical_json(data)
            ResourcePolicy().require_sizes([len(blob)])
            normalized = parse_json(blob)
            validate_shape(self.kind, normalized)
            _semantics(self.kind, normalized)
        except IntegrationError:
            raise
        except (ValueError, TypeError, OverflowError) as error:
            raise IntegrationError(FailureCode.INVALID_CONTRACT) from error
        object.__setattr__(self, "_bytes", blob)

    @property
    def canonical_bytes(self) -> bytes:
        """@brief Returns the immutable canonical profile 1.0 encoding.
        @return Exact UTF-8 canonical bytes without a trailing newline.
        @details The same deterministic input always yields the same bytes.
        """
        return self._bytes

    @property
    def sha256(self) -> str:
        """@brief Computes this object's external content identity.
        @return Lowercase SHA-256 digest.
        @details The identity is never embedded in its own document.
        """
        return sha256(self._bytes).hexdigest()

    @property
    def data(self) -> dict[str, Any]:
        """@brief Returns an independent JSON-compatible document copy.
        @return Parsed contract mapping with exact decimal values.
        @details Mutating the returned data does not mutate this object.
        """
        return parse_json(self._bytes)


@dataclass(frozen=True, init=False)
class IntegrationPlan(CanonicalContract):
    """@brief Freezes target, base, sources and intended aggregate operations.
    @details This contract grants no installation authority.
    """

    kind: ClassVar[str] = "integration_plan"


@dataclass(frozen=True, init=False)
class InstallationManifest(CanonicalContract):
    """@brief Identifies the complete final aggregate and required checks.
    @details Its external digest is the generation identity.
    """

    kind: ClassVar[str] = "installation_manifest"


@dataclass(frozen=True, init=False)
class IntegrationValidationReport(CanonicalContract):
    """@brief Retains deterministic staged semantic and native rule results.
    @details Run telemetry and post-manifest dependencies remain separate.
    """

    kind: ClassVar[str] = "integration_validation_report"


@dataclass(frozen=True, init=False)
class IntegrationAuthorizationBinding(CanonicalContract):
    """@brief Binds authorization to exact content, base and check identities.
    @details A binding alone is not an authenticated decision.
    """

    kind: ClassVar[str] = "integration_authorization_binding"


@dataclass(frozen=True, init=False)
class IntegrationAuditEnvelope(CanonicalContract):
    """@brief Retains immutable non-engineering operation and actor metadata.
    @details Its changing identity cannot affect plan or manifest hashes.
    """

    kind: ClassVar[str] = "integration_audit_envelope"


@dataclass(frozen=True, init=False)
class IntegrationJournal(CanonicalContract):
    """@brief Describes exact recoverable publication intent and state.
    @details Journals are operational evidence and cannot grant authority.
    """

    kind: ClassVar[str] = "integration_journal"
