"""Revised Phase 2: candidates, provenance, migration and packaging."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from partsmith.ir import (
    SUPPORTED_VERSIONS,
    ComponentIR,
    RequirementsContext,
    canonical_json,
    load_schema,
    migrate_v1_0_to_v1_1,
    normalize_ir,
    validate_ir,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/ir/v1.1"
CASES = json.loads((FIXTURES / "invalid/expected.json").read_text())
WIDTH = "/package/mechanical/body_width"
REQUIRED = ("/identity", "/pins", "/package", "/footprint", "/model_3d")
CONTEXT = RequirementsContext(
    "synthetic-0402", "test-1", "test-1", "test-1", REQUIRED, REQUIRED
)


@pytest.fixture
def valid():
    return json.loads(
        (FIXTURES / "valid/0402.json").read_text(encoding="utf-8")
    )


def codes(data, generation=False, context=CONTEXT):
    return {
        issue.code
        for issue in validate_ir(
            data, for_generation=generation, requirements=context
        )
    }


def historical(data, status="CONFLICTING"):
    old = copy.deepcopy(data["evidence"][0])
    old["id"] = "E-OLD"
    old["interpretation"]["status"] = status
    data["evidence"].append(old)
    return old


def resolution(data):
    decision = dict(
        id="R-1",
        target_path=WIDTH,
        superseded_evidence_ids=["E-OLD"],
        selected_evidence_ids=["E-001"],
        override_id=None,
        decision="select",
        reason="Source correction",
        reviewer="fixture-reviewer",
        timestamp="2026-09-19T12:00:00Z",
        approval_state="APPROVED",
    )
    data["resolutions"].append(decision)
    return decision


def standard(data):
    record = dict(
        id="S-1",
        organization="Synthetic",
        document="Test Method",
        revision="1",
        reference="controlled:test-method-1",
        access_date="2026-09-19",
        evidence_ids=["E-001"],
    )
    data["standards"].append(record)
    width = data["package"]["mechanical"]["body_width"]
    width.update(status="STANDARD", standard_id="S-1")
    return record


def override(data):
    width = data["package"]["mechanical"]["body_width"]
    previous = dict(
        source_value=None,
        source_unit=None,
        status="MISSING",
        evidence_ids=[],
        unresolved_reason="Original measurement absent",
    )
    width.update(status="USER_OVERRIDE", override_id="O-1")
    record = dict(
        id="O-1",
        path=WIDTH,
        previous_value=previous,
        new_value=copy.deepcopy(width),
        reason="Reviewed measurement",
        user="fixture-reviewer",
        timestamp="2026-09-19T12:00:00Z",
        evidence_reference="E-001",
        approval_state="APPROVED",
    )
    data["overrides"].append(record)
    return record


def test_phase_two_ir11_gate(valid):
    before = copy.deepcopy(valid)
    assert codes(valid, True) == set()
    ir = ComponentIR(valid)
    expected = (FIXTURES / "expected/0402.canonical.json").read_bytes()
    assert ir.canonical_bytes == expected
    assert (
        ir.sha256
        == sha256(expected).hexdigest()
        == (FIXTURES / "expected/0402.sha256").read_text().strip()
    )
    assert ComponentIR.from_json(expected).canonical_bytes == expected
    assert ir.data["package"]["mechanical"]["body_width"][
        "normalized_value"
    ] == Decimal("0.5")
    assert valid == before


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_offline_schema_packaging(version):
    schema = load_schema(version)
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema_version"]["const"] == version
    name = f"component-ir-{version}.schema.json"
    # Editable runs resolve the source schema; wheel runs must use resources.
    resource = files("partsmith.ir").joinpath(name)
    if "site-packages" in str(files("partsmith.ir")):
        assert resource.is_file()
        assert resource.read_bytes() == (ROOT / "schemas" / name).read_bytes()
    assert not any(
        ref.startswith(("http:", "https:")) for ref in _refs(schema)
    )


def _refs(node):
    if isinstance(node, dict):
        if "$ref" in node:
            yield node["$ref"]
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["file"])
def test_negative_fixture(case):
    data = json.loads((FIXTURES / "invalid" / case["file"]).read_text())
    issues = validate_ir(
        data, for_generation=case["for_generation"], requirements=CONTEXT
    )
    assert [(i.code, i.path) for i in issues] == [(case["code"], case["path"])]
    assert issues == validate_ir(
        data, for_generation=case["for_generation"], requirements=CONTEXT
    )


def test_negative_inventory():
    assert {c["file"] for c in CASES} == {
        p.name
        for p in (FIXTURES / "invalid").glob("*.json")
        if p.name != "expected.json"
    }


@pytest.mark.parametrize(
    "status", ["UNKNOWN", "INFERRED", "AMBIGUOUS", "CONFLICTING", "MISSING"]
)
@pytest.mark.parametrize("unit", [None, "mm"])
def test_missing_candidate_does_not_invent_number(valid, status, unit):
    value = valid["package"]["mechanical"]["body_width"]
    value.update(
        source_value=None,
        source_unit=unit,
        status=status,
        unresolved_reason="No authoritative measurement",
    )
    ir = normalize_ir(valid)
    assert (
        ir["package"]["mechanical"]["body_width"]["normalized_value"] is None
    )
    assert ir["package"]["mechanical"]["body_width"]["normalized_unit"] is None
    assert codes(ir, True) == {"IR_UNRESOLVED"}


def test_unknown_unit_and_required_reason(valid):
    value = valid["package"]["mechanical"]["body_width"]
    value.update(source_unit=None, status="UNKNOWN")
    assert "IR_SCHEMA" in codes(valid)
    value["unresolved_reason"] = "Unit absent"
    assert codes(valid) == set()
    assert "IR_UNRESOLVED" in codes(valid, True)


@pytest.mark.parametrize(
    "change",
    [
        dict(source_value=1, status="MISSING"),
        dict(source_value=None, status="DIRECT"),
        dict(
            source_value=None,
            status="UNKNOWN",
            normalized_value=1,
            normalized_unit="mm",
        ),
        dict(source_value=None, status="UNKNOWN", source_min=0, source_max=1),
    ],
)
def test_invalid_candidate_combinations(valid, change):
    value = valid["package"]["mechanical"]["body_width"]
    value.update(unresolved_reason="Missing", **change)
    assert codes(valid) & {"IR_SCHEMA", "IR_UNIT"}


def test_active_history_resolution_and_hash(valid):
    original = ComponentIR(valid)
    historical(valid)
    decision = resolution(valid)
    assert codes(valid, True) == set()
    assert ComponentIR(valid).sha256 != original.sha256
    assert valid["evidence"][1]["interpretation"]["status"] == "CONFLICTING"
    decision["selected_evidence_ids"] = ["E-OLD"]
    assert "IR_RESOLUTION" in codes(valid, True)


def test_active_unresolved_evidence_cannot_be_hidden(valid):
    historical(valid)
    valid["package"]["mechanical"]["body_width"]["evidence_ids"] = ["E-OLD"]
    assert "IR_UNRESOLVED" in codes(valid, True)


@pytest.mark.parametrize(
    "change",
    [
        dict(required_paths=()),
        dict(mandatory_paths=()),
        dict(required_paths=(WIDTH,)),
        dict(generator_version=""),
        dict(context_version="unknown"),
        dict(required_paths=("/evidence",)),
    ],
)
def test_context_cannot_omit_mandatory_inputs(valid, change):
    assert "IR_REQUIREMENTS" in codes(valid, True, replace(CONTEXT, **change))


def test_context_required_and_artifact_specific(valid):
    assert "IR_REQUIREMENTS" in codes(valid, True, None)
    valid["package"]["mechanical"]["body_width"]["status"] = "MISSING"
    valid["package"]["mechanical"]["body_width"].update(
        source_value=None, unresolved_reason="Absent"
    )
    symbol = RequirementsContext(
        "symbol", "1", "1", "1", ("/pins",), ("/pins",)
    )
    assert codes(valid, True, symbol) == set()
    assert "IR_UNRESOLVED" in codes(valid, True)


@pytest.mark.parametrize(
    "field", ["selected_evidence_ids", "superseded_evidence_ids"]
)
def test_resolution_references_must_resolve(valid, field):
    historical(valid)
    resolution(valid)[field] = ["absent"]
    assert codes(valid) & {"IR_REFERENCE", "IR_RESOLUTION"}


def test_cycles_and_dangling_history_fail_structurally(valid):
    other = historical(valid, "DERIVED")
    other["interpretation"].update(
        evidence_ids=["E-001"], derivation="Synthetic relationship"
    )
    valid["evidence"][0]["interpretation"].update(
        status="DERIVED",
        evidence_ids=["E-OLD"],
        derivation="Reverse relationship",
    )
    assert "IR_CYCLE" in codes(valid)
    other["interpretation"]["evidence_ids"] = ["absent"]
    assert "IR_REFERENCE" in codes(valid)


def test_approved_override_checks_binding_and_preserves_null_old_value(valid):
    record = override(valid)
    assert codes(valid, True) == set()
    assert (
        ComponentIR(valid).data["overrides"][0]["previous_value"][
            "source_value"
        ]
        is None
    )
    record["new_value"]["source_value"] = 42
    assert "IR_OVERRIDE" in codes(valid, True)


@pytest.mark.parametrize("state", ["PENDING", "REJECTED"])
def test_unapproved_override_blocks_only_when_active(valid, state):
    record = override(valid)
    record["approval_state"] = state
    assert "IR_OVERRIDE" in codes(valid, True)
    width = valid["package"]["mechanical"]["body_width"]
    width["status"] = "DIRECT"
    del width["override_id"]
    assert codes(valid, True) == set()


def test_zero_optional_feature_requires_pdl_declaration(valid):
    mechanical = valid["package"]["mechanical"]
    mechanical["chamfer"] = copy.deepcopy(mechanical["body_width"])
    mechanical["chamfer"]["source_value"] = 0
    assert codes(valid) == set()
    assert "IR_DIMENSION" in codes(valid, True)
    context = replace(
        CONTEXT, zero_allowed_paths=("/package/mechanical/chamfer",)
    )
    assert codes(valid, True, context) == set()
    mechanical["body_width"]["source_value"] = 0
    assert "IR_DIMENSION" in codes(
        valid,
        True,
        replace(
            context, zero_allowed_paths=context.zero_allowed_paths + (WIDTH,)
        ),
    )


def test_unversioned_identity_uses_actual_hash(valid):
    doc = valid["source"]["documents"][0]
    doc["revision"] = valid["identity"]["source_revision"] = "UNVERSIONED"
    assert "IR_SCHEMA" in codes(valid)
    doc["revision_basis"] = dict(
        kind="content_hash",
        sha256=doc["sha256"],
        captured_at="2026-09-19T12:00:00Z",
    )
    assert codes(valid, True) == set()
    doc["revision_basis"]["sha256"] = "0" * 64
    assert "IR_IDENTITY" in codes(valid)


def test_structured_standard_and_translation(valid):
    record = standard(valid)
    evidence = valid["evidence"][0]
    evidence["translation"] = dict(
        original_text=evidence["extracted"]["text"],
        translated_text="Synthetic translation",
        source_language="en",
        target_language="fr",
        provider="manual",
        model="not_applicable",
        timestamp="2026-09-19T12:00:00Z",
    )
    assert codes(valid, True) == set()
    original_hash = ComponentIR(valid).sha256
    evidence["translation"]["translated_text"] += " corrected"
    assert ComponentIR(valid).sha256 != original_hash
    record["revision"] = "UNKNOWN"
    assert "IR_PROVENANCE" in codes(valid, True)
    record["revision"] = "1"
    evidence["translation"]["original_text"] = "Wrong source"
    assert "IR_PROVENANCE" in codes(valid)


@pytest.mark.parametrize(
    "category", ["MANUFACTURER_RECOMMENDED", "IPC_DERIVED", "PDL_DERIVED"]
)
def test_land_pattern_enum(valid, category):
    valid["footprint"]["land_pattern_source"] = category
    assert codes(valid) == set()


def migration_inputs(valid):
    old = json.loads((ROOT / "fixtures/ir/valid/0402.json").read_text())
    supplied = dict(
        placement=valid["model_3d"]["placement"],
        reason="Synthetic fixture axes explicitly confirmed",
    )
    return old, supplied


def test_explicit_migration_preserves_original_and_is_deterministic(valid):
    old, supplied = migration_inputs(valid)
    before = copy.deepcopy(old)
    source = ComponentIR(old)
    result = migrate_v1_0_to_v1_1(source, supplied)
    assert result.issues == ()
    assert result.ir.canonical_bytes == ComponentIR(valid).canonical_bytes
    assert result.history == migrate_v1_0_to_v1_1(old, supplied).history
    assert json.loads(result.history)["source_ir_hash"] == source.sha256
    assert old == before
    assert codes(result.ir.data, True) == set()


@pytest.mark.parametrize("missing", ["placement", "reason"])
def test_migration_requires_frame_evidence(valid, missing):
    old, supplied = migration_inputs(valid)
    del supplied[missing]
    result = migrate_v1_0_to_v1_1(old, supplied)
    assert result.ir is None
    assert "IR_MIGRATION" in {i.code for i in result.issues}


@pytest.mark.parametrize("category", ["STANDARD", "USER_OVERRIDE"])
def test_migration_recovers_source_category(valid, category):
    old, supplied = migration_inputs(valid)
    old["footprint"]["land_pattern_source"] = category
    assert migrate_v1_0_to_v1_1(old, supplied).ir is None
    supplied["land_pattern_source"] = "IPC_DERIVED"
    assert migrate_v1_0_to_v1_1(old, supplied).issues == ()


def test_migration_does_not_invent_revision(valid):
    old, supplied = migration_inputs(valid)
    del old["source"]["documents"][0]["revision"]
    assert migrate_v1_0_to_v1_1(old, supplied).ir is None
    supplied["document_revisions"] = {"D-001": {"revision": "synthetic-1"}}
    assert migrate_v1_0_to_v1_1(old, supplied).issues == ()
    old["source"]["documents"][0]["revision"] = "conflicting"
    assert migrate_v1_0_to_v1_1(old, supplied).ir is None


def test_fresh_process_hash_seeds():
    path = str(FIXTURES / "valid/0402.json")
    program = (
        "from partsmith.ir import ComponentIR; import sys; "
        "print(ComponentIR.from_file(sys.argv[1]).sha256)"
    )
    expected = (FIXTURES / "expected/0402.sha256").read_text().strip()
    for seed in ("1", "7654321"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        output = subprocess.check_output(
            [sys.executable, "-c", program, path], env=env, text=True
        ).strip()
        assert output == expected


def test_canonical_profile_unchanged(valid):
    # Independent canonical-json profile regression rather than a new profile.
    assert (
        canonical_json({"z": Decimal("1.000"), "a": "e\u0301"})
        == '{"a":"é","z":1}'.encode()
    )


@pytest.mark.parametrize("state", ["PENDING", "REJECTED"])
def test_active_resolution_requires_approval(valid, state):
    historical(valid)
    resolution(valid)["approval_state"] = state
    assert "IR_RESOLUTION" in codes(valid, True)


def test_leaf_requirement_cannot_bypass_status(valid):
    valid["package"]["mechanical"]["body_width"]["status"] = "CONFLICTING"
    leaf = WIDTH + "/source_value"
    context = replace(CONTEXT, required_paths=(leaf,), mandatory_paths=(leaf,))
    assert "IR_UNRESOLVED" in codes(valid, True, context)


@pytest.mark.parametrize(
    "field",
    ["organization", "document", "revision", "access_date", "evidence_ids"],
)
def test_standard_metadata_is_structured_and_required(valid, field):
    record = standard(valid)
    del record[field]
    assert "IR_SCHEMA" in codes(valid)


def test_standard_provenance_cycle(valid):
    standard(valid)
    valid["evidence"][0]["interpretation"].update(
        status="STANDARD", standard_id="S-1"
    )
    assert "IR_CYCLE" in codes(valid)


def test_date_validation_and_empty_standard_evidence(valid):
    record = standard(valid)
    record["access_date"] = "2026-02-30"
    assert "IR_SCHEMA" in codes(valid)
    record["access_date"] = "2026-09-19"
    record["evidence_ids"] = []
    assert "IR_PROVENANCE" in codes(valid, True)


def test_escaped_requirement_pointer(valid):
    valid["electrical"]["a/b~c"] = dict(
        value=None, status="UNKNOWN", evidence_ids=[]
    )
    path = "/electrical/a~1b~0c"
    context = replace(CONTEXT, required_paths=(path,), mandatory_paths=(path,))
    assert "IR_UNRESOLVED" in codes(valid, True, context)


@pytest.mark.parametrize(
    "path", ["/pins/01", "/pins/-1", "/pins/99", "/electrical/unknown~2key"]
)
def test_invalid_requirement_pointer(valid, path):
    context = replace(CONTEXT, required_paths=(path,), mandatory_paths=(path,))
    assert "IR_REQUIREMENTS" in codes(valid, True, context)


def test_unknown_version_has_no_fallback(valid):
    valid["schema_version"] = "99.0"
    assert codes(valid) == {"IR_VERSION"}


def test_migration_rejects_already_migrated_source(valid):
    _, supplied = migration_inputs(valid)
    result = migrate_v1_0_to_v1_1(valid, supplied)
    assert result.ir is None
    assert any(issue.path == "/schema_version" for issue in result.issues)


def test_migration_standard_requires_explicit_metadata(valid):
    old, supplied = migration_inputs(valid)
    old["standards"] = [
        dict(
            id="S-1",
            name="Synthetic",
            revision="1",
            reference="controlled:test-method-1",
        )
    ]
    assert migrate_v1_0_to_v1_1(old, supplied).ir is None
    record = standard(valid)
    supplied["standards"] = {"S-1": record}
    assert migrate_v1_0_to_v1_1(old, supplied).issues == ()
    record["revision"] = "different"
    assert migrate_v1_0_to_v1_1(old, supplied).ir is None


def test_original_artifacts_preserved():
    evidence = json.loads(
        (ROOT / "docs/gates/phase-2-artifacts.json").read_text()
    )
    for name, digest in evidence["sha256"].items():
        if name.startswith(("schemas/", "fixtures/")):
            assert sha256((ROOT / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "name",
    ["status", "source_unit", "evidence_ids", "standard_id", "override_id"],
)
def test_named_properties_do_not_impersonate_metadata(valid, name):
    valid["electrical"][name] = dict(
        value=1, status="DIRECT", evidence_ids=["E-001"]
    )
    context = replace(CONTEXT, required_paths=REQUIRED + ("/electrical",))
    assert codes(valid, True, context) == set()
