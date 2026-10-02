"""@package partsmith.release.contracts
@brief Typed deterministic contracts for the Phase 8 release workflow.
@details Separates canonical engineering content from authenticated audit
metadata and rejects incomplete hash bindings before persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.release.schema import schema_issues

_SHA256_LENGTH = 64


class BuildState(StrEnum):
    """@brief Enumerates persisted PartSmith build states.
    @details HUMAN_REVIEW is intentionally absent because it is a validation
    result status; persisted waiting states use HUMAN_REVIEW_REQUIRED.
    """

    SOURCE_RECEIVED = "SOURCE_RECEIVED"
    SOURCE_ANALYZED = "SOURCE_ANALYZED"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    IR_BUILT = "IR_BUILT"
    PACKAGE_IDENTIFIED = "PACKAGE_IDENTIFIED"
    IR_VALIDATED = "IR_VALIDATED"
    SYMBOL_GENERATED = "SYMBOL_GENERATED"
    FOOTPRINT_GENERATED = "FOOTPRINT_GENERATED"
    MODEL_3D_GENERATED = "3D_GENERATED"
    ARTIFACT_VALIDATION = "ARTIFACT_VALIDATION"
    CROSS_VALIDATION = "CROSS_VALIDATION"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"
    REJECTED = "REJECTED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    IR_INVALID = "IR_INVALID"
    PACKAGE_UNSUPPORTED = "PACKAGE_UNSUPPORTED"
    NOT_GENERATABLE = "NOT_GENERATABLE"
    ARTIFACT_VALIDATION_FAILED = "ARTIFACT_VALIDATION_FAILED"
    CROSS_VALIDATION_FAILED = "CROSS_VALIDATION_FAILED"


class ReviewStage(StrEnum):
    """@brief Identifies input and release review boundaries.
    @details Input approval may create a reviewed revision but cannot approve
    released artifacts.
    """

    INPUT = "INPUT"
    RELEASE = "RELEASE"


class ValidationStage(StrEnum):
    """@brief Enumerates strict validation result stages.
    @details Only ARTIFACT and FINAL_ARTIFACT enter validation semantics.
    """

    INPUT = "INPUT"
    ARTIFACT = "ARTIFACT"
    FINAL_ARTIFACT = "FINAL_ARTIFACT"
    POST_MANIFEST = "POST_MANIFEST"
    REPRODUCIBILITY = "REPRODUCIBILITY"


class ValidationStatus(StrEnum):
    """@brief Enumerates applicable validation result statuses.
    @details NOT_APPLICABLE uses a null status and is not a member.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NOT_GENERATABLE = "NOT_GENERATABLE"


class BundleAvailability(StrEnum):
    """@brief Classifies portable bundle replay availability.
    @details OFFLINE_COMPLETE requires verified local objects and runtime.
    """

    OFFLINE_COMPLETE = "OFFLINE_COMPLETE"
    RETRIEVAL_REQUIRED = "RETRIEVAL_REQUIRED"


