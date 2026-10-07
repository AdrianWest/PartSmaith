"""@package partsmith.gui.viewer_prototype
@brief Provides the wxPython Phase 12.1 placement rendering experiment.
@details This modeless inspection window has no generation or approval action.
"""

import json

import wx

from partsmith.ir.canonical import canonical_json

from .scene import fixture_source
from .scene_controller import SceneController

DEFAULT_CAMERA = {"yaw": 35.0, "elevation": 28.0, "zoom": 1.0}


class Viewport(wx.Panel):
    """@brief Displays worker-owned raster output and camera gestures.
    @details wx only blits validated RGB bytes; no CAD or GPU context is used.
    """

    def __init__(self, parent):
        """@brief Sets up an empty double-buffered viewport.
        @param parent Owning prototype frame.
        @return None.
        @details Paint contexts exist only for the duration of each event.
        """
        super().__init__(parent)
        self.owner = parent
        self.bitmap = None
        self.dc_factory = wx.AutoBufferedPaintDC
        self.anchor = None
        self.SetMinSize((320, 240))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_up)

    def on_paint(self, _event):
        """@brief Blits the last complete frame with a temporary paint DC.
        @param _event wx paint event.
        @return None.
        @details Initialization/context errors disable only this viewport.
        """
        try:
            dc = self.dc_factory(self)
            dc.SetBackground(wx.Brush(wx.Colour(19, 27, 40)))
            dc.Clear()
            if self.bitmap is not None:
                dc.DrawBitmap(self.bitmap, 0, 0)
        except Exception:
            self.owner.fail("VIEWER_DISPLAY_CONTEXT_ERROR")

    def on_size(self, event):
        """@brief Requests a new bounded frame after resizing.
        @param event wx resize event.
        @return None.
        @details Rendering happens asynchronously and pending sizes coalesce.
        """
        self.owner.request_frame()
        event.Skip()

    def on_down(self, event):
        """@brief Begins a camera rotation gesture.
        @param event Mouse button event.
        @return None.
        @details Capture is released when the gesture or viewport ends.
        """
        self.anchor = event.GetPosition()
        if not self.HasCapture():
            self.CaptureMouse()

    def on_up(self, _event):
        """@brief Ends camera dragging and releases mouse capture.
        @param _event Mouse release or capture-lost event.
        @return None.
        @details Safe to call again during window cleanup.
        """
        self.anchor = None
        if self.HasCapture():
            self.ReleaseMouse()

    def on_motion(self, event):
        """@brief Rotates the display camera while dragging.
        @param event Mouse motion event.
        @return None.
        @details Leaves the engineering placement matrix and artifacts intact.
        """
        if self.anchor is None or not event.Dragging():
            return
        point = event.GetPosition()
        dx, dy = point.x - self.anchor.x, point.y - self.anchor.y
        self.anchor = point
        if event.ShiftDown():
            pan = self.owner.camera.setdefault("pan", [0.0, 0.0])
            size = self.GetClientSize()
            pan[0] += dx / max(1, size.width)
            pan[1] += dy / max(1, size.height)
        else:
            self.owner.camera["yaw"] += dx * 0.4
            self.owner.camera["elevation"] = max(
                -90, min(90, self.owner.camera["elevation"] + dy * 0.4)
            )
        self.owner.request_frame()

    def on_wheel(self, event):
        """@brief Adjusts display zoom within its declared range.
        @param event Mouse wheel event.
        @return None.
        @details Does not scale the engineering model or footprint.
        """
        self.owner.zoom(1.15 if event.GetWheelRotation() > 0 else 1 / 1.15)


