"""@package partsmith.gui.session
@brief Stores unfinished desktop sessions independently of release bundles.
@details Each load creates an isolated database and immutable asset store;
archives and recovery checkpoints are validated before atomic replacement.
"""

from __future__ import annotations

import base64
import os
import shutil
import tempfile
import threading
import zipfile
from contextlib import contextmanager
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence.database import connect, migrate
from partsmith.schema_support import decimal_validator_class

from .processing import Redactor

VERSION = "partsmith-session-1.0"
DEFAULT_BUDGETS = {
    "object_bytes": 128 * 1024 * 1024,
    "archive_bytes": 512 * 1024 * 1024,
    "expanded_bytes": 1024 * 1024 * 1024,
    "object_count": 10000,
    "log_bytes": 2 * 1024 * 1024,
    "image_cache_bytes": 64 * 1024 * 1024,
    "mesh_bytes": 16 * 1024 * 1024,
}
STATE_FIELDS = {
    "setup",
    "source",
    "extraction",
    "ai",
    "drafts",
    "viewer",
    "integration",
    "history",
    "component_id",
    "revision_id",
    "inventory_sha256",
    "pdl",
    "build_id",
    "proposal",
    "release",
    "status",
    "logs",
    "budgets",
    "acquisition_id",
}


@lru_cache(maxsize=1)
def transport_validator():
    """@brief Loads the packaged offline desktop transport schema.
    @return Decimal-aware JSON Schema validator.
    @details This schema is separate from engineering release bundles.
    """
    schema = parse_json(
        files("partsmith.gui")
        .joinpath("session-index-1.0.schema.json")
        .read_bytes()
    )
    return decimal_validator_class()(schema)


def user_root() -> Path:
    """@brief Resolves the user-writable desktop session directory.
    @return Absolute path outside the checkout.
    @details Uses LocalAppData on Windows and XDG data elsewhere.
    """
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / (
        "PartSmith/sessions"
    )


def _references(value):
    """@brief Enumerates immutable object references in session data.
    @param value JSON-compatible nested data.
    @return Iterator of SHA-256 identities.
    @details Only closed single-field asset reference records are accepted.
    """
    if isinstance(value, dict):
        if "$asset" in value:
            if set(value) != {"$asset"}:
                raise ValueError("Invalid session asset reference")
            yield value["$asset"]
        else:
            for child in value.values():
                yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _safe_state(value, redact):
    """@brief Rejects credential fields and redacts persisted text.
    @param value Session metadata to detach and sanitize.
    @param redact Credential redaction callable.
    @return Sanitized JSON-compatible value.
    @details Credentials never become desktop settings or saved actors.
    """
    if isinstance(value, dict):
        for key in value:
            if key.lower().replace("_", "") in {
                "apikey",
                "credential",
                "secret",
                "password",
                "authorization",
                "accesstoken",
                "refresh token",
                "bfttoken",
            }:
                raise ValueError("Credentials cannot be session metadata")
        return {
            key: _safe_state(child, redact) for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_state(child, redact) for child in value]
    return redact(value) if isinstance(value, str) else value


def _digest(value):
    """@brief Validates a content-addressed object identity.
    @param value Candidate SHA-256 text.
    @return The validated identity.
    @details Rejects path traversal and noncanonical digests.
    """
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("Invalid session object SHA-256")
    return value


