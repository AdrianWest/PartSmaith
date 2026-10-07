"""@package partsmith.gui.scene_worker
@brief Prepares CAD meshes and rasterizes them outside the wx process.
@details A persistent rasterizer caches display geometry until worker exit.
"""

import json
import math
import os
import sys
import time
import traceback
from hashlib import sha256
from pathlib import Path

from .scene import (
    MAX_PIXELS,
    MAX_SCENE_BYTES,
    MAX_TRIANGLES,
    MAX_VERTICES,
    MESH_TOLERANCE_MM,
    SceneSource,
    footprint_graphics,
    parse_footprint,
    placement_transform,
)
from .scene_transport import publish_text, read_message


def prepare(root: Path) -> None:
    """@brief Imports a bounded STEP snapshot and prepares display triangles.
    @param root Private worker directory containing the immutable inputs.
    @return None.
    @details CAD handles belong only to this process; no artifact is rewritten.
    Units are normalized by the existing STEP importer into millimetres.
    """
    import cadquery as cq

    from partsmith.ir.canonical import parse_json
    from partsmith.threed.transform import apply_point

    source = SceneSource(
        *(
            root.joinpath(name).read_bytes()
            for name in ("input.step", "input.kicad_mod", "placement.json")
        )
    )
    source.validate()
    transform = placement_transform(parse_json(source.placement))
    pads = parse_footprint(source.footprint)
    shape = cq.importers.importStep(str(root / "input.step")).val()
    solids = shape.Solids()
    if not solids or len(solids) > 256:
        raise ValueError("VIEWER_STEP: absent/oversized solid collection")
    triangles = []
    points = []
    solid_bounds = []
    for index, solid in enumerate(solids):
        vertices, faces = solid.tessellate(MESH_TOLERANCE_MM, 0.1)
        if len(points) + len(vertices) > MAX_VERTICES:
            raise ValueError("VIEWER_MESH_LIMIT: too many vertices")
        if len(triangles) + len(faces) > MAX_TRIANGLES:
            raise ValueError("VIEWER_MESH_LIMIT: too many triangles")
        transformed = [
            apply_point(transform, vertex.toTuple()) for vertex in vertices
        ]
        points.extend(transformed)
        solid_bounds.append(
            [
                [min(point[i] for point in transformed) for i in range(3)],
                [max(point[i] for point in transformed) for i in range(3)],
            ]
        )
        for face in faces:
            triangles.append(
                {
                    "points": [transformed[i] for i in face],
                    "colour": [64, 78, 100] if index == 0 else [180, 190, 206],
                }
            )
    if not triangles or not all(
        math.isfinite(value) for point in points for value in point
    ):
        raise ValueError("VIEWER_MESH: empty/non-finite geometry")
    bounds = [
        [min(point[i] for point in points) for i in range(3)],
        [max(point[i] for point in points) for i in range(3)],
    ]
    scene = {
        "version": "placement-display-1.0",
        "units": "mm",
        "bounds_mm": bounds,
        "solid_bounds_mm": solid_bounds,
        "triangles": triangles,
        "pads": pads,
        "graphics": footprint_graphics(source.footprint),
        "matrix": transform.matrix,
        "tolerance_mm": MESH_TOLERANCE_MM,
        "input_sha256": {
            name: sha256(value).hexdigest()
            for name, value in (
                ("step", source.step),
                ("footprint", source.footprint),
                ("placement", source.placement),
            )
        },
    }
    content = json.dumps(scene, allow_nan=False).encode("utf-8")
    if len(content) > MAX_SCENE_BYTES:
        raise ValueError("VIEWER_MESH_LIMIT: scene transport too large")
    (root / "scene.json").write_bytes(content)


def pad_outline(pad: dict) -> list[tuple]:
    """@brief Builds actual generated rectangular, rounded, circle/oval pads.
    @param pad Parsed footprint pad in engineering millimetres.
    @return List of three-dimensional perimeter points at board Z=0.
    @details Rounded display chords stay within 0.01 mm of actual outlines.
    """
    x, y = pad["centre"]
    w, h = (value / 2 for value in pad["size"])
    radius = min(pad["size"]) * pad["corner_ratio"]
    if pad["shape"] in {"circle", "oval"}:
        radius = min(w, h)
    if pad["shape"] == "rect" or radius == 0:
        return [
            (x - w, y - h, 0),
            (x + w, y - h, 0),
            (x + w, y + h, 0),
            (x - w, y + h, 0),
        ]
    points = []
    segments = max(
        8,
        math.ceil(
            math.pi
            / 2
            / (2 * math.acos(max(-1, 1 - MESH_TOLERANCE_MM / radius)))
        ),
    )
    for cx, cy, start in (
        (x + w - radius, y + h - radius, 0),
        (x - w + radius, y + h - radius, 90),
        (x - w + radius, y - h + radius, 180),
        (x + w - radius, y - h + radius, 270),
    ):
        for i in range(segments + 1):
            angle = math.radians(start + i * 90 / segments)
            points.append(
                (
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                    0,
                )
            )
    return points


