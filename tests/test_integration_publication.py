"""@package tests.test_integration_publication
@brief Exercises real NTFS publication, restart recovery and fresh rollback.
@details Native validation stays enabled; no mocked atomic boundary is used.
"""

import os
import pickle
import sqlite3
import subprocess
import sys
from threading import Event

import pytest
from phase13_support import TARGET
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources
from test_integration_review import CommitFaultConnection, principal
from test_integration_target import owned_target as owned_target

from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner, read_project
from partsmith.integration.publication import Publisher
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.review import IntegrationReview
from partsmith.integration.staging import Stager
from partsmith.integration.store import IntegrationStore
from partsmith.integration.target import OwnedTarget

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Requires local NTFS")


def prepared(target, builds, parent, planning=None):
    """@brief Creates a real checked and freshly approved test attempt.
    @param target Registered native target.
    @param builds Complete desired approved source build identifiers.
    @param parent Disposable ordinary staging parent.
    @param planning Optional fresh deliberate rollback plan.
    @return Attempt ID and exact staged generation.
    @details Real native checks and approval graph verification remain enabled.
    """
    connection = target.connection
    planning = planning or Planner(connection).plan(
        target.current(), TARGET, tuple(builds)
    )
    staged = Stager(connection).stage(planning, parent)
    attempt = IntegrationStore(connection).save_plan(
        planning.plan, planning.snapshot.document
    )
    Stager(connection).save(attempt, staged)
    connection.commit()
    IntegrationReview(connection, principal).decide(
        attempt,
        staged,
        "APPROVE",
        "Review complete native fixture",
        target=TARGET,
        root=target.current(),
    )
    return attempt, staged


def test_publish_update_rollback_and_initial_restore(owned_target, tmp_path):
    """@brief Publishes two sources, updates one and restores complete states.
    @param owned_target Real registered project and approved source builds.
    @param tmp_path Disposable staging parent.
    @return None.
    @details Rollback preserves latest mutable files and uses fresh approvals.
    Source bytes and original project remain unchanged throughout.
    """
    original, target, builds = owned_target
    before = read_project(original)
    initial = read_project(target.current())[0]
    publisher = Publisher(target.connection, principal)
    closed = ClosedProject(TARGET["project_id"], True)
    attempt, stage = prepared(target, builds[:2], tmp_path)
    old = target.current()
    one = publisher.publish(attempt, stage, target, closed)
    assert one.outcome == "COMMITTED" and one.committed
    assert target.current() != old and read_project(old)[0] == initial
    assert publisher.publish(attempt, stage, target, closed).reused
    assert (
        Planner(target.connection)
        .plan(target.current(), TARGET, builds[:2])
        .no_op
    )
    installed = dict(stage.objects)
    (target.current() / "user-note.txt").write_bytes(b"latest user file")
    update, changed = prepared(target, (builds[2], builds[1]), tmp_path)
    publisher.publish(update, changed, target, closed)
    assert (
        read_project(target.current())[0]["user-note.txt"]
        == b"latest user file"
    )
    planning = publisher.rollback_plan(target, stage.manifest.sha256)
    rollback, restored = prepared(target, (), tmp_path, planning)
    assert dict(restored.objects) == installed
    result = publisher.publish(
        rollback,
        restored,
        target,
        closed,
        intent="ROLLBACK",
        rollback_origin=stage.manifest.sha256,
    )
    assert result.committed
    assert (
        read_project(target.current())[0]["user-note.txt"]
        == b"latest user file"
    )
    planning = publisher.rollback_plan(target, None)
    removal, empty = prepared(target, (), tmp_path, planning)
    publisher.publish(removal, empty, target, closed, intent="ROLLBACK")
    actual = read_project(target.current())[0]
    assert actual == initial | {"user-note.txt": b"latest user file"}
    assert read_project(original) == before
    assert (
        target.connection.execute(
            "SELECT count(*) FROM integration_publications"
        ).fetchone()[0]
        == 4
    )
    assert (
        target.connection.execute(
            "SELECT count(*) FROM integration_events WHERE state='ROLLED_BACK'"
        ).fetchone()[0]
        == 2
    )


