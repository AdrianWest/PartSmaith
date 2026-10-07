"""@package tests.test_integration_review
@brief Tests fresh exact installation decisions and truthful durable outcomes.
@details Source approval and imported audit bytes never authorize installation.
"""

import sqlite3
from dataclasses import replace
from threading import Event

import pytest
from phase13_support import TARGET, database_identity
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources

from partsmith.integration.contracts import IntegrationValidationReport
from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner
from partsmith.integration.review import IntegrationReview, authorization_for
from partsmith.integration.staging import Stager
from partsmith.integration.store import IntegrationStore
from partsmith.release.contracts import AuthenticatedPrincipal


def principal():
    """@brief Resolves a test-owned live authentication adapter subject.
    @return Authenticated test principal, separate from source reviewer.
    @details Injection exists only at the service's trusted adapter boundary.
    """
    return AuthenticatedPrincipal("integration-reviewer", "test-live-adapter")


def unavailable_principal():
    """@brief Simulates failure of the live authentication adapter.
    @return None.
    @details Loaded subject strings cannot replace this missing principal.
    """
    raise PermissionError("Current principal unavailable")


@pytest.fixture
def review_fixture(approved_database, tmp_path):
    """@brief Persists a checked stage awaiting fresh installation review.
    @param approved_database Real complete approved source packages.
    @param tmp_path Disposable target/stage parent.
    @return Database, target, exact attempt and checked stage.
    @details Actual native checks remain enabled; fixture supplies no decision.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    planning = Planner(connection).plan(root, TARGET, builds[:2])
    staged = Stager(connection).stage(planning, tmp_path)
    attempt = IntegrationStore(connection).save_plan(
        planning.plan, planning.snapshot.document
    )
    Stager(connection).save(attempt, staged)
    connection.commit()
    return connection, root, attempt, staged


def test_fresh_approval_exact_retry_and_reopen(review_fixture, tmp_path):
    """@brief Binds a fresh approval to exact content without publication.
    @param review_fixture Actual checked native generation and saved attempt.
    @param tmp_path Disposable database path.
    @return None.
    @details Retries preserve the exact audit, actor, timestamp and reason.
    """
    connection, root, attempt, staged = review_fixture
    review = IntegrationReview(connection, principal)
    with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
        review.resolve(attempt, staged)
    one = review.decide(
        attempt,
        staged,
        "APPROVE",
        "Review exact packed files",
        target=TARGET,
        root=root,
    )
    assert one.outcome == "AUTHORIZED" and not one.reused
    assert one.authorization == authorization_for(staged)
    assert not connection.in_transaction
    assert not (root / "BFT_Symbols.kicad_sym").exists()
    two = review.decide(
        attempt,
        staged,
        "APPROVE",
        "Review exact packed files",
        target=TARGET,
        root=root,
    )
    assert two.reused and two.audit == one.audit
    assert (
        connection.execute(
            "SELECT count(*) FROM integration_decisions"
        ).fetchone()[0]
        == 1
    )
    assert (
        connection.execute(
            "SELECT count(*) FROM integration_events WHERE state='AUTHORIZED'"
        ).fetchone()[0]
        == 1
    )
    from partsmith.persistence import connect

    reopened = connect(tmp_path / "application.db")
    try:
        assert (
            IntegrationReview(reopened, principal)
            .resolve(attempt, staged)
            .audit
            == one.audit
        )
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "fault",
    [
        "saved-actor",
        "unavailable-principal",
        "wrong-target",
        "wrong-root",
        "target-edit",
        "staged-edit",
        "failed-report",
        "changed-report",
        "plan-only",
        "not-staged",
    ],
)
def test_failed_bindings_never_authorize(review_fixture, tmp_path, fault):
    """@brief Blocks stale, wrong, incomplete and unauthenticated decisions.
    @param review_fixture Actual persisted native stage.
    @param tmp_path Independent wrong root fixture.
    @param fault Exact deliberately changed identity or content.
    @return None.
    @details No failed attempt changes component approvals or publishes files.
    """
    connection, root, attempt, staged = review_fixture
    review = IntegrationReview(connection, principal)
    target, reviewer, content = TARGET, None, staged
    if fault == "saved-actor":
        reviewer = "integration-fixture-reviewer"
    elif fault == "unavailable-principal":
        review = IntegrationReview(connection, unavailable_principal)
    elif fault == "wrong-target":
        target = TARGET | {"project_id": "other-project"}
    elif fault == "wrong-root":
        root = tmp_path
    elif fault == "target-edit":
        (root / "user.kicad_pro").write_bytes(b"edited")
    elif fault == "staged-edit":
        (staged.root / "BFT_Symbols.kicad_sym").write_bytes(b"edited")
    elif fault in {"failed-report", "changed-report"}:
        data = staged.pre.data
        data["results"][0]["status"] = (
            "FAIL" if fault == "failed-report" else "PASS"
        )
        data["results"][0]["reason"] = "Imported assessment text"
        content = replace(staged, pre=IntegrationValidationReport(data))
    elif fault == "plan-only":
        content = staged.planning
    elif fault == "not-staged":
        attempt = IntegrationStore(connection).save_plan(
            staged.planning.plan, staged.planning.snapshot.document
        )
        connection.commit()
    before = database_identity(connection)
    with pytest.raises(IntegrationError):
        review.decide(
            attempt,
            content,
            "APPROVE",
            "Deliberate review",
            target=target,
            root=root,
            reviewer=reviewer,
        )
    assert database_identity(connection) == before
    assert not connection.execute(
        "SELECT * FROM integration_decisions"
    ).fetchall()


def test_raw_authorization_import_grants_no_decision(review_fixture):
    """@brief Refuses matching imported bindings without a trusted decision.
    @param review_fixture Actual checked stage and immutable source data.
    @return None.
    @details Historical release approval likewise supplies no decision row.
    """
    connection, _, attempt, staged = review_fixture
    IntegrationStore(connection).put_contract(authorization_for(staged))
    connection.commit()
    with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
        IntegrationReview(connection, principal).resolve(attempt, staged)


def test_plan_rejection_is_durable_and_does_not_authorize(review_fixture):
    """@brief Records rejection without requiring a passing generation.
    @param review_fixture Saved plan and actual checked candidate.
    @return None.
    @details Rejection keeps source release approval and target bytes intact.
    """
    connection, root, attempt, staged = review_fixture
    review = IntegrationReview(connection, principal)
    rejected = review.decide(
        attempt,
        staged.planning,
        "REJECT",
        "Do not install these entries",
        target=TARGET,
        root=root,
    )
    assert rejected.outcome == "REJECTED" and rejected.authorization is None
    repeated = review.decide(
        attempt,
        staged.planning,
        "REJECT",
        "Do not install these entries",
        target=TARGET,
        root=root,
    )
    assert repeated.reused and repeated.audit == rejected.audit
    with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
        review.resolve(attempt, staged)


def test_decision_storage_failure_rolls_back_all_authority(review_fixture):
    """@brief Rolls back interrupted decisions and preserves the saved stage.
    @param review_fixture Actual checked native stage and source approvals.
    @return None.
    @details A trigger fails after binding/audit inserts, before commit.
    """
    connection, root, attempt, staged = review_fixture
    connection.execute(
        "CREATE TRIGGER fail_review BEFORE INSERT ON integration_decisions "
        "BEGIN SELECT RAISE(ABORT, 'decision fault'); END"
    )
    connection.commit()
    before = database_identity(connection)
    with pytest.raises(sqlite3.IntegrityError, match="decision fault"):
        IntegrationReview(connection, principal).decide(
            attempt,
            staged,
            "APPROVE",
            "Review exact packed files",
            target=TARGET,
            root=root,
        )
    assert not connection.in_transaction
    assert database_identity(connection) == before


def test_busy_caller_transaction_is_preserved(review_fixture):
    """@brief Refuses to commit unrelated caller work during review.
    @param review_fixture Actual checked generation.
    @return None.
    @details The caller's pending object remains rollbackable after refusal.
    """
    connection, root, attempt, staged = review_fixture
    IntegrationStore(connection).put("artifact", b"unrelated caller work")
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationReview(connection, principal).decide(
            attempt,
            staged,
            "APPROVE",
            "Review",
            target=TARGET,
            root=root,
        )
    assert connection.in_transaction
    connection.rollback()


def test_predecision_cancel_grants_no_authority(review_fixture):
    """@brief Commits cancellation before a deliberate decision starts.
    @param review_fixture Saved actual native generation.
    @return None.
    @details No authentication, approval or target publication occurs.
    """
    connection, root, attempt, staged = review_fixture
    cancel = Event()
    cancel.set()
    outcome = IntegrationReview(connection, unavailable_principal).decide(
        attempt,
        staged,
        "APPROVE",
        "Review",
        target=TARGET,
        root=root,
        cancel=cancel,
    )
    assert outcome.outcome == "CANCELLED" and outcome.audit is None
    assert not connection.execute(
        "SELECT * FROM integration_decisions"
    ).fetchall()


def test_postcommit_cancel_and_checkpoint_failure_keep_decision(
    review_fixture,
):
    """@brief Preserves the real committed outcome after operational failures.
    @param review_fixture Actual saved native checked generation.
    @return None.
    @details Checkpoint failure and late cancellation cannot relabel approval.
    """
    connection, root, attempt, staged = review_fixture
    cancel = Event()

    def checkpoint(identity):
        """@brief Injects a late cancellation and checkpoint write failure.
        @param identity Actual committed immutable audit identity.
        @return None.
        @details The decision transaction has already completed.
        """
        cancel.set()
        raise OSError("Checkpoint unavailable")

    review = IntegrationReview(connection, principal)
    outcome = review.decide(
        attempt,
        staged,
        "APPROVE",
        "Review exact files",
        target=TARGET,
        root=root,
        cancel=cancel,
        checkpoint=checkpoint,
    )
    assert outcome.outcome == "AUTHORIZED"
    assert set(outcome.warnings) == {
        "CHECKPOINT_WRITE_FAILED_AFTER_DECISION",
        "LATE_CANCEL_AFTER_DECISION",
    }
    assert review.resolve(attempt, staged).audit == outcome.audit
    assert (
        connection.execute(
            "SELECT count(*) FROM integration_decisions"
        ).fetchone()[0]
        == 1
    )


class CommitFaultConnection(sqlite3.Connection):
    """@brief Injects SQLite driver exceptions around the COMMIT boundary.
    @details Fixtures use a disposable backup of the actual store.
    """

    fault: str | None = None

    def commit(self):
        """@brief Raises before or after the actual native SQLite commit.
        @return None.
        @details The after fault preserves the real durable database row.
        """
        fault, self.fault = self.fault, None
        if fault == "before":
            raise sqlite3.OperationalError("Injected pre-commit failure")
        super().commit()
        if fault == "after":
            raise sqlite3.OperationalError("Injected post-commit driver error")


@pytest.mark.parametrize("fault", ["before", "after"])
def test_commit_error_resolves_real_outcome(review_fixture, tmp_path, fault):
    """@brief Distinguishes rollback from actual completed commits.
    @param review_fixture Actual saved native stage.
    @param tmp_path Disposable independent commit-fault database.
    @param fault Exception boundary before or after real SQLite COMMIT.
    @return None.
    @details The original saved stage/database remains unchanged.
    """
    original, root, attempt, staged = review_fixture
    connection = sqlite3.connect(
        tmp_path / "commit-fault.db", factory=CommitFaultConnection
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    original.backup(connection)
    connection.fault = fault
    try:
        review = IntegrationReview(connection, principal)
        if fault == "before":
            with pytest.raises(sqlite3.OperationalError):
                review.decide(
                    attempt,
                    staged,
                    "APPROVE",
                    "Review exact files",
                    target=TARGET,
                    root=root,
                )
            assert not connection.execute(
                "SELECT * FROM integration_decisions"
            ).fetchall()
        else:
            outcome = review.decide(
                attempt,
                staged,
                "APPROVE",
                "Review exact files",
                target=TARGET,
                root=root,
            )
            assert outcome.outcome == "AUTHORIZED"
            assert outcome.warnings == ("COMMIT_DRIVER_ERROR_AFTER_DECISION",)
            assert review.resolve(attempt, staged).audit == outcome.audit
        assert not connection.in_transaction
    finally:
        connection.close()


def test_cancel_during_decision_write_rolls_back_authority(review_fixture):
    """@brief Rolls back authority when cancellation arrives during storage.
    @param review_fixture Actual native checked stage and saved source objects.
    @return None.
    @details Cancellation is recorded after the uncommitted decision rollback.
    """
    connection, root, attempt, staged = review_fixture
    cancel = Event()

    def request_cancel():
        """@brief Sets cancellation inside the simulated write boundary.
        @return Zero for SQLite's test-owned scalar function.
        @details No other transaction or native application is touched.
        """
        cancel.set()
        return 0

    connection.create_function("request_cancel", 0, request_cancel)
    connection.execute(
        "CREATE TRIGGER cancel_review BEFORE INSERT ON integration_decisions "
        "BEGIN SELECT request_cancel(); END"
    )
    connection.commit()
    outcome = IntegrationReview(connection, principal).decide(
        attempt,
        staged,
        "APPROVE",
        "Review exact files",
        target=TARGET,
        root=root,
        cancel=cancel,
    )
    assert outcome.outcome == "CANCELLED" and outcome.authorization is None
    assert not connection.execute(
        "SELECT * FROM integration_decisions"
    ).fetchall()
    assert not connection.execute(
        "SELECT * FROM integration_events WHERE state='AUTHORIZED'"
    ).fetchall()


def test_actual_os_principal_is_fresh(review_fixture):
    """@brief Exercises production process-token authentication.
    @param review_fixture Disposable actual native checked generation.
    @return None.
    @details Source reviewer text cannot replace the live OS subject.
    """
    connection, root, attempt, staged = review_fixture
    from partsmith.gui.identity import authenticated_principal

    actual = authenticated_principal()
    review = IntegrationReview(connection)
    with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
        review.decide(
            attempt,
            staged,
            "APPROVE",
            "Review disposable fixture",
            target=TARGET,
            root=root,
            reviewer="integration-fixture-reviewer",
        )
    outcome = review.decide(
        attempt,
        staged,
        "APPROVE",
        "Review disposable native fixture",
        target=TARGET,
        root=root,
        reviewer=actual.subject,
    )
    assert outcome.audit.data["authenticated_subject"] == actual.subject
    assert outcome.audit.data["authentication_mechanism"] == actual.mechanism


def test_review_inspection_remains_available_when_stale(review_fixture):
    """@brief Shows bound content and current blocking reasons.
    @param review_fixture Actual saved native checked generation.
    @return None.
    @details Inspection never calls authentication or writes a decision.
    """
    connection, root, attempt, staged = review_fixture
    review = IntegrationReview(connection, unavailable_principal)
    before = database_identity(connection)
    view = review.inspect(attempt, staged, target=TARGET, root=root)
    assert view["blocking_codes"] == []
    assert view["review_required"] and not view["installation_authority"]
    assert len(view["mechanical_differences"]) == 2
    assert view["manifest_hash"] == staged.manifest.sha256
    assert database_identity(connection) == before
    (root / "user.kicad_pro").write_bytes(b"edited")
    stale = review.inspect(attempt, staged, target=TARGET, root=root)
    assert stale["blocking_codes"] == ["STALE_BASE"]
    assert database_identity(connection) == before


def test_unicode_reason_retry_and_existing_late_cancel(review_fixture):
    """@brief Reuses canonical reasons and preserves committed outcomes.
    @param review_fixture Actual saved native generation.
    @return None.
    @details Fresh authentication runs for both requests; no duplicate audit.
    """
    connection, root, attempt, staged = review_fixture
    calls = []

    def fresh_principal():
        """@brief Records each trusted live authentication request.
        @return Actual test-owned principal.
        @details Saved display actors never supply this callback result.
        """
        calls.append(True)
        return principal()

    review = IntegrationReview(connection, fresh_principal)
    reason = "Reviewed cafe\u0301 fixture"
    one = review.decide(
        attempt, staged, "APPROVE", reason, target=TARGET, root=root
    )
    cancel = Event()
    cancel.set()
    two = review.decide(
        attempt,
        staged,
        "APPROVE",
        reason,
        target=TARGET,
        root=root,
        cancel=cancel,
    )
    assert len(calls) == 2
    assert one.audit == two.audit and two.reused
    assert two.outcome == "AUTHORIZED"
    assert two.warnings == ("LATE_CANCEL_AFTER_DECISION",)
