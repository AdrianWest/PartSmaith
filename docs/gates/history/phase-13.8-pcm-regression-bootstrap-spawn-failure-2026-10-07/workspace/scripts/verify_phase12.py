"""@file verify_phase12.py
@brief Verifies Phase 12 controls in an actual wx desktop.
@details Injectable dialogs exercise user choices without unattended prompts.
"""

import json
import os
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
import wx

from partsmith.gui.app import SetupFrame
from partsmith.gui.credentials import CredentialStore
from partsmith.gui.processing import JobController
from partsmith.gui.session import Session
from partsmith.ir import canonical_json
from scripts.verify_gui import Backend, pump


def capture(window, name):
    """@brief Captures actual displayed pixels for final visual inspection.
    @param window Actual foreground wx window or viewport.
    @param name Evidence artifact name within the configured gate directory.
    @return None.
    @details Capture is optional for ordinary repeated desktop unit checks.
    """
    directory = os.environ.get("PARTSMITH_GATE_CAPTURE")
    if not directory:
        return
    top = window.GetTopLevelParent()
    top.Refresh()
    top.Update()
    wx.Yield()
    width, height = window.GetClientSize()
    bitmap = wx.Bitmap(width, height)
    memory = wx.MemoryDC(bitmap)
    x, y = window.ClientToScreen((0, 0))
    memory.Blit(0, 0, width, height, wx.ScreenDC(), x, y)
    memory.SelectObject(wx.NullBitmap)
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    assert bitmap.SaveFile(str(path / name), wx.BITMAP_TYPE_PNG)


@pytest.fixture(scope="session")
def app():
    """@brief Creates the actual wx application for desktop checks.
    @return Shared wx application.
    @details Keeps the event loop alive between owned frames.
    """
    application = wx.GetApp() or wx.App(False)
    application.SetExitOnFrameDelete(False)
    return application


@pytest.fixture
def frame(app, tmp_path):
    """@brief Opens an isolated desktop without startup recovery prompts.
    @param app Actual wx application.
    @param tmp_path Temporary working-session root.
    @return SetupFrame through fixture yield.
    @details Teardown waits for worker and owned-window cleanup.
    """
    result = SetupFrame(
        store=CredentialStore(backend=Backend()),
        session=Session(tmp_path / "sessions"),
        recover=False,
    )
    result.Show()
    wx.Yield()
    yield result
    result.session.dirty = False
    result.closing = True
    result.Close()
    pump(lambda: not result, timeout=15)


class Dialog:
    """@brief Supplies explicit scripted chooser outcomes.
    @details Models cancel without silently selecting the recommended choice.
    """

    choice = wx.ID_CANCEL
    path = ""

    def __init__(self, *args, **kwargs):
        """@brief Accepts the real dialog constructor arguments.
        @param args Positional dialog arguments.
        @param kwargs Named dialog arguments.
        @return None.
        @details No native modal window is opened during automation.
        """

    def __enter__(self):
        """@brief Returns this scoped scripted dialog.
        @return This Dialog instance.
        @details Matches native wx context-manager behavior.
        """
        return self

    def __exit__(self, *args):
        """@brief Leaves the scripted dialog scope.
        @param args Exception context arguments.
        @return None.
        @details Does not suppress test failures.
        """

    def ShowModal(self):
        """@brief Returns the deliberately scripted user decision.
        @return wx modal result identifier.
        @details Cancellation is the default.
        """
        return self.choice

    def GetPath(self):
        """@brief Returns the deliberately selected transport path.
        @return Filesystem path text.
        @details No default path is invented by the test adapter.
        """
        return self.path

    def SetYesNoCancelLabels(self, *args):
        """@brief Accepts the production unsaved-work labels.
        @param args Save, Discard and Cancel labels.
        @return None.
        @details Leaves the scripted choice unchanged.
        """


