"""

@package tests.test_ir_v12
@brief IR 1.2 regression gates for reviewed contracts and immutable
history.
@details Provides the module implementation and public interfaces.
"""

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
    """

    @brief Implements the valid operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return json.loads((FIXTURES / "valid/0402.json").read_text())


def inventory(data):
    """

    @brief Implements the inventory operation.
    @param data The data argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return {
        "source_hashes": [r["sha256"] for r in data["source"]["documents"]],
        "evidence_ids": [r["id"] for r in data["evidence"]],
    }


def review(data):
    """

    @brief Implements the review operation.
    @param data The data argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    inv = inventory(data)
    data["revision"]["evidence_review"].update(
        inventory_sha256=sha256(canonical_json(inv)).hexdigest(),
        reviewed_evidence_ids=inv["evidence_ids"],
    )


def store(data, *parents):
    """

    @brief Implements the store operation.
    @param data The data argument.
    @param parents The parents argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return MemoryRevisionStore(
        parents, [inventory(d) for d in (data, *parents)]
    )


def issues(data, *parents, context=CONTEXT, revisions=None):
    """

    @brief Implements the issues operation.
    @param data The data argument.
    @param context The context argument.
    @param revisions The revisions argument.
    @param parents The parents argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return validate_ir(
        data,
        for_generation=True,
        requirements=context,
        revisions=revisions or store(data, *parents),
    )


def codes(data, *parents, **kwargs):
    """

    @brief Implements the codes operation.
    @param data The data argument.
    @param parents The parents argument.
    @param kwargs The kwargs argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return {i.code for i in issues(data, *parents, **kwargs)}


def child(data, key="IR12-2"):
    """

    @brief Implements the child operation.
    @param data The data argument.
    @param key The key argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    result = copy.deepcopy(data)
    result["revision"].update(id=key, parent_id=data["revision"]["id"])
    return result


def put(data, path, value):
    """

    @brief Implements the put operation.
    @param data The data argument.
    @param path The path argument.
    @param value The value argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    prefix, _, token = path.rpartition("/")
    node = resolve_pointer(data, prefix) if prefix else data
    node[int(token) if isinstance(node, list) else token] = value


def override(
    before, path=WIDTH, value=None, kind="QUANTITY_RECORD", key="O-1"
):
    """

    @brief Implements the override operation.
    @param before The before argument.
    @param path The path argument.
    @param value The value argument.
    @param kind The kind argument.
    @param key The key argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the resolution operation.
    @param data The data argument.
    @param key The key argument.
    @param target The target argument.
    @param old The old argument.
    @param selected The selected argument.
    @param base The base argument.
    @param supersedes The supersedes argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the conflict operation.
    @param data The data argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the projected operation.
    @param data The data argument.
    @param context The context argument.
    @param config The config argument.
    @param parents The parents argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return dependency_hash(
        data,
        requirements=context,
        revisions=store(data, *parents),
        configuration=config or CONFIG,
    )


def test_valid_fixture_roundtrip_and_frozen_hash(valid):
    """

    @brief Implements the test_valid_fixture_roundtrip_and_frozen_hash
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_negative_corpus operation.
    @param case The case argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = json.loads((FIXTURES / "invalid" / case["file"]).read_text())
    assert [
        {"code": i.code, "path": i.path} for i in validate_ir(data)
    ] == case["issues"]


def test_store_is_detached(valid):
    """

    @brief Implements the test_store_is_detached operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    repo = MemoryRevisionStore([valid], [inventory(valid)])
    valid["pins"].clear()
    assert len(repo.get_revision("IR12-1")["pins"]) == 2
    repo.get_revision("IR12-1")["pins"].clear()
    assert len(repo.get_revision("IR12-1")["pins"]) == 2


def test_generation_requires_real_history_and_context(valid):
    """

    @brief Implements the
    test_generation_requires_real_history_and_context operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_typed_leaf_overrides operation.
    @param valid The valid argument.
    @param path The path argument.
    @param value The value argument.
    @param kind The kind argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid, path, value, kind)
    assert issues(data, valid) == ()
    assert projected(data, valid) != projected(valid)


