"""

@package tests.test_threed
@brief Phase 6 CadQuery/OCP/OCCT 3D-generation gate tests.
@details Provides the module implementation and public interfaces.
"""

import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from partsmith.footprint import (
    FootprintContext,
    association_dependency_hash,
    serialize_footprint,
)
from partsmith.ir.canonical import parse_json
from partsmith.ir.model import validate_ir
from partsmith.pdl import load_pdl, pdl_hash
from partsmith.threed import (
    DeterministicThreeDGenerator,
    SolidMeasurement,
    StepMeasurement,
    ThreeDContext,
    cross_validate_footprint_3d,
    export_step_solids,
    generate_model_3d,
    threed_dependency_hash,
    validate_applicability_binding,
    validate_model_3d,
    validate_step_artifact,
    validate_step_file,
    validate_threed_inputs,
)
from partsmith.threed.geometry import build_solids
from partsmith.threed.step_backend import generate_step_bytes

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

    changed_tolerances = parse_json(pdl.canonical_bytes)
    changed_tolerances["validation"]["tolerances"]["BODY"]["value"] = 9.99
    changed_tolerances["content_sha256"] = pdl_hash(changed_tolerances)
    tolerance_pdl = type(pdl)(changed_tolerances)
    assert (
        threed_dependency_hash(ir, tolerance_pdl, ThreeDContext()) == baseline
    )

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


PHASE7 = ROOT / "fixtures/phase7"
PHASE7_PDL = PHASE7 / "pdl"


def _phase_seven_artifacts():
    """@brief Load the asymmetric committed Phase 7 corpus.
    @return IR, PDL, footprint bytes, and STEP bytes.
    @details Loads the isolated fixture-root subject without changing the
    packaged Phase 3 PDL inventory.
    """
    ir = parse_json((PHASE7 / "ir/asymmetric-sot23.json").read_bytes())
    pdl = load_pdl("synthetic-asymmetric-sot23", "1.0", root=PHASE7_PDL)
    footprint = (PHASE7 / "footprint/asymmetric-good.kicad_mod").read_bytes()
    step = (PHASE7 / "step/asymmetric-good.step").read_bytes()
    return ir, pdl, footprint, step


def _failed_rule_ids(results):
    """@brief Return rule IDs for blocking failures.
    @param results Validation results to inspect.
    @return The set of failed rule identifiers.
    @details Ignores passing and declared non-applicable results.
    """
    return {result.rule_id for result in results if result.status == "FAIL"}


def test_phase_seven_gate_passes_valid_asymmetric_geometry():
    """@brief Verify the asymmetric STEP and footprint pass Phase 7.
    @return None.
    @details Validates strict result serialization and pinned absence binding.
    """
    ir, pdl, footprint, step = _phase_seven_artifacts()
    model_results = validate_model_3d(step, ir, pdl)
    cross_results = cross_validate_footprint_3d(footprint, step, ir, pdl)
    assert _failed_rule_ids((*model_results, *cross_results)) == set()
    required = {item["id"] for item in pdl.data["required_observables"]}
    emitted = [result.rule_id for result in (*model_results, *cross_results)]
    assert all(emitted.count(rule_id) == 1 for rule_id in required)
    result_ids = [result.id for result in (*model_results, *cross_results)]
    assert len(result_ids) == len(set(result_ids))
    assert len(emitted) == len(set(emitted))
    exclusion = next(
        result
        for result in cross_results
        if result.rule_id == "exposed-pad-applicability"
    )
    assert exclusion.status is None
    assert validate_applicability_binding(exclusion, pdl) == exclusion
    report_ir = deepcopy(ir)
    report_ir["validation"]["results"] = [
        result.to_dict() for result in (*model_results, *cross_results)
    ]
    assert validate_ir(report_ir) == ()


@pytest.mark.parametrize(
    "filename,rule_id",
    [
        ("fault-offset.step", "step-offset"),
        ("fault-rotate-90.step", "step-orientation"),
        ("fault-rotate-180.step", "step-orientation"),
        ("fault-mirror-x.step", "step-mirror"),
        ("fault-mirror-y.step", "step-mirror"),
        ("fault-scale-2x.step", "step-scale"),
        ("fault-scale-0.5x.step", "step-scale"),
        ("fault-height.step", "OBS-BODY-HEIGHT"),
        ("fault-unit.step", "step-unit-scale"),
    ],
)
def test_phase_seven_geometry_faults_fail_intended_rule(filename, rule_id):
    """@brief Verify one committed STEP fault fails its intended rule.
    @param filename Fault artifact filename.
    @param rule_id Required failing rule.
    @return None.
    @details Collateral failures are allowed, but the intended result is
    mandatory.
    """
    ir, pdl, _, _ = _phase_seven_artifacts()
    step = (PHASE7 / "step" / filename).read_bytes()
    assert rule_id in _failed_rule_ids(validate_model_3d(step, ir, pdl))