def test_session_buttons_async_save_load_and_cancel(
    frame, tmp_path, monkeypatch
):
    """@brief Exercises unfinished setup, offline load and Cancel choices.
    @param frame Actual wx setup frame.
    @param tmp_path Temporary source and transport paths.
    @param monkeypatch Scoped chooser replacement.
    @return None.
    @details Save and Load disable while busy and do not trigger processing.
    """
    source = tmp_path / "datasheet.pdf"
    source.write_bytes(b"%PDF-1.4\nretained setup")
    frame.source.ChangeValue(str(source))
    frame.part.ChangeValue("FULL-SUFFIX-32R")
    frame.on_setup_changed(None)
    monkeypatch.setattr(wx, "FileDialog", Dialog)
    monkeypatch.setattr(wx, "MessageDialog", Dialog)
    Dialog.choice = wx.ID_CANCEL
    current = frame.session
    frame.on_clear_session(None)
    assert frame.session is current
    frame.on_save_session(None)
    assert not frame.actions.active
    Dialog.choice = wx.ID_OK
    Dialog.path = str(tmp_path / "unfinished.partsmith")
    frame.on_save_session(None)
    assert frame.actions.active
    assert not frame.load_button.IsEnabled()
    pump(lambda: not frame.actions.active, timeout=15)
    assert Path(Dialog.path).exists()
    assert not frame.session.dirty
    source.unlink()
    frame.on_load_session(None)
    pump(lambda: not frame.actions.active, timeout=15)
    assert frame.session.instance_id != current.instance_id
    assert frame.part.GetValue() == "FULL-SUFFIX-32R"
    assert frame.session.state["source"] == current.state["source"]
    assert not frame.job.active
    assert frame.save_button.IsEnabled()


def inspect_production_viewer(frame):
    """@brief Checks the actual generated viewer without a banner.
    @param frame Main frame with retained actual generation artifacts.
    @return None.
    @details Singleton and camera reopen behavior survive native cleanup.
    """
    assert frame.viewer_button.IsEnabled()
    frame.on_viewer(None)
    viewer = frame.viewer
    assert viewer is not None, frame.logs.GetValue()
    frame.on_viewer(None)
    assert frame.viewer is viewer
    pump(lambda: viewer.metadata is not None or viewer.failed, timeout=45)
    assert not viewer.failed
    assert not hasattr(viewer, "banner")
    for size in ((540, 420), (1000, 800), (740, 620)):
        viewer.SetSize(size)
        wx.Yield()
        assert viewer.review_views.GetPosition() == (0, 0)
        assert viewer.review_views.GetSize() == viewer.GetClientSize()
    from partsmith.gui.inspection import PRESETS, distance_mm

    original = canonical_json(frame.session.state["drafts"]["ir"])
    artifacts = canonical_json(frame.session.state["drafts"]["artifacts"])
    release = canonical_json(frame.session.state["release"])
    for name, angles in PRESETS.items():
        viewer.inspection.preset(name)
        assert (viewer.camera["yaw"], viewer.camera["elevation"]) == angles
    for key, control in viewer.inspection.layers.items():
        control.SetValue(False)
        viewer.inspection.layer(key)
        assert viewer.camera["layers"][key] is False
        control.SetValue(True)
        viewer.inspection.layer(key)
    assert distance_mm(viewer.inspection.pads, "1", "2") == pytest.approx(1)
    assert "Pin mapping:" in viewer.inspection.measurement.GetLabel()
    assert viewer.binding["pins"][0]["number"] == "1"
    assert viewer.metadata["bounds_mm"][1][2] == pytest.approx(0.35)
    assert viewer.metadata["graphics"]
    symbol = viewer.symbol_panel
    assert symbol.report is not None
    assert symbol.preview.svg is not None
    assert symbol.bytes.GetValue().encode() == symbol.report["content"]
    assert symbol.pins.GetItemCount() == 2
    assert all(
        row["diagnostic"] == "MATCH" for row in symbol.report["mapping"]
    )
    viewer.review_views.SetSelection(1)
    wx.Yield()
    for size in ((540, 420), (1000, 800), (740, 620)):
        viewer.SetSize(size)
        wx.Yield()
        assert symbol.preview.GetSize().width <= symbol.GetClientSize().width
    symbol.pins.Select(1)
    wx.Yield()
    assert viewer.camera["selected_pad"] == "2"
    symbol.mark_current(True)
    assert "STALE" in symbol.summary.GetLabel()
    symbol.mark_current(False)
    capture(viewer, "phase-12-symbol-inspection.png")
    viewer.review_views.SetSelection(0)
    viewer.inspection.preset("Isometric")
    revision = viewer.revision
    pump(lambda: viewer.frame_revision == revision, timeout=20)
    capture(viewer, "phase-12-viewer.png")
    capture(viewer.viewport, "phase-12-viewport.png")
    viewer.editor.entries["translation_mm"][0].SetFocus()
    viewer.scroll.Scroll(0, 1000)
    wx.Yield()
    capture(viewer, "phase-12-viewer-controls.png")
    assert canonical_json(frame.session.state["drafts"]["ir"]) == original
    assert (
        canonical_json(frame.session.state["drafts"]["artifacts"]) == artifacts
    )
    assert canonical_json(frame.session.state["release"]) == release
    editor = viewer.editor
    editor.entries["translation_mm"][0].SetValue("0.1234567890123456789")
    editor.entries["translation_mm"][2].SetValue("0.2")
    editor.entries["rotation_deg"][2].SetValue("90")
    editor.mirrors["x"].SetValue(True)
    editor.preview(None)
    assert "UNAPPROVED DRAFT" in editor.feedback.GetLabel()
    assert "HEIGHT:" in editor.feedback.GetLabel()
    assert "MIRROR:" in editor.feedback.GetLabel()
    pump(lambda: viewer.metadata is not None or viewer.failed, timeout=45)
    assert not viewer.failed
    assert canonical_json(frame.session.state["drafts"]["ir"]) == original
    assert canonical_json(frame.session.state["release"]) == release
    editor.discard(None)
    assert editor.draft.value == editor.draft.reviewed
    assert editor.entries["scale"][0].GetValue() == str(
        editor.draft.reviewed["scale"][0]
    )
    viewer.camera["yaw"] = 72.0
    viewer.review_views.SetSelection(1)
    viewer.Close()
    pump(lambda: frame.viewer is None, timeout=15)
    frame.on_viewer(None)
    assert frame.viewer.camera["yaw"] == 72.0
    assert frame.viewer.review_views.GetSelection() == 1
    assert (
        frame.viewer.symbol_panel.report["content"] == symbol.report["content"]
    )
    from copy import deepcopy

    from partsmith.gui.symbol_panel import SymbolInspectionPanel

    retained = deepcopy(frame.session.state["drafts"])
    for malformed in (False, True):
        drafts = deepcopy(retained)
        item = next(
            item
            for item in drafts["artifacts"]
            if item["type"] == "SYMBOL" and item["stage"] == "FINAL"
        )
        if malformed:
            content = b"(broken symbol"
            item["reference"] = frame.session.put(content)
            item["sha256"] = sha256(content).hexdigest()
        else:
            drafts["artifacts"].remove(item)
        frame.session.update(drafts=drafts)
        diagnostic = SymbolInspectionPanel(
            frame.viewer.review_views, frame.viewer
        )
        assert diagnostic.report is None
        assert "unavailable" in diagnostic.results.GetValue()
        diagnostic.Destroy()
    frame.session.update(drafts=retained)
    frame.viewer.Close()
    pump(lambda: frame.viewer is None, timeout=15)


