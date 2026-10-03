"""

@package src.partsmith.ir.schema
@brief Packaged, offline JSON Schema validation with stable
diagnostics.
@details Provides the module implementation and public interfaces.
"""

import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import FormatChecker

from partsmith.ir.errors import Issue, fail
from partsmith.schema_support import (
    decimal_validator_class,
    load_packaged_schema,
    schema_error_path,
)

SUPPORTED_VERSIONS = ("1.0", "1.1", "1.2")


def load_schema(version: str = "1.0") -> dict:
    """

    @brief Implements the load_schema operation.
    @param version The version argument.
    @return The dict result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    if version not in SUPPORTED_VERSIONS:
        fail("/schema_version", "IR_VERSION", "Unsupported IR version")
    name = f"component-ir-{version}.schema.json"
    fallback = Path(__file__).resolve().parents[3] / "schemas" / name
    return load_packaged_schema(__package__, name, fallback)


@lru_cache(maxsize=3)
def _validator(version):
    """

    @brief Implements the _validator operation.
    @param version The version argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    validator_class = decimal_validator_class()
    schema = load_schema(version)
    validator_class.check_schema(schema)
    formats = FormatChecker()

    @formats.checks("date-time", raises=ValueError)
    def timestamp(value):
        """

        @brief Implements the timestamp operation.
        @param value The value argument.
        @return The callable result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        if not isinstance(value, str):
            return True  # Type validation reports non-string input.
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
            r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
            value,
        ):
            return False
        return datetime.fromisoformat(value).utcoffset() is not None

    return validator_class(schema, format_checker=formats)


def fragment_valid(value, fragment, version="1.2"):
    """

    @brief Validate a trusted fragment using packaged local definitions.
    @param value The value argument.
    @param fragment The fragment argument.
    @param version The version argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    schema = {**fragment, "$defs": load_schema(version)["$defs"]}
    return _validator(version).evolve(schema=schema).is_valid(value)


def schema_issues(data) -> list[Issue]:
    """

    @brief Implements the schema_issues operation.
    @param data The data argument.
    @return The list[Issue] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    version = data.get("schema_version") if isinstance(data, dict) else None
    if version not in SUPPORTED_VERSIONS:
        return [
            Issue("/schema_version", "IR_VERSION", "Unsupported IR version")
        ]
    issues = []
    for error in _validator(version).iter_errors(data):
        path = schema_error_path(error)
        code = "IR_SCHEMA"
        if path == "/schema_version":
            code = "IR_VERSION"
        if path.endswith(("/source_unit", "/normalized_unit")):
            code = "IR_UNIT"
        # Do not include instance values in diagnostics (may contain secrets).
        issues.append(
            Issue(path, code, f"Schema constraint: {error.validator}")
        )
    return issues
