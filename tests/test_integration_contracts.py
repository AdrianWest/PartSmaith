"""@package tests.test_integration_contracts
@brief Exercises Phase 13.1 closed shapes, identities and binding failures.
@details Synthetic reports test contracts only, never native installation.
"""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.integration import (
    FailureCode,
    InstallationManifest,
    IntegrationAuditEnvelope,
    IntegrationAuthorizationBinding,
    IntegrationError,
    IntegrationJournal,
    IntegrationPlan,
    IntegrationValidationReport,
    ResourcePolicy,
    portable_path,
    verify_contract_bindings,
    verify_journal_binding,
)
from partsmith.integration.bindings import verify_audit_binding
from partsmith.integration.schema import validate_shape

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "integration"
CONTRACTS = {
    "plan": IntegrationPlan,
    "manifest": InstallationManifest,
    "pre-validation": IntegrationValidationReport,
    "post-validation": IntegrationValidationReport,
    "authorization": IntegrationAuthorizationBinding,
    "audit": IntegrationAuditEnvelope,
    "journal": IntegrationJournal,
}


def fixture(name: str):
    """@brief Loads one frozen valid golden contract.
    @param name Fixture identity in CONTRACTS.
    @return Validated immutable contract instance.
    @details Fixtures contain no live target or approval authority.
    """
    data = json.loads((ROOT / "valid" / f"{name}.json").read_bytes())
    return CONTRACTS[name](data)


def verify(**changes) -> None:
    """@brief Verifies the full golden dependency graph with selected changes.
    @param changes Replacement graph objects or observed bindings.
    @return None.
    @details Uses only synthetic bytes from the declared fixture inventory.
    """
    plan, manifest = fixture("plan"), fixture("manifest")
    pre = fixture("pre-validation")
    arguments = {
        "plan": plan,
        "manifest": manifest,
        "reports": {pre.sha256: pre},
        "post_manifest": fixture("post-validation"),
        "authorization": fixture("authorization"),
        "current_target": plan.data["target"],
        "current_base": plan.data["expected_base"],
        "files": {
            path: bytes.fromhex(content)
            for path, content in json.loads(
                (ROOT / "files.json").read_bytes()
            ).items()
        },
    }
    arguments.update(changes)
    verify_contract_bindings(**arguments)


def rebound(plan=None, files=None) -> dict:
    """@brief Rebuilds exact downstream references after intentional changes.
    @param plan Optional replacement frozen plan.
    @param files Optional replacement complete final byte inventory.
    @return Full arguments for binding verification with fresh content hashes.
    @details Synthetic successful reports exercise reference validation only.
    """
    plan = plan or fixture("plan")
    if files is None:
        files = {
            path: bytes.fromhex(content)
            for path, content in json.loads(
                (ROOT / "files.json").read_bytes()
            ).items()
        }
    p = plan.data
    shared = {
        key: p[key]
        for key in ("target", "expected_base", "sources", "mappings")
    }
    shared["files"] = [
        {
            "path": path,
            "sha256": sha256(blob).hexdigest(),
            "byte_length": len(blob),
        }
        for path, blob in sorted(files.items())
    ]
    r = fixture("pre-validation").data
    r.update(
        shared,
        plan_hash=plan.sha256,
        comparator_version=p["versions"]["comparator"],
    )
    pre = IntegrationValidationReport(r)
    m = fixture("manifest").data
    m.update(
        shared,
        plan_hash=plan.sha256,
        versions=p["versions"],
        semantic_validation_hash=pre.sha256,
    )
    for check in m["required_checks"]:
        check["report_hash"] = pre.sha256
    manifest = InstallationManifest(m)
    r.update(phase="POST_MANIFEST", manifest_hash=manifest.sha256)
    post = IntegrationValidationReport(r)
    a = fixture("authorization").data
    a.update(
        plan_hash=plan.sha256,
        installation_manifest_hash=manifest.sha256,
        target=p["target"],
        expected_base=p["expected_base"],
        required_checks=m["required_checks"],
        post_manifest_check_hash=post.sha256,
    )
    return {
        "plan": plan,
        "manifest": manifest,
        "reports": {pre.sha256: pre},
        "post_manifest": post,
        "authorization": IntegrationAuthorizationBinding(a),
        "current_target": p["target"],
        "current_base": p["expected_base"],
        "files": files,
    }


