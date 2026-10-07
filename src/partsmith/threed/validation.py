"""@package src.partsmith.threed.validation
@brief Phase 7 STEP and footprint-to-3D validation.
@details Produces strict IR 1.2 validation results for measured geometry,
declared placement, terminal mapping, and applicability.
"""

import math
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
from pathlib import Path

from partsmith.ir.model import ComponentIR, normalize_ir
from partsmith.ir.units import normalize_quantity
from partsmith.pdl import PDL
from partsmith.threed.package_geometry import terminal_dimensions
from partsmith.threed.step_backend import StepMeasurement, measure_step
from partsmith.threed.transform import (
    MirrorState,
    Placement,
    apply_bbox,
    apply_point,
    to_affine,
)


@dataclass(frozen=True)
class ValidationResult:
    """@brief One strict IR 1.2 validation result.
    @details A non-applicable result has null status and measurements and
    carries a pinned declaration basis.
    """

    id: str
    category: str
    rule_id: str
    status: str | None
    severity: str
    message: str
    evidence_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    measured: float | str | bool | None
    expected: float | str | bool | None
    tolerance: float | None
    stage: str
    applicability: str
    applicability_reason: str | None
    applicability_basis: dict | None
    measurement_mode: str

    def to_dict(self) -> dict:
        """@brief Serialize this result for an IR 1.2 report.
        @return The JSON-compatible result mapping.
        @details Converts immutable tuple bindings to JSON arrays.
        """
        result = asdict(self)
        result["evidence_ids"] = list(self.evidence_ids)
        result["artifact_ids"] = list(self.artifact_ids)
        return result


def _result(
    rule_id: str,
    passed: bool,
    message: str,
    artifact_ids: tuple[str, ...],
    *,
    measured: float | str | bool | None = None,
    expected: float | str | bool | None = None,
    tolerance: float | None = None,
    measurement_mode: str = "MEASURED",
    category: str = "model_3d",
) -> ValidationResult:
    """@brief Construct one applicable Phase 7 validation result.
    @param rule_id Stable rule identifier.
    @param passed Whether the rule passed.
    @param message Human-readable result explanation.
    @param artifact_ids Exact artifact hashes bound to the result.
    @param measured Measured scalar or summary.
    @param expected Expected scalar or summary.
    @param tolerance Applied numeric tolerance.
    @param measurement_mode MEASURED, DECLARED_ONLY, or NONE.
    @param category Validator category.
    @return The constructed validation result.
    @details Applicable failures are blocking ERROR results.
    """
    return ValidationResult(
        id=f"phase7-{rule_id}",
        category=category,
        rule_id=rule_id,
        status="PASS" if passed else "FAIL",
        severity="INFO" if passed else "ERROR",
        message=message,
        evidence_ids=(),
        artifact_ids=artifact_ids,
        measured=measured,
        expected=expected,
        tolerance=tolerance,
        stage="ARTIFACT",
        applicability="APPLICABLE",
        applicability_reason=None,
        applicability_basis=None,
        measurement_mode=measurement_mode,
    )


def _not_applicable(
    rule_id: str, feature_id: str, pdl: PDL
) -> ValidationResult:
    """@brief Construct a PDL-bound non-applicability result.
    @param rule_id Stable rule identifier.
    @param feature_id Pinned declaration identifying the absent feature.
    @param pdl Trusted package declaration.
    @return A strict non-applicable validation result.
    @details The PDL identity, revision, and declared content hash bind the
    exclusion to trusted input rather than a post-validation decision.
    """
    data = pdl.data
    return ValidationResult(
        id=f"phase7-{rule_id}",
        category="cross_artifact",
        rule_id=rule_id,
        status=None,
        severity="INFO",
        message="Pinned PDL declares this physical feature absent",
        evidence_ids=(),
        artifact_ids=(),
        measured=None,
        expected=None,
        tolerance=None,
        stage="ARTIFACT",
        applicability="NOT_APPLICABLE",
        applicability_reason="Absent in the pinned PDL revision",
        applicability_basis={
            "kind": "PDL",
            "id": data["id"],
            "revision": data["revision"],
            "sha256": data["content_sha256"],
            "feature_id": feature_id,
        },
        measurement_mode="NONE",
    )


def validate_applicability_binding(
    result: ValidationResult, pdl: PDL
) -> ValidationResult:
    """@brief Verify a non-applicable result against its pinned PDL feature.
    @param result Validation result to verify.
    @param pdl Trusted package declaration.
    @return The original result or an applicable blocking failure.
    @details Rejects stale identity, revision, hash, feature, and applicability
    bindings. Applicable results pass through unchanged.
    """
    if result.applicability != "NOT_APPLICABLE":
        return result
    data = pdl.data
    basis = result.applicability_basis or {}
    feature = next(
        (
            item
            for item in data["reference_features"]
            if item["id"] == basis.get("feature_id")
        ),
        None,
    )
    valid = (
        basis.get("kind") == "PDL"
        and basis.get("id") == data["id"]
        and basis.get("revision") == data["revision"]
        and basis.get("sha256") == data["content_sha256"]
        and feature is not None
        and feature["applicability"] == "ABSENT"
    )
    if valid:
        return result
    return _result(
        result.rule_id,
        False,
        "Non-applicability binding does not match a pinned absent feature",
        result.artifact_ids,
        measured=None,
        expected="trusted ABSENT PDL feature",
        measurement_mode="NONE",
        category=result.category,
    )


