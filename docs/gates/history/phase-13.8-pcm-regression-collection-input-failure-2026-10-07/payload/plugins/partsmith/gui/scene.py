"""@package partsmith.gui.scene
@brief Defines bounded, read-only inputs for the placement prototype.
@details Native CAD imports occur only inside the preparation subprocess.
"""

import json
import math
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

MAX_STEP_BYTES = 8 * 1024 * 1024
MAX_FOOTPRINT_BYTES = 1024 * 1024
MAX_SCENE_BYTES = 16 * 1024 * 1024
MAX_TRIANGLES = 100_000
MAX_VERTICES = 100_000
MAX_PIXELS = 4_000_000
MESH_TOLERANCE_MM = 0.01


@dataclass(frozen=True)
class SceneSource:
    """@brief Holds an immutable artifact pair and exact placement bytes.
    @details These display inputs cannot grant review or release approval.
    """

    step: bytes
    footprint: bytes
    placement: bytes

    def validate(self) -> None:
        """@brief Checks input lengths before copying or native import.
        @return None.
        @details Raises ValueError for absent or oversized input bytes.
        """
        for content, limit in (
            (self.step, MAX_STEP_BYTES),
            (self.footprint, MAX_FOOTPRINT_BYTES),
            (self.placement, 16_384),
        ):
            if not isinstance(content, bytes) or not 0 < len(content) <= limit:
                raise ValueError("VIEWER_INPUT_LIMIT: missing/oversized input")


def fixture_source() -> SceneSource:
    """@brief Reads the independently generated packaged 0402 artifacts.
    @return SceneSource with STEP, footprint, and explicit IR placement.
    @details Works from an installed wheel without the repository or cwd.
    """
    root = files("partsmith.gui").joinpath("prototype")
    if not root.joinpath("0402.step").is_file():
        repository = Path(__file__).resolve().parents[3]
        return SceneSource(
            (repository / "fixtures/threed/expected/0402.step").read_bytes(),
            (
                repository / "fixtures/footprint/expected/0402.kicad_mod"
            ).read_bytes(),
            (repository / "fixtures/viewer/0402-placement.json").read_bytes(),
        )
    return SceneSource(
        root.joinpath("0402.step").read_bytes(),
        root.joinpath("0402.kicad_mod").read_bytes(),
        root.joinpath("0402-placement.json").read_bytes(),
    )


def validate_placement(data: dict):
    """@brief Checks supported placement without importing native CAD code.
    @param data Explicit convention-1.1 placement metadata.
    @return Numeric vectors and supported mirror flags for display preparation.
    @details Rejects unsupported frames and invalid/nonfinite scales
    explicitly.
    """
    if (
        data.get("units") != {"length": "mm", "angle": "deg"}
        or data.get("convention_version") != "1.1"
        or data.get("order") != "T*R*S*M"
        or data.get("source_coordinate_system") != "component"
        or data.get("destination_coordinate_system") != "footprint"
    ):
        raise ValueError("VIEWER_TRANSFORM: unsupported coordinate contract")
    vectors = []
    for name in ("translation_mm", "rotation_deg", "scale"):
        vector = data.get(name)
        if not isinstance(vector, list) or len(vector) != 3:
            raise ValueError("VIEWER_TRANSFORM: invalid vector")
        if any(isinstance(value, bool) for value in vector):
            raise ValueError("VIEWER_TRANSFORM: invalid numeric value")
        values = tuple(float(value) for value in vector)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("VIEWER_TRANSFORM: non-finite vector")
        vectors.append(values)
    if any(value <= 0 for value in vectors[2]):
        raise ValueError("VIEWER_TRANSFORM: scale must be positive")
    mirror = data.get("mirror", {})
    if set(mirror) != {"x", "y", "z"} or any(
        type(value) is not bool for value in mirror.values()
    ):
        raise ValueError("VIEWER_TRANSFORM: invalid mirror flags")
    return vectors, mirror


def placement_transform(data: dict):
    """@brief Converts supported exact placement using existing native
    services.
    @param data Explicit supported convention-1.1 placement metadata.
    @return AffineTransform from component to footprint in millimetres.
    @details Called only by isolated scene preparation; CAD imports stay there.
    """
    from partsmith.threed.transform import MirrorState, Placement, to_affine

    vectors, mirror = validate_placement(data)
    return to_affine(
        Placement(*vectors, MirrorState(**mirror), "component", "footprint")
    )


