"""

@package src.partsmith.threed.model
@brief Deterministic CadQuery/OCP/OCCT 3D generation, snapshot-
profile-1.2 dependency hashing, and STEP dimensional validation.
@details Provides the module implementation and public interfaces.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from partsmith.ir.canonical import canonical_json
from partsmith.ir.errors import Issue
from partsmith.ir.model import ComponentIR, normalize_ir
from partsmith.pdl import PDL, ir_pdl_issues
from partsmith.threed.step_backend import (
    CADQUERY_VERSION,
    OCP_VERSION,
    generate_step_bytes,
    measure_step,
)

_SUPPORTED_BODY_STRATEGY = "CHIP_BODY"
_SUPPORTED_LEAD_STRATEGY = "END_TERMINATIONS"
_SUPPORTED_MARKER_STRATEGY = "NONE"


@dataclass(frozen=True)
class ThreeDContext:
    """Trusted, 3D-only generator configuration."""

    generator_version: str = "1.0"
    backend_name: str = "cadquery"
    backend_version: str = CADQUERY_VERSION
    ocp_version: str = OCP_VERSION
    target_format: str = "step"
    conventions_version: str = "1.0"
    python_version: str = "3.12"
    step_precision_mode: int = 0
    configuration_schema_version: str = "1.0"
    required_ir_paths: tuple[str, ...] = ("/identity", "/package")
    required_pdl_paths: tuple[str, ...] = (
        "/identity",
        "/mechanical",
        "/model_3d",
        "/reference_features",
    )
    required_configuration_paths: tuple[str, ...] = (
        "/generator_version",
        "/backend_name",
        "/backend_version",
        "/ocp_version",
        "/target_format",
        "/conventions_version",
    )


@dataclass(frozen=True)
class GeneratedArtifact:
    """Deterministic generated STEP artifact with exact byte identity.

    Attributes:
        artifact_type: The generated artifact kind.
        filename: The deterministic artifact filename.
        content: The serialized STEP artifact bytes.
        source_hash: The canonical normalized IR hash.
        dependency_hash: The consumed-input dependency hash.
        generator_version: The generator version used for export.
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
        @details Implements the documented behavior without changing the
        public contract.

        """
        return sha256(self.content).hexdigest()


class ThreeDGenerator(Protocol):
    """@brief Defines the 3D model generation interface.
    @details Implementations generate STEP artifacts independently of
    footprints.
    """

    def generate(
        self, ir: ComponentIR, pdl: PDL, context: ThreeDContext
    ) -> GeneratedArtifact:
        """

        @brief Generate a deterministic 3D STEP artifact.
        @param ir The ir argument.
        @param pdl The pdl argument.
        @param context The context argument.
        @return The GeneratedArtifact result.
        @details Implements the documented behavior without changing
        the public contract.

        """


def _ir_data(ir: ComponentIR | dict) -> dict:
    """

    @brief Return the mutable data mapping represented by an IR input.
    @param ir The ir argument.
    @return The dict result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return ir.data if isinstance(ir, ComponentIR) else ir


