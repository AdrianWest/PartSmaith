"""Connections and atomic, checksum-verified schema migrations."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from importlib.resources import files
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection with enforced relationships; caller must close it."""
    connection = sqlite3.connect(path)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("SQLite foreign-key enforcement is unavailable")
        return connection
    except BaseException:
        connection.close()
        raise


def _migration_sql() -> str:
    resource = files(__package__).joinpath("001_initial.sql")
    if resource.is_file():
        return resource.read_text(encoding="utf-8")
    # Editable installs use the single authoritative repository SQL file.
    source = Path(__file__).resolve().parents[3] / "migrations/001_initial.sql"
    return source.read_text(encoding="utf-8")


def migrate(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Apply 001 once, atomically; reject changed or unknown migrations.

    Requires an idle connection with foreign keys enabled. An immediate
    transaction serializes competing initializers. Never commits caller work.
    """
    if connection.in_transaction:
        raise RuntimeError("Migration requires an idle connection")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Migration requires foreign-key enforcement")
    sql = _migration_sql()
    checksum = sha256(sql.encode("utf-8")).hexdigest()
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        applied = dict(
            connection.execute("SELECT version, sha256 FROM schema_migrations")
        )
        if set(applied) - {"001"}:
            raise RuntimeError("Database has unsupported migrations")
        if "001" in applied:
            if applied["001"] != checksum:
                raise RuntimeError("Applied migration 001 checksum differs")
            result = ()
        else:
            # execute, not executescript: DDL must stay in this transaction.
            statement = ""
            for line in sql.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    connection.execute(statement)
                    statement = ""
            if statement.strip():
                raise RuntimeError("Incomplete migration SQL")
            connection.execute(
                "INSERT INTO schema_migrations VALUES "
                "(?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
                "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
                ("001", checksum),
            )
            result = ("001",)
        connection.commit()
        return result
    except BaseException:
        connection.rollback()
        raise


@contextmanager
def database(path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open/migrate, commit on success or roll back on error, always close."""
    connection = connect(path)
    try:
        migrate(connection)
        with connection:
            yield connection
    finally:
        connection.close()