def _ir_data(ir: ComponentIR | dict) -> dict:
    """@brief Return normalized IR data.
    @param ir Component IR object or mapping.
    @return A detached normalized IR mapping.
    @details Uses the repository IR normalization contract.
    """
    return normalize_ir(ir.data if isinstance(ir, ComponentIR) else ir)


def _body_and_terminals(
    measurement: StepMeasurement, pdl_data: dict
) -> tuple[object, dict[str, object]]:
    """@brief Identify the body and nominally matched terminal solids.
    @param measurement Parsed STEP measurements.
    @param pdl_data Validated PDL mapping.
    @return The body solid and terminal-ID-to-solid mapping.
    @details The largest solid is the body. Remaining solids are matched
    deterministically to nominal terminal anchors without reusing a solid.
    """
    body = max(
        measurement.solids,
        key=lambda solid: math.prod(solid.size_mm),
    )
    available = [solid for solid in measurement.solids if solid is not body]
    terminal_features = sorted(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "TERMINAL_ANCHOR"
            and feature["applicability"] == "REQUIRED"
        ),
        key=lambda feature: feature["terminal_id"],
    )
    matched = {}
    for feature in terminal_features:
        if not available:
            break
        anchor = tuple(float(value) for value in feature["anchor_mm"])
        solid = min(
            available,
            key=lambda candidate: sum(
                (candidate.center_mm[index] - anchor[index]) ** 2
                for index in range(3)
            ),
        )
        matched[feature["terminal_id"]] = solid
        available.remove(solid)
    return body, matched


def _distance_signature(
    point: tuple[float, float, float],
    points: tuple[tuple[float, float, float], ...],
) -> tuple[float, ...]:
    """@brief Build one scale-normalized inter-point distance signature.
    @param point Point whose signature is required.
    @param points Complete point constellation.
    @return Sorted normalized distances to all other points.
    @details Translation, rotation, mirror, and uniform scale do not change
    the signature.
    """
    distances = sorted(
        math.dist(point, candidate)
        for candidate in points
        if candidate != point
    )
    maximum = max(
        (
            math.dist(first, second)
            for first in points
            for second in points
            if first != second
        ),
        default=1.0,
    )
    return tuple(distance / maximum for distance in distances)


def _match_terminals(
    measurement: StepMeasurement, pdl_data: dict, body
) -> tuple[dict[str, object], bool]:
    """@brief Match terminal solids using invariant constellation signatures.
    @param measurement Parsed STEP geometry.
    @param pdl_data Validated package declaration.
    @param body Identified body solid.
    @return Terminal mapping and whether the optimum assignment is unique.
    @details Uses polynomial minimum-cost signature assignment and checks
    alternatives for ambiguity. A measured production index marker permits
    coordinate-frame tie breaking for otherwise symmetric lead arrays.
    """
    features = sorted(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "TERMINAL_ANCHOR"
            and feature["applicability"] == "REQUIRED"
        ),
        key=lambda feature: feature["terminal_id"],
    )
    solids = [solid for solid in measurement.solids if solid is not body]
    if len(solids) != len(features) or len(features) > 256:
        return {}, False
    expected_points = tuple(
        tuple(float(value) for value in feature["anchor_mm"])
        for feature in features
    )
    measured_points = tuple(solid.center_mm for solid in solids)
    if len(features) < 3:
        matched = {}
        available = solids.copy()
        for feature, point in zip(features, expected_points, strict=True):
            solid = min(
                available,
                key=lambda item: math.dist(item.center_mm, point),
            )
            matched[feature["terminal_id"]] = solid
            available.remove(solid)
        return matched, True

    expected_signatures = tuple(
        _distance_signature(point, expected_points)
        for point in expected_points
    )
    measured_signatures = tuple(
        _distance_signature(point, measured_points)
        for point in measured_points
    )
    from scipy.optimize import linear_sum_assignment

    costs = [
        [
            sum(
                abs(left - right)
                for left, right in zip(
                    expected_signatures[index],
                    measured_signatures[solid_index],
                    strict=True,
                )
            )
            for solid_index in range(len(solids))
        ]
        for index in range(len(features))
    ]
    if pdl_data["schema_version"] == "1.1" and pdl_data["model_3d"].get(
        "pin1_marker"
    ):
        # The marker is checked from parsed STEP faces below; malformed or
        # rotated markers remain blocking even when the array is symmetric.
        costs = [
            [
                cost + 1e-4 * math.dist(expected_points[i], measured_points[j])
                for j, cost in enumerate(row)
            ]
            for i, row in enumerate(costs)
        ]
    rows, best = linear_sum_assignment(costs)
    best_cost = sum(costs[i][j] for i, j in zip(rows, best, strict=True))
    unique = True
    for row, col in zip(rows, best, strict=True):
        alternatives = [values.copy() for values in costs]
        alternatives[row][col] = 1e12
        other_rows, other_cols = linear_sum_assignment(alternatives)
        cost = sum(
            alternatives[i][j]
            for i, j in zip(other_rows, other_cols, strict=True)
        )
        if cost - best_cost <= 1e-8:
            unique = False
            break
    return (
        {
            feature["terminal_id"]: solids[solid_index]
            for feature, solid_index in zip(features, best, strict=True)
        },
        unique,
    )