def test_save_failure_never_runs_pending_transition(
    frame, tmp_path, monkeypatch
):
    """@brief Checks failed saving cannot discard the current session.
    @param frame Actual wx setup frame.
    @param tmp_path Temporary transport path.
    @param monkeypatch Scoped atomic-write fault injection.
    @return None.
    @details The pending transition is cleared and unfinished state remains.
    """
    monkeypatch.setattr(wx, "FileDialog", Dialog)
    Dialog.choice, Dialog.path = wx.ID_OK, str(tmp_path / "failed.partsmith")
    current = frame.session

    def fail(destination, content):
        """@brief Fails the atomic transport replacement.
        @param destination Intended output path.
        @param content Staged output bytes.
        @return None.
        @details Simulates failure before an unsaved-work transition.
        """
        raise OSError("write failed")

    monkeypatch.setattr(current, "_atomic_copy", fail)
    frame.choose_save(
        lambda: frame.replace_session(Session(tmp_path / "other"))
    )
    pump(lambda: not frame.actions.active, timeout=15)
    assert frame.session is current
    assert frame.after_save is None
    assert "write failed" in frame.logs.GetValue()


@pytest.mark.parametrize(
    "choice", ["cancel", "discard", "save", "save-failure", "save-cancel"]
)
def test_bound_part_and_new_component_unsaved_policy(
    frame, tmp_path, monkeypatch, choice
):
    """@brief Switches ordering numbers only through the component policy.
    @param frame Actual wx setup and review window.
    @param tmp_path Temporary datasheet, reviewed session and saved transport.
    @param monkeypatch Scoped dialogs, worker and save-failure adapters.
    @param choice Explicit unsaved-work and destination-chooser choices.
    @return None.
    @details Cancel/failed Save preserve the old identity and retained history;
    successful Save/Discard creates fresh review data for the same datasheet.
    """
    from test_desktop_review import fielded_session

    original, _review = fielded_session(tmp_path)
    history = canonical_json(original.state["history"])
    source = original.directory / "source.pdf"
    source_bytes = source.read_bytes()
    original_part = original.state["setup"]["part_number"]
    frame.replace_session(original)
    assert not frame.part.IsEnabled()
    frame.part.SetValue("DIFFERENT-ORDERING-NUMBER")
    assert frame.part.GetValue() == original_part
    assert original.state["setup"]["part_number"] == original_part
    requests = []

    def worker(request, log, cancel):
        """@brief Records processing of an explicitly new component.
        @param request Actual full ordering-number and datasheet request.
        @param log Unused redacted progress callback.
        @param cancel Unused cooperative cancellation event.
        @return Successful operational status.
        @details Uses no provider and never returns engineering artifacts.
        """
        requests.append((request.part_number, request.datasheet.read_bytes()))
        return "success"

    frame.job = JobController(worker)
    frame.part.ChangeValue("DIFFERENT-ORDERING-NUMBER")
    frame.on_start(None)
    assert not frame.job.active
    assert not requests
    assert "Use New / Clear Component" in frame.logs.GetValue()
    frame.part.ChangeValue(original_part)

    class UnsavedDialog(Dialog):
        """@brief Supplies an explicit unsaved-component decision.
        @details Only Save and Discard may advance the component transition.
        """

    class SaveDialog(Dialog):
        """@brief Supplies an explicit session destination decision.
        @details A cancelled destination preserves the current component.
        """

    UnsavedDialog.choice = {
        "cancel": wx.ID_CANCEL,
        "discard": wx.ID_NO,
    }.get(choice, wx.ID_YES)
    SaveDialog.choice = wx.ID_CANCEL if choice == "save-cancel" else wx.ID_OK
    SaveDialog.path = str(tmp_path / "before-new-component.partsmith")
    monkeypatch.setattr(wx, "MessageDialog", UnsavedDialog)
    monkeypatch.setattr(wx, "FileDialog", SaveDialog)

    def fail_save(destination, content):
        """@brief Fails the explicit save before a new-component transition.
        @param destination Selected session transport destination.
        @param content Staged complete archive path.
        @return None.
        @details Leaves the original component and previous saved file intact.
        """
        raise OSError("new-component save failure")

    if choice == "save-failure":
        monkeypatch.setattr(original, "_atomic_copy", fail_save)
    frame.on_clear_session(None)
    pump(lambda: not frame.actions.active, timeout=15)
    if choice in {"cancel", "save-failure", "save-cancel"}:
        assert frame.session is original
        assert frame.part.GetValue() == original_part
        assert not frame.part.IsEnabled()
        assert not requests
    else:
        pump(lambda: frame.session is not original, timeout=15)
        assert frame.part.IsEnabled()
        assert not any(
            key in frame.session.state
            for key in ("component_id", "revision_id", "pdl", "release")
        )
        if choice == "save":
            restored = Session.load(
                Path(SaveDialog.path), root=tmp_path / "saved-old-component"
            )
            assert restored.state["setup"]["part_number"] == original_part
            assert canonical_json(restored.state["history"]) == history
        frame.source.ChangeValue(str(source))
        frame.part.SetValue("DIFFERENT-ORDERING-NUMBER")
        frame.on_start(None)
        pump(
            lambda: not frame.job.active and not frame.actions.active,
            timeout=15,
        )
        assert requests == [("DIFFERENT-ORDERING-NUMBER", source_bytes)]
        assert "component_id" not in frame.session.state
    assert canonical_json(original.state["history"]) == history


