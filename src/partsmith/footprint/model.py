"""

@package src.partsmith.footprint.model
@brief Deterministic KiCad footprint generation and dependency projections.
@details Provides the module implementation and public interfaces.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from partsmith.ir.canonical import canonical_json
from partsmith.ir.errors import Issue
from partsmith.ir.model import ComponentIR, normalize_ir
from partsmith.pdl import PDL, ir_pdl_issues

_PAD_SHAPES = {
    "rect": "rect",
    "roundrect": "roundrect",
    "circle": "circle",
    "oval": "oval",
}


@dataclass(frozen=True)
class FootprintContext:
    """Trusted, footprint-only generator configuration."""

    generator_version: str = "1.0"
    serializer_version: str = "1.0"
    target_format: str = "kicad_mod"
    conventions_version: str = "1.0"
    naming_version: str = "1.0"
    python_version: str = "3.12"
    configuration_schema_version: str = "1.0"
    required_ir_paths: tuple[str, ...] = (
        "/identity",
        "/package",
        "/pins",
        "/footprint",
    )
    required_pdl_paths: tuple[str, ...] = (
        "/identity",
        "/topology",
        "/land_pattern",
    )
    required_configuration_paths: tuple[str, ...] = (
        "/generator_version",
        "/serializer_version",
        "/target_format",
        "/conventions_version",
        "/naming_version",
    )


GeneratorContext = FootprintContext


@dataclass(frozen=True)
class GeneratedArtifact:
    """Deterministic generated artifact with exact byte identity.

    Attributes:
        artifact_type: The generated artifact kind.
        filename: The deterministic artifact filename.
        content: The serialized artifact bytes.
        source_hash: The canonical normalized IR hash.
        dependency_hash: The consumed-input dependency hash.
        generator_version: The generator version used for serialization.
        association_dependency_hash: The separate association-input hash.
    """

    artifact_type: str
    filename: str
    content: bytes
    source_hash: str
    dependency_hash: str
    generator_version: str
    association_dependency_hash: str | None = None

    @property
    def sha256(self) -> str:
        """

        @brief Return the SHA-256 digest of the serialized artifact bytes.
        @return The str result.
        @details Implements the documented behavior without changing the public
        contract.

        """

        return sha256(self.content).hexdigest()


class FootprintGenerator(Protocol):
    """@brief Defines the footprint-generation interface.
    @details Implementations serialize a footprint from IR, PDL, and context.
    """

    def generate(
        self, ir: ComponentIR, pdl: PDL, context: FootprintContext
    ) -> GeneratedArtifact:
        """

        @brief Generate a deterministic footprint artifact.
        @param ir The ir argument.
        @param pdl The pdl argument.
        @param context The context argument.
        @return The GeneratedArtifact result.
        @details Implements the documented behavior without changing the public
        contract.

        """


class DeterministicFootprintGenerator:
    """Concrete Phase 5 footprint generator implementation."""

    def generate(
        self, ir: ComponentIR, pdl: PDL, context: FootprintContext
    ) -> GeneratedArtifact:
        """

        @brief Generate a deterministic footprint artifact from IR and PDL.
        @param ir The ir argument.
        @param pdl The pdl argument.
        @param context The context argument.
        @return The GeneratedArtifact result.
        @details Implements the documented behavior without changing the public
        contract.

        """

        return serialize_footprint(ir, pdl, context)


def _ir_data(ir: ComponentIR | dict) -> dict:
    """

    @brief Return the mutable data mapping represented by an IR input.
    @param ir The ir argument.
    @return The dict result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    return ir.data if isinstance(ir, ComponentIR) else ir


def validate_footprint_inputs(
    ir: ComponentIR | dict, pdl: PDL
) -> tuple[Issue, ...]:
    """

    @brief Validate IR and package compatibility before footprint generation.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @return The tuple[Issue, ...] result.
    @details Implements the documented behavior without changing the public
    contract.

    """

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
    for group_index, group in enumerate(pdl.data["land_pattern"]["groups"]):
        for shape_index, shape in enumerate(group["shapes"]):
            try:
                _pad_shape(shape["shape"])
            except ValueError as error:
                issues.append(
                    Issue(
                        f"/land_pattern/groups/{group_index}/shapes/"
                        f"{shape_index}/shape",
                        "FOOTPRINT_SHAPE",
                        str(error),
                    )
                )
    return tuple(sorted(set(issues)))


