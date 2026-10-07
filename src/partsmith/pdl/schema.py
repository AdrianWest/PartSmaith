"""

@package src.partsmith.pdl.schema
@brief Packaged, offline PDL JSON Schema validation.
@details Provides the module implementation and public interfaces.
"""

from datetime import date
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from partsmith.ir.errors import Issue
from partsmith.schema_support import (
    decimal_validator_class,
    load_packaged_schema,
    schema_error_path,
)

SUPPORTED_VERSIONS = ("1.0", "1.1")


def load_schema(version: str = "1.0") -> dict:
    """

    @brief Load one supported PDL schema without network access.
    @param version The version argument.
    @return The dict result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported PDL version: {version}")
    name = f"pdl-{version}.schema.json"
    fallback = Path(__file__).resolve().parents[3] / "schemas" / name
    return load_packaged_schema(__package__, name, fallback)


@lru_cache(maxsize=1)
def _validator(version: str) -> Draft202012Validator:
    """

    @brief Implements the _validator operation.
    @param version The version argument.
    @return The Draft202012Validator result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    validator_class = decimal_validator_class()
    schema = load_schema(version)
    validator_class.check_schema(schema)
    formats = FormatChecker()

    @formats.checks("date", raises=ValueError)
    def valid_date(value: object) -> bool:
        """

        @brief Implements the valid_date operation.
        @param value The value argument.
        @return The bool result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        if not isinstance(value, str):
            return True
        return date.fromisoformat(value).isoformat() == value

    return validator_class(schema, format_checker=formats)


def schema_issues(data: object) -> list[Issue]:
    """

    @brief Return sorted, value-free schema diagnostics.
    @param data The data argument.
    @return The list[Issue] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    version = data.get("schema_version") if isinstance(data, dict) else None
    if version not in SUPPORTED_VERSIONS:
        return [
            Issue("/schema_version", "PDL_VERSION", "Unsupported PDL version")
        ]
    issues = []
    for error in _validator(version).iter_errors(data):
        path = schema_error_path(error)
        issues.append(
            Issue(path, "PDL_SCHEMA", f"Schema constraint: {error.validator}")
        )
    return sorted(set(issues))
