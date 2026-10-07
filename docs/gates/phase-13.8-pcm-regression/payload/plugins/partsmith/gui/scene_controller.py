"""@package partsmith.gui.scene_controller
@brief Runs bounded native viewer work with coalesced camera requests.
@details No subprocess reading, CAD preparation or rasterization runs in wx.
"""

import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Condition, Event, Thread
from uuid import uuid4

from partsmith.process import run_process

from .scene import MAX_PIXELS, MAX_SCENE_BYTES, SceneSource
from .scene_transport import publish_text, read_message


@dataclass(frozen=True)
class ViewerEvent:
    """@brief Binds worker results to a viewer instance and camera revision.
    @details Events cannot change engineering build or approval state.
    """

    instance: str
    stage: str
    outcome: str
    revision: int = 0
    payload: object = None


def worker_command(stage: str, root: Path) -> list[str]:
    """@brief Builds a command resolving the current source or wheel package.
    @param stage Preparation or rendering operation name.
    @param root Private operation directory.
    @return Argument list for the same Python runtime, without a shell.
    @details Does not rely on the checkout or the process working directory.
    """
    package_root = str(Path(__file__).resolve().parents[2])
    bootstrap = (
        "import sys; sys.path.insert(0,sys.argv.pop(1)); "
        "from partsmith.gui.scene_worker import main; raise SystemExit(main())"
    )
    return [sys.executable, "-c", bootstrap, package_root, stage, str(root)]


