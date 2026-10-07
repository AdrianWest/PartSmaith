"""@package tests.test_viewer_scene
@brief Verifies prototype geometry, rendering and native failure boundaries.
@details Uses real subprocesses without requiring a wx desktop or GPU.
"""

import json
import subprocess
import sys
import time
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.gui.scene import (
    MAX_STEP_BYTES,
    fixture_source,
    parse_footprint,
    placement_transform,
)
from partsmith.gui.scene_controller import SceneController, worker_command
from partsmith.gui.scene_worker import pad_outline

ROOT = Path(__file__).resolve().parents[1]
CAMERA = {"yaw": 35, "elevation": 28, "zoom": 1}


def wait_events(controller, outcome, timeout=40):
    """@brief Waits for one expected outcome while retaining observed events.
    @param controller Native display controller.
    @param outcome Expected outcome label.
    @param timeout Maximum wait in seconds.
    @return Matching ViewerEvent.
    @details Fails on unexpected native failure or missing publication.
    """
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        for event in controller.drain():
            if event.outcome == outcome:
                return event
            assert event.outcome != "failed", event
        time.sleep(0.01)
    pytest.fail(f"No {outcome} event within {timeout}s")


def cleanup(controller):
    """@brief Cancels and verifies native/cache cleanup.
    @param controller Controller whose resources must be released.
    @return None.
    @details Joins only in tests, never in a GUI event handler.
    """
    controller.close()
    if controller.thread is not None:
        controller.thread.join(10)
    assert not controller.active
    assert controller.process is None
    if controller.directory is not None:
        assert not controller.directory.exists()


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    """@brief Prepares the actual STEP/footprint pair in a child once.
    @param tmp_path_factory pytest directory factory.
    @return Private worker directory with prepared display scene.
    @details Uses real CAD import and exact immutable source snapshots.
    """
    root = tmp_path_factory.mktemp("viewer-scene")
    source = fixture_source()
    for name, content in (
        ("input.step", source.step),
        ("input.kicad_mod", source.footprint),
        ("placement.json", source.placement),
    ):
        (root / name).write_bytes(content)
    subprocess.run(
        worker_command("prepare", root),
        check=True,
        timeout=40,
        capture_output=True,
    )
    return root


def test_fixture_scale_orientation_and_independent_pad_relationship(prepared):
    """@brief Checks physical fixture scale, board plane and west pin-1 side.
    @param prepared Real native scene directory.
    @return None.
    @details STEP terminal anchors intentionally differ from pad centres;
    the viewer must retain their measured 0.1 mm X separation.
    """
    scene = json.loads((prepared / "scene.json").read_bytes())
    assert scene["units"] == "mm"
    assert scene["bounds_mm"][0] == pytest.approx([-0.5, -0.25, 0])
    assert scene["bounds_mm"][1] == pytest.approx([0.5, 0.25, 0.35])
    assert scene["matrix"] == [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]
    pads = scene["pads"]
    assert [p["number"] for p in pads] == ["1", "2"]
    assert pads[0]["centre"] == [-0.5, 0]
    assert pads[0]["size"] == [0.55, 0.6]
    west = scene["solid_bounds_mm"][1]
    west_centre = [(a + b) / 2 for a, b in zip(*west, strict=True)]
    assert west_centre == pytest.approx([-0.4, 0, 0.05])
    assert west_centre[0] - pads[0]["centre"][0] == pytest.approx(0.1)
    source = fixture_source()
    assert scene["input_sha256"] == {
        "step": sha256(source.step).hexdigest(),
        "footprint": sha256(source.footprint).hexdigest(),
        "placement": sha256(source.placement).hexdigest(),
    }


def test_actual_roundrect_pad_outline_uses_footprint_dimensions():
    """@brief Checks the display boundary follows actual corner geometry.
    @return None.
    @details Pad edges and radius come from serialized footprint bytes.
    """
    pad = parse_footprint(fixture_source().footprint)[0]
    outline = pad_outline(pad)
    assert len(outline) == 36
    assert min(p[0] for p in outline) == pytest.approx(-0.775)
    assert max(p[0] for p in outline) == pytest.approx(-0.225)
    assert min(p[1] for p in outline) == pytest.approx(-0.3)
    assert max(p[1] for p in outline) == pytest.approx(0.3)


