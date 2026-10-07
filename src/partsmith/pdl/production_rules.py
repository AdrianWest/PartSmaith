"""@package partsmith.pdl.production_rules
@brief Validates versioned production terminal geometry and model choices.
@details Extends PDL 1.1 without changing historical PDL 1.0 byte contracts.
"""

from partsmith.ir.errors import Issue


def production_issues(data: dict) -> list[Issue]:
    """@brief Checks explicit per-terminal dimensions and lead bindings.
    @param data Schema-valid PDL 1.1 document.
    @return Blocking semantic issues sorted by the normal PDL validator.
    @details Dimensions require resolved sources and ordered ranges; all
    exposed pads and peripheral leads have distinct immutable geometry.
    """
    if data["schema_version"] != "1.1":
        return []
    issues = []
    terminals = data["topology"]["terminals"]
    expected = {item["id"] for item in terminals}
    dimensions = data["mechanical"]["terminals"]
    actual = [item["terminal_id"] for item in dimensions]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        issues.append(
            Issue(
                "/mechanical/terminals",
                "PDL_TOPOLOGY",
                "Geometry must cover every terminal exactly once",
            )
        )
    sources = {item["id"] for item in data["sources"]}
    for index, terminal in enumerate(dimensions):
        for name in ("length", "width", "height"):
            value = terminal[name]
            if not (
                value["minimum_mm"]
                <= value["nominal_mm"]
                <= value["maximum_mm"]
            ):
                issues.append(
                    Issue(
                        f"/mechanical/terminals/{index}/{name}",
                        "PDL_DIMENSION",
                        "Invalid dimension range",
                    )
                )
            if not set(value["source_ids"]) <= sources:
                issues.append(
                    Issue(
                        f"/mechanical/terminals/{index}/{name}",
                        "PDL_REFERENCE",
                        "Unresolved geometry source",
                    )
                )
    model = data["model_3d"]
    profiles = model.get("lead_profiles", [])
    profile_ids = [p["terminal_id"] for p in profiles]
    peripheral = {t["id"] for t in terminals if t["kind"] == "PERIPHERAL"}
    if (
        len(profile_ids) != len(set(profile_ids))
        or not set(profile_ids) <= peripheral
    ):
        issues.append(
            Issue(
                "/model_3d/lead_profiles",
                "PDL_TOPOLOGY",
                "Profiles must bind distinct peripheral terminals",
            )
        )
    for index, profile in enumerate(profiles):
        points = profile["points_mm"]
        area = sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in zip(
                points, points[1:] + points[:1], strict=True
            )
        )
        if not area or len({tuple(p) for p in points}) != len(points):
            issues.append(
                Issue(
                    f"/model_3d/lead_profiles/{index}",
                    "PDL_DIMENSION",
                    "Lead profile requires area and distinct vertices",
                )
            )
    if model["lead_strategy"] == "GULL_WING" and (
        len(profile_ids) != len(set(profile_ids))
        or set(profile_ids) != peripheral
    ):
        issues.append(
            Issue(
                "/model_3d/lead_profiles",
                "PDL_TOPOLOGY",
                "Gull-wing profiles must cover peripheral leads",
            )
        )
    if model["marker_strategy"] == "PIN1_RECESS" and not model.get(
        "pin1_marker"
    ):
        issues.append(
            Issue(
                "/model_3d/pin1_marker",
                "PDL_REFERENCE",
                "Index recess requires frozen marker geometry",
            )
        )
    marker = model.get("pin1_marker")
    if marker:
        body = data["mechanical"]["body"]
        x, y, z = marker["center_mm"]
        radius, depth = marker["radius_mm"], marker["depth_mm"]
        body_anchor = next(
            f["anchor_mm"]
            for f in data["reference_features"]
            if f["kind"] == "BODY_CENTER"
        )
        height = body["height"]["nominal_mm"]
        top = body_anchor[2] + height / 2
        if (
            abs(x - body_anchor[0]) + radius
            >= body["length"]["nominal_mm"] / 2
            or abs(y - body_anchor[1]) + radius
            >= body["width"]["nominal_mm"] / 2
            or not 0 < depth < height
            or abs(z + depth - top) > 0.000001
        ):
            issues.append(
                Issue(
                    "/model_3d/pin1_marker",
                    "PDL_DIMENSION",
                    "Index recess must terminate at and stay inside the body",
                )
            )
    return issues