def test_quantity_override_has_no_projection_cycle(valid):
    """

    @brief Implements the test_quantity_override_has_no_projection_cycle
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_bad_override_is_rejected operation.
    @param valid The valid argument.
    @param change The change argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid)
    change(data)
    assert validate_ir(data)


def test_override_previous_value_must_match_base(valid):
    """

    @brief Implements the test_override_previous_value_must_match_base
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid, "/pins/0/electrical_type", "input", "STRING")
    data["overrides"][0]["previous_value"] = "output"
    assert "IR_HISTORY" in codes(data, valid)


def test_overlapping_active_overrides_rejected(valid):
    """

    @brief Implements the test_overlapping_active_overrides_rejected
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_unlinking_conflicting_candidate_cannot_pass operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    conflict(valid)
    assert "IR_CONFLICT" in codes(valid)
    valid["package"]["mechanical"]["body_width"]["evidence_ids"] = ["E-001"]
    assert "IR_CONFLICT" in codes(valid)
    resolution(valid, old=["E-CONFLICT"])
    assert issues(valid) == ()


def test_unrelated_history_does_not_block_generator(valid):
    """

    @brief Implements the
    test_unrelated_history_does_not_block_generator operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    conflict(valid)
    context = replace(
        CONTEXT, mandatory_paths=("/pins",), required_paths=("/pins",)
    )
    assert issues(valid, context=context) == ()


def test_selected_evidence_requires_relevance(valid):
    """

    @brief Implements the test_selected_evidence_requires_relevance
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    valid["evidence"][0]["candidate_targets"] = [WIDTH]
    assert "IR_RELEVANCE" in codes(valid)


def test_successive_resolutions_keep_approved_history(valid):
    """

    @brief Implements the
    test_successive_resolutions_keep_approved_history operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_second_resolution_must_keep_conflict_disposition operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    conflict(valid)
    resolution(valid, old=["E-CONFLICT"])
    data = child(valid)
    resolution(data, key="R-2", base="IR12-1", supersedes="R-1")
    assert "IR_CONFLICT" in codes(data, valid)


@pytest.mark.parametrize(
    "domain", ["evidence", "source", "resolutions", "overrides"]
)
def test_history_cannot_be_rewritten(valid, domain):
    """

    @brief Implements the test_history_cannot_be_rewritten operation.
    @param valid The valid argument.
    @param domain The domain argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_candidate_target_dismissal_is_a_transition_error operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_review_inventory_and_acquisition_are_required operation.
    @param valid The valid argument.
    @param change The change argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    change(valid)
    assert issues(valid)


def test_real_provenance_cycle_rejected(valid):
    """

    @brief Implements the test_real_provenance_cycle_rejected operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    valid["evidence"][0]["interpretation"].update(
        status="DERIVED", derivation="cycle", evidence_ids=["E-001"]
    )
    assert "IR_CYCLE" in {i.code for i in validate_ir(valid)}


def result():
    """

    @brief Implements the result operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_non_applicability_is_not_fabricated_pass
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_invalid_applicability_rejected operation.
    @param valid The valid argument.
    @param field The field argument.
    @param value The value argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    record = result()
    record[field] = value
    valid["validation"]["results"] = [record]
    assert validate_ir(valid)


def region(data):
    """

    @brief Implements the region operation.
    @param data The data argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_source_region_contract operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_invalid_source_regions_fail operation.
    @param valid The valid argument.
    @param change The change argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    region(valid)
    change(valid["evidence"][0]["source"])
    assert validate_ir(valid)


