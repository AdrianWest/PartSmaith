"""Phase 2 fixture gate and canonicalization/validation regressions."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from decimal import Decimal, localcontext
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from partsmith.ir import (
    ComponentIR,
    IRValidationError,
    canonical_ir,
    canonical_json,
    ir_hash,
    load_schema,
    normalize_ir,
    normalize_quantity,
    validate_ir,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/ir"
NEGATIVE_CASES = json.loads((FIXTURES / "invalid/expected.json").read_text())


@pytest.fixture
def valid():
    return json.loads(
        (FIXTURES / "valid/0402.json").read_text(encoding="utf-8")
    )


def test_phase_two_gate(valid):
    Draft202012Validator.check_schema(load_schema())
    assert validate_ir(valid) == ()
    normalized = normalize_ir(valid)
    width = normalized["package"]["mechanical"]["body_width"]
    assert width["source_value"] == 500
    assert width["source_unit"] == "um"
    assert width["normalized_value"] == Decimal("0.5")
    assert width["normalized_unit"] == "mm"
    assert validate_ir(normalized, for_generation=True) == ()
    expected = (FIXTURES / "expected/0402.canonical.json").read_bytes()
    expected_hash = (FIXTURES / "expected/0402.sha256").read_text().strip()
    assert canonical_ir(valid) == expected
    assert ir_hash(valid) == expected_hash == sha256(expected).hexdigest()
    assert canonical_ir(normalized) == expected
    assert ComponentIR.from_json(expected).canonical_bytes == expected


@pytest.mark.parametrize("case", NEGATIVE_CASES, ids=lambda c: c["file"])
def test_negative_fixtures_fail_intended_validator(case):
    data = json.loads((FIXTURES / "invalid" / case["file"]).read_text())
    issues = validate_ir(data, for_generation=case["for_generation"])
    assert [(issue.code, issue.path) for issue in issues] == [
        (case["code"], case["path"])
    ]
    assert issues == validate_ir(data, for_generation=case["for_generation"])
    with pytest.raises(IRValidationError) as caught:
        normalize_ir(data, for_generation=case["for_generation"])
    assert caught.value.issues == issues


def test_every_invalid_fixture_has_expectations():
    assert {c["file"] for c in NEGATIVE_CASES} == {
        p.name
        for p in (FIXTURES / "invalid").glob("*.json")
        if p.name != "expected.json"
    }


@pytest.mark.parametrize(
    "unit,value,expected,target",
    [
        ("mm", 1, "1", "mm"),
        ("mil", Decimal("118.1"), "2.99974", "mm"),
        ("inch", Decimal("0.1"), "2.54", "mm"),
        ("um", 500, "0.5", "mm"),
        ("µm", 350, "0.35", "mm"),
        ("μm", 350, "0.35", "mm"),
        ("degree", 90, "90", "deg"),
        ("degrees", -90, "-90", "deg"),
        ("deg", 360, "360", "deg"),
    ],
)
def test_exact_unit_conversions(unit, value, expected, target):
    with localcontext() as context:
        context.prec = 2
        assert normalize_quantity(value, unit) == (Decimal(expected), target)


@pytest.mark.parametrize("unit", [None, "", "rad", "cm", "MM"])
def test_never_guess_units(unit):
    with pytest.raises(IRValidationError, match="IR_UNIT"):
        normalize_quantity(1, unit)


def test_canonical_json_has_independent_expected_bytes():
    value = {
        "z": [-0.0, Decimal("1.2300"), 1e3, True, None],
        "a": "e\u0301\r\nline",
    }
    assert (
        canonical_json(value)
        == '{"a":"é\\nline","z":[0,1.23,1000,true,null]}'.encode()
    )
    assert canonical_json({"number": 1}) == canonical_json(
        {"number": Decimal("1.000")}
    )
    with localcontext() as context:
        context.prec = 2
        assert canonical_json(Decimal("123.456789")) == b"123.456789"


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("1e101"),
        Decimal("1e-101"),
    ],
)
def test_nonfinite_and_unbounded_numbers_are_rejected(value):
    with pytest.raises(IRValidationError, match="IR_NUMBER"):
        canonical_json(value)


@pytest.mark.parametrize(
    "value", [{1: "bad"}, {"é": 1, "e\u0301": 2}, (1, 2), {1, 2}]
)
def test_non_json_data_and_key_collisions_are_rejected(value):
    with pytest.raises(IRValidationError, match="IR_JSON"):
        canonical_json(value)


@pytest.mark.parametrize(
    "text,code",
    [
        ('{"a":1,"a":2}', "IR_JSON"),
        ('{"a":NaN}', "IR_NUMBER"),
        ('{"a":Infinity}', "IR_NUMBER"),
        ('{"a":-Infinity}', "IR_NUMBER"),
        ("{broken", "IR_JSON"),
        (b"\xff", "IR_JSON"),
        ('{"a":"\\ud800"}', "IR_TEXT"),
    ],
)
def test_invalid_json_is_rejected_before_schema(text, code):
    with pytest.raises(IRValidationError, match=code):
        ComponentIR.from_json(text)


def test_no_input_mutation_and_immutable_model(valid):
    original = copy.deepcopy(valid)
    component = ComponentIR(valid)
    detached = component.data
    detached["identity"]["mpn"] = "different"
    assert valid == original
    assert component.data["identity"]["mpn"] == original["identity"]["mpn"]
    with pytest.raises(FrozenInstanceError):
        component.canonical_bytes = b"{}"


def test_cosmetic_variants_have_equal_hashes(valid):
    first = copy.deepcopy(valid)
    first["revision"]["description"] = "Café\nTest"
    second = dict(reversed(list(first.items())))
    second = copy.deepcopy(second)
    second["revision"]["description"] = "Cafe\u0301\r\nTest"
    second["source"]["documents"][0]["path"] = "source\\.\\synthetic-0402.txt"
    second["package"]["mechanical"]["body_length"]["source_value"] = Decimal(
        "1.0000"
    )
    assert ir_hash(first) == ir_hash(second)


def test_source_units_remain_hash_significant(valid):
    changed = copy.deepcopy(valid)
    changed["package"]["mechanical"]["body_width"].update(
        source_value=0.5, source_unit="mm"
    )
    assert normalize_ir(changed)["package"]["mechanical"]["body_width"][
        "normalized_value"
    ] == Decimal("0.5")
    # Provenance changes even when physical dimensions are equivalent.
    assert ir_hash(valid) != ir_hash(changed)


def test_hash_covers_engineering_values_provenance_and_array_order(valid):
    changed = copy.deepcopy(valid)
    changed["electrical"]["resistance"]["value"] = 22000
    assert ir_hash(changed) != ir_hash(valid)
    changed = copy.deepcopy(valid)
    changed["evidence"][0]["extracted"]["text"] += " changed"
    assert ir_hash(changed) != ir_hash(valid)
    changed = copy.deepcopy(valid)
    changed["pins"].reverse()
    assert ir_hash(changed) != ir_hash(valid)


def test_hash_is_stable_across_processes_and_hash_seeds(valid):
    code = (
        "from partsmith.ir import ComponentIR; import sys; "
        "print(ComponentIR.from_file(sys.argv[1]).sha256)"
    )
    expected = ir_hash(valid)
    for seed in ("1", "293"):
        result = subprocess.run(
            [sys.executable, "-c", code, str(FIXTURES / "valid/0402.json")],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    "status", ["UNKNOWN", "INFERRED", "AMBIGUOUS", "CONFLICTING", "MISSING"]
)
def test_candidates_are_preserved_but_cannot_enter_generation(valid, status):
    valid["package"]["mechanical"]["body_height"]["status"] = status
    assert validate_ir(valid) == ()
    assert (
        ComponentIR(valid).data["package"]["mechanical"]["body_height"][
            "status"
        ]
        == status
    )
    assert {i.code for i in validate_ir(valid, for_generation=True)} == {
        "IR_UNRESOLVED"
    }


@pytest.mark.parametrize(
    "field,value",
    [("source_value", True), ("source_value", "0.5"), ("status", "APPROVED")],
)
def test_schema_rejects_coercion(valid, field, value):
    valid["package"]["mechanical"]["body_width"][field] = value
    assert {i.code for i in validate_ir(valid)} == {"IR_SCHEMA"}


def test_supplied_normalization_cannot_override_source(valid):
    width = valid["package"]["mechanical"]["body_width"]
    width.update(normalized_value=1, normalized_unit="mm")
    assert {i.code for i in validate_ir(valid)} == {"IR_UNIT"}
    width.update(normalized_value=0.5, normalized_unit="deg")
    assert {i.code for i in validate_ir(valid)} == {"IR_UNIT"}


def test_reference_integrity_and_provenance(valid):
    valid["evidence"][0]["source"]["document_hash"] = "0" * 64
    assert {i.code for i in validate_ir(valid)} == {"IR_REFERENCE"}
    valid["evidence"][0]["source"]["document_hash"] = valid["source"][
        "documents"
    ][0]["sha256"]
    valid["package"]["mechanical"]["body_width"]["evidence_ids"] = []
    assert {i.code for i in validate_ir(valid, for_generation=True)} == {
        "IR_PROVENANCE"
    }


def test_synthetic_source_hash_is_real(valid):
    source = valid["source"]["documents"][0]
    assert (
        sha256((FIXTURES / source["path"]).read_bytes()).hexdigest()
        == source["sha256"]
    )


@pytest.mark.parametrize(
    "path",
    ["../private.pdf", "/home/private.pdf", "\\\\server\\private.pdf", "."],
)
def test_nonportable_paths_are_rejected(valid, path):
    valid["source"]["documents"][0]["path"] = path
    assert {i.code for i in validate_ir(valid)} == {"IR_PATH"}


@pytest.mark.parametrize("number", ["A1", "NC", "EP"])
def test_alphanumeric_pin_numbers_are_preserved(valid, number):
    valid["pins"][0]["number"] = number
    assert ComponentIR(valid).data["pins"][0]["number"] == number


def test_duplicate_evidence_ids_are_rejected(valid):
    valid["evidence"].append(copy.deepcopy(valid["evidence"][0]))
    assert {i.code for i in validate_ir(valid)} == {"IR_DUPLICATE_ID"}


def test_null_electrical_value_is_not_generation_ready(valid):
    valid["electrical"]["resistance"]["value"] = None
    assert validate_ir(valid) == ()
    assert {i.code for i in validate_ir(valid, for_generation=True)} == {
        "IR_UNRESOLVED"
    }


def test_derived_and_standard_values_require_provenance(valid):
    width = valid["package"]["mechanical"]["body_width"]
    width["status"] = "DERIVED"
    assert {i.code for i in validate_ir(valid, for_generation=True)} == {
        "IR_PROVENANCE"
    }
    width["derivation"] = "Half of the source body length"
    assert validate_ir(valid, for_generation=True) == ()
    width["status"] = "STANDARD"
    assert {i.code for i in validate_ir(valid, for_generation=True)} == {
        "IR_PROVENANCE"
    }
    valid["standards"] = [
        {
            "id": "STD-1",
            "name": "Synthetic test standard",
            "revision": "1",
            "reference": "test-only",
        }
    ]
    width["standard_id"] = "STD-1"
    assert validate_ir(valid, for_generation=True) == ()


def test_override_audit_data_and_timestamp_are_validated_and_hashed(valid):
    before = ir_hash(valid)
    value = {
        "value": 10000,
        "unit": "ohm",
        "status": "DIRECT",
        "evidence_ids": ["E-001"],
    }
    valid["overrides"] = [
        {
            "id": "O-1",
            "path": "electrical.resistance",
            "previous_value": value,
            "new_value": {**value, "value": 22000},
            "reason": "Synthetic test",
            "user": "test-reviewer",
            "timestamp": "2026-09-19T12:00:00Z",
            "evidence_reference": "E-001",
            "approval_state": "APPROVED",
        }
    ]
    assert validate_ir(valid) == ()
    assert ir_hash(valid) != before
    assert (
        ComponentIR(valid).data["overrides"][0]["previous_value"]["value"]
        == 10000
    )
    valid["overrides"][0]["timestamp"] = "not a timestamp"
    assert {i.code for i in validate_ir(valid)} == {"IR_SCHEMA"}


def test_manufacturer_and_mpn_spellings_are_preserved(valid):
    valid["identity"]["manufacturer"]["name"] = "Example Components Inc."
    valid["identity"]["mpn"] = "Test-R-0402/a"
    identity = ComponentIR(valid).data["identity"]
    assert identity["manufacturer"]["name"] == "Example Components Inc."
    assert identity["manufacturer"]["normalized_name"] == "example components"
    assert identity["mpn"] == "Test-R-0402/a"
    assert identity["normalized_mpn"] == "TEST-R-0402"


def test_error_order_is_independent_of_input_key_order(valid):
    valid["package"]["mechanical"]["body_width"]["source_value"] = float("inf")
    valid["electrical"]["resistance"]["value"] = float("nan")
    reversed_data = dict(reversed(list(valid.items())))
    assert validate_ir(valid) == validate_ir(reversed_data)


@pytest.mark.parametrize(
    "number",
    [
        Decimal("1e100"),
        Decimal("1e-100"),
        Decimal("123.4500"),
        Decimal("-0.000"),
    ],
)
def test_numeric_limits_survive_canonical_round_trip(valid, number):
    valid["electrical"]["resistance"]["value"] = number
    ir = ComponentIR(valid)
    assert ComponentIR.from_json(ir.canonical_bytes).sha256 == ir.sha256
