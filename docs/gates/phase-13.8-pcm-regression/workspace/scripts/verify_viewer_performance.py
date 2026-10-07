"""@file verify_viewer_performance.py
@brief Measures persistent viewer latency and continuous-camera progress.
@details Uses the actual isolated CPU renderer and immutable 0402 fixture.
Results describe this local runtime rather than a universal frame-rate claim.
"""

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path

from partsmith.gui.scene import fixture_source
from partsmith.gui.scene_controller import SceneController, worker_command

CAMERA = {"yaw": 35, "elevation": 28, "zoom": 1}


def wait_frame(controller, revision=None):
    """@brief Waits for a complete real-worker frame.
    @param controller Active scene controller.
    @param revision Optional exact requested revision to await.
    @return Complete frame event from the current worker.
    @details Raises on worker failure or a 40-second verification timeout.
    """
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        for event in controller.drain():
            if event.outcome == "failed":
                raise RuntimeError(event.payload)
            if event.outcome == "frame" and (
                revision is None or event.revision == revision
            ):
                return event
        time.sleep(0.002)
    raise TimeoutError("Viewer did not publish the expected frame")


def measure(size):
    """@brief Compares single-shot and persistent rendering at one viewport.
    @param size Width and height in pixels.
    @return Latency, continuous-motion progress and cleanup measurements.
    @details Excludes initial CAD preparation from steady-state frame latency;
    checks final-camera convergence, worker reuse and immutable source bytes.
    """
    controller = SceneController(fixture_source())
    controller.request(CAMERA, size)
    controller.start()
    try:
        wait_frame(controller)
        child = controller.process
        names = (
            "input.step",
            "input.kicad_mod",
            "placement.json",
            "scene.json",
        )
        root = controller.directory
        inputs = {name: (root / name).read_bytes() for name in names}
        (root / "camera.json").write_text(
            json.dumps({**CAMERA, "size": list(size)}), encoding="utf-8"
        )
        fresh = []
        for _ in range(5):
            started = time.perf_counter()
            subprocess.run(
                worker_command("render", root),
                check=True,
                capture_output=True,
                timeout=15,
            )
            fresh.append((time.perf_counter() - started) * 1000)
        persistent = []
        for yaw in range(35, 55):
            started = time.perf_counter()
            revision = controller.request({**CAMERA, "yaw": yaw}, size)
            wait_frame(controller, revision)
            persistent.append((time.perf_counter() - started) * 1000)
        frames = []
        started = time.monotonic()
        while time.monotonic() - started < 2:
            controller.request(
                {**CAMERA, "yaw": controller.revision * 0.8}, size
            )
            for event in controller.drain():
                if event.outcome == "failed":
                    raise RuntimeError(event.payload)
                if event.outcome == "frame":
                    frames.append(event.revision)
            time.sleep(0.005)
        elapsed = time.monotonic() - started
        final = controller.request({**CAMERA, "yaw": 180}, size)
        wait_frame(controller, final)
        assert len(frames) >= 3, "Continuous navigation starved the display"
        assert frames == sorted(set(frames))
        assert controller.process is child
        assert inputs == {name: (root / name).read_bytes() for name in names}
        result = {
            "size": list(size),
            "fresh_process_median_ms": round(statistics.median(fresh), 2),
            "persistent_request_to_frame_median_ms": round(
                statistics.median(persistent), 2
            ),
            "continuous_motion_frames": len(frames),
            "continuous_motion_seconds": round(elapsed, 3),
            "continuous_motion_frame_events_per_second": round(
                len(frames) / elapsed, 2
            ),
            "same_renderer_process": True,
            "final_camera_rendered": True,
            "source_bytes_unchanged": True,
        }
    finally:
        controller.close()
        controller.thread.join(10)
        assert not controller.active
        assert controller.process is None
        assert not controller.directory.exists()
    result["child_reaped_and_cache_removed"] = child.poll() is not None
    return result


def main():
    """@brief Writes local benchmark evidence for two practical viewport sizes.
    @return Zero after all real-renderer checks pass.
    @details Optional output is a scoped JSON receipt using LF final bytes.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = {
        "status": "PASS",
        "scope": "Local 0402 CPU-renderer/controller measurements; no GPU.",
        "measurements": [measure(size) for size in ((400, 300), (880, 480))],
    }
    content = json.dumps(result, indent=2) + "\n"
    if arguments.output is not None:
        arguments.output.write_text(content, encoding="utf-8", newline="\n")
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
