"""@package partsmith.release.workflow
@brief Persisted Phase 8 state transitions and headless release review.
@details The orchestrator exclusively advances build state while the review
service atomically verifies and records authenticated release decisions.
"""

from __future__ import annotations

import sqlite3

from partsmith.persistence.database import savepoint, utc_timestamp
from partsmith.persistence.records import Build, Repository
from partsmith.persistence.release import ReleaseStore
from partsmith.release.contracts import (
    ApprovalBinding,
    AuthenticatedPrincipal,
    BuildState,
    ReviewStage,
)

_ALLOWED_TRANSITIONS = {
    BuildState.SOURCE_RECEIVED: {BuildState.SOURCE_ANALYZED},
    BuildState.SOURCE_ANALYZED: {BuildState.EVIDENCE_COLLECTED},
    BuildState.EVIDENCE_COLLECTED: {BuildState.IR_BUILT},
    BuildState.IR_BUILT: {
        BuildState.PACKAGE_IDENTIFIED,
        BuildState.HUMAN_REVIEW_REQUIRED,
    },
    BuildState.PACKAGE_IDENTIFIED: {
        BuildState.IR_VALIDATED,
        BuildState.HUMAN_REVIEW_REQUIRED,
    },
    BuildState.IR_VALIDATED: {BuildState.SYMBOL_GENERATED},
    BuildState.SYMBOL_GENERATED: {BuildState.FOOTPRINT_GENERATED},
    BuildState.FOOTPRINT_GENERATED: {BuildState.MODEL_3D_GENERATED},
    BuildState.MODEL_3D_GENERATED: {BuildState.ARTIFACT_VALIDATION},
    BuildState.ARTIFACT_VALIDATION: {
        BuildState.CROSS_VALIDATION,
        BuildState.ARTIFACT_VALIDATION_FAILED,
        BuildState.HUMAN_REVIEW_REQUIRED,
    },
    BuildState.CROSS_VALIDATION: {
        BuildState.HUMAN_REVIEW_REQUIRED,
        BuildState.CROSS_VALIDATION_FAILED,
    },
    BuildState.HUMAN_REVIEW_REQUIRED: {
        BuildState.IR_BUILT,
        BuildState.APPROVED,
        BuildState.REJECTED,
    },
    BuildState.APPROVED: {BuildState.EXPORTED},
}
_FAILURE_TRANSITIONS = {
    BuildState.EXTRACTION_FAILED,
    BuildState.EVIDENCE_CONFLICT,
    BuildState.IR_INVALID,
    BuildState.PACKAGE_UNSUPPORTED,
    BuildState.NOT_GENERATABLE,
    BuildState.ARTIFACT_VALIDATION_FAILED,
    BuildState.CROSS_VALIDATION_FAILED,
}


class BuildOrchestrator:
    """@brief Owns persisted build-state advancement.
    @details State changes append immutable transition records and reject
    invalid review-stage or terminal-state transitions.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the build orchestrator.
        @param connection Migrated SQLite connection.
        @return None.
        @details The caller owns the surrounding transaction.
        """
        self.connection = connection
        self.repository = Repository(connection)

    def start(
        self,
        component_id: str,
        *,
        supplied_reviewed_inputs: bool = False,
        reason: str = "Build created",
    ) -> Build:
        """@brief Starts one persisted build attempt.
        @param component_id Component identity being built.
        @param supplied_reviewed_inputs Whether retained reviewed inputs exist.
        @param reason Audit reason for the initial state.
        @return Newly created build record.
        @details Reviewed deterministic fixtures may begin at IR_BUILT;
        ordinary builds begin at SOURCE_RECEIVED.
        """
        initial = (
            BuildState.IR_BUILT
            if supplied_reviewed_inputs
            else BuildState.SOURCE_RECEIVED
        )
        build = self.repository.create_build(component_id, initial.value)
        self.connection.execute(
            "INSERT INTO build_state_transitions "
            "(build_id, from_state, to_state, review_stage, reason, "
            "created_at) "
            "VALUES (?, NULL, ?, NULL, ?, ?)",
            (build.id, initial.value, reason, utc_timestamp()),
        )
        return build

    def advance(
        self,
        build_id: str,
        to_state: BuildState,
        reason: str,
        *,
        review_stage: ReviewStage | None = None,
    ) -> Build:
        """@brief Advances one build through an allowed persisted transition.
        @param build_id Build identity to advance.
        @param to_state Requested next state.
        @param reason Nonempty transition reason.
        @param review_stage INPUT or RELEASE for a review waiting state.
        @return Updated build record.
        @details Invalid edges and missing review-stage bindings fail before
        mutating the build.
        """
        if not reason:
            raise ValueError("Transition reason must not be empty")
        build = self.repository.get_build(build_id)
        if build is None:
            raise KeyError(build_id)
        current = BuildState(build.state)
        allowed = set(_ALLOWED_TRANSITIONS.get(current, set()))
        if current not in {
            BuildState.APPROVED,
            BuildState.EXPORTED,
            BuildState.REJECTED,
        }:
            allowed.update(_FAILURE_TRANSITIONS)
        if to_state not in allowed:
            raise ValueError(
                f"Invalid build transition: {current} -> {to_state}"
            )
        if to_state == BuildState.HUMAN_REVIEW_REQUIRED:
            if review_stage is None:
                raise ValueError(
                    "Review waiting state requires a review stage"
                )
        elif review_stage is not None:
            raise ValueError("Review stage is only valid for a waiting state")
        now = utc_timestamp()
        completed_at = (
            now
            if to_state
            in {
                BuildState.EXPORTED,
                BuildState.REJECTED,
                *_FAILURE_TRANSITIONS,
            }
            else build.completed_at
        )
        self.connection.execute(
            "UPDATE builds SET state = ?, completed_at = ?, updated_at = ? "
            "WHERE id = ?",
            (to_state.value, completed_at, now, build_id),
        )
        self.connection.execute(
            "INSERT INTO build_state_transitions "
            "(build_id, from_state, to_state, review_stage, reason, "
            "created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                build_id,
                current.value,
                to_state.value,
                review_stage.value if review_stage is not None else None,
                reason,
                now,
            ),
        )
        updated = self.repository.get_build(build_id)
        if updated is None:
            raise RuntimeError("Updated build disappeared")
        return updated