class Session:
    """@brief Owns an isolated working database and immutable byte objects.
    @details Connections are opened and closed in the calling thread; one
    mutation lock serializes actions and consistent checkpoint boundaries.
    """

    def __init__(self, root=None, *, secrets=()):
        """@brief Creates a new operational session instance.
        @param root Optional user storage root for tests or deployment.
        @param secrets Known credentials to redact before persistence.
        @return None.
        @details Initializes the existing engineering schema without approval.
        """
        self.storage = Path(root) if root is not None else user_root()
        self.storage.mkdir(parents=True, exist_ok=True)
        self.instance_id = str(uuid4())
        self.directory = self.storage / self.instance_id
        self.directory.mkdir()
        self.assets = self.directory / "objects"
        self.assets.mkdir()
        self.database = self.directory / "working.sqlite"
        self._migrated = False
        self.lock = threading.RLock()
        self.busy = False
        self.dirty = False
        self.redact = Redactor(secrets)
        self._display_extraction = None
        self._display_extraction_reference = None
        self.state = {
            "setup": {},
            "status": "setup",
            "logs": [],
            "budgets": dict(DEFAULT_BUDGETS),
        }
        with self.connection() as connection:
            connection.execute(
                "CREATE TABLE desktop_session (id INTEGER PRIMARY KEY "
                "CHECK(id = 1), data BLOB NOT NULL)"
            )
            connection.execute(
                "INSERT INTO desktop_session VALUES (1, ?)",
                (canonical_json(self.state),),
            )

    @contextmanager
    def connection(self):
        """@brief Opens a thread-owned migrated database transaction.
        @return Iterator yielding one SQLite connection.
        @details Commits success, rolls back failure, and always closes.
        """
        connection = connect(self.database)
        previous, previous_dirty = self.state, self.dirty
        try:
            if not self._migrated:
                migrate(connection)
                self._migrated = True
            connection.execute("BEGIN")
            with connection:
                yield connection
        except BaseException:
            self.state, self.dirty = previous, previous_dirty
            raise
        finally:
            connection.close()

    def put(self, content: bytes) -> dict:
        """@brief Retains immutable bytes by their SHA-256 identity.
        @param content Original source or derived asset bytes.
        @return Closed asset reference mapping.
        @details Writes atomically and verifies any existing object.
        """
        if len(content) > self.state["budgets"]["object_bytes"]:
            raise ValueError("Session object exceeds configured byte budget")
        digest = sha256(content).hexdigest()
        destination = self.assets / digest
        with self.lock:
            if destination.exists():
                if destination.read_bytes() != content:
                    raise ValueError("Immutable session object changed")
            else:
                if (
                    len(list(self.assets.iterdir()))
                    >= self.state["budgets"]["object_count"]
                ):
                    raise ValueError("Session exceeds object-count budget")
                self._atomic(destination, content)
        return {"$asset": digest}

    def get(self, reference: dict) -> bytes:
        """@brief Reads and verifies one retained immutable object.
        @param reference Closed content-addressed reference mapping.
        @return Exact original bytes.
        @details Missing or tampered objects fail instead of reacquisition.
        """
        digest = _digest(reference["$asset"])
        data = (self.assets / digest).read_bytes()
        if sha256(data).hexdigest() != digest:
            raise ValueError("Session object hash mismatch")
        return data

    def update(self, *, _connection=None, **changes):
        """@brief Commits one detached desktop state boundary.
        @param changes Whitelisted session fields to replace.
        @param _connection Optional transaction already owned by this worker.
        @return None.
        @details Redacts metadata before storing it in the working database.
        """
        if set(changes) - STATE_FIELDS:
            raise ValueError("Unknown desktop session field")
        if "integration" in changes:
            schema = {
                "$ref": "#/$defs/integration",
                "$defs": transport_validator().schema["$defs"],
            }
            if any(
                decimal_validator_class()(schema).iter_errors(
                    changes["integration"]
                )
            ):
                raise ValueError("Invalid integration session extension")
        with self.lock:
            state = {**self.state, **_safe_state(changes, self.redact)}
            budgets = state["budgets"]
            if set(budgets) != set(DEFAULT_BUDGETS) or any(
                type(value) not in (int, Decimal)
                or value != int(value)
                or not 0 < value <= DEFAULT_BUDGETS[key]
                for key, value in budgets.items()
            ):
                raise ValueError("Invalid session resource budgets")
            if (
                len(canonical_json(state.get("logs", [])))
                > budgets["log_bytes"]
            ):
                raise ValueError("Session log exceeds configured byte budget")
            for digest in _references(state):
                self.get({"$asset": digest})
            content = canonical_json(state)
            if _connection is None:
                with self.connection() as connection:
                    connection.execute(
                        "UPDATE desktop_session SET data=?", (content,)
                    )
            else:
                _connection.execute(
                    "UPDATE desktop_session SET data=?", (content,)
                )
            self.state = parse_json(content)
            self.dirty = True

    def verify_part_number(self, ir):
        """@brief Checks the setup request against an immutable component.
        @param ir Component document read from the trusted revision store.
        @return None.
        @details Generation, release and restored sessions must retain the
        exact ordering number used to assemble their component identity.
        """
        if (
            self.state.get("setup", {}).get("part_number")
            != ir["identity"]["mpn"]
        ):
            raise ValueError(
                "Required part number differs from the component identity; "
                "use New / Clear Component to start another component"
            )

    def acquire(self, source: Path) -> Path:
        """@brief Snapshots a selected PDF before extraction or setup save.
        @param source Explicitly selected readable PDF path.
        @return Immutable snapshot path used for subsequent processing.
        @details Reuses retained bytes until the user explicitly reacquires.
        """
        with self.lock:
            if "source" not in self.state:
                with Path(source).open("rb") as stream:
                    content = stream.read(100 * 1024 * 1024 + 1)
                if (
                    len(content) > 100 * 1024 * 1024
                    or b"%PDF-" not in content[:1024]
                ):
                    raise ValueError("Invalid or oversized source PDF")
                reference = self.put(content)
                self.update(source=reference, acquisition_id=str(uuid4()))
            content = self.get(self.state["source"])
            snapshot = self.directory / "source.pdf"
            if not snapshot.exists():
                self._atomic(snapshot, content)
            elif snapshot.read_bytes() != content:
                raise ValueError("Source snapshot changed")
            return snapshot

    def retain_extraction(self, result):
        """@brief Retains the complete local result before provider work.
        @param result Extraction result including original evidence and assets.
        @return None.
        @details Bulk image bytes are separately hashed and remain on demand.
        """
        detached = parse_json(canonical_json(result))
        detached["assets"] = {
            digest: self.put(base64.b64decode(value, validate=True))
            for digest, value in detached.get("assets", {}).items()
        }
        for digest, reference in detached["assets"].items():
            if reference["$asset"] != digest:
                raise ValueError("Extraction asset hash mismatch")
        self.update(
            extraction=self.put(canonical_json(detached)), status="extracted"
        )
        self.extraction()
        self.checkpoint()

    def extraction(self):
        """@brief Loads retained evidence without decoding bulk image bytes.
        @return Complete extraction metadata or None before extraction.
        @details Source and evidence identities survive archive recovery.
        """
        reference = self.state.get("extraction")
        data = parse_json(self.get(reference)) if reference else None
        self._display_extraction = data
        self._display_extraction_reference = reference
        return data

    def display_extraction(self):
        """@brief Returns metadata already prepared by extraction/load workers.
        @return Retained read-only display mapping or None until prepared.
        @details Does no disk reading, JSON parsing or bulk copying in wx.
        The view must never mutate this mapping or treat it as review
        authority.
        """
        if getattr(
            self, "_display_extraction_reference", None
        ) == self.state.get("extraction"):
            return getattr(self, "_display_extraction", None)
        return None

    def refresh(self):
        """@brief Reads the latest committed worker-owned session state.
        @return None.
        @details Engineering decisions remain in the shared isolated database.
        """
        with self.connection() as connection:
            state = parse_json(
                connection.execute(
                    "SELECT data FROM desktop_session WHERE id=1"
                ).fetchone()[0]
            )
        self.state = state

    @classmethod
    def attach(cls, directory):
        """@brief Attaches an authorized native worker to its isolated session.
        @param directory Existing working-instance directory supplied by
        parent.
        @return Session with a process-local lock and thread-owned connections.
        @details Only operational worker attachment reuses the working
        instance;
        user archive loading always creates a fresh instance through load.
        """
        session = object.__new__(cls)
        session.directory = Path(directory).resolve()
        session.instance_id = session.directory.name
        session.storage = session.directory.parent
        session.database = session.directory / "working.sqlite"
        session._migrated = False
        session.assets = session.directory / "objects"
        if not session.database.is_file() or not session.assets.is_dir():
            raise ValueError("Worker session does not exist")
        session.lock = threading.RLock()
        session.state = {"budgets": dict(DEFAULT_BUDGETS)}
        session.dirty, session.busy = False, True
        session.redact = Redactor()
        session.refresh()
        return session

    @staticmethod
    def _atomic(destination, content):
        """@brief Atomically replaces one durable file.
        @param destination Target path in an existing directory.
        @param content Complete final bytes.
        @return None.
        @details Flushes bytes before replacement and removes failed staging.
        """
        handle, name = tempfile.mkstemp(
            dir=destination.parent, prefix=".staged-"
        )
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)

    def save(self, destination: Path, *, checkpoint=False):
        """@brief Saves a consistent unfinished session transport archive.
        @param destination User-selected archive or recovery checkpoint path.
        @param checkpoint Whether this is an internal consistent boundary.
        @return None.
        @details Manual busy saves fail; atomic replacement retains last good.
        """
        destination = Path(destination)
        if self.busy and not checkpoint:
            raise ValueError(
                "Save and Load are unavailable during active work"
            )
        with (
            self.lock,
            tempfile.TemporaryDirectory(dir=self.directory) as staging,
        ):
            snapshot = Path(staging) / "database.sqlite"
            original = connect(self.database)
            target = connect(snapshot)
            try:
                original.backup(target)
            finally:
                target.close()
                original.close()
            objects = {path.name: path for path in self.assets.iterdir()}
            expanded = snapshot.stat().st_size + sum(
                path.stat().st_size for path in objects.values()
            )
            if expanded > self.state["budgets"]["expanded_bytes"]:
                raise ValueError("Session archive expansion exceeds budget")
            database_bytes = snapshot.read_bytes()
            index = {
                "schema_version": VERSION,
                "state": self.state,
                "database_sha256": sha256(database_bytes).hexdigest(),
                "objects": {
                    key: {
                        "sha256": sha256(value.read_bytes()).hexdigest(),
                        "size": value.stat().st_size,
                    }
                    for key, value in objects.items()
                },
            }
            archive = Path(staging) / "session.partsmith"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                output.writestr("index.json", canonical_json(index))
                output.writestr("database.sqlite", database_bytes)
                for digest, content in sorted(objects.items()):
                    output.write(content, "objects/" + digest)
            if archive.stat().st_size > self.state["budgets"]["archive_bytes"]:
                raise ValueError(
                    "Session archive exceeds configured byte budget"
                )
            self._atomic_copy(destination, archive)
            if not checkpoint:
                self.dirty = False

    @staticmethod
    def _atomic_copy(destination, source):
        """@brief Atomically replaces an archive using bounded copy buffers.
        @param destination User-selected transport path.
        @param source Fully staged archive path.
        @return None.
        @details Flushes before replacement and preserves the last good file.
        """
        handle, name = tempfile.mkstemp(
            dir=destination.parent, prefix=".staged-"
        )
        try:
            with (
                os.fdopen(handle, "wb") as output,
                source.open("rb") as input_file,
            ):
                shutil.copyfileobj(input_file, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, destination)
        finally:
            Path(name).unlink(missing_ok=True)

    def checkpoint(self):
        """@brief Retains the last complete consistent recovery boundary.
        @return None.
        @details Recovery is offered by the GUI and never starts an action.
        """
        self.save(self.storage / "recovery.partsmith", checkpoint=True)

    @classmethod
    def load(cls, archive: Path, *, root=None, secrets=()):
        """@brief Stages and validates an archive in a fresh working instance.
        @param archive User-selected session transport archive.
        @param root Optional storage root independent of the original session.
        @param secrets Known credentials to redact from imported metadata.
        @return New Session with unchanged historical engineering identities.
        @details No extraction, provider call, approval, or retry is performed.
        """
        if Path(archive).stat().st_size > DEFAULT_BUDGETS["archive_bytes"]:
            raise ValueError("Session archive exceeds transport limit")
        session = cls(root, secrets=secrets)
        try:
            with zipfile.ZipFile(archive) as source:
                entries = source.infolist()
                if len(entries) > DEFAULT_BUDGETS["object_count"] + 2:
                    raise ValueError("Session archive has too many objects")
                names = [item.filename for item in entries]
                if len(set(names)) != len(names):
                    raise ValueError("Duplicate session archive member")
                if (
                    sum(item.file_size for item in entries)
                    > DEFAULT_BUDGETS["expanded_bytes"]
                ):
                    raise ValueError(
                        "Session archive expansion exceeds budget"
                    )
                if any(
                    item.file_size > DEFAULT_BUDGETS["object_bytes"]
                    for item in entries
                ):
                    raise ValueError("Session member exceeds object budget")
                index = parse_json(source.read("index.json"))
                if not transport_validator().is_valid(index):
                    raise ValueError("Invalid session transport schema")
                if set(index) != {
                    "schema_version",
                    "state",
                    "database_sha256",
                    "objects",
                }:
                    raise ValueError("Invalid session transport schema")
                if index["schema_version"] != VERSION:
                    raise ValueError("Unsupported session transport version")
                state = index["state"]
                if not isinstance(state, dict) or set(state) - STATE_FIELDS:
                    raise ValueError("Invalid session state schema")
                budgets = state.get("budgets", {})
                if set(budgets) != set(DEFAULT_BUDGETS) or any(
                    type(value) not in (int, Decimal)
                    or value != int(value)
                    or value <= 0
                    or value > DEFAULT_BUDGETS[key]
                    for key, value in budgets.items()
                ):
                    raise ValueError("Invalid session resource budgets")
                expected = {"index.json", "database.sqlite"}
                for digest, record in index["objects"].items():
                    _digest(digest)
                    if (
                        set(record) != {"sha256", "size"}
                        or record["sha256"] != digest
                    ):
                        raise ValueError("Invalid session object index")
                    name = "objects/" + digest
                    expected.add(name)
                    data = source.read(name)
                    if (
                        len(data) != record["size"]
                        or sha256(data).hexdigest() != digest
                    ):
                        raise ValueError("Session object hash mismatch")
                    session.put(data)
                if set(names) != expected:
                    raise ValueError("Unexpected or missing session member")
                data = source.read("database.sqlite")
                if sha256(data).hexdigest() != _digest(
                    index["database_sha256"]
                ):
                    raise ValueError("Session database hash mismatch")
                session._atomic(session.database, data)
                session._migrated = False
            with session.connection() as connection:
                if (
                    connection.execute("PRAGMA integrity_check").fetchone()[0]
                    != "ok"
                ):
                    raise ValueError("Session database failed integrity check")
                if connection.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError(
                        "Session database has unresolved references"
                    )
                stored = parse_json(
                    connection.execute(
                        "SELECT data FROM desktop_session WHERE id=1"
                    ).fetchone()[0]
                )
                if canonical_json(stored) != canonical_json(state):
                    raise ValueError("Session state differs from database")
            for digest in _references(state):
                session.get({"$asset": digest})
            session.update(**state)
            from .session_validation import validate_database

            with session.connection() as connection:
                validate_database(session, connection)
            session.state["budgets"] = {
                key: int(value) for key, value in budgets.items()
            }
            extraction = session.extraction()
            if extraction:
                for digest in _references(extraction):
                    session.get({"$asset": digest})
                if (
                    extraction["document"]["sha256"]
                    != session.state["source"]["$asset"]
                ):
                    raise ValueError("Extraction source identity differs")
            session.dirty = False
            if "source" in session.state:
                session.acquire(Path())
            return session
        except BaseException:
            shutil.rmtree(session.directory)
            raise
