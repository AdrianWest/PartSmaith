"""@file verify_viewer_prototype.py
@brief Verifies Phase 12.1 in a real wx desktop and source or PCM payload.
@details Run pytest against the declared package root; no GPU is required.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import wx

from partsmith.gui.app import SetupFrame
from partsmith.gui.credentials import CredentialStore
from partsmith.gui.scene import SceneSource, fixture_source
from partsmith.gui.scene_controller import (
    SceneController,
    ViewerEvent,
    worker_command,
)
from partsmith.gui.session import Session
from partsmith.gui.viewer_prototype import PrototypeFrame
from scripts.verify_gui import Backend, pump


@pytest.fixture(scope="session")
def app():
    """@brief Creates or reuses the desktop application.
    @return wx.App suitable for repeated modeless window checks.
    @details Keeps the application alive while individual frames close.
    """
    result = wx.GetApp() or wx.App(False)
    result.SetExitOnFrameDelete(False)
    return result


@pytest.fixture
def frame(app, tmp_path):
    """@brief Opens the real setup window with a dummy credential backend.
    @param app Desktop wx application.
    @param tmp_path Isolated operational session root.
    @return SetupFrame through a pytest fixture yield.
    @details Cleanup waits for native display worker teardown.
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
        pump(lambda: not result, timeout=15)


def open_prototype(frame):
    """@brief Opens the actual button action and waits for a complete frame.
    @param frame Main setup window.
    @return Ready PrototypeFrame.
    @details Tests the production path rather than creating a substitute scene.
    """
    frame.on_prototype(None)
    viewer = frame.prototype
    assert viewer is not None
    pump(lambda: viewer.frame_revision > 0 or viewer.failed, timeout=40)
    assert not viewer.failed, viewer.status.GetLabel()
    return viewer


def test_actual_modeless_rotation_zoom_resize_and_reopen(frame, tmp_path):
    """@brief Exercises modeless viewing, singleton and camera retention.
    @param frame Real main application frame.
    @param tmp_path Unrelated cwd for resource-resolution verification.
    @return None.
    @details Repeated closes release children, caches, bitmaps and callbacks.
    """
    source = fixture_source()
    frame.ai_candidates = {"review_state": "UNREVIEWED"}
    frame.source.ChangeValue("retained-source.pdf")
    for iteration in range(3):
        viewer = open_prototype(frame)
        assert viewer.GetParent() == frame
        frame.on_prototype(None)
        assert frame.prototype is viewer
        assert frame.start.IsEnabled()
        assert frame.part.IsEnabled()
        frame.part.ChangeValue(f"MAIN-REMAINS-RESPONSIVE-{iteration}")
        before = viewer.frame_revision
        viewer.camera["yaw"] += 30
        viewer.zoom(1.25)
        pump(lambda v=viewer, r=before: v.frame_revision > r, timeout=15)
        viewer.SetSize((1100, 720))
        wx.Yield()
        revision = viewer.revision
        pump(lambda v=viewer, r=revision: v.frame_revision == r, timeout=15)
        assert viewer.viewport.bitmap.GetWidth() == (
            viewer.viewport.GetClientSize().width
        )
        assert viewer.metadata["bounds_mm"] == [
            [-0.5, -0.25, 0.0],
            [0.5, 0.25, 0.35],
        ]
        # Retain a real displayed frame, not an idealized reference rendering.
        viewer.viewport.bitmap.SaveFile(
            str(tmp_path / "actual-viewport.png"), wx.BITMAP_TYPE_PNG
        )
        camera = dict(viewer.camera)
        controller = viewer.controller
        directory = controller.directory
        viewer.Close()
        pump(lambda: frame.prototype is None, timeout=15)
        pump(lambda v=viewer: not v, timeout=15)
        assert not controller.active
        assert controller.process is None
        assert not directory.exists()
        assert not viewer
        assert frame.prototype_camera == camera
    assert frame.ai_candidates == {"review_state": "UNREVIEWED"}
    assert frame.source.GetValue() == "retained-source.pdf"
    assert fixture_source() == source
    assert "12.1 prepare ready" in frame.logs.GetValue()
    assert "resources released" in frame.logs.GetValue()


