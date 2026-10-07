"""@package tests.test_atomic_target
@brief Exercises real disposable NTFS generation selection and anchored reads.
@details These probes require Windows; they do not publish user libraries or
claim crash recovery, journal persistence, editor refresh or production safety.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from partsmith.integration.atomic_target import (
    AtomicTargetProbe,
    junction_buffer,
)
from partsmith.integration.errors import IntegrationError
from partsmith.integration.policy import ResourcePolicy

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Requires local NTFS")


@pytest.fixture
def probe(tmp_path):
    """@brief Creates a fresh disposable target with two exact inventories.
    @param tmp_path Pytest-owned temporary directory.
    @return Yielded exclusively owned NTFS feasibility target.
    @details Removes the junction before pytest cleans its disposable tree.
    """
    generations = {
        name: {"first.txt": name.encode(), "dir/second.txt": name.encode()}
        for name in ("old", "new")
    }
    target = AtomicTargetProbe(tmp_path / "owned", generations, "old")
    try:
        yield target
    finally:
        target.close()


def test_root_handle_preserves_complete_generation_across_switch(probe):
    """@brief Keeps old roots anchored while new roots select new data.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details All descendants use NtCreateFile RootDirectory on the same handle.
    """
    with probe.reader() as handle:
        assert probe.api.read_relative(handle, "first.txt") == b"old"
        assert probe.switch("new", expected="old")
        assert probe.api.read_relative(handle, "dir/second.txt") == b"old"
        assert probe.api.read_relative(handle, "first.txt") == b"old"
    with probe.reader() as handle:
        assert probe.api.read_relative(handle, "first.txt") == b"new"
        assert probe.api.read_relative(handle, "dir/second.txt") == b"new"


def test_both_changed_library_tables_share_one_root_boundary(tmp_path):
    """@brief Selects both changed project tables through one root boundary.
    @param tmp_path Pytest-owned disposable parent.
    @return None.
    @details An old root keeps both original table bytes after replacement,
    while a reopened root reads both complete new table bytes.
    """
    generations = {
        generation: {
            "sym-lib-table": (
                f'(sym_lib_table (version 7) (lib (name "{generation}") '
                '(type "KiCad") (uri "Symbols.kicad_sym") '
                '(options "") (descr "probe")))\n'
            ).encode(),
            "fp-lib-table": (
                f'(fp_lib_table (version 7) (lib (name "{generation}") '
                '(type "KiCad") (uri "Footprints.pretty") '
                '(options "") (descr "probe")))\n'
            ).encode(),
        }
        for generation in ("old", "new")
    }
    probe = AtomicTargetProbe(tmp_path / "tables", generations, "old")
    try:
        with probe.reader() as handle:
            assert probe.switch("new", expected="old")
            for path, content in generations["old"].items():
                assert probe.api.read_relative(handle, path) == content
        with probe.reader() as handle:
            for path, content in generations["new"].items():
                assert probe.api.read_relative(handle, path) == content
    finally:
        probe.close()


def test_concurrent_anchored_readers_never_mix_generations(probe):
    """@brief Stresses bounded readers during repeated real junction switches.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details Four readers take 120 complete snapshots during 60 root switches.
    Exceptions, missing files or mixed snapshots fail the required real probe.
    """
    barrier = Barrier(5)

    def read_snapshots():
        """@brief Reads bounded complete pairs through one root per snapshot.
        @return Recorded old or new generation byte pairs.
        @details Starts concurrently with the junction writer.
        """
        barrier.wait(timeout=10)
        snapshots = []
        for _ in range(30):
            with probe.reader() as handle:
                snapshots.append(
                    (
                        probe.api.read_relative(handle, "first.txt"),
                        probe.api.read_relative(handle, "dir/second.txt"),
                    )
                )
        return snapshots

    with ThreadPoolExecutor(max_workers=4) as executor:
        readers = [executor.submit(read_snapshots) for _ in range(4)]
        barrier.wait(timeout=10)
        current = "old"
        for _ in range(60):
            new = "new" if current == "old" else "old"
            probe.switch(new, expected=current)
            current = new
        snapshots = [
            pair for reader in readers for pair in reader.result(timeout=20)
        ]
    assert len(snapshots) == 120
    assert set(snapshots) <= {(b"old", b"old"), (b"new", b"new")}


def test_independent_path_opens_need_quiescence(probe):
    """@brief Demonstrates the scope limit for independent file path lookups.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details This intentional mixed pair proves why editors must quiesce and
    reopen; a single reparse update is not a transaction over separate opens.
    """
    first = (probe.link / "first.txt").read_bytes()
    probe.switch("new", expected="old")
    second = (probe.link / "dir/second.txt").read_bytes()
    assert (first, second) == (b"old", b"new")


def test_sharing_failure_leaves_exact_old_generation(probe):
    """@brief Forces a real Win32 sharing failure before the reparse update.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details A read-only shared handle on the reparse object blocks write-open;
    releasing it allows the same intended switch to succeed.
    """
    with probe.api.directory(probe.link, reparse=True, share=1) as handle:
        before = probe.api.reparse(handle)
        with pytest.raises(OSError) as error:
            probe.switch("new", expected="old")
        assert error.value.winerror == 32
        assert probe.api.reparse(handle) == before
        assert (probe.link / "first.txt").read_bytes() == b"old"
    assert probe.switch("new", expected="old")


def test_cancel_rollback_and_noop_are_exact(probe):
    """@brief Cancels before switching and repeats a verified rollback safely.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details No-op and cancellation preserve the complete payload and files.
    """
    assert not probe.switch("new", expected="old", cancel=True)
    assert (probe.link / "first.txt").read_bytes() == b"old"
    assert probe.switch("new", expected="old")
    assert probe.switch("old", expected="new")
    assert not probe.switch("old", expected="old")
    for name, target in probe.generations.items():
        assert probe._inventory(target) == probe.inventories[name]


def test_stale_current_payload_is_a_conflict(probe):
    """@brief Refuses a switch whose expected generation is already stale.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details Exact raw reparse readback enforces the prototype base condition.
    """
    probe.switch("new", expected="old")
    with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
        probe.switch("old", expected="old")
    assert (probe.link / "first.txt").read_bytes() == b"new"


@pytest.mark.parametrize("mutation", ["changed", "extra"])
def test_modified_complete_generation_blocks_switch(probe, mutation):
    """@brief Refuses modified or extra generation files before selection.
    @param probe Exclusively owned feasibility target.
    @param mutation Changed or added file condition.
    @return None.
    @details Failure leaves the active old target unchanged.
    """
    path = probe.generations["new"] / (
        "first.txt" if mutation == "changed" else "extra.txt"
    )
    path.write_bytes(b"tampered")
    with pytest.raises(IntegrationError, match="TAMPERED_SOURCE"):
        probe.switch("new", expected="old")
    assert (probe.link / "first.txt").read_bytes() == b"old"


def test_foreign_reparse_payload_is_never_adopted(probe, tmp_path):
    """@brief Rejects a reparse destination outside the owned generation set.
    @param probe Exclusively owned feasibility target.
    @param tmp_path Pytest-owned disposable parent.
    @return None.
    @details Restores the fixture's owned payload for controlled cleanup only;
    the foreign directory's sentinel remains untouched.
    """
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    sentinel = foreign / "untouched.txt"
    sentinel.write_bytes(b"unrelated")
    with probe.api.directory(probe.link, reparse=True, write=True) as handle:
        probe.api.reparse(handle, junction_buffer(foreign))
    try:
        with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
            probe.switch("new", expected="old")
        assert sentinel.read_bytes() == b"unrelated"
    finally:
        with probe.api.directory(
            probe.link, reparse=True, write=True
        ) as handle:
            probe.api.reparse(
                handle, junction_buffer(probe.generations["old"])
            )


def test_existing_workspace_is_not_a_supported_target(tmp_path):
    """@brief Rejects adoption of an existing ordinary project directory.
    @param tmp_path Pytest-owned disposable directory.
    @return None.
    @details Existing unrelated content is retained byte-for-byte.
    """
    sentinel = tmp_path / "untouched.txt"
    sentinel.write_bytes(b"unrelated")
    with pytest.raises(IntegrationError, match="UNSUPPORTED_ATOMIC_INSTALL"):
        AtomicTargetProbe(tmp_path, {"old": {}, "new": {}}, "old")
    assert sentinel.read_bytes() == b"unrelated"


def test_generation_reparse_descendant_is_unsupported(probe):
    """@brief Refuses a foreign reparse inside an otherwise owned generation.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details Removes the deliberately injected fixture junction directly.
    """
    nested = probe.generations["new"] / "foreign"
    nested.mkdir()
    with probe.api.directory(nested, reparse=True, write=True) as handle:
        probe.api.reparse(handle, junction_buffer(probe.generations["old"]))
    try:
        with pytest.raises(
            IntegrationError, match="UNSUPPORTED_ATOMIC_INSTALL"
        ):
            probe.switch("new", expected="old")
    finally:
        nested.rmdir()


def test_volume_root_is_never_adopted(tmp_path):
    """@brief Rejects a filesystem root before creating any probe directories.
    @param tmp_path Pytest-owned directory identifying the real local volume.
    @return None.
    @details The root is never treated as an owned or disposable workspace.
    """
    with pytest.raises(IntegrationError, match="UNSUPPORTED_ATOMIC_INSTALL"):
        AtomicTargetProbe(Path(tmp_path.anchor), {"old": {}, "new": {}}, "old")


def test_changed_owner_marker_blocks_selection(probe):
    """@brief Refuses a target after its ownership marker changes.
    @param probe Exclusively owned feasibility target.
    @return None.
    @details The exact old reparse destination and unrelated content remain.
    """
    probe.marker.write_text("foreign-owner", encoding="ascii")
    with pytest.raises(IntegrationError, match="TARGET_CONFLICT"):
        probe.switch("new", expected="old")
    assert (probe.link / "first.txt").read_bytes() == b"old"


def test_outside_generation_path_cannot_escape_owned_workspace(
    probe, tmp_path
):
    """@brief Refuses a changed generation mapping outside the owned workspace.
    @param probe Exclusively owned feasibility target.
    @param tmp_path Pytest-owned parent containing the unrelated sentinel.
    @return None.
    @details Lexical containment is checked before reading or switching.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "untouched.txt"
    sentinel.write_bytes(b"unrelated")
    probe.generations["new"] = outside
    with pytest.raises(IntegrationError, match="UNSUPPORTED_ATOMIC_INSTALL"):
        probe.switch("new", expected="old")
    assert sentinel.read_bytes() == b"unrelated"
    assert (probe.link / "first.txt").read_bytes() == b"old"


def test_total_generation_limit_precedes_workspace_creation(
    tmp_path, monkeypatch
):
    """@brief Bounds total prepared generations before creating the workspace.
    @param tmp_path Pytest-owned disposable parent.
    @param monkeypatch Temporary resource policy substitution.
    @return None.
    @details Individually valid generations cannot bypass a cumulative limit.
    """
    monkeypatch.setattr(
        "partsmith.integration.atomic_target.ResourcePolicy",
        lambda: ResourcePolicy(object_bytes=3, total_bytes=5, object_count=2),
    )
    workspace = tmp_path / "limited"
    with pytest.raises(IntegrationError, match="RESOURCE_LIMIT"):
        AtomicTargetProbe(
            workspace,
            {"old": {"item": b"old"}, "new": {"item": b"new"}},
            "old",
        )
    assert not workspace.exists()