def _land_pattern_provenance(ir_data: dict, pdl_data: dict) -> dict:
    """

    @brief Collects source records for the selected land pattern.
    @param ir_data Normalized component IR data.
    @param pdl_data Validated PDL data.
    @return The land-pattern provenance mapping.
    @details Retains PDL sources and IR evidence page references.

    """
    evidence = {item["id"]: item for item in ir_data["evidence"]}
    evidence_sources = []
    for evidence_id in ir_data["footprint"].get("evidence_ids", []):
        item = evidence.get(evidence_id)
        if item is None:
            continue
        source = item["source"]
        evidence_sources.append(
            {
                "evidence_id": evidence_id,
                "document_id": source["document_id"],
                "page": source["page"],
            }
        )
    return {
        "land_pattern_source": ir_data["footprint"]["land_pattern_source"],
        "ir_evidence": evidence_sources,
        "pdl_sources": pdl_data["sources"],
    }


def footprint_projection(
    ir: ComponentIR | dict, pdl: PDL, context: FootprintContext
) -> dict:
    """

    @brief Project IR, PDL land-pattern data, and trusted CAD configuration.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The dict result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    data = normalize_ir(_ir_data(ir))
    pdl_data = pdl.data
    identity = {
        key: value
        for key, value in data["identity"].items()
        if key != "component_id"
    }
    return {
        "snapshot_profile": "1.2",
        "node_kind": "FOOTPRINT",
        "declaration": {
            "id": "partsmith.footprint",
            "version": context.generator_version,
            "configuration_schema_version": (
                context.configuration_schema_version
            ),
            "required_ir_paths": list(context.required_ir_paths),
            "required_pdl_paths": list(context.required_pdl_paths),
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
        },
        "inputs": {
            "identity": identity,
            "package": data["package"],
            "pins": data["pins"],
            "footprint": data["footprint"],
            "pdl": {
                "identity": pdl_data["identity"],
                "topology": pdl_data["topology"],
                "land_pattern": pdl_data["land_pattern"],
            },
            "provenance": _land_pattern_provenance(data, pdl_data),
        },
    }


def footprint_dependency_hash(
    ir: ComponentIR | dict, pdl: PDL, context: FootprintContext
) -> str:
    """

    @brief Hash the canonical footprint-only profile-1.2 projection.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The str result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    projection = footprint_projection(ir, pdl, context)
    consumed_inputs = {
        "snapshot_profile": projection["snapshot_profile"],
        "node_kind": projection["node_kind"],
        "inputs": projection["inputs"],
    }
    return sha256(canonical_json(consumed_inputs)).hexdigest()


def association_dependency_hash(ir: ComponentIR | dict) -> str:
    """

    @brief Hash symbol-association inputs separately from footprint geometry.
    @param ir The ir argument.
    @return The str result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    data = normalize_ir(_ir_data(ir))
    association = {
        "symbol": data["symbol"],
        "pin_numbers": [pin["number"] for pin in data["pins"]],
        "model_3d": data["model_3d"],
    }
    return sha256(canonical_json(association)).hexdigest()


def _quote(value: str) -> str:
    """

    @brief Quote a KiCad string value with escaped special characters.
    @param value The value argument.
    @return The str result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _fmt(value: Decimal | float | int) -> str:
    """

    @brief Format a numeric coordinate or dimension for KiCad output.
    @param value The value argument.
    @return The str result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    return f"{value:g}"


def _pad_shape(shape: str) -> str:
    """

    @brief Maps a PDL pad shape to its KiCad shape name.
    @param shape PDL land-pattern shape name.
    @return The KiCad pad shape name.
    @details Raises ValueError for unsupported Phase 5 pad shapes.

    """
    try:
        return _PAD_SHAPES[shape.lower()]
    except KeyError as error:
        raise ValueError(f"Unsupported Phase 5 pad shape: {shape}") from error


def _fp_rect(
    layer: str,
    start: tuple[Decimal | float | int, Decimal | float | int],
    end: tuple[Decimal | float | int, Decimal | float | int],
) -> str:
    """

    @brief Serialize a rectangular footprint graphic on one KiCad layer.
    @param layer The layer argument.
    @param start The start argument.
    @param end The end argument.
    @return The str result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    return "\n".join(
        (
            f"  (fp_rect (start {_fmt(start[0])} {_fmt(start[1])}) "
            f"(end {_fmt(end[0])} {_fmt(end[1])})",
            f"    (stroke (width 0.05) (type default)) (fill none) "
            f"(layer {_quote(layer)})",
            "  )",
        )
    )