def test_real_input_commit_and_checkpoint_warning_update_main_status(
    frame, tmp_path, monkeypatch
):
    """@brief Shows a committed input decision after late cancellation.
    @param frame Actual wx main window and shared log surface.
    @param tmp_path Isolated unreviewed input session.
    @param monkeypatch Scoped recovery-storage failure adapter.
    @return None.
    @details Success and a recovery warning replace the Cancelling label.
    """
    from test_desktop_review import fielded_session

    from partsmith.gui.review_service import DesktopReview

    session, review = fielded_session(tmp_path, review_inputs=False)
    review.propose_evidence("Inspect exact original acquisition inventory")
    frame.replace_session(session)

    def operation(current, cancel, emit):
        """@brief Commits one real explicit input decision.
        @param current Isolated reviewed component session.
        @param cancel Cooperative action cancellation signal.
        @param emit Unused redacted service progress callback.
        @return Immutable committed review result.
        @details Cancelling is injected after the atomic transaction completes.
        """
        result = DesktopReview(current).decide_inputs(
            True, "Inspected exact input revision"
        )
        cancel.set()
        return result

    def fail_checkpoint():
        """@brief Injects unavailable recovery archive storage.
        @return None.
        @details Leaves the working decision and earlier checkpoints intact.
        """
        raise OSError("checkpoint storage unavailable")

    monkeypatch.setattr(session, "checkpoint", fail_checkpoint)
    frame.checkpoint_due = None
    frame.actions.start(session, "input review", operation)
    frame.set_running(True)
    frame.status.SetLabel("Cancelling…")
    pump(lambda: not frame.actions.active, timeout=15)
    assert session.state["status"] == "inputs-reviewed"
    assert frame.status.GetLabel() == "Inputs-reviewed"
    assert "[input review/success] Completed" in frame.logs.GetValue()
    assert "CHECKPOINT_ERROR" not in frame.status.GetLabel()
    assert "Recovery checkpoint failed" in frame.logs.GetValue()
    assert not frame.part.IsEnabled()
    assert session.state["history"][-1]["kind"] == "INPUT_APPROVE"