def test_ocr_cannot_omit_pixel_transform(valid):
    """

    @brief Implements the test_ocr_cannot_omit_pixel_transform
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    region(valid)
    valid["evidence"][0]["extractor"]["method"] = "ocr"
    valid["evidence"][0]["source"]["render_transform"] = None
    assert "IR_REGION" in {i.code for i in validate_ir(valid)}


def migration_evidence(valid):
    """

    @brief Implements the migration_evidence operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_explicit_migration_preserves_input
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_migration_does_not_guess operation.
    @param valid The valid argument.
    @param field The field argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    supplied = migration_evidence(valid)
    del supplied[field]
    old = ComponentIR.from_file(ROOT / "fixtures/ir/v1.1/valid/0402.json")
    migrated = migrate_v1_1_to_v1_2(old, supplied)
    assert migrated.ir is None and migrated.issues
    assert json.loads(migrated.history)["status"] == "FAILED"


def test_migration_rejects_changed_source_identity(valid):
    """

    @brief Implements the test_migration_rejects_changed_source_identity
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    supplied = migration_evidence(valid)
    supplied["evidence"]["E-001"]["source"]["page"] = 4
    old = ComponentIR.from_file(ROOT / "fixtures/ir/v1.1/valid/0402.json")
    assert migrate_v1_1_to_v1_2(old, supplied).ir is None


def test_projection_audit_changes_do_not_invalidate(valid):
    """

    @brief Implements the
    test_projection_audit_changes_do_not_invalidate operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid)
    before = projected(data, valid)
    data["overrides"][0].update(
        user="another-reviewer", timestamp="2026-09-21T00:00:00Z"
    )
    assert projected(data, valid) == before
    data["overrides"][0]["reason"] = "Changed engineering rationale"
    assert projected(data, valid) != before


def test_placement_only_edit_preserves_geometry_projection(valid):
    """

    @brief Implements the
    test_placement_only_edit_preserves_geometry_projection operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    context = replace(
        CONTEXT, required_paths=("/package",), mandatory_paths=("/package",)
    )
    data = override(valid, "/model_3d/placement/translation_mm/0", 1, "NUMBER")
    assert projected(data, valid, context=context) == projected(
        valid, context=context
    )
    assert projected(data, valid) != projected(valid)


def test_output_reports_not_in_input_projection(valid):
    """

    @brief Implements the test_output_reports_not_in_input_projection
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    before = projected(valid)
    valid["validation"]["results"] = [result()]
    assert projected(valid) == before


def test_source_revision_changes_projection(valid):
    """

    @brief Implements the test_source_revision_changes_projection
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    before = projected(valid)
    valid["source"]["documents"][0]["revision"] = "new"
    valid["identity"]["source_revision"] = "new"
    assert projected(valid) != before


def test_projection_configuration_and_accuracy_cannot_be_omitted(valid):
    """

    @brief Implements the
    test_projection_configuration_and_accuracy_cannot_be_omitted
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    with pytest.raises(IRValidationError):
        projected(valid, config={"runtime": {}})
    valid["model_3d"]["accuracy_class"] = "CLASS_C"
    with pytest.raises(IRValidationError):
        projected(valid)


def test_canonical_hash_independent_process_seeds(valid):
    """

    @brief Implements the test_canonical_hash_independent_process_seeds
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_schema_loading_is_detached operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_whole_record_overrides operation.
    @param valid The valid argument.
    @param path The path argument.
    @param kind The kind argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid, path=path, kind=kind)
    assert issues(data, valid) == ()
    assert len(projected(data, valid)) == 64


def test_override_cannot_authorize_another_value(valid):
    """

    @brief Implements the test_override_cannot_authorize_another_value
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid, "/pins/0/electrical_type", "input", "STRING")
    data["package"]["mechanical"]["body_width"].update(
        status="USER_OVERRIDE", override_id="O-1", source_value=123
    )
    assert "IR_OVERRIDE" in {i.code for i in validate_ir(data)}