def _courtyard(pdl_data: dict) -> tuple:
    """@brief Computes the versioned engineering courtyard bounds.
    @param pdl_data Validated PDL document.
    @return Minimum X/Y followed by maximum X/Y in native KiCad coordinates.
    @details PDL 1.1 encloses body and copper with a 0.25 mm fixture margin;
    historical PDL 1.0 retains its frozen body-only 0.05 mm convention.
    """
    body = pdl_data["mechanical"]["body"]
    x = body["length"]["nominal_mm"] / 2
    y = body["width"]["nominal_mm"] / 2
    bounds = [-x, -y, x, y]
    margin = Decimal("0.05")
    if pdl_data["schema_version"] == "1.1":
        margin = Decimal("0.25")
        for group in pdl_data["land_pattern"]["groups"]:
            for shape in group["shapes"]:
                px, py = shape["center_mm"]
                w, h = shape["size_mm"]
                bounds = [
                    min(bounds[0], px - w / 2),
                    min(bounds[1], -py - h / 2),
                    max(bounds[2], px + w / 2),
                    max(bounds[3], -py + h / 2),
                ]
    return (
        bounds[0] - margin,
        bounds[1] - margin,
        bounds[2] + margin,
        bounds[3] + margin,
    )


def serialize_footprint(
    ir: ComponentIR | dict, pdl: PDL, context: FootprintContext
) -> GeneratedArtifact:
    """

    @brief Serialize PDL land-pattern groups as a deterministic KiCad
    footprint.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The GeneratedArtifact result.
    @details PDL 1.1 explicitly converts engineering upward Y to native KiCad
    downward Y and encloses the complete body and land pattern in a courtyard.
    PDL 1.0 bytes preserve their historical serializer convention.

    """

    data = normalize_ir(_ir_data(ir))
    pdl_data = pdl.data
    name = data["identity"]["normalized_mpn"]
    body = pdl_data["mechanical"]["body"]
    land_pattern = pdl_data["land_pattern"]
    provenance = _land_pattern_provenance(data, pdl_data)
    references = ", ".join(
        source["reference"] for source in provenance["pdl_sources"]
    )
    pages = (
        ", ".join(
            str(item["page"])
            for item in provenance["ir_evidence"]
            if item["page"] is not None
        )
        or "not recorded"
    )
    description = (
        f"Land pattern source: {provenance['land_pattern_source']}; "
        f"references: {references}; page(s): {pages}"
    )
    tags = f"{data['package']['family']} {data['package']['variant']}"
    courtyard = _courtyard(pdl_data)
    label_top, label_bottom = Decimal("-1.2"), Decimal("1.2")
    if pdl_data["schema_version"] == "1.1":
        label_top, label_bottom = courtyard[1] - 1, courtyard[3] + 1
    pads = []
    for group in land_pattern["groups"]:
        for shape in group["shapes"]:
            x, y = shape["center_mm"]
            if pdl_data["schema_version"] == "1.1":
                y = -y
            width, height = shape["size_mm"]
            pad_shape = _pad_shape(shape["shape"])
            pad = [
                f"  (pad {_quote(group['terminal_number'])} smd {pad_shape} "
                f"(at {_fmt(x)} {_fmt(y)}) "
                f"(size {_fmt(width)} {_fmt(height)})",
                '    (layers "F.Cu" "F.Paste" "F.Mask")',
            ]
            if pad_shape == "roundrect":
                pad.append("    (roundrect_rratio 0.2)")
            pad.append("  )")
            pads.append("\n".join(pad))
    half_length = body["length"]["nominal_mm"] / 2
    half_width = body["width"]["nominal_mm"] / 2
    content = "\n".join(
        (
            f"(footprint {_quote(name)}",
            "  (version 20240108)",
            "  (generator partsmith)",
            f"  (descr {_quote(description)})",
            f"  (tags {_quote(tags)})",
            *[
                f"  (property {_quote(key)} {_quote(str(value))})"
                for key, value in sorted(
                    data["footprint"]["properties"].items()
                )
            ],
            f"  (fp_text reference "
            f"{_quote(data['symbol']['reference_prefix'] + '?')} "
            f'(at 0 {_fmt(label_top)}) (layer "F.SilkS")',
            "    (effects (font (size 1 1) (thickness 0.15)))",
            "  )",
            f"  (fp_text value {_quote(name)} "
            f'(at 0 {_fmt(label_bottom)}) (layer "F.Fab")',
            "    (effects (font (size 1 1) (thickness 0.15)))",
            "  )",
            _fp_rect(
                "F.CrtYd",
                courtyard[:2],
                courtyard[2:],
            ),
            _fp_rect(
                "F.Fab", (-half_length, -half_width), (half_length, half_width)
            ),
            *pads,
            ")",
            "",
        )
    ).encode("utf-8")
    return GeneratedArtifact(
        artifact_type="FOOTPRINT",
        filename=f"{name}.kicad_mod",
        content=content,
        source_hash=sha256(canonical_json(data)).hexdigest(),
        dependency_hash=footprint_dependency_hash(data, pdl, context),
        generator_version=context.generator_version,
        association_dependency_hash=association_dependency_hash(data),
    )