class SceneController:
    """@brief Owns one display worker thread and its native child operations.
    @details Cancellation kills children with bounded cleanup; close is async.
    Latest camera requests replace pending ones rather than accumulating work.
    """

    def __init__(
        self,
        source: SceneSource,
        *,
        command=worker_command,
        prepare_timeout: float = 30,
        render_timeout: float = 10,
        mesh_budget: int = MAX_SCENE_BYTES,
    ):
        """@brief Initializes an idle controller for immutable display inputs.
        @param source STEP, footprint and placement snapshots.
        @param command Child argument factory, injectable for failure checks.
        @param prepare_timeout Maximum native preparation time in seconds.
        @param render_timeout Maximum per-frame rendering time in seconds.
        @param mesh_budget Maximum derived scene transport bytes.
        @return None.
        @details Does not start a worker or allocate native resources yet.
        """
        source.validate()
        self.source = source
        self.command = command
        self.timeouts = {"prepare": prepare_timeout, "render": render_timeout}
        self.mesh_budget = min(mesh_budget, MAX_SCENE_BYTES)
        self.instance = str(uuid4())
        self.events = Queue()
        self.cancelled = Event()
        self.condition = Condition()
        self.pending = None
        self.revision = 0
        self.thread = None
        self.process = None
        self.directory = None
        self.latest_frame = None
        self.requested_camera = None

    @property
    def active(self) -> bool:
        """@brief Reports whether resources are still owned by the worker.
        @return True until worker and native child cleanup finishes.
        @details Safe to query from the GUI thread without joining it.
        """
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> None:
        """@brief Starts native preparation without blocking the caller.
        @return None.
        @details Controllers are single use, preventing stale instance reuse.
        """
        if self.thread is not None:
            raise RuntimeError("VIEWER_STATE: controller already started")
        self.thread = Thread(
            target=self._run, daemon=True, name=f"placement-{self.instance}"
        )
        self.thread.start()

    def request(self, camera: dict, size: tuple[int, int]) -> int:
        """@brief Coalesces a display-only camera and viewport update.
        @param camera Yaw/elevation in degrees and dimensionless zoom.
        @param size Viewport width and height in pixels.
        @return Monotonic display revision for ignoring obsolete frames.
        @details Enforces allocation limits and snapshots nested camera state.
        """
        width, height = size
        if (
            type(width) is not int
            or type(height) is not int
            or width < 1
            or height < 1
            or width > 4096
            or height > 4096
            or width * height > MAX_PIXELS
        ):
            raise ValueError("VIEWER_RENDER_LIMIT: viewport too large")
        content = json.dumps({**camera, "size": list(size)}, allow_nan=False)
        if len(content.encode("utf-8")) > 65000:
            raise ValueError("VIEWER_CAMERA: request too large")
        snapshot = json.loads(content)
        with self.condition:
            if self.requested_camera is not None and any(
                snapshot.get(key) != self.requested_camera.get(key)
                for key in ("size", "layers", "selected_pad")
            ):
                self.latest_frame = None
            self.revision += 1
            self.pending = (self.revision, snapshot)
            self.requested_camera = snapshot
            self.condition.notify()
            return self.revision

    def close(self) -> None:
        """@brief Requests cancellation and bounded native cleanup.
        @return None.
        @details The caller never waits for child exit on the GUI thread.
        """
        self.cancelled.set()
        with self.condition:
            self.pending = None
            self.latest_frame = None
            self.condition.notify()

    def drain(self) -> list[ViewerEvent]:
        """@brief Drains worker events for GUI-thread dispatch.
        @return List of immutable viewer-instance-bound events.
        @details Empty queues return immediately; only the caller handles UI.
        """
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except Empty:
                with self.condition:
                    if self.latest_frame is not None:
                        result.append(self.latest_frame)
                        self.latest_frame = None
                return result

    def _operation(self, stage: str, root: Path, *, on_poll=None) -> None:
        """@brief Supervises one bounded child with no inherited secrets.
        @param stage Native operation to supervise.
        @param root Private native operation directory.
        @param on_poll Optional render-stream deadline and transport callback.
        @return None.
        @details Native output reaches queued main-thread redaction; process
        containment kills and reaps descendants on cancellation or timeout.
        """
        import os

        environment = {
            key: value
            for key, value in os.environ.items()
            if not any(
                token in key.upper()
                for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
            )
        }
        command = self.command(stage, root)
        if on_poll is not None:
            command = [*command, "--persistent"]
        try:
            result = run_process(
                command,
                env=environment,
                cancel=self.cancelled,
                timeout=self.timeouts[stage] if on_poll is None else None,
                on_poll=on_poll,
                poll_interval=0.005 if on_poll is not None else 0.02,
                log=lambda message: self.events.put(
                    ViewerEvent(self.instance, stage, "log", payload=message)
                ),
                on_start=lambda child: setattr(self, "process", child),
            )
            if result.returncode:
                raise RuntimeError(f"VIEWER_CHILD_EXIT:{result.returncode}")
        except InterruptedError as error:
            raise RuntimeError("VIEWER_CANCELLED") from error
        except TimeoutError as error:
            raise RuntimeError("VIEWER_TIMEOUT") from error
        finally:
            self.process = None

    def _render(self, root: Path) -> None:
        """@brief Supervises a persistent renderer with one frame in flight.
        @param root Private display transport directory.
        @return None after cancellation or native worker exit.
        @details Startup and every submitted frame have independent deadlines.
        Complete frames may advance during dragging; superseded sizes and
        layer selections cannot restore obsolete display content.
        """
        started = time.monotonic()
        submitted = 0.0
        inflight = None
        ready = False

        def poll(_process):
            """@brief Exchanges atomic frame requests outside the GUI thread.
            @param _process Owned child supervised by run_process.
            @return None.
            @details Raises TimeoutError on stalled startup or frame output;
            caps submissions at 60 Hz and keeps pending camera storage bounded.
            """
            nonlocal inflight, ready, submitted
            if self.cancelled.is_set():
                return
            now = time.monotonic()
            if not ready:
                ready = (root / "render-ready").is_file()
                if not ready:
                    if now - started > self.timeouts["render"]:
                        raise TimeoutError("Renderer startup exceeded timeout")
                    return
            if inflight is not None:
                revision, camera = inflight
                completed = read_message(root / "frame-ready") == str(revision)
                if not completed:
                    if now - submitted > self.timeouts["render"]:
                        raise TimeoutError("Frame exceeded timeout")
                    return
                width, height = camera["size"]
                path = root / "frame.rgb"
                if path.stat().st_size != width * height * 3:
                    raise RuntimeError("VIEWER_FRAME_INVALID")
                frame = path.read_bytes()
                with self.condition:
                    current = self.requested_camera
                    if not self.cancelled.is_set() and all(
                        camera.get(key) == current.get(key)
                        for key in ("size", "layers", "selected_pad")
                    ):
                        self.latest_frame = ViewerEvent(
                            self.instance,
                            "render",
                            "frame",
                            revision,
                            (width, height, frame),
                        )
                inflight = None
            if now - submitted < 1 / 60:
                return
            with self.condition:
                if self.pending is None or self.cancelled.is_set():
                    return
                revision, camera = self.pending
                self.pending = None
            content = json.dumps(
                {"revision": revision, "camera": camera}, allow_nan=False
            )
            publish_text(root / "camera-request.json", content)
            inflight = (revision, camera)
            submitted = time.monotonic()

        self._operation("render", root, on_poll=poll)
        if not self.cancelled.is_set():
            raise RuntimeError("VIEWER_RENDER_STREAM_CLOSED")

    def _run(self) -> None:
        """@brief Owns native work, immutable snapshots and display caches.
        @return None.
        @details Deletes all meshes/frames on exit; emits structured failures.
        Child operations have no SQLite connection or engineering write path.
        """
        stage = "prepare"
        try:
            with tempfile.TemporaryDirectory(prefix="partsmith-viewer-") as d:
                root = Path(d)
                self.directory = root
                for name, content in (
                    ("input.step", self.source.step),
                    ("input.kicad_mod", self.source.footprint),
                    ("placement.json", self.source.placement),
                ):
                    (root / name).write_bytes(content)
                self._operation(stage, root)
                path = root / "scene.json"
                if path.stat().st_size > self.mesh_budget:
                    raise RuntimeError("VIEWER_MESH_LIMIT")
                scene = json.loads(path.read_bytes())
                metadata = {
                    key: value
                    for key, value in scene.items()
                    if key != "triangles"
                }
                self.events.put(
                    ViewerEvent(
                        self.instance, stage, "ready", payload=metadata
                    )
                )
                stage = "render"
                self._render(root)
        except Exception as error:
            code = (
                str(error)
                if isinstance(error, RuntimeError)
                else ("VIEWER_OPERATION_ERROR")
            )
            self.events.put(
                ViewerEvent(
                    self.instance,
                    stage,
                    "cancelled" if self.cancelled.is_set() else "failed",
                    payload=code,
                )
            )
        finally:
            with self.condition:
                self.latest_frame = None
            self.events.put(ViewerEvent(self.instance, "cleanup", "closed"))
