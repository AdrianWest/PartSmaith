"""@package partsmith.integration.schema
@brief Validates closed integration contracts without network access.
@details Package resources use the shared source-tree fallback convention.
"""

from functools import cache
from pathlib import Path

from partsmith.schema_support import (
    decimal_validator_class,
    load_packaged_schema,
    schema_error_path,
)


@cache
def load_schema() -> dict:
    """@brief Loads schema version 1.0 from package or source.
    @return Parsed integration schema.
    @details All references are internal; validation never retrieves URLs.
    """
    name = "integration-contracts-1.0.schema.json"
    fallback = Path(__file__).resolve().parents[3] / "schemas" / name
    return load_packaged_schema(__package__, name, fallback)


@cache
def validator(kind: str):
    """@brief Constructs a validator for a named definition.
    @param kind Integration definition name.
    @return Offline Draft 2020-12 validator.
    @details Unknown definitions raise ValueError before validating data.
    """
    schema = load_schema()
    if kind not in schema["$defs"]:
        raise ValueError("Unsupported integration contract kind")
    cls = decimal_validator_class()
    cls.check_schema(schema)
    return cls(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{kind}",
        }
    )


def validate_shape(kind: str, data: object) -> None:
    """@brief Rejects invalid closed contract shapes.
    @param kind Integration definition name.
    @param data Candidate JSON-compatible document.
    @return None.
    @details Diagnostics contain paths and constraint names, never values.
    """
    errors = sorted(
        (schema_error_path(e), str(e.validator))
        for e in validator(kind).iter_errors(data)
    )
    if errors:
        raise ValueError(f"Invalid {kind}: {errors}")