def _observable(pdl_data: dict, *, feature_id: str, kind: str) -> dict | None:
    """@brief Resolve one required observable by feature and kind.
    @param pdl_data Validated package declaration.
    @param feature_id Stable reference-feature ID.
    @param kind Observable kind.
    @return The observable mapping, or None when not declared.
    @details PDL semantic validation guarantees uniqueness of observable IDs.
    """
    return next(
        (
            item
            for item in pdl_data["required_observables"]
            if item["feature_id"] == feature_id and item["kind"] == kind
        ),
        None,
    )


def _tolerance(pdl_data: dict, observable: dict) -> float:
    """@brief Resolve one observable's numeric tolerance.
    @param pdl_data Validated package declaration.
    @param observable Required observable mapping.
    @return Numeric tolerance value.
    @details The PDL validator guarantees the tolerance reference resolves.
    """
    return float(
        pdl_data["validation"]["tolerances"][observable["tolerance_id"]][
            "value"
        ]
    )


def validate_model_3d(
    step_bytes: bytes, ir: ComponentIR | dict, pdl: PDL
) -> tuple[ValidationResult, ...]:
    """@brief Validate STEP scale, height, position, and required solids.
    @param step_bytes STEP artifact bytes.
    @param ir Component IR supplying independent mechanical dimensions.
    @param pdl Trusted package declaration and tolerances.
    @return Strict Phase 7 validation results.
    @details Parse failure returns a blocking parse result. Successful parsing
    produces measured rules for finite coordinates, count, body dimensions,
    independent IR scale, body center, and terminal positions.
    """
    artifact_ids = (sha256(step_bytes).hexdigest(),)
    try:
        measurement = measure_step(step_bytes)
    except (OSError, RuntimeError, ValueError) as error:
        return (
            _result(
                "step-parse",
                False,
                f"STEP parsing failed: {error}",
                artifact_ids,
                measured=False,
                expected=True,
                measurement_mode="NONE",
            ),
        )

    data = _ir_data(ir)
    pdl_data = pdl.data
    tolerances = pdl_data["validation"]["tolerances"]
    body_tolerance = float(tolerances["BODY"]["value"])
    position_tolerance = float(tolerances["POSITION"]["value"])
    body = max(measurement.solids, key=lambda solid: math.prod(solid.size_mm))
    terminals, unique_mapping = _match_terminals(measurement, pdl_data, body)
    terminal_features = [
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "TERMINAL_ANCHOR"
        and feature["applicability"] == "REQUIRED"
    ]
    expected_count = 1 + len(terminal_features)
    results = [
        _result(
            "step-unit-scale",
            measurement.length_unit_mm == 1.0,
            "STEP length unit is millimetres",
            artifact_ids,
            measured=measurement.length_unit_mm,
            expected=1.0,
            tolerance=0.0,
        ),
        _result(
            "step-parse",
            True,
            "STEP artifact parsed successfully",
            artifact_ids,
            measured=True,
            expected=True,
            measurement_mode="NONE",
        ),
        _result(
            "finite-coordinates",
            all(
                math.isfinite(value)
                for solid in measurement.solids
                for value in (*solid.center_mm, *solid.size_mm)
            ),
            "All measured STEP coordinates are finite",
            artifact_ids,
            measured=True,
            expected=True,
            measurement_mode="MEASURED",
        ),
        _result(
            "solid-count",
            measurement.solid_count == expected_count,
            "STEP solid count matches required body and terminals",
            artifact_ids,
            measured=measurement.solid_count,
            expected=expected_count,
            tolerance=0,
        ),
        _result(
            "terminal-mapping",
            unique_mapping,
            "Terminal geometry has one deterministic identity assignment",
            artifact_ids,
            measured=unique_mapping,
            expected=True,
            measurement_mode="MEASURED",
        ),
    ]

    pdl_body = pdl_data["mechanical"]["body"]
    ir_mechanical = data["package"]["mechanical"]
    body_extent = next(
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "BODY_EXTENT"
    )
    dimensions = (
        ("LENGTH", 0, "length", "body_length"),
        ("WIDTH", 1, "width", "body_width"),
        ("HEIGHT", 2, "height", "body_height"),
    )
    for kind, axis, pdl_name, ir_name in dimensions:
        observable = _observable(
            pdl_data, feature_id=body_extent["id"], kind=kind
        )
        if observable is None:
            continue
        tolerance = _tolerance(pdl_data, observable)
        expected = float(pdl_body[pdl_name]["nominal_mm"])
        measured = body.size_mm[axis]
        independent_value, independent_unit = normalize_quantity(
            ir_mechanical[ir_name]["source_value"],
            ir_mechanical[ir_name]["source_unit"],
        )
        if independent_unit != "mm":
            raise ValueError(
                f"Expected a length dimension for {ir_name}, "
                f"received {independent_unit}"
            )
        independent = float(independent_value)
        results.append(
            _result(
                observable["id"],
                abs(measured - expected) <= tolerance
                and abs(measured - independent) <= tolerance,
                f"Measured {pdl_name} matches PDL and independent IR",
                artifact_ids,
                measured=measured,
                expected=f"PDL={expected};IR={independent}",
                tolerance=tolerance,
            )
        )

    body_center = next(
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "BODY_CENTER"
    )
    expected_center = tuple(float(v) for v in body_center["anchor_mm"])
    center_delta = max(
        abs(body.center_mm[index] - expected_center[index])
        for index in range(3)
    )
    results.append(
        _result(
            "step-offset",
            center_delta <= position_tolerance,
            "Measured body center matches its required reference feature",
            artifact_ids,
            measured=center_delta,
            expected=0.0,
            tolerance=position_tolerance,
        )
    )
    expected_points = {
        feature["terminal_id"]: tuple(
            float(value) for value in feature["anchor_mm"]
        )
        for feature in terminal_features
    }
    if len(expected_points) >= 2 and len(terminals) == len(expected_points):
        terminal_ids = sorted(expected_points)
        first_id, second_id = terminal_ids[:2]
        expected_vector = tuple(
            expected_points[second_id][axis] - expected_points[first_id][axis]
            for axis in range(2)
        )
        measured_vector = tuple(
            terminals[second_id].center_mm[axis]
            - terminals[first_id].center_mm[axis]
            for axis in range(2)
        )
        expected_distance = math.hypot(*expected_vector)
        measured_distance = math.hypot(*measured_vector)
        scale = measured_distance / expected_distance
        scale_tolerance = body_tolerance / max(expected_distance, 1e-12)
        results.append(
            _result(
                "step-scale",
                abs(scale - 1.0) <= scale_tolerance,
                "Terminal constellation scale matches the PDL",
                artifact_ids,
                measured=scale,
                expected=1.0,
                tolerance=scale_tolerance,
            )
        )
        angle = math.degrees(
            math.atan2(
                expected_vector[0] * measured_vector[1]
                - expected_vector[1] * measured_vector[0],
                expected_vector[0] * measured_vector[0]
                + expected_vector[1] * measured_vector[1],
            )
        )
        angle = (angle + 180.0) % 360.0 - 180.0
        orientation_observable = _observable(
            pdl_data, feature_id=body_extent["id"], kind="ORIENTATION"
        )
        orientation_tolerance = (
            _tolerance(pdl_data, orientation_observable)
            if orientation_observable is not None
            else float(tolerances["ORIENTATION"]["value"])
        )
        results.append(
            _result(
                "step-orientation",
                abs(angle) <= orientation_tolerance,
                "Terminal constellation orientation matches the PDL",
                artifact_ids,
                measured=angle,
                expected=0.0,
                tolerance=orientation_tolerance,
            )
        )
        if orientation_observable is not None:
            results.append(
                _result(
                    orientation_observable["id"],
                    abs(angle) <= orientation_tolerance,
                    "Measured body orientation matches the PDL",
                    artifact_ids,
                    measured=angle,
                    expected=0.0,
                    tolerance=orientation_tolerance,
                )
            )
    if len(expected_points) >= 3 and len(terminals) == len(expected_points):
        triples = combinations(sorted(expected_points), 3)
        first_id, second_id, third_id = next(
            (
                ids
                for ids in triples
                if abs(
                    (expected_points[ids[1]][0] - expected_points[ids[0]][0])
                    * (expected_points[ids[2]][1] - expected_points[ids[0]][1])
                    - (expected_points[ids[1]][1] - expected_points[ids[0]][1])
                    * (expected_points[ids[2]][0] - expected_points[ids[0]][0])
                )
                > 1e-8
            ),
            tuple(sorted(expected_points)[:3]),
        )

        def _signed_area(points) -> float:
            """@brief Return twice the signed XY area of three points.
            @param points Three points in stable terminal order.
            @return Signed area scalar.
            @details Its sign is invariant under proper transforms and flips
            under X/Y mirror.
            """
            first, second, third = points
            return (second[0] - first[0]) * (third[1] - first[1]) - (
                second[1] - first[1]
            ) * (third[0] - first[0])

        expected_area = _signed_area(
            [
                expected_points[first_id],
                expected_points[second_id],
                expected_points[third_id],
            ]
        )
        measured_area = _signed_area(
            [
                terminals[first_id].center_mm,
                terminals[second_id].center_mm,
                terminals[third_id].center_mm,
            ]
        )
        results.append(
            _result(
                "step-mirror",
                expected_area * measured_area > 0,
                "Terminal constellation chirality matches the PDL",
                artifact_ids,
                measured=measured_area > 0,
                expected=expected_area > 0,
                measurement_mode="MEASURED",
            )
        )
    for feature in terminal_features:
        terminal_id = feature["terminal_id"]
        solid = terminals.get(terminal_id)
        expected_anchor = tuple(float(v) for v in feature["anchor_mm"])
        delta = (
            math.inf
            if solid is None
            else max(
                abs(solid.center_mm[index] - expected_anchor[index])
                for index in range(3)
            )
        )
        observable = _observable(
            pdl_data, feature_id=feature["id"], kind="POSITION"
        )
        if observable is None:
            continue
        observable_tolerance = _tolerance(pdl_data, observable)
        results.append(
            _result(
                observable["id"],
                delta <= observable_tolerance,
                f"Measured terminal {terminal_id} matches its PDL anchor",
                artifact_ids,
                measured=delta,
                expected=0.0,
                tolerance=observable_tolerance,
            )
        )
        dimension_axes = (
            ("LENGTH", 0, "length"),
            ("WIDTH", 1, "width"),
            ("HEIGHT", 2, "height"),
        )
        for kind, axis, dimension_name in dimension_axes:
            dimension_observable = _observable(
                pdl_data, feature_id=feature["id"], kind=kind
            )
            if dimension_observable is None:
                continue
            dimension_tolerance = _tolerance(pdl_data, dimension_observable)
            expected_dimension = float(
                terminal_dimensions(pdl_data, terminal_id)[dimension_name][
                    "nominal_mm"
                ]
            )
            measured_dimension = (
                math.inf if solid is None else solid.size_mm[axis]
            )
            results.append(
                _result(
                    dimension_observable["id"],
                    abs(measured_dimension - expected_dimension)
                    <= dimension_tolerance,
                    f"Measured terminal {terminal_id} {dimension_name} "
                    "matches the PDL",
                    artifact_ids,
                    measured=measured_dimension,
                    expected=expected_dimension,
                    tolerance=dimension_tolerance,
                )
            )

    mounting_plane = next(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "MOUNTING_PLANE"
            and feature["applicability"] == "REQUIRED"
        ),
        None,
    )
    if mounting_plane is not None:
        expected_plane = float(mounting_plane["anchor_mm"][2])
        plane_tolerance = float(tolerances["HEIGHT"]["value"])
        deviations = [
            abs(solid.minimum_mm[2] - expected_plane)
            for solid in terminals.values()
        ]
        maximum_deviation = max(deviations, default=math.inf)
        body_penetration = max(0.0, expected_plane - body.minimum_mm[2])
        results.append(
            _result(
                "mounting-plane",
                maximum_deviation <= plane_tolerance
                and body_penetration <= plane_tolerance,
                "Required solids respect the declared mounting plane",
                artifact_ids,
                measured=max(maximum_deviation, body_penetration),
                expected=0.0,
                tolerance=plane_tolerance,
            )
        )
    marker = pdl_data["model_3d"].get("pin1_marker")
    if marker is not None:
        expected = tuple(map(float, marker["center_mm"]))
        # A recess cylinder's face center lies halfway along its cut depth.
        expected = (*expected[:2], expected[2] + float(marker["depth_mm"]) / 2)
        delta = min(
            (
                math.dist(center, expected)
                for center, radius in body.cylindrical_faces
                if abs(radius - float(marker["radius_mm"])) < 1e-5
            ),
            default=math.inf,
        )
        results.append(
            _result(
                "pin1-index-geometry",
                delta <= position_tolerance,
                "Parsed STEP index recess fixes the package orientation",
                artifact_ids,
                measured=delta,
                expected=0.0,
                tolerance=position_tolerance,
            )
        )
    return tuple(results)


