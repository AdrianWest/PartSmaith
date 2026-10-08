"""@file verify_external_dependencies_gui.py
@brief Verifies native prerequisite dialogs, links and launching-host closure.
@details Uses real wx widgets without opening browsers or changing installs.
Optional PARTSMITH_PREREQUISITE_SCREENSHOT retains a rendered dialog image.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import wx
import wx.adv

from partsmith import external_dependencies as external
from partsmith.gui import __main__ as desktop
from partsmith.gui.prerequisites import MissingDependenciesDialog


@pytest.fixture(scope="module")
def app():
    """@brief Owns a native application for prerequisite dialog verification.
    @return wx application retained throughout this module.
    @details No setup session, project or recovery state is created.
    """
    result = wx.App.Get() or wx.App(False)
    result.SetExitOnFrameDelete(False)
    return result


def children(window):
    """@brief Enumerates controls recursively inside an owned native window.
    @param window Parent widget to inspect.
    @return Iterator over descendant widgets.
    @details Does not inspect or interact with another application's windows.
    """
    for child in window.GetChildren():
        yield child
        yield from children(child)


def capture_dialog(dialog, target):
    """@brief Captures only the owned dialog after modal painting completes.
    @param dialog Native PartSmith dialog being verified.
    @param target Explicit evidence PNG path.
    @return None.
    @details Windows PrintWindow includes child controls without other apps.
    """
    import ctypes
    from ctypes import wintypes

    target.parent.mkdir(parents=True, exist_ok=True)
    size = dialog.GetClientSize()
    bitmap = wx.Bitmap(size.width, size.height)
    memory = wx.MemoryDC(bitmap)
    render = ctypes.WinDLL("user32").PrintWindow
    render.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    render.restype = wintypes.BOOL
    try:
        assert render(dialog.GetHandle(), memory.GetHandle(), 1)
        memory.SelectObject(wx.NullBitmap)
        assert bitmap.SaveFile(str(target), wx.BITMAP_TYPE_PNG)
    finally:
        dialog.EndModal(wx.ID_OK)


def test_prerequisite_language_dialog_has_clickable_links(app, monkeypatch):
    """@brief Renders missing languages with real native hyperlink controls.
    @param app Native wx application owner.
    @param monkeypatch Local OCR probe substitution helper.
    @return None.
    @details Retains an optional screenshot; no hyperlink is activated.
    """
    monkeypatch.setattr(external, "find_tesseract", lambda: "ocr")
    outputs = iter(["tesseract 5.5.3", "List of languages (0):\n"])
    monkeypatch.setattr(external, "_probe", lambda *_args: next(outputs))
    issues = external.check_external_dependencies()
    with MissingDependenciesDialog(issues) as dialog:
        dialog.Show()
        dialog.Raise()
        wx.Yield()
        dialog.Update()
        assert dialog.IsShownOnScreen()
        links = [
            item
            for item in children(dialog)
            if isinstance(item, wx.adv.HyperlinkCtrl)
        ]
        assert [link.GetURL() for link in links] == [i.url for i in issues]
        assert len(links) == 3
        assert all(
            link.IsShown() and link.GetSize().width > 0 for link in links
        )
        screenshot = os.environ.get("PARTSMITH_PREREQUISITE_SCREENSHOT")
        dialog.Hide()
        if screenshot:
            wx.CallLater(500, capture_dialog, dialog, Path(screenshot))
        else:
            wx.CallLater(100, dialog.EndModal, wx.ID_OK)
        assert dialog.ShowModal() == wx.ID_OK
        dialog.stop_monitoring()
        assert not dialog.timer.IsRunning()


def test_prerequisite_dialog_closes_when_launch_host_exits(app):
    """@brief Closes the modal error automatically when its owner exits.
    @param app Native wx application owner.
    @return None.
    @details Real timer delivery must close the modal loop without user input.
    """
    issue = external._engine_issue("TESSERACT_MISSING", "Not installed.")
    with MissingDependenciesDialog(
        (issue,), host_alive=lambda: False
    ) as dialog:
        timeout = wx.CallLater(3000, dialog.EndModal, wx.ID_ABORT)
        try:
            assert dialog.ShowModal() == wx.ID_CANCEL
            assert not dialog.timer.IsRunning()
        finally:
            timeout.Stop()
            dialog.stop_monitoring()


@pytest.mark.parametrize("case", ["engine", "languages"])
def test_prerequisite_startup_with_real_missing_install(
    app, monkeypatch, tmp_path, case
):
    """@brief Exercises real startup probes through the native blocking popup.
    @param app Native application retained by the desktop harness.
    @param monkeypatch Isolated launch environment and main-frame substitution.
    @param tmp_path Empty executable/model locations for this launch only.
    @param case Missing executable or missing required language files.
    @return None.
    @details Does not alter installed OCR files or create recovery sessions.
    """
    if case == "engine":
        monkeypatch.setenv("PARTSMITH_TESSERACT", str(tmp_path / "absent.exe"))
    else:
        monkeypatch.delenv("PARTSMITH_TESSERACT", raising=False)
        monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    expected = external.check_external_dependencies()
    assert len(expected) == (1 if case == "engine" else 3)
    frame = Mock()
    monkeypatch.setitem(
        sys.modules, "partsmith.gui.app", SimpleNamespace(SetupFrame=frame)
    )
    monkeypatch.setattr(wx, "App", Mock(return_value=app))
    observed = []

    def inspect_and_close():
        """@brief Records links from the actual startup popup and closes it.
        @return None.
        @details Captures application-owned widgets without activating links.
        """
        for window in wx.GetTopLevelWindows():
            if (
                isinstance(window, MissingDependenciesDialog)
                and window.IsModal()
            ):
                observed.extend(
                    item.GetURL()
                    for item in children(window)
                    if isinstance(item, wx.adv.HyperlinkCtrl)
                )
                window.EndModal(wx.ID_OK)

    timer = wx.CallLater(500, inspect_and_close)
    try:
        assert desktop.main() == 2
        assert observed == [issue.url for issue in expected]
        frame.assert_not_called()
    finally:
        timer.Stop()
