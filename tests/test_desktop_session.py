"""@package tests.test_desktop_session
@brief Verifies isolated unfinished-session save, load and recovery.
@details Exercises immutable acquisition, hostile transport and atomic writes.
"""

import zipfile
from hashlib import sha256
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest

from partsmith.gui.actions import ActionController
from partsmith.gui.session import Session
from partsmith.ir.canonical import canonical_json, parse_json


def sample(tmp_path):
    """@brief Creates an unfinished setup and retained local extraction.
    @param tmp_path Temporary filesystem root.
    @return Session and original source path.
    @details A tiny PDF header is sufficient for transport-only checks.
    """
    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.4\nimmutable source")
    session = Session(tmp_path / "storage")
    session.update(setup={"source_path": str(source), "part_number": "FULL-R"})
    session.acquire(source)
    digest = sha256(source.read_bytes()).hexdigest()
    session.retain_extraction(
        {
            "document": {"sha256": digest},
            "evidence": [{"id": "local-original"}],
            "assets": {},
        }
    )
    return session, source


def test_local_extraction_survives_source_loss_and_repeated_load(tmp_path):
    """@brief Checks offline restart and isolated repeated loads.
    @param tmp_path Temporary filesystem root.
    @return None.
    @details Historical identifiers remain unchanged across fresh instances.
    """
    session, source = sample(tmp_path)
    archive = tmp_path / "unfinished.partsmith"
    session.save(archive)
    source.unlink()
    loaded = Session.load(archive, root=tmp_path / "other")
    second = Session.load(archive, root=tmp_path / "other")
    assert (
        len({session.instance_id, loaded.instance_id, second.instance_id}) == 3
    )
    assert loaded.database != second.database
    assert loaded.state["acquisition_id"] == session.state["acquisition_id"]
    assert loaded.extraction() == session.extraction()
    assert (
        loaded.acquire(Path("missing.pdf")).read_bytes().startswith(b"%PDF-")
    )
    loaded.update(status="failed")
    assert second.state["status"] == "extracted"


def test_snapshot_never_follows_changed_original_path(tmp_path):
    """@brief Checks immutable source provenance after path changes.
    @param tmp_path Temporary filesystem root.
    @return None.
    @details Reacquisition requires a new explicitly selected session.
    """
    session, source = sample(tmp_path)
    original = session.acquire(source).read_bytes()
    source.write_bytes(b"%PDF-1.4\nchanged")
    assert session.acquire(source).read_bytes() == original


def rewrite(archive, name, transform):
    """@brief Rewrites one archive member for hostile-input testing.
    @param archive Session transport path.
    @param name Member to modify.
    @param transform Transformation of its exact bytes.
    @return None.
    @details Preserves other entries to isolate validation failure causes.
    """
    with zipfile.ZipFile(archive) as source:
        objects = {item: source.read(item) for item in source.namelist()}
    objects[name] = transform(objects[name])
    with zipfile.ZipFile(archive, "w") as output:
        for key, value in objects.items():
            output.writestr(key, value)


@pytest.mark.parametrize(
    "fault", ["object", "version", "reference", "database", "extra"]
)
def test_bad_archive_is_staged_without_modifying_current_session(
    tmp_path, fault
):
    """@brief Rejects tampered bytes, versions and unresolved references.
    @param tmp_path Temporary filesystem root.
    @param fault Specific archive fault to inject.
    @return None.
    @details Failed staging is removed and the current instance remains usable.
    """
    session, _ = sample(tmp_path)
    archive = tmp_path / "session.partsmith"
    session.save(archive)
    before = session.database.read_bytes()
    if fault == "object":
        rewrite(
            archive,
            "objects/" + session.state["source"]["$asset"],
            lambda _: b"tampered",
        )
    elif fault == "database":
        rewrite(archive, "database.sqlite", lambda _: b"tampered")
    elif fault == "extra":
        with zipfile.ZipFile(archive, "a") as output:
            output.writestr("../outside", b"bad")
    else:

        def change(data):
            """@brief Injects one invalid index field.
            @param data Original index bytes.
            @return Modified canonical index bytes.
            @details Version and reference validation must fail closed.
            """
            index = parse_json(data)
            if fault == "version":
                index["schema_version"] = "future-99"
            else:
                index["state"]["source"] = {"$asset": "0" * 64}
            return canonical_json(index)

        rewrite(archive, "index.json", change)
    with pytest.raises((ValueError, FileNotFoundError)):
        Session.load(archive, root=session.storage)
    assert session.database.read_bytes() == before
    assert len(list(session.storage.glob("*/working.sqlite"))) == 1