def validate_step_file(
    path: str | Path, ir: ComponentIR | dict, pdl: PDL
) -> tuple[ValidationResult, ...]:
    """@brief Validate a STEP file with an explicit existence result.
    @param path STEP artifact path.
    @param ir Component IR supplying independent dimensions.
    @param pdl Trusted package declaration.
    @return File and model validation results.
    @details Missing paths return only a blocking existence result; existing
    paths are hash-bound and delegated to the bytes validator.
    """
    step_path = Path(path)
    if not step_path.is_file():
        return (
            _result(
                "step-file-exists",
                False,
                "STEP artifact file does not exist",
                (),
                measured=False,
                expected=True,
                measurement_mode="NONE",
            ),
        )
    content = step_path.read_bytes()
    artifact_ids = (sha256(content).hexdigest(),)
    return (
        _result(
            "step-file-exists",
            True,
            "STEP artifact file exists",
            artifact_ids,
            measured=True,
            expected=True,
            measurement_mode="NONE",
        ),
        *validate_model_3d(content, ir, pdl),
    )


_PAD_PATTERN = re.compile(
    rb'\(pad "([^"]+)" smd (\w+) '
    rb"\(at ([-+.\deE]+) ([-+.\deE]+)(?: ([-+.\deE]+))?\) "
    rb"\(size ([-+.\deE]+) ([-+.\deE]+)\)"
)