def footprint_nodes(content: bytes) -> list:
    """@brief Parses the bounded KiCad footprint wrapper.
    @param content Generated KiCad footprint bytes, independent of STEP.
    @return Parsed direct footprint nodes.
    @details Rejects malformed and excessively nested input explicitly.
    """
    text = content.decode("utf-8")
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    roots = []
    for token in tokens:
        if token == "(":
            if len(stack) >= 32:
                raise ValueError("VIEWER_FOOTPRINT: excessive nesting")
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("VIEWER_FOOTPRINT: unbalanced syntax")
            stack.pop()
        elif not stack:
            raise ValueError("VIEWER_FOOTPRINT: invalid wrapper")
        else:
            stack[-1].append(json.loads(token) if token[0] == '"' else token)
    if stack or len(roots) != 1 or roots[0][0] != "footprint":
        raise ValueError("VIEWER_FOOTPRINT: invalid wrapper")
    return roots[0]


def parse_footprint(content: bytes) -> list[dict]:
    """@brief Reads actual generated footprint pads into display geometry.
    @param content Generated KiCad footprint bytes, independent of STEP.
    @return Pads with number, shape, centre, size and corner ratio.
    @details Supports generated unrotated front SMD pads; unsupported pad
    fields or coordinate conventions fail explicitly.
    """
    pads = []
    for node in footprint_nodes(content):
        if not isinstance(node, list) or not node or node[0] != "pad":
            continue
        if len(node) < 7 or node[2:4] not in (
            ["smd", "rect"],
            ["smd", "roundrect"],
            ["smd", "circle"],
            ["smd", "oval"],
        ):
            raise ValueError("VIEWER_FOOTPRINT: unsupported pad")
        fields = {}
        for field in node[4:]:
            if not isinstance(field, list) or not field or field[0] in fields:
                raise ValueError("VIEWER_FOOTPRINT: invalid pad fields")
            fields[field[0]] = field[1:]
        if (
            set(fields) - {"at", "size", "layers", "roundrect_rratio"}
            or len(fields.get("at", [])) != 2
            or len(fields.get("size", [])) != 2
            or fields.get("layers") != ["F.Cu", "F.Paste", "F.Mask"]
            or (node[3] != "roundrect" and "roundrect_rratio" in fields)
        ):
            raise ValueError("VIEWER_FOOTPRINT: unsupported pad fields")
        centre = [float(value) for value in fields["at"]]
        size = [float(value) for value in fields["size"]]
        ratio_values = fields.get("roundrect_rratio", ["0"])
        if len(ratio_values) != 1:
            raise ValueError("VIEWER_FOOTPRINT: invalid corner ratio")
        ratio = float(ratio_values[0])
        if (
            not all(math.isfinite(value) for value in [*centre, *size, ratio])
            or any(value <= 0 for value in size)
            or not 0 <= ratio <= 0.5
            or (node[3] == "roundrect" and "roundrect_rratio" not in fields)
            or (node[3] == "circle" and size[0] != size[1])
        ):
            raise ValueError("VIEWER_FOOTPRINT: invalid pad dimensions")
        pads.append(
            dict(
                number=node[1],
                shape=node[3],
                centre=centre,
                size=size,
                corner_ratio=ratio,
            )
        )
    if not pads or len(pads) > 1024:
        raise ValueError("VIEWER_FOOTPRINT: absent/oversized pad collection")
    return pads


def footprint_graphics(content: bytes) -> list[dict]:
    """@brief Reads actual generated silk, courtyard and fabrication graphics.
    @param content Independently generated KiCad footprint bytes.
    @return Layer-bound lines, rectangles, circles and text anchors.
    @details Never synthesizes missing package outlines or pin-1 markings.
    """
    graphics = []
    for node in footprint_nodes(content):
        if not isinstance(node, list) or not node:
            continue
        if node[0] not in {"fp_line", "fp_rect", "fp_circle", "fp_text"}:
            if node[0].startswith("fp_"):
                raise ValueError("VIEWER_GRAPHIC: unsupported primitive")
            continue
        fields = {item[0]: item[1:] for item in node if isinstance(item, list)}
        layer = fields.get("layer", [None])[0]
        if layer not in {"F.SilkS", "F.CrtYd", "F.Fab"}:
            continue
        keys = (
            ("at",)
            if node[0] == "fp_text"
            else (
                ("center", "end")
                if node[0] == "fp_circle"
                else ("start", "end")
            )
        )
        points = []
        for key in keys:
            values = fields.get(key, [])
            if len(values) != 2:
                raise ValueError("VIEWER_GRAPHIC: unsupported coordinates")
            point = [float(value) for value in values]
            if not all(math.isfinite(value) for value in point):
                raise ValueError("VIEWER_GRAPHIC: non-finite coordinates")
            points.append(point)
        graphics.append(
            {
                "kind": node[0],
                "layer": layer,
                "points": points,
                "text": node[2] if node[0] == "fp_text" else "",
            }
        )
    return graphics
