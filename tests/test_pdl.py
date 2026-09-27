"""Phase 3 Package Definition Library gate tests."""

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from partsmith.ir.canonical import parse_json
from partsmith.pdl import (
    PDL,
    PDLValidationError,
    ir_pdl_issues,
    list_pdls,
    load_pdl,
    load_schema,
    pdl_hash,
    resolve_pdl,
    validate_pdl,
)

ROOT = Path(__file__).parents[1]
ENTRY = ROOT / "pdl/entries/synthetic-0402@1.0.json"
IR = ROOT / "fixtures/ir/v1.2/valid/0402.json"
GOLDEN = ROOT / "fixtures/pdl/golden/GOLD-0402-001.json"
CASES = ROOT / "fixtures/pdl/invalid/cases.json"


@pytest.fixture
def valid():
    return parse_json(ENTRY.read_bytes())


def _target(data, path):
    tokens = path.strip("/").split("/")
    parent = data
    for token in tokens[:-1]:
        parent = (
            parent[int(token)] if isinstance(parent, list) else parent[token]
        )
    token = tokens[-1]
    return parent, int(token) if isinstance(parent, list) else token


def test_phase_three_gate(valid):
    Draft202012Validator.check_schema(load_schema("1.0"))
    pdl = load_pdl("synthetic-0402", "1.0")
    assert pdl.data == valid
    assert pdl.sha256 == pdl_hash(valid)
    assert validate_pdl(valid) == ()
    assert list_pdls() == (("synthetic-0402", "1.0"),)

    ir = parse_json(IR.read_bytes())
    assert ir_pdl_issues(ir, pdl.data) == ()
    assert (
        resolve_pdl("chip_resistor", "0402", {"1", "2"}).sha256 == pdl.sha256
    )


def test_golden_fixture_binds_exact_ir_and_pdl_bytes():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    ir_path = ROOT / golden["component_ir"]["path"]
    source_path = ROOT / golden["source"]["path"]
    profile_path = ROOT / golden["release_profile"]["path"]
    pdl = load_pdl(golden["pdl"]["id"], golden["pdl"]["revision"])
    assert golden["id"] == "GOLD-0402-001"
    assert golden["production_evidence"] is False
    assert (
        sha256(ir_path.read_bytes()).hexdigest()
        == golden["component_ir"]["sha256"]
    )
    assert (
        sha256(source_path.read_bytes()).hexdigest()
        == golden["source"]["sha256"]
    )
    assert (
        pdl.data["sources"][0]["content_sha256"] == golden["source"]["sha256"]
    )
    assert (
        sha256(ENTRY.read_bytes()).hexdigest() == golden["pdl"]["file_sha256"]
    )
    assert pdl.sha256 == golden["pdl"]["content_sha256"]
    assert (
        sha256(profile_path.read_bytes()).hexdigest()
        == golden["release_profile"]["file_sha256"]
    )
    assert pdl.data["release_profile"] == {
        key: golden["release_profile"][key]
        for key in ("id", "version", "sha256")
    }


@pytest.mark.parametrize(
    "case",
    json.loads(CASES.read_text(encoding="utf-8")),
    ids=lambda case: case["name"],
)
def test_invalid_pdl_cases_fail_deterministically(valid, case):
    data = copy.deepcopy(valid)
    parent, key = _target(data, case["path"])
    if case["operation"] == "remove":
        del parent[key]
    else:
        parent[key] = case["value"]
    if case["name"] != "bad-content-hash":
        data["content_sha256"] = pdl_hash(data)
    issue = (case["issue_path"], case["code"])
    assert issue in {(item.path, item.code) for item in validate_pdl(data)}


def test_loader_requires_exact_safe_identity(tmp_path, valid):
    with pytest.raises(PDLValidationError, match="PDL_NOT_FOUND"):
        load_pdl("missing", root=tmp_path)
    with pytest.raises(PDLValidationError, match="PDL_ID"):
        load_pdl("../unsafe", root=tmp_path)

    for revision in ("1.0", "2.0"):
        data = copy.deepcopy(valid)
        data["revision"] = revision
        data["change_history"][-1]["revision"] = revision
        data["content_sha256"] = pdl_hash(data)
        (tmp_path / f"synthetic-0402@{revision}.json").write_bytes(
            PDL(data).canonical_bytes
        )
    with pytest.raises(PDLValidationError, match="PDL_REVISION_REQUIRED"):
        load_pdl("synthetic-0402", root=tmp_path)

    mismatched = copy.deepcopy(valid)
    mismatched["id"] = "mismatched"
    mismatched["revision"] = "2.0"
    mismatched["change_history"][-1]["revision"] = "2.0"
    mismatched["content_sha256"] = pdl_hash(mismatched)
    (tmp_path / "mismatched@1.0.json").write_bytes(
        PDL(mismatched).canonical_bytes
    )
    with pytest.raises(PDLValidationError, match="PDL_REVISION"):
        load_pdl("mismatched", root=tmp_path)

    assert (
        load_pdl("synthetic-0402", "2.0", root=tmp_path).data["revision"]
        == "2.0"
    )


@pytest.mark.parametrize(
    ("profile_id", "version"),
    [("../escape", "1.0"), ("mvp-1", "../escape"), ("mvp/1", "1.0")],
)
def test_release_profile_requires_safe_identity(tmp_path, profile_id, version):
    from partsmith.pdl import load_release_profile

    with pytest.raises(PDLValidationError, match="PDL_PROFILE_"):
        load_release_profile(profile_id, version, root=tmp_path)


def test_release_profile_rejects_non_object_json(tmp_path):
    from partsmith.pdl import load_release_profile

    (tmp_path / "mvp-1@1.0.json").write_text("[]", encoding="utf-8")
    with pytest.raises(PDLValidationError, match="PDL_PROFILE"):
        load_release_profile("mvp-1", "1.0", root=tmp_path)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("package", "variant"), "0603"),
        (("package", "pin_count"), 3),
        (("pins", 0, "number"), "A1"),
        (("pins", 0, "physical", "topology_side"), "north"),
        (("pins", 0, "physical", "topology_index"), 1),
    ],
)
def test_ir_pdl_topology_mismatches_are_rejected(path, value):
    ir = parse_json(IR.read_bytes())
    target = ir
    for token in path[:-1]:
        target = target[token]
    target[path[-1]] = value
    assert ir_pdl_issues(ir, load_pdl("synthetic-0402").data)


def test_linear_terminal_order_is_validated(valid):
    data = copy.deepcopy(valid)
    data["topology"]["terminals"].reverse()
    data["content_sha256"] = pdl_hash(data)
    issues = validate_pdl(data)
    assert ("/topology/terminals", "PDL_TOPOLOGY") in {
        (item.path, item.code) for item in issues
    }