def _pads(
    footprint_bytes: bytes, *, engineering_y: bool = False
) -> tuple[dict, ...]:
    """@brief Parse supported pads from a generated KiCad footprint.
    @param footprint_bytes KiCad footprint artifact bytes.
    @param engineering_y Converts native downward Y into engineering upward Y.
    @return Parsed pad mappings in artifact order.
    @details Rejects nonzero rotation and unsupported shapes because PDL 1.0
    cannot declare their geometry for cross-validation.
    """
    pads = []
    for number, shape, x, y, rotation, width, height in _PAD_PATTERN.findall(
        footprint_bytes
    ):
        shape_name = shape.decode().upper()
        if shape_name not in {"RECT", "ROUNDRECT", "CIRCLE", "OVAL"}:
            raise ValueError(f"Unsupported footprint pad shape: {shape_name}")
        if rotation and float(rotation) != 0.0:
            raise ValueError("PDL 1.0 cannot validate rotated pads")
        center = (float(x), -float(y) if engineering_y else float(y))
        size = (float(width), float(height))
        pads.append(
            {
                "number": number.decode(),
                "shape": shape_name,
                "center_mm": center,
                "size_mm": size,
                "minimum_mm": (
                    center[0] - size[0] / 2,
                    center[1] - size[1] / 2,
                ),
                "maximum_mm": (
                    center[0] + size[0] / 2,
                    center[1] + size[1] / 2,
                ),
            }
        )
    if footprint_bytes.count(b"(pad ") != len(pads):
        raise ValueError("Footprint contains an unsupported or malformed pad")
    return tuple(pads)


