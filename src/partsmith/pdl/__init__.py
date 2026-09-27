"""Versioned Package Definition Library contracts."""

from partsmith.pdl.compatibility import ir_pdl_issues
from partsmith.pdl.errors import PDLValidationError
from partsmith.pdl.loader import list_pdls, load_pdl, resolve_pdl
from partsmith.pdl.model import PDL, canonical_pdl, pdl_hash, validate_pdl
from partsmith.pdl.profiles import load_release_profile, release_profile_hash
from partsmith.pdl.schema import SUPPORTED_VERSIONS, load_schema, schema_issues

__all__ = [
    "PDL",
    "PDLValidationError",
    "SUPPORTED_VERSIONS",
    "canonical_pdl",
    "ir_pdl_issues",
    "list_pdls",
    "load_pdl",
    "load_release_profile",
    "load_schema",
    "pdl_hash",
    "release_profile_hash",
    "resolve_pdl",
    "schema_issues",
    "validate_pdl",
]