@pytest.mark.parametrize("name", CONTRACTS)
def test_golden_canonical_and_frozen(name):
    """@brief Verifies deterministic canonical hashes and deep immutability.
    @param name Golden contract kind.
    @return None.
    @details Mutating input/output dictionaries cannot alter frozen bytes.
    """
    document = fixture(name)
    golden = json.loads((ROOT / "golden.json").read_bytes())
    assert document.sha256 == golden[name]
    data = document.data
    rebuilt = CONTRACTS[name](dict(reversed(list(data.items()))))
    assert rebuilt.canonical_bytes == document.canonical_bytes
    data["schema_version"] = "tampered"
    assert document.data["schema_version"] == "1.0"
    with pytest.raises(FrozenInstanceError):
        document._bytes = b"tampered"


@pytest.mark.parametrize("name", CONTRACTS)
def test_closed_unknown_and_every_missing_required_field(name):
    """@brief Rejects unknown versions, fields and every omitted root field.
    @param name Contract fixture kind.
    @return None.
    @details Transient IPC tokens are rejected as unknown contract data.
    """
    document = fixture(name)
    for field in document.data:
        data = document.data
        del data[field]
        with pytest.raises(ValueError):
            CONTRACTS[name](data)
    for field, value in (
        ("ipc_token", "secret-fixture-value"),
        ("schema_version", "2.0"),
        ("sha256", "a" * 64),
    ):
        data = document.data
        data[field] = value
        with pytest.raises(ValueError) as error:
            CONTRACTS[name](data)
        assert "secret-fixture-value" not in str(error.value)


@pytest.mark.parametrize(
    "path", sorted((ROOT / "invalid").glob("*.json")), ids=lambda p: p.stem
)
def test_invalid_plan_fixtures(path):
    """@brief Rejects declared negative plan fixtures before use.
    @param path Invalid fixture file.
    @return None.
    @details Covers omissions, digests, cycles, path aliases and stale bases.
    """
    with pytest.raises(ValueError):
        IntegrationPlan(json.loads(path.read_bytes()))


@pytest.mark.parametrize(
    "path",
    [
        "../item",
        "./item",
        "/item",
        "C:/item",
        "dir\\item",
        "dir//item",
        "dir/../item",
        "NUL.step",
        "aux.txt",
        "COM1",
        "COM¹.step",
        "LPT².txt",
        "NUL .step",
        "CONIN$",
        "item.",
        "item ",
        "item\x00",
        "dir:e",
        "e\u0301.step",
        "dir/" + "a" * 64 + ".step",
    ],
)
def test_unsafe_windows_paths(path):
    """@brief Rejects portable path aliases and generation hash cycles.
    @param path Unsafe path spelling.
    @return None.
    @details Includes reserved Windows names and decomposed Unicode aliases.
    """
    with pytest.raises(ValueError):
        portable_path(path)


def test_acyclic_graph_and_journal():
    """@brief Resolves valid golden staged content and journal references.
    @return None.
    @details All check references resolve to exact supplied report bytes.
    """
    verify()
    verify_journal_binding(
        fixture("journal"),
        fixture("plan"),
        fixture("manifest"),
        fixture("authorization"),
    )
    data = fixture("journal").data
    data["authorization_hash"] = "c" * 64
    with pytest.raises(IntegrationError):
        verify_journal_binding(
            IntegrationJournal(data),
            fixture("plan"),
            fixture("manifest"),
            fixture("authorization"),
        )


@pytest.mark.parametrize(
    "field", ["target", "expected_base", "sources", "mappings", "versions"]
)
def test_changed_cross_object_bindings(field):
    """@brief Rejects stale target, base, source, mapping or version bindings.
    @param field Changed installation-manifest binding.
    @return None.
    @details A self-consistent shape still cannot substitute for exact content.
    """
    data = fixture("manifest").data
    if field == "target":
        data[field]["project_id"] = "other-project"
    elif field == "expected_base":
        data[field].update(generation_hash="c" * 64, manifest_hash="c" * 64)
    elif field == "sources":
        data[field][0]["artifacts"][0]["sha256"] = "c" * 64
    elif field == "mappings":
        data[field][0]["symbol_name"] = "changed"
    else:
        data[field]["serializer"] = "2.0"
    with pytest.raises(IntegrationError):
        verify(manifest=InstallationManifest(data))


