"""@file verify_gui.py
@brief Verifies setup controls, credential storage and desktop launch behavior.
@details Uses isolated working sessions and explicit scripted test teardown.
"""

import subprocess
import sys
import time
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
import wx

from partsmith.gui.app import KeyDialog, SetupFrame, banner_bytes
from partsmith.gui.credentials import CredentialStore
from partsmith.gui.session import Session


class Backend:
    def __init__(self):
        """@brief Init.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
        self.value = "dummy-saved-key"
        self.fail = False

    def get_password(self, *_args):
        """@brief Get password.
        @param _args  args input.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
        return self.value

    def set_password(self, _service, _account, value):
        """@brief Set password.
        @param _service  service input.
        @param _account  account input.
        @param value Value input.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
        if self.fail:
            raise RuntimeError("dummy-secret-in-backend-error")
        self.value = value


@pytest.fixture(scope="session")
def app():
    """@brief App.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    result = wx.App(False)
    result.SetExitOnFrameDelete(False)
    return result


@pytest.fixture
def frame(app, tmp_path):
    """@brief Frame.
    @param app App input.
    @param tmp_path Isolated operational session root.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    result = SetupFrame(
        store=CredentialStore(backend=Backend()),
        session=Session(tmp_path / "sessions"),
        recover=False,
    )
    result.Show()
    wx.Yield()
    yield result
    if result:
        result.closing = True
        result.session.dirty = False
        result.Close()
        pump(lambda: not result)


def pump(condition, timeout=5):
    """@brief Pump.
    @param condition Condition input.
    @param timeout Timeout input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    end = time.monotonic() + timeout
    errors = []
    app = wx.GetApp()
    pending = []
    active = True

    def check():
        """@brief Check.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
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
    """@brief Modal.
    @param dialog Dialog input.
    @param operation Operation input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    errors = []

    def run():
        """@brief Run.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
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
    """@brief Test banner and layout from unrelated working directory.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @param monkeypatch Monkeypatch input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    monkeypatch.chdir(tmp_path)
    assert (
        banner_bytes()
        == (
            Path(__file__).resolve().parents[1]
            / "resources/PartSmith-Banner3.png"
        ).read_bytes()
    )
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
    for size in ((620, 740), (1050, 900), (1280, 960)):
        frame.SetSize(size)
        wx.Yield()
        assert frame.banner.ClientToScreen((0, 0)) == frame.ClientToScreen(
            (0, 0)
        )
        assert frame.banner.GetSize().width == frame.GetClientSize().width
        assert (
            abs(
                frame.banner.GetSize().height
                - frame.banner.GetSize().width * ratio
            )
            <= 1
        )
    for factor in (1, 1.25, 1.5, 2):
        bitmap = frame.banner.display_bitmap(540, factor)
        assert bitmap.GetWidth() == round(540 * factor)
        assert bitmap.GetScaleFactor() == factor
        assert abs(bitmap.GetHeight() - round(bitmap.GetWidth() * ratio)) <= 1


def test_key_dialog_always_blank_and_masked_with_cancel(frame):
    """@brief Test key dialog always blank and masked with cancel.
    @param frame Frame input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    for _ in range(2):
        with KeyDialog(frame, frame.store) as dialog:
            assert dialog.key.GetValue() == ""
            assert dialog.key.GetWindowStyle() & wx.TE_PASSWORD

            def cancel():
                """@brief Cancel.
                @return Result of this operation.
                @details Retains the documented processing and redaction
                contract.
                """
                dialog.key.ChangeValue("dummy-discarded-key")
                dialog.on_cancel(None)

            assert modal(dialog, cancel) == wx.ID_CANCEL
            assert dialog.key.GetValue() == ""
        assert frame.store.read_for_processing() == "dummy-saved-key"


def test_key_dialog_ok_persists_and_next_dialog_blank(frame):
    """@brief Test key dialog ok persists and next dialog blank.
    @param frame Frame input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    with KeyDialog(frame, frame.store) as dialog:

        def save():
            """@brief Save.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            dialog.key.ChangeValue("dummy-replacement-key")
            dialog.on_save(None)

        assert modal(dialog, save) == wx.ID_OK
        assert dialog.key.GetValue() == ""
    assert frame.store.read_for_processing() == "dummy-replacement-key"
    with KeyDialog(frame, frame.store) as dialog:
        assert dialog.key.GetValue() == ""
    assert "dummy-replacement-key" not in frame.logs.GetValue()


def test_key_dialog_blank_or_save_failure_stays_open(frame):
    """@brief Test key dialog blank or save failure stays open.
    @param frame Frame input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    for failure in (False, True):
        frame.store.backend.fail = failure
        with KeyDialog(frame, frame.store) as dialog:

            def attempt(failure=failure):
                """@brief Attempt.
                @param failure Failure input.
                @return Result of this operation.
                @details Retains the documented processing and redaction
                contract.
                """
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
    """@brief Test file selection and cancel preserve source.
    @param frame Frame input.
    @param monkeypatch Monkeypatch input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """

    class FileDialog:
        result = wx.ID_OK

        def __init__(self, *_args, **_kwargs):
            """@brief Init.
            @param _args  args input.
            @param _kwargs  kwargs input.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            pass

        def __enter__(self):
            """@brief Enter.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            return self

        def __exit__(self, *_args):
            """@brief Exit.
            @param _args  args input.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            pass

        def ShowModal(self):
            """@brief Showmodal.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            return self.result

        def GetPath(self):
            """@brief Getpath.
            @return Result of this operation.
            @details Retains the documented processing and redaction contract.
            """
            return "selected-datasheet.pdf"

    monkeypatch.setattr(wx, "FileDialog", FileDialog)
    frame.on_file(None)
    assert frame.source.GetValue() == "selected-datasheet.pdf"
    FileDialog.result = wx.ID_CANCEL
    frame.session.dirty = False
    frame.on_file(None)
    assert frame.source.GetValue() == "selected-datasheet.pdf"