def test_packaged_fixture_resources_from_unrelated_cwd(
    frame, tmp_path, monkeypatch
):
    """@brief Resolves the prototype inputs with no repository working cwd.
    @param frame Real main window.
    @param tmp_path Directory without repository resources.
    @param monkeypatch pytest cwd helper.
    @return None.
    @details PCM acceptance requires exact packaged bytes.
    """
    monkeypatch.chdir(tmp_path)
    viewer = open_prototype(frame)
    assert viewer.metadata["input_sha256"]


@pytest.mark.parametrize(
    "failure",
    ["malformed", "prepare_exit", "prepare_timeout", "graphics_unavailable"],
)
def test_failed_native_work_leaves_main_state_usable(frame, failure):
    """@brief Injects native failure with the actual desktop event loop alive.
    @param frame Main application window.
    @param failure Selected native-failure scenario.
    @return None.
    @details Failure stops the viewport without replacing session or log data.
    """
    source = fixture_source()
    if failure == "malformed":
        source = SceneSource(
            b"broken STEP", source.footprint, source.placement
        )

    def command(stage, root):
        """@brief Injects renderer or native preparation failure.
        @param stage Requested operation boundary.
        @param root Private worker directory.
        @return Child command argument list.
        @details Valid stages continue to use the real implementation.
        """
        if stage == "prepare" and failure == "prepare_exit":
            return [sys.executable, "-c", "import os; os._exit(31)"]
        if stage == "prepare" and failure == "prepare_timeout":
            return [sys.executable, "-c", "import time; time.sleep(60)"]
        if stage == "render" and failure == "graphics_unavailable":
            return [sys.executable, "-c", "raise ImportError('no rasterizer')"]
        return worker_command(stage, root)

    def factory(inputs):
        """@brief Builds a controller with the injected native boundary.
        @param inputs Retained immutable source inputs.
        @return SceneController.
        @details Timeout scenarios use a short explicit acceptance deadline.
        """
        return SceneController(
            inputs,
            command=command,
            prepare_timeout=0.3 if failure == "prepare_timeout" else 30,
        )

    frame.ai_candidates = {"retained": True}
    frame.source.ChangeValue("original-source.pdf")
    viewer = PrototypeFrame(
        frame, source=source, log=frame.append_log, controller_factory=factory
    )
    viewer.Show()
    try:
        pump(lambda: viewer.failed, timeout=40)
        pump(lambda: not viewer.controller.active, timeout=10)
        assert frame.IsShown()
        assert frame.start.IsEnabled()
        assert frame.ai_candidates == {"retained": True}
        assert frame.source.GetValue() == "original-source.pdf"
        frame.part.ChangeValue("STILL-USABLE")
        frame.append_log("Inspection remains available")
        assert "viewport failed" in frame.logs.GetValue()
        assert viewer.viewport.bitmap is None
    finally:
        viewer.Close()
        pump(lambda: not viewer, timeout=15)


@pytest.mark.parametrize("failure", ["initialization", "context"])
def test_display_initialization_and_context_errors_are_contained(
    frame, failure
):
    """@brief Verifies graphics allocation/context failures preserve main UI.
    @param frame Main application frame.
    @param failure Bitmap initialization or display context failure.
    @return None.
    @details Failed viewports drop bitmaps, cancel children and log safe codes.
    """

    def unavailable(*args):
        """@brief Simulates unavailable bitmap or native display support.
        @param args Display allocation arguments.
        @return None; always raises RuntimeError.
        @details Does not change the main window's display factory.
        """
        raise RuntimeError("Unavailable display support")

    viewer = PrototypeFrame(
        frame,
        log=frame.append_log,
        bitmap_factory=unavailable
        if failure == "initialization"
        else wx.Bitmap.FromBuffer,
    )
    viewer.Show()
    try:
        if failure == "context":
            pump(lambda: viewer.frame_revision > 0, timeout=40)
            viewer.viewport.dc_factory = unavailable
            viewer.viewport.Refresh()
            viewer.viewport.Update()
        pump(lambda: viewer.failed, timeout=40)
        assert frame.start.IsEnabled()
        assert viewer.viewport.bitmap is None
        assert "VIEWER_DISPLAY_" in frame.logs.GetValue()
    finally:
        viewer.Close()
        pump(lambda: not viewer, timeout=15)