@pytest.mark.parametrize(
    "prefix",
    [b".CENTI.", b".MICRO.", b".NANO.", b".KILO."],
)
def test_phase_seven_parseable_non_mm_units_fail_unit_rule(prefix):
    """@brief Classify parseable non-mm STEP units as unit failures.
    @param prefix ISO 10303 SI prefix token.
    @return None.
    @details Successful OCP parsing remains distinct from unit-scale
    validation.
    """
    ir, pdl, _, good = _phase_seven_artifacts()
    changed = good.replace(b".MILLI.", prefix)
    failed = _failed_rule_ids(validate_model_3d(changed, ir, pdl))
    assert "step-unit-scale" in failed
    assert "step-parse" not in failed


@pytest.mark.parametrize(
    "unit,value",
    [
        ("mm", 3),
        ("inch", 3 / 25.4),
        ("mil", 3 / 0.0254),
        ("um", 3000),
        ("µm", 3000),
        ("μm", 3000),
    ],
)
def test_phase_seven_normalizes_all_ir_length_units(unit, value):
    """@brief Normalize every supported IR length unit before comparison.
    @param unit Source length unit.
    @param value Source value equivalent to three millimetres.
    @return None.
    @details Prevents correct non-mm evidence from failing validation.
    """
    ir, pdl, _, step = _phase_seven_artifacts()
    changed = deepcopy(ir)
    changed["package"]["mechanical"]["body_length"]["source_value"] = value
    changed["package"]["mechanical"]["body_length"]["source_unit"] = unit
    failed = _failed_rule_ids(validate_model_3d(step, changed, pdl))
    assert "OBS-BODY-LENGTH" not in failed


def test_phase_seven_rejects_false_pass_from_unconverted_ir_unit():
    """@brief Reject a three-inch declaration against a three-mm body.
    @return None.
    @details Guards against treating a valid non-mm source value as mm.
    """
    ir, pdl, _, step = _phase_seven_artifacts()
    changed = deepcopy(ir)
    changed["package"]["mechanical"]["body_length"]["source_value"] = 3
    changed["package"]["mechanical"]["body_length"]["source_unit"] = "inch"
    assert "OBS-BODY-LENGTH" in _failed_rule_ids(
        validate_model_3d(step, changed, pdl)
    )


def test_phase_six_measurement_constructors_remain_compatible():
    """@brief Preserve the exported Phase 6 measurement constructors.
    @return None.
    @details New bounds and unit fields default from the former public
    signatures.
    """
    solid = SolidMeasurement((1, 2, 3), (2, 4, 6))
    measurement = StepMeasurement((solid,))
    assert solid.minimum_mm == (0, 0, 0)
    assert solid.maximum_mm == (2, 4, 6)
    assert measurement.length_unit_mm == 1.0


def test_phase_seven_fault_steps_are_deterministically_reproducible():
    """@brief Regenerate committed geometry faults byte-for-byte.
    @return None.
    @details Uses the same production normalization and solid-count check.
    """
    _, pdl, _, good = _phase_seven_artifacts()
    solids = build_solids(pdl.data)
    expected = {
        "fault-offset.step": export_step_solids(
            [solid.translate((0.2, 0, 0)) for solid in solids]
        ),
        "fault-rotate-90.step": export_step_solids(
            [solid.rotate((0, 0, 0), (0, 0, 1), 90) for solid in solids]
        ),
        "fault-rotate-180.step": export_step_solids(
            [solid.rotate((0, 0, 0), (0, 0, 1), 180) for solid in solids]
        ),
        "fault-mirror-x.step": export_step_solids(
            [solid.mirror("YZ") for solid in solids]
        ),
        "fault-mirror-y.step": export_step_solids(
            [solid.mirror("XZ") for solid in solids]
        ),
        "fault-scale-2x.step": export_step_solids(
            [solid.scale(2) for solid in solids]
        ),
        "fault-scale-0.5x.step": export_step_solids(
            [solid.scale(0.5) for solid in solids]
        ),
        "fault-unit.step": good.replace(
            b"SI_UNIT(.MILLI.,.METRE.)",
            b"SI_UNIT(.CENTI.,.METRE.)",
        ),
    }
    wrong = pdl.data
    wrong["mechanical"]["body"]["height"]["nominal_mm"] = 1.5
    wrong["mechanical"]["body"]["height"]["maximum_mm"] = 1.6
    expected["fault-height.step"] = generate_step_bytes(wrong)
    for filename, content in expected.items():
        assert (PHASE7 / "step" / filename).read_bytes() == content


