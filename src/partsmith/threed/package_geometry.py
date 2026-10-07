"""@package partsmith.threed.package_geometry
@brief Constructs versioned molded, gull-wing and no-lead package geometry.
@details PDL 1.1 freezes terminal dimensions, lead profiles and index markers.
No electrical behavior or undocumented JEDEC dimensions are inferred here.
"""

import cadquery as cq


def terminal_dimensions(pdl_data: dict, terminal_id: str) -> dict:
    """@brief Resolves one terminal's explicit axis-aligned dimensions.
    @param pdl_data Validated PDL data.
    @param terminal_id Stable physical terminal identity.
    @return Length, width and height quantity mappings.
    @details PDL 1.0 entries preserve their uniform terminal contract.
    """
    for item in pdl_data["mechanical"].get("terminals", []):
        if item["terminal_id"] == terminal_id:
            return {key: item[key] for key in ("length", "width", "height")}
    return pdl_data["mechanical"]["terminal"]


def build_terminal(pdl_data: dict, feature: dict):
    """@brief Builds a terminal using its frozen profile or rectangular solid.
    @param pdl_data Validated PDL data.
    @param feature Required TERMINAL_ANCHOR in the model coordinate system.
    @return One CadQuery solid.
    @details Gull-wing profiles are continuous extrusions with the specified
    cardinal rotation. Exposed pads retain their own dimensions and identity.
    """
    profiles = pdl_data["model_3d"].get("lead_profiles", [])
    profile = next(
        (p for p in profiles if p["terminal_id"] == feature["terminal_id"]),
        None,
    )
    if profile is not None:
        shape = (
            cq.Workplane("XZ")
            .polyline([tuple(map(float, p)) for p in profile["points_mm"]])
            .close()
            .extrude(float(profile["width_mm"]) / 2, both=True)
            .val()
        )
        shape = shape.rotate(
            (0, 0, 0), (0, 0, 1), float(profile["rotation_deg"])
        )
    else:
        dimensions = terminal_dimensions(pdl_data, feature["terminal_id"])
        shape = (
            cq.Workplane("XY")
            .box(
                *(
                    float(dimensions[key]["nominal_mm"])
                    for key in ("length", "width", "height")
                )
            )
            .val()
        )
    return shape.translate(tuple(map(float, feature["anchor_mm"])))


def apply_index_marker(body, pdl_data: dict):
    """@brief Cuts the frozen pin-one index recess into a molded body.
    @param body CadQuery molded body solid.
    @param pdl_data Validated PDL including marker dimensions and source basis.
    @return Molded body with its physically measurable orientation marker.
    @details Does not add an electrically counted solid. Marker dimensions
    are rendering choices when a drawing specifies an index area only.
    """
    marker = pdl_data["model_3d"].get("pin1_marker")
    if marker is None:
        return body
    center = tuple(map(float, marker["center_mm"]))
    cutter = (
        cq.Workplane("XY")
        .circle(float(marker["radius_mm"]))
        .extrude(float(marker["depth_mm"]) + 0.01)
        .translate(center)
        .val()
    )
    return body.cut(cutter)
