"""IR 1.2 regression gates for reviewed contracts and immutable history."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.ir import (
    ComponentIR,
    IRValidationError,
    MemoryRevisionStore,
    RequirementsContext,
    canonical_json,
    dependency_hash,
    dependency_projection,
    load_schema,
    migrate_v1_1_to_v1_2,
    normalize_ir,
    validate_ir,
    validate_revision_transition,
)
from partsmith.ir.revised import resolve_pointer

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/ir/v1.2"
PATHS = (
    "/identity",
    "/electrical",
    "/pins",
    "/package",
    "/footprint",
    "/model_3d",
)
CONTEXT = RequirementsContext(
    "synthetic", "test-1", "test-1", "test-1", PATHS, PATHS
)
WIDTH = "/package/mechanical/body_width"
CONFIG = {
    "pdl": {"id": "synthetic-0402", "version": "test-1"},
    "release_profile": {
        "id": "mvp-1",
        "version": "test-1",
        "accuracy_class": "CLASS_A",
    },
    "runtime": {
        key: "test-1"
        for key in (
            "python",
            "cadquery",
            "ocp",
            "occt",
            "generator",
            "validator",
        )
    },
    "exporter": {"version": "test-1", "timestamp": "fixed"},
}


@pytest.fixture
def valid():
    return json.loads((FIXTURES / "valid/0402.json").read_text())


def inventory(data):
    return {
        "source_hashes": [r["sha256"] for r in data["source"]["documents"]],
        "evidence_ids": [r["id"] for r in data["evidence"]],
    }


def review(data):
    inv = inventory(data)
    data["revision"]["evidence_review"].update(
        inventory_sha256=sha256(canonical_json(inv)).hexdigest(),
        reviewed_evidence_ids=inv["evidence_ids"],
    )


def store(data, *parents):
    return MemoryRevisionStore(
        parents, [inventory(d) for d in (data, *parents)]
    )


def issues(data, *parents, context=CONTEXT, revisions=None):
    return validate_ir(
        data,
        for_generation=True,
        requirements=context,
        revisions=revisions or store(data, *parents),
    )


def codes(data, *parents, **kwargs):
    return {i.code for i in issues(data, *parents, **kwargs)}


def child(data, key="IR12-2"):
    result = copy.deepcopy(data)
    result["revision"].update(id=key, parent_id=data["revision"]["id"])
    return result


def put(data, path, value):
    prefix, _, token = path.rpartition("/")
    node = resolve_pointer(data, prefix) if prefix else data
    node[int(token) if isinstance(node, list) else token] = value


def override(
    before, path=WIDTH, value=None, kind="QUANTITY_RECORD", key="O-1"
):
    data = child(before)
    old = copy.deepcopy(resolve_pointer(data, path))
    if value is None:
        value = copy.deepcopy(old)
    if isinstance(value, dict) and "status" in value:
        value.update(status="USER_OVERRIDE", override_id=key)
    put(data, path, value)
    data["overrides"].append(
        dict(
            id=key,
            path=path,
            value_type=kind,
            previous_value=old,
            new_value=copy.deepcopy(value),
            reason="Synthetic review",
            user="reviewer",
            timestamp="2026-09-20T12:00:00Z",
            evidence_reference="E-001",
            approval_state="APPROVED",
            base_revision_id=before["revision"]["id"],
            supersedes_override_id=None,
        )
    )
    data["revision"]["active_override_ids"] = [key]
    return data


def resolution(
    data,
    key="R-1",
    target=WIDTH,
    old=(),
    selected=("E-001",),
    base=None,
    supersedes=None,
):
    data["resolutions"].append(
        dict(
            id=key,
            target_path=target,
            superseded_evidence_ids=list(old),
            selected_evidence_ids=list(selected),
            override_id=None,
            decision="select",
            reason="Reviewed synthetic conflict",
            reviewer="reviewer",
            timestamp="2026-09-20T12:00:00Z",
            approval_state="APPROVED",
            base_revision_id=base or data["revision"]["id"],
            supersedes_resolution_id=supersedes,
        )
    )
    data["revision"]["active_resolution_ids"] = [key]


def conflict(data):
    evidence = copy.deepcopy(data["evidence"][0])
    evidence.update(
        id="E-CONFLICT",
        candidate_targets=[WIDTH],
        acquisition_revision_id=data["revision"]["id"],
    )
    evidence["interpretation"]["status"] = "CONFLICTING"
    data["evidence"].append(evidence)
    review(data)


def projected(data, *parents, context=CONTEXT, config=None):
    return dependency_hash(
        data,
        requirements=context,
        revisions=store(data, *parents),
        configuration=config or CONFIG,
    )


def test_valid_fixture_roundtrip_and_frozen_hash(valid):
    assert issues(valid) == ()
    ir = ComponentIR(valid)
    assert (
        ir.canonical_bytes
        == (FIXTURES / "expected/0402.canonical.json").read_bytes()
    )
    assert ir.sha256 == (FIXTURES / "expected/0402.sha256").read_text().strip()
    assert ComponentIR.from_json(ir.canonical_bytes).sha256 == ir.sha256
    ir.data["pins"].clear()
    assert len(ir.data["pins"]) == 2


@pytest.mark.parametrize(
    "case",
    json.loads((FIXTURES / "invalid/expected.json").read_text()),
    ids=lambda c: c["file"],
)
def test_negative_corpus(case):
    data = json.loads((FIXTURES / "invalid" / case["file"]).read_text())
    assert [
        {"code": i.code, "path": i.path} for i in validate_ir(data)
    ] == case["issues"]


def test_store_is_detached(valid):
    repo = MemoryRevisionStore([valid], [inventory(valid)])
    valid["pins"].clear()
    assert len(repo.get_revision("IR12-1")["pins"]) == 2
    repo.get_revision("IR12-1")["pins"].clear()
    assert len(repo.get_revision("IR12-1")["pins"]) == 2


def test_generation_requires_real_history_and_context(valid):
    assert "IR_HISTORY" in {
        i.code
        for i in validate_ir(valid, for_generation=True, requirements=CONTEXT)
    }
    assert "IR_REQUIREMENTS" in codes(valid, context=None)
    data = child(valid)
    assert "IR_HISTORY" in codes(data)
    assert issues(data, valid) == ()


@pytest.mark.parametrize(
    "path,value,kind",
    [
        ("/pins/0/electrical_type", "input", "STRING"),
        ("/pins/0/number", "3", "STRING"),
        ("/pins/0/active_low", True, "BOOLEAN"),
        ("/pins/0/physical/topology_index", 2, "NUMBER"),
        ("/model_3d/placement/translation_mm/0", Decimal("1.25"), "NUMBER"),
        ("/model_3d/placement/rotation_deg", [0, 0, 90], "VEC3"),
        ("/model_3d/placement/scale", [2, 1, 1], "VEC3"),
        (
            "/model_3d/placement/mirror",
            dict(x=True, y=False, z=False),
            "MIRROR_RECORD",
        ),
        ("/model_3d/placement/mirror/x", True, "BOOLEAN"),
    ],
)
def test_typed_leaf_overrides(valid, path, value, kind):
    data = override(valid, path, value, kind)
    assert issues(data, valid) == ()
    assert projected(data, valid) != projected(valid)


def test_quantity_override_has_no_projection_cycle(valid):
    data = override(valid)
    assert issues(data, valid) == ()
    assert len(projected(data, valid)) == 64
    assert projected(data, valid) != projected(valid)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["overrides"][0].update(value_type="BOOLEAN"),
        lambda d: d["overrides"][0].update(path="/revision/description"),
        lambda d: d["overrides"][0].update(new_value="POWER_INPUT"),
        lambda d: d["overrides"][0].update(approval_state="PENDING"),
        lambda d: d["revision"].update(active_override_ids=[]),
    ],
)
def test_bad_override_is_rejected(valid, change):
    data = override(valid)
    change(data)
    assert validate_ir(data)


def test_override_previous_value_must_match_base(valid):
    data = override(valid, "/pins/0/electrical_type", "input", "STRING")
    data["overrides"][0]["previous_value"] = "output"
    assert "IR_HISTORY" in codes(data, valid)


def test_overlapping_active_overrides_rejected(valid):
    data = override(
        valid, "/model_3d/placement/translation_mm", [1, 0, 0], "VEC3"
    )
    other = copy.deepcopy(data["overrides"][0])
    other.update(
        id="O-2",
        path="/model_3d/placement/translation_mm/0",
        value_type="NUMBER",
        previous_value=0,
        new_value=1,
    )
    data["overrides"].append(other)
    data["revision"]["active_override_ids"].append("O-2")
    assert "IR_SELECTION" in {i.code for i in validate_ir(data)}


def test_unlinking_conflicting_candidate_cannot_pass(valid):
    conflict(valid)
    assert "IR_CONFLICT" in codes(valid)
    valid["package"]["mechanical"]["body_width"]["evidence_ids"] = ["E-001"]
    assert "IR_CONFLICT" in codes(valid)
    resolution(valid, old=["E-CONFLICT"])
    assert issues(valid) == ()


def test_unrelated_history_does_not_block_generator(valid):
    conflict(valid)
    context = replace(
        CONTEXT, mandatory_paths=("/pins",), required_paths=("/pins",)
    )
    assert issues(valid, context=context) == ()


def test_selected_evidence_requires_relevance(valid):
    valid["evidence"][0]["candidate_targets"] = [WIDTH]
    assert "IR_RELEVANCE" in codes(valid)


def test_successive_resolutions_keep_approved_history(valid):
    conflict(valid)
    resolution(valid, old=["E-CONFLICT"])
    data = child(valid)
    resolution(
        data, key="R-2", old=["E-CONFLICT"], base="IR12-1", supersedes="R-1"
    )
    assert issues(data, valid) == ()
    assert data["resolutions"][0]["approval_state"] == "APPROVED"
    data["revision"]["active_resolution_ids"] = ["R-1", "R-2"]
    assert "IR_SELECTION" in {i.code for i in validate_ir(data)}


def test_second_resolution_must_keep_conflict_disposition(valid):
    conflict(valid)
    resolution(valid, old=["E-CONFLICT"])
    data = child(valid)
    resolution(data, key="R-2", base="IR12-1", supersedes="R-1")
    assert "IR_CONFLICT" in codes(data, valid)


@pytest.mark.parametrize(
    "domain", ["evidence", "source", "resolutions", "overrides"]
)
def test_history_cannot_be_rewritten(valid, domain):
    if domain == "resolutions":
        resolution(valid)
    if domain == "overrides":
        valid = override(valid)
    data = child(valid, "IR12-3")
    if domain == "source":
        data["source"]["documents"][0]["path"] = "source/changed.txt"
    else:
        data[domain][0]["id"] = "rewritten"
        if domain in {"resolutions", "overrides"}:
            data["revision"]["active_" + domain[:-1] + "_ids"] = ["rewritten"]
    assert validate_revision_transition(valid, data)


def test_candidate_target_dismissal_is_a_transition_error(valid):
    conflict(valid)
    data = child(valid)
    data["evidence"][1]["candidate_targets"] = []
    assert "IR_TRANSITION" in {
        i.code for i in validate_revision_transition(valid, data)
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["revision"].update(evidence_review=None),
        lambda d: d["revision"]["evidence_review"].update(
            approval_state="PENDING"
        ),
        lambda d: d["revision"]["evidence_review"].update(
            reviewed_evidence_ids=[]
        ),
        lambda d: d["revision"]["evidence_review"].update(
            inventory_sha256="0" * 64
        ),
        lambda d: d["evidence"][0].update(acquisition_revision_id="missing"),
    ],
)
def test_review_inventory_and_acquisition_are_required(valid, change):
    change(valid)
    assert issues(valid)


def test_real_provenance_cycle_rejected(valid):
    valid["evidence"][0]["interpretation"].update(
        status="DERIVED", derivation="cycle", evidence_ids=["E-001"]
    )
    assert "IR_CYCLE" in {i.code for i in validate_ir(valid)}


def result():
    return dict(
        id="V-1",
        category="cross_validation",
        rule_id="exposed-pad",
        status=None,
        severity="INFO",
        message="Fixture has no exposed pad",
        evidence_ids=[],
        artifact_ids=[],
        measured=None,
        expected=None,
        tolerance=None,
        stage="FINAL_ARTIFACT",
        applicability="NOT_APPLICABLE",
        applicability_reason="Absent in pinned fixture",
        applicability_basis=dict(
            kind="FIXTURE",
            id="synthetic",
            revision="1",
            sha256="a" * 64,
            feature_id="ep",
        ),
        measurement_mode="NONE",
    )


def test_non_applicability_is_not_fabricated_pass(valid):
    valid["validation"]["results"] = [result()]
    assert validate_ir(valid) == ()
    valid["validation"]["results"][0]["status"] = "PASS"
    assert validate_ir(valid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("applicability_reason", None),
        ("applicability_basis", None),
        ("measurement_mode", "MEASURED"),
        ("measured", 1),
        ("stage", "UNKNOWN"),
    ],
)
def test_invalid_applicability_rejected(valid, field, value):
    record = result()
    record[field] = value
    valid["validation"]["results"] = [record]
    assert validate_ir(valid)


def region(data):
    data["evidence"][0]["source"].update(
        region=dict(x=10, y=10, width=20, height=30),
        coordinate_convention="document-page-1.0",
        page_geometry=dict(
            media_box=[-10, -20, 602, 772],
            crop_box=[0, 0, 600, 700],
            user_unit=1,
            rotation_deg=90,
        ),
        render_transform=dict(
            image_sha256="b" * 64,
            width_px=600,
            height_px=700,
            dpi_x=72,
            dpi_y=72,
            renderer="synthetic",
            version="1",
            pixel_to_page=[[1, 0, 10], [0, -1, 720], [0, 0, 1]],
        ),
    )


def test_source_region_contract(valid):
    region(valid)
    assert validate_ir(valid) == ()


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s["region"].update(x=-1),
        lambda s: s["region"].update(width=1000),
        lambda s: s["page_geometry"].update(user_unit=0),
        lambda s: s["page_geometry"].update(media_box=[0, 0, 0, 1]),
        lambda s: s["render_transform"].update(
            pixel_to_page=[[0, 0, 0], [0, 0, 0], [0, 0, 1]]
        ),
        lambda s: s["render_transform"].update(
            pixel_to_page=[[1, 0, 0], [0, 1, 0], [0, 1, 1]]
        ),
        lambda s: s.update(coordinate_convention="pixels"),
    ],
)
def test_invalid_source_regions_fail(valid, change):
    region(valid)
    change(valid["evidence"][0]["source"])
    assert validate_ir(valid)


def test_ocr_cannot_omit_pixel_transform(valid):
    region(valid)
    valid["evidence"][0]["extractor"]["method"] = "ocr"
    valid["evidence"][0]["source"]["render_transform"] = None
    assert "IR_REGION" in {i.code for i in validate_ir(valid)}


def migration_evidence(valid):
    return dict(
        reason="Reviewed synthetic migration context",
        revision=valid["revision"],
        accuracy_class="CLASS_A",
        evidence={
            r["id"]: {
                k: r[k]
                for k in (
                    "acquisition_revision_id",
                    "candidate_targets",
                    "source",
                )
            }
            for r in valid["evidence"]
        },
    )


def test_explicit_migration_preserves_input(valid):
    old = ComponentIR.from_file(ROOT / "fixtures/ir/v1.1/valid/0402.json")
    before = old.canonical_bytes
    migrated = migrate_v1_1_to_v1_2(old, migration_evidence(valid))
    assert migrated.issues == ()
    assert migrated.ir.sha256 == ComponentIR(valid).sha256
    assert old.canonical_bytes == before
    assert json.loads(migrated.history)["source_ir_hash"] == old.sha256


@pytest.mark.parametrize(
    "field", ["revision", "accuracy_class", "evidence", "reason"]
)
def test_migration_does_not_guess(valid, field):
    supplied = migration_evidence(valid)
    del supplied[field]
    old = ComponentIR.from_file(ROOT / "fixtures/ir/v1.1/valid/0402.json")
    migrated = migrate_v1_1_to_v1_2(old, supplied)
    assert migrated.ir is None and migrated.issues
    assert json.loads(migrated.history)["status"] == "FAILED"


def test_migration_rejects_changed_source_identity(valid):
    supplied = migration_evidence(valid)
    supplied["evidence"]["E-001"]["source"]["page"] = 4
    old = ComponentIR.from_file(ROOT / "fixtures/ir/v1.1/valid/0402.json")
    assert migrate_v1_1_to_v1_2(old, supplied).ir is None


def test_projection_audit_changes_do_not_invalidate(valid):
    data = override(valid)
    before = projected(data, valid)
    data["overrides"][0].update(
        user="another-reviewer", timestamp="2026-09-21T00:00:00Z"
    )
    assert projected(data, valid) == before
    data["overrides"][0]["reason"] = "Changed engineering rationale"
    assert projected(data, valid) != before


def test_placement_only_edit_preserves_geometry_projection(valid):
    context = replace(
        CONTEXT, required_paths=("/package",), mandatory_paths=("/package",)
    )
    data = override(valid, "/model_3d/placement/translation_mm/0", 1, "NUMBER")
    assert projected(data, valid, context=context) == projected(
        valid, context=context
    )
    assert projected(data, valid) != projected(valid)


def test_output_reports_not_in_input_projection(valid):
    before = projected(valid)
    valid["validation"]["results"] = [result()]
    assert projected(valid) == before


def test_source_revision_changes_projection(valid):
    before = projected(valid)
    valid["source"]["documents"][0]["revision"] = "new"
    valid["identity"]["source_revision"] = "new"
    assert projected(valid) != before


def test_projection_configuration_and_accuracy_cannot_be_omitted(valid):
    with pytest.raises(IRValidationError):
        projected(valid, config={"runtime": {}})
    valid["model_3d"]["accuracy_class"] = "CLASS_C"
    with pytest.raises(IRValidationError):
        projected(valid)


def test_canonical_hash_independent_process_seeds(valid):
    path = FIXTURES / "valid/0402.json"
    command = (
        "from partsmith.ir import ComponentIR; import sys; "
        "print(ComponentIR.from_file(sys.argv[1]).sha256)"
    )
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", command, str(path)],
            env={**os.environ, "PYTHONHASHSEED": seed},
            text=True,
        ).strip()
        for seed in ("1", "73")
    ]
    assert outputs == [ComponentIR(valid).sha256] * 2


def test_schema_loading_is_detached():
    schema = load_schema("1.2")
    schema["$defs"].clear()
    assert load_schema("1.2")["$defs"]


@pytest.mark.parametrize(
    "path,kind",
    [
        ("/pins/0", "PIN_RECORD"),
        ("/pins", "PIN_ARRAY"),
        ("/electrical/resistance", "VALUE_RECORD"),
        ("/model_3d/placement", "PLACEMENT_RECORD"),
    ],
)
def test_whole_record_overrides(valid, path, kind):
    data = override(valid, path=path, kind=kind)
    assert issues(data, valid) == ()
    assert len(projected(data, valid)) == 64


def test_override_cannot_authorize_another_value(valid):
    data = override(valid, "/pins/0/electrical_type", "input", "STRING")
    data["package"]["mechanical"]["body_width"].update(
        status="USER_OVERRIDE", override_id="O-1", source_value=123
    )
    assert "IR_OVERRIDE" in {i.code for i in validate_ir(data)}


def test_replaced_override_preserves_previous_approval(valid):
    first = override(valid)
    second = override(first, key="O-2")
    second["revision"]["id"] = "IR12-3"
    second["overrides"][1]["supersedes_override_id"] = "O-1"
    assert issues(second, valid, first) == ()
    assert second["overrides"][0] == first["overrides"][0]
    assert len(projected(second, valid, first)) == 64


def test_retained_decision_supersession_cycle_rejected(valid):
    data = override(valid)
    data["overrides"][0]["supersedes_override_id"] = "O-1"
    assert "IR_HISTORY" in {i.code for i in validate_ir(data)}


def test_stored_revision_identity_cannot_be_reused(valid):
    repo = MemoryRevisionStore([valid], [inventory(valid)])
    valid["revision"]["description"] = "Changed stored revision"
    assert "IR_HISTORY" in codes(valid, revisions=repo)


def test_reordered_pins_require_explicit_simultaneous_rebindings(valid):
    data = child(valid)
    data["pins"].reverse()
    assert "IR_TRANSITION" in codes(data, valid)
    for old, new in ((0, 1), (1, 0)):
        data["revision"]["target_rebindings"].append(
            dict(
                old_path=f"/pins/{old}",
                new_path=f"/pins/{new}",
                base_revision_id="IR12-1",
                reason="Reordered array",
                reviewer="reviewer",
                timestamp="2026-09-20T12:00:00Z",
                approval_state="APPROVED",
            )
        )
    assert issues(data, valid) == ()
    bad = copy.deepcopy(data)
    bad["revision"]["target_rebindings"][0]["new_path"] = "/pins/0"
    assert "IR_TRANSITION" in codes(bad, valid)


def test_history_can_resolve_changed_evidence_selection(valid):
    resolution(valid)
    data = child(valid)
    new = copy.deepcopy(valid["evidence"][0])
    new.update(id="E-NEW", acquisition_revision_id="IR12-2")
    data["evidence"].append(new)
    data["package"]["mechanical"]["body_width"]["evidence_ids"] = ["E-NEW"]
    resolution(
        data,
        key="R-2",
        old=["E-001"],
        selected=["E-NEW"],
        base="IR12-1",
        supersedes="R-1",
    )
    review(data)
    assert issues(data, valid) == ()


def test_historical_previous_value_does_not_change_projection(valid):
    first = override(valid, "/pins/0/electrical_type", "input", "STRING")
    other_base = copy.deepcopy(valid)
    other_base["pins"][0]["electrical_type"] = "output"
    second = override(other_base, "/pins/0/electrical_type", "input", "STRING")
    assert ComponentIR(first).sha256 != ComponentIR(second).sha256
    assert projected(first, valid) == projected(second, other_base)


def test_projection_replaces_run_ids_with_content(valid):
    before = projected(valid)
    valid["identity"]["component_id"] = "another-component-id"
    valid["source"]["documents"][0]["id"] = "D-OTHER"
    valid["identity"]["source_document_id"] = "D-OTHER"
    valid["evidence"][0]["source"]["document_id"] = "D-OTHER"
    valid["evidence"][0]["id"] = "E-OTHER"
    from partsmith.ir.model import _walk

    for _, record in _walk(valid):
        if "evidence_ids" in record:
            record["evidence_ids"] = ["E-OTHER"]
    review(valid)
    assert projected(valid) == before


def test_invalid_resolution_target_returns_diagnostics(valid):
    resolution(valid, target="/model_3d/required")
    assert validate_ir(valid)


def test_migration_from_wrong_version_fails_cleanly(valid):
    source = ComponentIR.from_file(ROOT / "fixtures/ir/valid/0402.json")
    result = migrate_v1_1_to_v1_2(source, migration_evidence(valid))
    assert result.ir is None
    assert "IR_MIGRATION" in {i.code for i in result.issues}


def test_missing_nominal_values_remain_candidates(valid):
    quantity = valid["package"]["mechanical"]["body_width"]
    quantity.update(
        source_value=None,
        source_unit=None,
        status="MISSING",
        unresolved_reason="Synthetic absent value",
    )
    assert (
        normalize_ir(valid)["package"]["mechanical"]["body_width"][
            "normalized_value"
        ]
        is None
    )
    assert "IR_UNRESOLVED" in codes(valid)


def test_unassigned_evidence_requires_recorded_exclusion(valid):
    raw = copy.deepcopy(valid["evidence"][0])
    raw.update(id="E-RAW", candidate_targets=[])
    valid["evidence"].append(raw)
    review(valid)
    assert "IR_REVIEW" in codes(valid)
    valid["revision"]["evidence_exclusions"].append(
        dict(
            evidence_id="E-RAW",
            replacement_evidence_ids=["E-001"],
            reason="Assigned interpretation retained separately",
            reviewer="fixture",
            timestamp="2026-09-20T12:00:00Z",
            approval_state="APPROVED",
        )
    )
    assert issues(valid) == ()
    before = projected(valid)
    valid["revision"]["evidence_exclusions"][0]["reason"] = "Revised rationale"
    assert projected(valid) != before
    valid["revision"]["evidence_exclusions"][0]["evidence_id"] = "E-001"
    assert validate_ir(valid)


def test_removing_override_requires_explicit_review(valid):
    first = override(valid)
    second = child(first, "IR12-3")
    second["revision"]["active_override_ids"] = []
    second["package"]["mechanical"]["body_width"] = copy.deepcopy(
        resolve_pointer(valid, WIDTH)
    )
    assert "IR_TRANSITION" in codes(second, valid, first)
    resolution(second, base=first["revision"]["id"])
    second["resolutions"][0]["decision"] = "remove_override"
    assert issues(second, valid, first) == ()


def test_cyclic_revision_ancestry_fails(valid):
    parent = copy.deepcopy(valid)
    parent["revision"]["parent_id"] = "IR12-2"
    data = child(parent)
    assert "IR_HISTORY" in codes(data, parent)


def test_scalar_resolution_pointer_never_crashes_generation(valid):
    resolution(valid, target="/model_3d/required")
    assert validate_ir(
        valid,
        for_generation=True,
        requirements=CONTEXT,
        revisions=MemoryRevisionStore(),
    )


@pytest.mark.parametrize("label", ["0402", "quantity-override"])
def test_frozen_dependency_projections(valid, label):
    data, parents = (
        (valid, ()) if label == "0402" else (override(valid), (valid,))
    )
    projection = dependency_projection(
        data,
        requirements=CONTEXT,
        revisions=store(data, *parents),
        configuration=CONFIG,
    )
    assert (
        canonical_json(projection)
        == (FIXTURES / f"expected/{label}.projection.json").read_bytes()
    )
    assert (
        projected(data, *parents)
        == (FIXTURES / f"expected/{label}.dependency.sha256")
        .read_text()
        .strip()
    )
