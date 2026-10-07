"""@package tests.test_integration_planner
@brief Verifies pure planning, target inventory and stale-base refusal.
@details Real source approval fixtures are separate from synthetic prior heads.
"""

import importlib
import os

import pytest
from phase13_support import (
    TARGET,
    database_identity,
    install_prior_fixture,
)
from phase13_support import (
    approved_database as approved_database,
)
from phase13_support import (
    approved_sources as approved_sources,
)

from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import (
    Planner,
    read_project,
    snapshot_target,
)
from partsmith.integration.policy import ResourcePolicy


def refuse_hydration(connection, build_id):
    """@brief Fails if content hydration precedes a cumulative size check.
    @param connection Real test database.
    @param build_id Requested release build ID.
    @return None.
    @details This guard is used only in the resource-bound negative case.
    """
    raise AssertionError("Source hydration happened before resource refusal")


def bounded_policy():
    """@brief Returns a small effective cumulative source policy.
    @return Resource policy with four total permitted bytes.
    @details Semantic and approval rules remain enabled.
    """
    return ResourcePolicy(object_bytes=4, total_bytes=4)


def test_cumulative_source_limit_precedes_hydration(
    approved_database, tmp_path, monkeypatch
):
    """@brief Bounds cumulative sources before loading artifact blobs.
    @param approved_database Real native approved source database.
    @param tmp_path Disposable project root.
    @param monkeypatch Scoped policy and hydration guards.
    @return None.
    @details Resource rejection makes no target or database changes.
    """
    connection, builds = approved_database
    module = importlib.import_module("partsmith.integration.planner")
    monkeypatch.setattr(module, "ResourcePolicy", bounded_policy)
    monkeypatch.setattr(module, "resolve_approved_source", refuse_hydration)
    with pytest.raises(IntegrationError, match="RESOURCE_LIMIT"):
        Planner(connection).plan(tmp_path, TARGET, builds[:2])


def test_first_and_two_source_plans_are_pure(approved_database, tmp_path):
    """@brief Freezes one/two-source plans without touching any prior bytes.
    @param approved_database Actual reviewed and approved source history.
    @param tmp_path Isolated project root.
    @return None.
    @details Raw project and entire component database identities stay equal.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    (root / "user.kicad_pro").write_bytes(b'{"user":"preserved"}')
    (root / "sym-lib-table").write_bytes(
        b'(sym_lib_table (lib (name "Unrelated") (type "KiCad") '
        b'(uri "${KIPRJMOD}/unrelated.kicad_sym")))\n'
    )
    before_files = read_project(root)
    before_database = database_identity(connection)
    planner = Planner(connection)
    first = planner.plan(root, TARGET, (builds[0],))
    second = planner.plan(root, TARGET, builds[:2])
    repeated = planner.plan(root, TARGET, tuple(reversed(builds[:2])))
    assert first.plan.data["expected_base"]["generation_hash"] is None
    assert len(first.sources) == 1 and len(second.sources) == 2
    assert second.plan.canonical_bytes == repeated.plan.canonical_bytes
    assert second.dry_run() == repeated.dry_run()
    assert any(
        o["kind"] == "SYMBOL_TABLE" and o["action"] == "MODIFY"
        for o in first.plan.data["operations"]
    )
    assert read_project(root) == before_files
    assert database_identity(connection) == before_database
    assert not connection.in_transaction


def test_update_removal_and_exact_noop(approved_database, tmp_path):
    """@brief Preserves the second component through updates and removals.
    @param approved_database Real immutable approved releases and revision.
    @param tmp_path Isolated managed fixture project.
    @return None.
    @details Unchanged installed sources produce no operations or writes.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    planner = Planner(connection)
    original = planner.plan(root, TARGET, builds[:2])
    manifest, _ = install_prior_fixture(connection, original)
    before_files, before_db = read_project(root), database_identity(connection)
    noop = planner.plan(root, TARGET, builds[:2])
    assert noop.no_op and noop.plan.data["operations"] == []
    assert noop.plan.data["expected_base"]["manifest_hash"] == manifest.sha256
    update = planner.plan(root, TARGET, (builds[2], builds[1]))
    second = next(
        s
        for s in original.sources
        if s.binding() in update.plan.data["sources"]
    )
    assert second.binding() in update.plan.data["sources"]
    assert not any(
        o["kind"] in {"FOOTPRINT", "MODEL_3D"}
        and o["basis"] == [second.component_id]
        for o in update.plan.data["operations"]
    )
    removal = planner.plan(root, TARGET, (builds[1],))
    assert len(removal.plan.data["removals"]) == 1
    assert (
        sum(o["action"] == "DELETE" for o in removal.plan.data["operations"])
        == 2
    )
    assert read_project(root) == before_files
    assert database_identity(connection) == before_db


