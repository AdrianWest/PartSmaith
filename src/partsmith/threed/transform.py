"""

@package src.partsmith.threed.transform
@brief Section 92/150 placement and affine-transform contract.
@details Implements the convention-1.1 engineering frame (right-handed,
mm/degrees, column vectors) as a simple Placement record and a full
convention `affine-1.0` AffineTransform, with conversion, composition,
inversion, point/vector/bbox application, and simple-placement
recovery with explicit rejection of nonrepresentable (e.g. sheared)
matrices.
"""

import math
from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Row4 = tuple[float, float, float, float]
Matrix4x4 = tuple[Row4, Row4, Row4, Row4]

_IDENTITY: Matrix4x4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)

_MIRROR_COMBINATIONS: tuple[tuple[bool, bool, bool], ...] = tuple(
    (bool(i & 1), bool(i & 2), bool(i & 4)) for i in range(8)
)


class UnsupportedTransformError(ValueError):
    """@brief Raised when an affine transform cannot be serialized.
    @details Raised for singular linear parts, mismatched frame IDs at
    a composition boundary, and matrices (for example genuine shear)
    that cannot round-trip through a simple Placement within the
    caller's tolerance.
    """


@dataclass(frozen=True)
class MirrorState:
    """@brief Per-axis mirror flags applied before rotation.
    @details Each True flag negates the corresponding source axis
    about the source origin, before scale and rotation.
    """

    x: bool = False
    y: bool = False
    z: bool = False


@dataclass(frozen=True)
class Placement:
    """@brief Convention-1.1 simple placement record.
    @details translation_mm is destination-frame mm. rotation_deg is
    (rx, ry, rz), applied X then Y then Z as active, right-hand
    positive, extrinsic rotations about fixed source axes. scale and
    mirror act about the source origin before rotation. Matches
    section 92: `p_dest = T * Rz(rz) * Ry(ry) * Rx(rx) * S * M *
    p_src`.
    """

    translation_mm: Vec3
    rotation_deg: Vec3
    scale: Vec3
    mirror: MirrorState
    source_frame: str
    destination_frame: str


@dataclass(frozen=True)
class AffineTransform:
    """@brief Section 150 full affine map between two named frames.
    @details matrix uses column vectors, mm translations, finite
    entries, and a last row of exactly (0.0, 0.0, 0.0, 1.0); its
    convention is `affine-1.0` and it does not replace the persisted
    simple IR placement record.
    """

    matrix: Matrix4x4
    source_frame: str
    destination_frame: str


def _matmul(a: Matrix4x4, b: Matrix4x4) -> Matrix4x4:
    """

    @brief Multiply two 4x4 matrices using column-vector convention.
    @param a The left matrix.
    @param b The right matrix.
    @return The Matrix4x4 result.
    @details Computes `a @ b`; row i, column j is the dot product of
    row i of `a` and column j of `b`.

    """
    return tuple(
        tuple(sum(a[row][k] * b[k][col] for k in range(4)) for col in range(4))
        for row in range(4)
    )


