"""@package partsmith.persistence.release
@brief Immutable persistence for Phase 8 build and release content.
@details Stores snapshots, artifacts, validation results, manifests, reports,
and exact approval bindings without committing caller transactions.
"""

from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import PurePosixPath
from uuid import uuid4

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence.database import utc_timestamp
from partsmith.persistence.immutable import IdentityConflictError
from partsmith.release.contracts import (
    ApprovalBinding,
    EngineeringManifest,
    PostManifestReport,
)
from partsmith.release.schema import schema_issues

_SEMANTIC_AUDIT_FIELDS = {
    "created_at",
    "duration_ms",
    "execution_time_ms",
    "id",
    "run_id",
    "timestamp",
    "updated_at",
}
_ARTIFACT_NAMES = {
    "SYMBOL": "symbol",
    "FOOTPRINT": "footprint",
    "MODEL_3D": "model_3d",
}


def _require_sha256(name: str, value: str) -> None:
    """@brief Requires a lowercase SHA-256 hexadecimal digest.
    @param name Diagnostic field name.
    @param value Digest to validate.
    @return None.
    @details Raises ValueError before invalid bindings reach SQLite.
    """
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.lower() != value
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(
            f"{name} must be a lowercase SHA-256 digest"
        ) from error


def _portable_path(value: str) -> str:
    """@brief Normalizes one portable logical artifact path.
    @param value Proposed logical path.
    @return Normalized POSIX-style relative path.
    @details Rejects absolute, parent-relative, drive, and backslash paths.
    """
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
    ):
        raise ValueError("Artifact path must be portable and relative")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) == ".":
        raise ValueError("Artifact path must be portable and relative")
    return str(path)


def _semantic_result(result: dict) -> dict:
    """@brief Removes audit-only fields from one validation result.
    @param result Complete persisted validation result.
    @return Deterministic validation-semantic content.
    @details Engineering fields and exact artifact bindings remain intact.
    """
    return {
        key: value
        for key, value in result.items()
        if key not in _SEMANTIC_AUDIT_FIELDS
    }


def validation_semantics_hash(results: list[dict]) -> str:
    """@brief Hashes final retained validation semantics.
    @param results ARTIFACT and FINAL_ARTIFACT result mappings.
    @return Lowercase SHA-256 semantic digest.
    @details Caller order and audit-only identities do not affect the hash.
    """
    semantic = [_semantic_result(result) for result in results]
    semantic.sort(key=canonical_json)
    return sha256(canonical_json(semantic)).hexdigest()


