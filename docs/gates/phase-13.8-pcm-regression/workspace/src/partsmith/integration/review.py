"""@package partsmith.integration.review
@brief Records fresh authenticated decisions on exact integration content.
@details Imported approval objects and historical release decisions are data.
This service owns an idle-connection decision transaction and never commits
unrelated caller work. Post-commit cancellation/checkpoint errors are warnings.
"""

import platform
import sqlite3
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from partsmith.gui.identity import authenticated_principal
from partsmith.integration.bindings import (
    verify_audit_binding,
    verify_contract_bindings,
)
from partsmith.integration.contracts import (
    IntegrationAuditEnvelope,
    IntegrationAuthorizationBinding,
    IntegrationPlan,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.planner import PlanningResult
from partsmith.integration.sexpr import children, parse
from partsmith.integration.staging import Stager, StageResult
from partsmith.integration.store import IntegrationStore
from partsmith.ir.canonical import canonical_json
from partsmith.persistence.database import utc_timestamp
from partsmith.release.contracts import AuthenticatedPrincipal


@dataclass(frozen=True)
class DecisionResult:
    """@brief Reports a durable decision separately from operational warnings.
    @details AUTHORIZED never means files have been published.
    """

    outcome: str
    audit: IntegrationAuditEnvelope | None
    authorization: IntegrationAuthorizationBinding | None
    reused: bool = False
    warnings: tuple[str, ...] = ()


def authorization_for(staged: StageResult) -> IntegrationAuthorizationBinding:
    """@brief Constructs the exact content-only installation decision binding.
    @param staged Fully checked final proposed generation.
    @return Immutable authorization data awaiting a trusted decision.
    @details Constructing these bytes alone supplies no publication authority.
    """
    manifest = staged.manifest.data
    return IntegrationAuthorizationBinding(
        {
            "schema_version": "1.0",
            "plan_hash": staged.planning.plan.sha256,
            "installation_manifest_hash": staged.manifest.sha256,
            "target": manifest["target"],
            "expected_base": manifest["expected_base"],
            "required_checks": manifest["required_checks"],
            "post_manifest_check_hash": staged.post.sha256,
        }
    )


def current_base(
    connection: sqlite3.Connection,
    planning: PlanningResult,
    target: dict,
    root: Path,
) -> None:
    """@brief Rechecks the selected target and trusted current head.
    @param connection Authoritative current integration database.
    @param planning Exact frozen plan and whole-project snapshot.
    @param target Independently selected logical project/library scope.
    @param root Independently selected physical project root.
    @return None.
    @details A matching portable layout at another root cannot authorize it.
    """
    if target != planning.plan.data["target"] or (
        root.absolute() != planning.snapshot.root.absolute()
    ):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    from partsmith.integration.target import registered_root

    registered = registered_root(connection, target)
    if registered and registered.absolute() != root.absolute():
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    head = IntegrationStore(connection).head(target)
    if (head.sha256 if head else None) != planning.plan.data["expected_base"][
        "manifest_hash"
    ]:
        raise IntegrationError(FailureCode.STALE_BASE)
    planning.snapshot.recheck()


class IntegrationReview:
    """@brief Resolves fresh principals and commits deliberate exact decisions.
    @details A principal provider is a trusted live adapter dependency;
    it is never populated from session archives or request actor text.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        principal_provider: Callable = authenticated_principal,
        *,
        source_connection=None,
    ):
        """@brief Binds the review service to an idle application connection.
        @param connection Migrated authoritative application database.
        @param principal_provider Trusted live authentication adapter.
        @param source_connection Separate trusted component source catalog.
        @return None.
        @details Authentication is requested again for every actual decision.
        """
        self.connection = connection
        self.source_connection = source_connection or connection
        self.store = IntegrationStore(connection)
        self.principal_provider = principal_provider

    def inspect(
        self, attempt_id: str, staged: StageResult, *, target: dict, root: Path
    ) -> dict:
        """@brief Displays exact review bindings and mechanical differences.
        @param attempt_id Existing persisted integration attempt.
        @param staged Current proposed generation and immutable reports.
        @param target Independently selected logical target.
        @param root Independently selected physical project root.
        @return Detached review data with visible blocking categories.
        @details Inspection authenticates nobody and grants no authority.
        Stored passing checks stay labeled as bound evidence when stale.
        """
        row = self.connection.execute(
            "SELECT plan_hash, snapshot_hash FROM integration_attempts "
            "WHERE id=?",
            (attempt_id,),
        ).fetchone()
        if row is None or row[0] != staged.planning.plan.sha256:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        blocked = []
        try:
            if (
                row["snapshot_hash"]
                != sha256(
                    canonical_json(staged.planning.snapshot.document)
                ).hexdigest()
            ):
                raise IntegrationError(FailureCode.STALE_BASE)
            current_base(self.connection, staged.planning, target, root)
            staged.recheck()
            from partsmith.integration.staging import resolve_sources

            resolve_sources(
                self.source_connection,
                staged.planning.plan.data["sources"],
                staged.planning.sources,
            )
        except IntegrationError as error:
            blocked.append(error.code.value)
        differences = []
        for source, mapping in zip(
            staged.planning.sources,
            staged.manifest.data["mappings"],
            strict=True,
        ):
            artifacts = {
                role: (path, blob) for role, path, blob in source.artifacts
            }
            symbol = children(parse(artifacts["symbol"][1]), "symbol")[0]
            old_reference = next(
                (
                    p[2]
                    for p in children(symbol, "property")
                    if p[1] == "Footprint"
                ),
                None,
            )
            differences.append(
                {
                    "component_id": source.component_id,
                    "symbol_name": {
                        "source": symbol[1],
                        "installed": mapping["symbol_name"],
                    },
                    "footprint_name": {
                        "source": parse(artifacts["footprint"][1])[1],
                        "installed": mapping["footprint_name"],
                    },
                    "symbol_footprint_reference": {
                        "source": old_reference,
                        "installed": mapping["footprint_nickname"]
                        + ":"
                        + mapping["footprint_name"],
                    },
                    "model_uri": {
                        "source": artifacts["model_3d"][0],
                        "installed": "${KIPRJMOD}/" + mapping["model_path"],
                    },
                }
            )
        return {
            "schema_version": "partsmith-integration-review-view-1.0",
            "attempt_id": attempt_id,
            "plan_hash": staged.planning.plan.sha256,
            "manifest_hash": staged.manifest.sha256,
            "plan": staged.planning.plan.data,
            "manifest": staged.manifest.data,
            "pre_validation": staged.pre.data,
            "post_validation": staged.post.data,
            "mechanical_differences": differences,
            "blocking_codes": blocked,
            "review_required": True,
            "installation_authority": False,
        }

    def resolve(self, attempt_id: str, staged: StageResult) -> DecisionResult:
        """@brief Resolves one actual trusted approval and verifies its graph.
        @param attempt_id Existing exact integration attempt.
        @param staged Current hash-bound proposed generation.
        @return Existing immutable AUTHORIZED decision receipt.
        @details Raw imported binding/audit objects cannot supply this row.
        Publication must additionally recheck the current target and content.
        """
        row = self.connection.execute(
            "SELECT d.*, a.snapshot_hash FROM integration_decisions d "
            "JOIN integration_attempts a ON a.id=d.attempt_id "
            "WHERE d.attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if row is None or row["authorization_hash"] is None:
            raise IntegrationError(FailureCode.AUTHENTICATION_FAILED)
        if (
            row["snapshot_hash"]
            != sha256(
                canonical_json(staged.planning.snapshot.document)
            ).hexdigest()
        ):
            raise IntegrationError(FailureCode.STALE_BASE)
        audit = self.store.contract(
            row["audit_hash"], IntegrationAuditEnvelope
        )
        authorization = self.store.contract(
            row["authorization_hash"], IntegrationAuthorizationBinding
        )
        if authorization != authorization_for(staged):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        verify_contract_bindings(
            staged.planning.plan,
            staged.manifest,
            {staged.pre.sha256: staged.pre},
            staged.post,
            authorization,
            current_target=staged.planning.snapshot.target,
            current_base=staged.planning.plan.data["expected_base"],
            files=staged.recheck(),
        )
        verify_audit_binding(
            audit,
            staged.planning.plan,
            staged.manifest,
            authorization,
            staged.post,
            attempt_id=attempt_id,
        )
        if audit.data["execution"]["root"] != str(
            staged.planning.snapshot.root.absolute()
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        return DecisionResult("AUTHORIZED", audit, authorization, reused=True)

    def _cancel(self, attempt_id: str) -> DecisionResult:
        """@brief Commits a pre-decision cancellation event without authority.
        @param attempt_id Exact existing planned attempt.
        @return Durable CANCELLED operational result.
        @details Existing decisions are resolved before this method is called.
        """
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.store.event(attempt_id, "CANCELLED")
            self.connection.commit()
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
        return DecisionResult("CANCELLED", None, None)

    def decide(
        self,
        attempt_id: str,
        content: StageResult | PlanningResult,
        decision: str,
        reason: str,
        *,
        target: dict,
        root: Path,
        reviewer: str | None = None,
        cancel=None,
        checkpoint: Callable | None = None,
    ) -> DecisionResult:
        """@brief Commits deliberate decisions and resolves exact retries.
        @param attempt_id Exact already persisted planned attempt.
        @param content Checked stage for approval; plan or stage for rejection.
        @param decision Explicit APPROVE or REJECT action.
        @param reason Nonempty deliberate reviewer explanation.
        @param target Independently selected current target identity.
        @param root Independently selected current physical target root.
        @param reviewer Optional subject that must match fresh authentication.
        @param cancel Optional cooperative cancellation event.
        @param checkpoint Optional post-commit operational checkpoint callback.
        @return Durable truthful decision with separate warnings.
        @details Refuses busy caller transactions, stale/changed content and
        incomplete approval. A committed decision survives late cancellation.
        """
        if self.connection.in_transaction:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        if (
            decision not in {"APPROVE", "REJECT"}
            or not isinstance(reason, str)
            or (not reason.strip() or len(reason) > 4096)
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        reason = unicodedata.normalize("NFC", reason)
        staged = content if isinstance(content, StageResult) else None
        planning = staged.planning if staged else content
        if not isinstance(planning, PlanningResult):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        row = self.connection.execute(
            "SELECT plan_hash, snapshot_hash FROM integration_attempts "
            "WHERE id=?",
            (attempt_id,),
        ).fetchone()
        if (
            row is None
            or row[0] != planning.plan.sha256
            or self.store.contract(row[0], IntegrationPlan) != planning.plan
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        if (
            row["snapshot_hash"]
            != sha256(canonical_json(planning.snapshot.document)).hexdigest()
        ):
            raise IntegrationError(FailureCode.STALE_BASE)
        existing = self.connection.execute(
            "SELECT * FROM integration_decisions WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if cancel is not None and cancel.is_set() and existing is None:
            return self._cancel(attempt_id)
        try:
            principal = self.principal_provider()
            if not isinstance(principal, AuthenticatedPrincipal):
                raise PermissionError("Fresh principal unavailable")
            principal.require_reviewer(reviewer or principal.subject)
        except (PermissionError, OSError, ValueError) as error:
            raise IntegrationError(
                FailureCode.AUTHENTICATION_FAILED
            ) from error
        current_base(self.connection, planning, target, root)
        authorization = None
        if decision == "APPROVE":
            if staged is None:
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            stage_event = self.connection.execute(
                "SELECT 1 FROM integration_events WHERE attempt_id=? "
                "AND state='STAGED' AND object_hash=?",
                (attempt_id, staged.manifest.sha256),
            ).fetchone()
            if stage_event is None:
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            Stager(self.connection, self.source_connection).revalidate(staged)
            authorization = authorization_for(staged)
            verify_contract_bindings(
                planning.plan,
                staged.manifest,
                {staged.pre.sha256: staged.pre},
                staged.post,
                authorization,
                current_target=target,
                current_base=planning.plan.data["expected_base"],
                files=staged.recheck(),
            )
        references = {
            "plan_hash": planning.plan.sha256,
            "manifest_hash": staged.manifest.sha256 if staged else None,
            "authorization_hash": authorization.sha256
            if authorization
            else None,
            "check_hashes": sorted({staged.pre.sha256, staged.post.sha256})
            if staged
            else [],
        }
        if existing:
            audit = self.store.contract(
                existing["audit_hash"], IntegrationAuditEnvelope
            )
            if audit.data["references"] != references or (
                audit.data["decision"],
                audit.data["reason"],
                audit.data["authenticated_subject"],
            ) != (decision, reason, principal.subject):
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            result = (
                self.resolve(attempt_id, staged)
                if authorization
                else DecisionResult("REJECTED", audit, None, reused=True)
            )
            if cancel is not None and cancel.is_set():
                return DecisionResult(
                    result.outcome,
                    result.audit,
                    result.authorization,
                    reused=True,
                    warnings=("LATE_CANCEL_AFTER_DECISION",),
                )
            return result
        if cancel is not None and cancel.is_set():
            return self._cancel(attempt_id)
        outcome = "AUTHORIZED" if authorization else "REJECTED"
        audit = None
        warnings = []
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            current_base(self.connection, planning, target, root)
            sequence = self.connection.execute(
                "SELECT count(*) + 1 FROM integration_events "
                "WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()[0]
            audit = IntegrationAuditEnvelope(
                {
                    "schema_version": "1.0",
                    "event_id": str(uuid4()),
                    "attempt_id": attempt_id,
                    "sequence": sequence,
                    "authenticated_subject": principal.subject,
                    "authentication_mechanism": principal.mechanism,
                    "timestamp": utc_timestamp().replace("+00:00", "Z"),
                    "decision": decision,
                    "reason": reason,
                    "outcome": outcome,
                    "target": target,
                    "references": references,
                    "execution": {
                        "root": str(root.absolute()),
                        "staging_root": str(staged.root.absolute())
                        if staged
                        else None,
                        "runtime_id": "python-" + platform.python_version(),
                    },
                }
            )
            authorization_hash = (
                self.store.put_contract(authorization)
                if authorization
                else None
            )
            audit_hash = self.store.put_contract(audit)
            if authorization_hash:
                self.store.reference(
                    authorization_hash,
                    (
                        planning.plan.sha256,
                        staged.manifest.sha256,
                        staged.pre.sha256,
                        staged.post.sha256,
                    ),
                )
            self.store.reference(
                audit_hash,
                tuple(
                    digest
                    for digest in (
                        planning.plan.sha256,
                        references["manifest_hash"],
                        authorization_hash,
                    )
                    if digest is not None
                ),
            )
            self.connection.execute(
                "INSERT INTO integration_decisions VALUES (?, ?, ?, ?)",
                (attempt_id, audit_hash, authorization_hash, utc_timestamp()),
            )
            self.store.event(attempt_id, outcome, audit_hash)
            current_base(self.connection, planning, target, root)
            if cancel is not None and cancel.is_set():
                self.connection.rollback()
                return self._cancel(attempt_id)
            self.connection.commit()
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
                raise
            # A driver may raise after its actual COMMIT completed. Resolve
            # the exact trusted row before reporting a failure to the caller.
            committed = (
                self.connection.execute(
                    "SELECT audit_hash FROM integration_decisions "
                    "WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                if audit is not None
                else None
            )
            if committed is None or committed[0] != audit.sha256:
                raise
            warnings.append("COMMIT_DRIVER_ERROR_AFTER_DECISION")
        if checkpoint:
            try:
                checkpoint(audit.sha256)
            except Exception:
                warnings.append("CHECKPOINT_WRITE_FAILED_AFTER_DECISION")
        if cancel is not None and cancel.is_set():
            warnings.append("LATE_CANCEL_AFTER_DECISION")
        return DecisionResult(
            outcome, audit, authorization, warnings=tuple(warnings)
        )
