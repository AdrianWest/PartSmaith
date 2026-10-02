"""@package partsmith.release.input_review
@brief Authenticated Phase 8 input evidence-review operations.
@details Persists immutable candidates and decisions, verifies exact revision
and inventory bindings, and advances reviewed heads with atomic stale checks.
"""

from __future__ import annotations

import copy
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from partsmith.ir import ComponentIR, canonical_json
from partsmith.ir.canonical import parse_json
from partsmith.ir.history import validate_revision_transition
from partsmith.ir.revised import resolve_pointer
from partsmith.ir.schema import fragment_valid
from partsmith.ir.targets import overlaps, owner_path, target_schema
from partsmith.persistence.immutable import ImmutableStore, StaleHeadError
from partsmith.release.contracts import AuthenticatedPrincipal
from partsmith.release.schema import schema_issues

NO_HEAD_HASH = "0" * 64


def _now() -> str:
    """@brief Returns one server-controlled UTC review timestamp.
    @return ISO 8601 UTC timestamp.
    @details Caller-supplied timestamps are never trusted review metadata.
    """
    return datetime.now(UTC).isoformat()


def _validate_request(kind: str, data: dict) -> None:
    """@brief Validates one closed input-review request.
    @param kind Phase 8 schema definition name.
    @param data JSON-compatible request mapping.
    @return None.
    @details Stable schema paths are included in invalid-request errors.
    """
    issues = schema_issues(kind, data)
    if issues:
        detail = "; ".join(
            f"{issue.path or '/'}:{issue.code}" for issue in issues
        )
        raise ValueError(f"Invalid {kind}: {detail}")