def fill(frame, tmp_path):
    """@brief Fill.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    source = tmp_path / "multiple-packages.pdf"
    source.write_bytes(b"%PDF-1.4\nSynthetic fixture")
    frame.source.ChangeValue(str(source))
    frame.part.ChangeValue("EXAMPLE-TSSOP-28R")
    return source


def test_running_controls_live_logs_and_cancel(frame, tmp_path):
    """@brief Test running controls live logs and cancel.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    entered = Event()
    seen = []

    def worker(request, log, cancel):
        """@brief Worker.
        @param request Request input.
        @param log Log input.
        @param cancel Cancel input.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
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
        lambda: (
            not frame.job.active
            and not frame.actions.active
            and frame.status.GetLabel() == "Cancelled"
        )
    )
    assert frame.start.IsEnabled()
    assert not frame.cancel.IsEnabled()
    assert frame.status.GetLabel() == "Cancelled"


def test_provider_disclosure_local_default_and_candidate_retention(frame):
    """@brief Test provider disclosure local default and candidate retention.
    @param frame Frame input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    assert not frame.ai_enabled.GetValue()
    assert "gpt-4.1-mini-2025-04-14" in frame.ai_disclosure.GetLabel()
    assert "store=false" in frame.ai_disclosure.GetLabel()
    bundle = {"review_state": "UNREVIEWED", "candidate_evidence": []}
    frame.job.events.put(("candidates", bundle))
    frame.poll(None)
    assert frame.ai_candidates == bundle


def test_local_job_can_start_without_secure_store(frame, tmp_path):
    """@brief Test local job can start without secure store.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    from partsmith.gui.credentials import CredentialError

    def unavailable_store():
        """@brief Unavailable store.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
        raise CredentialError("Secure credential storage is unavailable.")

    frame.store.read_for_processing = unavailable_store
    frame.job.worker = lambda request, log, cancel: "unavailable"
    fill(frame, tmp_path)
    frame.on_start(None)
    pump(lambda: not frame.job.active)
    assert frame.status.GetLabel() == "Unavailable"


@pytest.mark.parametrize("result", ["success", "failed", "unavailable"])
def test_job_terminal_statuses(frame, tmp_path, result):
    """@brief Test job terminal statuses.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @param result Result input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """

    def worker(request, log, cancel):
        """@brief Worker.
        @param request Request input.
        @param log Log input.
        @param cancel Cancel input.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
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
    """@brief Test start requires part number and valid source.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
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


def test_window_close_waits_for_worker_cleanup(frame, tmp_path, monkeypatch):
    """@brief Test window close waits for worker cleanup.
    @param frame Frame input.
    @param tmp_path Tmp path input.
    @param monkeypatch Monkeypatch input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    entered = Event()
    cleaned = Event()

    def worker(request, log, cancel):
        """@brief Worker.
        @param request Request input.
        @param log Log input.
        @param cancel Cancel input.
        @return Result of this operation.
        @details Retains the documented processing and redaction contract.
        """
        entered.set()
        assert cancel.wait(5)
        cleaned.set()
        return "cancelled"

    frame.job.worker = worker
    fill(frame, tmp_path)
    frame.on_start(None)
    assert entered.wait(5)
    monkeypatch.setattr(frame, "transition", lambda callback: callback())
    frame.Close()
    pump(lambda: not frame)
    assert cleaned.is_set()


def test_native_credential_store_persists_across_process_restart():
    # Unique service avoids touching the user's actual provider credentials.
    """@brief Test native credential store persists across process restart.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
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
