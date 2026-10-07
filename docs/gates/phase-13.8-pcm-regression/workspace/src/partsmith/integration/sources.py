"""@package partsmith.integration.sources
@brief Resolves complete approved releases from the trusted component store.
@details Imported audit text and unfinished session archives are not authority.
"""

import sqlite3
from dataclasses import dataclass
from hashlib import sha256

from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence.release import ReleaseStore
from partsmith.release.contracts import ApprovalBinding


class SourceCatalog:
    """@brief Resolves sources across explicitly selected component stores.
    @details These caller-owned connections are separate from installation
    authority. Duplicate copies must resolve to identical approved bytes.
    """

    def __init__(self, connections: tuple[sqlite3.Connection, ...]):
        """@brief Binds trusted validated component connections.
        @param connections Explicitly selected component session databases.
        @return None.
        @details Construction grants no installation authority.
        """
        ResourcePolicy().require_sizes([0] * len(connections))
        self.connections = connections

    def matches(self, build_id: str) -> tuple[sqlite3.Connection, ...]:
        """@brief Locates bounded candidate stores for an exact build.
        @param build_id Desired approved release identity.
        @return Connections containing that build, in caller order.
        @details Fetches no artifact blobs while locating candidates.
        """
        matches = tuple(
            c
            for c in self.connections
            if c.execute(
                "SELECT 1 FROM builds WHERE id=?", (build_id,)
            ).fetchone()
        )
        if not matches:
            raise IntegrationError(FailureCode.MISSING_SOURCE)
        return matches


@dataclass(frozen=True)
class ApprovedSource:
    """@brief Retains exact approved engineering and historical decision bytes.
    @details The immutable tuple preserves artifact roles, paths and bytes.
    """

    component_id: str
    revision_id: str
    manifest_bytes: bytes
    approval_bytes: bytes
    artifacts: tuple[tuple[str, str, bytes], ...]

    def binding(self) -> dict:
        """@brief Returns deterministic plan source bindings.
        @return Exact component, release, historical approval and file hashes.
        @details Historical approval supplies no integration authority.
        """
        return {
            "component_id": self.component_id,
            "revision_id": self.revision_id,
            "release_manifest_hash": sha256(self.manifest_bytes).hexdigest(),
            "release_approval_hash": sha256(self.approval_bytes).hexdigest(),
            "artifacts": [
                {
                    "role": role,
                    "path": path,
                    "sha256": sha256(blob).hexdigest(),
                    "byte_length": len(blob),
                }
                for role, path, blob in self.artifacts
            ],
        }


def _require_inventory_sizes(
    connection: sqlite3.Connection | SourceCatalog, build_id: str
) -> list[int]:
    """@brief Bounds source content before loading its blobs into memory.
    @param connection Trusted component database or selected source catalog.
    @param build_id Requested complete release identity.
    @return Verified content sizes for cumulative multi-source limits.
    @details Applies cumulative limits to artifacts and verification objects.
    """
    if isinstance(connection, SourceCatalog):
        sizes = [
            size
            for c in connection.matches(build_id)
            for size in _require_inventory_sizes(c, build_id)
        ]
        ResourcePolicy().require_sizes(sizes)
        return sizes
    sizes = []
    for table, column in (
        ("build_snapshots", "canonical_bytes"),
        ("engineering_manifests", "canonical_bytes"),
        ("artifacts", "content"),
        ("validation_results", "canonical_bytes"),
        ("post_manifest_reports", "canonical_bytes"),
        ("approval_bindings", "canonical_bytes"),
        ("release_decisions", "canonical_bytes"),
    ):
        sizes.extend(
            row[0]
            for row in connection.execute(
                f"SELECT length({column}) FROM {table} "
                "WHERE build_id = ? LIMIT 10001",
                (build_id,),
            )
        )
    ResourcePolicy().require_sizes(sizes)
    return sizes