@pytest.mark.parametrize("shape,size", [("circle", [1, 1]), ("oval", [1, 2])])
def test_generated_circle_and_oval_pad_outlines(shape, size):
    """@brief Checks every additional supported Phase 5 pad primitive.
    @param shape Generated SMD pad shape.
    @param size Actual KiCad dimensions in millimetres.
    @return None.
    @details Viewer geometry does not substitute a rectangular pad outline.
    """
    content = (
        f'(footprint "actual" (pad "1" smd {shape} (at 0 0) '
        f'(size {size[0]} {size[1]}) (layers "F.Cu" "F.Paste" "F.Mask")))'
    ).encode()
    pad = parse_footprint(content)[0]
    outline = pad_outline(pad)
    assert len(outline) > 4
    for axis in (0, 1):
        assert min(point[axis] for point in outline) == pytest.approx(
            -size[axis] / 2
        )
        assert max(point[axis] for point in outline) == pytest.approx(
            size[axis] / 2
        )


@pytest.mark.parametrize(
    "replacement",
    [
        (b"smd roundrect", b"smd oval"),
        (b"(at -0.5 0)", b"(at -0.5 0 90)"),
        (b"(size 0.55 0.6)", b"(size -1 0.6)"),
        (b'"F.Cu"', b'"B.Cu"'),
        (b"(roundrect_rratio 0.2)", b"(roundrect_rratio 0.8)"),
    ],
)
def test_unsupported_footprint_geometry_is_never_substituted(replacement):
    """@brief Rejects geometry the prototype cannot display faithfully.
    @param replacement Unsupported syntax mutation.
    @return None.
    @details Unsupported artifacts stay inspectable outside this viewport.
    """
    original, changed = replacement
    with pytest.raises(ValueError, match="VIEWER_FOOTPRINT"):
        parse_footprint(fixture_source().footprint.replace(original, changed))


def test_full_placement_preserves_scale_mirror_rotation_and_translation():
    """@brief Checks nonunit placement against a separately calculated point.
    @return None.
    @details Display conversion retains exact source bytes and full transform.
    """
    from partsmith.threed.transform import apply_point

    source = fixture_source()
    data = json.loads(source.placement)
    data.update(
        translation_mm=[1, 2, 3],
        rotation_deg=[0, 0, 90],
        scale=[2, 3, 4],
        mirror={"x": True, "y": False, "z": True},
    )
    transform = placement_transform(data)
    assert apply_point(transform, (1, 2, 3)) == pytest.approx((-5, 0, -9))
    assert source.placement == fixture_source().placement
    data["convention_version"] = "unsupported"
    with pytest.raises(ValueError, match="VIEWER_TRANSFORM"):
        placement_transform(data)


def test_rotation_zoom_resize_and_read_only_inputs(prepared):
    """@brief Exercises real CPU frames under rotation, zoom and resizing.
    @param prepared Real native scene directory.
    @return None.
    @details Frames differ while immutable engineering/display inputs do not.
    """
    names = ("input.step", "input.kicad_mod", "placement.json", "scene.json")
    before = {name: (prepared / name).read_bytes() for name in names}
    hashes = []
    for camera, size in (
        (CAMERA, [640, 400]),
        ({**CAMERA, "yaw": 90}, [640, 400]),
        ({**CAMERA, "zoom": 2}, [640, 400]),
        (CAMERA, [900, 650]),
        ({**CAMERA, "pan": [0.15, -0.1]}, [640, 400]),
        ({**CAMERA, "layers": {"body": False}}, [640, 400]),
        ({**CAMERA, "layers": {"pads": False}}, [640, 400]),
        ({**CAMERA, "layers": {"courtyard": False, "fab": False}}, [640, 400]),
        ({**CAMERA, "selected_pad": "1"}, [640, 400]),
    ):
        (prepared / "camera.json").write_text(
            json.dumps({**camera, "size": size}), encoding="utf-8"
        )
        subprocess.run(
            worker_command("render", prepared),
            check=True,
            timeout=15,
            capture_output=True,
        )
        frame = (prepared / "frame.rgb").read_bytes()
        assert len(frame) == size[0] * size[1] * 3
        assert len(set(frame)) > 30
        hashes.append(sha256(frame).hexdigest())
    assert len(set(hashes)) == 9
    assert before == {name: (prepared / name).read_bytes() for name in names}