def test_tampered_staged_files_and_unresolved_reports():
    """@brief Rejects changed, missing or extra staged bytes and copied hashes.
    @return None.
    @details Knowing a successful report digest cannot replace its object.
    """
    files = {
        path: bytes.fromhex(content)
        for path, content in json.loads(
            (ROOT / "files.json").read_bytes()
        ).items()
    }
    for mutation in ("tamper", "missing", "extra"):
        changed = dict(files)
        path = next(iter(changed))
        if mutation == "tamper":
            changed[path] += b"tampered"
        elif mutation == "missing":
            del changed[path]
        else:
            changed["unmanaged.step"] = b"extra"
        with pytest.raises(IntegrationError):
            verify(files=changed)
    with pytest.raises(IntegrationError):
        verify(reports={})


@pytest.mark.parametrize("rule", range(4))
def test_failed_or_excluded_checks_cannot_authorize(rule):
    """@brief Rejects rehashed failed native and semantic report content.
    @param rule Required rule index.
    @return None.
    @details Updating references cannot bypass a failed applicable check.
    """
    for status in ("FAIL", None):
        data = fixture("pre-validation").data
        data["results"][rule]["status"] = status
        if status is None:
            data["results"][rule]["applicability"] = "NOT_APPLICABLE"
        report = IntegrationValidationReport(data)
        data = fixture("manifest").data
        for check in data["required_checks"]:
            check["report_hash"] = report.sha256
        data["semantic_validation_hash"] = report.sha256
        with pytest.raises(IntegrationError):
            verify(
                manifest=InstallationManifest(data),
                reports={report.sha256: report},
            )


def test_audit_identity_does_not_change_engineering_hashes():
    """@brief Keeps changing actor, time and attempt outside engineering data.
    @return None.
    @details New audit identity preserves plan, manifest and authority hashes.
    """
    before = {name: fixture(name).sha256 for name in CONTRACTS}
    data = fixture("audit").data
    data.update(
        authenticated_subject="another-reviewer",
        attempt_id="another-attempt",
        event_id="another-event",
        timestamp="2026-10-06T15:00:00Z",
    )
    changed = IntegrationAuditEnvelope(data)
    assert changed.sha256 != before["audit"]
    for name in ("plan", "manifest", "authorization", "pre-validation"):
        assert fixture(name).sha256 == before[name]


@pytest.mark.parametrize("sizes", [[5], [3, 3], [1, 1, 1], [-1], [True]])
def test_resource_limits(sizes):
    """@brief Rejects per-object, cumulative, count and invalid-size overflow.
    @param sizes Inventory sizes for a deliberately small frozen policy.
    @return None.
    @details Boundary-sized valid inventories remain permitted.
    """
    policy = ResourcePolicy(object_bytes=4, total_bytes=5, object_count=2)
    with pytest.raises(IntegrationError, match="RESOURCE_LIMIT"):
        policy.require_sizes(sizes)
    policy.require_sizes([2, 3])


@pytest.mark.parametrize("field", ["symbol_nickname", "footprint_name"])
def test_control_characters_cannot_enter_native_names(field):
    """@brief Rejects native identifiers containing control characters.
    @param field Identifier field to alter.
    @return None.
    @details Canonical text normalization cannot hide an unsafe native name.
    """
    data = fixture("plan").data
    data["mappings"][0][field] = "item\nsecret"
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationPlan(data)


@pytest.mark.parametrize("path", ["e\u0301.step", "item\r.step", "item\x7f"])
def test_original_path_spelling_is_validated_before_normalization(path):
    """@brief Rejects unsafe supplied paths before canonical normalization.
    @param path Unsafe original source-artifact path.
    @return None.
    @details NFC and line-ending normalization cannot silently rewrite paths.
    """
    data = fixture("plan").data
    data["sources"][0]["artifacts"][0]["path"] = path
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationPlan(data)


@pytest.mark.parametrize(
    "path", ["BFT_3D", "bft_3D/second.step", "BFT_3D/item.step"]
)
def test_file_directory_and_cross_role_aliases(path):
    """@brief Rejects file parents, directory case aliases and role collisions.
    @param path Conflicting replacement footprint destination.
    @return None.
    @details Conflicts fail while freezing mappings, before any filesystem use.
    """
    data = fixture("plan").data
    data["mappings"][0]["footprint_path"] = path
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationPlan(data)


@pytest.mark.parametrize("mutation", ["kind", "path", "table-basis"])
def test_operations_require_a_matching_artifact_basis(mutation):
    """@brief Rejects fabricated role, path and preserved-table artifact basis.
    @param mutation Operation binding to change.
    @return None.
    @details Merely naming a declared source cannot justify an unrelated file.
    """
    data = fixture("plan").data
    if mutation == "kind":
        data["operations"][0]["kind"] = "FOOTPRINT"
    elif mutation == "path":
        data["operations"][0]["path"] = "A-unmanaged.step"
        data["expected_base"]["files"][0]["path"] = "A-unmanaged.step"
    else:
        data["operations"][0]["basis"] = ["PRESERVED_TABLE"]
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationPlan(data)