@contextmanager
def _savepoint(connection: sqlite3.Connection, name: str) -> Iterator[None]:
    """@brief Protects one input-review operation with a savepoint.
    @param connection Active SQLite connection.
    @param name Trusted internal savepoint name.
    @return Iterator yielding control inside the savepoint.
    @details Any failure removes partial candidates, events, and head changes.
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


@dataclass(frozen=True)
class InputReviewProposal:
    """@brief Binds one evidence-review candidate to an exact base.
    @details Phase 8 initially supports the closed EVIDENCE_REVIEW action;
    engineering overrides are separate typed proposal operations.
    """

    component_id: str
    base_revision_id: str
    base_revision_hash: str
    expected_head_hash: str
    candidate_revision_id: str
    candidate_revision_hash: str
    inventory_sha256: str
    reason: str
    actions: tuple[str, ...] = ("EVIDENCE_REVIEW",)
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """@brief Validates this closed proposal request.
        @return None.
        @details Unknown actions and incomplete bindings are rejected.
        """
        _validate_request("input_review_proposal", self.to_dict())

    def to_dict(self) -> dict:
        """@brief Serializes this proposal request.
        @return JSON-compatible closed request mapping.
        @details Tuple actions become a deterministic JSON array.
        """
        return {
            "schema_version": self.schema_version,
            "component_id": self.component_id,
            "base_revision_id": self.base_revision_id,
            "base_revision_hash": self.base_revision_hash,
            "expected_head_hash": self.expected_head_hash,
            "candidate_revision_id": self.candidate_revision_id,
            "candidate_revision_hash": self.candidate_revision_hash,
            "inventory_sha256": self.inventory_sha256,
            "reason": self.reason,
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class OverrideProposalRequest:
    """@brief Requests one typed engineering override proposal.
    @details The trusted path registry derives value type and captures the
    previous value; callers provide no history or active-selector fields.
    """

    component_id: str
    base_revision_id: str
    base_revision_hash: str
    expected_head_hash: str
    path: str
    new_value: object
    evidence_reference: str
    reason: str
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """@brief Validates this closed override proposal request.
        @return None.
        @details Exact value typing is validated later against the trusted
        target registry.
        """
        _validate_request("override_proposal_request", self.to_dict())

    def to_dict(self) -> dict:
        """@brief Serializes this override proposal request.
        @return JSON-compatible closed request mapping.
        @details Previous values, decision IDs, and actor metadata are absent.
        """
        return {
            "schema_version": self.schema_version,
            "component_id": self.component_id,
            "base_revision_id": self.base_revision_id,
            "base_revision_hash": self.base_revision_hash,
            "expected_head_hash": self.expected_head_hash,
            "path": self.path,
            "new_value": self.new_value,
            "evidence_reference": self.evidence_reference,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class InputApprovalRequest:
    """@brief Requests approval of one exact persisted input proposal.
    @details The authenticated principal must match reviewer exactly.
    """

    proposal_id: str
    proposal_hash: str
    component_id: str
    candidate_revision_id: str
    candidate_revision_hash: str
    expected_head_hash: str
    inventory_sha256: str
    reviewer: str
    reason: str
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """@brief Validates this closed approval request.
        @return None.
        @details Every proposal, candidate, head, and inventory hash is
        mandatory.
        """
        _validate_request("input_approval_request", self.to_dict())

    def to_dict(self) -> dict:
        """@brief Serializes this input approval request.
        @return JSON-compatible closed request mapping.
        @details Field names are stable external service contract names.
        """
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "component_id": self.component_id,
            "candidate_revision_id": self.candidate_revision_id,
            "candidate_revision_hash": self.candidate_revision_hash,
            "expected_head_hash": self.expected_head_hash,
            "inventory_sha256": self.inventory_sha256,
            "reviewer": self.reviewer,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class InputRejectionRequest:
    """@brief Requests rejection of one exact persisted input proposal.
    @details Rejection records an immutable event and never changes the head.
    """

    proposal_id: str
    proposal_hash: str
    component_id: str
    candidate_revision_id: str
    candidate_revision_hash: str
    expected_head_hash: str
    reviewer: str
    reason: str
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """@brief Validates this closed rejection request.
        @return None.
        @details Exact proposal, candidate, and head bindings are mandatory.
        """
        _validate_request("input_rejection_request", self.to_dict())

    def to_dict(self) -> dict:
        """@brief Serializes this input rejection request.
        @return JSON-compatible closed request mapping.
        @details Field names are stable external service contract names.
        """
        return {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "component_id": self.component_id,
            "candidate_revision_id": self.candidate_revision_id,
            "candidate_revision_hash": self.candidate_revision_hash,
            "expected_head_hash": self.expected_head_hash,
            "reviewer": self.reviewer,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ProposalResult:
    """@brief Identifies one immutable persisted input proposal.
    @details The proposal hash binds the exact request and generated identity.
    """

    proposal_id: str
    proposal_hash: str
    candidate_revision_id: str
    candidate_revision_hash: str


@dataclass(frozen=True)
class RevisionResult:
    """@brief Identifies one newly reviewed current revision.
    @details Input approval never grants artifact release approval.
    """

    revision_id: str
    revision_hash: str
    review_event_id: str


@dataclass(frozen=True)
class InputReviewResult:
    """@brief Identifies one immutable input-review rejection.
    @details The candidate and proposal remain unchanged after rejection.
    """

    proposal_id: str
    review_event_id: str
    decision: str


class InputReviewService:
    """@brief Implements immutable evidence/inventory input review.
    @details Proposal, approval, and rejection operations use savepoints and
    exact compare-and-swap head bindings.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the input-review service.
        @param connection Migrated SQLite connection.
        @return None.
        @details The caller owns the outer transaction and connection.
        """
        self.connection = connection
        self.store = ImmutableStore(connection)

    def _head(self, component_id: str) -> sqlite3.Row | None:
        """@brief Loads the current reviewed component head.
        @param component_id Component identity.
        @return Current head row or None.
        @details The head is a mutable index over immutable revisions.
        """
        return self.connection.execute(
            "SELECT * FROM component_heads WHERE component_id = ?",
            (component_id,),
        ).fetchone()

    def _require_expected_head(
        self, component_id: str, expected_head_hash: str
    ) -> sqlite3.Row | None:
        """@brief Verifies an exact current-head expectation.
        @param component_id Component identity.
        @param expected_head_hash Expected digest or NO_HEAD_HASH.
        @return Current head row or None.
        @details Stale expectations raise StaleHeadError without rebasing.
        """
        head = self._head(component_id)
        if head is None:
            if expected_head_hash != NO_HEAD_HASH:
                raise StaleHeadError("Component head is absent")
        elif head["revision_hash"] != expected_head_hash:
            raise StaleHeadError("Component head changed")
        return head

    def _proposal(self, proposal_id: str, proposal_hash: str) -> sqlite3.Row:
        """@brief Resolves and verifies one immutable proposal.
        @param proposal_id Proposal identity.
        @param proposal_hash Expected canonical proposal digest.
        @return Persisted proposal row.
        @details Missing, tampered, or already decided proposals fail.
        """
        row = self.connection.execute(
            "SELECT * FROM review_proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
        if row is None:
            raise KeyError(proposal_id)
        blob = bytes(row["canonical_bytes"])
        if (
            row["canonical_sha256"] != proposal_hash
            or sha256(blob).hexdigest() != proposal_hash
        ):
            raise ValueError("Input proposal hash mismatch")
        decided = self.connection.execute(
            "SELECT 1 FROM review_events WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        if decided is not None:
            raise ValueError("Input proposal already has a decision")
        return row

    def _inventory_matches(self, revision: dict, digest: str) -> dict:
        """@brief Verifies an inventory covers all retained source/evidence.
        @param revision Candidate revision mapping.
        @param digest Acquisition inventory digest.
        @return Verified detached inventory mapping.
        @details Missing, stale, or incomplete inventories cannot be reviewed.
        """
        inventory = self.store.get_inventory(digest)
        source_hashes = {
            document["sha256"] for document in revision["source"]["documents"]
        }
        evidence_ids = {record["id"] for record in revision["evidence"]}
        if (
            set(inventory["source_hashes"]) != source_hashes
            or set(inventory["evidence_ids"]) != evidence_ids
        ):
            raise ValueError("Inventory does not match candidate inputs")
        return inventory

    def _require_review_only_transition(
        self, base: dict, candidate: dict
    ) -> None:
        """@brief Restricts this service to evidence-review-only candidates.
        @param base Exact base revision mapping.
        @param candidate Proposed child revision mapping.
        @return None.
        @details Engineering content and decision history must remain
        unchanged.
        """
        before = copy.deepcopy(base)
        after = copy.deepcopy(candidate)
        before_revision = before.pop("revision")
        after_revision = after.pop("revision")
        if before != after:
            raise ValueError(
                "EVIDENCE_REVIEW cannot change engineering content"
            )
        if after_revision["id"] == before_revision["id"]:
            raise ValueError("Candidate revision identity must be new")
        if after_revision["parent_id"] != before_revision["id"]:
            raise ValueError("Candidate must be a direct child of its base")
        for key in (
            "active_override_ids",
            "active_resolution_ids",
            "evidence_exclusions",
            "target_rebindings",
        ):
            if after_revision[key] != before_revision[key]:
                raise ValueError(
                    "EVIDENCE_REVIEW cannot change decision history"
                )
        if after_revision["evidence_review"] is not None:
            raise ValueError(
                "Proposal cannot assert trusted evidence-review metadata"
            )

    def _require_current_base(
        self,
        component_id: str,
        base_revision_id: str,
        base_revision_hash: str,
        expected_head_hash: str,
    ) -> tuple[sqlite3.Row, dict]:
        """@brief Verifies and loads one exact reviewed current base.
        @param component_id Component identity.
        @param base_revision_id Expected current revision identity.
        @param base_revision_hash Expected base revision digest.
        @param expected_head_hash Exact mutable-head expectation.
        @return Current head row and detached base revision.
        @details Override proposals require an existing reviewed head.
        """
        head = self._require_expected_head(component_id, expected_head_hash)
        if head is None:
            raise StaleHeadError("Override proposal requires a reviewed head")
        if (
            head["revision_id"] != base_revision_id
            or head["revision_hash"] != base_revision_hash
        ):
            raise StaleHeadError("Override base is not the current head")
        base = self.store.get_revision(base_revision_id)
        if (
            ComponentIR(base).sha256 != base_revision_hash
            or base["identity"]["component_id"] != component_id
        ):
            raise ValueError("Override base binding is stale")
        return head, base

    def _evidence_supports_path(
        self, revision: dict, evidence_id: str, path: str
    ) -> None:
        """@brief Verifies evidence is a candidate for an override target.
        @param revision Base revision containing evidence assignments.
        @param evidence_id Supporting evidence identity.
        @param path Trusted override target path.
        @return None.
        @details Pin leaves and quantity leaves compare by provenance owner.
        """
        evidence = next(
            (
                record
                for record in revision["evidence"]
                if record["id"] == evidence_id
            ),
            None,
        )
        if evidence is None:
            raise ValueError("Override evidence does not resolve")
        target_owner = owner_path(revision, path)
        candidate_owners = set()
        for candidate_path in evidence["candidate_targets"]:
            try:
                candidate_owners.add(owner_path(revision, candidate_path))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        if target_owner not in candidate_owners:
            raise ValueError("Override evidence does not support target")

    def _active_override(self, revision: dict, path: str) -> dict | None:
        """@brief Finds an exact active override or rejects overlap.
        @param revision Reviewed base revision.
        @param path Proposed trusted target path.
        @return Existing exact active override or None.
        @details Ancestor or descendant overlaps require a different explicit
        review operation.
        """
        records = {record["id"]: record for record in revision["overrides"]}
        matches = [
            records[override_id]
            for override_id in revision["revision"]["active_override_ids"]
            if overlaps(records[override_id]["path"], path)
        ]
        if any(record["path"] != path for record in matches):
            raise ValueError("Override target overlaps an active override")
        if len(matches) > 1:
            raise ValueError("Override target has ambiguous active decisions")
        return matches[0] if matches else None

    def _replace_pointer(
        self, revision: dict, path: str, value: object
    ) -> None:
        """@brief Replaces one already trusted JSON Pointer target.
        @param revision Mutable detached revision mapping.
        @param path Trusted non-root target path.
        @param value Replacement JSON-compatible value.
        @return None.
        @details The target registry and schema are validated before mutation.
        """
        parent_path, _, token = path.rpartition("/")
        parent = (
            resolve_pointer(revision, parent_path)
            if parent_path
            else (revision)
        )
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(parent, list):
            parent[int(token)] = value
        else:
            parent[token] = value

    def propose_override(
        self,
        request: OverrideProposalRequest,
        principal: AuthenticatedPrincipal,
    ) -> ProposalResult:
        """@brief Persists one typed pending override proposal.
        @param request Exact current base, target, value, and evidence binding.
        @param principal Authenticated proposing principal.
        @return Immutable proposal and generated candidate identities.
        @details The service captures the previous value and type, retains the
        engineering target unchanged, and appends a PENDING decision record.
        """
        with _savepoint(self.connection, "override_review_proposal"):
            _, base = self._require_current_base(
                request.component_id,
                request.base_revision_id,
                request.base_revision_hash,
                request.expected_head_hash,
            )
            schema, value_type = target_schema(request.path)
            self._evidence_supports_path(
                base, request.evidence_reference, request.path
            )
            existing = self._active_override(base, request.path)
            pending_id = str(uuid4())
            new_value = copy.deepcopy(request.new_value)
            if isinstance(new_value, dict) and "status" in new_value:
                new_value["status"] = "USER_OVERRIDE"
                new_value["override_id"] = pending_id
            if not fragment_valid(new_value, schema):
                raise ValueError("Override value does not match target schema")
            previous_value = copy.deepcopy(resolve_pointer(base, request.path))
            timestamp = _now()
            candidate = copy.deepcopy(base)
            candidate["revision"]["id"] = str(uuid4())
            candidate["revision"]["parent_id"] = request.base_revision_id
            candidate["revision"]["description"] = (
                f"Pending override for {request.path}"
            )
            candidate["revision"]["evidence_review"] = None
            candidate["overrides"].append(
                {
                    "id": pending_id,
                    "path": request.path,
                    "previous_value": previous_value,
                    "new_value": new_value,
                    "reason": request.reason,
                    "user": principal.subject,
                    "timestamp": timestamp,
                    "evidence_reference": request.evidence_reference,
                    "approval_state": "PENDING",
                    "value_type": value_type,
                    "base_revision_id": request.base_revision_id,
                    "supersedes_override_id": (
                        existing["id"] if existing is not None else None
                    ),
                }
            )
            candidate_document = ComponentIR(candidate)
            transition_issues = validate_revision_transition(base, candidate)
            if transition_issues:
                raise ValueError("Invalid pending override transition")
            inventory_sha256 = base["revision"]["evidence_review"][
                "inventory_sha256"
            ]
            self._inventory_matches(candidate, inventory_sha256)
            stored = self.store.put_revision(
                candidate,
                inventory_sha256=inventory_sha256,
                reviewed=False,
            )
            proposal_id = str(uuid4())
            proposal_data = request.to_dict() | {
                "proposal_id": proposal_id,
                "candidate_revision_id": stored.revision_id,
                "candidate_revision_hash": stored.canonical_sha256,
                "inventory_sha256": inventory_sha256,
                "pending_override_id": pending_id,
                "value_type": value_type,
                "previous_value": previous_value,
                "actions": ["OVERRIDE_REPLACEMENT"],
            }
            blob = canonical_json(proposal_data)
            digest = sha256(blob).hexdigest()
            now = _now()
            self.connection.execute(
                "INSERT INTO review_proposals VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal_id,
                    request.component_id,
                    request.base_revision_id,
                    request.base_revision_hash,
                    stored.revision_id,
                    stored.canonical_sha256,
                    request.expected_head_hash,
                    digest,
                    blob,
                    "PENDING",
                    now,
                    now,
                ),
            )
            if candidate_document.sha256 != stored.canonical_sha256:
                raise RuntimeError("Stored override candidate hash mismatch")
            return ProposalResult(
                proposal_id,
                digest,
                stored.revision_id,
                stored.canonical_sha256,
            )

    def propose(
        self, request: InputReviewProposal, candidate_revision: dict
    ) -> ProposalResult:
        """@brief Persists one unreviewed evidence-review proposal.
        @param request Exact base, candidate, inventory, and head bindings.
        @param candidate_revision Complete proposed IR 1.2 child revision.
        @return Immutable proposal identity and hashes.
        @details The candidate is persisted unreviewed and no approval metadata
        or current-head change is created.
        """
        with _savepoint(self.connection, "input_review_proposal"):
            head = self._require_expected_head(
                request.component_id, request.expected_head_hash
            )
            base = self.store.get_revision(request.base_revision_id)
            base_document = ComponentIR(base)
            if (
                base_document.sha256 != request.base_revision_hash
                or base["identity"]["component_id"] != request.component_id
            ):
                raise ValueError("Input proposal base binding is stale")
            if head is not None and (
                head["revision_id"] != request.base_revision_id
                or head["revision_hash"] != request.base_revision_hash
            ):
                raise StaleHeadError("Proposal base is not the current head")
            if head is None and base["revision"]["parent_id"] is not None:
                raise StaleHeadError("Initial review base must be a root")
            candidate = ComponentIR(candidate_revision)
            candidate_data = candidate.data
            if (
                candidate_data["revision"]["id"]
                != request.candidate_revision_id
                or candidate.sha256 != request.candidate_revision_hash
                or candidate_data["identity"]["component_id"]
                != request.component_id
            ):
                raise ValueError("Input proposal candidate binding is stale")
            transition_issues = validate_revision_transition(
                base, candidate_data
            )
            if transition_issues:
                raise ValueError("Invalid input proposal revision transition")
            self._require_review_only_transition(base, candidate_data)
            self._inventory_matches(candidate_data, request.inventory_sha256)
            stored = self.store.put_revision(
                candidate_data,
                inventory_sha256=request.inventory_sha256,
                reviewed=False,
            )
            proposal_id = str(uuid4())
            proposal_data = request.to_dict() | {"proposal_id": proposal_id}
            blob = canonical_json(proposal_data)
            digest = sha256(blob).hexdigest()
            now = _now()
            self.connection.execute(
                "INSERT INTO review_proposals VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal_id,
                    request.component_id,
                    request.base_revision_id,
                    request.base_revision_hash,
                    stored.revision_id,
                    stored.canonical_sha256,
                    request.expected_head_hash,
                    digest,
                    blob,
                    "PENDING",
                    now,
                    now,
                ),
            )
            return ProposalResult(
                proposal_id,
                digest,
                stored.revision_id,
                stored.canonical_sha256,
            )

    def _request_matches_proposal(
        self,
        row: sqlite3.Row,
        *,
        component_id: str,
        candidate_revision_id: str,
        candidate_revision_hash: str,
        expected_head_hash: str,
        inventory_sha256: str | None = None,
    ) -> dict:
        """@brief Verifies a decision request against proposal content.
        @param row Persisted proposal row.
        @param component_id Requested component identity.
        @param candidate_revision_id Requested candidate identity.
        @param candidate_revision_hash Requested candidate digest.
        @param expected_head_hash Requested current-head expectation.
        @param inventory_sha256 Requested inventory digest when approving.
        @return Parsed immutable proposal content.
        @details Decision requests cannot substitute any reviewed binding.
        """
        data = parse_json(bytes(row["canonical_bytes"]))
        expected = {
            "component_id": component_id,
            "candidate_revision_id": candidate_revision_id,
            "candidate_revision_hash": candidate_revision_hash,
            "expected_head_hash": expected_head_hash,
        }
        if any(data[key] != value for key, value in expected.items()):
            raise ValueError("Decision request does not match proposal")
        if (
            inventory_sha256 is not None
            and data["inventory_sha256"] != inventory_sha256
        ):
            raise ValueError("Decision inventory does not match proposal")
        return data

    def _record_event(
        self,
        proposal_id: str,
        decision: str,
        actor: str,
        reason: str,
        content: dict,
        timestamp: str,
    ) -> str:
        """@brief Appends one immutable input-review event.
        @param proposal_id Reviewed proposal identity.
        @param decision APPROVE or REJECT.
        @param actor Authenticated reviewer subject.
        @param reason Nonempty decision rationale.
        @param content Exact decision bindings and result content.
        @param timestamp Server-controlled event timestamp.
        @return New review-event identity.
        @details Event IDs and timestamps remain audit metadata.
        """
        event_id = str(uuid4())
        data = {
            "schema_version": "1.0",
            "event_id": event_id,
            "proposal_id": proposal_id,
            "stage": "INPUT",
            "decision": decision,
            "actor": actor,
            "reason": reason,
            "timestamp": timestamp,
            "content": content,
        }
        blob = canonical_json(data)
        digest = sha256(blob).hexdigest()
        self.connection.execute(
            "INSERT INTO review_events VALUES "
            "(?, ?, NULL, 'INPUT', ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                proposal_id,
                decision,
                actor,
                reason,
                digest,
                blob,
                timestamp,
                timestamp,
            ),
        )
        return event_id

    def _approved_revision(
        self,
        candidate: dict,
        proposal: dict,
        request: InputApprovalRequest,
        inventory: dict,
        timestamp: str,
    ) -> dict:
        """@brief Constructs the reviewed child for one accepted proposal.
        @param candidate Exact immutable proposal candidate.
        @param proposal Parsed immutable proposal content.
        @param request Authenticated exact approval request.
        @param inventory Verified acquisition inventory.
        @param timestamp Server-controlled approval timestamp.
        @return Complete reviewed child revision mapping.
        @details Pending override decisions remain unchanged; override approval
        appends a new APPROVED record with a new identity.
        """
        approved = copy.deepcopy(candidate)
        approved["revision"]["id"] = str(uuid4())
        approved["revision"]["parent_id"] = request.candidate_revision_id
        approved["revision"]["evidence_review"] = {
            "inventory_sha256": request.inventory_sha256,
            "reviewed_evidence_ids": list(inventory["evidence_ids"]),
            "reviewer": request.reviewer,
            "timestamp": timestamp,
            "approval_state": "APPROVED",
        }
        actions = proposal["actions"]
        if actions == ["EVIDENCE_REVIEW"]:
            return approved
        if actions != ["OVERRIDE_REPLACEMENT"]:
            raise ValueError("Unsupported input proposal action")
        pending = next(
            (
                record
                for record in approved["overrides"]
                if record["id"] == proposal["pending_override_id"]
            ),
            None,
        )
        if pending is None or pending["approval_state"] != "PENDING":
            raise ValueError("Pending override does not resolve")
        approved_record = copy.deepcopy(pending)
        approved_record["id"] = str(uuid4())
        approved_record["approval_state"] = "APPROVED"
        approved_record["user"] = request.reviewer
        approved_record["timestamp"] = timestamp
        new_value = copy.deepcopy(approved_record["new_value"])
        if isinstance(new_value, dict) and "status" in new_value:
            new_value["override_id"] = approved_record["id"]
            approved_record["new_value"] = copy.deepcopy(new_value)
        approved["overrides"].append(approved_record)
        self._replace_pointer(approved, approved_record["path"], new_value)
        active = approved["revision"]["active_override_ids"]
        prior_id = approved_record["supersedes_override_id"]
        approved["revision"]["active_override_ids"] = [
            override_id for override_id in active if override_id != prior_id
        ] + [approved_record["id"]]
        return approved

    def approve_inputs(
        self,
        request: InputApprovalRequest,
        principal: AuthenticatedPrincipal,
    ) -> RevisionResult:
        """@brief Approves one exact evidence-review proposal.
        @param request Exact proposal, candidate, inventory, and head bindings.
        @param principal Authenticated reviewer principal.
        @return Newly reviewed current revision and audit event identities.
        @details Revision insertion, event append, and head compare-and-swap
        occur atomically and never approve generated artifacts.
        """
        with _savepoint(self.connection, "input_review_approval"):
            principal.require_reviewer(request.reviewer)
            row = self._proposal(request.proposal_id, request.proposal_hash)
            self._request_matches_proposal(
                row,
                component_id=request.component_id,
                candidate_revision_id=request.candidate_revision_id,
                candidate_revision_hash=request.candidate_revision_hash,
                expected_head_hash=request.expected_head_hash,
                inventory_sha256=request.inventory_sha256,
            )
            head = self._require_expected_head(
                request.component_id, request.expected_head_hash
            )
            candidate = self.store.get_revision(request.candidate_revision_id)
            candidate_document = ComponentIR(candidate)
            if candidate_document.sha256 != request.candidate_revision_hash:
                raise ValueError("Candidate revision hash mismatch")
            inventory = self._inventory_matches(
                candidate, request.inventory_sha256
            )
            timestamp = _now()
            proposal = parse_json(bytes(row["canonical_bytes"]))
            approved = self._approved_revision(
                candidate,
                proposal,
                request,
                inventory,
                timestamp,
            )
            transition_issues = validate_revision_transition(
                candidate, approved
            )
            if transition_issues:
                raise ValueError("Approved revision transition is invalid")
            stored = self.store.put_revision(
                approved,
                inventory_sha256=request.inventory_sha256,
                reviewed=True,
            )
            event_id = self._record_event(
                request.proposal_id,
                "APPROVE",
                request.reviewer,
                request.reason,
                {
                    "candidate_revision_id": request.candidate_revision_id,
                    "candidate_revision_hash": (
                        request.candidate_revision_hash
                    ),
                    "approved_revision_id": stored.revision_id,
                    "approved_revision_hash": stored.canonical_sha256,
                    "inventory_sha256": request.inventory_sha256,
                },
                timestamp,
            )
            self.store.compare_and_swap_head(
                request.component_id,
                stored.revision_id,
                None if head is None else request.expected_head_hash,
            )
            return RevisionResult(
                stored.revision_id,
                stored.canonical_sha256,
                event_id,
            )

    def reject_inputs(
        self,
        request: InputRejectionRequest,
        principal: AuthenticatedPrincipal,
    ) -> InputReviewResult:
        """@brief Rejects one exact input-review proposal.
        @param request Exact proposal, candidate, and head bindings.
        @param principal Authenticated reviewer principal.
        @return Immutable rejection event identity.
        @details Rejection does not modify the candidate or component head.
        """
        with _savepoint(self.connection, "input_review_rejection"):
            principal.require_reviewer(request.reviewer)
            row = self._proposal(request.proposal_id, request.proposal_hash)
            self._request_matches_proposal(
                row,
                component_id=request.component_id,
                candidate_revision_id=request.candidate_revision_id,
                candidate_revision_hash=request.candidate_revision_hash,
                expected_head_hash=request.expected_head_hash,
            )
            self._require_expected_head(
                request.component_id, request.expected_head_hash
            )
            candidate = self.store.get_revision(request.candidate_revision_id)
            if (
                ComponentIR(candidate).sha256
                != request.candidate_revision_hash
            ):
                raise ValueError("Candidate revision hash mismatch")
            event_id = self._record_event(
                request.proposal_id,
                "REJECT",
                request.reviewer,
                request.reason,
                {
                    "candidate_revision_id": request.candidate_revision_id,
                    "candidate_revision_hash": (
                        request.candidate_revision_hash
                    ),
                },
                _now(),
            )
            return InputReviewResult(request.proposal_id, event_id, "REJECT")
