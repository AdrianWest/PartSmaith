"""Desktop integration checks: python -m pytest scripts/verify_gui.py -v."""

import subprocess
import sys
import time
from threading import Event
from uuid import uuid4

import pytest
import wx

from partsmith.gui.app import KeyDialog, SetupFrame, banner_bytes
from partsmith.gui.credentials import CredentialStore


class Backend:
    def __init__(self):
        self.value = "dummy-saved-key"
        self.fail = False

    def get_password(self, *_args):
        return self.value

    def set_password(self, _service, _account, value):
        if self.fail:
            raise RuntimeError("dummy-secret-in-backend-error")
        self.value = value


@pytest.fixture(scope="session")
def app():
    result = wx.App(False)
    result.SetExitOnFrameDelete(False)
    return result


@pytest.fixture
def frame(app):
    result = SetupFrame(store=CredentialStore(backend=Backend()))
    result.Show()
    wx.Yield()
    yield result
    if result:
        result.Close()
        pump(lambda: not result)


def pump(condition, timeout=5):
    end = time.monotonic() + timeout
    errors = []
    app = wx.GetApp()
    pending = []
    active = True

    def check():
        if not active:
            return
        try:
            done = condition()
            if not done and time.monotonic() > end:
                raise AssertionError("GUI operation timed out")
        except Exception as error:
            errors.append(error)
            done = True
        if done:
            app.ExitMainLoop()
        else:
            pending.append(wx.CallLater(10, check))

    try:
        while not condition() and not errors:
            if time.monotonic() > end:
                raise AssertionError("GUI operation timed out")
            pending.append(wx.CallLater(10, check))
            app.MainLoop()
            for timer in pending:
                timer.Stop()
            pending.clear()
    finally:
        active = False
        for timer in pending:
            timer.Stop()
    if errors:
        raise errors[0]


def modal(dialog, operation):
    errors = []

    def run():
        try:
            operation()
        except Exception as error:
            errors.append(error)
            dialog.EndModal(wx.ID_CANCEL)

    wx.CallLater(25, run)
    result = dialog.ShowModal()
    if errors:
        raise errors[0]
    return result