def validate_footprint_artifact(
    artifact: GeneratedArtifact, ir: ComponentIR | dict, pdl: PDL
) -> tuple[Issue, ...]:
    """

    @brief Check syntax, pad mapping, courtyard, and required graphics.
    @param artifact The artifact argument.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @return The tuple[Issue, ...] result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    data = normalize_ir(_ir_data(ir))
    pdl_data = pdl.data
    text = artifact.content.decode("utf-8")
    issues = []
    if text.count("(") != text.count(")"):
        issues.append(
            Issue("/artifact", "FOOTPRINT_SYNTAX", "Unbalanced KiCad syntax")
        )
    if not text.startswith(
        f"(footprint {_quote(data['identity']['normalized_mpn'])}\n"
    ) or not text.rstrip().endswith(")"):
        issues.append(
            Issue("/artifact", "FOOTPRINT_FORMAT", "Invalid footprint wrapper")
        )
    for marker in ("(version 20240108)", "(generator partsmith)"):
        if marker not in text:
            issues.append(
                Issue(
                    "/artifact",
                    "FOOTPRINT_FORMAT",
                    f"Missing required format marker {marker}",
                )
            )

    expected = []
    for group in pdl_data["land_pattern"]["groups"]:
        for shape in group["shapes"]:
            try:
                shape_name = _pad_shape(shape["shape"])
            except ValueError as error:
                issues.append(
                    Issue("/land_pattern", "FOOTPRINT_SHAPE", str(error))
                )
                continue
            expected.append(
                (
                    group["terminal_number"],
                    shape_name,
                    str(shape["center_mm"][0]),
                    str(
                        -shape["center_mm"][1]
                        if pdl_data["schema_version"] == "1.1"
                        else shape["center_mm"][1]
                    ),
                    *(str(value) for value in shape["size_mm"]),
                    "F.Cu",
                    "F.Paste",
                    "F.Mask",
                )
            )
    pad_pattern = re.compile(
        r'\(pad "([^"]+)" smd (\w+) \(at ([^ ]+) ([^)]+)\) '
        r'\(size ([^ ]+) ([^)]+)\)\s+\(layers "([^"]+)" '
        r'"([^"]+)" "([^"]+)"\)',
        re.MULTILINE,
    )
    actual = [match.groups() for match in pad_pattern.finditer(text)]
    if actual != expected:
        issues.append(
            Issue(
                "/artifact",
                "FOOTPRINT_PADS",
                "Pad number, geometry, or layers do not match PDL",
            )
        )
    if data["package"]["pin_count"] != len(actual):
        issues.append(
            Issue(
                "/package/pin_count",
                "FOOTPRINT_PADS",
                "Pad count does not match IR",
            )
        )

    expected_courtyard = _courtyard(pdl_data)
    courtyard_pattern = re.compile(
        r"\(fp_rect \(start ([-\d.]+) ([-\d.]+)\) "
        r"\(end ([-\d.]+) ([-\d.]+)\).*?"
        r'\(layer "F.CrtYd"\)',
        re.DOTALL,
    )
    courtyard = courtyard_pattern.search(text)
    if courtyard is None:
        issues.append(
            Issue("/artifact", "FOOTPRINT_COURTYARD", "Missing courtyard")
        )
    else:
        actual_courtyard = tuple(
            Decimal(value) for value in courtyard.groups()
        )
        if actual_courtyard != expected_courtyard:
            issues.append(
                Issue(
                    "/artifact",
                    "FOOTPRINT_COURTYARD",
                    "Courtyard does not match PDL body bounds",
                )
            )
    for marker in (
        '(layer "F.CrtYd")',
        '(layer "F.Fab")',
        '(layer "F.SilkS")',
        "(descr ",
    ):
        if marker not in text:
            issues.append(
                Issue(
                    "/artifact",
                    "FOOTPRINT_GRAPHICS",
                    f"Missing required layer {marker}",
                )
            )
    return tuple(sorted(set(issues)))