def test_coplanar_terminal_faces_have_stable_material(prepared):
    """@brief Checks actual overlapping STEP surfaces render without noise.
    @param prepared Real native scene directory.
    @return None.
    @details Samples an independently calculated terminal-face screen region.
    A numerical depth tie must prefer the terminal's material consistently.
    """
    (prepared / "camera.json").write_text(
        json.dumps({"yaw": 0, "elevation": 0, "zoom": 1, "size": [400, 300]}),
        encoding="utf-8",
    )
    subprocess.run(
        worker_command("render", prepared),
        check=True,
        timeout=15,
        capture_output=True,
    )
    frame = (prepared / "frame.rgb").read_bytes()
    # +Y-facing terminal face: X in 0.3–0.5 mm, Z in 0–0.1 mm.
    # Scale is 140 px/mm; centre is (200, 150), model centre Z=0.175.
    colours = {
        tuple(frame[(y * 400 + x) * 3 : (y * 400 + x) * 3 + 3])
        for y in range(164, 172)
        for x in range(247, 265)
    }
    assert colours == {(99, 105, 113)}


@pytest.mark.parametrize(
    "stage,mode",
    [
        ("prepare", "exit"),
        ("prepare", "timeout"),
        ("render", "exit"),
        ("render", "timeout"),
    ],
)
def test_native_termination_and_timeout_are_contained(stage, mode):
    """@brief Injects actual native-process exits and bounded timeouts.
    @param stage Preparation or rendering failure boundary.
    @param mode Abrupt termination or a stalled child.
    @return None.
    @details Failure identifies its stage; cleanup reaps children.
    """

    def command(operation, root):
        """@brief Supplies a real failing child at the selected boundary.
        @param operation Requested native operation.
        @param root Native directory.
        @return Child command arguments.
        @details Other stages use the real native implementation.
        """
        if operation != stage:
            return worker_command(operation, root)
        code = (
            "import os; os._exit(23)"
            if mode == "exit"
            else ("import time; time.sleep(60)")
        )
        return [sys.executable, "-c", code]

    controller = SceneController(
        fixture_source(),
        command=command,
        prepare_timeout=0.4
        if stage == "prepare" and mode == "timeout"
        else 30,
        render_timeout=0.4,
    )
    controller.request(CAMERA, (400, 300))
    controller.start()
    try:
        event = wait_events(controller, "failed")
        assert event.stage == stage
        assert event.payload == (
            "VIEWER_CHILD_EXIT:23" if mode == "exit" else "VIEWER_TIMEOUT"
        )
    finally:
        cleanup(controller)


def test_malformed_step_is_contained_and_source_is_retained():
    """@brief Sends malformed STEP through the real native parser boundary.
    @return None.
    @details The caller survives with exact inputs and can retry separately.
    """
    source = replace(fixture_source(), step=b"ISO-10303-21; malformed")
    controller = SceneController(source)
    controller.start()
    try:
        event = wait_events(controller, "failed")
        assert event.stage == "prepare"
        assert controller.source is source
    finally:
        cleanup(controller)


def test_controller_cancel_releases_child_and_coalesces_camera():
    """@brief Checks cancellation and bounded pending-camera storage.
    @return None.
    @details Close can interrupt native import without waiting in the caller.
    """
    controller = SceneController(fixture_source())
    for yaw in range(100):
        controller.request({**CAMERA, "yaw": yaw}, (400, 300))
    assert controller.pending[0] == 100
    assert controller.pending[1]["yaw"] == 99
    controller.start()
    end = time.monotonic() + 5
    while controller.process is None and time.monotonic() < end:
        time.sleep(0.01)
    child = controller.process
    assert child is not None
    cleanup(controller)
    assert child.poll() is not None
    assert controller.latest_frame is None


def test_persistent_renderer_reuses_mesh_and_survives_idle_timeout():
    """@brief Checks mesh caching, worker reuse and per-frame deadlines.
    @return None.
    @details An idle viewer stays usable beyond its frame timeout; later
    frames use the same child and cached mesh even if the transport changes.
    """
    controller = SceneController(fixture_source(), render_timeout=1)
    controller.request(CAMERA, (400, 300))
    controller.start()
    try:
        first = wait_events(controller, "frame")
        child = controller.process
        assert child is not None
        (controller.directory / "scene.json").write_bytes(b"invalid transport")
        time.sleep(1.1)
        for yaw in (45, 65, 85):
            revision = controller.request({**CAMERA, "yaw": yaw}, (400, 300))
            frame = wait_events(controller, "frame")
            assert frame.revision == revision
            assert frame.payload != first.payload
            assert controller.process is child
            assert child.poll() is None
        assert (controller.directory / "input.step").read_bytes() == (
            controller.source.step
        )
    finally:
        cleanup(controller)
    assert child.poll() is not None


