"""@package tests.test_integration_staging
@brief Tests native deterministic packing and exact engineering preservation.
@details Actual approved sources and pinned KiCad CLI checks stay enabled.
"""

import importlib
from hashlib import sha256

import pytest
from phase13_support import TARGET, database_identity, install_prior_fixture
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources

from partsmith.integration.contracts import IntegrationPlan
from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner, read_project
from partsmith.integration.sexpr import Atom, children, parse, serialize
from partsmith.integration.staging import (
    Stager,
    native_check,
    planned_files,
    verify_semantics,
)
from partsmith.integration.store import IntegrationStore
from partsmith.kicad.runtime import KiCadCompatibilityError


def test_two_native_stages_are_identical(approved_database, tmp_path):
    """@brief Verifies native packing and deterministic check identities.
    @param approved_database Complete approved source packages.
    @param tmp_path Isolated target and owned staging parent.
    @return None.
    @details Unrelated table/project bytes and SQLite remain unchanged.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    (root / "sym-lib-table").write_bytes(
        b'(sym_lib_table (version 7) (lib (name "User") (type "KiCad") '
        b'(uri "${KIPRJMOD}/user.kicad_sym") (descr "User property")))'
    )
    (root / "user.kicad_pro").write_bytes(b"{}")
    (root / "empty-user-folder").mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    before = database_identity(connection), read_project(root)
    one = Stager(connection).stage(result, tmp_path)
    two = Stager(connection).stage(result, tmp_path)
    assert one.root != two.root
    assert one.objects == two.objects
    assert one.manifest == two.manifest
    assert one.pre == two.pre and one.post == two.post
    assert len(one.native_receipt["entries"]) == 2
    assert len(one.native_receipt["operations"]) == 5
    assert one.native_receipt["native_pin_semantics_preserved"]
    assert before == (database_identity(connection), read_project(root))
    one.recheck()
    assert (one.root / "empty-user-folder").is_dir()
    Stager(connection).revalidate(one)
    store = IntegrationStore(connection)
    attempt = store.save_plan(result.plan, result.snapshot.document)
    Stager(connection).save(attempt, one)
    assert connection.in_transaction
    connection.rollback()
    assert database_identity(connection) == before[0]


@pytest.mark.parametrize("field", ["name", "number"])
def test_native_pin_normalization_is_rejected(
    approved_database, tmp_path, field
):
    """@brief Rejects actual KiCad whitespace normalization of pin semantics.
    @param approved_database Real approved native-compatible sources.
    @param tmp_path Owned disposable native check directory.
    @param field Pin name or number changed by the actual KiCad parser.
    @return None.
    @details Does not count successful parsing as semantic preservation.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    objects = planned_files(result, result.sources)
    tree = parse(objects["BFT_Symbols.kicad_sym"])
    symbol = children(tree, "symbol")[0]
    pin = next(
        p for unit in children(symbol, "symbol") for p in children(unit, "pin")
    )
    children(pin, field)[0][1] = "Changed pin"
    objects["BFT_Symbols.kicad_sym"] = serialize(tree)
    for name, blob in objects.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    with pytest.raises(IntegrationError, match="SEMANTIC_CHECK_FAILED"):
        native_check(
            root,
            tuple(m["symbol_name"] for m in result.plan.data["mappings"]),
            "10.0.6",
        )


