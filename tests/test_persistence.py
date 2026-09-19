"""Phase 1 gate and persistence failure-path tests."""

import importlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime

import pytest

from partsmith.persistence import Repository, connect, database, migrate

database_module = importlib.import_module("partsmith.persistence.database")


def test_phase_one_gate(tmp_path):
    path = tmp_path / "partsmith.sqlite3"
    assert not path.exists()
    with closing(connect(path)) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert migrate(connection) == ("001",)
        original = tuple(
            connection.execute("SELECT * FROM schema_migrations").fetchone()
        )
        assert migrate(connection) == ()

    with database(path) as connection:
        assert migrate(connection) == ()
        assert (
            tuple(
                connection.execute(
                    "SELECT * FROM schema_migrations"
                ).fetchone()
            )
            == original
        )
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        repository = Repository(connection)
        project = repository.create_project("Board 'α'", "/projects/board")
        component = repository.create_component(
            "Example", "R-0402", "0402", project_id=project.id
        )
        build = repository.create_build(
            component.id,
            "DRAFT",
            schema_version="1.0",
            pdl_revision="r1",
            ai_provider="example-provider",
            ai_model="example-model",
            source_hash="source",
            ir_hash="ir",
            build_inputs_hash="inputs",
            started_at="2026-09-19T12:00:00+00:00",
            completed_at="2026-09-19T12:01:00+00:00",
        )

    with database(path) as connection:
        repository = Repository(connection)
        assert repository.get_project(project.id) == project
        assert repository.get_component(component.id) == component
        assert repository.get_build(build.id) == build
        assert repository.list_components(project.id) == [component]
        assert repository.list_builds(component.id) == [build]
        for record in (project, component, build):
            for value in (record.created_at, record.updated_at):
                assert (
                    datetime.fromisoformat(value).utcoffset().total_seconds()
                    == 0
                )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
            == 1
        )
        with pytest.raises(sqlite3.IntegrityError):
            repository.create_component("X", "Y", "Z", project_id="missing")
        with pytest.raises(sqlite3.IntegrityError):
            repository.create_build("missing", "DRAFT")


def test_parent_deletion_is_restricted(tmp_path):
    with database(tmp_path / "db") as connection:
        repository = Repository(connection)
        project = repository.create_project("Board", "/board")
        component = repository.create_component(
            "X", "Y", "Z", project_id=project.id
        )
        repository.create_build(component.id, "DRAFT")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM projects WHERE id = ?", (project.id,)
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM components WHERE id = ?", (component.id,)
            )


def test_queries_are_parameterized_and_scoped(tmp_path):
    with database(tmp_path / "db") as connection:
        repository = Repository(connection)
        first = repository.create_project("First", "/first")
        second = repository.create_project("Second", "/second")
        component = repository.create_component(
            "X", "'; DROP TABLE projects; --", "Z", project_id=first.id
        )
        standalone = repository.create_component("X", "Y", "Z")
        assert standalone.project_id is None
        assert repository.get_component(component.id) == component
        assert repository.list_components(second.id) == []
        assert repository.list_builds(standalone.id) == []
        assert repository.get_project("' OR 1=1 --") is None
        assert repository.get_component("missing") is None
        assert repository.get_build("missing") is None


def test_context_rolls_back_and_closes_on_error(tmp_path):
    path = tmp_path / "db"
    with pytest.raises(ValueError, match="abort"):
        with database(path) as connection:
            project = Repository(connection).create_project("Board", "/board")
            raise ValueError("abort")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with database(path) as reopened:
        assert Repository(reopened).get_project(project.id) is None


def test_success_closes_connection(tmp_path):
    with database(tmp_path / "db") as connection:
        pass
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_failed_migration_is_atomic_and_retryable(tmp_path, monkeypatch):
    original = database_module._migration_sql()
    with closing(connect(tmp_path / "db")) as connection:
        monkeypatch.setattr(
            database_module,
            "_migration_sql",
            lambda: original + "\nCREATE TABLE builds (bad TEXT);\n",
        )
        with pytest.raises(sqlite3.OperationalError):
            migrate(connection)
        assert not connection.in_transaction
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            == []
        )
        monkeypatch.setattr(
            database_module, "_migration_sql", lambda: original
        )
        assert migrate(connection) == ("001",)


def test_changed_migration_is_rejected(tmp_path, monkeypatch):
    with database(tmp_path / "db") as connection:
        original = database_module._migration_sql()
        monkeypatch.setattr(
            database_module,
            "_migration_sql",
            lambda: original + "\n-- changed",
        )
        with pytest.raises(RuntimeError, match="checksum"):
            migrate(connection)


def test_unknown_migration_is_rejected(tmp_path):
    with database(tmp_path / "db") as connection:
        connection.execute("UPDATE schema_migrations SET version = '999'")
        connection.commit()
        with pytest.raises(RuntimeError, match="unsupported"):
            migrate(connection)


def test_migration_does_not_commit_caller_work(tmp_path):
    with database(tmp_path / "db") as connection:
        repository = Repository(connection)
        project = repository.create_project("Board", "/board")
        with pytest.raises(RuntimeError, match="idle"):
            migrate(connection)
        connection.rollback()
        assert repository.get_project(project.id) is None


def test_migration_requires_foreign_keys():
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        with pytest.raises(RuntimeError, match="foreign-key"):
            migrate(connection)


def test_concurrent_initializers_apply_once(tmp_path):
    path = tmp_path / "db"

    def initialize(_):
        with closing(connect(path)) as connection:
            return migrate(connection)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(initialize, range(4)))
    assert results.count(("001",)) == 1
    assert results.count(()) == 3


def test_required_ids_and_duplicate_ids_are_rejected(tmp_path):
    with database(tmp_path / "db") as connection:
        project = Repository(connection).create_project("Board", "/board")
        for record_id in (None, project.id):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO projects VALUES (?, ?, ?, ?, ?)",
                    (record_id, "Board", "/board", "now", "now"),
                )