class ReleaseStore:
    """@brief Persists immutable Phase 8 release records.
    @details Methods verify existing identities and participate in the caller's
    current transaction without committing.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the release store.
        @param connection Migrated SQLite connection.
        @return None.
        @details The caller owns the transaction and connection lifetime.
        """
        self.connection = connection

    def _require_build(self, build_id: str) -> sqlite3.Row:
        """@brief Resolves one build or fails explicitly.
        @param build_id Build identity to resolve.
        @return Persisted build row.
        @details Missing builds never create orphan release records.
        """
        row = self.connection.execute(
            "SELECT * FROM builds WHERE id = ?", (build_id,)
        ).fetchone()
        if row is None:
            raise KeyError(build_id)
        return row

    def put_snapshot(
        self,
        build_id: str,
        snapshot: dict,
        *,
        ir_record_hash: str,
        pdl_id: str,
        pdl_revision: str,
        pdl_hash: str,
    ) -> str:
        """@brief Freezes one complete build-input snapshot.
        @param build_id Build that consumes the snapshot.
        @param snapshot Complete deterministic input mapping.
        @param ir_record_hash Full normalized IR record digest.
        @param pdl_id Selected PDL identity.
        @param pdl_revision Selected PDL revision.
        @param pdl_hash Exact selected PDL content digest.
        @return Input snapshot SHA-256 digest.
        @details A build cannot replace an existing snapshot with new bytes.
        """
        self._require_build(build_id)
        _require_sha256("ir_record_hash", ir_record_hash)
        _require_sha256("pdl_hash", pdl_hash)
        blob = canonical_json(snapshot)
        digest = sha256(blob).hexdigest()
        existing = self.connection.execute(
            "SELECT * FROM build_snapshots WHERE build_id = ?", (build_id,)
        ).fetchone()
        if existing is not None:
            if (
                bytes(existing["canonical_bytes"]) != blob
                or existing["input_snapshot_hash"] != digest
            ):
                raise IdentityConflictError(
                    "Build snapshot is bound to different bytes"
                )
            return digest
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO build_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                build_id,
                digest,
                ir_record_hash,
                pdl_id,
                pdl_revision,
                pdl_hash,
                blob,
                now,
                now,
            ),
        )
        self.connection.execute(
            "UPDATE builds SET ir_hash = ?, build_inputs_hash = ?, "
            "pdl_revision = ?, updated_at = ? WHERE id = ?",
            (ir_record_hash, digest, pdl_revision, now, build_id),
        )
        return digest

    def put_artifact(
        self,
        build_id: str,
        artifact_type: str,
        stage: str,
        logical_path: str,
        content: bytes,
        *,
        dependency_hash: str,
        generator: str,
        generator_version: str,
    ) -> str:
        """@brief Stores or verifies one exact artifact byte sequence.
        @param build_id Owning build identity.
        @param artifact_type SYMBOL, FOOTPRINT, or MODEL_3D.
        @param stage PRELIMINARY or FINAL.
        @param logical_path Portable component-relative path.
        @param content Exact artifact bytes.
        @param dependency_hash Generator dependency digest.
        @param generator Generator identity.
        @param generator_version Generator version.
        @return Exact artifact SHA-256 digest.
        @details One build/type/stage identity cannot be rebound.
        """
        self._require_build(build_id)
        if artifact_type not in _ARTIFACT_NAMES:
            raise ValueError("Unsupported artifact type")
        if stage not in {"PRELIMINARY", "FINAL"}:
            raise ValueError("Unsupported artifact stage")
        path = _portable_path(logical_path)
        _require_sha256("dependency_hash", dependency_hash)
        if not isinstance(content, bytes):
            raise TypeError("Artifact content must be bytes")
        digest = sha256(content).hexdigest()
        existing = self.connection.execute(
            "SELECT * FROM artifacts WHERE build_id = ? "
            "AND artifact_type = ? AND stage = ?",
            (build_id, artifact_type, stage),
        ).fetchone()
        if existing is not None:
            if (
                bytes(existing["content"]) != content
                or existing["sha256"] != digest
                or existing["logical_path"] != path
                or existing["dependency_hash"] != dependency_hash
            ):
                raise IdentityConflictError(
                    "Artifact identity is bound to different content"
                )
            return digest
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO artifacts VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                build_id,
                artifact_type,
                stage,
                path,
                digest,
                dependency_hash,
                generator,
                generator_version,
                content,
                now,
                now,
            ),
        )
        return digest

    def put_validation_result(
        self,
        build_id: str,
        subject_id: str,
        result: dict,
        *,
        superseded: bool = False,
    ) -> str:
        """@brief Stores one immutable validation result.
        @param build_id Owning build identity.
        @param subject_id Stable validated subject identity.
        @param result Complete validation result mapping.
        @param superseded Whether a newer retained result replaced this one.
        @return Canonical validation-result digest.
        @details Schema-invalid or stage-inconsistent results are rejected.
        """
        self._require_build(build_id)
        issues = schema_issues("validation_result", result)
        if issues:
            raise ValueError("Invalid validation result")
        if not subject_id:
            raise ValueError("subject_id must not be empty")
        blob = canonical_json(result)
        digest = sha256(blob).hexdigest()
        existing = self.connection.execute(
            "SELECT * FROM validation_results WHERE canonical_sha256 = ?",
            (digest,),
        ).fetchone()
        if existing is not None:
            if (
                existing["build_id"] != build_id
                or existing["subject_id"] != subject_id
                or bytes(existing["canonical_bytes"]) != blob
            ):
                raise IdentityConflictError(
                    "Validation result hash is bound to another identity"
                )
            return digest
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO validation_results VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                build_id,
                result["stage"],
                result["rule_id"],
                subject_id,
                digest,
                blob,
                int(superseded),
                now,
                now,
            ),
        )
        return digest

    def retained_validation_results(self, build_id: str) -> list[dict]:
        """@brief Loads retained final validation results for one build.
        @param build_id Build whose semantic results are required.
        @return Detached ARTIFACT and FINAL_ARTIFACT result mappings.
        @details Preliminary, superseded, post-manifest, and replay results
        are excluded.
        """
        self._require_build(build_id)
        results = []
        for row in self.connection.execute(
            "SELECT canonical_sha256, canonical_bytes "
            "FROM validation_results "
            "WHERE build_id = ? AND superseded = 0 "
            "AND stage IN ('ARTIFACT', 'FINAL_ARTIFACT') "
            "ORDER BY canonical_sha256",
            (build_id,),
        ):
            blob = bytes(row["canonical_bytes"])
            if sha256(blob).hexdigest() != row["canonical_sha256"]:
                raise RuntimeError("Stored validation result hash mismatch")
            results.append(parse_json(blob))
        return results

    def validation_semantics_hash(self, build_id: str) -> str:
        """@brief Hashes retained validation semantics for one build.
        @param build_id Build whose semantic digest is required.
        @return Lowercase SHA-256 semantic digest.
        @details At least one retained final validation result is required.
        """
        results = self.retained_validation_results(build_id)
        if not results:
            raise ValueError("No retained validation semantics")
        return validation_semantics_hash(results)

    def _final_artifacts(self, build_id: str) -> dict[str, sqlite3.Row]:
        """@brief Loads the complete final artifact set.
        @param build_id Build whose final artifacts are required.
        @return Artifact rows keyed by manifest artifact name.
        @details Missing or duplicate required artifacts fail explicitly.
        """
        rows = self.connection.execute(
            "SELECT * FROM artifacts WHERE build_id = ? AND stage = 'FINAL'",
            (build_id,),
        ).fetchall()
        for row in rows:
            if sha256(bytes(row["content"])).hexdigest() != row["sha256"]:
                raise RuntimeError("Stored artifact hash mismatch")
        artifacts = {
            _ARTIFACT_NAMES[row["artifact_type"]]: row for row in rows
        }
        if set(artifacts) != set(_ARTIFACT_NAMES.values()):
            raise ValueError("Build does not have all three final artifacts")
        return artifacts

    def put_manifest(
        self, build_id: str, manifest: EngineeringManifest
    ) -> str:
        """@brief Stores a manifest bound to persisted final content.
        @param build_id Owning build identity.
        @param manifest Frozen deterministic engineering manifest.
        @return Engineering manifest SHA-256 digest.
        @details Snapshot, artifact, and validation bindings are rechecked.
        """
        self._require_build(build_id)
        snapshot = self.connection.execute(
            "SELECT input_snapshot_hash, canonical_bytes "
            "FROM build_snapshots "
            "WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if snapshot is None:
            raise ValueError("Build snapshot is missing")
        data = manifest.data
        snapshot_hash = snapshot["input_snapshot_hash"]
        if (
            data["component_ir"]["input_snapshot_hash"] != snapshot_hash
            or data["reproducibility"]["build_inputs_hash"] != snapshot_hash
        ):
            raise ValueError("Manifest snapshot binding is stale")
        artifacts = self._final_artifacts(build_id)
        for name, artifact in artifacts.items():
            output = data["outputs"][name]
            if (
                output.get("sha256") != artifact["sha256"]
                or output.get("path") != artifact["logical_path"]
            ):
                raise ValueError(f"Manifest {name} binding is stale")
        semantics_hash = self.validation_semantics_hash(build_id)
        if validation_semantics_hash(data["validation"]["results"]) != (
            semantics_hash
        ):
            raise ValueError("Manifest validation semantics are stale")
        existing = self.connection.execute(
            "SELECT * FROM engineering_manifests WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if existing is not None:
            if (
                bytes(existing["canonical_bytes"]) != manifest.canonical_bytes
                or existing["sha256"] != manifest.sha256
                or existing["validation_semantics_hash"] != semantics_hash
            ):
                raise IdentityConflictError(
                    "Build manifest is bound to different content"
                )
            return manifest.sha256
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO engineering_manifests VALUES (?, ?, ?, ?, ?, ?)",
            (
                build_id,
                manifest.sha256,
                semantics_hash,
                manifest.canonical_bytes,
                now,
                now,
            ),
        )
        return manifest.sha256

    def put_post_manifest_report(
        self, build_id: str, report: PostManifestReport
    ) -> str:
        """@brief Stores a post-manifest verification report.
        @param build_id Owning build identity.
        @param report Frozen post-manifest report.
        @return Report SHA-256 digest.
        @details The report must bind the exact stored manifest.
        """
        self._require_build(build_id)
        manifest = self.connection.execute(
            "SELECT sha256 FROM engineering_manifests WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if (
            manifest is None
            or report.data["manifest_hash"] != manifest["sha256"]
        ):
            raise ValueError("Post-manifest report binding is stale")
        existing = self.connection.execute(
            "SELECT * FROM post_manifest_reports WHERE sha256 = ?",
            (report.sha256,),
        ).fetchone()
        if existing is not None:
            if (
                existing["build_id"] != build_id
                or bytes(existing["canonical_bytes"]) != report.canonical_bytes
            ):
                raise IdentityConflictError(
                    "Post-manifest report hash is bound elsewhere"
                )
            return report.sha256
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO post_manifest_reports VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                build_id,
                manifest["sha256"],
                report.sha256,
                report.canonical_bytes,
                now,
                now,
            ),
        )
        return report.sha256

    def verify_approval_binding(
        self,
        build_id: str,
        binding: ApprovalBinding,
        *,
        allow_approved: bool = False,
    ) -> None:
        """@brief Verifies all deterministic content required for approval.
        @param build_id Build proposed for release approval.
        @param binding Exact content binding supplied by the decision.
        @param allow_approved Permit approved/exported source re-verification.
        @return None.
        @details Blocking validation, stale bytes, or failed manifest checks
        prevent approval.
        """
        build = self._require_build(build_id)
        allowed_states = {"HUMAN_REVIEW_REQUIRED"}
        if allow_approved:
            allowed_states.update({"APPROVED", "EXPORTED"})
        if build["state"] not in allowed_states:
            raise ValueError("Build is not waiting for review")
        transition = self.connection.execute(
            "SELECT review_stage FROM build_state_transitions "
            "WHERE build_id = ? AND to_state = 'HUMAN_REVIEW_REQUIRED' "
            "ORDER BY id DESC LIMIT 1",
            (build_id,),
        ).fetchone()
        if transition is None or transition["review_stage"] != "RELEASE":
            raise ValueError("Build is not waiting for release review")
        snapshot = self.connection.execute(
            "SELECT input_snapshot_hash, canonical_bytes "
            "FROM build_snapshots "
            "WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        manifest = self.connection.execute(
            "SELECT sha256, validation_semantics_hash "
            "FROM engineering_manifests WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if snapshot is None or manifest is None:
            raise ValueError("Build release content is incomplete")
        if (
            sha256(bytes(snapshot["canonical_bytes"])).hexdigest()
            != (snapshot["input_snapshot_hash"])
        ):
            raise RuntimeError("Stored build snapshot hash mismatch")
        if binding.input_snapshot_hash != snapshot["input_snapshot_hash"]:
            raise ValueError("Approval snapshot binding is stale")
        manifest_row = self.connection.execute(
            "SELECT canonical_bytes FROM engineering_manifests "
            "WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        manifest_document = EngineeringManifest(
            parse_json(bytes(manifest_row["canonical_bytes"]))
        )
        if manifest_document.sha256 != manifest["sha256"]:
            raise RuntimeError("Stored engineering manifest hash mismatch")
        if binding.engineering_manifest_hash != manifest["sha256"]:
            raise ValueError("Approval manifest binding is stale")
        semantics_hash = self.validation_semantics_hash(build_id)
        if (
            binding.validation_semantics_hash != semantics_hash
            or manifest["validation_semantics_hash"] != semantics_hash
        ):
            raise ValueError("Approval validation binding is stale")
        results = self.retained_validation_results(build_id)
        blockers = [
            result
            for result in results
            if result["applicability"] == "APPLICABLE"
            and result["status"] != "PASS"
        ]
        if blockers:
            raise ValueError("Blocking validation results prevent approval")
        artifact_hashes = sorted(
            row["sha256"] for row in self._final_artifacts(build_id).values()
        )
        if sorted(binding.artifact_hashes) != artifact_hashes:
            raise ValueError("Approval artifact binding is stale")
        report_rows = self.connection.execute(
            "SELECT sha256, manifest_hash, canonical_bytes "
            "FROM post_manifest_reports WHERE build_id = ? ORDER BY sha256",
            (build_id,),
        ).fetchall()
        if sorted(binding.post_manifest_report_hashes) != [
            row["sha256"] for row in report_rows
        ]:
            raise ValueError("Approval post-manifest binding is stale")
        for row in report_rows:
            if row["manifest_hash"] != manifest["sha256"]:
                raise ValueError("Post-manifest report binding is stale")
            report = PostManifestReport(
                parse_json(bytes(row["canonical_bytes"]))
            )
            if report.sha256 != row["sha256"]:
                raise RuntimeError("Stored post-manifest report hash mismatch")
            if any(
                result["applicability"] == "APPLICABLE"
                and result["status"] != "PASS"
                for result in report.data["results"]
            ):
                raise ValueError("Post-manifest verification blocks approval")

    def record_release_decision(
        self,
        build_id: str,
        decision: str,
        actor: str,
        reason: str,
        binding: ApprovalBinding | None,
    ) -> str:
        """@brief Appends one immutable release decision.
        @param build_id Reviewed build identity.
        @param decision APPROVE or REJECT.
        @param actor Authenticated reviewer subject.
        @param reason Nonempty decision rationale.
        @param binding Exact approval binding, or None for rejection.
        @return New release decision identity.
        @details Approval bindings are persisted separately in the same
        transaction as the decision and state transition.
        """
        self._require_build(build_id)
        if decision not in {"APPROVE", "REJECT"}:
            raise ValueError("Unsupported release decision")
        if not actor or not reason:
            raise ValueError("Release decision actor and reason are required")
        if decision == "APPROVE" and binding is None:
            raise ValueError("Approval requires an exact content binding")
        decision_id = str(uuid4())
        content = {
            "schema_version": "1.0",
            "decision_id": decision_id,
            "build_id": build_id,
            "decision": decision,
            "actor": actor,
            "reason": reason,
            "binding": binding.to_dict() if binding is not None else None,
        }
        blob = canonical_json(content)
        binding_sha = (
            sha256(canonical_json(binding.to_dict())).hexdigest()
            if binding is not None
            else sha256(canonical_json(None)).hexdigest()
        )
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO release_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision_id,
                build_id,
                decision,
                actor,
                reason,
                binding_sha,
                blob,
                now,
                now,
            ),
        )
        if binding is not None:
            binding_blob = canonical_json(binding.to_dict())
            self.connection.execute(
                "INSERT INTO approval_bindings VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    build_id,
                    decision_id,
                    binding.input_snapshot_hash,
                    binding.engineering_manifest_hash,
                    binding.validation_semantics_hash,
                    sha256(binding_blob).hexdigest(),
                    binding_blob,
                    now,
                    now,
                ),
            )
        return decision_id