def test_banner_and_layout_from_unrelated_working_directory(
    frame, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    assert banner_bytes().startswith(b"\x89PNG")
    assert frame.banner.image.IsOk()
    assert frame.banner.GetPosition().y == 0
    assert frame.banner.GetPosition().x == 0
    assert frame.banner.GetSize().width == frame.GetClientSize().width
    ratio = frame.banner.image.GetHeight() / frame.banner.image.GetWidth()
    assert (
        abs(
            frame.banner.GetSize().height
            - frame.banner.GetSize().width * ratio
        )
        <= 1
    )
    assert frame.part.GetPosition().y < frame.logs.GetPosition().y
    assert frame.logs.GetSize().height > 80
    assert not frame.logs.IsEditable()
    assert not frame.source.IsEditable()
    assert not frame.cancel.IsEnabled()
    assert "dummy-saved-key" not in frame.key_status.GetLabel()
    frame.SetSize((1050, 900))
    wx.Yield()
    assert frame.banner.GetSize().width == frame.GetClientSize().width
    assert (
        abs(
            frame.banner.GetSize().height
            - frame.banner.GetSize().width * ratio
        )
        <= 1
    )


def test_key_dialog_always_blank_and_masked_with_cancel(frame):
    for _ in range(2):
        with KeyDialog(frame, frame.store) as dialog:
            assert dialog.key.GetValue() == ""
            assert dialog.key.GetWindowStyle() & wx.TE_PASSWORD

            def cancel():
                dialog.key.ChangeValue("dummy-discarded-key")
                dialog.on_cancel(None)

            assert modal(dialog, cancel) == wx.ID_CANCEL
            assert dialog.key.GetValue() == ""
        assert frame.store.read_for_processing() == "dummy-saved-key"


def test_key_dialog_ok_persists_and_next_dialog_blank(frame):
    with KeyDialog(frame, frame.store) as dialog:

        def save():
            dialog.key.ChangeValue("dummy-replacement-key")
            dialog.on_save(None)

        assert modal(dialog, save) == wx.ID_OK
        assert dialog.key.GetValue() == ""
    assert frame.store.read_for_processing() == "dummy-replacement-key"
    with KeyDialog(frame, frame.store) as dialog:
        assert dialog.key.GetValue() == ""
    assert "dummy-replacement-key" not in frame.logs.GetValue()


def test_key_dialog_blank_or_save_failure_stays_open(frame):
    for failure in (False, True):
        frame.store.backend.fail = failure
        with KeyDialog(frame, frame.store) as dialog:

            def attempt(failure=failure):
                if failure:
                    dialog.key.ChangeValue("dummy-new-key")
                dialog.on_save(None)
                assert dialog.IsModal()
                assert dialog.message.GetLabel()
                assert "dummy-secret" not in dialog.message.GetLabel()
                assert frame.store.read_for_processing() == "dummy-saved-key"
                dialog.on_cancel(None)

            assert modal(dialog, attempt) == wx.ID_CANCEL


def test_file_selection_and_cancel_preserve_source(frame, monkeypatch):
    class FileDialog:
        result = wx.ID_OK

        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def ShowModal(self):
            return self.result

        def GetPath(self):
            return "selected-datasheet.pdf"

    monkeypatch.setattr(wx, "FileDialog", FileDialog)
    frame.on_file(None)
    assert frame.source.GetValue() == "selected-datasheet.pdf"
    FileDialog.result = wx.ID_CANCEL
    frame.on_file(None)
    assert frame.source.GetValue() == "selected-datasheet.pdf"


def fill(frame, tmp_path):
    source = tmp_path / "multiple-packages.pdf"
    source.write_bytes(b"%PDF-1.4\nSynthetic fixture")
    frame.source.ChangeValue(str(source))
    frame.part.ChangeValue("EXAMPLE-TSSOP-28R")
    return source


def test_running_controls_live_logs_and_cancel(frame, tmp_path):
    entered = Event()
    seen = []

    def worker(request, log, cancel):
        seen.append(request)
        log("Offline worker progress: dummy-saved-key")
        entered.set()
        assert cancel.wait(5)
        return "cancelled"

    frame.job.worker = worker
    source = fill(frame, tmp_path)
    frame.on_start(None)
    assert entered.wait(5)
    pump(lambda: "Offline worker progress" in frame.logs.GetValue())
    assert not frame.start.IsEnabled()
    assert not frame.key_button.IsEnabled()
    assert not frame.file_button.IsEnabled()
    assert not frame.part.IsEnabled()
    assert frame.cancel.IsEnabled()
    assert "dummy-saved-key" not in frame.logs.GetValue()
    frame.on_start(None)
    assert len(seen) == 1
    assert seen[0].part_number == "EXAMPLE-TSSOP-28R"
    assert seen[0].datasheet == source
    frame.on_cancel(None)
    pump(
        lambda: not frame.job.active and frame.status.GetLabel() == "Cancelled"
    )
    assert frame.start.IsEnabled()
    assert not frame.cancel.IsEnabled()
    assert frame.status.GetLabel() == "Cancelled"


@pytest.mark.parametrize("result", ["success", "failed", "unavailable"])
def test_job_terminal_statuses(frame, tmp_path, result):
    def worker(request, log, cancel):
        if result == "failed":
            raise RuntimeError("dummy-saved-key")
        return result

    frame.job.worker = worker
    fill(frame, tmp_path)
    frame.on_start(None)
    pump(lambda: frame.status.GetLabel() == result.capitalize())
    assert frame.status.GetLabel() == result.capitalize()
    assert "dummy-saved-key" not in frame.logs.GetValue()


def test_start_requires_part_number_and_valid_source(frame, tmp_path):
    import pymupdf

    frame.on_start(None)
    assert not frame.job.active
    assert "required part number" in frame.logs.GetValue()
    fill(frame, tmp_path)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "EXAMPLE-QFN-32R datasheet")
        pdf.save(frame.source.GetValue())
    frame.on_start(None)
    pump(lambda: frame.status.GetLabel() == "Unavailable")
    assert frame.status.GetLabel() == "Unavailable"
    assert "No component was built" in frame.logs.GetValue()


def test_window_close_waits_for_worker_cleanup(frame, tmp_path):
    entered = Event()
    cleaned = Event()

    def worker(request, log, cancel):
        entered.set()
        assert cancel.wait(5)
        cleaned.set()
        return "cancelled"

    frame.job.worker = worker
    fill(frame, tmp_path)
    frame.on_start(None)
    assert entered.wait(5)
    frame.Close()
    pump(lambda: not frame)
    assert cleaned.is_set()


def test_native_credential_store_persists_across_process_restart():
    # Unique service avoids touching the user's actual provider credentials.
    store = CredentialStore(provider=f"Phase9.5-test-{uuid4()}")
    dummy = "dummy-phase95-credential-not-a-live-key"
    try:
        store.save(dummy)
        script = (
            "import sys; "
            "from partsmith.gui.credentials import CredentialStore;"
            "value=CredentialStore(sys.argv[1]).read_for_processing();"
            "assert value == 'dummy-phase95-credential-not-a-live-key';"
            "print('Native credential restart PASS')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script, store.provider],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "restart PASS" in result.stdout
        assert dummy not in result.stdout + result.stderr
    finally:
        store._backend().delete_password(store.service, "api-key")
