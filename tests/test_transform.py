"""

@package tests.test_transform
@brief Phase 6 section 92/150 coordinate-transform-library gate tests.
@details Provides the module implementation and public interfaces.
"""

import math

import pytest

from partsmith.threed.transform import (
    MirrorState,
    Placement,
    UnsupportedTransformError,
    apply_bbox,
    apply_point,
    apply_vector,
    compose,
    equivalent_within_tolerance,
    invert,
    simple_placement_from_affine,
    to_affine,
)

TOLERANCE = 1e-9


def _placement(
    translation=(0.0, 0.0, 0.0),
    rotation=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
    mirror=None,
    source="A",
    destination="B",
):
    """

    @brief Build a Placement fixture with convenient defaults.
    @param translation The translation argument.
    @param rotation The rotation argument.
    @param scale The scale argument.
    @param mirror The mirror argument.
    @param source The source argument.
    @param destination The destination argument.
    @return The Placement result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return Placement(
        translation,
        rotation,
        scale,
        mirror if mirror is not None else MirrorState(),
        source,
        destination,
    )


def test_identity_placement_is_identity_matrix():
    """

    @brief Implements the test_identity_placement_is_identity_matrix
    operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    affine = to_affine(_placement())
    for row in range(4):
        for col in range(4):
            assert affine.matrix[row][col] == pytest.approx(
                1.0 if row == col else 0.0
            )


def test_translation_maps_origin_to_translation():
    """

    @brief Implements the test_translation_maps_origin_to_translation
    operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    affine = to_affine(_placement(translation=(1.0, 2.0, 3.0)))
    assert apply_point(affine, (0.0, 0.0, 0.0)) == pytest.approx(
        (1.0, 2.0, 3.0)
    )


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        ((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
    ],
)
def test_rz_90_maps_basis_vectors(basis, expected):
    """

    @brief Implements the test_rz_90_maps_basis_vectors operation.
    @param basis The basis argument.
    @param expected The expected argument.
    @return The callable result.
    @details Rz(90) maps (1,0,0) to (0,1,0) per section 92's example.

    """
    affine = to_affine(_placement(rotation=(0.0, 0.0, 90.0)))
    assert apply_vector(affine, basis) == pytest.approx(expected, abs=1e-9)


def test_mirror_axis_negates_source_axis():
    """

    @brief Implements the test_mirror_axis_negates_source_axis
    operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    affine = to_affine(_placement(mirror=MirrorState(x=True)))
    assert apply_vector(affine, (1.0, 1.0, 1.0)) == pytest.approx(
        (-1.0, 1.0, 1.0)
    )


def test_combined_noncommuting_rotations():
    """

    @brief Implements the test_combined_noncommuting_rotations
    operation.
    @return The callable result.
    @details Rx(90) then Ry(90) (in that composition order) maps a
    basis vector differently than Ry(90) then Rx(90), proving
    rotations do not commute.

    """
    rx90 = to_affine(
        _placement(rotation=(90.0, 0.0, 0.0), source="A", destination="B")
    )
    ry90 = to_affine(
        _placement(rotation=(0.0, 90.0, 0.0), source="B", destination="C")
    )
    ry90_first = to_affine(
        _placement(rotation=(0.0, 90.0, 0.0), source="A", destination="B")
    )
    rx90_second = to_affine(
        _placement(rotation=(90.0, 0.0, 0.0), source="B", destination="C")
    )
    x_then_y = compose(rx90, ry90)
    y_then_x = compose(ry90_first, rx90_second)
    point = (1.0, 0.0, 0.0)
    assert apply_point(x_then_y, point) != pytest.approx(
        apply_point(y_then_x, point), abs=1e-9
    )


def test_composition_is_bc_matrix_times_ab_matrix():
    """

    @brief Implements the
    test_composition_is_bc_matrix_times_ab_matrix operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    ab = to_affine(
        _placement(translation=(1.0, 0.0, 0.0), source="A", destination="B")
    )
    bc = to_affine(
        _placement(translation=(0.0, 1.0, 0.0), source="B", destination="C")
    )
    composed = compose(ab, bc)
    assert composed.source_frame == "A"
    assert composed.destination_frame == "C"
    assert apply_point(composed, (0.0, 0.0, 0.0)) == pytest.approx(
        (1.0, 1.0, 0.0)
    )


def test_composition_rejects_frame_mismatch():
    """

    @brief Implements the test_composition_rejects_frame_mismatch
    operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    ab = to_affine(_placement(source="A", destination="B"))
    bc = to_affine(_placement(source="X", destination="C"))
    with pytest.raises(UnsupportedTransformError):
        compose(ab, bc)