@pytest.mark.parametrize(
    "fault",
    [
        "pin-number",
        "pin-type",
        "pin-name",
        "pin-position",
        "pad-position",
        "pad-layer",
        "model-offset",
        "model-scale",
        "model-rotation",
        "model-uri",
        "footprint-mapping",
        "symbol-property",
        "missing-entry",
        "extra-entry",
        "step",
        "table",
    ],
)
def test_engineering_faults_are_rejected(approved_database, tmp_path, fault):
    """@brief Rejects token and byte faults against approved engineering.
    @param approved_database Complete real approved sources.
    @param tmp_path Disposable project.
    @param fault Exact deliberately corrupted field or inventory.
    @return None.
    @details Comparisons include all fields of unchanged retained entries.
    """
    connection, builds = approved_database
    result = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    objects = planned_files(result, result.sources)
    mapping = result.plan.data["mappings"][0]
    symbol = parse(objects["BFT_Symbols.kicad_sym"])
    entry = children(symbol, "symbol")[0]
    pin = children(children(entry, "symbol")[0], "pin")[0]
    footprint = parse(objects[mapping["footprint_path"]])
    pad = children(footprint, "pad")[0]
    model = children(footprint, "model")[0]
    if fault == "pin-number":
        children(pin, "number")[0][1] = "wrong"
    elif fault == "pin-type":
        pin[1] = Atom("input")
    elif fault == "pin-name":
        children(pin, "name")[0][1] = "wrong"
    elif fault == "pin-position":
        children(pin, "at")[0][1] = Atom("99")
    elif fault == "pad-position":
        children(pad, "at")[0][1] = Atom("99")
    elif fault == "pad-layer":
        children(pad, "layers")[0][1] = "B.Cu"
    elif fault.startswith("model-"):
        field = fault.removeprefix("model-")
        if field == "uri":
            model[1] = "${KIPRJMOD}/missing.step"
        else:
            field = {"rotation": "rotate"}.get(field, field)
            children(children(model, field)[0], "xyz")[0][1] = Atom("99")
    elif fault == "footprint-mapping":
        children(entry, "property")[0][2] = "Other:wrong"
    elif fault == "symbol-property":
        children(entry, "property")[1][2] = "Wrong reference"
    elif fault == "missing-entry":
        symbol.remove(entry)
    elif fault == "extra-entry":
        symbol.append(entry)
    objects["BFT_Symbols.kicad_sym"] = serialize(symbol)
    objects[mapping["footprint_path"]] = serialize(footprint)
    if fault == "step":
        objects[mapping["model_path"]] += b"tamper"
    elif fault == "table":
        objects["sym-lib-table"] = b"(sym_lib_table)"
    with pytest.raises((IntegrationError, ValueError)):
        verify_semantics(result, result.sources, objects)


def test_update_retains_other_component_exactly(approved_database, tmp_path):
    """@brief Stages a reviewed update while preserving the other source entry.
    @param approved_database Two releases and a separately approved revision.
    @param tmp_path Disposable target and stage directories.
    @return None.
    @details Prior-head setup is synthetic; both stages use actual native CLI.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    planner = Planner(connection)
    initial = planner.plan(root, TARGET, builds[:2])
    first = Stager(connection).stage(initial, tmp_path)
    install_prior_fixture(connection, initial, dict(first.objects))
    updated = planner.plan(root, TARGET, (builds[1], builds[2]))
    second = Stager(connection).stage(updated, tmp_path)
    unchanged = next(
        s
        for s in initial.sources
        if s.binding() in updated.plan.data["sources"]
    )
    mapping = next(
        m
        for m in initial.plan.data["mappings"]
        if m["component_id"] == unchanged.component_id
    )
    for field in ("footprint_path", "model_path"):
        assert (
            dict(first.objects)[mapping[field]]
            == dict(second.objects)[mapping[field]]
        )
    before = children(
        parse(dict(first.objects)["BFT_Symbols.kicad_sym"]), "symbol"
    )
    after = children(
        parse(dict(second.objects)["BFT_Symbols.kicad_sym"]), "symbol"
    )
    assert next(s for s in before if s[1] == mapping["symbol_name"]) == next(
        s for s in after if s[1] == mapping["symbol_name"]
    )
    assert unchanged.binding() in second.manifest.data["sources"]


def test_stage_tampering_and_target_edits_invalidate(
    approved_database, tmp_path
):
    """@brief Refuses edits made after checks or to the frozen target snapshot.
    @param approved_database Complete source approvals.
    @param tmp_path Disposable target and isolated stage.
    @return None.
    @details Staged hashes cannot remain valid after a foreign file is added.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    staged = Stager(connection).stage(result, tmp_path)
    (staged.root / "unexpected.txt").write_bytes(b"foreign")
    with pytest.raises(IntegrationError):
        staged.recheck()
    (root / "user.kicad_pro").write_bytes(b"edited")
    with pytest.raises(IntegrationError, match="STALE_BASE"):
        Stager(connection).stage(result, tmp_path)


def reject_native(root, names, version):
    """@brief Injects native validation failure before manifest creation.
    @param root Owned stage.
    @param names Exact intended entry names.
    @param version Frozen CLI version.
    @return None.
    @details The negative test supplies no passing native receipt.
    """
    raise IntegrationError(
        importlib.import_module(
            "partsmith.integration.errors"
        ).FailureCode.NATIVE_CHECK_FAILED
    )


