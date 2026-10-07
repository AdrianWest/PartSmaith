"""@package tests.test_integration_target
@brief Tests actual owned NTFS registration, containment and writer exclusion.
@details Windows cases are real native filesystem tests, not mock publication.
"""

import os

import pytest
from phase13_support import TARGET
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources

from partsmith.integration.atomic_target import junction_buffer
from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner, read_project
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.target import OwnedTarget

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Requires fixed local NTFS"
)


@pytest.fixture
def owned_target(approved_database, tmp_path):
    """@brief Registers an explicitly closed disposable native project copy.
    @param approved_database Actual migrated authoritative source database.
    @param tmp_path Ordinary owned source and managed-container parent.
    @return Original root, native owned target and source build identities.
    @details Unlinks only the verified fixture junction before test cleanup.
    """
    connection, builds = approved_database
    original = tmp_path / "original"
    original.mkdir()
    (original / "project.kicad_pro").write_bytes(b"{}")
    (original / "empty-user-folder").mkdir()
    before = read_project(original)
    target = OwnedTarget.create(
        connection,
        TARGET,
        original,
        tmp_path / "managed",
        ClosedProject(TARGET["project_id"], True),
    )
    assert read_project(original) == before
    try:
        yield original, target, builds
    finally:
        with target.api.directory(target.link, reparse=True) as handle:
            assert (
                list(target.api.identity(handle))
                == target.metadata["link_identity"]
            )
        target.link.rmdir()


def test_registration_preserves_original_and_resolves_owned_root(owned_target):
    """@brief Preserves source bytes and establishes paired copied tables.
    @param owned_target Real registered fixed-local-NTFS fixture.
    @return None.
    @details Planner resolves only the trusted physical root; logical links
    and other directories cannot bypass its ordinary inventory checks.
    """
    original, target, builds = owned_target
    current = target.current()
    assert current.parent == target.workspace / "slots"
    assert not (original / "sym-lib-table").exists()
    assert (current / "sym-lib-table").is_file()
    assert (current / "fp-lib-table").is_file()
    assert (current / "empty-user-folder").is_dir()
    planned = Planner(target.connection).plan(current, TARGET, builds[:2])
    assert planned.snapshot.root == current
    with pytest.raises(IntegrationError):
        Planner(target.connection).plan(original, TARGET, builds[:2])


def test_exclusive_lock_and_file_write_sharing(owned_target):
    """@brief Uses real Windows sharing to exclude publishers and file writers.
    @param owned_target Native registered target.
    @return None.
    @details Existing project-file edits fail before replacing any generation.
    """
    _, target, _ = owned_target
    closed = ClosedProject(TARGET["project_id"], True)
    with target.lock(closed) as (_, current):
        with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
            with target.lock(closed):
                pytest.fail("Concurrent publisher entered lock")
        objects, _ = read_project(current)
        with target.freeze_files(current, objects):
            with pytest.raises(PermissionError):
                (current / "project.kicad_pro").write_bytes(b"foreign edit")
            assert read_project(current)[0] == objects


def test_false_closed_confirmation_makes_no_copy(approved_database, tmp_path):
    """@brief Refuses a cancelled/missing closed-project confirmation.
    @param approved_database Actual migrated application database.
    @param tmp_path Disposable ordinary source.
    @return None.
    @details No marker, junction, registration or source edit is created.
    """
    connection, _ = approved_database
    original = tmp_path / "source"
    original.mkdir()
    destination = tmp_path / "managed"
    with pytest.raises(IntegrationError):
        OwnedTarget.create(
            connection,
            TARGET,
            original,
            destination,
            ClosedProject(TARGET["project_id"], False),
        )
    assert not destination.exists()
    assert not connection.execute(
        "SELECT * FROM integration_targets"
    ).fetchall()


@pytest.mark.parametrize(
    "fault", ["marker", "foreign-junction", "unknown-slot"]
)
def test_changed_ownership_is_refused(owned_target, fault):
    """@brief Rejects marker tampering, foreign targets and unrecorded slots.
    @param owned_target Native registered fixture.
    @param fault Exact ownership boundary to change.
    @return None.
    @details Changed reparse payloads are restored only for fixture cleanup.
    """
    _, target, _ = owned_target
    current = target.current()
    if fault == "marker":
        (target.workspace / "owner.json").write_bytes(b"forged")
    else:
        destination = target.workspace / (
            "foreign"
            if fault == "foreign-junction"
            else "slots/slot-" + "f" * 32
        )
        destination.mkdir()
        with target.api.directory(
            target.link, reparse=True, write=True
        ) as handle:
            target.api.reparse(handle, junction_buffer(destination))
    try:
        with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
            target.current()
    finally:
        if fault != "marker":
            with target.api.directory(
                target.link, reparse=True, write=True
            ) as handle:
                target.api.reparse(handle, junction_buffer(current))