def test_replaced_override_preserves_previous_approval(valid):
    """

    @brief Implements the
    test_replaced_override_preserves_previous_approval operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    first = override(valid)
    second = override(first, key="O-2")
    second["revision"]["id"] = "IR12-3"
    second["overrides"][1]["supersedes_override_id"] = "O-1"
    assert issues(second, valid, first) == ()
    assert second["overrides"][0] == first["overrides"][0]
    assert len(projected(second, valid, first)) == 64


def test_retained_decision_supersession_cycle_rejected(valid):
    """

    @brief Implements the
    test_retained_decision_supersession_cycle_rejected operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = override(valid)
    data["overrides"][0]["supersedes_override_id"] = "O-1"
    assert "IR_HISTORY" in {i.code for i in validate_ir(data)}


def test_stored_revision_identity_cannot_be_reused(valid):
    """

    @brief Implements the test_stored_revision_identity_cannot_be_reused
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    repo = MemoryRevisionStore([valid], [inventory(valid)])
    valid["revision"]["description"] = "Changed stored revision"
    assert "IR_HISTORY" in codes(valid, revisions=repo)


def test_reordered_pins_require_explicit_simultaneous_rebindings(valid):
    """

    @brief Implements the
    test_reordered_pins_require_explicit_simultaneous_rebindings
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_history_can_resolve_changed_evidence_selection operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_historical_previous_value_does_not_change_projection operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    first = override(valid, "/pins/0/electrical_type", "input", "STRING")
    other_base = copy.deepcopy(valid)
    other_base["pins"][0]["electrical_type"] = "output"
    second = override(other_base, "/pins/0/electrical_type", "input", "STRING")
    assert ComponentIR(first).sha256 != ComponentIR(second).sha256
    assert projected(first, valid) == projected(second, other_base)


def test_projection_replaces_run_ids_with_content(valid):
    """

    @brief Implements the test_projection_replaces_run_ids_with_content
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_invalid_resolution_target_returns_diagnostics operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    resolution(valid, target="/model_3d/required")
    assert validate_ir(valid)


def test_migration_from_wrong_version_fails_cleanly(valid):
    """

    @brief Implements the
    test_migration_from_wrong_version_fails_cleanly operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    source = ComponentIR.from_file(ROOT / "fixtures/ir/valid/0402.json")
    result = migrate_v1_1_to_v1_2(source, migration_evidence(valid))
    assert result.ir is None
    assert "IR_MIGRATION" in {i.code for i in result.issues}


def test_missing_nominal_values_remain_candidates(valid):
    """

    @brief Implements the test_missing_nominal_values_remain_candidates
    operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_unassigned_evidence_requires_recorded_exclusion operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the
    test_removing_override_requires_explicit_review operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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
    """

    @brief Implements the test_cyclic_revision_ancestry_fails operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    parent = copy.deepcopy(valid)
    parent["revision"]["parent_id"] = "IR12-2"
    data = child(parent)
    assert "IR_HISTORY" in codes(data, parent)


def test_scalar_resolution_pointer_never_crashes_generation(valid):
    """

    @brief Implements the
    test_scalar_resolution_pointer_never_crashes_generation operation.
    @param valid The valid argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    resolution(valid, target="/model_3d/required")
    assert validate_ir(
        valid,
        for_generation=True,
        requirements=CONTEXT,
        revisions=MemoryRevisionStore(),
    )


@pytest.mark.parametrize("label", ["0402", "quantity-override"])
def test_frozen_dependency_projections(valid, label):
    """

    @brief Implements the test_frozen_dependency_projections operation.
    @param valid The valid argument.
    @param label The label argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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


