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
    export_step_solids,
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
from partsmith.threed.validation import (
    ValidationResult,
    cross_validate_footprint_3d,
    validate_applicability_binding,
    validate_model_3d,
    validate_step_file,
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
    "ValidationResult",
    "apply_bbox",
    "apply_point",
    "apply_vector",
    "compose",
    "cross_validate_footprint_3d",
    "equivalent_within_tolerance",
    "export_step_solids",
    "generate_model_3d",
    "generate_step_bytes",
    "invert",
    "measure_step",
    "simple_placement_from_affine",
    "threed_dependency_hash",
    "threed_projection",
    "to_affine",
    "validate_step_artifact",
    "validate_model_3d",
    "validate_applicability_binding",
    "validate_step_file",
    "validate_threed_inputs",
]