def test_atomic_save_failure_retains_last_good_checkpoint(
    tmp_path, monkeypatch
):
    """@brief Checks interrupted replacement preserves durable recovery bytes.
    @param tmp_path Temporary filesystem root.
    @param monkeypatch Temporary fault injection fixture.
    @return None.
    @details Save failure leaves both the active state and previous archive.
    """
    session, _ = sample(tmp_path)
    archive = session.storage / "recovery.partsmith"
    before = archive.read_bytes()
    session.update(drafts={"pending": "exact decimal 0.1000000001"})

    def fail(*args):
        """@brief Simulates interruption before the atomic replacement.
        @param args Replacement arguments.
        @return None.
        @details Always raises without changing the destination.
        """
        raise OSError("interrupted")

    monkeypatch.setattr("partsmith.gui.session.os.replace", fail)
    with pytest.raises(OSError):
        session.checkpoint()
    assert archive.read_bytes() == before
    assert not list(session.storage.glob(".staged-*"))


def test_credentials_excluded_from_settings_logs_and_archive(tmp_path):
    """@brief Checks known and credential-shaped secrets cannot persist.
    @param tmp_path Temporary filesystem root.
    @return None.
    @details Metadata credentials are rejected and log text is redacted.
    """
    secret = "dummy-secret-12.2"
    session = Session(tmp_path / "storage", secrets=(secret,))
    session.update(logs=[secret, "Authorization: Bearer dummy-token"])
    with pytest.raises(ValueError, match="Credentials"):
        session.update(setup={"api_key": secret})
    archive = tmp_path / "session.partsmith"
    session.save(archive)
    with zipfile.ZipFile(archive) as source:
        assert all(
            secret.encode() not in source.read(name)
            for name in source.namelist()
        )


def test_background_serialization_and_committed_outcome(tmp_path):
    """@brief Checks busy exclusion and cancellation after commit.
    @param tmp_path Temporary filesystem root.
    @return None.
    @details A committed decision reports success instead of false cancel.
    """
    session = Session(tmp_path / "storage")
    controller = ActionController()
    entered, finish = Event(), Event()

    def operation(current, cancel, emit):
        """@brief Simulates a worker-owned committed operation.
        @param current Isolated session.
        @param cancel Cancellation event.
        @param emit Progress callback.
        @return Persisted decision identity.
        @details Late cancellation does not rewrite the successful result.
        """
        entered.set()
        assert finish.wait(5)
        current.update(history=["committed-decision"])
        cancel.set()
        return "committed-decision"

    controller.start(session, "review", operation)
    assert entered.wait(5)
    with pytest.raises(ValueError, match="unavailable"):
        session.save(tmp_path / "busy.partsmith")
    with pytest.raises(ValueError, match="already"):
        controller.start(session, "another", operation)
    finish.set()
    events = []
    deadline = monotonic() + 10
    while controller.active and monotonic() < deadline:
        events.extend(controller.drain())
        sleep(0.01)
    events.extend(controller.drain())
    assert not controller.active
    assert events[-1].outcome == "success"
    assert events[-1].payload == "committed-decision"
    assert all(event.instance == session.instance_id for event in events)


def test_checkpoint_only_failure_preserves_engineering_status(
    tmp_path, monkeypatch
):
    """@brief Reports a failed recovery-only action without false success.
    @param tmp_path Temporary working-session storage.
    @param monkeypatch Scoped recovery-storage failure adapter.
    @return None.
    @details The checkpoint attempt cannot relabel previously committed work.
    """
    session = Session(tmp_path / "storage")
    session.update(status="inputs-reviewed", history=["committed-decision"])
    controller = ActionController()

    def fail_checkpoint():
        """@brief Injects unavailable recovery storage.
        @return None.
        @details Raises before replacing the last good archive.
        """
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(session, "checkpoint", fail_checkpoint)
    controller.start(session, "checkpoint", lambda *args: None)
    controller.thread.join(10)
    assert not controller.thread.is_alive()
    events = controller.drain()
    assert events[-1].outcome == "failed"
    assert events[-1].code == "CHECKPOINT_ERROR"
    session.refresh()
    assert session.state["status"] == "inputs-reviewed"
    assert session.state["history"] == ["committed-decision"]