def _rotation_x(degrees: float) -> Matrix4x4:
    """

    @brief Build an active right-hand rotation about the X axis.
    @param degrees The rotation angle in degrees.
    @return The Matrix4x4 result.
    @details Section 92 rotation convention; degrees, not radians.

    """
    radians = math.radians(degrees)
    c, s = math.cos(radians), math.sin(radians)
    return (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, c, -s, 0.0),
        (0.0, s, c, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotation_y(degrees: float) -> Matrix4x4:
    """

    @brief Build an active right-hand rotation about the Y axis.
    @param degrees The rotation angle in degrees.
    @return The Matrix4x4 result.
    @details Section 92 rotation convention; degrees, not radians.

    """
    radians = math.radians(degrees)
    c, s = math.cos(radians), math.sin(radians)
    return (
        (c, 0.0, s, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (-s, 0.0, c, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _rotation_z(degrees: float) -> Matrix4x4:
    """

    @brief Build an active right-hand rotation about the Z axis.
    @param degrees The rotation angle in degrees.
    @return The Matrix4x4 result.
    @details Section 92 rotation convention; degrees, not radians.

    """
    radians = math.radians(degrees)
    c, s = math.cos(radians), math.sin(radians)
    return (
        (c, -s, 0.0, 0.0),
        (s, c, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _translation_matrix(translation_mm: Vec3) -> Matrix4x4:
    """

    @brief Build a translation matrix in destination-frame mm.
    @param translation_mm The translation_mm argument.
    @return The Matrix4x4 result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    x, y, z = translation_mm
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


def _scale_mirror_matrix(scale: Vec3, mirror: MirrorState) -> Matrix4x4:
    """

    @brief Build the combined `S * M` diagonal matrix.
    @param scale The scale argument.
    @param mirror The mirror argument.
    @return The Matrix4x4 result.
    @details Raises UnsupportedTransformError when any scale factor is
    not strictly positive; mirror flags negate their axis.

    """
    values = []
    for factor, flag in zip(
        scale, (mirror.x, mirror.y, mirror.z), strict=True
    ):
        if not factor > 0:
            raise UnsupportedTransformError(
                "Scale factors must be strictly positive"
            )
        values.append(-factor if flag else factor)
    sx, sy, sz = values
    return (
        (sx, 0.0, 0.0, 0.0),
        (0.0, sy, 0.0, 0.0),
        (0.0, 0.0, sz, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def to_affine(placement: Placement) -> AffineTransform:
    """

    @brief Convert a simple Placement into its full AffineTransform.
    @param placement The placement argument.
    @return The AffineTransform result.
    @details Computes `T * Rz(rz) * Ry(ry) * Rx(rx) * S * M` per
    section 92; raises UnsupportedTransformError for non-positive
    scale factors.

    """
    rx, ry, rz = placement.rotation_deg
    matrix = _matmul(
        _translation_matrix(placement.translation_mm),
        _matmul(
            _rotation_z(rz),
            _matmul(
                _rotation_y(ry),
                _matmul(
                    _rotation_x(rx),
                    _scale_mirror_matrix(placement.scale, placement.mirror),
                ),
            ),
        ),
    )
    return AffineTransform(
        matrix, placement.source_frame, placement.destination_frame
    )


def compose(ab: AffineTransform, bc: AffineTransform) -> AffineTransform:
    """

    @brief Compose A->B and B->C transforms into a single A->C map.
    @param ab The source-to-intermediate transform.
    @param bc The intermediate-to-destination transform.
    @return The AffineTransform result.
    @details Returns `bc.matrix * ab.matrix`; raises
    UnsupportedTransformError when `ab.destination_frame` does not
    equal `bc.source_frame`.

    """
    if ab.destination_frame != bc.source_frame:
        raise UnsupportedTransformError(
            f"Frame mismatch: {ab.destination_frame!r} != {bc.source_frame!r}"
        )
    return AffineTransform(
        _matmul(bc.matrix, ab.matrix), ab.source_frame, bc.destination_frame
    )


def _invert4x4(matrix: Matrix4x4) -> Matrix4x4:
    """

    @brief Invert a 4x4 matrix with an affine last row.
    @param matrix The matrix argument.
    @return The Matrix4x4 result.
    @details Uses Gauss-Jordan elimination with partial pivoting;
    raises UnsupportedTransformError when the linear part is singular
    or numerically unstable.

    """
    augmented = [list(matrix[row]) + list(_IDENTITY[row]) for row in range(4)]
    for column in range(4):
        pivot_row = max(
            range(column, 4), key=lambda row: abs(augmented[row][column])
        )
        pivot = augmented[pivot_row][column]
        if abs(pivot) < 1e-12:
            raise UnsupportedTransformError(
                "Affine transform has a singular linear part"
            )
        augmented[column], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[column],
        )
        augmented[column] = [value / pivot for value in augmented[column]]
        for row in range(4):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(
                    augmented[row], augmented[column], strict=True
                )
            ]
    return tuple(tuple(row[4:]) for row in augmented)


def invert(transform: AffineTransform) -> AffineTransform:
    """

    @brief Invert an AffineTransform and swap its frame IDs.
    @param transform The transform argument.
    @return The AffineTransform result.
    @details Raises UnsupportedTransformError for a singular or
    numerically unstable linear part.

    """
    return AffineTransform(
        _invert4x4(transform.matrix),
        transform.destination_frame,
        transform.source_frame,
    )


def apply_point(transform: AffineTransform, point: Vec3) -> Vec3:
    """

    @brief Map a destination-frame point (homogeneous w=1).
    @param transform The transform argument.
    @param point The point argument.
    @return The Vec3 result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    x, y, z = point
    m = transform.matrix
    return tuple(
        m[row][0] * x + m[row][1] * y + m[row][2] * z + m[row][3]
        for row in range(3)
    )


def apply_vector(transform: AffineTransform, vector: Vec3) -> Vec3:
    """

    @brief Map a direction vector (homogeneous w=0), ignoring
    translation.
    @param transform The transform argument.
    @param vector The vector argument.
    @return The Vec3 result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    x, y, z = vector
    m = transform.matrix
    return tuple(
        m[row][0] * x + m[row][1] * y + m[row][2] * z for row in range(3)
    )


def apply_bbox(
    transform: AffineTransform, bbox: tuple[Vec3, Vec3]
) -> tuple[Vec3, Vec3]:
    """

    @brief Map an axis-aligned bounding box through an affine
    transform.
    @param transform The transform argument.
    @param bbox The (minimum, maximum) corner pair.
    @return The (minimum, maximum) destination-axis-aligned result.
    @details Transforms all eight corners with `apply_point` and
    returns their destination-axis-aligned bounds.

    """
    (min_x, min_y, min_z), (max_x, max_y, max_z) = bbox
    corners = (
        apply_point(transform, (x, y, z))
        for x in (min_x, max_x)
        for y in (min_y, max_y)
        for z in (min_z, max_z)
    )
    xs, ys, zs = zip(*corners, strict=True)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def equivalent_within_tolerance(
    a: AffineTransform, b: AffineTransform, tolerance: float
) -> bool:
    """

    @brief Compare two affine transforms elementwise within tolerance.
    @param a The a argument.
    @param b The b argument.
    @param tolerance The maximum allowed per-element absolute
    difference.
    @return The bool result.
    @details Returns False when frame IDs differ, regardless of
    matrix values.

    """
    if (a.source_frame, a.destination_frame) != (
        b.source_frame,
        b.destination_frame,
    ):
        return False
    return all(
        abs(a.matrix[row][col] - b.matrix[row][col]) <= tolerance
        for row in range(4)
        for col in range(4)
    )


def _extract_rotation_deg(rotation: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    """

    @brief Recover (rx, ry, rz) degrees from an `Rz*Ry*Rx` rotation
    matrix.
    @param rotation The 3x3 rotation matrix as a tuple of rows.
    @return The Vec3 result.
    @details Valid away from gimbal lock (`cos(ry) == 0`); matches the
    section 92 `Rz(rz) * Ry(ry) * Rx(rx)` composition order.

    """
    r20 = max(-1.0, min(1.0, -rotation[2][0]))
    ry = math.asin(r20)
    rx = math.atan2(rotation[2][1], rotation[2][2])
    rz = math.atan2(rotation[1][0], rotation[0][0])
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def simple_placement_from_affine(
    transform: AffineTransform, tolerance: float
) -> Placement:
    """

    @brief Recover a simple Placement from an AffineTransform, if
    possible.
    @param transform The transform argument.
    @param tolerance The maximum allowed per-element reconstruction
    error.
    @return The Placement result.
    @details Tries each of the eight per-axis mirror combinations,
    extracting scale and rotation for each; returns the first
    candidate whose reconstructed matrix agrees with `transform`
    within `tolerance`. Raises UnsupportedTransformError (never
    silently drops shear) when no candidate matches, or when the
    linear part is singular.

    """
    linear = tuple(tuple(row[:3]) for row in transform.matrix[:3])
    translation = (
        transform.matrix[0][3],
        transform.matrix[1][3],
        transform.matrix[2][3],
    )
    for mx, my, mz in _MIRROR_COMBINATIONS:
        mirror_signs = (
            -1.0 if mx else 1.0,
            -1.0 if my else 1.0,
            -1.0 if mz else 1.0,
        )
        unmirrored = tuple(
            tuple(linear[row][col] * mirror_signs[col] for col in range(3))
            for row in range(3)
        )
        scale = tuple(
            math.sqrt(sum(unmirrored[row][col] ** 2 for row in range(3)))
            for col in range(3)
        )
        if any(factor < 1e-12 for factor in scale):
            continue
        rotation = tuple(
            tuple(unmirrored[row][col] / scale[col] for col in range(3))
            for row in range(3)
        )
        rotation_deg = _extract_rotation_deg(rotation)
        candidate = Placement(
            translation_mm=translation,
            rotation_deg=rotation_deg,
            scale=scale,
            mirror=MirrorState(mx, my, mz),
            source_frame=transform.source_frame,
            destination_frame=transform.destination_frame,
        )
        try:
            reconstructed = to_affine(candidate)
        except UnsupportedTransformError:
            continue
        if equivalent_within_tolerance(reconstructed, transform, tolerance):
            return candidate
    raise UnsupportedTransformError(
        "Affine transform has no representable simple Placement "
        "(for example, genuine shear) within the given tolerance"
    )
