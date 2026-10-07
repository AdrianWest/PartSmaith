"""@package partsmith.integration.instance_semantics
@brief Compares read-only PCB instances with approved installed mappings.
@details Comparator 1.0 covers top-side pad centres and footprint-local model
parameters. Unsupported sides fail visibly. Reports grant no execution right.
"""

from decimal import Decimal
from math import cos, radians, sin

from .ipc import BoardInspection
from .staging import relocated


def _nodes(tree, tag):
    """@brief Traverses bounded parsed native trees for an exact node tag.
    @param tree Already bounded parsed symbol or footprint tree.
    @param tag Exact requested tag.
    @return Matching nodes in traversal order.
    @details Does not infer inherited or missing values.
    """
    found = []
    if isinstance(tree, list):
        if tree and tree[0] == tag:
            found.append(tree)
        for child in tree[1:]:
            found.extend(_nodes(child, tag))
    return found


def _vector(model, name):
    """@brief Extracts one explicit footprint-local model vector.
    @param model Approved relocated model node.
    @param name Offset, rotate or scale node tag.
    @return Exact decimal XYZ tuple.
    @details Missing or duplicate fields raise instead of defaulting.
    """
    nodes = _nodes(model, name)
    if len(nodes) != 1 or len(nodes[0]) != 2:
        raise ValueError("Ambiguous model vector")
    xyz = nodes[0][1]
    if not isinstance(xyz, list) or xyz[0] != "xyz" or len(xyz) != 4:
        raise ValueError("Invalid model vector")
    return tuple(Decimal(v) for v in xyz[1:])


def compare_instances(inspection: BoardInspection, sources, mappings) -> dict:
    """@brief Compares actual instances to exact approved engineering sources.
    @param inspection Immutable declared-unit read from a selected PCB session.
    @param sources Verified approved packages in installation mapping order.
    @param mappings Exact current installation manifest component mappings.
    @return Data-only semantic report with visible mismatch categories.
    @details Global pad positions allow 0.000001 mm native rounding. Model
    parameters allow 0.000000001 scalar tolerance. No board write is performed.
    """
    if len(sources) != len(mappings) or len(mappings) > 10000:
        raise ValueError("Invalid comparison inventory")
    components = []
    for source, mapping in zip(sources, mappings, strict=True):
        if source.component_id != mapping["component_id"]:
            raise ValueError("Source mapping identity mismatch")
        symbol, footprint = relocated(source, mapping)
        pins = sorted({n[1] for n in _nodes(symbol, "number")})
        pads = _nodes(footprint, "pad")
        numbers = sorted({n[1] for n in pads})
        library_id = (
            mapping["footprint_nickname"] + ":" + (mapping["footprint_name"])
        )
        instances = []
        for actual in inspection.footprints:
            if actual.library_id != library_id:
                continue
            failures = []
            if actual.side != "top":
                failures.append("UNSUPPORTED_SIDE")
            if pins != numbers or numbers != sorted(
                {p.number for p in actual.pads}
            ):
                failures.append("PIN_PAD_MAPPING_MISMATCH")
            angle = radians(float(actual.orientation_degrees))
            expected = []
            for pad in pads:
                at = _nodes(pad, "at")[0]
                x, y = float(at[1]), float(at[2])
                expected.append(
                    (
                        pad[1],
                        float(actual.x_mm) + x * cos(angle) + y * sin(angle),
                        float(actual.y_mm) + x * sin(angle) - y * cos(angle),
                    )
                )
            observed = [
                (p.number, float(p.x_mm), float(p.y_mm)) for p in actual.pads
            ]
            if len(expected) != len(observed) or any(
                a[0] != b[0]
                or abs(a[1] - b[1]) > 0.000001
                or abs(a[2] - b[2]) > 0.000001
                for a, b in zip(
                    sorted(expected), sorted(observed), strict=True
                )
            ):
                failures.append("PAD_PLACEMENT_MISMATCH")
            models = _nodes(footprint, "model")
            if len(models) != len(actual.models):
                failures.append("MODEL_COUNT_MISMATCH")
            for expected_model, model in zip(
                models, actual.models, strict=False
            ):
                if expected_model[1] != model.filename:
                    failures.append("MODEL_REFERENCE_MISMATCH")
                for tag, value in (
                    ("offset", model.offset_mm),
                    ("rotate", model.rotation_degrees),
                    ("scale", model.scale),
                ):
                    if any(
                        abs(a - Decimal(b)) > Decimal("0.000000001")
                        for a, b in zip(
                            _vector(expected_model, tag), value, strict=True
                        )
                    ):
                        failures.append("MODEL_PLACEMENT_MISMATCH")
                if not model.visible:
                    failures.append("MODEL_HIDDEN")
            instances.append(
                {
                    "reference": actual.reference,
                    "item_id": actual.item_id,
                    "blocking_codes": sorted(set(failures)),
                    "passed": not failures,
                }
            )
        components.append(
            {
                "source": source.binding(),
                "library_id": library_id,
                "pin_numbers": pins,
                "pad_numbers": numbers,
                "instances": instances,
                "passed": bool(instances)
                and all(i["passed"] for i in instances),
            }
        )
    return {
        "schema_version": "partsmith-instance-semantics-1.0",
        "board_path": inspection.capabilities.board_path,
        "evidence_origin": inspection.capabilities.evidence_origin,
        "components": components,
        "passed": bool(components) and all(c["passed"] for c in components),
        "installation_authority": False,
    }
