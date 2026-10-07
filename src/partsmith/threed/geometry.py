"""

@package src.partsmith.threed.geometry
@brief Section 145 body/lead solid construction from PDL mechanical
data and reference features.
@details Provides the module implementation and public interfaces.
"""

import cadquery as cq

from partsmith.threed.package_geometry import (
    apply_index_marker,
    build_terminal,
)

_SUPPORTED_BODY_STRATEGIES = {"CHIP_BODY", "MOLDED_BODY"}
_SUPPORTED_LEAD_STRATEGIES = {"END_TERMINATIONS", "GULL_WING", "NO_LEAD"}
_SUPPORTED_MARKER_STRATEGIES = {"NONE", "PIN1_RECESS"}


def _reference_feature(pdl_data: dict, kind: str) -> dict:
    """

    @brief Return the single required reference feature of a kind.
    @param pdl_data The pdl_data argument.
    @param kind The kind argument.
    @return The dict result.
    @details Raises ValueError when zero or more than one feature of
    `kind` is declared.

    """
    matches = [
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == kind
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {kind} reference feature, found "
            f"{len(matches)}"
        )
    return matches[0]


def _terminal_features(pdl_data: dict) -> list[dict]:
    """

    @brief Return TERMINAL_ANCHOR reference features in terminal-ID
    order.
    @param pdl_data The pdl_data argument.
    @return The list[dict] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    features = [
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "TERMINAL_ANCHOR"
        and feature["applicability"] == "REQUIRED"
    ]
    if not features:
        raise ValueError("At least one TERMINAL_ANCHOR feature is required")
    return sorted(features, key=lambda feature: feature["terminal_id"])


def _box_at(
    dimensions: tuple[float, float, float], center: tuple[float, float, float]
):
    """

    @brief Build an axis-aligned box centered at a model-frame point.
    @param dimensions The (length, width, height) box size in mm.
    @param center The (x, y, z) model-frame center point in mm.
    @return The cadquery solid result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    length, width, height = dimensions
    return (
        cq.Workplane("XY").box(length, width, height).translate(center).val()
    )


def build_solids(pdl_data: dict) -> list:
    """

    @brief Builds body and independently identified terminal solids.
    @param pdl_data The pdl_data argument.
    @return The list result.
    @details Returns `[body_solid, *terminal_solids]` in terminal-ID
    order; validates supported chip, molded, gull-wing and no-lead strategies.

    """
    model_3d = pdl_data["model_3d"]
    if model_3d["body_strategy"] not in _SUPPORTED_BODY_STRATEGIES:
        raise ValueError(
            f"Unsupported body_strategy: {model_3d['body_strategy']}"
        )
    if model_3d["lead_strategy"] not in _SUPPORTED_LEAD_STRATEGIES:
        raise ValueError(
            f"Unsupported lead_strategy: {model_3d['lead_strategy']}"
        )
    if model_3d["marker_strategy"] not in _SUPPORTED_MARKER_STRATEGIES:
        raise ValueError(
            f"Unsupported marker_strategy: {model_3d['marker_strategy']}"
        )

    mechanical = pdl_data["mechanical"]
    body = mechanical["body"]
    body_center = tuple(
        float(value)
        for value in _reference_feature(pdl_data, "BODY_CENTER")["anchor_mm"]
    )
    body_solid = _box_at(
        (
            float(body["length"]["nominal_mm"]),
            float(body["width"]["nominal_mm"]),
            float(body["height"]["nominal_mm"]),
        ),
        body_center,
    )

    body_solid = apply_index_marker(body_solid, pdl_data)
    terminal_solids = [
        build_terminal(pdl_data, feature)
        for feature in _terminal_features(pdl_data)
    ]
    return [body_solid, *terminal_solids]