def test_phase_seven_symmetry_equivalent_geometry_is_positive():
    """@brief Accept a separately declared symmetry-equivalent geometry.
    @return None.
    @details A 180-degree symmetric 0402 is positive equivalence evidence and
    is not counted as an injected detected fault.
    """
    ir = parse_json((PHASE7 / "ir/symmetric-0402.json").read_bytes())
    ir["model_3d"]["placement"]["rotation_deg"] = [0, 0, 180]
    pdl = load_pdl("synthetic-0402-phase7", "1.0", root=PHASE7_PDL)
    footprint = serialize_footprint(ir, pdl, FootprintContext()).content
    step = (PHASE7 / "step/symmetric-rotate-180.step").read_bytes()
    results = (
        *validate_model_3d(step, ir, pdl),
        *cross_validate_footprint_3d(footprint, step, ir, pdl),
    )
    assert _failed_rule_ids(results) == set()


def test_phase_seven_rejects_pin1_and_pad_inventory_faults():
    """@brief Reject swapped pin 1, missing pads, and extra pads.
    @return None.
    @details Mutations are deterministic test inputs because footprint labels,
    unlike STEP solids, carry terminal identity.
    """
    ir, pdl, footprint, step = _phase_seven_artifacts()
    swapped = (
        footprint.replace(b'(pad "1"', b'(pad "X"', 1)
        .replace(b'(pad "2"', b'(pad "1"', 1)
        .replace(b'(pad "X"', b'(pad "2"', 1)
    )
    swapped_results = cross_validate_footprint_3d(swapped, step, ir, pdl)
    assert "OBS-PIN1" in _failed_rule_ids(swapped_results)

    declared_fault = deepcopy(ir)
    declared_fault["pins"][0]["physical"]["topology_side"] = "east"
    declared_fault["pins"][1]["physical"]["topology_side"] = "west"
    assert "OBS-PIN1" in _failed_rule_ids(
        cross_validate_footprint_3d(footprint, step, declared_fault, pdl)
    )

    missing = footprint.replace(b'(pad "3"', b'(xpad "3"', 1)
    assert "pad-count" in _failed_rule_ids(
        cross_validate_footprint_3d(missing, step, ir, pdl)
    )
    extra = footprint.replace(
        b"\n)",
        b'\n  (pad "4" smd rect (at 0 0) (size 0.2 0.2)\\n'
        b'    (layers "F.Cu" "F.Paste" "F.Mask")\\n  )\n)',
        1,
    )
    assert {"pad-count", "physical-pin-count"} <= _failed_rule_ids(
        cross_validate_footprint_3d(extra, step, ir, pdl)
    )


def test_phase_seven_missing_measured_terminal_emits_failures():
    """@brief Fail count, mapping, and observable rules for missing geometry.
    @return None.
    @details A required measured feature never becomes a skipped result.
    """
    ir, pdl, _, _ = _phase_seven_artifacts()
    incomplete = export_step_solids(build_solids(pdl.data)[:-1])
    failed = _failed_rule_ids(validate_model_3d(incomplete, ir, pdl))
    assert {"solid-count", "terminal-mapping", "OBS-TERMINAL-3"} <= failed


def test_phase_seven_rejects_terminal_dimension_and_plane_faults():
    """@brief Reject oversized, penetrating, and floating terminals.
    @return None.
    @details Terminal dimensions and mounting-plane contact are measured
    independently from center-position validation.
    """
    ir, pdl, _, _ = _phase_seven_artifacts()
    oversized = pdl.data
    oversized["mechanical"]["terminal"]["height"]["nominal_mm"] = 0.4
    oversized["mechanical"]["terminal"]["height"]["maximum_mm"] = 0.45
    penetrating = generate_step_bytes(oversized)
    penetrating_failures = _failed_rule_ids(
        validate_model_3d(penetrating, ir, pdl)
    )
    assert {"OBS-T-1-HEIGHT", "mounting-plane"} <= penetrating_failures

    solids = build_solids(pdl.data)
    floating = export_step_solids(
        [solids[0], *[solid.translate((0, 0, 0.1)) for solid in solids[1:]]]
    )
    assert "mounting-plane" in _failed_rule_ids(
        validate_model_3d(floating, ir, pdl)
    )


