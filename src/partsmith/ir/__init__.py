"""Versioned Component IR validation, migration, provenance, and hashing."""

from partsmith.ir.canonical import canonical_json
from partsmith.ir.errors import IRValidationError, Issue
from partsmith.ir.history import (
    MemoryRevisionStore,
    RevisionStore,
    validate_revision_transition,
)
from partsmith.ir.migration import MigrationResult, migrate_v1_0_to_v1_1
from partsmith.ir.migration_v12 import migrate_v1_1_to_v1_2
from partsmith.ir.model import (
    ComponentIR,
    canonical_ir,
    ir_hash,
    normalize_ir,
    validate_ir,
)
from partsmith.ir.projection import dependency_hash, dependency_projection
from partsmith.ir.revised import RequirementsContext
from partsmith.ir.schema import SUPPORTED_VERSIONS, load_schema
from partsmith.ir.units import normalize_quantity

__all__ = [
    "ComponentIR",
    "IRValidationError",
    "Issue",
    "MigrationResult",
    "MemoryRevisionStore",
    "RevisionStore",
    "RequirementsContext",
    "SUPPORTED_VERSIONS",
    "canonical_ir",
    "canonical_json",
    "dependency_hash",
    "dependency_projection",
    "ir_hash",
    "load_schema",
    "migrate_v1_0_to_v1_1",
    "migrate_v1_1_to_v1_2",
    "normalize_ir",
    "normalize_quantity",
    "validate_ir",
    "validate_revision_transition",
]
