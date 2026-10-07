"""@package tests.test_symbol_inspection
@brief Verifies actual symbol inspection and exact viewer binding isolation.
@details Checks generated native previews, mapping faults, missing/stale data
and offline restoration without granting release approval.
"""

from copy import deepcopy
from pathlib import Path
from threading import Event

import pytest
from test_desktop_generation import ready_session

from partsmith.gui.artifact_scene import session_scene
from partsmith.gui.generation import generate_session
from partsmith.gui.scene import parse_footprint
from partsmith.gui.session import Session
from partsmith.gui.symbol_inspection import (
    MAX_SYMBOL_BYTES,
    bound_symbol,
    parse_symbol,
    pin_mapping,
)
from partsmith.ir.canonical import canonical_json

ROOT = Path(__file__).resolve().parents[1]
SYMBOL = (ROOT / "fixtures/symbol/expected/0402.kicad_sym").read_bytes()


@pytest.fixture(scope="module")
def generated_archive(tmp_path_factory):
    """@brief Generates and saves one real reviewed fixture without approval.
    @param tmp_path_factory Module-owned isolated archive directory factory.
    @return Saved archive containing actual native artifacts.
    @details Each check loads a separate working session for fault injection.
    """
    root = tmp_path_factory.mktemp("symbol-inspection")
    session = ready_session(root)
    generate_session(session, Event(), lambda *args, **kwargs: None)
    archive = root / "generated.partsmith"
    session.save(archive)
    return archive


def test_symbol_parser_retains_actual_names_types_and_properties():
    """@brief Reads pin labels and electrical types from exact symbol bytes.
    @return None.
    @details Escaped names are decoded without replacing them with IR values.
    """
    content = SYMBOL.replace(b'(name "1"', b'(name "A\\"B"')
    content = content.replace(b"(pin passive", b"(pin input", 1)
    report = parse_symbol(content)
    assert report["properties"]["Reference"] == "R"
    assert report["pins"][0] == {
        "number": "1",
        "name": 'A"B',
        "electrical_type": "input",
    }


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"()",
        b"(kicad_symbol_lib)",
        SYMBOL[:-3],
        SYMBOL.replace(
            b'(symbol "TEST-R-0402"',
            b'(symbol "TEST-R-0402" (extends "Other")',
        ),
        b"x" * (MAX_SYMBOL_BYTES + 1),
    ],
    ids=[
        "empty",
        "empty-node",
        "no-symbol",
        "truncated",
        "inherited",
        "oversized",
    ],
)
def test_malformed_or_unsupported_symbol_is_explicitly_unavailable(content):
    """@brief Rejects invalid symbol inputs before preview construction.
    @param content Malformed, inherited or oversized symbol library bytes.
    @return None.
    @details No idealized drawing or reviewed pin list substitutes the bytes.
    """
    with pytest.raises(ValueError):
        parse_symbol(content)


def test_mapping_retains_duplicate_missing_extra_and_mismatched_pins():
    """@brief Detects pin name/type, duplicate and missing mapping faults.
    @return None.
    @details Generated fields remain visible even when comparison fails.
    """
    pins = parse_symbol(SYMBOL)["pins"]
    actual = [
        dict(pins[0], name="Wrong", electrical_type="output"),
        pins[0],
        dict(pins[1], number="3"),
    ]
    rows = pin_mapping(actual, pins, [{"number": "1"}, {"number": "2"}])
    assert rows[0]["name"] == "Wrong"
    for message in ("Duplicate", "name differs", "electrical_type differs"):
        assert message in rows[0]["diagnostic"]
    assert "Missing footprint pad" in rows[2]["diagnostic"]
    assert any(
        row["diagnostic"] == "Reviewed pin missing from symbol" for row in rows
    )
    assert any(
        row["diagnostic"] == "Footprint pad missing from symbol"
        for row in rows
    )


def test_real_bound_symbol_survives_offline_restore_without_approval(
    generated_archive,
    tmp_path,
):
    """@brief Inspects native final symbol data from a restored real attempt.
    @param generated_archive Exact generated transport from the module fixture.
    @param tmp_path Fresh source-independent operational storage.
    @return None.
    @details Reading the symbol preserves all session and release bindings.
    """
    session = Session.load(generated_archive, root=tmp_path)
    before = canonical_json(session.state)
    source, binding = session_scene(session)
    report = bound_symbol(session, binding, parse_footprint(source.footprint))
    assert b"<svg" in report["preview"]
    assert all(row["diagnostic"] == "MATCH" for row in report["mapping"])
    assert report["validation"]
    assert report["artifact"]["build_id"] == binding["build_id"]
    assert session.state["release"]["approved"] is False
    assert canonical_json(session.state) == before


@pytest.mark.parametrize("fault", ["missing", "revision", "hash"])
def test_symbol_never_substitutes_another_binding(
    generated_archive,
    tmp_path,
    fault,
):
    """@brief Rejects missing, cross-revision and wrong-hash symbol metadata.
    @param generated_archive Known real final-artifact archive.
    @param tmp_path Fault-specific restored operational session.
    @param fault Metadata fault to inject without altering immutable artifacts.
    @return None.
    @details Valid 3D data remains separately inspectable.
    """
    session = Session.load(generated_archive, root=tmp_path)
    source, binding = session_scene(session)
    drafts = deepcopy(session.state["drafts"])
    item = next(
        item
        for item in drafts["artifacts"]
        if item["type"] == "SYMBOL" and item["stage"] == "FINAL"
    )
    if fault == "missing":
        drafts["artifacts"].remove(item)
    elif fault == "revision":
        item["revision_id"] = "another-revision"
    else:
        item["sha256"] = "0" * 64
    session.update(drafts=drafts)
    with pytest.raises(ValueError):
        bound_symbol(session, binding, parse_footprint(source.footprint))
    assert session_scene(session)[0] == source


def test_preview_requires_exact_attempt_hash_and_final_stage(
    generated_archive,
    tmp_path,
    monkeypatch,
):
    """@brief Ignores mismatched native SVG and final SVG for preliminary data.
    @param generated_archive Known actual native generation archive.
    @param tmp_path Isolated restored session for preview metadata faults.
    @param monkeypatch Scoped unavailable-preview read fault injection.
    @return None.
    @details Missing SVG never prevents inspection of the exact symbol text.
    """
    session = Session.load(generated_archive, root=tmp_path)
    source, binding = session_scene(session)
    pads = parse_footprint(source.footprint)
    drafts = deepcopy(session.state["drafts"])
    original_get = session.get
    preview_reference = next(
        item["reference"]
        for item in drafts["previews"]
        if item["type"] == "SYMBOL"
    )

    def unreadable_preview(reference):
        """@brief Simulates a missing SVG while preserving engineering reads.
        @param reference Retained immutable asset reference to read.
        @return Original asset bytes when the asset is not the SVG.
        @details Raises OSError only for the symbol preview read.
        """
        if reference == preview_reference:
            raise OSError("Native symbol preview unreadable")
        return original_get(reference)

    with monkeypatch.context() as scoped:
        scoped.setattr(session, "get", unreadable_preview)
        report = bound_symbol(session, binding, pads)
        assert report["content"]
        assert report["preview"] is None
        assert report["preview_error"]
    for preview in drafts["previews"]:
        if preview["type"] == "SYMBOL":
            assert "artifact_sha256" in preview
            preview["artifact_sha256"] = "0" * 64
    session.update(drafts=drafts)
    assert bound_symbol(session, binding, pads)["preview"] is None
    assert (
        bound_symbol(session, {**binding, "stage": "PRELIMINARY"}, pads)[
            "preview"
        ]
        is None
    )
