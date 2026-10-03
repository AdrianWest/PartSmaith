"""

@package src.partsmith.persistence.database
@brief Connections and atomic, checksum-verified schema migrations.
@details Provides the module implementation and public interfaces.
"""

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

_SAVEPOINT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def utc_timestamp() -> str:
    """@brief Returns one server-controlled UTC audit timestamp.
    @return ISO 8601 UTC timestamp.
    @details The timestamp is suitable for non-engineering audit metadata.
    """
    return datetime.now(UTC).isoformat()


@contextmanager
def savepoint(connection: sqlite3.Connection, name: str) -> Iterator[None]:
    """@brief Protects caller work with a named SQLite savepoint.
    @param connection Active SQLite connection.
    @param name Trusted identifier containing letters, digits, or underscores.
    @return Iterator yielding control inside the savepoint.
    @details Failures roll back partial work while preserving the caller's
    outer transaction.
    """
    if not _SAVEPOINT_NAME.fullmatch(name):
        raise ValueError("Invalid SQLite savepoint name")
    connection.execute(f"SAVEPOINT {name}")
    try:
        yield
    except BaseException:
        connection.execute(f"ROLLBACK TO {name}")
        connection.execute(f"RELEASE {name}")
        raise
    else:
        connection.execute(f"RELEASE {name}")


def connect(path: str | Path) -> sqlite3.Connection:
    """

    @brief Open a connection with enforced relationships; caller must
    close it.
    @param path The path argument.
    @return The sqlite3.Connection result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the _migration_sql operation.
    @return The str result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    resource = files(__package__).joinpath("001_initial.sql")
    if resource.is_file():
        return resource.read_text(encoding="utf-8")
    # Editable installs use the single authoritative repository SQL file.
    source = Path(__file__).resolve().parents[3] / "migrations/001_initial.sql"
    return source.read_text(encoding="utf-8")


def _migration_sql_002() -> str:
    """@brief Loads the immutable Phase 8 persistence migration.
    @return Migration 002 SQL text.
    @details Packaged wheels and editable installs use identical bytes.
    """
    resource = files(__package__).joinpath("002_phase8.sql")
    if resource.is_file():
        return resource.read_text(encoding="utf-8")
    source = Path(__file__).resolve().parents[3] / "migrations/002_phase8.sql"
    return source.read_text(encoding="utf-8")


def _migrations() -> tuple[tuple[str, str], ...]:
    """@brief Returns supported migrations in application order.
    @return Version and SQL pairs ordered by version.
    @details Existing migration bytes are loaded independently and never
    concatenated before checksum verification.
    """
    return (("001", _migration_sql()), ("002", _migration_sql_002()))


def migrate(connection: sqlite3.Connection) -> tuple[str, ...]:
    """

    @brief Apply 001 once, atomically; reject changed or unknown
    migrations. Requires an idle connection with foreign keys enabled.
    An immediate transaction serializes competing initializers. Never
    commits caller work.
    @param connection The connection argument.
    @return The tuple[str, ...] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    if connection.in_transaction:
        raise RuntimeError("Migration requires an idle connection")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Migration requires foreign-key enforcement")
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
        migrations = _migrations()
        supported = {version for version, _ in migrations}
        if set(applied) - supported:
            raise RuntimeError("Database has unsupported migrations")
        result = []
        for version, sql in migrations:
            checksum = sha256(sql.encode("utf-8")).hexdigest()
            if version in applied:
                if applied[version] != checksum:
                    raise RuntimeError(
                        f"Applied migration {version} checksum differs"
                    )
                continue
            # Use execute, not executescript: DDL stays in this transaction.
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
                (version, checksum),
            )
            result.append(version)
        connection.commit()
        return tuple(result)
    except BaseException:
        connection.rollback()
        raise


@contextmanager
def database(path: str | Path) -> Iterator[sqlite3.Connection]:
    """

    @brief Open/migrate, commit on success or roll back on error, always
    close.
    @param path The path argument.
    @return The Iterator[sqlite3.Connection] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    connection = connect(path)
    try:
        migrate(connection)
        with connection:
            yield connection
    finally:
        connection.close()
