"""Packaged, offline JSON Schema validation with stable diagnostics."""

import json
import re
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, validators

from partsmith.ir.errors import Issue, fail, pointer

SUPPORTED_VERSIONS = ("1.0", "1.1", "1.2")


def load_schema(version: str = "1.0") -> dict:
    if version not in SUPPORTED_VERSIONS:
        fail("/schema_version", "IR_VERSION", "Unsupported IR version")
    name = f"component-ir-{version}.schema.json"
    resource = files(__package__).joinpath(name)
    if not resource.is_file():
        resource = Path(__file__).resolve().parents[3] / "schemas" / name
    return json.loads(resource.read_text(encoding="utf-8"))


@lru_cache(maxsize=3)
def _validator(version):
    checker = Draft202012Validator.TYPE_CHECKER.redefine(
        "integer",
        lambda _, value: (
            not isinstance(value, bool)
            and isinstance(value, (int, float, Decimal))
            and value == int(value)
        ),
    )
    validator_class = validators.extend(
        Draft202012Validator, type_checker=checker
    )
    schema = load_schema(version)
    validator_class.check_schema(schema)
    formats = FormatChecker()

    @formats.checks("date-time", raises=ValueError)
    def timestamp(value):
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
    """Validate a trusted fragment using packaged local definitions."""
    schema = {**fragment, "$defs": load_schema(version)["$defs"]}
    return _validator(version).evolve(schema=schema).is_valid(value)


def schema_issues(data) -> list[Issue]:
    version = data.get("schema_version") if isinstance(data, dict) else None
    if version not in SUPPORTED_VERSIONS:
        return [
            Issue("/schema_version", "IR_VERSION", "Unsupported IR version")
        ]
    issues = []
    for error in _validator(version).iter_errors(data):
        path = ""
        for key in error.absolute_path:
            path = pointer(path, key)
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
