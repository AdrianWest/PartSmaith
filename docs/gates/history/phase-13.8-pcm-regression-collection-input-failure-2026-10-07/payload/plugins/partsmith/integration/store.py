"""@package partsmith.integration.store
@brief Stores immutable integration objects and append-only history.
@details The migrated application database owns these records. Methods never
commit caller transactions; importing bytes cannot grant publication authority.
"""

import re
import sqlite3
from uuid import uuid4

from partsmith.integration.contracts import (
    CanonicalContract,
    InstallationManifest,
    IntegrationPlan,
    _files,
    _ordered,
    _paths,
    portable_path,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.ir.canonical import canonical_json
from partsmith.persistence.database import savepoint, utc_timestamp

KINDS = {
    "integration_plan",
    "installation_manifest",
    "integration_validation_report",
    "integration_authorization_binding",
    "integration_audit_envelope",
    "integration_journal",
    "artifact",
    "source_manifest",
    "source_approval",
    "target_snapshot",
    "execution_intent",
    "publication_receipt",
}
STATES = {
    "PLANNED",
    "STAGED",
    "AUTHORIZED",
    "REJECTED",
    "CANCELLED",
    "PREPARED",
    "COMMITTED",
    "FAILED",
    "RECOVERY_REQUIRED",
    "ROLLED_BACK",
}


def validate_snapshot(snapshot: dict, plan: IntegrationPlan) -> None:
    """@brief Verifies the closed whole-project snapshot/base binding.
    @param snapshot Versioned complete operational inventory.
    @param plan Frozen exact intended integration plan.
    @return None.
    @details Snapshot persistence grants no authority; malformed or mismatched
    inventory fails before opening a save transaction.
    """
    try:
        if not isinstance(snapshot, dict):
            raise ValueError("Snapshot mapping required")
        if (
            set(snapshot)
            != {
                "schema_version",
                "target",
                "generation_hash",
                "files",
                "directories",
            }
            or snapshot["schema_version"] != "partsmith-target-snapshot-1.0"
        ):
            raise ValueError("Snapshot shape")
        if snapshot["target"] != plan.data["target"]:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if (
            snapshot["generation_hash"]
            != (plan.data["expected_base"]["generation_hash"])
        ):
            raise IntegrationError(FailureCode.STALE_BASE)
        if not isinstance(snapshot["files"], list) or not isinstance(
            snapshot["directories"], list
        ):
            raise ValueError("Snapshot arrays required")
        for item in snapshot["files"]:
            if not isinstance(item, dict) or not isinstance(
                item.get("path"), str
            ):
                raise ValueError("Snapshot file path")
        if not all(isinstance(name, str) for name in snapshot["directories"]):
            raise ValueError("Snapshot directory path")
        ResourcePolicy().require_sizes([0] * len(snapshot["directories"]))
        _files(snapshot["files"])
        for item in snapshot["files"]:
            if set(item) != {"path", "sha256", "byte_length"} or not (
                isinstance(item["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            ):
                raise ValueError("Snapshot file identity")
        _ordered(snapshot["directories"])
        for directory in snapshot["directories"]:
            portable_path(directory)
        _paths(
            [item["path"] for item in snapshot["files"]]
            + [
                directory + "/.directory"
                for directory in snapshot["directories"]
            ]
        )
        actual = {item["path"]: item for item in snapshot["files"]}
        for item in plan.data["expected_base"]["files"]:
            if item["sha256"] is None:
                if item["path"] in actual:
                    raise IntegrationError(FailureCode.STALE_BASE)
            elif actual.get(item["path"]) != item:
                raise IntegrationError(FailureCode.STALE_BASE)
    except IntegrationError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise IntegrationError(FailureCode.INVALID_CONTRACT) from error


class IntegrationStore:
    """@brief Persists detached content identities and operational references.
    @details Reads are bounded before fetching content; authority lives only
    in a trusted decision service and its authenticated transaction.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Binds the store to a caller-owned migrated connection.
        @param connection Application database with migration 005 applied.
        @return None.
        @details Does not migrate, begin or commit during construction.
        """
        self.connection = connection

    def put(self, kind: str, blob: bytes) -> str:
        """@brief Inserts or verifies one exact immutable content object.
        @param kind Explicit closed object kind.
        @param blob Exact bytes to retain.
        @return External SHA-256 identity.
        @details The caller must commit. Equal bytes are idempotent; a kind or
        byte mismatch cannot replace an existing object.
        """
        from hashlib import sha256

        if (
            not isinstance(kind, str)
            or kind not in KINDS
            or not isinstance(blob, bytes)
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        ResourcePolicy().require_sizes([len(blob)])
        digest = sha256(blob).hexdigest()
        existing = self.connection.execute(
            "SELECT kind, length(content) FROM integration_objects "
            "WHERE sha256 = ?",
            (digest,),
        ).fetchone()
        if existing is not None:
            if existing["kind"] != kind or self.get(digest, kind) != blob:
                raise IntegrationError(FailureCode.TAMPERED_SOURCE)
            return digest
        self.connection.execute(
            "INSERT INTO integration_objects VALUES (?, ?, ?, ?)",
            (digest, kind, blob, utc_timestamp()),
        )
        return digest

    def get(self, digest: str, kind: str) -> bytes:
        """@brief Resolves a typed, bounded object and verifies exact content.
        @param digest Required external SHA-256 identity.
        @param kind Expected stored kind.
        @return Detached immutable bytes.
        @details Raw audit/authorization objects do not establish a decision.
        """
        from hashlib import sha256

        if (
            not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not isinstance(kind, str)
            or kind not in KINDS
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        row = self.connection.execute(
            "SELECT kind, length(content) AS size FROM integration_objects "
            "WHERE sha256 = ?",
            (digest,),
        ).fetchone()
        if row is None or row["kind"] != kind:
            raise IntegrationError(FailureCode.MISSING_SOURCE)
        ResourcePolicy().require_sizes([row["size"]])
        blob = bytes(
            self.connection.execute(
                "SELECT content FROM integration_objects WHERE sha256 = ?",
                (digest,),
            ).fetchone()[0]
        )
        if sha256(blob).hexdigest() != digest:
            raise IntegrationError(FailureCode.TAMPERED_SOURCE)
        return blob

    def put_contract(self, contract: CanonicalContract) -> str:
        """@brief Retains one fully validated immutable contract.
        @param contract Closed contract already validated by its constructor.
        @return External content identity.
        @details This records data without creating authority or publication.
        """
        return self.put(contract.kind, contract.canonical_bytes)

    def reference(self, owner: str, children: tuple[str, ...]) -> None:
        """@brief Retains append-only references to existing content objects.
        @param owner Existing parent content identity.
        @param children Existing child content identities.
        @return None.
        @details Foreign keys reject missing objects; callers own commit.
        """
        ResourcePolicy().require_sizes([0] * len(children))
        self.connection.executemany(
            "INSERT OR IGNORE INTO integration_object_refs VALUES (?, ?)",
            [(owner, child) for child in children],
        )

    def retain_sources(self, sources: tuple) -> tuple[str, ...]:
        """@brief Explicitly retains bounded immutable source package bytes.
        @param sources Complete source packages already resolved by the caller.
        @return Ordered manifest identities with historical object references.
        @details Retention grants no authority; execution resolves trusted
        approvals again. A savepoint preserves caller work on storage failure.
        """
        objects = [
            (
                "source_manifest",
                source.manifest_bytes,
                "source_approval",
                source.approval_bytes,
                source.artifacts,
            )
            for source in sources
        ]
        ResourcePolicy().require_sizes(
            [
                size
                for _, manifest, _, approval, artifacts in objects
                for size in [len(manifest), len(approval)]
                + [len(blob) for _, _, blob in artifacts]
            ]
        )
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")
        manifests = []
        with savepoint(self.connection, "integration_retain_sources"):
            for kind, manifest, approval_kind, approval, artifacts in objects:
                parent = self.put(kind, manifest)
                children = (self.put(approval_kind, approval),) + tuple(
                    self.put("artifact", blob) for _, _, blob in artifacts
                )
                self.reference(parent, children)
                manifests.append(parent)
        return tuple(manifests)

    def contract(self, digest: str, contract_type: type) -> CanonicalContract:
        """@brief Reloads and validates one exact typed contract.
        @param digest Required object identity.
        @param contract_type Expected CanonicalContract subclass.
        @return Validated detached contract.
        @details Noncanonical bytes fail rather than being normalized silently.
        """
        from partsmith.ir.canonical import parse_json

        if not isinstance(contract_type, type) or not issubclass(
            contract_type, CanonicalContract
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        blob = self.get(digest, contract_type.kind)
        try:
            result = contract_type(parse_json(blob))
        except (ValueError, TypeError) as error:
            raise IntegrationError(FailureCode.TAMPERED_SOURCE) from error
        if result.canonical_bytes != blob:
            raise IntegrationError(FailureCode.TAMPERED_SOURCE)
        return result

    def head(self, target: dict) -> InstallationManifest | None:
        """@brief Resolves the trusted published head for an exact target.
        @param target Project/library/scope identity.
        @return Current immutable manifest or None before registration/install.
        @details A supplied manifest or imported GUI label is never a head.
        """
        row = self.connection.execute(
            "SELECT t.library_id, t.scope, h.manifest_hash "
            "FROM integration_targets t JOIN integration_heads h "
            "ON h.project_id = t.project_id WHERE t.project_id = ?",
            (target["project_id"],),
        ).fetchone()
        if row is None:
            return None
        if (row["library_id"], row["scope"]) != (
            target["library_id"],
            target["scope"],
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if row["manifest_hash"] is None:
            return None
        manifest = self.contract(row["manifest_hash"], InstallationManifest)
        if manifest.data["target"] != target:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        return manifest

    def save_plan(self, plan: IntegrationPlan, snapshot: dict) -> str:
        """@brief Explicitly persists a frozen plan and detached snapshot.
        @param plan Exact reviewed planning data.
        @param snapshot Whole-target operational snapshot identity document.
        @return New operational attempt ID.
        @details Dry run never calls this method. Atomic savepoints preserve
        caller work and leave the resulting transaction uncommitted.
        """
        validate_snapshot(snapshot, plan)
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")
        with savepoint(self.connection, "integration_save_plan"):
            plan_hash = self.put_contract(plan)
            snapshot_hash = self.put(
                "target_snapshot", canonical_json(snapshot)
            )
            attempt_id = str(uuid4())
            self.connection.execute(
                "INSERT INTO integration_attempts VALUES (?, ?, ?, ?, ?)",
                (
                    attempt_id,
                    plan.data["target"]["project_id"],
                    plan_hash,
                    snapshot_hash,
                    utc_timestamp(),
                ),
            )
            self.event(attempt_id, "PLANNED", plan_hash)
        return attempt_id

    def event(
        self, attempt_id: str, state: str, object_hash: str | None = None
    ) -> None:
        """@brief Appends one truthful operational attempt event.
        @param attempt_id Existing immutable attempt ID.
        @param state Closed publication/task state distinct from BuildState.
        @param object_hash Optional immutable supporting object identity.
        @return None.
        @details Earlier events stay unchanged; the caller owns commit.
        """
        if state not in STATES:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        self.connection.execute(
            "INSERT INTO integration_events "
            "(attempt_id, state, object_hash, created_at) VALUES (?, ?, ?, ?)",
            (attempt_id, state, object_hash, utc_timestamp()),
        )