def test_original_evidence_overlay_and_explicit_ai_preview(frame, tmp_path):
    """@brief Inspects original text, source overlay and AI disclosure.
    @param frame Actual wx desktop frame.
    @param tmp_path Temporary source snapshot path.
    @return None.
    @details Request preview makes no provider call or source changes.
    """
    from PIL import Image

    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.4\nretained original")
    session = frame.session
    session.acquire(source)
    session.update(setup={"part_number": "FULL-SUFFIX-32R"})
    content = BytesIO()
    Image.new("RGB", (100, 100), "white").save(content, format="PNG")
    reference = session.put(content.getvalue())
    record = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "fixtures/ir/v1.2/valid/0402.json"
        ).read_text()
    )["evidence"][0]
    record["source"].update(
        document_hash=sha256(source.read_bytes()).hexdigest(),
        page=1,
        region={"x": 10, "y": 10, "width": 20, "height": 20},
        coordinate_convention="document-page-1.0",
        page_geometry={
            "media_box": [0, 0, 100, 100],
            "crop_box": [0, 0, 100, 100],
            "user_unit": 1,
            "rotation_deg": 0,
        },
    )
    record["extracted"]["text"] = "Original untranslated source text"
    record["interpretation"]["status"] = "UNKNOWN"
    record["candidate_targets"] = []
    render = {
        "image_sha256": reference["$asset"],
        "width_px": 100,
        "height_px": 100,
        "pixel_to_page": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }
    extraction = {
        "document": {
            "sha256": session.state["source"]["$asset"],
            "page_count": 1,
        },
        "selected_pages": [1],
        "evidence": [record],
        "pages": [{"page": 1, "render_transform": render}],
        "assets": {reference["$asset"]: reference},
    }
    session.update(extraction=session.put(canonical_json(extraction)))
    frame.review.refresh_session()
    pump(lambda: bool(frame.review.evidence.records), timeout=15)
    frame.review.evidence.Select(0)
    pump(lambda: frame.review.image.image is not None, timeout=15)
    assert (
        "Original untranslated source text" in frame.review.original.GetValue()
    )
    assert frame.review.image.image is not None
    assert frame.review.image.region["x"] == 10
    frame.review.on_preview(None)
    assert "1 records" in frame.review.request_info.GetLabel()
    assert "canonical bytes" in frame.review.request_info.GetLabel()
    assert not frame.actions.active
    assert (
        session.extraction()["evidence"][0]["extracted"]["text"]
        == record["extracted"]["text"]
    )
    component = frame.review.component
    component.editor.ChangeValue("{}")
    component.on_assemble(None)
    pump(lambda: not frame.actions.active, timeout=15)
    assert frame.session.state["drafts"]["ir"]["pins"] == []
    assert "Authenticated reviewer:" in component.actor.GetLabel()
    component.reason.SetValue("Inspect original source and exact inventory")
    component.on_evidence(None)
    pump(lambda: not frame.actions.active, timeout=15)
    assert frame.session.state["proposal"]
    assert component.approve.IsEnabled()
    component.decide(True)
    pump(lambda: not frame.actions.active, timeout=15)
    assert (
        frame.session.state["drafts"]["ir"]["revision"]["evidence_review"][
            "approval_state"
        ]
        == "APPROVED"
    )
    assert frame.session.state.get("release") is None


