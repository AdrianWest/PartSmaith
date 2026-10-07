"""@package tests.test_integration_sources
@brief Tests approved-source resolution and exact export/import preservation.
@details Imported history never grants authority to a rebuilt release.
"""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.integration import (
    IntegrationError,
    resolve_approved_source,
    verify_source_bindings,
)
from partsmith.ir import canonical_json
from partsmith.pdl import load_pdl
from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release import AuthenticatedPrincipal, BuildState
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.replay import OfflineReplayService
from partsmith.release.workflow import ReviewService

ROOT = Path(__file__).resolve().parents[1]


def candidate(connection):
    """@brief Creates a complete real native-validated release fixture.
    @param connection Isolated authoritative migrated component store.
    @return Release candidate awaiting authenticated approval.
    @details Source bytes and geometry reuse the established 0402 fixture.
    """
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    data = json.loads((ROOT / "fixtures/ir/v1.2/valid/0402.json").read_bytes())
    data["identity"]["component_id"] = component.id
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
    store.compare_and_swap_head(component.id, revision.revision_id, None)
    return KnownGoodReleasePipeline(connection).run(
        component.id, revision.revision_id, load_pdl("synthetic-0402")
    )


def approve(connection, release) -> None:
    """@brief Explicitly approves a real exact release in the fixture store.
    @param connection Authoritative isolated database.
    @param release Complete exact candidate and binding.
    @return None.
    @details Uses a trusted test principal, never a saved session label.
    """
    ReviewService(connection).approve(
        release.build_id,
        "fixture-reviewer",
        "Exact source preservation test",
        release.binding,
        AuthenticatedPrincipal("fixture-reviewer", "test"),
    )


def test_unfinished_and_revision_only_data_are_not_approved_sources(tmp_path):
    """@brief Rejects absent and unfinished sources without mutating history.
    @param tmp_path Isolated fixture directory.
    @return None.
    @details Reviewed revisions and successful generation are insufficient.
    """
    with database(tmp_path / "source.db") as connection:
        with pytest.raises(IntegrationError, match="MISSING_SOURCE"):
            resolve_approved_source(
                connection, "revision-only-or-session-label"
            )
        release = candidate(connection)
        before = connection.total_changes
        with pytest.raises(IntegrationError, match="UNAPPROVED_SOURCE"):
            resolve_approved_source(connection, release.build_id)
        assert connection.total_changes == before


def test_approved_source_resolution_is_exact_and_read_only(tmp_path):
    """@brief Resolves a real approved source and exported source unchanged.
    @param tmp_path Isolated fixture directory.
    @return None.
    @details Manifest, historical approval and three artifact bytes are exact.
    """
    with database(tmp_path / "source.db") as connection:
        release = candidate(connection)
        approve(connection, release)
        before = connection.total_changes
        source = resolve_approved_source(connection, release.build_id)
        assert connection.total_changes == before
        expected = [source.binding()]
        verify_source_bindings(expected, (source,))
        expected[0]["release_approval_hash"] = "a" * 64
        with pytest.raises(IntegrationError, match="TAMPERED_SOURCE"):
            verify_source_bindings(expected, (source,))
        with pytest.raises(IntegrationError, match="INVALID_CONTRACT"):
            verify_source_bindings([], (source, source))
        assert source.binding()["release_manifest_hash"] == (
            release.binding.engineering_manifest_hash
        )
        assert sorted(
            sha256(blob).hexdigest() for _, _, blob in source.artifacts
        ) == sorted(release.binding.artifact_hashes)
        assert source.approval_bytes == bytes(
            connection.execute(
                "SELECT canonical_bytes FROM release_decisions "
                "WHERE build_id = ?",
                (release.build_id,),
            ).fetchone()[0]
        )
        KnownGoodReleasePipeline(connection).orchestrator.advance(
            release.build_id,
            BuildState.EXPORTED,
            "Fixture exact export",
        )
        assert resolve_approved_source(connection, release.build_id) == source


def test_export_import_preserves_original_bytes_and_history(tmp_path):
    """@brief Verifies exact approved outputs/audits survive replay transport.
    @param tmp_path Isolated source and destination stores.
    @return None.
    @details Historical source bytes are retained while rebuilt content still
    requires fresh release approval and separate integration authorization.
    """
    source_blob = (ROOT / "fixtures/ir/source/synthetic-0402.txt").read_bytes()
    with database(tmp_path / "source.db") as connection:
        release = candidate(connection)
        approve(connection, release)
        original = resolve_approved_source(connection, release.build_id)
        before = connection.total_changes
        bundle = OfflineReplayService(connection).export(
            release.build_id,
            "phase13-source-preservation",
            source_objects={sha256(source_blob).hexdigest(): source_blob},
        )
        assert (
            bundle.objects["outputs/manifest.json"] == original.manifest_bytes
        )
        for _, path, blob in original.artifacts:
            assert bundle.objects["outputs/" + path] == blob
        decisions = json.loads(bundle.objects["audit/release_decisions.json"])
        assert bytes.fromhex(decisions[0]["canonical_bytes"]) == (
            original.approval_bytes
        )
        assert connection.total_changes == before
    with database(tmp_path / "imported.db") as connection:
        rebuilt, report = OfflineReplayService(connection).rebuild(bundle)
        assert report["status"] == "PASS"
        retained = {
            row["relative_path"]: bytes(row["content"])
            for row in connection.execute(
                "SELECT relative_path, content FROM bundle_objects "
                "WHERE bundle_id = ?",
                (bundle.index["bundle_id"],),
            )
        }
        assert retained == bundle.objects
        stored_index = connection.execute(
            "SELECT canonical_bytes FROM bundle_imports WHERE bundle_id = ?",
            (bundle.index["bundle_id"],),
        ).fetchone()[0]
        assert bytes(stored_index) == canonical_json(bundle.index)
        with pytest.raises(IntegrationError, match="UNAPPROVED_SOURCE"):
            resolve_approved_source(connection, rebuilt.build_id)


def test_tampered_final_source_rejected_without_partial_change(tmp_path):
    """@brief Rejects corrupt trusted-store source content before planning.
    @param tmp_path Isolated authoritative component database.
    @return None.
    @details Test corruption bypasses immutable triggers to simulate damage.
    """
    with database(tmp_path / "source.db") as connection:
        release = candidate(connection)
        approve(connection, release)
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND tbl_name = 'artifacts'"
        ).fetchall():
            connection.execute(f'DROP TRIGGER "{row[0]}"')
        connection.execute(
            "UPDATE artifacts SET content = X'00' "
            "WHERE build_id = ? AND stage = 'FINAL'",
            (release.build_id,),
        )
        before = connection.total_changes
        with pytest.raises(IntegrationError, match="TAMPERED_SOURCE"):
            resolve_approved_source(connection, release.build_id)
        assert connection.total_changes == before