def _overlap(
    first_min: tuple[float, float],
    first_max: tuple[float, float],
    second_min: tuple[float, float],
    second_max: tuple[float, float],
) -> tuple[float, float]:
    """@brief Return nonnegative XY intersection extents.
    @param first_min First rectangle minimum point.
    @param first_max First rectangle maximum point.
    @param second_min Second rectangle minimum point.
    @param second_max Second rectangle maximum point.
    @return X and Y overlap extents.
    @details A separated axis has zero overlap.
    """
    return tuple(
        max(
            0.0,
            min(first_max[axis], second_max[axis])
            - max(first_min[axis], second_min[axis]),
        )
        for axis in range(2)
    )


def _placement(ir_data: dict) -> Placement:
    """@brief Convert the persisted IR placement to the transform type.
    @param ir_data Normalized component IR mapping.
    @return The parsed model-to-footprint placement.
    @details Preserves convention 1.1 translation, rotation, scale, mirrors,
    and named frames.
    """
    value = ir_data["model_3d"]["placement"]
    mirror = value["mirror"]
    return Placement(
        translation_mm=tuple(float(v) for v in value["translation_mm"]),
        rotation_deg=tuple(float(v) for v in value["rotation_deg"]),
        scale=tuple(float(v) for v in value["scale"]),
        mirror=MirrorState(mirror["x"], mirror["y"], mirror["z"]),
        source_frame=value["source_coordinate_system"],
        destination_frame=value["destination_coordinate_system"],
    )


def _determinant(matrix) -> float:
    """@brief Return a transform's 3x3 linear determinant.
    @param matrix A 4x4 affine matrix.
    @return The signed linear determinant.
    @details The sign distinguishes mirrored from proper transforms.
    """
    a, b, c = (row[:3] for row in matrix[:3])
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _column_scales(matrix) -> tuple[float, float, float]:
    """@brief Measure affine scale magnitudes by linear column.
    @param matrix A 4x4 affine matrix.
    @return Positive X, Y, and Z scale magnitudes.
    @details Rotation and mirror do not change these magnitudes.
    """
    return tuple(
        math.sqrt(sum(float(matrix[row][column]) ** 2 for row in range(3)))
        for column in range(3)
    )


def _normalized_linear(matrix):
    """@brief Remove scale magnitudes from an affine linear matrix.
    @param matrix A 4x4 affine matrix.
    @return The normalized 3x3 rotation/mirror rows.
    @details Input matrices are already required to be invertible.
    """
    scales = _column_scales(matrix)
    return tuple(
        tuple(
            float(matrix[row][column]) / scales[column] for column in range(3)
        )
        for row in range(3)
    )


def _matrix_close(left, right, tolerance: float) -> bool:
    """@brief Compare equal-shaped numeric matrices within tolerance.
    @param left First matrix.
    @param right Second matrix.
    @param tolerance Maximum elementwise absolute difference.
    @return True when every corresponding value agrees.
    @details Supports the 3x3 and 4x4 matrices used by placement checks.
    """
    return all(
        abs(float(a) - float(b)) <= tolerance
        for left_row, right_row in zip(left, right, strict=True)
        for a, b in zip(left_row, right_row, strict=True)
    )


