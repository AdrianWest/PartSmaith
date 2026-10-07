"""@package tests.test_integration_store
@brief Verifies immutable integration records and SQLite transaction ownership.
@details Migration tests retain actual approved release artifacts and history.
"""

import importlib
import sqlite3
from contextlib import closing
from hashlib import sha256

import pytest
from phase13_support import (
    TARGET,
    create_release,
    database_identity,
)
from phase13_support import (
    approved_database as approved_database,
)
from phase13_support import (
    approved_sources as approved_sources,
)

from partsmith.integration.contracts import (
    IntegrationAuthorizationBinding,
    IntegrationPlan,
)
from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.store import IntegrationStore
from partsmith.persistence import connect, migrate


def test_explicit_source_retention_is_immutable(approved_database, tmp_path):
    """@brief Retains complete source bytes without installation authority.
    @param approved_database Real approved source database.
    @param tmp_path Disposable project root.
    @return None.
    @details References survive commit; caller rollback removes all new data.
    """
    connection, builds = approved_database
    result = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    before = database_identity(connection)
    store = IntegrationStore(connection)
    identities = store.retain_sources(result.sources)
    assert len(identities) == 2
    assert connection.in_transaction
    for identity, source in zip(identities, result.sources, strict=True):
        assert store.get(identity, "source_manifest") == source.manifest_bytes
        references = {
            row[0]
            for row in connection.execute(
                "SELECT child_hash FROM integration_object_refs "
                "WHERE owner_hash=?",
                (identity,),
            )
        }
        expected = {sha256(source.approval_bytes).hexdigest()} | {
            sha256(blob).hexdigest() for _, _, blob in source.artifacts
        }
        assert expected <= references
    assert not connection.execute(
        "SELECT * FROM integration_decisions"
    ).fetchall()
    connection.rollback()
    assert database_identity(connection) == before


def test_explicit_plan_save_and_reopen(approved_database, tmp_path):
    """@brief Separates pure planning from explicit immutable persistence.
    @param approved_database Actual approved source history.
    @param tmp_path Disposable physical target.
    @return None.
    @details Stored plan bytes and all operational events survive reconnect.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    before = database_identity(connection)
    result.dry_run()
    assert database_identity(connection) == before
    store = IntegrationStore(connection)
    attempt = store.save_plan(result.plan, result.snapshot.document)
    assert connection.in_transaction
    assert store.contract(result.plan.sha256, IntegrationPlan) == result.plan
    assert (
        connection.execute(
            "SELECT state FROM integration_events WHERE attempt_id = ?",
            (attempt,),
        ).fetchone()[0]
        == "PLANNED"
    )
    connection.commit()
    with closing(connect(tmp_path / "application.db")) as reopened:
        assert migrate(reopened) == ()
        assert (
            IntegrationStore(reopened)
            .contract(result.plan.sha256, IntegrationPlan)
            .canonical_bytes
            == result.plan.canonical_bytes
        )


def test_caller_rollback_retains_no_plan_or_event(approved_database, tmp_path):
    """@brief Leaves outer transaction commit/rollback under caller control.
    @param approved_database Actual immutable source database.
    @param tmp_path Disposable target.
    @return None.
    @details Plan saves cannot commit unrelated component-store work.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, (builds[0],))
    before = database_identity(connection)
    connection.execute("BEGIN")
    store = IntegrationStore(connection)
    attempt = store.save_plan(result.plan, result.snapshot.document)
    store.event(attempt, "CANCELLED")
    connection.rollback()
    assert database_identity(connection) == before
    assert not connection.execute(
        "SELECT * FROM integration_attempts"
    ).fetchall()


def test_storage_failure_preserves_outer_work(approved_database, tmp_path):
    """@brief Rolls back a partial plan save without losing caller records.
    @param approved_database Actual source history.
    @param tmp_path Disposable target root.
    @return None.
    @details A trigger simulates event persistence failure after object insert.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, (builds[0],))
    store = IntegrationStore(connection)
    prior_hash = store.put("artifact", b"caller work")
    connection.execute(
        "CREATE TRIGGER fail_integration_event BEFORE INSERT "
        "ON integration_events BEGIN SELECT RAISE(ABORT, 'fault'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="fault"):
        store.save_plan(result.plan, result.snapshot.document)
    assert store.get(prior_hash, "artifact") == b"caller work"
    assert not connection.execute(
        "SELECT * FROM integration_attempts"
    ).fetchall()
    assert not connection.execute(
        "SELECT * FROM integration_objects WHERE sha256 = ?",
        (result.plan.sha256,),
    ).fetchall()
    connection.rollback()


def test_object_identity_and_append_only_events(approved_database, tmp_path):
    """@brief Rejects object replacement and deletion of operational history.
    @param approved_database Actual trusted source database.
    @param tmp_path Isolated project.
    @return None.
    @details Idempotent insertion retains one exact typed object.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, (builds[0],))
    store = IntegrationStore(connection)
    digest = store.put_contract(result.plan)
    assert store.put_contract(result.plan) == digest
    with pytest.raises(IntegrationError, match="TAMPERED_SOURCE"):
        store.put("artifact", result.plan.canonical_bytes)
    with pytest.raises(sqlite3.IntegrityError, match="Immutable"):
        connection.execute(
            "UPDATE integration_objects SET content = X'00' WHERE sha256 = ?",
            (digest,),
        )
    attempt = store.save_plan(result.plan, result.snapshot.document)
    store.event(attempt, "FAILED")
    with pytest.raises(sqlite3.IntegrityError, match="Append-only"):
        connection.execute(
            "DELETE FROM integration_events WHERE attempt_id = ?", (attempt,)
        )
    assert (
        len(
            connection.execute(
                "SELECT * FROM integration_events WHERE attempt_id = ?",
                (attempt,),
            ).fetchall()
        )
        == 2
    )


