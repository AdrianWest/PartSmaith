"""Phase 9.5 service contracts without requiring a desktop or wxPython."""

import importlib.util
import json
import sys
from pathlib import Path
from threading import Event

import pytest

from partsmith.gui.credentials import CredentialError, CredentialStore
from partsmith.gui.install_kicad import install
from partsmith.gui.processing import (
    JobController,
    ProcessingRequest,
    Redactor,
)


class MemoryBackend:
    def __init__(self):
        self.values = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, value):
        self.values[service, account] = value


@pytest.fixture
def processing_request(tmp_path):
    path = tmp_path / "multi-package.pdf"
    path.write_bytes(b"%PDF-1.4\nOffline synthetic multi-package fixture")
    return ProcessingRequest(path, "EXAMPLE-QFN-32R")


def finish(job):
    job.thread.join(timeout=5)
    assert not job.thread.is_alive(), "Worker did not finish"
    events = job.drain()
    assert not job.active
    return events


def test_secure_save_preserves_full_key_and_blank_does_not_replace():
    backend = MemoryBackend()
    store = CredentialStore(backend=backend)
    assert not store.configured()
    store.save("dummy-api-key-for-testing")
    with pytest.raises(CredentialError, match="nonblank"):
        store.save("  ")
    reopened = CredentialStore(backend=backend)
    assert reopened.configured()
    assert reopened.read_for_processing() == "dummy-api-key-for-testing"
    assert not CredentialStore("Other", backend).configured()


def test_backend_error_never_exposes_key():
    class Broken(MemoryBackend):
        def set_password(self, *_args):
            raise RuntimeError("dummy-secret-do-not-display")

        def get_password(self, *_args):
            raise RuntimeError("dummy-secret-do-not-display")

    store = CredentialStore(backend=Broken())
    for operation in (lambda: store.save("dummy"), store.configured):
        with pytest.raises(CredentialError) as error:
            operation()
        assert "dummy-secret" not in str(error.value)


@pytest.mark.parametrize("part", ["EXAMPLE-QFN-32R", "EXAMPLE-TSSOP-28R"])
def test_preserves_package_specific_requests(processing_request, part):
    seen = []

    def worker(value, log, cancel):
        seen.append(value)
        log("offline work complete")
        return "success"

    processing_request = ProcessingRequest(processing_request.datasheet, part)
    job = JobController(worker)
    job.start(processing_request)
    assert ("done", "success") in finish(job)
    assert seen == [processing_request]
    assert seen[0].part_number == part


@pytest.mark.parametrize("part", ["", "  "])
def test_rejects_missing_part(processing_request, part):
    with pytest.raises(ValueError, match="full required part number"):
        ProcessingRequest(processing_request.datasheet, part).validate()


def test_rejects_missing_invalid_and_non_pdf_files(tmp_path):
    for filename, data in [
        ("missing.pdf", None),
        ("bad.pdf", b"not a PDF"),
        ("wrong.txt", b"%PDF-1.4"),
    ]:
        path = tmp_path / filename
        if data is not None:
            path.write_bytes(data)
        with pytest.raises(ValueError):
            ProcessingRequest(path, "EXAMPLE-QFN").validate()


def test_cancel_and_duplicate_start_while_progress_streams(processing_request):
    entered = Event()

    def worker(value, log, cancel):
        log("Working on package selection")
        entered.set()
        assert cancel.wait(5)
        return "cancelled"

    job = JobController(worker)
    job.start(processing_request)
    assert entered.wait(5)
    assert ("log", "Working on package selection") in job.drain()
    with pytest.raises(ValueError, match="already running"):
        job.start(processing_request)
    job.cancel()
    assert ("done", "cancelled") in finish(job)
    job.worker = lambda *_args: "success"
    job.start(processing_request)
    assert ("done", "success") in finish(job)


def test_worker_failure_and_logs_do_not_leak_credentials(processing_request):
    secret = "dummy-token-never-in-logs"

    def worker(value, log, cancel):
        log(f"unexpected output: {secret}")
        raise RuntimeError(secret)

    job = JobController(worker)
    job.start(processing_request, secrets=(secret,))
    events = finish(job)
    assert ("done", "failed") in events
    assert secret not in str(events)
    assert "[REDACTED]" in str(events)


def test_redacts_authorization_and_api_key_fields():
    redact = Redactor()
    for message in (
        "Authorization: Bearer dummy-token",
        "api_key=dummy-token",
        "BFT_TOKEN: dummy-token",
        "sk-dummy-token",
    ):
        assert "dummy-token" not in redact(message)


def test_unavailable_stages_do_not_report_success(processing_request):
    # Phase 10 now parses the PDF; use an actual document at this boundary.
    import pymupdf

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "EXAMPLE-QFN-32R datasheet")
        pdf.save(processing_request.datasheet)
    job = JobController()
    job.start(processing_request)
    events = finish(job)
    assert ("done", "unavailable") in events
    assert "No component was built" in str(events)
    assert ("done", "success") not in events


def test_kicad_launch_uses_external_runtime_and_removes_embedded_paths(
    tmp_path, monkeypatch
):
    import types

    registered = []

    class ActionPlugin:
        def register(self):
            registered.append(self)

    monkeypatch.setitem(
        sys.modules, "pcbnew", types.SimpleNamespace(ActionPlugin=ActionPlugin)
    )
    monkeypatch.setitem(
        sys.modules,
        "wx",
        types.SimpleNamespace(
            MessageBox=lambda *_args: pytest.fail("Unexpected launch error"),
            OK=1,
            ICON_ERROR=2,
        ),
    )
    source = Path(__file__).resolve().parents[1] / "integrations" / "kicad"
    plugin = tmp_path / "__init__.py"
    plugin.write_bytes(
        (source / "partsmith_setup" / "__init__.py").read_bytes()
    )
    (tmp_path / "launcher.json").write_text(
        json.dumps({"python": sys.executable}), encoding="utf-8"
    )
    spec = importlib.util.spec_from_file_location("launch_plugin_test", plugin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("PYTHONHOME", "embedded-kicad-home")
    monkeypatch.setenv("PYTHONPATH", "embedded-kicad-path")
    calls = []
    monkeypatch.setattr(
        module.subprocess, "Popen", lambda *a, **k: calls.append((a, k))
    )
    registered[0].Run()
    args, kwargs = calls[0]
    assert args[0] == [sys.executable, "-m", "partsmith.gui"]
    assert "PYTHONHOME" not in kwargs["env"]
    assert "PYTHONPATH" not in kwargs["env"]
    assert kwargs["cwd"] == tmp_path


def test_installer_copies_launch_only_plugin_and_runtime_path(tmp_path):
    target = install(tmp_path, sys.executable)
    assert json.loads((target / "launcher.json").read_text("utf-8")) == {
        "python": sys.executable
    }
    assert (target / "__init__.py").is_file()
    assert not (target / "__pycache__").exists()
    assert not (target / "app.py").exists()
    assert not (target / "credentials.py").exists()


def test_installer_rejects_missing_runtime_without_writing(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        install(tmp_path, tmp_path / "missing-python.exe")
    assert not (tmp_path / "partsmith_setup").exists()