def reordered_revision(before, order, key):
    """

    @brief Build a valid simultaneous reorder, retaining all historical
    links.
    @param before The before argument.
    @param order The order argument.
    @param key The key argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    data = child(before, key)
    data["pins"] = [copy.deepcopy(before["pins"][i]) for i in order]
    data["package"]["pin_count"] = len(order)
    for old in range(len(before["pins"])):
        new = order.index(old) if old in order else None
        if old == new:
            continue
        data["revision"]["target_rebindings"].append(
            dict(
                old_path=f"/pins/{old}",
                new_path=None if new is None else f"/pins/{new}",
                base_revision_id=before["revision"]["id"],
                reason=f"Retain terminal {before['pins'][old]['number']}",
                reviewer="fixture",
                timestamp="2026-09-20T12:00:00Z",
                approval_state="APPROVED",
            )
        )
    return data


@pytest.mark.parametrize("target", ["/pins/0", "/pins/0/name"])
@pytest.mark.parametrize("order", [(1, 0), (1,)])
def test_projection_exclusion_tracks_rebound_candidate(valid, target, order):
    """

    @brief Implements the
    test_projection_exclusion_tracks_rebound_candidate operation.
    @param valid The valid argument.
    @param target The target argument.
    @param order The order argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    raw = copy.deepcopy(valid["evidence"][0])
    raw.update(id="E-RAW", candidate_targets=[])
    replacement = copy.deepcopy(raw)
    replacement.update(id="E-REPLACEMENT", candidate_targets=[target])
    valid["evidence"].extend([raw, replacement])
    valid["pins"][0]["evidence_ids"] = ["E-REPLACEMENT"]
    valid["revision"]["evidence_exclusions"].append(
        dict(
            evidence_id="E-RAW",
            replacement_evidence_ids=["E-REPLACEMENT"],
            reason="Interpretation assigned to original terminal",
            reviewer="fixture",
            timestamp="2026-09-20T12:00:00Z",
            approval_state="APPROVED",
        )
    )
    review(valid)
    selected = "/pins/1/name" if len(order) == 2 else "/pins/0/name"
    context = replace(
        CONTEXT, required_paths=(selected,), mandatory_paths=(selected,)
    )

    def snapshot(root):
        """

        @brief Implements the snapshot operation.
        @param root The root argument.
        @return The callable result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        data = reordered_revision(root, order, "REORDERED")
        assert issues(data, root, context=context) == ()
        return dependency_projection(
            data,
            requirements=context,
            revisions=store(data, root),
            configuration=CONFIG,
        )

    baseline = snapshot(valid)
    assert bool(baseline["dispositions"]) == (len(order) == 2)
    # Compare valid histories without mutating either retained parent.
    changed = copy.deepcopy(valid)
    changed["revision"]["evidence_exclusions"][0]["reason"] = "New rationale"
    assert (canonical_json(snapshot(changed)) != canonical_json(baseline)) == (
        len(order) == 2
    )


@pytest.mark.parametrize("first_binding", [0, 1])
def test_projection_rebinding_tracks_entire_chain(valid, first_binding):
    """

    @brief Implements the test_projection_rebinding_tracks_entire_chain
    operation.
    @param valid The valid argument.
    @param first_binding The first_binding argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    third = copy.deepcopy(valid["pins"][1])
    third.update(number="3", name="3")
    third["physical"]["topology_index"] = 1
    valid["pins"].append(third)
    valid["package"]["pin_count"] = 3
    valid["evidence"][0]["candidate_targets"].append("/pins/2")
    context = replace(
        CONTEXT,
        required_paths=("/pins/2/name",),
        mandatory_paths=("/pins/2/name",),
    )

    def snapshot(reason=None):
        """

        @brief Implements the snapshot operation.
        @param reason The reason argument.
        @return The callable result.
        @details Implements the documented behavior without changing the
        public contract.

        """
        first = reordered_revision(valid, (1, 0, 2), "REORDER-1")
        if reason:
            first["revision"]["target_rebindings"][first_binding]["reason"] = (
                reason
            )
        second = reordered_revision(first, (0, 2, 1), "REORDER-2")
        assert issues(second, valid, first, context=context) == ()
        return dependency_projection(
            second,
            requirements=context,
            revisions=store(second, valid, first),
            configuration=CONFIG,
        )

    baseline = snapshot()
    assert [
        (r["old_path"], r["new_path"]) for r in baseline["rebindings"]
    ] == [
        ("/pins/0", "/pins/1"),
        ("/pins/1", "/pins/2"),
    ]
    assert (
        canonical_json(snapshot("New rationale")) != canonical_json(baseline)
    ) == (first_binding == 0)