def validate_threed_inputs(
    ir: ComponentIR | dict, pdl: PDL
) -> tuple[Issue, ...]:
    """

    @brief Validate IR/PDL compatibility and 3D-strategy support.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @return The tuple[Issue, ...] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    try:
        data = normalize_ir(_ir_data(ir))
    except ValueError as error:
        return tuple(
            sorted(
                set(
                    getattr(
                        error, "issues", (Issue("", "IR_INPUT", str(error)),)
                    )
                )
            )
        )
    issues = list(ir_pdl_issues(data, pdl.data))
    model_3d = pdl.data["model_3d"]
    if model_3d["body_strategy"] != _SUPPORTED_BODY_STRATEGY:
        issues.append(
            Issue(
                "/model_3d/body_strategy",
                "THREED_STRATEGY",
                f"Unsupported body_strategy: {model_3d['body_strategy']}",
            )
        )
    if model_3d["lead_strategy"] != _SUPPORTED_LEAD_STRATEGY:
        issues.append(
            Issue(
                "/model_3d/lead_strategy",
                "THREED_STRATEGY",
                f"Unsupported lead_strategy: {model_3d['lead_strategy']}",
            )
        )
    if model_3d["marker_strategy"] != _SUPPORTED_MARKER_STRATEGY:
        issues.append(
            Issue(
                "/model_3d/marker_strategy",
                "THREED_STRATEGY",
                f"Unsupported marker_strategy: {model_3d['marker_strategy']}",
            )
        )
    return tuple(sorted(set(issues)))


def threed_projection(
    ir: ComponentIR | dict, pdl: PDL, context: ThreeDContext
) -> dict:
    """

    @brief Project IR package/PDL 3D geometry data and trusted CAD
    configuration.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The dict result.
    @details Excludes `ir.model_3d.placement`: placement-only edits
    must preserve the canonical STEP dependency hash. CAD backend/
    runtime versions are consumed inputs and do invalidate it.

    """
    data = normalize_ir(_ir_data(ir))
    pdl_data = pdl.data
    identity = {
        key: value
        for key, value in data["identity"].items()
        if key != "component_id"
    }
    result = {
        "snapshot_profile": "1.2",
        "node_kind": "MODEL_3D",
        "declaration": {
            "id": "partsmith.threed",
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
            "backend_name": context.backend_name,
            "backend_version": context.backend_version,
            "ocp_version": context.ocp_version,
            "target_format": context.target_format,
            "conventions_version": context.conventions_version,
        },
        "inputs": {
            "identity": identity,
            "package": data["package"],
            "pdl": {
                "identity": pdl_data["identity"],
                "mechanical": pdl_data["mechanical"],
                "model_3d": pdl_data["model_3d"],
                "reference_features": pdl_data["reference_features"],
                "coordinate_system": pdl_data["coordinate_system"],
            },
        },
    }
    if context.step_precision_mode != 0:
        result["configuration"]["step_precision_mode"] = (
            context.step_precision_mode
        )
    return result


def threed_dependency_hash(
    ir: ComponentIR | dict, pdl: PDL, context: ThreeDContext
) -> str:
    """

    @brief Hash the canonical 3D-only profile-1.2 projection.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The str result.
    @details Includes `configuration` (backend/runtime versions) unlike
    the footprint dependency hash: section 6 requires CAD backend/
    runtime settings to invalidate the 3D dependency, while placement
    (association-only) and validator tolerances stay excluded from
    `inputs`.

    """
    projection = threed_projection(ir, pdl, context)
    consumed_inputs = {
        "snapshot_profile": projection["snapshot_profile"],
        "node_kind": projection["node_kind"],
        "configuration": projection["configuration"],
        "inputs": projection["inputs"],
    }
    return sha256(canonical_json(consumed_inputs)).hexdigest()


def generate_model_3d(
    ir: ComponentIR | dict, pdl: PDL, context: ThreeDContext
) -> GeneratedArtifact:
    """

    @brief Generate a deterministic STEP artifact from IR and PDL.
    @param ir The ir argument.
    @param pdl The pdl argument.
    @param context The context argument.
    @return The GeneratedArtifact result.
    @details Raises ValueError when IR/PDL fail
    `validate_threed_inputs`.

    """
    issues = validate_threed_inputs(ir, pdl)
    if issues:
        raise ValueError(
            "; ".join(
                f"{i.code} at {i.path or '/'}: {i.message}" for i in issues
            )
        )
    data = normalize_ir(_ir_data(ir))
    identity = data["identity"]
    content = generate_step_bytes(
        pdl.data, precision_mode=context.step_precision_mode
    )
    source_hash = sha256(canonical_json(data)).hexdigest()
    dependency_hash = threed_dependency_hash(ir, pdl, context)
    filename = f"{identity['normalized_mpn'].upper()}.step"
    return GeneratedArtifact(
        artifact_type="MODEL_3D",
        filename=filename,
        content=content,
        source_hash=source_hash,
        dependency_hash=dependency_hash,
        generator_version=context.generator_version,
    )


class DeterministicThreeDGenerator:
    """Concrete Phase 6 CadQuery 3D generator implementation."""

    def generate(
        self, ir: ComponentIR | dict, pdl: PDL, context: ThreeDContext
    ) -> GeneratedArtifact:
        """

        @brief Generate a deterministic STEP artifact from IR and PDL.
        @param ir The ir argument.
        @param pdl The pdl argument.
        @param context The context argument.
        @return The GeneratedArtifact result.
        @details Implements the documented behavior without changing
        the public contract.

        """
        return generate_model_3d(ir, pdl, context)


def validate_step_artifact(step_bytes: bytes, pdl: PDL) -> tuple[Issue, ...]:
    """

    @brief Validate a STEP artifact's dimensions and reference
    geometry against PDL tolerances (section 147).
    @param step_bytes The step_bytes argument.
    @param pdl The pdl argument.
    @return The tuple[Issue, ...] result.
    @details Checks parseability, solid count, body dimensions,
    body/mounting-plane position, and each declared terminal anchor
    position, all against the package-specific tolerances in
    `pdl.data["validation"]["tolerances"]`.

    """
    pdl_data = pdl.data
    try:
        measurement = measure_step(step_bytes)
    except ValueError as error:
        return (Issue("", "STEP_PARSE", str(error)),)

    issues: list[Issue] = []
    tolerances = pdl_data["validation"]["tolerances"]
    body_tolerance = float(tolerances["BODY"]["value"])
    height_tolerance = float(tolerances["HEIGHT"]["value"])
    position_tolerance = float(tolerances["POSITION"]["value"])

    terminal_features = sorted(
        (
            feature
            for feature in pdl_data["reference_features"]
            if feature["kind"] == "TERMINAL_ANCHOR"
            and feature["applicability"] == "REQUIRED"
        ),
        key=lambda feature: feature["terminal_id"],
    )
    expected_solid_count = 1 + len(terminal_features)
    if measurement.solid_count != expected_solid_count:
        issues.append(
            Issue(
                "/model_3d",
                "STEP_SOLID_COUNT",
                f"Expected {expected_solid_count} solids, measured "
                f"{measurement.solid_count}",
            )
        )
        return tuple(issues)

    body_solid = max(
        measurement.solids,
        key=lambda solid: (
            solid.size_mm[0] * solid.size_mm[1] * solid.size_mm[2]
        ),
    )
    body = pdl_data["mechanical"]["body"]
    expected_body_size = (
        float(body["length"]["nominal_mm"]),
        float(body["width"]["nominal_mm"]),
        float(body["height"]["nominal_mm"]),
    )
    for axis, name, tolerance in (
        (0, "length", body_tolerance),
        (1, "width", body_tolerance),
        (2, "height", height_tolerance),
    ):
        delta = abs(body_solid.size_mm[axis] - expected_body_size[axis])
        if delta > tolerance:
            issues.append(
                Issue(
                    f"/mechanical/body/{name}",
                    "STEP_DIMENSION",
                    f"Measured {name} {body_solid.size_mm[axis]:.6f}mm "
                    f"differs from {expected_body_size[axis]:.6f}mm by "
                    f"more than {tolerance:.6f}mm",
                )
            )

    body_center_feature = next(
        feature
        for feature in pdl_data["reference_features"]
        if feature["kind"] == "BODY_CENTER"
    )
    expected_body_center = tuple(
        float(value) for value in body_center_feature["anchor_mm"]
    )
    for axis, label in enumerate(("x", "y", "z")):
        delta = abs(body_solid.center_mm[axis] - expected_body_center[axis])
        if delta > position_tolerance:
            issues.append(
                Issue(
                    f"/reference_features/BODY-CENTER/anchor_mm/{axis}",
                    "STEP_POSITION",
                    f"Measured body center {label}="
                    f"{body_solid.center_mm[axis]:.6f}mm differs from "
                    f"{expected_body_center[axis]:.6f}mm by more than "
                    f"{position_tolerance:.6f}mm",
                )
            )

    remaining_solids = [
        solid for solid in measurement.solids if solid is not body_solid
    ]
    for feature in terminal_features:
        expected_center = tuple(float(value) for value in feature["anchor_mm"])
        nearest = min(
            remaining_solids,
            key=lambda solid: sum(
                (solid.center_mm[axis] - expected_center[axis]) ** 2
                for axis in range(3)
            ),
        )
        for axis, label in enumerate(("x", "y", "z")):
            delta = abs(nearest.center_mm[axis] - expected_center[axis])
            if delta > position_tolerance:
                issues.append(
                    Issue(
                        f"/reference_features/{feature['id']}/anchor_mm/{axis}",
                        "STEP_POSITION",
                        f"Measured terminal center {label}="
                        f"{nearest.center_mm[axis]:.6f}mm differs from "
                        f"{expected_center[axis]:.6f}mm by more than "
                        f"{position_tolerance:.6f}mm",
                    )
                )
    return tuple(issues)
