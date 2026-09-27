"""Phase 4 deterministic symbol-generation gate tests."""

from hashlib import sha256
from pathlib import Path

from partsmith.ir.canonical import parse_json
from partsmith.ir.model import ComponentIR
from partsmith.pdl import load_pdl
from partsmith.symbol import (
    DeterministicSymbolGenerator,
    GeneratorContext,
    SymbolContext,
    serialize_symbol,
    symbol_dependency_hash,
    validate_symbol_artifact,
    validate_symbol_inputs,
)

ROOT = Path(__file__).parents[1]
IR_PATH = ROOT / "fixtures/ir/v1.2/valid/0402.json"
GOLDEN = ROOT / "fixtures/symbol/expected/0402.kicad_sym"


def _inputs():
    return parse_json(IR_PATH.read_bytes()), load_pdl("synthetic-0402")


def test_phase_four_gate_generates_valid_deterministic_symbol():
    ir, pdl = _inputs()
    context = SymbolContext()
    assert validate_symbol_inputs(ir, pdl) == ()

    first = serialize_symbol(ir, context)
    second = serialize_symbol(ir, context)
    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert validate_symbol_artifact(first, ir) == ()
    assert first.filename == "TEST-R-0402.kicad_sym"
    assert first.content.startswith(b"(kicad_symbol_lib\n")
    assert first.content == GOLDEN.read_bytes()
    assert sha256(first.content).hexdigest() == (
        "25e1017ac38814bf025ae5dab90761beb10dd09b8b3e93d3e876bfc5d2fd6d31"
    )


def test_symbol_dependency_changes_only_for_consumed_inputs():
    ir, _ = _inputs()
    baseline = symbol_dependency_hash(ir, SymbolContext())

    changed_pin = parse_json(IR_PATH.read_bytes())
    changed_pin["pins"][0]["name"] = "A"
    assert symbol_dependency_hash(changed_pin, SymbolContext()) != baseline

    changed_cad_context = SymbolContext()
    assert symbol_dependency_hash(ir, changed_cad_context) == baseline

    changed_component_id = parse_json(IR_PATH.read_bytes())
    changed_component_id["identity"]["component_id"] = (
        "01995ead-8000-7000-8000-000000000099"
    )
    assert (
        symbol_dependency_hash(changed_component_id, SymbolContext())
        == baseline
    )
    assert (
        symbol_dependency_hash(ir, SymbolContext(naming_version="2.0"))
        != baseline
    )


def test_symbol_input_validation_rejects_malformed_ir():
    _, pdl = _inputs()
    issues = validate_symbol_inputs({}, pdl)
    assert issues
    assert all(issue.code in {"IR_SCHEMA", "IR_VERSION"} for issue in issues)


def test_concrete_generator_implements_component_ir_api():
    ir = ComponentIR.from_file(IR_PATH)
    artifact = DeterministicSymbolGenerator().generate(ir, GeneratorContext())
    assert artifact.artifact_type == "SYMBOL"


def test_symbol_artifact_preserves_ir_pin_numbers():
    ir, _ = _inputs()
    artifact = serialize_symbol(ir, SymbolContext())
    text = artifact.content.decode("utf-8")
    assert '(number "1"' in text
    assert '(number "2"' in text
    unit_start = text.index('(symbol "TEST-R-0402_1_1"')
    assert unit_start < text.index("(pin passive line", unit_start)
    assert validate_symbol_artifact(artifact, ir) == ()