def test_oversized_object_is_bounded_before_content_fetch(
    approved_database, monkeypatch
):
    """@brief Refuses excessive stored blobs before loading their content.
    @param approved_database Migrated disposable database.
    @param monkeypatch Scoped resource policy override.
    @return None.
    @details Metadata checks bound reads as well as new object ingestion.
    """
    connection, _ = approved_database
    store = IntegrationStore(connection)
    digest = store.put("artifact", b"too large for the test policy")
    store_module = importlib.import_module("partsmith.integration.store")
    monkeypatch.setattr(store_module, "ResourcePolicy", small_policy)
    queries = []
    connection.set_trace_callback(queries.append)
    try:
        with pytest.raises(IntegrationError, match="RESOURCE_LIMIT"):
            store.get(digest, "artifact")
    finally:
        connection.set_trace_callback(None)
    assert not any("SELECT content" in query for query in queries)


def small_policy():
    """@brief Returns an effective small resource bound for rejection testing.
    @return Policy limiting each test object to four bytes.
    @details Does not disable semantic or authorization requirements.
    """
    return ResourcePolicy(object_bytes=4)


def test_raw_authorization_import_is_only_data(approved_database):
    """@brief Retains imported contract bytes without fabricating a decision.
    @param approved_database Disposable application database.
    @return None.
    @details Publication cannot resolve a trusted decision from object storage.
    """
    connection, _ = approved_database
    digest = IntegrationStore(connection).put(
        "integration_authorization_binding", b"imported untrusted record"
    )
    assert len(digest) == 64
    assert not connection.execute(
        "SELECT * FROM integration_decisions"
    ).fetchall()
    assert not connection.execute(
        "SELECT * FROM integration_publications"
    ).fetchall()
    with pytest.raises(IntegrationError, match="TAMPERED_SOURCE"):
        IntegrationStore(connection).contract(
            digest, IntegrationAuthorizationBinding
        )


@pytest.mark.parametrize("fault", ["unknown", "target", "base", "occupied"])
def test_snapshot_persistence_rejects_bad_bindings(
    approved_database, tmp_path, fault
):
    """@brief Refuses malformed or mismatched snapshot data before persistence.
    @param approved_database Real approved immutable source database.
    @param tmp_path Disposable physical project.
    @param fault Exact snapshot fault to inject.
    @return None.
    @details A rejected snapshot leaves all application records unchanged.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, (builds[0],))
    document = result.snapshot.document
    if fault == "unknown":
        document["imported_actor"] = "untrusted"
    elif fault == "target":
        document["target"]["project_id"] = "another-project"
    elif fault == "base":
        document["generation_hash"] = "f" * 64
    else:
        document["files"] = [
            {
                "path": "BFT_Symbols.kicad_sym",
                "sha256": "f" * 64,
                "byte_length": 1,
            }
        ]
    before = database_identity(connection)
    with pytest.raises(IntegrationError):
        IntegrationStore(connection).save_plan(result.plan, document)
    assert database_identity(connection) == before
    assert not connection.in_transaction


def test_forward_migration_preserves_real_approved_release(
    tmp_path, monkeypatch
):
    """@brief Adds integration persistence to an actual approved 004 database.
    @param tmp_path Isolated authoritative source database directory.
    @param monkeypatch Scoped older migration catalog.
    @return None.
    @details Artifacts, original manifest and trusted approval stay exact.
    """
    database_module = importlib.import_module("partsmith.persistence.database")
    migrations = database_module._migrations()
    with closing(connect(tmp_path / "older.db")) as connection:
        with monkeypatch.context() as scoped:
            scoped.setattr(database_module, "_migrations", older_migrations)
            assert migrate(connection) == ("001", "002", "003", "004")
        release = create_release(connection)
        original = resolve_approved_source(connection, release.build_id)
        connection.commit()
        assert migrate(connection) == ("005",)
        assert (
            resolve_approved_source(connection, release.build_id) == original
        )
        assert migrate(connection) == ()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert sha256(original.manifest_bytes).hexdigest() == (
            release.binding.engineering_manifest_hash
        )
    assert len(migrations) == 5


def older_migrations():
    """@brief Loads only the immutable pre-integration migration catalog.
    @return First four supported migration pairs.
    @details Calls the retained original loader rather than patched recursion.
    """
    return ORIGINAL_MIGRATIONS()[:4]


ORIGINAL_MIGRATIONS = importlib.import_module(
    "partsmith.persistence.database"
)._migrations