def resolve_approved_source(
    connection: sqlite3.Connection | SourceCatalog, build_id: str
) -> ApprovedSource:
    """@brief Verifies and resolves one complete trusted approved release.
    @param connection Trusted component database or selected source catalog.
    @param build_id Exact release build to resolve.
    @return Frozen source bytes and historical approval bindings.
    @details No mutation, import, regeneration or hydration is performed.
    Revision-only and unfinished sources fail before any installation work.
    """
    if isinstance(connection, SourceCatalog):
        _require_inventory_sizes(connection, build_id)
        sources = [
            resolve_approved_source(c, build_id)
            for c in connection.matches(build_id)
        ]
        if any(s != sources[0] for s in sources[1:]):
            raise IntegrationError(FailureCode.TAMPERED_SOURCE)
        return sources[0]
    build = connection.execute(
        "SELECT * FROM builds WHERE id = ?", (build_id,)
    ).fetchone()
    if build is None:
        raise IntegrationError(FailureCode.MISSING_SOURCE)
    if build["state"] not in {"APPROVED", "EXPORTED"}:
        raise IntegrationError(FailureCode.UNAPPROVED_SOURCE)
    _require_inventory_sizes(connection, build_id)
    row = connection.execute(
        "SELECT a.canonical_bytes, a.canonical_sha256, "
        "d.canonical_bytes AS decision_bytes, d.decision, d.build_id, "
        "d.id AS decision_id, d.actor, d.reason, d.binding_sha256 "
        "FROM approval_bindings a "
        "JOIN release_decisions d ON d.id = a.release_decision_id "
        "WHERE a.build_id = ?",
        (build_id,),
    ).fetchone()
    if row is None or row["decision"] != "APPROVE":
        raise IntegrationError(FailureCode.UNAPPROVED_SOURCE)
    try:
        binding_blob = bytes(row["canonical_bytes"])
        decision_blob = bytes(row["decision_bytes"])
        ResourcePolicy().require_sizes([len(binding_blob), len(decision_blob)])
        if sha256(binding_blob).hexdigest() != row["canonical_sha256"]:
            raise ValueError("Approval content mismatch")
        binding = parse_json(binding_blob)
        decision = parse_json(decision_blob)
        if (
            canonical_json(decision) != decision_blob
            or set(decision)
            != {
                "schema_version",
                "decision_id",
                "build_id",
                "decision",
                "actor",
                "reason",
                "binding",
            }
            or decision["schema_version"] != "1.0"
            or decision["decision_id"] != row["decision_id"]
            or decision["actor"] != row["actor"]
            or decision["reason"] != row["reason"]
            or row["binding_sha256"] != row["canonical_sha256"]
            or decision["build_id"] != build_id
            or decision["decision"] != "APPROVE"
            or decision["binding"] != binding
            or row["build_id"] != build_id
        ):
            raise ValueError("Approval identity mismatch")
        store = ReleaseStore(connection)
        store.verify_approval_binding(
            build_id,
            ApprovalBinding(
                binding["input_snapshot_hash"],
                binding["engineering_manifest_hash"],
                binding["validation_semantics_hash"],
                tuple(binding["artifact_hashes"]),
                tuple(binding["post_manifest_report_hashes"]),
            ),
            allow_approved=True,
        )
        manifest = connection.execute(
            "SELECT canonical_bytes FROM engineering_manifests "
            "WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        revision = connection.execute(
            "SELECT r.id FROM ir_revisions r JOIN build_snapshots s "
            "ON s.ir_record_hash = r.canonical_sha256 "
            "WHERE s.build_id = ?",
            (build_id,),
        ).fetchone()
        if revision is None:
            raise ValueError("Approved source revision missing")
        artifacts = store._final_artifacts(build_id)
        objects = tuple(
            (role, item["logical_path"], bytes(item["content"]))
            for role, item in sorted(artifacts.items())
        )
        manifest_blob = bytes(manifest[0])
        ResourcePolicy().require_sizes(
            [len(manifest_blob), len(decision_blob)]
            + [len(blob) for _, _, blob in objects]
        )
        return ApprovedSource(
            build["component_id"],
            revision[0],
            manifest_blob,
            decision_blob,
            objects,
        )
    except IntegrationError:
        raise
    except (KeyError, ValueError, RuntimeError, TypeError) as error:
        raise IntegrationError(FailureCode.TAMPERED_SOURCE) from error


def verify_source_bindings(
    expected: list[dict], sources: tuple[ApprovedSource, ...]
) -> None:
    """@brief Matches planned declarations to trusted resolved source bytes.
    @param expected Exact ordered source bindings from a frozen plan.
    @param sources Sources resolved from the authoritative release store.
    @return None.
    @details Missing, extra or changed source/approval hashes fail; historical
    approvals do not authenticate a new integration authorization.
    """
    bindings = sorted(
        (source.binding() for source in sources),
        key=lambda binding: binding["component_id"],
    )
    if len({s.component_id for s in sources}) != len(sources):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    if expected != bindings:
        raise IntegrationError(FailureCode.TAMPERED_SOURCE)
