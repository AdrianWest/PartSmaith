"""

@package tests.test_footprint
@brief Phase 5 deterministic footprint-generation gate tests.
@details Provides the module implementation and public interfaces.
"""

from pathlib import Path

from partsmith.footprint import (
    DeterministicFootprintGenerator,
    FootprintContext,
    association_dependency_hash,
    footprint_dependency_hash,
    serialize_footprint,
    validate_footprint_artifact,
    validate_footprint_inputs,
)
from partsmith.ir.canonical import parse_json
from partsmith.ir.model import ComponentIR
from partsmith.pdl import load_pdl, pdl_hash

ROOT = Path(__file__).parents[1]
IR_PATH = ROOT / "fixtures/ir/v1.2/valid/0402.json"
GOLDEN = ROOT / "fixtures/footprint/expected/0402.kicad_mod"


def _inputs():
    """

    @brief Load the known-good Phase 5 IR and PDL fixtures.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    return parse_json(IR_PATH.read_bytes()), load_pdl("synthetic-0402")


def test_phase_five_gate_generates_valid_deterministic_footprint():
    """

    @brief Verify deterministic 0402 output and required footprint features.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    ir, pdl = _inputs()
    context = FootprintContext()
    assert validate_footprint_inputs(ir, pdl) == ()

    first = serialize_footprint(ir, pdl, context)
    second = serialize_footprint(ir, pdl, context)
    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert validate_footprint_artifact(first, ir, pdl) == ()
    assert first.filename == "TEST-R-0402.kicad_mod"
    assert first.content.startswith(b'(footprint "TEST-R-0402"')
    assert first.content == GOLDEN.read_bytes().replace(b"\r\n", b"\n")
    assert b'(pad "1" smd' in first.content
    assert b'(pad "2" smd' in first.content
    assert b"F.CrtYd" in first.content
    assert b"Land pattern source:" in first.content


def test_footprint_dependency_changes_only_for_consumed_inputs():
    """

    @brief Verify hashing tracks geometry but excludes unrelated data.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    ir, pdl = _inputs()
    baseline = footprint_dependency_hash(ir, pdl, FootprintContext())

    changed_land_pattern = pdl.data
    changed_land_pattern["land_pattern"]["groups"][0]["shapes"][0]["size_mm"][
        0
    ] = 0.56
    changed_land_pattern["content_sha256"] = pdl_hash(changed_land_pattern)
    changed_pdl = type(pdl)(changed_land_pattern)
    assert (
        footprint_dependency_hash(ir, changed_pdl, FootprintContext())
        != baseline
    )

    changed_3d = parse_json(IR_PATH.read_bytes())
    changed_3d["model_3d"]["placement"]["translation_mm"][0] = 1
    assert (
        footprint_dependency_hash(changed_3d, pdl, FootprintContext())
        == baseline
    )

    changed_component_id = parse_json(IR_PATH.read_bytes())
    changed_component_id["identity"]["component_id"] = (
        "01995ead-8000-7000-8000-000000000099"
    )
    changed_component_hash = footprint_dependency_hash(
        changed_component_id, pdl, FootprintContext()
    )
    assert changed_component_hash == baseline
    assert (
        footprint_dependency_hash(
            ir,
            pdl,
            FootprintContext(
                generator_version="9.0",
                serializer_version="9.0",
                naming_version="9.0",
                python_version="9.0",
            ),
        )
        == baseline
    )
    changed_3d_association = parse_json(IR_PATH.read_bytes())
    changed_3d_association["model_3d"]["placement"]["translation_mm"][0] = 1
    assert association_dependency_hash(changed_3d_association) != (
        association_dependency_hash(ir)
    )
    assert association_dependency_hash(ir) == association_dependency_hash(
        changed_component_id
    )


def test_footprint_artifact_validation_rejects_changed_pad_geometry():
    """

    @brief Rejects a footprint whose pad geometry differs from the PDL.
    @return The callable result.
    @details Exercises the structural pad validator rather than only numbering.

    """
    ir, pdl = _inputs()
    artifact = serialize_footprint(ir, pdl, FootprintContext())
    changed = artifact.content.replace(b"(size 0.55 0.6)", b"(size 0.56 0.6)")
    changed_artifact = type(artifact)(
        artifact_type=artifact.artifact_type,
        filename=artifact.filename,
        content=changed,
        source_hash=artifact.source_hash,
        dependency_hash=artifact.dependency_hash,
        generator_version=artifact.generator_version,
        association_dependency_hash=artifact.association_dependency_hash,
    )
    assert any(
        issue.code == "FOOTPRINT_PADS"
        for issue in validate_footprint_artifact(changed_artifact, ir, pdl)
    )


def test_footprint_input_validation_rejects_malformed_ir():
    """

    @brief Verify malformed IR is rejected before footprint generation.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    _, pdl = _inputs()
    issues = validate_footprint_inputs({}, pdl)
    assert issues
    assert all(issue.code in {"IR_SCHEMA", "IR_VERSION"} for issue in issues)


def test_concrete_generator_implements_component_ir_api():
    """

    @brief Verify the concrete generator implements the public artifact API.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """

    ir, pdl = _inputs()
    artifact = DeterministicFootprintGenerator().generate(
        ComponentIR.from_file(IR_PATH), pdl, FootprintContext()
    )
    assert artifact.artifact_type == "FOOTPRINT"
    assert artifact.association_dependency_hash is not None
