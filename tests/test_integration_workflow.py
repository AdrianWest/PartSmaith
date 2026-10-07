"""@package tests.test_integration_workflow
@brief Tests isolated authority and safe shared installation actions.
@details Real native checks stay enabled; saved actor text cannot authenticate.
"""

from contextlib import closing

import pytest
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources
from test_integration_review import principal

from partsmith.gui.session import Session
from partsmith.integration.errors import IntegrationError
from partsmith.integration.workflow import IntegrationWorkflow
from partsmith.ir.canonical import canonical_json
from partsmith.persistence import connect


@pytest.fixture
def component_session(approved_database, tmp_path):
    """@brief Creates an actual session containing approved source history.
    @param approved_database Real native approved component fixture database.
    @param tmp_path Owned working session storage.
    @return Working source session and complete release build identities.
    @details No integration authority row is inserted in the source session.
    """
    connection, builds = approved_database
    session = Session(tmp_path / "sessions")
    with closing(connect(session.database)) as copied:
        connection.backup(copied)
        copied.execute(
            "CREATE TABLE desktop_session (id INTEGER PRIMARY KEY, data BLOB)"
        )
        copied.execute(
            "INSERT INTO desktop_session VALUES (1,?)",
            (canonical_json(session.state),),
        )
        copied.commit()
    return session, builds


def test_separate_authority_and_saved_draft_require_new_actions(
    component_session, tmp_path
):
    """@brief Exercises shared native workflow and safe archive round trips.
    @param component_session Actual approved sources in a real working session.
    @param tmp_path Owned original, workspace, authority and archive paths.
    @return None.
    @details A loaded archive retains references without rows or permission.
    Fresh explicit publish with current authentication still uses central data.
    """
    session, builds = component_session
    original = tmp_path / "original"
    original.mkdir()
    (original / "design.kicad_pro").write_bytes(b"{}")
    workflow = IntegrationWorkflow(
        [session],
        directory=tmp_path / "authority",
        principal_provider=principal,
    )
    target, link = workflow.register(
        original, tmp_path / "managed", confirmed=True
    )
    from partsmith.integration.target import OwnedTarget

    try:
        draft = workflow.plan(target, builds[:2])
        assert draft.attempt_id is None
        stage = workflow.stage(draft)
        view = workflow.inspect(stage)
        assert view["blocking_codes"] == []
        session.update(integration=stage.references())
        archive = tmp_path / "draft.partsmith"
        session.save(archive)
        loaded = Session.load(archive, root=tmp_path / "loaded")
        assert loaded.state["integration"] == stage.references()
        with loaded.connection() as connection:
            assert not connection.execute(
                "SELECT * FROM integration_decisions"
            ).fetchall()
        resumed = IntegrationWorkflow(
            [loaded],
            directory=workflow.directory,
            principal_provider=principal,
        )
        with pytest.raises(IntegrationError, match="AUTHENTICATION_FAILED"):
            resumed.publish(stage, confirmed=True)
        approved = resumed.authorize(
            stage, "Review exact library installation"
        )
        assert approved.outcome == "AUTHORIZED"
        with pytest.raises(IntegrationError):
            resumed.publish(stage, confirmed=False)
        assert resumed.publish(stage, confirmed=True).committed
        assert resumed.plan(target, builds[:2]).planning.no_op
        assert not (original / "sym-lib-table").exists()
        with session.connection() as connection:
            assert not connection.execute(
                "SELECT * FROM integration_targets"
            ).fetchall()
    finally:
        with closing(connect(workflow.database)) as connection:
            owned = OwnedTarget(connection, target)
            assert str(owned.link) == link
            owned.link.rmdir()


def test_imported_installation_rows_cannot_load_or_supply_sources(
    component_session, tmp_path
):
    """@brief Rejects installation execution rows in session archives.
    @param component_session Real approved source session.
    @param tmp_path Owned archive and authority paths.
    @return None.
    @details Transport hashes may be valid; execution records remain forbidden.
    """
    session, _ = component_session
    with session.connection() as connection:
        connection.execute(
            "INSERT INTO integration_targets VALUES (?,?,?,?,?,?)",
            (
                "forged-target",
                "bft-library",
                "project-local",
                "foreign",
                canonical_json({}),
                "2026-10-07T00:00:00Z",
            ),
        )
    archive = tmp_path / "with-execution-rows.partsmith"
    session.save(archive)
    with pytest.raises(ValueError, match="installation execution records"):
        Session.load(archive, root=tmp_path / "load-rejected")
    workflow = IntegrationWorkflow([session], directory=tmp_path / "authority")
    with pytest.raises(ValueError, match="installation execution records"):
        with workflow.services():
            pytest.fail("Imported execution rows entered the source catalog")


def test_data_only_extension_rejects_live_fields(component_session, tmp_path):
    """@brief Rejects principals, confirmation and unknown extension versions.
    @param component_session Real source session.
    @param tmp_path Owned archive destination.
    @return None.
    @details The closed saved extension contains references only.
    """
    session, _ = component_session
    for field, value in (
        ("confirmed", True),
        ("principal", "saved actor"),
        ("schema_version", "unknown"),
    ):
        extension = {
            "schema_version": "partsmith-session-integration-1.0",
            "project_id": "data-only",
            "drafts": [],
        }
        extension[field] = value
        with pytest.raises(ValueError):
            session.update(integration=extension)
            session.save(tmp_path / "invalid.partsmith")