def test_continuous_navigation_updates_actual_desktop(frame):
    """@brief Checks visible bitmap progress while navigation keeps updating.
    @param frame Main desktop frame owning the modeless viewer.
    @return None.
    @details The same native renderer serves intermediate and final camera
    states while wx processes paint events and the main controls stay live.
    """
    viewer = open_prototype(frame)
    child = viewer.controller.process
    revisions = set()
    until = time.monotonic() + 1.5

    def move_camera():
        """@brief Drives continuous movement inside the actual wx main loop.
        @return True when the continuous-navigation interval has ended.
        @details Native timers and paint events remain dispatchable while
        camera requests arrive; exceptions propagate through the QA pump.
        """
        if time.monotonic() >= until:
            return True
        viewer.camera["yaw"] += 0.8
        viewer.request_frame()
        revisions.add(viewer.frame_revision)
        assert not viewer.failed, viewer.status.GetLabel()
        return False

    pump(move_camera, timeout=10)
    assert len(revisions) >= 3
    assert viewer.controller.process is child
    final = viewer.revision
    pump(lambda: viewer.frame_revision == final, timeout=15)
    assert frame.start.IsEnabled()
    viewer.Close()
    pump(lambda: frame.prototype is None, timeout=15)
    assert child.poll() is not None


def test_superseded_and_closing_events_cannot_change_display(frame):
    """@brief Rejects stale instance/camera updates and late close callbacks.
    @param frame Main application window.
    @return None.
    @details Untrusted event identities never publish a replacement frame.
    """
    viewer = open_prototype(frame)
    before = viewer.frame_revision
    viewer.controller.events.put(ViewerEvent("stale", "render", "failed"))
    viewer.controller.events.put(
        ViewerEvent(
            viewer.controller.instance,
            "render",
            "frame",
            before - 1,
            (1, 1, b"abc"),
        )
    )
    viewer.poll(None)
    assert not viewer.failed
    assert viewer.frame_revision == before
    viewer.Close()
    pump(lambda: frame.prototype is None, timeout=15)
    wx.Yield()
    assert frame.start.IsEnabled()


def test_main_close_waits_for_viewer_worker_cleanup(frame):
    """@brief Closes the main window during native preparation.
    @param frame Real main window.
    @return None.
    @details Destruction waits for child exit and private-cache removal.
    """
    frame.on_prototype(None)
    controller = frame.prototype.controller
    frame.Close()
    pump(lambda: not frame, timeout=15)
    assert not controller.active
    assert controller.process is None
    if controller.directory is not None:
        assert not controller.directory.exists()


def test_package_resources_and_no_cad_in_main_import():
    """@brief Verifies real GUI imports do not initialize CAD or a renderer.
    @return None.
    @details Child imports use the same package root as the parent runtime.
    """
    command = worker_command("prepare", Path.cwd())
    code = (
        "import sys;sys.path.insert(0,sys.argv[1]); "
        "import partsmith.gui.app; "
        "assert 'cadquery' not in sys.modules; "
        "assert 'PIL.ImageDraw' not in sys.modules"
    )
    subprocess.run(
        [sys.executable, "-c", code, command[3]],
        check=True,
        capture_output=True,
        timeout=15,
    )
    assert (
        json.loads(fixture_source().placement)["convention_version"] == "1.1"
    )