def test_continuous_camera_updates_publish_intermediate_and_final_frames():
    """@brief Prevents display starvation while camera requests keep arriving.
    @return None.
    @details Complete frames advance monotonically during movement, and the
    last camera is eventually rendered after movement ends.
    """
    controller = SceneController(fixture_source())
    controller.request(CAMERA, (640, 400))
    controller.start()
    try:
        initial = wait_events(controller, "frame")
        frames = []
        logs = []
        until = time.monotonic() + 1.5
        while time.monotonic() < until:
            revision = controller.request(
                {**CAMERA, "yaw": controller.revision * 0.4}, (640, 400)
            )
            for event in controller.drain():
                if event.outcome == "log":
                    logs.append(event.payload)
                assert event.outcome != "failed", (event, logs)
                if event.outcome == "frame":
                    frames.append((event.revision, revision))
            time.sleep(0.005)
        assert len(frames) >= 3
        assert any(rendered < requested for rendered, requested in frames)
        revisions = [initial.revision, *(frame[0] for frame in frames)]
        assert revisions == sorted(set(revisions))
        final_revision = controller.request({**CAMERA, "yaw": 180}, (400, 300))
        final = wait_events(controller, "frame")
        assert final.revision == final_revision
        assert final.payload[:2] == (400, 300)
    finally:
        cleanup(controller)


def test_camera_requests_snapshot_nested_state():
    """@brief Freezes mutable pan and layer settings at the request boundary.
    @return None.
    @details Later GUI mutations cannot change an already submitted camera.
    """
    controller = SceneController(fixture_source())
    camera = {**CAMERA, "pan": [0, 0], "layers": {"body": True}}
    controller.request(camera, (400, 300))
    camera["pan"][0] = 1
    camera["layers"]["body"] = False
    assert controller.pending[1]["pan"] == [0, 0]
    assert controller.pending[1]["layers"] == {"body": True}


def test_persistent_frame_timeout_after_worker_startup():
    """@brief Contains a renderer that starts but never completes its frame.
    @return None.
    @details The deadline covers individual requests after startup readiness.
    """

    def command(stage, root):
        """@brief Injects a live renderer stuck after advertising readiness.
        @param stage Native operation requested by the controller.
        @param root Private transport directory.
        @return Command arguments for preparation or the stalled renderer.
        @details The child stays alive until timeout supervision reaps it.
        """
        if stage != "render":
            return worker_command(stage, root)
        code = (
            "import sys,time;from pathlib import Path;"
            "Path(sys.argv[1],'render-ready').touch();time.sleep(60)"
        )
        return [sys.executable, "-c", code, str(root)]

    controller = SceneController(
        fixture_source(), command=command, render_timeout=0.4
    )
    controller.request(CAMERA, (400, 300))
    controller.start()
    try:
        event = wait_events(controller, "failed")
        assert event.stage == "render"
        assert event.payload == "VIEWER_TIMEOUT"
    finally:
        cleanup(controller)


def test_input_and_viewport_limits_fail_before_native_allocation():
    """@brief Rejects oversized inputs and decoded frame allocations.
    @return None.
    @details No controller thread or native child is created by invalid input.
    """
    source = fixture_source()
    with pytest.raises(ValueError, match="VIEWER_INPUT_LIMIT"):
        SceneController(replace(source, step=b"x" * (MAX_STEP_BYTES + 1)))
    controller = SceneController(source)
    with pytest.raises(ValueError, match="VIEWER_RENDER_LIMIT"):
        controller.request(CAMERA, (4096, 4096))
    assert controller.thread is None


def test_gui_import_does_not_load_cad_or_graphics_renderer():
    """@brief Checks that the desktop import avoids native preparation code.
    @return None.
    @details Real CAD and Pillow rasterizer imports belong only to children.
    """
    command = worker_command("prepare", ROOT)
    bootstrap = (
        "import sys; sys.path.insert(0,sys.argv[1]); "
        "import partsmith.gui.app; "
        "assert 'cadquery' not in sys.modules; "
        "assert 'vtk' not in sys.modules; "
        "assert 'PIL.ImageDraw' not in sys.modules"
    )
    # wx is optional in headless CI; this check exercises non-wx scene imports.
    bootstrap = bootstrap.replace(
        "partsmith.gui.app", "partsmith.gui.scene_controller"
    )
    subprocess.run(
        [sys.executable, "-c", bootstrap, command[3]],
        check=True,
        capture_output=True,
        timeout=15,
    )
