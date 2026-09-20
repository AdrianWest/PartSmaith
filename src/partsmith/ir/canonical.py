"""Exact decimal, NFC UTF-8 canonical JSON (PartSmith profile 1.0)."""

import json
import math
import unicodedata
from decimal import Decimal

from partsmith.ir.errors import fail, pointer


def decimal_number(value, path: str = "") -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        fail(path, "IR_NUMBER", "Expected a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        fail(path, "IR_NUMBER", "Numbers must be finite")
    number = Decimal(str(value))
    if not number.is_finite():
        fail(path, "IR_NUMBER", "Numbers must be finite")
    if number == 0:
        return Decimal(0)
    # Strip redundant zeros without Decimal.normalize(), which rounds using
    # the caller's context. Bounds must survive plain-decimal serialization.
    sign, digits, exponent = number.as_tuple()
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    if len(digits) > 100 or abs(exponent) > 100:
        fail(path, "IR_NUMBER", "Number exceeds profile precision/range")
    return Decimal((sign, digits, exponent))


def normalize_text(value: str) -> str:
    text = unicodedata.normalize(
        "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
    )
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        fail("", "IR_TEXT", "Unpaired Unicode surrogate")
    return text


def normalize_json(value, path: str = ""):
    """Copy JSON data; reject invalid types and normalized key collisions."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, (int, float, Decimal)):
        return decimal_number(value, path)
    if isinstance(value, list):
        return [
            normalize_json(item, pointer(path, i))
            for i, item in enumerate(value)
        ]
    if isinstance(value, dict):
        result = {}
        if any(not isinstance(key, str) for key in value):
            fail(path, "IR_JSON", "Object keys must be strings")
        for key, item in value.items():
            key = normalize_text(key)
            if key in result:
                fail(path, "IR_JSON", "Duplicate normalized object key")
            result[key] = item
        return {
            key: normalize_json(result[key], pointer(path, key))
            for key in sorted(result)
        }
    fail(path, "IR_JSON", "Expected JSON-compatible data")


def canonical_json(value) -> bytes:
    """Sort keys, preserve array order, and emit exact decimal tokens."""

    def encode(item):
        if item is None:
            return "null"
        if isinstance(item, bool):
            return "true" if item else "false"
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False)
        if isinstance(item, Decimal):
            if item == 0:
                return "0"
            token = format(item, "f")
            return token.rstrip("0").rstrip(".") if "." in token else token
        if isinstance(item, list):
            return "[" + ",".join(encode(entry) for entry in item) + "]"
        return (
            "{"
            + ",".join(
                encode(key) + ":" + encode(item[key]) for key in sorted(item)
            )
            + "}"
        )

    return encode(normalize_json(value)).encode("utf-8")


def parse_json(text: str | bytes):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                fail("", "IR_JSON", "Duplicate object key")
            result[key] = value
        return result

    def reject_constant(_):
        fail("", "IR_NUMBER", "Numbers must be finite")

    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        return json.loads(
            text,
            parse_float=Decimal,
            parse_int=Decimal,
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        fail("", "IR_JSON", "Invalid UTF-8 JSON")
