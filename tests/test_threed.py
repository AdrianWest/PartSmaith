"""

@package tests.test_threed
@brief Phase 6 CadQuery/OCP/OCCT 3D-generation gate tests.
@details Provides the module implementation and public interfaces.
"""

import subprocess
import sys
from pathlib import Path

from partsmith.footprint import association_dependency_hash
from partsmith.ir.canonical import parse_json
from partsmith.pdl import load_pdl, pdl_hash
from partsmith.threed import (
    DeterministicThreeDGenerator,
    ThreeDContext,
    generate_model_3d,
    threed_dependency_hash,
    validate_step_artifact,
    validate_threed_inputs,
)

ROOT = Path(__file__).parents[1]
IR_PATH = ROOT / "fixtures/ir/v1.2/valid/0402.json"
GOLDEN = ROOT / "fixtures/threed/expected/0402.step"


def _inputs():
    """

    @brief Load the known-good Phase 6 IR and PDL fixtures.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """
    return parse_json(IR_PATH.read_bytes()), load_pdl("synthetic-0402")


def test_phase_six_gate_generates_valid_deterministic_step():
    """

    @brief Verify deterministic 0402 STEP output and dimensional
    validation.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """
    ir, pdl = _inputs()
    context = ThreeDContext()
    assert validate_threed_inputs(ir, pdl) == ()

    first = DeterministicThreeDGenerator().generate(ir, pdl, context)
    second = generate_model_3d(ir, pdl, context)
    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert first.filename == "TEST-R-0402.step"
    assert first.content.startswith(b"ISO-10303-21;")
    assert first.content == GOLDEN.read_bytes().replace(b"\r\n", b"\n")
    assert validate_step_artifact(first.content, pdl) == ()


def test_step_generation_is_byte_identical_across_fresh_processes():
    """

    @brief Verify the Phase 6 gate's cross-process determinism
    requirement.
    @return The callable result.
    @details Runs generation twice in separate fresh Python processes,
    each with its own work directory and no shared artifact cache, and
    requires exact STEP SHA-256 equality.

    """
    script = (
        "from pathlib import Path\n"
        "from partsmith.ir.canonical import parse_json\n"
        "from partsmith.pdl import load_pdl\n"
        "from partsmith.threed import (\n"
        "    DeterministicThreeDGenerator, ThreeDContext,\n"
        ")\n"
        f"ir = parse_json(Path(r'{IR_PATH}').read_bytes())\n"
        "pdl = load_pdl('synthetic-0402')\n"
        "artifact = DeterministicThreeDGenerator().generate(\n"
        "    ir, pdl, ThreeDContext()\n"
        ")\n"
        "print(artifact.sha256)\n"
    )

    def _run_in_fresh_process() -> str:
        """

        @brief Run one clean-process STEP export and return its hash.
        @return The str result.
        @details Implements the documented behavior without changing
        the public contract.

        """
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()

    first_hash = _run_in_fresh_process()
    second_hash = _run_in_fresh_process()
    assert first_hash == second_hash


def test_threed_dependency_changes_only_for_consumed_inputs():
    """

    @brief Verify hashing tracks geometry but excludes association-only
    data.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """
    ir, pdl = _inputs()
    baseline = threed_dependency_hash(ir, pdl, ThreeDContext())

    changed_mechanical = parse_json(pdl.canonical_bytes)
    changed_mechanical["mechanical"]["body"]["length"]["nominal_mm"] = 1.02
    changed_mechanical["content_sha256"] = pdl_hash(changed_mechanical)
    changed_pdl = type(pdl)(changed_mechanical)
    assert threed_dependency_hash(ir, changed_pdl, ThreeDContext()) != baseline

    changed_placement = parse_json(IR_PATH.read_bytes())
    changed_placement["model_3d"]["placement"]["translation_mm"][0] = 1
    assert (
        threed_dependency_hash(changed_placement, pdl, ThreeDContext())
        == baseline
    )

    changed_component_id = parse_json(IR_PATH.read_bytes())
    changed_component_id["identity"]["component_id"] = (
        "01995ead-8000-7000-8000-000000000099"
    )
    assert (
        threed_dependency_hash(changed_component_id, pdl, ThreeDContext())
        == baseline
    )
    assert (
        threed_dependency_hash(
            ir,
            pdl,
            ThreeDContext(generator_version="9.0", python_version="9.0"),
        )
        != baseline
    )
    assert association_dependency_hash(
        changed_placement
    ) != association_dependency_hash(ir)


def test_validate_threed_inputs_rejects_unsupported_strategy():
    """

    @brief Reject a model_3d strategy this Phase 6 bootstrap does not
    implement.
    @return The callable result.
    @details Implements the documented behavior without changing the public
    contract.

    """
    ir, pdl = _inputs()
    unsupported = pdl.data
    unsupported["model_3d"]["marker_strategy"] = "PIN1_DOT"
    unsupported["content_sha256"] = pdl_hash(unsupported)
    issues = validate_threed_inputs(ir, type(pdl)(unsupported))
    assert any(issue.code == "THREED_STRATEGY" for issue in issues)


def test_validate_step_artifact_rejects_wrong_solid_count():
    """

    @brief Reject a STEP artifact missing a required terminal solid.
    @return The callable result.
    @details Builds STEP bytes from only the body solid, then validates
    against the full two-terminal PDL fixture.

    """

    from partsmith.threed.geometry import build_solids
    from partsmith.threed.step_backend import (
        _export_raw_step,
        _normalize_step_bytes,
    )

    _, pdl = _inputs()
    solids = build_solids(pdl.data)
    body_only = _normalize_step_bytes(_export_raw_step(solids[:1]))
    issues = validate_step_artifact(body_only, pdl)
    assert any(issue.code == "STEP_SOLID_COUNT" for issue in issues)


def test_validate_step_artifact_rejects_wrong_body_height():
    """

    @brief Reject a STEP artifact whose body height violates PDL
    tolerance.
    @return The callable result.
    @details Regenerates STEP from a PDL copy with a doubled body
    height, then validates it against the original, unmodified PDL.

    """
    _, pdl = _inputs()
    wrong = parse_json(pdl.canonical_bytes)
    wrong["mechanical"]["body"]["height"]["nominal_mm"] = 0.5
    wrong["mechanical"]["body"]["height"]["maximum_mm"] = 0.6
    wrong["content_sha256"] = pdl_hash(wrong)

    from partsmith.threed.step_backend import generate_step_bytes

    wrong_bytes = generate_step_bytes(wrong)
    issues = validate_step_artifact(wrong_bytes, pdl)
    assert any(issue.code == "STEP_DIMENSION" for issue in issues)
