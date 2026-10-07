"""

@package src.partsmith.footprint.__init__
@brief Deterministic KiCad footprint generation.
@details Provides the module implementation and public interfaces.
"""

from partsmith.footprint.model import (
    DeterministicFootprintGenerator,
    FootprintContext,
    FootprintGenerator,
    GeneratedArtifact,
    GeneratorContext,
    association_dependency_hash,
    footprint_dependency_hash,
    footprint_projection,
    serialize_footprint,
    validate_footprint_artifact,
    validate_footprint_inputs,
)

__all__ = [
    "DeterministicFootprintGenerator",
    "FootprintContext",
    "FootprintGenerator",
    "GeneratorContext",
    "GeneratedArtifact",
    "association_dependency_hash",
    "footprint_dependency_hash",
    "footprint_projection",
    "serialize_footprint",
    "validate_footprint_artifact",
    "validate_footprint_inputs",
]
