"""@package partsmith.release.schema
@brief Offline JSON Schema validation for Phase 8 contracts.
@details Loads one packaged schema and validates named closed definitions
without network access.
"""

from functools import cache, lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from partsmith.ir.errors import Issue
from partsmith.schema_support import (
    decimal_validator_class,
    load_packaged_schema,
    schema_error_path,
)

SCHEMA_VERSION = "1.0"


@lru_cache(maxsize=1)
def load_schema() -> dict:
    """@brief Loads the packaged Phase 8 contract schema.
    @return Parsed JSON Schema mapping.
    @details Editable installs fall back to the repository schema file.
    """
    name = f"phase8-contracts-{SCHEMA_VERSION}.schema.json"
    fallback = Path(__file__).resolve().parents[3] / "schemas" / name
    return load_packaged_schema(__package__, name, fallback)


@cache
def _validator(kind: str) -> Draft202012Validator:
    """@brief Builds a validator for one named schema definition.
    @param kind Definition name under `$defs`.
    @return Configured offline JSON Schema validator.
    @details Raises ValueError for an unknown external contract kind.
    """
    schema = load_schema()
    if kind not in schema["$defs"]:
        raise ValueError(f"Unsupported Phase 8 schema kind: {kind}")
    validator_class = decimal_validator_class()
    validator_class.check_schema(schema)
    return validator_class(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{kind}",
        }
    )


def schema_issues(kind: str, data: object) -> tuple[Issue, ...]:
    """@brief Returns stable schema issues for a Phase 8 document.
    @param kind Named definition under the packaged schema.
    @param data JSON-compatible document to validate.
    @return Sorted immutable schema issues.
    @details Diagnostics contain paths and constraint names but not values.
    """
    issues = []
    for error in _validator(kind).iter_errors(data):
        path = schema_error_path(error)
        issues.append(
            Issue(
                path,
                "PHASE8_SCHEMA",
                f"Schema constraint: {error.validator}",
            )
        )
    return tuple(sorted(set(issues)))