def test_native_failure_preserves_store_and_target(
    approved_database, tmp_path, monkeypatch
):
    """@brief Leaves all source and target bytes intact after native failure.
    @param approved_database Complete source database.
    @param tmp_path Disposable physical project.
    @param monkeypatch Scoped native failure injection.
    @return None.
    @details No manifest or authorization is persisted on failure.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    before = database_identity(connection), read_project(root)
    module = importlib.import_module("partsmith.integration.staging")
    monkeypatch.setattr(module, "native_check", reject_native)
    with pytest.raises(IntegrationError, match="NATIVE_CHECK_FAILED"):
        Stager(connection).stage(result, tmp_path)
    assert before == (database_identity(connection), read_project(root))


def corrupt_during_native(root, names, version):
    """@brief Simulates an external staged edit during a native worker.
    @param root Owned stage under test.
    @param names Frozen proposed entries.
    @param version Pinned CLI version.
    @return Synthetic transport receipt used only in this negative test.
    @details This never supplies actual passing native acceptance evidence.
    """
    (root / "BFT_Symbols.kicad_sym").write_bytes(b"edited during checks")
    return {}


def fail_stage_directory(*args, **kwargs):
    """@brief Injects a disk/permission failure before stage file creation.
    @param args Temporary-directory positional arguments.
    @param kwargs Temporary-directory keyword arguments.
    @return None.
    @details Represents an operating-system write failure with no target edit.
    """
    raise OSError("Injected disk/permission failure")


@pytest.mark.parametrize("fault", ["stage-write", "during-native"])
def test_stage_write_and_concurrent_faults(
    approved_database, tmp_path, monkeypatch, fault
):
    """@brief Refuses disk failures and edits during check boundaries.
    @param approved_database Complete source approvals.
    @param tmp_path Disposable target and staging parent.
    @param monkeypatch Scoped failure injection.
    @param fault Exact stage boundary to fault.
    @return None.
    @details No checks, manifest or installation authority are persisted.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, builds[:2])
    before = database_identity(connection), read_project(root)
    module = importlib.import_module("partsmith.integration.staging")
    if fault == "stage-write":
        monkeypatch.setattr(module, "mkdtemp", fail_stage_directory)
    else:
        monkeypatch.setattr(module, "native_check", corrupt_during_native)
    with pytest.raises((IntegrationError, OSError)):
        Stager(connection).stage(result, tmp_path)
    assert before == (database_identity(connection), read_project(root))


def test_step_source_hash_is_preserved(approved_database, tmp_path):
    """@brief Checks original STEP identity after deterministic assembly.
    @param approved_database Complete real source releases.
    @param tmp_path Disposable project root.
    @return None.
    @details No mesh, diagnostic render or CAD regeneration replaces STEP.
    """
    connection, builds = approved_database
    result = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    objects = planned_files(result, result.sources)
    for source, mapping in zip(
        result.sources, result.plan.data["mappings"], strict=True
    ):
        original = next(
            a for a in source.binding()["artifacts"] if a["role"] == "model_3d"
        )
        assert (
            sha256(objects[mapping["model_path"]]).hexdigest()
            == (original["sha256"])
        )


def unavailable_runtime(version):
    """@brief Simulates absence of the exact required native runtime.
    @param version Requested pinned version.
    @return None.
    @details The native wrapper must convert this to a stable failure code.
    """
    raise KiCadCompatibilityError("Pinned runtime unavailable")


def test_unavailable_runtime_is_explicit(
    approved_database, tmp_path, monkeypatch
):
    """@brief Blocks missing native tooling without a passing manifest.
    @param approved_database Actual approved source releases.
    @param tmp_path Disposable target and stage.
    @param monkeypatch Scoped runtime discovery failure.
    @return None.
    @details This is a negative transport test, not native acceptance.
    """
    connection, builds = approved_database
    result = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    module = importlib.import_module("partsmith.integration.staging")
    monkeypatch.setattr(module, "discover_kicad", unavailable_runtime)
    with pytest.raises(IntegrationError, match="NATIVE_CHECK_FAILED"):
        Stager(connection).stage(result, tmp_path)


def test_unsupported_comparator_version_is_refused(
    approved_database, tmp_path
):
    """@brief Rejects a valid contract naming an unimplemented comparator.
    @param approved_database Actual approved source releases.
    @param tmp_path Disposable target.
    @return None.
    @details Version declarations cannot silently choose permissive rules.
    """
    from dataclasses import replace

    connection, builds = approved_database
    result = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    data = result.plan.data
    data["versions"]["comparator"] = "9.0"
    result = replace(result, plan=IntegrationPlan(data))
    with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
        Stager(connection).stage(result, tmp_path)
