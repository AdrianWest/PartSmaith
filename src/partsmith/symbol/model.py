"""Deterministic KiCad symbol generation and symbol dependency projections."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from partsmith.ir.canonical import canonical_json
from partsmith.ir.errors import Issue
from partsmith.ir.model import ComponentIR, normalize_ir
from partsmith.pdl import PDL, ir_pdl_issues


@dataclass(frozen=True)
class SymbolContext:
    """Trusted, symbol-only generator configuration."""

    generator_version: str = "1.0"
    serializer_version: str = "1.0"
    target_format: str = "kicad_sym"
    conventions_version: str = "1.0"
    naming_version: str = "1.0"
    assignment_version: str = "1.0"
    python_version: str = "3.12"
    configuration_schema_version: str = "1.0"
    required_ir_paths: tuple[str, ...] = (
        "/identity",
        "/electrical",
        "/pins",
        "/symbol",
    )
    required_configuration_paths: tuple[str, ...] = (
        "/generator_version",
        "/serializer_version",
        "/target_format",
        "/conventions_version",
        "/naming_version",
        "/assignment_version",
    )


GeneratorContext = SymbolContext


@dataclass(frozen=True)
class GeneratedArtifact:
    """Deterministic generated artifact with exact byte identity."""

    artifact_type: str
    filename: str
    content: bytes
    source_hash: str
    dependency_hash: str
    generator_version: str

    @property
    def sha256(self) -> str:
        return sha256(self.content).hexdigest()


class SymbolGenerator(Protocol):
    def generate(
        self, ir: ComponentIR, context: SymbolContext
    ) -> GeneratedArtifact: ...


class DeterministicSymbolGenerator:
    """Concrete Phase 4 symbol generator implementation."""

    def generate(
        self, ir: ComponentIR, context: SymbolContext
    ) -> GeneratedArtifact:
        return serialize_symbol(ir, context)


def _ir_data(ir: ComponentIR | dict) -> dict:
    return ir.data if isinstance(ir, ComponentIR) else ir


def validate_symbol_inputs(
    ir: ComponentIR | dict, pdl: PDL
) -> tuple[Issue, ...]:
    """Validate IR and its package compatibility before symbol generation."""
    try:
        data = normalize_ir(_ir_data(ir))
    except ValueError as error:
        return tuple(
            sorted(
                set(
                    getattr(
                        error,
                        "issues",
                        (Issue("", "IR_INPUT", str(error)),),
                    )
                )
            )
        )
    issues = list(ir_pdl_issues(data, pdl.data))
    return tuple(sorted(set(issues)))


def symbol_projection(ir: ComponentIR | dict, context: SymbolContext) -> dict:
    """Project only IR and trusted symbol configuration."""
    data = normalize_ir(_ir_data(ir))
    identity = {
        key: value
        for key, value in data["identity"].items()
        if key != "component_id"
    }
    return {
        "snapshot_profile": "1.2",
        "node_kind": "SYMBOL",
        "declaration": {
            "id": "partsmith.symbol",
            "version": context.generator_version,
            "configuration_schema_version": (
                context.configuration_schema_version
            ),
            "required_ir_paths": list(context.required_ir_paths),
            "required_configuration_paths": list(
                context.required_configuration_paths
            ),
        },
        "configuration": {
            "python_version": context.python_version,
            "generator_version": context.generator_version,
            "serializer_version": context.serializer_version,
            "target_format": context.target_format,
            "conventions_version": context.conventions_version,
            "naming_version": context.naming_version,
            "assignment_version": context.assignment_version,
        },
        "inputs": {
            "identity": identity,
            "electrical": data["electrical"],
            "pins": data["pins"],
            "symbol": data["symbol"],
        },
    }


def symbol_dependency_hash(
    ir: ComponentIR | dict, context: SymbolContext
) -> str:
    """Hash the canonical symbol-only profile-1.2 projection."""
    return sha256(canonical_json(symbol_projection(ir, context))).hexdigest()


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _pin(number: str, name: str, electrical_type: str, x: int) -> str:
    return "\n".join(
        (
            f"      (pin {electrical_type} line (at {x} 0 0) (length 2.54)",
            f"        (name {_quote(name)} (effects (font (size 1.27 1.27))))",
            f"        (number {_quote(number)} (effects "
            f"(font (size 1.27 1.27))))",
            "      )",
        )
    )


def serialize_symbol(
    ir: ComponentIR | dict, context: SymbolContext
) -> GeneratedArtifact:
    """Serialize a deterministic single-unit resistor-style KiCad symbol."""
    data = normalize_ir(_ir_data(ir))
    pins = data["pins"]
    reference = data["symbol"]["reference_prefix"]
    value = data["identity"]["mpn"]
    symbol_name = data["identity"]["normalized_mpn"]
    pin_blocks = []
    for index, pin in enumerate(pins):
        x = -2.54 if index % 2 == 0 else 2.54
        pin_blocks.append(
            _pin(pin["number"], pin["name"], pin["electrical_type"], x)
        )
    content = "\n".join(
        (
            "(kicad_symbol_lib",
            "  (version 20231120)",
            "  (generator kicad_symbol_editor)",
            f"  (symbol {_quote(symbol_name)}",
            f'    (property "Reference" {_quote(reference)})',
            f'    (property "Value" {_quote(value)})',
            "    (symbol " + _quote(symbol_name + "_1_1"),
            "      (rectangle (start -1.27 1.27) (end 1.27 -1.27)",
            "        (stroke (width 0) (type default))",
            "        (fill (type none))",
            "      )",
            *pin_blocks,
            "    )",
            "  )",
            ")",
            "",
        )
    ).encode("utf-8")
    return GeneratedArtifact(
        artifact_type="SYMBOL",
        filename=f"{symbol_name}.kicad_sym",
        content=content,
        source_hash=sha256(canonical_json(data)).hexdigest(),
        dependency_hash=symbol_dependency_hash(data, context),
        generator_version=context.generator_version,
    )


def validate_symbol_artifact(
    artifact: GeneratedArtifact, ir: ComponentIR | dict
) -> tuple[Issue, ...]:
    """Check deterministic symbol syntax and exact physical pin numbering."""
    issues = []
    text = artifact.content.decode("utf-8")
    if text.count("(") != text.count(")"):
        issues.append(
            Issue(
                "/artifact", "SYMBOL_SYNTAX", "Unbalanced KiCad symbol syntax"
            )
        )
    expected = {pin["number"] for pin in normalize_ir(_ir_data(ir))["pins"]}
    actual = set()
    for line in text.splitlines():
        if line.strip().startswith("(number "):
            actual.add(line.strip().split('"')[1])
    if actual != expected:
        issues.append(
            Issue(
                "/artifact",
                "SYMBOL_PINS",
                "Symbol pin numbers do not match IR",
            )
        )
    return tuple(sorted(set(issues)))