class ReviewService:
    """@brief Performs authenticated headless release decisions.
    @details Approval rechecks every deterministic binding and records the
    decision, binding, and orchestrator transition in one savepoint.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the release review service.
        @param connection Migrated SQLite connection.
        @return None.
        @details The service shares the caller transaction but rolls back its
        own partial operation on any failure.
        """
        self.connection = connection
        self.store = ReleaseStore(connection)
        self.orchestrator = BuildOrchestrator(connection)

    def approve(
        self,
        build_id: str,
        reviewer: str,
        reason: str,
        binding: ApprovalBinding,
        principal: AuthenticatedPrincipal,
    ) -> str:
        """@brief Approves one exact verified release.
        @param build_id Build waiting for release review.
        @param reviewer Requested reviewer subject.
        @param reason Nonempty approval rationale.
        @param binding Exact snapshot, manifest, validation, and artifact
        hashes.
        @param principal Authenticated service principal.
        @return Immutable release decision identity.
        @details Stale bindings, blockers, or identity mismatches leave no
        decision or state transition behind.
        """
        with savepoint(self.connection, "release_approval"):
            principal.require_reviewer(reviewer)
            self.store.verify_approval_binding(build_id, binding)
            decision_id = self.store.record_release_decision(
                build_id,
                "APPROVE",
                reviewer,
                reason,
                binding,
            )
            self.orchestrator.advance(
                build_id,
                BuildState.APPROVED,
                reason,
            )
            return decision_id

    def reject(
        self,
        build_id: str,
        reviewer: str,
        reason: str,
        principal: AuthenticatedPrincipal,
    ) -> str:
        """@brief Rejects one build waiting for human review.
        @param build_id Build waiting for input or release review.
        @param reviewer Requested reviewer subject.
        @param reason Nonempty rejection rationale.
        @param principal Authenticated service principal.
        @return Immutable release decision identity.
        @details Rejection requires authentication but no approval binding.
        """
        with savepoint(self.connection, "release_rejection"):
            principal.require_reviewer(reviewer)
            build = self.orchestrator.repository.get_build(build_id)
            if build is None:
                raise KeyError(build_id)
            if build.state != BuildState.HUMAN_REVIEW_REQUIRED:
                raise ValueError("Build is not waiting for review")
            transition = self.connection.execute(
                "SELECT review_stage FROM build_state_transitions "
                "WHERE build_id = ? ORDER BY id DESC LIMIT 1",
                (build_id,),
            ).fetchone()
            if transition is None or transition["review_stage"] != "RELEASE":
                raise ValueError("Build is not waiting for release review")
            decision_id = self.store.record_release_decision(
                build_id,
                "REJECT",
                reviewer,
                reason,
                None,
            )
            self.orchestrator.advance(
                build_id,
                BuildState.REJECTED,
                reason,
            )
            return decision_id