def test_complete_removal_retains_existing_table_and_required_checks():
    """@brief Allows an empty final source set after an explicit last removal.
    @return None.
    @details Managed artifacts are deleted and exact existing table bytes stay
    in the complete inventory; the four required rules remain mandatory.
    """
    data = fixture("plan").data
    previous = fixture("manifest")
    table = b"(sym_lib_table (version 7))\n"
    data["sources"], data["mappings"] = [], []
    data["removals"] = ["component-1"]
    data["expected_base"] = {
        "generation_hash": previous.sha256,
        "manifest_hash": previous.sha256,
        "files": previous.data["files"]
        + [
            {
                "path": "sym-lib-table",
                "sha256": sha256(table).hexdigest(),
                "byte_length": len(table),
            }
        ],
    }
    for operation in data["operations"]:
        operation["action"] = "DELETE"
    graph = rebound(IntegrationPlan(data), {"sym-lib-table": table})
    verify_contract_bindings(**graph)
    assert len(graph["manifest"].data["required_checks"]) == 4


def test_base_inventory_cumulative_resource_limit():
    """@brief Bounds expanded previous-generation content as well as new files.
    @return None.
    @details Individually permitted declarations can still exceed one GiB.
    """
    data = fixture("plan").data
    data["expected_base"]["files"].extend(
        {
            "path": f"preserved-{index}.step",
            "sha256": "c" * 64,
            "byte_length": 128 * 1024 * 1024,
        }
        for index in range(9)
    )
    with pytest.raises(IntegrationError, match="RESOURCE_LIMIT"):
        IntegrationPlan(data)


def test_rehashed_changed_step_cannot_use_passing_report_labels():
    """@brief Rejects changed installed STEP bytes with a fully rebound DAG.
    @return None.
    @details Successful synthetic labels cannot waive exact source model bytes.
    """
    graph = rebound()
    graph["files"]["BFT_3D/item.step"] += b"changed engineering content"
    graph = rebound(files=graph["files"])
    with pytest.raises(IntegrationError) as error:
        verify_contract_bindings(**graph)
    assert error.value.code == FailureCode.SEMANTIC_CHECK_FAILED


@pytest.mark.parametrize("field", ["plan_hash", "installation_manifest_hash"])
def test_journal_cannot_wrap_a_mismatched_authorization_graph(field):
    """@brief Resolves authority's own references when checking journal intent.
    @param field Authorization reference to substitute.
    @return None.
    @details A journal repeating the new authority digest cannot hide its stale
    underlying plan or manifest binding.
    """
    a = fixture("authorization").data
    a[field] = "c" * 64
    authorization = IntegrationAuthorizationBinding(a)
    j = fixture("journal").data
    j["authorization_hash"] = authorization.sha256
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        verify_journal_binding(
            IntegrationJournal(j),
            fixture("plan"),
            fixture("manifest"),
            authorization,
        )


@pytest.mark.parametrize(
    "field",
    [
        None,
        "attempt_id",
        "plan_hash",
        "manifest_hash",
        "authorization_hash",
        "check_hashes",
        "target",
    ],
)
def test_approval_audit_resolves_exact_current_references(field):
    """@brief Resolves approval audits to the current attempt and objects.
    @param field Audit binding to substitute, or None for the valid graph.
    @return None.
    @details Imported decision text alone supplies no reference evidence.
    """
    data = fixture("audit").data
    if field == "attempt_id":
        data[field] = "historical-attempt"
    elif field == "target":
        data[field]["project_id"] = "wrong-project"
    elif field == "check_hashes":
        data["references"][field] = ["c" * 64]
    elif field:
        data["references"][field] = "c" * 64
    audit = IntegrationAuditEnvelope(data)
    arguments = (
        audit,
        fixture("plan"),
        fixture("manifest"),
        fixture("authorization"),
        fixture("post-validation"),
    )
    if field is None:
        verify_audit_binding(*arguments, attempt_id="attempt-1")
    else:
        with pytest.raises(IntegrationError):
            verify_audit_binding(*arguments, attempt_id="attempt-1")


def test_audit_calendar_date_is_real():
    """@brief Rejects syntactically shaped dates outside the real calendar.
    @return None.
    @details Audit times remain separate from deterministic engineering hashes.
    """
    data = fixture("audit").data
    data["timestamp"] = "2026-02-31T25:00:00Z"
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationAuditEnvelope(data)