class PrototypeFrame(wx.Frame):
    """@brief Owns an isolated, modeless rendering prototype.
    @details Closing retains source/camera and reaps native workers.
    """

    def __init__(
        self,
        parent,
        *,
        source=None,
        camera=None,
        log=None,
        on_closed=None,
        controller_factory=SceneController,
        bitmap_factory=wx.Bitmap.FromBuffer,
    ):
        """@brief Opens the fixture experiment and starts native preparation.
        @param parent Main application frame.
        @param source Immutable display input, defaults to packaged 0402.
        @param camera Retained display camera, separate from placement.
        @param log Main-window redacted logging callback.
        @param on_closed Callback receiving the retained camera after cleanup.
        @param controller_factory Controller factory for failure injection.
        @param bitmap_factory Bitmap factory for initialization failure checks.
        @return None.
        @details Native resources never belong to the GUI process.
        """
        controller = controller_factory(source or fixture_source())
        super().__init__(
            parent,
            title="PartSmith — 12.1 Rendering Prototype",
            size=(920, 660),
        )
        self.SetMinSize((540, 420))
        self.camera = json.loads(canonical_json(camera or DEFAULT_CAMERA))
        self.log = log or (lambda message: None)
        self.on_closed = on_closed
        self.bitmap_factory = bitmap_factory
        self.closing = False
        self.failed = False
        self.metadata = None
        self.revision = 0
        self.frame_revision = 0
        self.controller = controller
        self.retiring = []
        layout = wx.BoxSizer(wx.VERTICAL)
        self.notice = wx.StaticText(
            self,
            label=(
                "Known synthetic 0402 fixture — inspection prototype; "
                "no release approval. Drag to rotate; wheel to zoom."
            ),
        )
        layout.Add(self.notice, 0, wx.EXPAND | wx.ALL, 12)
        self.viewport = Viewport(self)
        layout.Add(self.viewport, 1, wx.EXPAND)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        for label, callback in (
            ("Reset camera", self.reset_camera),
            ("Zoom +", self.zoom_in),
            ("Zoom −", self.zoom_out),
        ):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, callback)
            controls.Add(button, 0, wx.RIGHT, 8)
        layout.Add(controls, 0, wx.ALL, 12)
        self.status = wx.StaticText(
            self, label="Preparing STEP in isolated worker…"
        )
        layout.Add(
            self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12
        )
        self.SetSizer(layout)
        self.Layout()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.poll, self.timer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.timer.Start(16)
        self.controller.start()
        self.log(
            "Viewer prepare started: explicit snapshot; mm; convention 1.1"
        )
        self.request_frame()

    def request_frame(self):
        """@brief Requests the latest camera and client-size display frame.
        @return None.
        @details Ignores destroyed/failed/closing viewports and bounds pixels.
        """
        if self.closing or self.failed or not hasattr(self, "viewport"):
            return
        size = self.viewport.GetClientSize()
        if size.width < 1 or size.height < 1:
            return
        try:
            self.revision = self.controller.request(
                dict(self.camera), (size.width, size.height)
            )
        except ValueError:
            self.fail("VIEWER_RENDER_LIMIT")

    def zoom(self, factor):
        """@brief Updates camera magnification and schedules rendering.
        @param factor Positive display zoom multiplier.
        @return None.
        @details Engineering scale is unchanged and zoom stays in 0.2–8.
        """
        self.camera["zoom"] = max(0.2, min(8, self.camera["zoom"] * factor))
        self.request_frame()

    def zoom_in(self, _event):
        """@brief Handles the increase-zoom button.
        @param _event wx button event.
        @return None.
        @details Delegates to display-only camera zoom.
        """
        self.zoom(1.25)

    def zoom_out(self, _event):
        """@brief Handles the decrease-zoom button.
        @param _event wx button event.
        @return None.
        @details Delegates to display-only camera zoom.
        """
        self.zoom(0.8)

    def reset_camera(self, _event):
        """@brief Restores the initial display camera.
        @param _event wx button event.
        @return None.
        @details Never resets engineering placement metadata.
        """
        self.camera = dict(DEFAULT_CAMERA)
        self.request_frame()

    def fail(self, code):
        """@brief Disables the viewport while preserving the main application.
        @param code Safe structured failure code.
        @return None.
        @details Logs once, clears native bitmap references and cancels work.
        """
        if self.failed or self.closing:
            return
        self.failed = True
        self.viewport.bitmap = None
        self.controller.close()
        self.status.SetLabel(
            f"Viewport unavailable: {code}. Close/reopen to retry."
        )
        self.log(f"12.1 viewport failed: {code}; main session retained")

    def poll(self, _event):
        """@brief Dispatches current-instance worker events onto the wx thread.
        @param _event wx timer event.
        @return None.
        @details Displays monotonically newer complete frames while dragging;
        rejects replaced instances, old viewport sizes and closing results.
        """
        for worker in self.retiring:
            for event in worker.drain():
                if event.outcome == "log":
                    self.log(f"[viewer/{event.stage}/retired] {event.payload}")
        self.retiring = [worker for worker in self.retiring if worker.active]
        for event in self.controller.drain():
            if event.instance != self.controller.instance:
                continue
            if event.outcome == "log":
                self.log(f"[viewer/{event.stage}] {event.payload}")
                continue
            if self.closing:
                continue
            if event.outcome == "ready":
                self.metadata = event.payload
                self.log(
                    "12.1 prepare ready: actual STEP mesh and footprint pads"
                )
            elif event.outcome == "failed":
                self.fail(f"{event.stage}/{event.payload}")
            elif (
                event.outcome == "frame"
                and not self.failed
                and self.frame_revision < event.revision <= self.revision
                and event.payload[:2] == tuple(self.viewport.GetClientSize())
            ):
                try:
                    width, height, rgb = event.payload
                    self.viewport.bitmap = self.bitmap_factory(
                        width, height, rgb
                    )
                    if not self.viewport.bitmap.IsOk():
                        raise RuntimeError("Invalid bitmap")
                except Exception:
                    self.fail("VIEWER_DISPLAY_INIT_ERROR")
                    continue
                self.frame_revision = event.revision
                self.status.SetLabel(
                    "Display ready — CPU; mm; mesh tolerance 0.01 mm. "
                    "Engineering validators remain authoritative."
                )
                self.viewport.Refresh()
        if self.closing and not self.controller.active and not self.retiring:
            self.timer.Stop()
            self.viewport.bitmap = None
            self.metadata = None
            callback, self.on_closed = self.on_closed, None
            if callback is not None:
                callback(dict(self.camera))
            self.Destroy()

    def on_close(self, event):
        """@brief Cancels work before releasing the modeless viewer.
        @param event wx close event.
        @return None.
        @details Timer completes async cleanup; the main session is retained.
        """
        self.closing = True
        self.viewport.on_up(None)
        self.controller.close()
        for worker in self.retiring:
            worker.close()
        if event.CanVeto():
            event.Veto()
        self.Hide()
        self.poll(None)
