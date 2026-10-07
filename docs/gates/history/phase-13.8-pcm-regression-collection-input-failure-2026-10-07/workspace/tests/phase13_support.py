"""@package tests.phase13_support
@brief Creates real approved source releases for integration milestone checks.
@details Disposable databases reuse native generation and exact release review;
synthetic prior-head fixtures make no publication or native-staging claim.
"""

import json
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from partsmith.integration.contracts import InstallationManifest
from partsmith.integration.planner import file_inventory
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.store import IntegrationStore
from partsmith.ir.canonical import canonical_json
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, Repository, connect, migrate
from partsmith.release import AuthenticatedPrincipal
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.workflow import ReviewService

ROOT = Path(__file__).resolve().parents[1]
TARGET = {
    "project_id": "phase13-owned-project",
    "library_id": "bft-library",
    "scope": "project-local",
}


def create_release(connection, component=None, parent=None, changed=False):
    """@brief Generates and approves one complete native source release.
    @param connection Disposable authoritative application database.
    @param component Existing component ID for a deliberate revision update.
    @param parent Parent immutable revision ID.
    @param changed Whether to revise the first symbol pin name.
    @return Exact complete release candidate.
    @details All updates require reviewed IR, generation and release approval.
    """
    if component is None:
        component = (
            Repository(connection)
            .create_component("Synthetic", "0402", "0402")
            .id
        )
    if parent:
        data = json.loads(
            connection.execute(
                "SELECT canonical_bytes FROM ir_revisions WHERE id = ?",
                (parent,),
            ).fetchone()[0]
        )
    else:
        data = json.loads(
            (ROOT / "fixtures/ir/v1.2/valid/0402.json").read_bytes()
        )
    data["identity"]["component_id"] = component
    data["revision"]["id"] = str(uuid4())
    data["revision"]["parent_id"] = parent
    if parent is None:
        for evidence in data["evidence"]:
            evidence["acquisition_revision_id"] = data["revision"]["id"]
    if changed:
        data["pins"][0]["name"] = "Revised_terminal"
    store = ImmutableStore(connection)
    inventory = store.put_inventory(
        {
            "source_hashes": [
                d["sha256"] for d in data["source"]["documents"]
            ],
            "evidence_ids": [e["id"] for e in data["evidence"]],
        }
    )
    revision = store.put_revision(
        data, inventory_sha256=inventory, reviewed=True
    )
    expected = None
    if parent:
        expected = connection.execute(
            "SELECT canonical_sha256 FROM ir_revisions WHERE id = ?",
            (parent,),
        ).fetchone()[0]
    store.compare_and_swap_head(component, revision.revision_id, expected)
    release = KnownGoodReleasePipeline(connection).run(
        component, revision.revision_id, load_pdl("synthetic-0402")
    )
    ReviewService(connection).approve(
        release.build_id,
        "integration-fixture-reviewer",
        "Approve exact generated source for integration testing",
        release.binding,
        AuthenticatedPrincipal("integration-fixture-reviewer", "test"),
    )
    return release


@pytest.fixture(scope="session")
def approved_sources(tmp_path_factory):
    """@brief Builds two actual approved releases and one approved update.
    @param tmp_path_factory Session-owned fixture directory factory.
    @return Source database path and exact three release build IDs.
    @details Native CLI and locked CAD generation run once per test session.
    """
    path = tmp_path_factory.mktemp("integration-approved") / "sources.db"
    with closing(connect(path)) as connection:
        migrate(connection)
        first = create_release(connection)
        second = create_release(connection)
        original = resolve_approved_source(connection, first.build_id)
        updated = create_release(
            connection, original.component_id, original.revision_id, True
        )
        connection.commit()
    return path, (first.build_id, second.build_id, updated.build_id)


@pytest.fixture
def approved_database(tmp_path, approved_sources):
    """@brief Copies real approved history into one test-owned database.
    @param tmp_path Isolated test directory.
    @param approved_sources Session-generated real approved releases.
    @return Yields mutable test connection and exact release build IDs.
    @details Each test mutates its own backup; source fixture stays unchanged.
    """
    source, builds = approved_sources
    with closing(connect(source)) as original:
        with closing(connect(tmp_path / "application.db")) as connection:
            original.backup(connection)
            yield connection, builds


def install_prior_fixture(connection, result, objects=None):
    """@brief Records a synthetic prior head for read-only planner tests.
    @param connection Disposable application database.
    @param result First-install production planning result.
    @param objects Optional complete fixture file content mapping.
    @return Exact synthetic prior manifest and installed file mapping.
    @details This is test setup, not native staging or publication evidence.
    """
    plan = result.plan.data
    if objects is None:
        objects = {
            "BFT_Symbols.kicad_sym": b"synthetic packed prior fixture\n"
        }
        for source, mapping in zip(
            result.sources, plan["mappings"], strict=True
        ):
            artifacts = {role: blob for role, _, blob in source.artifacts}
            objects[mapping["footprint_path"]] = artifacts["footprint"]
            objects[mapping["model_path"]] = artifacts["model_3d"]
        objects["sym-lib-table"] = (
            b'(sym_lib_table (lib (name "BFT_Symbols") '
            b'(type "KiCad") (uri "${KIPRJMOD}/BFT_Symbols.kicad_sym")))\n'
        )
        objects["fp-lib-table"] = (
            b'(fp_lib_table (lib (name "BFT_Footprints") '
            b'(type "KiCad") (uri "${KIPRJMOD}/BFT_Footprints.pretty")))\n'
        )
    for name, blob in objects.items():
        path = result.snapshot.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    manifest = InstallationManifest(
        {
            "schema_version": "1.0",
            "plan_hash": result.plan.sha256,
            "target": plan["target"],
            "expected_base": plan["expected_base"],
            "sources": plan["sources"],
            "mappings": plan["mappings"],
            "versions": plan["versions"],
            "files": file_inventory(objects),
            "semantic_validation_hash": "f" * 64,
            "required_checks": [
                {"rule_id": rule, "report_hash": "f" * 64}
                for rule in plan["required_rules"]
            ],
        }
    )
    store = IntegrationStore(connection)
    store.put_contract(manifest)
    connection.execute(
        "INSERT INTO integration_targets VALUES (?, ?, ?, ?, ?, ?)",
        (
            TARGET["project_id"],
            TARGET["library_id"],
            TARGET["scope"],
            str(result.snapshot.root),
            canonical_json({"fixture": True}),
            "fixture",
        ),
    )
    connection.execute(
        "INSERT INTO integration_heads VALUES (?, ?)",
        (TARGET["project_id"], manifest.sha256),
    )
    connection.commit()
    return manifest, objects


def database_identity(connection) -> str:
    """@brief Hashes the entire logical database including release history.
    @param connection Disposable application database.
    @return Exact dump SHA-256.
    @details Detects dry-run changes independently of connection change counts.
    """
    return sha256("\n".join(connection.iterdump()).encode()).hexdigest()