def load_render_scene(root: Path) -> dict:
    """@brief Loads and caches camera-independent display geometry.
    @param root Private directory containing the bounded prepared mesh.
    @return Scene dictionary with cached pad outlines and material colours.
    @details Derived caches stay in the renderer and never rewrite inputs.
    """
    if (root / "scene.json").stat().st_size > MAX_SCENE_BYTES:
        raise ValueError("VIEWER_MESH_LIMIT: scene transport too large")
    scene = json.loads((root / "scene.json").read_bytes())
    for pad in scene["pads"]:
        pad["outline"] = pad_outline(pad)
    for triangle in scene["triangles"]:
        a, b, c = triangle["points"]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        normal = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        length = math.sqrt(sum(n * n for n in normal)) or 1
        light = 0.55 + 0.45 * abs(normal[2]) / length
        triangle["lit_colour"] = tuple(
            round(value * light) for value in triangle["colour"]
        )
    return scene


def render(root: Path, scene: dict | None = None, camera: dict | None = None):
    """@brief Renders a bounded orthographic scene to a raw RGB frame.
    @param root Directory containing the scene and latest camera request.
    @param scene Optional worker-owned cached display geometry.
    @param camera Optional immutable camera request supplied by the stream.
    @return None.
    @details Pillow and its native rasterizer live only in this subprocess.
    No OpenGL context, GPU, textures or driver extension is required.
    """
    import numpy as np
    from PIL import Image, ImageDraw

    if scene is None:
        scene = load_render_scene(root)
    if camera is None:
        camera = json.loads((root / "camera.json").read_bytes())
    width, height = camera["size"]
    if (
        type(width) is not int
        or type(height) is not int
        or not 1 <= width <= 4096
        or not 1 <= height <= 4096
        or width * height > MAX_PIXELS
    ):
        raise ValueError("VIEWER_RENDER_LIMIT: viewport too large")
    yaw, elevation, zoom = (
        float(camera[key]) for key in ("yaw", "elevation", "zoom")
    )
    if not all(math.isfinite(value) for value in (yaw, elevation, zoom)):
        raise ValueError("VIEWER_CAMERA: non-finite camera")
    if not 0.2 <= zoom <= 8:
        raise ValueError("VIEWER_CAMERA: zoom outside profile")
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    ce, se = (
        math.cos(math.radians(elevation)),
        math.sin(math.radians(elevation)),
    )
    low, high = scene["bounds_mm"]
    centre = [(a + b) / 2 for a, b in zip(low, high, strict=True)]
    span = max(1.5, *(b - a for a, b in zip(low, high, strict=True)))
    scale = min(width, height) * 0.7 * zoom / span
    pan = camera.get("pan", [0, 0])
    if len(pan) != 2 or not all(math.isfinite(float(v)) for v in pan):
        raise ValueError("VIEWER_CAMERA: invalid pan")
    layers = camera.get("layers", {})

    def project(point):
        """@brief Projects a world point through the display-only camera.
        @param point Footprint-frame point in millimetres.
        @return Screen X/Y and camera depth.
        @details Does not modify engineering placement or coordinates.
        """
        x, y, z = (a - b for a, b in zip(point, centre, strict=True))
        horizontal = cy * x - sy * y
        forward = sy * x + cy * y
        return (
            width / 2 + horizontal * scale + float(pan[0]) * width,
            height / 2
            + (se * forward - ce * z) * scale
            + float(pan[1]) * height,
            ce * forward + se * z,
        )

    pixels = np.empty((height, width, 3), dtype=np.uint8)
    pixels[:] = (19, 27, 40)
    depth = np.full((height, width), -np.inf, dtype=np.float64)

    def rasterize(vertices, colour):
        """@brief Rasterizes one projected triangle with depth testing.
        @param vertices Three screen X/Y and depth points.
        @param colour RGB material colour.
        @return None.
        @details Z buffering handles overlapping body/terminal surfaces;
        allocations are clipped to the bounded viewport before rasterization.
        """
        a, b, c = vertices
        xmin = max(0, math.floor(min(p[0] for p in vertices)))
        xmax = min(width - 1, math.ceil(max(p[0] for p in vertices)))
        ymin = max(0, math.floor(min(p[1] for p in vertices)))
        ymax = min(height - 1, math.ceil(max(p[1] for p in vertices)))
        if xmin > xmax or ymin > ymax:
            return
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (
            a[1] - c[1]
        )
        if abs(denominator) < 1e-12:
            return
        ys, xs = np.ogrid[ymin : ymax + 1, xmin : xmax + 1]
        w1 = (
            (b[1] - c[1]) * (xs + 0.5 - c[0])
            + (c[0] - b[0]) * (ys + 0.5 - c[1])
        ) / denominator
        w2 = (
            (c[1] - a[1]) * (xs + 0.5 - c[0])
            + (a[0] - c[0]) * (ys + 0.5 - c[1])
        ) / denominator
        w3 = 1 - w1 - w2
        candidate = w1 * a[2] + w2 * b[2] + w3 * c[2]
        tile = depth[ymin : ymax + 1, xmin : xmax + 1]
        # STEP body/end solids share coplanar faces. Prefer the later
        # material within numerical noise rather than create z fighting.
        visible = (
            (w1 >= -1e-9)
            & (w2 >= -1e-9)
            & (w3 >= -1e-9)
            & (candidate >= tile - 1e-9 * span)
        )
        tile[visible] = candidate[visible]
        pixels[ymin : ymax + 1, xmin : xmax + 1][visible] = colour

    for pad in scene["pads"] if layers.get("pads", True) else []:
        vertices = [project(point) for point in pad["outline"]]
        centre_point = project((*pad["centre"], 0))
        for i, point in enumerate(vertices):
            rasterize(
                (centre_point, point, vertices[(i + 1) % len(vertices)]),
                (255, 80, 90)
                if pad["number"] == camera.get("selected_pad")
                else (204, 145, 60),
            )
    for triangle in scene["triangles"] if layers.get("body", True) else []:
        vertices = [project(point) for point in triangle["points"]]
        rasterize(vertices, triangle["lit_colour"])

    with Image.fromarray(pixels) as image:
        draw = ImageDraw.Draw(image)
        origin = project((0, 0, 0))[:2]
        if layers.get("origin", True):
            x, y = origin
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), outline=(255, 255, 255))
        for axis, colour in enumerate(
            ((231, 95, 99), (105, 214, 153), (93, 174, 255))
        ):
            if not layers.get("axes", True):
                break
            endpoint = [0, 0, 0]
            endpoint[axis] = 0.8
            end = project(endpoint)[:2]
            draw.line([origin, end], fill=colour, width=2)
            draw.text(end, "XYZ"[axis], fill=colour)
        for graphic in scene.get("graphics", []):
            layer = {
                "F.SilkS": "silk",
                "F.CrtYd": "courtyard",
                "F.Fab": "fab",
            }[graphic["layer"]]
            if not layers.get(layer, True):
                continue
            colour = {
                "silk": (240, 240, 240),
                "courtyard": (185, 116, 250),
                "fab": (94, 210, 218),
            }[layer]
            points = graphic["points"]
            if graphic["kind"] == "fp_rect":
                a, b = points
                points = [a, [b[0], a[1]], b, [a[0], b[1]], a]
            elif graphic["kind"] == "fp_circle":
                centre, edge = points
                radius = math.dist(centre, edge)
                points = [
                    [
                        centre[0] + radius * math.cos(i * math.pi / 32),
                        centre[1] + radius * math.sin(i * math.pi / 32),
                    ]
                    for i in range(65)
                ]
            projected = [project((*point, 0))[:2] for point in points]
            if graphic["kind"] == "fp_text":
                draw.text(projected[0], graphic["text"], fill=colour)
            else:
                draw.line(projected, fill=colour, width=1)
        for pad in scene["pads"] if layers.get("pads", True) else []:
            x, y = pad["centre"]
            point = project((x, y, 0))[:2]
            draw.text(
                (point[0] - 12, point[1] + 18),
                f"Pad {pad['number']}",
                fill=(255, 221, 143),
            )
        for pad in scene["pads"]:
            point = project((*pad["centre"], 0))[:2]
            if pad["number"] == "1" and layers.get("pin1", True):
                draw.ellipse(
                    (point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4),
                    fill=(255, 65, 90),
                )
        dimensions = " x ".join(
            f"{b - a:.3f}" for a, b in zip(low, high, strict=True)
        )
        draw.text(
            (16, 16),
            f"Actual STEP | {dimensions} mm | mesh tolerance 0.01 mm",
            fill=(226, 235, 248),
        )
        draw.text(
            (16, 34),
            "Origin: footprint centre; +Z above board",
            fill=(172, 190, 213),
        )
        (root / "frame.rgb").write_bytes(image.tobytes())


