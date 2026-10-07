"""@package partsmith.kicad
@brief Exposes pinned native KiCad runtime validation.
@details Native compatibility is mandatory for Phase 8 release approval.
"""

from partsmith.kicad.runtime import (
    KiCadCompatibilityError,
    KiCadRuntime,
    NativeKiCadValidation,
    discover_kicad,
    validate_native_artifacts,
)

__all__ = [
    "KiCadCompatibilityError",
    "KiCadRuntime",
    "NativeKiCadValidation",
    "discover_kicad",
    "validate_native_artifacts",
]
