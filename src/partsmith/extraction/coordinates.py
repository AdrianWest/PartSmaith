"""@package partsmith.extraction.coordinates
@brief Maps document source regions through retained affine transforms.
@details Accepts original floating coordinates and exact session Decimals.
"""

import math
from decimal import Decimal


def transform_point(matrix, x, y):
    """@brief Transform point.
    @param matrix Matrix input.
    @param x X input.
    @param y Y input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    return (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2],
    )


def inverse(matrix):
    """@brief Inverse.
    @param matrix Matrix input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    if matrix[2] != [0, 0, 1] or not all(
        math.isfinite(v) for row in matrix for v in row
    ):
        raise ValueError("An affine finite mapping is required.")
    det = a * e - b * d
    if abs(det) < 1e-15:
        raise ValueError("Singular document coordinate mapping.")
    return [
        [e / det, -b / det, (b * f - e * c) / det],
        [-d / det, a / det, (d * c - a * f) / det],
        [0, 0, 1],
    ]


def bounds(matrix, box):
    """@brief Bounds.
    @param matrix Matrix input.
    @param box Box input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Source regions require positive area.")
    points = [
        transform_point(matrix, x, y)
        for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
    ]
    xs, ys = zip(*points, strict=True)
    return {
        "x": min(xs),
        "y": min(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def region_box(region):
    """@brief Region box.
    @param region Region input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    return (
        region["x"],
        region["y"],
        region["x"] + region["width"],
        region["y"] + region["height"],
    )


def validate_region(region, geometry):
    """@brief Validate region.
    @param region Region input.
    @param geometry Geometry input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    box = region_box(region)
    media = geometry["media_box"]
    width = (media[2] - media[0]) * geometry["user_unit"]
    height = (media[3] - media[1]) * geometry["user_unit"]
    epsilon = Decimal("0.0000001") if isinstance(width, Decimal) else 1e-7
    if (
        not all(math.isfinite(v) for v in box)
        or region["width"] <= 0
        or region["height"] <= 0
        or box[0] < -epsilon
        or box[1] < -epsilon
        or box[2] > width + epsilon
        or box[3] > height + epsilon
    ):
        raise ValueError("Source region lies outside the original MediaBox.")


def overlay_box(source):
    """@brief Recover the recorded region in the retained rendered image.
    @param source Source input.
    @return Result of this operation.
    @details Retains the documented processing and redaction contract.
    """
    render = source["render_transform"]
    if render is None:
        raise ValueError("This evidence has no rendered image.")
    return bounds(
        inverse(render["pixel_to_page"]), region_box(source["region"])
    )