@pytest.mark.parametrize("point", ["after_prepare", "after_switch"])
def test_actual_process_crash_recovery(owned_target, tmp_path, point):
    """@brief Terminates an actual child at the journal or switch boundary.
    @param owned_target Real NTFS target and trusted fixture database.
    @param tmp_path Disposable stage and trusted pickle transport parent.
    @param point Exact pre-receipt crash checkpoint.
    @return None.
    @details Restart reconciliation never switches automatically or grants
    another approval. Pickle is test-owned transport, never a product import.
    """
    _, target, builds = owned_target
    attempt, stage = prepared(target, builds[:2], tmp_path)
    old = target.current()
    payload = tmp_path / "test-owned-stage.pickle"
    payload.write_bytes(pickle.dumps(stage))
    database = target.connection.execute("PRAGMA database_list").fetchone()[2]
    script = '''
import os, pickle, sys
from pathlib import Path
from partsmith.persistence import connect
from partsmith.integration.publication import Publisher
from partsmith.integration.target import OwnedTarget
from partsmith.integration.quiescence import ClosedProject
from partsmith.release.contracts import AuthenticatedPrincipal
def principal():
    """@brief Supplies a test-owned live adapter principal.
    @return Exact test authenticated principal.
    @details Exists only in the trusted disposable child fixture.
    """
    return AuthenticatedPrincipal("integration-reviewer", "test-live-adapter")
def fault(name):
    """@brief Terminates the child at the requested actual boundary.
    @param name Actual publication checkpoint name.
    @return None.
    @details os._exit bypasses handlers and leaves only durable state.
    """
    if name == sys.argv[4]:
        os._exit(91)
conn = connect(Path(sys.argv[1]))
stage = pickle.loads(Path(sys.argv[2]).read_bytes())
target = OwnedTarget(conn, stage.planning.plan.data["target"])
Publisher(conn, principal).publish(sys.argv[3], stage, target,
    ClosedProject(target.target["project_id"], True), fault=fault)
'''
    process = subprocess.run(
        [sys.executable, "-c", script, database, str(payload), attempt, point],
        capture_output=True,
        text=True,
        timeout=90,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert process.returncode == 91, process.stderr
    with pytest.raises(IntegrationError, match="RECOVERY_REQUIRED"):
        Planner(target.connection).plan(target.current(), TARGET, builds[:2])
    publisher = Publisher(target.connection, principal)
    closed = ClosedProject(TARGET["project_id"], True)
    if point == "after_switch":
        (target.current() / "latest-after-crash.txt").write_bytes(b"keep")
    result = publisher.recover(attempt, target, closed)
    assert result.committed == (point == "after_switch")
    assert (target.current() == old) == (point == "after_prepare")
    if result.committed:
        assert publisher.recover(attempt, target, closed).reused
        assert (
            target.current() / "latest-after-crash.txt"
        ).read_bytes() == b"keep"
    assert (
        target.connection.execute(
            "SELECT count(*) FROM integration_decisions WHERE attempt_id=?",
            (attempt,),
        ).fetchone()[0]
        == 1
    )


@pytest.mark.parametrize("point", ["after_prepare", "after_switch"])
def test_cancel_boundary_resolves_real_outcome(owned_target, tmp_path, point):
    """@brief Cleans pre-switch candidates and resolves late cancellation.
    @param owned_target Real closed target.
    @param tmp_path Disposable staging parent.
    @param point Actual cancellation checkpoint.
    @return None.
    @details Late cancellation preserves the committed complete generation.
    """
    _, target, builds = owned_target
    attempt, stage = prepared(target, builds[:2], tmp_path)
    old = target.current()
    cancel = Event()

    def fault(name):
        """@brief Sets cancellation at one actual publication checkpoint.
        @param name Current injected checkpoint.
        @return None.
        @details Does not mock filesystem behavior.
        """
        if name == point:
            cancel.set()

    result = Publisher(target.connection, principal).publish(
        attempt,
        stage,
        target,
        ClosedProject(TARGET["project_id"], True),
        cancel=cancel,
        fault=fault,
    )
    assert result.committed == (point == "after_switch")
    if not result.committed:
        assert target.current() == old
        assert list((target.workspace / "slots").iterdir()) == [old]
    else:
        assert "LATE_CANCEL_AFTER_PUBLICATION" in result.warnings


@pytest.mark.parametrize(
    "point", ["before_slot_write", "before_switch", "before_receipt"]
)
def test_write_and_receipt_failures_are_truthful(
    owned_target, tmp_path, point
):
    """@brief Preserves a complete old or recoverable new state on I/O faults.
    @param owned_target Real closed target.
    @param tmp_path Disposable stage parent.
    @param point Fault point representing disk, permission or receipt failure.
    @return None.
    @details Receipt failure reports the filesystem commit and can reconcile.
    """
    _, target, builds = owned_target
    attempt, stage = prepared(target, builds[:2], tmp_path)
    old = target.current()

    def fault(name):
        """@brief Injects one operational write/permission failure.
        @param name Actual boundary checkpoint.
        @return None.
        @details Atomic junction operation remains native and unmocked.
        """
        if name == point:
            raise PermissionError("Injected owned write failure")

    publisher = Publisher(target.connection, principal)
    closed = ClosedProject(TARGET["project_id"], True)
    if point == "before_receipt":
        result = publisher.publish(attempt, stage, target, closed, fault=fault)
        assert result.committed and result.outcome == "RECOVERY_REQUIRED"
        assert publisher.recover(attempt, target, closed).committed
    else:
        with pytest.raises((IntegrationError, PermissionError)):
            publisher.publish(attempt, stage, target, closed, fault=fault)
        assert target.current() == old
        assert not target.connection.execute(
            "SELECT * FROM integration_publications"
        ).fetchall()


def test_stale_whole_snapshot_cannot_reuse_attempt(owned_target, tmp_path):
    """@brief Rejects a new mutable snapshot under the same plan.
    @param owned_target Native closed project.
    @param tmp_path Disposable stages.
    @return None.
    @details New user files require a new stage and approval.
    """
    _, target, builds = owned_target
    attempt, stage = prepared(target, builds[:2], tmp_path)
    (target.current() / "new-user-file.txt").write_bytes(b"keep")
    fresh = Planner(target.connection).plan(
        target.current(), TARGET, builds[:2]
    )
    assert fresh.plan == stage.planning.plan
    replacement = Stager(target.connection).stage(fresh, tmp_path)
    with pytest.raises(IntegrationError, match="STALE_BASE"):
        Stager(target.connection).save(attempt, replacement)
    with pytest.raises(IntegrationError, match="STALE_BASE"):
        Publisher(target.connection, principal).publish(
            attempt, stage, target, ClosedProject(TARGET["project_id"], True)
        )
    assert (target.current() / "new-user-file.txt").read_bytes() == b"keep"


@pytest.mark.parametrize("fault", ["before", "after"])
def test_receipt_driver_commit_exception(owned_target, tmp_path, fault):
    """@brief Resolves errors on either side of the actual receipt COMMIT.
    @param owned_target Native target and real approved database.
    @param tmp_path Disposable backup connection and stage parent.
    @param fault Before or after the actual SQLite receipt commit.
    @return None.
    @details A real durable receipt prevents duplicate recovery or publication.
    """
    _, original, builds = owned_target
    attempt, stage = prepared(original, builds[:2], tmp_path)
    connection = sqlite3.connect(
        tmp_path / "fault.db", factory=CommitFaultConnection
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    original.connection.backup(connection)
    target = OwnedTarget(connection, TARGET)

    def checkpoint(name):
        """@brief Arms the driver fault only at the receipt boundary.
        @param name Actual trusted publication checkpoint.
        @return None.
        @details Preparation uses a normal durable transaction.
        """
        if name == "before_receipt":
            connection.fault = fault

    try:
        publisher = Publisher(connection, principal)
        closed = ClosedProject(TARGET["project_id"], True)
        result = publisher.publish(
            attempt, stage, target, closed, fault=checkpoint
        )
        assert result.committed
        assert result.outcome == (
            "COMMITTED" if fault == "after" else "RECOVERY_REQUIRED"
        )
        assert publisher.recover(attempt, target, closed).committed
        assert (
            connection.execute(
                "SELECT count(*) FROM integration_publications"
            ).fetchone()[0]
            == 1
        )
        # Restore the test parent's authoritative rows for safe final cleanup.
        connection.backup(original.connection)
    finally:
        connection.close()


def test_live_conflicts_and_authentication_block_publication(
    owned_target, tmp_path
):
    """@brief Rejects authentication, closure and lock conflicts.
    @param owned_target Registered native fixture.
    @param tmp_path Ordinary staging parent.
    @return None.
    @details All failures retain the original complete generation and history.
    """
    _, target, builds = owned_target
    attempt, stage = prepared(target, builds[:2], tmp_path)
    old = target.current()
    publisher = Publisher(target.connection, principal)
    closed = ClosedProject(TARGET["project_id"], True)

    def missing_principal():
        """@brief Rejects authentication through the trusted adapter.
        @return None.
        @details Existing saved actor text grants no replacement authority.
        """
        raise PermissionError("Unavailable fresh authentication")

    with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
        Publisher(target.connection, missing_principal).publish(
            attempt, stage, target, closed
        )
    with pytest.raises(IntegrationError):
        publisher.publish(
            attempt, stage, target, ClosedProject(TARGET["project_id"], False)
        )
    with target.lock(closed):
        with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
            publisher.publish(attempt, stage, target, closed)
    assert target.current() == old
    assert not target.connection.execute(
        "SELECT * FROM integration_publications"
    ).fetchall()
    assert (
        target.connection.execute(
            "SELECT count(*) FROM integration_decisions"
        ).fetchone()[0]
        == 1
    )