def cross_validate_footprint_3d(
    footprint_bytes: bytes,
    step_bytes: bytes,
    ir: ComponentIR | dict,
    pdl: PDL,
) -> tuple[ValidationResult, ...]:
    """@brief Cross-validate independent footprint and STEP artifacts.
    @param footprint_bytes KiCad footprint artifact bytes.
    @param step_bytes STEP artifact bytes.
    @param ir Component IR with exact placement and pin identities.
    @param pdl Trusted package declaration.
    @return Strict Phase 7 cross-artifact validation results.
    @details Checks transformed terminal-to-pad offset relationships, pin-1
    identity, and exposed-pad applicability. No geometry is repaired.
    """
    ir_data = _ir_data(ir)
    pdl_data = pdl.data
    artifact_ids = (
        sha256(footprint_bytes).hexdigest(),
        sha256(step_bytes).hexdigest(),
    )
    try:
        measurement = measure_step(step_bytes)
    except (OSError, RuntimeError, ValueError) as error:
        return (
            _result(
                "cross-step-parse",
                False,
                f"STEP parsing failed: {error}",
                artifact_ids,
                measured=False,
                expected=True,
                measurement_mode="NONE",
                category="cross_artifact",
            ),
        )

    try:
        parsed_pads = _pads(
            footprint_bytes, engineering_y=pdl_data["schema_version"] == "1.1"
        )
    except (UnicodeDecodeError, ValueError) as error:
        return (
            _result(
                "footprint-parse",
                False,
                str(error),
                artifact_ids,
                measured=False,
                expected=True,
                measurement_mode="NONE",
                category="cross_artifact",
            ),
        )
    body = max(measurement.solids, key=lambda solid: math.prod(solid.size_mm))
    measured_terminals, unique_mapping = _match_terminals(
        measurement, pdl_data, body
    )
    transform = to_affine(_placement(ir_data))
    tolerance = float(
        pdl_data["validation"]["tolerances"]["POSITION"]["value"]
    )
    allowed_placements = [
        symmetry["matrix"] for symmetry in pdl_data["allowed_symmetries"]
    ]
    matching_symmetry = next(
        (
            symmetry
            for symmetry in pdl_data["allowed_symmetries"]
            if _matrix_close(transform.matrix, symmetry["matrix"], 1e-9)
        ),
        None,
    )
    placement_allowed = matching_symmetry is not None
    actual_translation = tuple(row[3] for row in transform.matrix[:3])
    translation_allowed = any(
        all(
            abs(actual_translation[index] - float(matrix[index][3])) <= 1e-9
            for index in range(3)
        )
        for matrix in allowed_placements
    )
    actual_scales = _column_scales(transform.matrix)
    scale_allowed = any(
        all(
            abs(actual_scales[index] - _column_scales(matrix)[index]) <= 1e-9
            for index in range(3)
        )
        for matrix in allowed_placements
    )
    mirror_allowed = any(
        (_determinant(transform.matrix) < 0) == (_determinant(matrix) < 0)
        for matrix in allowed_placements
    )
    orientation_allowed = any(
        _matrix_close(
            _normalized_linear(transform.matrix),
            _normalized_linear(matrix),
            1e-9,
        )
        for matrix in allowed_placements
    )
    results = [
        _result(
            "footprint-parse",
            True,
            "Footprint pads parsed successfully",
            artifact_ids,
            measured=True,
            expected=True,
            measurement_mode="NONE",
            category="cross_artifact",
        ),
        _result(
            "declared-placement",
            placement_allowed,
            "Declared placement matches a pinned PDL allowed transform",
            artifact_ids,
            measured=str(transform.matrix),
            expected="one pinned allowed_symmetries matrix",
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        ),
        _result(
            "placement-offset",
            translation_allowed,
            "Placement offset matches a pinned PDL allowed transform",
            artifact_ids,
            measured=str(actual_translation),
            expected="pinned allowed translation",
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        ),
        _result(
            "placement-scale",
            scale_allowed,
            "Placement scale matches a pinned PDL allowed transform",
            artifact_ids,
            measured=str(actual_scales),
            expected="pinned allowed scale",
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        ),
        _result(
            "placement-mirror",
            mirror_allowed,
            "Placement mirror state matches a pinned PDL allowed transform",
            artifact_ids,
            measured=_determinant(transform.matrix) < 0,
            expected="pinned allowed mirror state",
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        ),
        _result(
            "placement-orientation",
            orientation_allowed,
            "Placement orientation matches a pinned PDL allowed transform",
            artifact_ids,
            measured=str(_normalized_linear(transform.matrix)),
            expected="pinned allowed orientation",
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        ),
    ]
    features = {
        feature["terminal_id"]: feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "TERMINAL_ANCHOR"
        and feature["applicability"] == "REQUIRED"
    }
    groups = {
        group["terminal_number"]: group
        for group in pdl_data["land_pattern"]["groups"]
    }
    terminals = {
        terminal["id"]: terminal
        for terminal in pdl_data["topology"]["terminals"]
    }
    expected_pad_count = sum(
        len(group["shapes"]) for group in pdl_data["land_pattern"]["groups"]
    )
    results.extend(
        (
            _result(
                "pad-count",
                len(parsed_pads) == expected_pad_count,
                "Footprint pad-shape count matches the PDL",
                artifact_ids,
                measured=len(parsed_pads),
                expected=expected_pad_count,
                tolerance=0.0,
                category="cross_artifact",
            ),
            _result(
                "cross-terminal-mapping",
                unique_mapping,
                "STEP terminals have a unique geometry assignment",
                artifact_ids,
                measured=unique_mapping,
                expected=True,
                measurement_mode="MEASURED",
                category="cross_artifact",
            ),
        )
    )
    pads_by_number: dict[str, list[dict]] = {}
    for pad in parsed_pads:
        pads_by_number.setdefault(pad["number"], []).append(pad)
    expected_numbers = {
        group["terminal_number"]
        for group in pdl_data["land_pattern"]["groups"]
    }
    results.append(
        _result(
            "physical-pin-count",
            set(pads_by_number) == expected_numbers,
            "Footprint physical terminal inventory matches the PDL",
            artifact_ids,
            measured=",".join(sorted(pads_by_number)),
            expected=",".join(sorted(expected_numbers)),
            measurement_mode="MEASURED",
            category="cross_artifact",
        )
    )
    symmetry_mapping = (
        matching_symmetry["terminal_mapping"]
        if matching_symmetry is not None
        else {terminal_id: terminal_id for terminal_id in terminals}
    )
    maximum_relationship_delta = 0.0
    all_overlap = True
    alignment_deltas = {}
    for terminal_id, _terminal in sorted(terminals.items()):
        destination_id = symmetry_mapping.get(terminal_id, terminal_id)
        destination = terminals[destination_id]
        number = destination["number"]
        feature = features.get(terminal_id)
        solid = measured_terminals.get(terminal_id)
        pads = pads_by_number.get(number, [])
        group = groups.get(number)
        if feature is None or solid is None or not pads or group is None:
            delta = math.inf
            overlap_delta = math.inf
            all_overlap = False
        else:
            nominal_pad = (
                sum(float(shape["center_mm"][0]) for shape in group["shapes"])
                / len(group["shapes"]),
                sum(float(shape["center_mm"][1]) for shape in group["shapes"])
                / len(group["shapes"]),
            )
            nominal_anchor = tuple(float(v) for v in feature["anchor_mm"])
            transformed_anchor = apply_point(transform, nominal_anchor)
            expected_offset = (
                transformed_anchor[0] - nominal_pad[0],
                transformed_anchor[1] - nominal_pad[1],
            )
            transformed = apply_point(transform, solid.center_mm)
            actual_pad_center = (
                sum(pad["center_mm"][0] for pad in pads) / len(pads),
                sum(pad["center_mm"][1] for pad in pads) / len(pads),
            )
            measured_offset = (
                transformed[0] - actual_pad_center[0],
                transformed[1] - actual_pad_center[1],
            )
            delta = max(
                abs(measured_offset[index] - expected_offset[index])
                for index in range(2)
            )
            terminal_size = terminal_dimensions(pdl_data, terminal_id)
            nominal_lead_min = (
                transformed_anchor[0]
                - float(terminal_size["length"]["nominal_mm"]) / 2,
                transformed_anchor[1]
                - float(terminal_size["width"]["nominal_mm"]) / 2,
            )
            nominal_lead_max = (
                transformed_anchor[0]
                + float(terminal_size["length"]["nominal_mm"]) / 2,
                transformed_anchor[1]
                + float(terminal_size["width"]["nominal_mm"]) / 2,
            )
            nominal_pad_min = (
                min(
                    float(shape["center_mm"][0])
                    - float(shape["size_mm"][0]) / 2
                    for shape in group["shapes"]
                ),
                min(
                    float(shape["center_mm"][1])
                    - float(shape["size_mm"][1]) / 2
                    for shape in group["shapes"]
                ),
            )
            nominal_pad_max = (
                max(
                    float(shape["center_mm"][0])
                    + float(shape["size_mm"][0]) / 2
                    for shape in group["shapes"]
                ),
                max(
                    float(shape["center_mm"][1])
                    + float(shape["size_mm"][1]) / 2
                    for shape in group["shapes"]
                ),
            )
            expected_overlap = _overlap(
                nominal_lead_min,
                nominal_lead_max,
                nominal_pad_min,
                nominal_pad_max,
            )
            transformed_bounds = apply_bbox(
                transform, (solid.minimum_mm, solid.maximum_mm)
            )
            actual_pad_min = (
                min(pad["minimum_mm"][0] for pad in pads),
                min(pad["minimum_mm"][1] for pad in pads),
            )
            actual_pad_max = (
                max(pad["maximum_mm"][0] for pad in pads),
                max(pad["maximum_mm"][1] for pad in pads),
            )
            actual_overlap = _overlap(
                transformed_bounds[0][:2],
                transformed_bounds[1][:2],
                actual_pad_min,
                actual_pad_max,
            )
            overlap_delta = max(
                abs(actual_overlap[axis] - expected_overlap[axis])
                for axis in range(2)
            )
            all_overlap = all_overlap and all(
                value > 0 for value in actual_overlap
            )
        maximum_relationship_delta = max(
            maximum_relationship_delta, delta, overlap_delta
        )
        alignment_deltas[terminal_id] = delta
        results.append(
            _result(
                f"footprint-3d-alignment-{terminal_id.lower()}",
                delta <= tolerance,
                f"Terminal {terminal_id} preserves its declared pad offset",
                artifact_ids,
                measured=delta,
                expected=0.0,
                tolerance=tolerance,
                category="cross_artifact",
            )
        )

    pin1_feature = next(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "PIN1_ANCHOR"
        ),
        None,
    )
    pin1_terminal = (
        terminals.get(pin1_feature["terminal_id"])
        if pin1_feature is not None
        else None
    )
    ir_pin1 = next(
        (pin for pin in ir_data["pins"] if pin["number"] == "1"), None
    )
    pin1_passed = (
        pin1_terminal is not None
        and ir_pin1 is not None
        and pin1_terminal["number"] == ir_pin1["number"]
        and pin1_terminal["side"] == ir_pin1["physical"]["topology_side"]
        and pin1_terminal["topology_index"]
        == ir_pin1["physical"]["topology_index"]
        and alignment_deltas.get(pin1_feature["terminal_id"], math.inf)
        <= tolerance
    )
    pin1_observable = (
        _observable(
            pdl_data,
            feature_id=pin1_feature["id"],
            kind="ORIENTATION",
        )
        if pin1_feature is not None
        else None
    )
    results.append(
        _result(
            pin1_observable["id"]
            if pin1_observable is not None
            else "pin1-mapping",
            pin1_passed,
            "Pin 1 identity and topology agree across IR and PDL",
            artifact_ids,
            measured=pin1_feature["terminal_id"] if pin1_feature else None,
            expected=pin1_feature["terminal_id"] if pin1_feature else None,
            measurement_mode="DECLARED_ONLY",
            category="cross_artifact",
        )
    )
    clearance_feature = next(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "LAND_PATTERN_EXTENT"
        ),
        None,
    )
    clearance_observable = (
        _observable(
            pdl_data,
            feature_id=clearance_feature["id"],
            kind="CLEARANCE",
        )
        if clearance_feature is not None
        else None
    )
    if clearance_observable is not None:
        clearance_tolerance = _tolerance(pdl_data, clearance_observable)
        results.append(
            _result(
                clearance_observable["id"],
                all_overlap
                and maximum_relationship_delta <= clearance_tolerance,
                "Measured lead/pad overlap and clearance match the PDL",
                artifact_ids,
                measured=maximum_relationship_delta,
                expected=0.0,
                tolerance=clearance_tolerance,
                category="cross_artifact",
            )
        )
    absent_exposed = next(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "TERMINAL_ANCHOR"
            and feature["applicability"] == "ABSENT"
        ),
        None,
    )
    if absent_exposed is not None:
        results.append(
            _not_applicable(
                "exposed-pad-applicability",
                absent_exposed["id"],
                pdl,
            )
        )
    return tuple(results)