def test_actual_generation_button_native_previews_and_live_main(
    frame, tmp_path
):
    """@brief Runs the real generation control and inspects bound native
    previews.
    @param frame Actual wx main frame.
    @param tmp_path Temporary explicitly reviewed known-input session.
    @return None.
    @details Main timers continue while CAD/KiCad run in the isolated child.
    """
    from test_desktop_review import fielded_session

    from partsmith.pdl import resolve_pdl

    session, _review = fielded_session(tmp_path, review_inputs=False)
    frame.replace_session(session)
    component = frame.review.component
    assert session.state["drafts"]["ir"]["revision"]["evidence_review"] is None
    component.reason.SetValue(
        "Inspected original inventory and engineering fields"
    )
    component.on_evidence(None)
    pump(lambda: not frame.actions.active, timeout=15)
    assert session.state["proposal"] is not None
    component.decide(True)
    pump(lambda: not frame.actions.active, timeout=15)
    assert session.state.get("release") is None
    pdl = resolve_pdl("chip_resistor", "0402", {"1", "2"})
    index = component.pdls.index((pdl.data["id"], pdl.data["revision"]))
    component.pdl.SetSelection(index)
    component.on_pdl(None)
    pump(lambda: not frame.actions.active, timeout=15)
    panel = frame.review.artifacts
    panel.on_generate(None)
    assert frame.actions.active
    assert not frame.save_button.IsEnabled()
    assert frame.cancel.IsEnabled()
    frame.status.SetLabel("Main window remains responsive")
    wx.Yield()
    pump(lambda: not frame.actions.active, timeout=120)
    assert frame.session.state["release"]["approved"] is False
    assert "FINAL" in panel.bytes.GetValue()
    assert all(preview.svg is not None for preview in panel.previews.values())
    assert "Exit status: 0" in frame.logs.GetValue()
    assert "[stdout]" in frame.logs.GetValue()
    assert frame.save_button.IsEnabled()
    inspect_production_viewer(frame)
    final = frame.review.release
    frame.review.SetSelection(4)
    frame.SetSize((1050, 1000))
    frame.review.GetParent().ScrollChildIntoView(frame.review)
    wx.Yield()
    capture(frame, "phase-12-release-review.png")
    assert not final.report["blockers"]
    final.reason.SetValue("Inspected actual artifacts and bound validation")
    final.decide(True)
    pump(lambda: not frame.actions.active, timeout=30)
    assert frame.session.state["release"]["approved"] is True
    assert frame.session.state["history"][-1]["kind"] == "RELEASE_APPROVE"
    destination = tmp_path / "approved.partsmith"
    frame.session.save(destination)
    restored = Session.load(destination, root=tmp_path / "restored")
    assert restored.state["release"]["approved"] is True
    assert restored.instance_id != frame.session.instance_id
    frame.replace_session(restored)
    assert frame.viewer_button.IsEnabled()
    assert not frame.job.active


def test_missing_banner_and_unsaved_close_cancel(frame, tmp_path, monkeypatch):
    """@brief Checks absent Banner3 and Cancel before close/load/source
    choices.
    @param frame Actual wx main frame.
    @param tmp_path Isolated resource-failure storage.
    @param monkeypatch Scoped resource and dialog adapters.
    @return None.
    @details Missing decoration does not disable inspection or saving.
    """
    from partsmith.gui.app import Banner

    banner = Banner(frame, "missing-Phase12-Banner3.png", frame.append_log)
    assert banner.image is None
    assert (
        "Banner unavailable: missing-Phase12-Banner3.png"
        in frame.logs.GetValue()
    )
    banner.Destroy()
    frame.session.update(setup={"part_number": "UNSAVED-FULL-SUFFIX"})
    monkeypatch.setattr(wx, "MessageDialog", Dialog)
    Dialog.choice = wx.ID_CANCEL
    current = frame.session
    frame.Close()
    wx.Yield()
    assert frame and not frame.closing
    assert frame.session is current

    def forbidden(*args, **kwargs):
        """@brief Rejects a chooser reached after unsaved Cancel.
        @param args Dialog constructor arguments.
        @param kwargs Dialog constructor named arguments.
        @return None.
        @details Cancel must stop before choosing another source or archive.
        """
        raise AssertionError("Chooser must not open after Cancel")

    monkeypatch.setattr(wx, "FileDialog", forbidden)
    frame.on_load_session(None)
    frame.on_file(None)
    frame.on_clear_session(None)
    assert frame.session is current