@pytest.mark.parametrize("kind", ["base", "precondition", "result"])
def test_schema_declares_null_pairing_without_python_semantics(kind):
    """@brief Rejects inconsistent null relationships in the offline schema.
    @param kind Schema definition to exercise directly.
    @return None.
    @details Shape consumers also enforce absence and applicability pairing.
    """
    if kind == "base":
        data = deepcopy(fixture("plan").data["expected_base"])
        data["generation_hash"] = "c" * 64
    elif kind == "precondition":
        data = deepcopy(fixture("plan").data["expected_base"]["files"][0])
        data["byte_length"] = 0
    else:
        data = deepcopy(fixture("pre-validation").data["results"][0])
        data["applicability"] = "NOT_APPLICABLE"
    with pytest.raises(ValueError):
        validate_shape(kind, data)


def test_safe_machine_failure_references():
    """@brief Exposes machine object references without leaking their metadata.
    @return None.
    @details Freeform action text and malformed reference hashes are rejected.
    """
    error = IntegrationError(
        FailureCode.TAMPERED_SOURCE,
        action="stage",
        attempt_id="attempt-1",
        target_id="project-1",
        object_hashes=("a" * 64,),
        check_hashes=("b" * 64,),
    )
    assert error.object_hashes == ("a" * 64,)
    assert error.check_hashes == ("b" * 64,)
    assert str(error) == "TAMPERED_SOURCE: stage"
    with pytest.raises(ValueError):
        IntegrationError(FailureCode.INVALID_CONTRACT, action="secret token")
    with pytest.raises(ValueError):
        IntegrationError(
            FailureCode.INVALID_CONTRACT, object_hashes=("secret token",)
        )


@pytest.mark.parametrize("mutation", [None, "path", "nickname", "basis"])
def test_packed_symbol_sharing_requires_exact_namespace_and_source_basis(
    mutation,
):
    """@brief Allows exact packed-library sharing while refusing aliases.
    @param mutation Shared symbol binding to change, or None for valid sharing.
    @return None.
    @details Every retained component justifies the shared symbol operation;
    case aliases and incomplete declared basis fail before staging.
    """
    data = fixture("plan").data
    source = deepcopy(data["sources"][0])
    source["component_id"] = "component-2"
    data["sources"].append(source)
    mapping = deepcopy(data["mappings"][0])
    mapping.update(
        component_id="component-2",
        symbol_name="second",
        footprint_name="second",
        footprint_path="BFT_Footprints.pretty/second.kicad_mod",
        model_path="BFT_3D/second.step",
    )
    data["mappings"].append(mapping)
    data["operations"][-1]["basis"].append("component-2")
    for kind, field in (
        ("FOOTPRINT", "footprint_path"),
        ("MODEL_3D", "model_path"),
    ):
        data["operations"].append(
            {
                "action": "CREATE",
                "kind": kind,
                "path": mapping[field],
                "basis": ["component-2"],
            }
        )
        data["expected_base"]["files"].append(
            {"path": mapping[field], "sha256": None, "byte_length": None}
        )
    data["operations"].sort(key=lambda operation: operation["path"])
    data["expected_base"]["files"].sort(key=lambda entry: entry["path"])
    if mutation == "path":
        mapping["symbol_path"] = "bft_symbols.kicad_sym"
    elif mutation == "nickname":
        mapping["symbol_nickname"] = "bft_symbols"
    elif mutation == "basis":
        data["operations"][-1]["basis"] = ["component-1"]
    if mutation is None:
        IntegrationPlan(data)
    else:
        with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
            IntegrationPlan(data)


@pytest.mark.parametrize("suffix", ["\n", "\r\n"])
def test_hash_schema_rejects_trailing_line_endings(suffix):
    """@brief Requires exact lowercase 64-byte hexadecimal hash spellings.
    @param suffix Line ending that permissive regex end anchors may accept.
    @return None.
    @details Digest identity includes no whitespace even before normalization.
    """
    data = fixture("plan").data
    data["sources"][0]["release_manifest_hash"] += suffix
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        IntegrationPlan(data)


def test_manifest_semantic_reference_matches_its_required_rule():
    """@brief Rejects inconsistent semantic report references when freezing.
    @return None.
    @details The semantic identity identifies the same required check.
    """
    data = fixture("manifest").data
    data["semantic_validation_hash"] = "c" * 64
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        InstallationManifest(data)
