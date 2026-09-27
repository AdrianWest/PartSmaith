"""Deterministic KiCad symbol generation and symbol dependency projections."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from partsmith.ir.canonical import canonical_json
from partsmith.ir.errors import Issue
from partsmith.ir.model import normalize_ir
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
        self, ir: dict, context: SymbolContext
    ) -> GeneratedArtifact: ...


def validate_symbol_inputs(ir: dict, pdl: PDL) -> tuple[Issue, ...]:
    """Validate IR and its package compatibility before symbol generation."""
    issues = list(ir_pdl_issues(ir, pdl.data))
    try:
        normalize_ir(ir)
    except ValueError as error:
        issues.append(Issue("", "IR_INPUT", str(error)))
    return tuple(sorted(set(issues)))


def symbol_projection(ir: dict, context: SymbolContext) -> dict:
    """Project only IR and trusted symbol configuration."""
    data = normalize_ir(ir)
    return {
        "snapshot_profile": "1.2",
        "node_kind": "SYMBOL",
        "declaration": {
            "id": "partsmith.symbol",
            "version": context.generator_version,
        },
        "configuration": {
            "generator_version": context.generator_version,
            "serializer_version": context.serializer_version,
            "target_format": context.target_format,
            "conventions_version": context.conventions_version,
            "naming_version": context.naming_version,
            "assignment_version": context.assignment_version,
        },
        "inputs": {
            "identity": data["identity"],
            "electrical": data["electrical"],
            "pins": data["pins"],
            "symbol": data["symbol"],
        },
    }


def symbol_dependency_hash(ir: dict, context: SymbolContext) -> str:
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


def serialize_symbol(ir: dict, context: SymbolContext) -> GeneratedArtifact:
    """Serialize a deterministic single-unit resistor-style KiCad symbol."""
    data = normalize_ir(ir)
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
            "    )",
            *pin_blocks,
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
    artifact: GeneratedArtifact, ir: dict
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
    expected = {pin["number"] for pin in normalize_ir(ir)["pins"]}
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