def serve(root: Path) -> None:
    """@brief Reuses one isolated rasterizer for successive camera requests.
    @param root Private controller-owned transport directory.
    @return None; runs until the supervising controller stops the process.
    @details Atomic request/acknowledgement files permit one frame in flight.
    The controller enforces each frame's deadline and all native cleanup.
    """
    scene = load_render_scene(root)
    (root / "render-ready").touch()
    revision = 0
    request = root / "camera-request.json"
    while True:
        content = read_message(request)
        if content is not None:
            message = json.loads(content)
            if message["revision"] > revision:
                revision = message["revision"]
                render(root, scene, message["camera"])
                publish_text(root / "frame-ready", str(revision))
                continue
        time.sleep(0.004)


def main() -> int:
    """@brief Executes private preparation, a single frame or a render stream.
    @return Integer exit status, zero on successful output publication.
    @details Suppresses native Windows crash dialogs; exports safe error codes.
    """
    if os.name == "nt":
        import ctypes

        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    root = Path(sys.argv[2])
    try:
        operation = {"prepare": prepare, "render": render}[sys.argv[1]]
        if sys.argv[1] == "render" and "--persistent" in sys.argv[3:]:
            operation = serve
        operation(root)
    except Exception:
        traceback.print_exc()
        (root / "error").write_text("VIEWER_WORKER_ERROR", encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
