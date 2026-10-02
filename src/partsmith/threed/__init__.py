"""

@package src.partsmith.threed.__init__
@brief Deterministic CadQuery/OCP/OCCT 3D generation.
@details Provides the module implementation and public interfaces.
"""

from partsmith.threed.model import (
    DeterministicThreeDGenerator,
    GeneratedArtifact,
    ThreeDContext,
    ThreeDGenerator,
    generate_model_3d,
    threed_dependency_hash,
    threed_projection,
    validate_step_artifact,
    validate_threed_inputs,
)
from partsmith.threed.step_backend import (
    CADQUERY_VERSION,
    OCP_VERSION,
    SolidMeasurement,
    StepMeasurement,
    generate_step_bytes,
    measure_step,
)
from partsmith.threed.transform import (
    AffineTransform,
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

__all__ = [
    "CADQUERY_VERSION",
    "OCP_VERSION",
    "AffineTransform",
    "DeterministicThreeDGenerator",
    "GeneratedArtifact",
    "MirrorState",
    "Placement",
    "SolidMeasurement",
    "StepMeasurement",
    "ThreeDContext",
    "ThreeDGenerator",
    "UnsupportedTransformError",
    "apply_bbox",
    "apply_point",
    "apply_vector",
    "compose",
    "equivalent_within_tolerance",
    "generate_model_3d",
    "generate_step_bytes",
    "invert",
    "measure_step",
    "simple_placement_from_affine",
    "threed_dependency_hash",
    "threed_projection",
    "to_affine",
    "validate_step_artifact",
    "validate_threed_inputs",
]
