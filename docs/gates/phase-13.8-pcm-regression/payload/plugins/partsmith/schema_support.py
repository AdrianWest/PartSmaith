"""@package partsmith.schema_support
@brief Shared offline JSON Schema loading and validator primitives.
@details Domain modules retain version, format, diagnostic, and result policy.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import cache
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator, validators


def load_packaged_schema(
    package: str, name: str, fallback: str | Path
) -> dict:
    """@brief Loads one packaged JSON Schema with an editable fallback.
    @param package Resource-anchor package supplied by the domain caller.
    @param name Schema resource filename.
    @param fallback Explicit editable-repository fallback path.
    @return Parsed JSON Schema mapping.
    @details Resource and fallback locations are caller-owned so this helper
    never derives paths from its own package location.
    """
    resource = files(package).joinpath(name)
    path = resource if resource.is_file() else Path(fallback)
    return json.loads(path.read_text(encoding="utf-8"))


@cache
def decimal_validator_class():
    """@brief Builds the shared Decimal-compatible validator class.
    @return Extended Draft 2020-12 validator class.
    @details Booleans remain non-integers while integral Decimal and float
    values satisfy JSON Schema integer constraints.
    """
    checker = Draft202012Validator.TYPE_CHECKER.redefine(
        "integer",
        lambda _, value: (
            not isinstance(value, bool)
            and isinstance(value, (int, float, Decimal))
            and value == int(value)
        ),
    )
    return validators.extend(Draft202012Validator, type_checker=checker)


def schema_error_path(error) -> str:
    """@brief Converts a JSON Schema error path to a JSON Pointer.
    @param error Validation error with an absolute path.
    @return Escaped JSON Pointer or an empty root path.
    @details Instance values are never included in the returned diagnostic.
    """
    path = ""
    for key in error.absolute_path:
        token = str(key).replace("~", "~0").replace("/", "~1")
        path = f"{path}/{token}"
    return path