def test_inverse_round_trip():
    """

    @brief Implements the test_inverse_round_trip operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    affine = to_affine(
        _placement(
            translation=(1.0, 2.0, 3.0),
            rotation=(10.0, 20.0, 30.0),
            scale=(2.0, 3.0, 4.0),
        )
    )
    inverse = invert(affine)
    assert inverse.source_frame == affine.destination_frame
    assert inverse.destination_frame == affine.source_frame
    round_trip = compose(affine, inverse)
    for row in range(4):
        for col in range(4):
            assert round_trip.matrix[row][col] == pytest.approx(
                1.0 if row == col else 0.0, abs=1e-9
            )


def test_invert_rejects_singular_matrix():
    """

    @brief Implements the test_invert_rejects_singular_matrix
    operation.
    @return The callable result.
    @details A zero scale factor is rejected before it can produce a
    singular matrix.

    """
    with pytest.raises(UnsupportedTransformError):
        to_affine(_placement(scale=(0.0, 1.0, 1.0)))


def test_bounding_box_transforms_all_eight_corners():
    """

    @brief Implements the test_bounding_box_transforms_all_eight_corners
    operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    affine = to_affine(_placement(rotation=(0.0, 0.0, 90.0)))
    bbox = ((0.0, 0.0, 0.0), (1.0, 2.0, 3.0))
    minimum, maximum = apply_bbox(affine, bbox)
    assert minimum == pytest.approx((-2.0, 0.0, 0.0), abs=1e-9)
    assert maximum == pytest.approx((0.0, 1.0, 3.0), abs=1e-9)


def test_nonuniform_scale_composed_with_planar_rotation_exact_matrix():
    """

    @brief Implements the
    test_nonuniform_scale_composed_with_planar_rotation_exact_matrix
    operation.
    @return The callable result.
    @details cos=3/5, sin=4/5 with S=diag(2,1,1) produces the exact
    linear part [[6/5,-4/5,0],[8/5,3/5,0],[0,0,1]] per section 150.

    """
    angle = math.degrees(math.atan2(4.0, 3.0))
    affine = to_affine(
        _placement(rotation=(0.0, 0.0, angle), scale=(2.0, 1.0, 1.0))
    )
    expected = (
        (1.2, -0.8, 0.0, 0.0),
        (1.6, 0.6, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    for row in range(4):
        for col in range(4):
            assert affine.matrix[row][col] == pytest.approx(
                expected[row][col], abs=1e-9
            )


def test_simple_placement_from_affine_round_trip():
    """

    @brief Implements the
    test_simple_placement_from_affine_round_trip operation.
    @return The callable result.
    @details A representable placement (rotation + nonuniform scale,
    no shear) recovers a Placement that reconstructs the same matrix.

    """
    angle = math.degrees(math.atan2(4.0, 3.0))
    affine = to_affine(
        _placement(
            translation=(1.0, 2.0, 3.0),
            rotation=(0.0, 0.0, angle),
            scale=(2.0, 1.0, 1.0),
            mirror=MirrorState(x=True),
        )
    )
    placement = simple_placement_from_affine(affine, TOLERANCE)
    reconstructed = to_affine(placement)
    assert equivalent_within_tolerance(reconstructed, affine, 1e-6)


def test_simple_placement_from_affine_rejects_shear():
    """

    @brief Implements the
    test_simple_placement_from_affine_rejects_shear operation.
    @return The callable result.
    @details A genuine shear matrix (nonorthogonal columns) has no
    representable Placement and must be rejected, never silently
    dropped.

    """
    from partsmith.threed.transform import AffineTransform

    sheared = AffineTransform(
        (
            (1.0, 1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        "A",
        "B",
    )
    with pytest.raises(UnsupportedTransformError):
        simple_placement_from_affine(sheared, TOLERANCE)


def test_equivalent_within_tolerance_rejects_frame_mismatch():
    """

    @brief Implements the
    test_equivalent_within_tolerance_rejects_frame_mismatch operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    a = to_affine(_placement(source="A", destination="B"))
    b = to_affine(_placement(source="A", destination="C"))
    assert not equivalent_within_tolerance(a, b, 1.0)
