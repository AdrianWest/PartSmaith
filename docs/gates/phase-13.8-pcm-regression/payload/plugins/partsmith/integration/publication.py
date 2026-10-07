"""@package partsmith.integration.publication
@brief Publishes one verified complete owned NTFS generation and reconciles
gaps.
@details One junction payload replacement is the publication boundary. Journal,
physical execution intent and slots are durable before it; SQLite head/receipt
follow verified readback. Outcomes distinguish filesystem commit from recovery.
"""

import re
import shutil
import sqlite3
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from partsmith.gui.identity import authenticated_principal
from partsmith.integration.atomic_target import junction_buffer
from partsmith.integration.bindings import (
    verify_audit_binding,
    verify_contract_bindings,
    verify_files,
    verify_journal_binding,
)
from partsmith.integration.contracts import (
    InstallationManifest,
    IntegrationAuditEnvelope,
    IntegrationAuthorizationBinding,
    IntegrationJournal,
    IntegrationPlan,
    IntegrationValidationReport,
    _files,
    _ordered,
    _paths,
    portable_path,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.planner import (
    Planner,
    PlanningResult,
    file_inventory,
    read_project,
    snapshot_target,
)
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.review import IntegrationReview, current_base
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.staging import (
    Stager,
    StageResult,
    verify_project_references,
    whole_generation,
)
from partsmith.integration.store import IntegrationStore
from partsmith.integration.target import OwnedTarget, write_slot
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence.database import utc_timestamp
from partsmith.release.contracts import AuthenticatedPrincipal

STRATEGY = "ntfs-owned-whole-project-junction-1.0"
QUIESCENCE = "explicit-closed-exclusive-project-1.0"


@dataclass(frozen=True)
class PublicationResult:
    """@brief Reports actual filesystem/SQLite outcomes without false failure.
    @details A true committed flag means the complete new boundary was read
    back;
    RECOVERY_REQUIRED retains the journal and prior complete physical slot.
    """

    outcome: str
    committed: bool
    receipt_hash: str | None = None
    reused: bool = False
    warnings: tuple[str, ...] = ()


def checkpoint(callback: Callable | None, name: str) -> None:
    """@brief Invokes one explicitly injected operational fault checkpoint.
    @param callback Trusted test/operational hook, or None in normal execution.
    @param name Closed phase boundary identifier.
    @return None.
    @details Hooks cannot become installation authority or replace validation.
    """
    if callback is not None:
        callback(name)


def verify_intent(
    intent: dict, owned: OwnedTarget, journal: IntegrationJournal
) -> None:
    """@brief Verifies physical intent, journal and ownership.
    @param intent Stored versioned operational publication document.
    @param owned Independently resolved current registered target.
    @param journal Exact trusted persisted logical publication journal.
    @return None.
    @details Physical slots are UUID names independent of manifest identities.
    Imported markers/intent objects alone grant no switch permission.
    """
    if (
        set(intent)
        != {
            "schema_version",
            "owner",
            "target",
            "attempt_id",
            "journal_hash",
            "old_slot",
            "new_slot",
            "old_slot_identity",
            "new_slot_identity",
            "old_payload_sha256",
            "new_payload_sha256",
            "whole_files",
            "directories",
            "previous_manifest_hash",
            "new_manifest_hash",
            "rollback_origin",
            "publication_strategy",
            "quiescence_policy",
        }
        or intent["schema_version"] != "partsmith-publication-intent-1.0"
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    if (
        intent["owner"],
        intent["target"],
        intent["attempt_id"],
        intent["journal_hash"],
        intent["new_manifest_hash"],
        intent["previous_manifest_hash"],
        intent["publication_strategy"],
    ) != (
        owned.metadata["owner"],
        owned.target,
        journal.data["attempt_id"],
        journal.sha256,
        journal.data["new_manifest_hash"],
        journal.data["expected_base"]["manifest_hash"],
        STRATEGY,
    ):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    for prefix in ("old", "new"):
        root = Path(intent[prefix + "_slot"])
        if root.parent != owned.workspace / "slots" or not (
            re.fullmatch(r"slot-[0-9a-f]{32}", root.name)
        ):
            raise IntegrationError(FailureCode.PATH_CONFLICT)
        if (
            sha256(junction_buffer(root)).hexdigest()
            != intent[prefix + "_payload_sha256"]
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        with owned.api.directory(root) as handle:
            if (
                list(owned.api.identity(handle))
                != intent[prefix + "_slot_identity"]
            ):
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
    if (
        intent["old_slot"] == intent["new_slot"]
        or intent["new_slot"] != journal.data["owned_staging_root"]
        or intent["quiescence_policy"] != QUIESCENCE
    ):
        raise IntegrationError(FailureCode.INVALID_CONTRACT)
    try:
        _files(intent["whole_files"])
        _ordered(intent["directories"])
        ResourcePolicy().require_sizes([0] * len(intent["directories"]))
        for directory in intent["directories"]:
            portable_path(directory)
        _paths(
            [i["path"] for i in intent["whole_files"]]
            + [d + "/.directory" for d in intent["directories"]]
        )
        for item in intent["whole_files"]:
            if set(item) != {"path", "sha256", "byte_length"} or not (
                re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            ):
                raise ValueError("Whole file identity")
    except (ValueError, TypeError, KeyError) as error:
        raise IntegrationError(FailureCode.INVALID_CONTRACT) from error


def verify_generation(root: Path, inventory: list, directories: list) -> None:
    """@brief Verifies every complete file and directory in a candidate.
    @param root Ordinary isolated complete generation directory.
    @param inventory Exact bounded complete file identities.
    @param directories Exact ordered complete directory paths.
    @return None.
    @details Unknown additions, changed bytes and missing empty folders fail.
    """
    objects, actual_directories = read_project(root)
    verify_files(inventory, objects)
    if list(actual_directories) != list(directories):
        raise IntegrationError(FailureCode.STALE_BASE)


def discard_candidate(owned: OwnedTarget, root: Path) -> None:
    """@brief Cleans one verified unselected owned candidate generation.
    @param owned Locked registered target whose boundary is still old.
    @param root Exact newly allocated candidate beneath its ordinary slots.
    @return None.
    @details Never follows reparse directories or deletes a selected slot.
    """
    if (
        root.parent != owned.workspace / "slots"
        or not re.fullmatch(r"slot-[0-9a-f]{32}", root.name)
        or root == owned.current()
    ):
        raise IntegrationError(FailureCode.TARGET_CONFLICT)
    read_project(root)
    shutil.rmtree(root)


def discard_stage(staged: StageResult) -> None:
    """@brief Cleans the exact verified isolated stage on cancellation.
    @param staged Service-created stage being deliberately cancelled.
    @return None.
    @details Containment, ordinary paths and exact bytes are checked first.
    Original projects, selected slots and imported directories are excluded.
    """
    from partsmith.integration.atomic_target import _ordinary_ancestors

    root = staged.root.absolute()
    if (
        not re.fullmatch(r"stage-[a-z0-9_]{8}", root.name)
        or root == staged.planning.snapshot.root.absolute()
        or root in staged.planning.snapshot.root.absolute().parents
    ):
        raise IntegrationError(FailureCode.PATH_CONFLICT)
    _ordinary_ancestors(root)
    staged.recheck()
    shutil.rmtree(root)


class Publisher:
    """@brief Publishes complete generations and reconciles crashes.
    @details Acts only on registered local NTFS managed copies after a fresh
    closed/exclusive-editor confirmation and matching current authentication.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        principal_provider: Callable = authenticated_principal,
        *,
        source_connection=None,
    ):
        """@brief Binds the trusted store and authentication adapter.
        @param connection Idle authoritative migrated integration database.
        @param principal_provider Trusted fresh live authentication adapter.
        @param source_connection Separate trusted component source catalog.
        @return None.
        @details Never derives a principal from saved audit/GUI actor text.
        """
        self.connection = connection
        self.source_connection = source_connection or connection
        self.store = IntegrationStore(connection)
        self.principal_provider = principal_provider

    def _principal(self, subject: str) -> None:
        """@brief Requires a live subject matching the actual decision.
        @param subject Previously trusted authenticated audit subject.
        @return None.
        @details Session import or a supplied display label cannot
        authenticate.
        """
        try:
            actual = self.principal_provider()
            if not isinstance(actual, AuthenticatedPrincipal):
                raise PermissionError("Fresh principal unavailable")
            actual.require_reviewer(subject)
        except (PermissionError, OSError, ValueError) as error:
            raise IntegrationError(
                FailureCode.AUTHENTICATION_FAILED
            ) from error

    def _event(
        self, attempt: str, state: str, identity: str | None = None
    ) -> None:
        """@brief Commits a truthful event after an operational boundary.
        @param attempt Actual persisted attempt ID.
        @param state Actual operation state.
        @param identity Optional immutable supporting journal/receipt identity.
        @return None.
        @details Caller must be idle; partial event writes are rolled back.
        """
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.store.event(attempt, state, identity)
            self.connection.commit()
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise

    def rollback_plan(
        self, owned: OwnedTarget, origin: str | None
    ) -> PlanningResult:
        """@brief Plans fresh restoration of a trusted historical source set.
        @param owned Exact current registered managed project.
        @param origin Prior committed manifest, or None for initial tables.
        @return New plan against the current base, without authorization.
        @details Historical slots and decisions are never reused to publish.
        Mutable project files come from the current project snapshot.
        """
        self._rollback_sources(owned, origin)
        historical = (
            self.store.contract(origin, InstallationManifest)
            if origin
            else None
        )
        builds = tuple(
            parse_json(
                self.store.get(s["release_approval_hash"], "source_approval")
            )["build_id"]
            for s in (historical.data["sources"] if historical else [])
        )
        return Planner(self.connection, self.source_connection).plan(
            owned.current(), owned.target, builds
        )

    def _rollback_sources(
        self, owned: OwnedTarget, origin: str | None
    ) -> list:
        """@brief Requires rollback origin on this target's committed ancestry.
        @param owned Exact registered current target.
        @param origin Historical manifest or initial generation identity.
        @return Historical complete approved source declarations.
        @details Raw imported manifests cannot establish publication history.
        """
        head = self.store.head(owned.target)
        if head is None or origin == head.sha256:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        seen = set()
        current = head.sha256
        while current is not None and current not in seen:
            seen.add(current)
            row = self.connection.execute(
                "SELECT p.receipt_hash FROM integration_publications p "
                "JOIN integration_attempts a ON a.id=p.attempt_id "
                "WHERE a.project_id=? AND p.manifest_hash=? "
                "ORDER BY p.rowid DESC LIMIT 1",
                (owned.target["project_id"], current),
            ).fetchone()
            if row is None:
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            receipt = parse_json(self.store.get(row[0], "publication_receipt"))
            current = receipt["previous_manifest_hash"]
            if current == origin:
                return (
                    self.store.contract(origin, InstallationManifest).data[
                        "sources"
                    ]
                    if origin
                    else []
                )
        raise IntegrationError(FailureCode.INVALID_CONTRACT)

    def _finish(
        self,
        attempt: str,
        journal: IntegrationJournal,
        intent: dict,
        manifest: InstallationManifest,
    ) -> str:
        """@brief CAS-updates the exact head and stores one immutable receipt.
        @param attempt Exact persisted approved attempt.
        @param journal Durable pre-switch publication journal.
        @param intent Verified physical execution intent.
        @param manifest Exact complete selected installed generation.
        @return Durable immutable publication receipt identity.
        @details A transaction failure after the switch leaves recovery work;
        it does not imply the old filesystem generation stayed active.
        """
        prior = self.connection.execute(
            "SELECT receipt_hash, manifest_hash FROM integration_publications "
            "WHERE attempt_id=?",
            (attempt,),
        ).fetchone()
        if prior:
            if prior["manifest_hash"] != manifest.sha256:
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            return prior["receipt_hash"]
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            cursor = self.connection.execute(
                "UPDATE integration_heads SET manifest_hash=? "
                "WHERE project_id=? AND manifest_hash IS ?",
                (
                    manifest.sha256,
                    intent["target"]["project_id"],
                    intent["previous_manifest_hash"],
                ),
            )
            if cursor.rowcount != 1:
                raise IntegrationError(FailureCode.STALE_BASE)
            receipt = {
                "schema_version": "partsmith-publication-receipt-1.0",
                "attempt_id": attempt,
                "target": intent["target"],
                "journal_hash": journal.sha256,
                "manifest_hash": manifest.sha256,
                "previous_manifest_hash": intent["previous_manifest_hash"],
                "physical_slot": intent["new_slot"],
                "physical_slot_identity": intent["new_slot_identity"],
                "intent": journal.data["intent"],
                "rollback_origin": intent["rollback_origin"],
                "outcome": "COMMITTED",
                "timestamp": utc_timestamp(),
            }
            identity = self.store.put(
                "publication_receipt", canonical_json(receipt)
            )
            self.store.reference(identity, (journal.sha256, manifest.sha256))
            self.connection.execute(
                "INSERT INTO integration_publications VALUES (?, ?, ?, ?, ?)",
                (
                    attempt,
                    journal.sha256,
                    manifest.sha256,
                    identity,
                    utc_timestamp(),
                ),
            )
            self.store.event(attempt, "COMMITTED", identity)
            if journal.data["intent"] == "ROLLBACK":
                self.store.event(attempt, "ROLLED_BACK", identity)
            self.connection.commit()
            return identity
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
            else:
                actual = self.connection.execute(
                    "SELECT receipt_hash, manifest_hash "
                    "FROM integration_publications WHERE attempt_id=?",
                    (attempt,),
                ).fetchone()
                if actual and actual["manifest_hash"] == manifest.sha256:
                    self.store.get(
                        actual["receipt_hash"], "publication_receipt"
                    )
                    return actual["receipt_hash"]
            raise

    def publish(
        self,
        attempt: str,
        staged: StageResult,
        owned: OwnedTarget,
        closed: ClosedProject,
        *,
        cancel=None,
        intent: str = "PUBLISH",
        rollback_origin: str | None = None,
        fault: Callable | None = None,
    ) -> PublicationResult:
        """@brief Publishes approved files and retains failed attempt history.
        @param attempt Exact saved and reviewed attempt.
        @param staged Verified service-created isolated generation.
        @param owned Registered native managed project.
        @param closed Fresh explicit writer exclusion confirmation.
        @param cancel Optional cooperative cancellation signal.
        @param intent Deliberate PUBLISH or ROLLBACK operation.
        @param rollback_origin Trusted historical manifest or initial state.
        @param fault Optional trusted operational fault injection.
        @return Truthful filesystem and database publication outcome.
        @details Never commits or rolls back a caller's unrelated transaction.
        Prepared uncertain outcomes remain available for explicit recovery.
        """
        busy = self.connection.in_transaction
        try:
            return self._publish(
                attempt,
                staged,
                owned,
                closed,
                cancel=cancel,
                intent=intent,
                rollback_origin=rollback_origin,
                fault=fault,
            )
        except BaseException:
            if not busy and not self.connection.in_transaction:
                latest = self.connection.execute(
                    "SELECT state FROM integration_events WHERE attempt_id=? "
                    "ORDER BY sequence DESC LIMIT 1",
                    (attempt,),
                ).fetchone()
                if latest and latest[0] not in {
                    "PREPARED",
                    "RECOVERY_REQUIRED",
                    "COMMITTED",
                    "ROLLED_BACK",
                    "CANCELLED",
                    "FAILED",
                }:
                    try:
                        self._event(attempt, "FAILED")
                    except Exception:
                        pass
            raise

    def _publish(
        self,
        attempt: str,
        staged: StageResult,
        owned: OwnedTarget,
        closed: ClosedProject,
        *,
        cancel=None,
        intent: str = "PUBLISH",
        rollback_origin: str | None = None,
        fault: Callable | None = None,
    ) -> PublicationResult:
        """@brief Publishes approved complete files through one NTFS switch.
        @param attempt Exact persisted stage/decision attempt.
        @param staged Exact previously approved complete generation.
        @param owned Independently registered selected managed target.
        @param closed Fresh explicit saved/closed/exclusive-writer
        confirmation.
        @param cancel Optional cooperative cancellation signal.
        @param intent PUBLISH or deliberately reviewed ROLLBACK operation.
        @param rollback_origin Historical manifest for a fresh rollback plan.
        @param fault Optional trusted fault-injection checkpoint callback.
        @return Actual committed/cancelled/recovery outcome.
        @details Old slots remain complete; no sequential file replacement is
        called atomic. Cancellation after the boundary resolves its real
        result.
        """
        if self.connection.in_transaction or intent not in {
            "PUBLISH",
            "ROLLBACK",
        }:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        prior = self.connection.execute(
            "SELECT receipt_hash, manifest_hash FROM integration_publications "
            "WHERE attempt_id=?",
            (attempt,),
        ).fetchone()
        if prior:
            receipt = parse_json(
                self.store.get(prior["receipt_hash"], "publication_receipt")
            )
            if (
                prior["manifest_hash"] != staged.manifest.sha256
                or receipt["target"] != owned.target
            ):
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
            row = self.connection.execute(
                "SELECT audit_hash FROM integration_decisions "
                "WHERE attempt_id=?",
                (attempt,),
            ).fetchone()
            audit = self.store.contract(row[0], IntegrationAuditEnvelope)
            self._principal(audit.data["authenticated_subject"])
            head = self.store.head(owned.target)
            return PublicationResult(
                "COMMITTED",
                True,
                prior["receipt_hash"],
                reused=True,
                warnings=("HISTORICAL_RECEIPT_TARGET_ADVANCED",)
                if head is None or head.sha256 != prior["manifest_hash"]
                else (),
            )
        owned.require_reconciled()
        if staged.planning.plan.data["target"] != owned.target:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        if intent == "ROLLBACK":
            if staged.manifest.data["sources"] != self._rollback_sources(
                owned, rollback_origin
            ):
                raise IntegrationError(FailureCode.INVALID_CONTRACT)
        elif rollback_origin is not None:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        self.connection.execute("PRAGMA synchronous=FULL")
        review = IntegrationReview(
            self.connection,
            self.principal_provider,
            source_connection=self.source_connection,
        )
        decision = review.resolve(attempt, staged)
        self._principal(decision.audit.data["authenticated_subject"])
        if cancel is not None and cancel.is_set():
            discard_stage(staged)
            self._event(attempt, "CANCELLED")
            return PublicationResult("CANCELLED", False)
        checkpoint(fault, "before_lock")
        journal, operation = None, None
        with owned.lock(closed) as (boundary, current):
            current_base(
                self.connection, staged.planning, owned.target, current
            )
            Stager(self.connection, self.source_connection).revalidate(staged)
            closed.require(owned.target)
            originals, _ = read_project(current)
            with owned.freeze_files(current, originals), ExitStack() as leases:
                staged.planning.snapshot.recheck()
                managed = staged.recheck()
                whole, directories = whole_generation(staged.planning, managed)
                new = owned.workspace / "slots" / ("slot-" + uuid4().hex)
                checkpoint(fault, "before_slot_write")
                write_slot(new, whole, directories)
                leases.enter_context(owned.freeze_files(new, whole))
                checkpoint(fault, "after_slot_write")
                with owned.api.directory(current) as handle:
                    old_identity = list(owned.api.identity(handle))
                with owned.api.directory(new) as handle:
                    new_identity = list(owned.api.identity(handle))
                journal = IntegrationJournal(
                    {
                        "schema_version": "1.0",
                        "attempt_id": attempt,
                        "target": owned.target,
                        "expected_base": staged.planning.plan.data[
                            "expected_base"
                        ],
                        "plan_hash": staged.planning.plan.sha256,
                        "new_manifest_hash": staged.manifest.sha256,
                        "new_generation_hash": staged.manifest.sha256,
                        "authorization_hash": decision.authorization.sha256,
                        "required_checks": staged.manifest.data[
                            "required_checks"
                        ],
                        "post_manifest_check_hash": staged.post.sha256,
                        "owned_staging_root": str(new),
                        "publication_strategy": STRATEGY,
                        "intent": intent,
                        "state": "PREPARED",
                    }
                )
                verify_journal_binding(
                    journal,
                    staged.planning.plan,
                    staged.manifest,
                    decision.authorization,
                )
                operation = {
                    "schema_version": "partsmith-publication-intent-1.0",
                    "owner": owned.metadata["owner"],
                    "target": owned.target,
                    "attempt_id": attempt,
                    "journal_hash": journal.sha256,
                    "old_slot": str(current),
                    "new_slot": str(new),
                    "old_slot_identity": old_identity,
                    "new_slot_identity": new_identity,
                    "old_payload_sha256": sha256(
                        junction_buffer(current)
                    ).hexdigest(),
                    "new_payload_sha256": sha256(
                        junction_buffer(new)
                    ).hexdigest(),
                    "whole_files": file_inventory(whole),
                    "directories": list(directories),
                    "previous_manifest_hash": staged.planning.plan.data[
                        "expected_base"
                    ]["manifest_hash"],
                    "new_manifest_hash": staged.manifest.sha256,
                    "rollback_origin": rollback_origin,
                    "publication_strategy": STRATEGY,
                    "quiescence_policy": QUIESCENCE,
                }
                verify_intent(operation, owned, journal)
                try:
                    self.connection.execute("BEGIN IMMEDIATE")
                    current_base(
                        self.connection, staged.planning, owned.target, current
                    )
                    journal_hash = self.store.put_contract(journal)
                    operation_hash = self.store.put(
                        "execution_intent", canonical_json(operation)
                    )
                    self.store.reference(
                        journal_hash,
                        (
                            operation_hash,
                            decision.authorization.sha256,
                            staged.manifest.sha256,
                        ),
                    )
                    self.store.event(attempt, "PREPARED", journal_hash)
                    self.connection.commit()
                except BaseException:
                    if self.connection.in_transaction:
                        self.connection.rollback()
                    raise
                try:
                    checkpoint(fault, "after_prepare")
                    staged.planning.snapshot.recheck()
                    verify_generation(new, file_inventory(whole), directories)
                    closed.require(owned.target)
                    if cancel is not None and cancel.is_set():
                        self._event(attempt, "CANCELLED", journal.sha256)
                        leases.close()
                        discard_candidate(owned, new)
                        discard_stage(staged)
                        return PublicationResult("CANCELLED", False)
                    if owned.api.reparse(boundary) != junction_buffer(current):
                        raise IntegrationError(FailureCode.STALE_BASE)
                    checkpoint(fault, "before_switch")
                    staged.planning.snapshot.recheck()
                    closed.require(owned.target)
                    if cancel is not None and cancel.is_set():
                        self._event(attempt, "CANCELLED", journal.sha256)
                        leases.close()
                        discard_candidate(owned, new)
                        discard_stage(staged)
                        return PublicationResult("CANCELLED", False)
                    owned.api.reparse(boundary, junction_buffer(new))
                    checkpoint(fault, "after_switch")
                    if owned.api.reparse(boundary) != junction_buffer(new):
                        raise IntegrationError(FailureCode.RECOVERY_REQUIRED)
                    verify_generation(
                        new, operation["whole_files"], operation["directories"]
                    )
                    checkpoint(fault, "before_receipt")
                    receipt = self._finish(
                        attempt, journal, operation, staged.manifest
                    )
                    warnings = []
                    if cancel is not None and cancel.is_set():
                        warnings.append("LATE_CANCEL_AFTER_PUBLICATION")
                    try:
                        checkpoint(fault, "after_receipt")
                    except Exception:
                        warnings.append("CHECKPOINT_FAILED_AFTER_PUBLICATION")
                    return PublicationResult(
                        "COMMITTED", True, receipt, warnings=tuple(warnings)
                    )
                except BaseException:
                    if self.connection.in_transaction:
                        self.connection.rollback()
                    payload = owned.api.reparse(boundary)
                    committed = payload == junction_buffer(new)
                    if committed:
                        try:
                            self._event(
                                attempt, "RECOVERY_REQUIRED", journal.sha256
                            )
                        except Exception:
                            pass
                        return PublicationResult(
                            "RECOVERY_REQUIRED",
                            True,
                            warnings=("FILESYSTEM_COMMITTED_RECEIPT_PENDING",),
                        )
                    if payload == junction_buffer(current):
                        self._event(attempt, "FAILED", journal.sha256)
                        raise IntegrationError(
                            FailureCode.PUBLICATION_FAILED
                        ) from None
                    return PublicationResult(
                        "RECOVERY_REQUIRED",
                        False,
                        warnings=("PUBLICATION_SELECTION_UNRESOLVED",),
                    )

    def recover(
        self, attempt: str, owned: OwnedTarget, closed: ClosedProject
    ) -> PublicationResult:
        """@brief Reconciles the recorded selection after restart.
        @param attempt Exact unfinished trusted publication attempt.
        @param owned Independently verified registered target ownership.
        @param closed Fresh explicit closed/exclusive-writer confirmation.
        @return Truthful old-state failure or completed new-state receipt.
        @details Never switches automatically. Unknown/tampered states remain
        blocked and preserved; current unrelated mutable files are retained.
        """
        if self.connection.in_transaction:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        actual = self.connection.execute(
            "SELECT receipt_hash FROM integration_publications "
            "WHERE attempt_id=?",
            (attempt,),
        ).fetchone()
        if actual:
            receipt = parse_json(
                self.store.get(actual[0], "publication_receipt")
            )
            if receipt["target"] != owned.target:
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            decision = self.connection.execute(
                "SELECT audit_hash FROM integration_decisions "
                "WHERE attempt_id=?",
                (attempt,),
            ).fetchone()
            audit = self.store.contract(decision[0], IntegrationAuditEnvelope)
            self._principal(audit.data["authenticated_subject"])
            return PublicationResult("COMMITTED", True, actual[0], reused=True)
        state = self.connection.execute(
            "SELECT state FROM integration_events WHERE attempt_id=? "
            "ORDER BY sequence DESC LIMIT 1",
            (attempt,),
        ).fetchone()
        if state is None or state[0] not in {"PREPARED", "RECOVERY_REQUIRED"}:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        row = self.connection.execute(
            "SELECT object_hash FROM integration_events WHERE attempt_id=? "
            "AND state='PREPARED' ORDER BY sequence DESC LIMIT 1",
            (attempt,),
        ).fetchone()
        if row is None:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        journal = self.store.contract(row[0], IntegrationJournal)
        children = self.connection.execute(
            "SELECT child_hash FROM integration_object_refs r "
            "JOIN integration_objects o ON o.sha256=r.child_hash "
            "WHERE r.owner_hash=? AND o.kind='execution_intent'",
            (journal.sha256,),
        ).fetchall()
        if len(children) != 1:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        operation = parse_json(
            self.store.get(children[0][0], "execution_intent")
        )
        verify_intent(operation, owned, journal)
        manifest = self.store.contract(
            journal.data["new_manifest_hash"], InstallationManifest
        )
        plan = self.store.contract(journal.data["plan_hash"], IntegrationPlan)
        authorization = self.store.contract(
            journal.data["authorization_hash"], IntegrationAuthorizationBinding
        )
        verify_journal_binding(journal, plan, manifest, authorization)
        decision = self.connection.execute(
            "SELECT authorization_hash, audit_hash "
            "FROM integration_decisions WHERE attempt_id=?",
            (attempt,),
        ).fetchone()
        if decision is None or decision[0] != authorization.sha256:
            raise IntegrationError(FailureCode.AUTHENTICATION_FAILED)
        audit = self.store.contract(decision[1], IntegrationAuditEnvelope)
        post = self.store.contract(
            journal.data["post_manifest_check_hash"],
            IntegrationValidationReport,
        )
        pre = {
            item["report_hash"]: self.store.contract(
                item["report_hash"], IntegrationValidationReport
            )
            for item in manifest.data["required_checks"]
        }
        verify_audit_binding(
            audit, plan, manifest, authorization, post, attempt_id=attempt
        )
        self._principal(audit.data["authenticated_subject"])
        with owned.lock(closed) as (boundary, current):
            if current == Path(operation["old_slot"]):
                snapshot_target(
                    current, owned.target, self.store.head(owned.target)
                )
                actual, _ = read_project(current)
                previous = plan.data["expected_base"]["files"]
                for item in previous:
                    if item["sha256"] is not None:
                        verify_files(
                            [item], {item["path"]: actual[item["path"]]}
                        )
                    elif item["path"] in actual:
                        raise IntegrationError(FailureCode.STALE_BASE)
                self._event(attempt, "FAILED", journal.sha256)
                return PublicationResult("FAILED_UNSWITCHED", False)
            if current != Path(operation["new_slot"]):
                raise IntegrationError(FailureCode.RECOVERY_REQUIRED)
            actual, _ = read_project(current)
            current_snapshot = snapshot_target(current, owned.target, manifest)
            sources = tuple(
                resolve_approved_source(
                    self.source_connection,
                    parse_json(
                        self.store.get(
                            s["release_approval_hash"], "source_approval"
                        )
                    )["build_id"],
                )
                for s in manifest.data["sources"]
            )
            previous = (
                self.store.contract(
                    operation["previous_manifest_hash"], InstallationManifest
                )
                if operation["previous_manifest_hash"]
                else None
            )
            snapshot = snapshot_target(
                Path(operation["old_slot"]), owned.target, previous
            )
            attempt_row = self.connection.execute(
                "SELECT snapshot_hash FROM integration_attempts WHERE id=?",
                (attempt,),
            ).fetchone()
            if (
                sha256(canonical_json(snapshot.document)).hexdigest()
                != (attempt_row[0])
            ):
                raise IntegrationError(FailureCode.STALE_BASE)
            planning = PlanningResult(plan, snapshot, sources, False)
            managed = {
                i["path"]: actual[i["path"]] for i in manifest.data["files"]
            }
            verify_project_references(
                PlanningResult(plan, current_snapshot, sources, False), managed
            )
            verify_contract_bindings(
                plan,
                manifest,
                pre,
                post,
                authorization,
                current_target=owned.target,
                current_base=plan.data["expected_base"],
                files=managed,
            )
            # Native checks run on a disposable exact approved stage; current
            # mutable files stay in the selected slot and are never rewritten.
            with TemporaryDirectory(prefix="recovery-check-") as temporary:
                root = Path(temporary) / "generation"
                whole, directories = whole_generation(planning, managed)
                write_slot(root, whole, directories)
                staged = StageResult(
                    planning,
                    root,
                    tuple(sorted(managed.items())),
                    manifest,
                    next(iter(pre.values())),
                    post,
                    {},
                )
                Stager(self.connection, self.source_connection).revalidate(
                    staged
                )
            verify_files(
                manifest.data["files"],
                {
                    item["path"]: actual[item["path"]]
                    for item in manifest.data["files"]
                },
            )
            if owned.api.reparse(boundary) != junction_buffer(current):
                raise IntegrationError(FailureCode.RECOVERY_REQUIRED)
            receipt = self._finish(attempt, journal, operation, manifest)
            return PublicationResult("COMMITTED", True, receipt)