def test_legacy_step_validator_accepts_phase_seven_absent_features():
    """@brief Keep the public Phase 6 validator compatible with Phase 7 PDLs.
    @return None.
    @details Declared-absent terminal anchors neither sort as terminals nor
    increase the expected solid count.
    """
    _, pdl, _, step = _phase_seven_artifacts()
    assert validate_step_artifact(step, pdl) == ()


def test_phase_seven_rejects_stale_applicability_binding():
    """@brief Convert a stale exclusion binding into an applicable failure.
    @return None.
    @details A stale hash cannot become a justified non-applicability record.
    """
    _, pdl, footprint, step = _phase_seven_artifacts()
    ir = parse_json((PHASE7 / "ir/asymmetric-sot23.json").read_bytes())
    result = next(
        item
        for item in cross_validate_footprint_3d(footprint, step, ir, pdl)
        if item.applicability == "NOT_APPLICABLE"
    )
    stale = type(result)(
        **{
            **result.__dict__,
            "applicability_basis": {
                **result.applicability_basis,
                "sha256": "0" * 64,
            },
        }
    )
    verified = validate_applicability_binding(stale, pdl)
    assert verified.status == "FAIL"
    assert verified.applicability == "APPLICABLE"


def test_phase_seven_applies_position_and_orientation_boundaries():
    """@brief Verify just-inside and just-outside geometric tolerances.
    @return None.
    @details Uses a 0.001 margin above OCCT measurement noise.
    """
    ir, pdl, _, _ = _phase_seven_artifacts()
    solids = build_solids(pdl.data)
    inside_offset = export_step_solids(
        [solid.translate((0.049, 0, 0)) for solid in solids]
    )
    outside_offset = export_step_solids(
        [solid.translate((0.051, 0, 0)) for solid in solids]
    )
    assert "step-offset" not in _failed_rule_ids(
        validate_model_3d(inside_offset, ir, pdl)
    )
    assert "step-offset" in _failed_rule_ids(
        validate_model_3d(outside_offset, ir, pdl)
    )

    inside_rotation = export_step_solids(
        [solid.rotate((0, 0, 0), (0, 0, 1), 0.099) for solid in solids]
    )
    outside_rotation = export_step_solids(
        [solid.rotate((0, 0, 0), (0, 0, 1), 0.101) for solid in solids]
    )
    assert "step-orientation" not in _failed_rule_ids(
        validate_model_3d(inside_rotation, ir, pdl)
    )
    assert "step-orientation" in _failed_rule_ids(
        validate_model_3d(outside_rotation, ir, pdl)
    )


def test_phase_seven_applies_height_and_clearance_boundaries():
    """@brief Verify height and clearance tolerances at pinned boundaries.
    @return None.
    @details Uses deterministic generated geometry and footprint mutations.
    """
    ir, pdl, footprint, step = _phase_seven_artifacts()
    inside_height = pdl.data
    inside_height["mechanical"]["body"]["height"]["nominal_mm"] = 1.049
    outside_height = pdl.data
    outside_height["mechanical"]["body"]["height"]["nominal_mm"] = 1.051
    assert "OBS-BODY-HEIGHT" not in _failed_rule_ids(
        validate_model_3d(generate_step_bytes(inside_height), ir, pdl)
    )
    assert "OBS-BODY-HEIGHT" in _failed_rule_ids(
        validate_model_3d(generate_step_bytes(outside_height), ir, pdl)
    )

    inside_clearance = footprint.replace(
        b"(at -1.3 -0.6)", b"(at -1.349 -0.6)", 1
    )
    outside_clearance = footprint.replace(
        b"(at -1.3 -0.6)", b"(at -1.351 -0.6)", 1
    )
    assert "OBS-CLEARANCE" not in _failed_rule_ids(
        cross_validate_footprint_3d(inside_clearance, step, ir, pdl)
    )
    assert "OBS-CLEARANCE" in _failed_rule_ids(
        cross_validate_footprint_3d(outside_clearance, step, ir, pdl)
    )


def test_phase_seven_reports_missing_and_invalid_step():
    """@brief Report missing files and malformed STEP with intended rules.
    @return None.
    @details Missing paths are distinct from malformed existing bytes.
    """
    ir, pdl, _, _ = _phase_seven_artifacts()
    assert _failed_rule_ids(
        validate_step_file(PHASE7 / "step/missing.step", ir, pdl)
    ) == {"step-file-exists"}
    assert _failed_rule_ids(
        validate_model_3d(b"not a STEP artifact", ir, pdl)
    ) == {"step-parse"}