@pytest.mark.parametrize(
    "conflict",
    [
        "file",
        "empty-directory",
        "nickname",
        "alias",
        "uri",
        "table-path-alias",
        "unicode",
    ],
)
def test_unmanaged_namespace_conflicts(approved_database, tmp_path, conflict):
    """@brief Rejects unmanaged reserved names and table nickname aliases.
    @param approved_database Real approved source database.
    @param tmp_path Isolated target directory.
    @param conflict Specific unmanaged path or namespace fault.
    @return None.
    @details No unmanaged bytes or component state are modified on rejection.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    if conflict == "file":
        (root / "BFT_Symbols.kicad_sym").write_bytes(b"user owned")
    elif conflict == "empty-directory":
        (root / "BFT_3DSTEP").mkdir()
    elif conflict == "table-path-alias":
        (root / "SYM-LIB-TABLE").write_bytes(b"(sym_lib_table)")
    else:
        names = {
            "nickname": ["BFT_Symbols"],
            "alias": ["x", "X"],
            "uri": ["Unrelated"],
            "unicode": ["e\u0301"],
        }[conflict]
        uri = (
            "${KIPRJMOD}/BFT_Symbols.kicad_sym"
            if conflict == "uri"
            else "user"
        )
        entries = " ".join(
            f'(lib (name "{name}") (uri "{uri}"))' for name in names
        )
        (root / "sym-lib-table").write_text(
            f"(sym_lib_table {entries})", encoding="utf-8"
        )
    before = read_project(root)
    with pytest.raises(IntegrationError, match="CONFLICT"):
        Planner(connection).plan(root, TARGET, (builds[0],))
    assert read_project(root) == before


def test_stale_whole_project_and_changed_installed_content(
    approved_database, tmp_path
):
    """@brief Refuses target edits and corrupted installed bytes.
    @param approved_database Real approved source database.
    @param tmp_path Isolated physical target.
    @return None.
    @details Mutable project edits invalidate a frozen snapshot as well.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    planner = Planner(connection)
    result = planner.plan(root, TARGET, (builds[0],))
    (root / "board.kicad_pcb").write_bytes(b"new unsaved-to-old-plan data")
    with pytest.raises(IntegrationError, match="STALE_BASE"):
        result.snapshot.recheck()
    fresh = planner.plan(root, TARGET, (builds[0],))
    install_prior_fixture(connection, fresh)
    (root / "BFT_Symbols.kicad_sym").write_bytes(b"tampered")
    with pytest.raises(IntegrationError, match="STALE_BASE"):
        planner.plan(root, TARGET, (builds[0],))


def test_wrong_scope_and_duplicate_source_are_refused(
    approved_database, tmp_path
):
    """@brief Refuses global-table mutation and duplicate component aliases.
    @param approved_database Real approved source history.
    @param tmp_path Isolated physical project.
    @return None.
    @details Inspected source approvals do not bypass scope/path constraints.
    """
    connection, builds = approved_database
    with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
        Planner(connection).plan(
            tmp_path, TARGET | {"scope": "global"}, (builds[0],)
        )
    with pytest.raises(IntegrationError, match="NAMESPACE_CONFLICT"):
        Planner(connection).plan(tmp_path, TARGET, (builds[0], builds[0]))


def test_unsafe_paths_and_nested_reparse_are_refused(tmp_path):
    """@brief Rejects Windows aliases and nested links before copying content.
    @param tmp_path Disposable project directory.
    @return None.
    @details A symlink test is conditional on local unprivileged link support.
    """
    if os.name != "nt":
        (tmp_path / "file:stream").touch()
        with pytest.raises(IntegrationError, match="PATH_CONFLICT"):
            read_project(tmp_path)
        (tmp_path / "file:stream").unlink()
    target = tmp_path / "outside"
    target.mkdir()
    try:
        (tmp_path / "linked").symlink_to(target, target_is_directory=True)
    except OSError:
        # Actual Windows junction rejection is independently mandatory below.
        from partsmith.integration.atomic_target import (
            WindowsFiles,
            junction_buffer,
        )

        link = tmp_path / "linked"
        link.mkdir()
        native = WindowsFiles()
        with native.directory(link, reparse=True, write=True) as handle:
            native.reparse(handle, junction_buffer(target.absolute()))
    with pytest.raises(IntegrationError, match="PATH_CONFLICT"):
        snapshot_target(tmp_path, TARGET, None)


def test_wrong_registered_root_is_refused(approved_database, tmp_path):
    """@brief Refuses a different root even when its content can match a head.
    @param approved_database Real source history.
    @param tmp_path Two disposable directories.
    @return None.
    @details A portable target label alone does not identify its physical root.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    result = Planner(connection).plan(root, TARGET, (builds[0],))
    install_prior_fixture(connection, result)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
        Planner(connection).plan(other, TARGET, (builds[0],))