def _require_text(name: str, value: str) -> None:
    """@brief Requires a nonempty string field.
    @param name Field name used in diagnostics.
    @param value Field value to validate.
    @return None.
    @details Raises ValueError instead of creating an incomplete contract.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _require_sha256(name: str, value: str) -> None:
    """@brief Requires a lowercase SHA-256 hexadecimal digest.
    @param name Field name used in diagnostics.
    @param value Digest to validate.
    @return None.
    @details Rejects uppercase, truncated, and non-hexadecimal bindings.
    """
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or value.lower() != value
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(
            f"{name} must be a lowercase SHA-256 digest"
        ) from error


def _validated_document(kind: str, data: dict[str, Any]) -> bytes:
    """@brief Validates and canonicalizes one external Phase 8 document.
    @param kind Schema definition name.
    @param data JSON-compatible document content.
    @return Canonical JSON bytes.
    @details Raises ValueError with stable schema paths before hashing.
    """
    issues = schema_issues(kind, data)
    if issues:
        detail = "; ".join(
            f"{issue.path or '/'}:{issue.code}" for issue in issues
        )
        raise ValueError(f"Invalid {kind}: {detail}")
    return canonical_json(data)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """@brief Represents an authenticated headless reviewer.
    @details The authentication mechanism is trusted adapter metadata and is
    never inferred from a caller-supplied reviewer display name.
    """

    subject: str
    mechanism: str

    def __post_init__(self) -> None:
        """@brief Validates the authenticated principal.
        @return None.
        @details Rejects empty subject and mechanism identifiers.
        """
        _require_text("subject", self.subject)
        _require_text("mechanism", self.mechanism)

    def require_reviewer(self, reviewer: str) -> None:
        """@brief Verifies a requested reviewer matches this principal.
        @param reviewer Reviewer identity supplied by the service request.
        @return None.
        @details Raises PermissionError on an identity mismatch.
        """
        if reviewer != self.subject:
            raise PermissionError(
                "Reviewer does not match the authenticated principal"
            )


@dataclass(frozen=True)
class NotGeneratableDetail:
    """@brief Explains why an artifact cannot be generated safely.
    @details Implements the four mandatory statements in section 194.
    """

    missing: str
    importance: str
    blocked_artifact: str
    unblocking_evidence: str

    def __post_init__(self) -> None:
        """@brief Validates the complete non-generatable explanation.
        @return None.
        @details Every section 194 statement must be present.
        """
        _validated_document("not_generatable", self.to_dict())

    def to_dict(self) -> dict[str, str]:
        """@brief Serializes this non-generatable explanation.
        @return JSON-compatible section 194 content.
        @details Field names are stable external contract names.
        """
        return {
            "missing": self.missing,
            "importance": self.importance,
            "blocked_artifact": self.blocked_artifact,
            "unblocking_evidence": self.unblocking_evidence,
        }


@dataclass(frozen=True)
class WarningPolicy:
    """@brief Defines one versioned policy for accepting a warning.
    @details Warning acceptance is audit metadata and never rewrites WARN to
    PASS in validation content.
    """

    schema_version: str
    policy_id: str
    rule_id: str
    scope: str
    rationale: str
    required_reviewer_decision: str

    def __post_init__(self) -> None:
        """@brief Validates the closed warning policy contract.
        @return None.
        @details Rejects incomplete or unknown policy fields through schema.
        """
        _validated_document("warning_policy", self.to_dict())

    def to_dict(self) -> dict[str, str]:
        """@brief Serializes this warning policy.
        @return JSON-compatible warning policy content.
        @details The serialized bytes are deterministic engineering input.
        """
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "rule_id": self.rule_id,
            "scope": self.scope,
            "rationale": self.rationale,
            "required_reviewer_decision": (self.required_reviewer_decision),
        }

    @property
    def sha256(self) -> str:
        """@brief Hashes the canonical warning policy.
        @return Lowercase SHA-256 content digest.
        @details Actor identities and timestamps are not part of this policy.
        """
        return sha256(canonical_json(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class ApprovalBinding:
    """@brief Binds release approval to exact deterministic content.
    @details A binding is reusable only when every recorded digest matches.
    """

    input_snapshot_hash: str
    engineering_manifest_hash: str
    validation_semantics_hash: str
    artifact_hashes: tuple[str, ...]
    post_manifest_report_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        """@brief Validates every exact-hash approval binding.
        @return None.
        @details Empty artifact or post-manifest sets cannot be approved.
        """
        _require_sha256("input_snapshot_hash", self.input_snapshot_hash)
        _require_sha256(
            "engineering_manifest_hash", self.engineering_manifest_hash
        )
        _require_sha256(
            "validation_semantics_hash", self.validation_semantics_hash
        )
        if not self.artifact_hashes:
            raise ValueError("artifact_hashes must not be empty")
        if not self.post_manifest_report_hashes:
            raise ValueError("post_manifest_report_hashes must not be empty")
        for index, digest in enumerate(self.artifact_hashes):
            _require_sha256(f"artifact_hashes[{index}]", digest)
        for index, digest in enumerate(self.post_manifest_report_hashes):
            _require_sha256(f"post_manifest_report_hashes[{index}]", digest)

    def to_dict(self) -> dict[str, Any]:
        """@brief Serializes exact release approval bindings.
        @return JSON-compatible binding content.
        @details Hash arrays are sorted so caller order cannot alter identity.
        """
        return {
            "input_snapshot_hash": self.input_snapshot_hash,
            "engineering_manifest_hash": self.engineering_manifest_hash,
            "validation_semantics_hash": self.validation_semantics_hash,
            "artifact_hashes": sorted(self.artifact_hashes),
            "post_manifest_report_hashes": sorted(
                self.post_manifest_report_hashes
            ),
        }


class _CanonicalDocument:
    """@brief Stores one validated external document as canonical bytes.
    @details Returned data is detached so callers cannot mutate frozen content.
    """

    schema_kind: str

    def __init__(self, data: dict[str, Any]):
        """@brief Validates and freezes one external document.
        @param data JSON-compatible document mapping.
        @return None.
        @details Canonical bytes become the immutable source of record.
        """
        self._canonical_bytes = _validated_document(self.schema_kind, data)

    @property
    def canonical_bytes(self) -> bytes:
        """@brief Returns canonical document bytes.
        @return Immutable canonical UTF-8 JSON bytes.
        @details The returned bytes are safe to hash or persist directly.
        """
        return self._canonical_bytes

    @property
    def data(self) -> dict[str, Any]:
        """@brief Returns a detached parsed document.
        @return JSON-compatible document mapping.
        @details Mutating the returned value does not change frozen content.
        """
        return parse_json(self._canonical_bytes)

    @property
    def sha256(self) -> str:
        """@brief Hashes the canonical document bytes.
        @return Lowercase SHA-256 content digest.
        @details No self-hash field is added to deterministic content.
        """
        return sha256(self._canonical_bytes).hexdigest()


class EngineeringManifest(_CanonicalDocument):
    """@brief Frozen deterministic engineering manifest.
    @details The manifest excludes audit metadata and contains no self-hash.
    """

    schema_kind = "engineering_manifest"


class AuditEnvelope(_CanonicalDocument):
    """@brief Frozen audit envelope referencing deterministic content.
    @details Actors, decisions, run IDs, and timestamps belong here rather
    than in the engineering manifest.
    """

    schema_kind = "audit_envelope"


class ReleaseReport(_CanonicalDocument):
    """@brief Frozen section 234 machine-readable release report.
    @details Declared exclusions remain present with null validation status.
    """

    schema_kind = "release_report"


class PostManifestReport(_CanonicalDocument):
    """@brief Frozen post-manifest verification report.
    @details Every result is bound to the completed manifest and remains
    outside the deterministic engineering manifest.
    """

    schema_kind = "post_manifest_report"

    def __init__(self, data: dict[str, Any]):
        """@brief Validates and freezes one post-manifest report.
        @param data JSON-compatible report mapping.
        @return None.
        @details Rejects results from any stage other than POST_MANIFEST.
        """
        super().__init__(data)
        if any(
            result["stage"] != ValidationStage.POST_MANIFEST
            for result in self.data["results"]
        ):
            raise ValueError(
                "Post-manifest report contains a non-POST_MANIFEST result"
            )
