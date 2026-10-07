"""@package tests.test_desktop_evidence
@brief Checks explicit acquisition selection and exact provider requests.
@details Oversized selections preserve local evidence and source provenance.
"""

import copy
import json
from pathlib import Path

import pytest

from partsmith.ai import AIError
from partsmith.gui.evidence import (
    evidence_overlay,
    parse_pages,
    selected_request,
)
from partsmith.gui.session import Session
from partsmith.ir import canonical_json


@pytest.mark.parametrize(
    "text,expected",
    [("All Pages", None), ("1,3-5", [1, 3, 4, 5]), ("5,2", [2, 5])],
)
def test_explicit_page_selection(text, expected):
    """@brief Checks one-based ranges and deliberate all-page mode.
    @param text User selection text.
    @param expected Expected page list or None.
    @return None.
    @details No zero-based or default partial selection is inferred.
    """
    assert parse_pages(text) == expected


@pytest.mark.parametrize(
    "text", ["", "0", "2-1", "1,1", "1-3,2", "1-5001", "auto"]
)
def test_invalid_pages_fail_without_truncation(text):
    """@brief Rejects ambiguous or invalid acquisition selections.
    @param text Invalid page input.
    @return None.
    @details Ranges fail before source processing starts.
    """
    with pytest.raises(ValueError):
        parse_pages(text)


def evidence_session(tmp_path, count=3, text="original source text"):
    """@brief Builds a local-only unreviewed evidence session.
    @param tmp_path Temporary session directory.
    @param count Number of retained original evidence records.
    @param text Original text retained on every record.
    @return Session ready for deliberate provider selection.
    @details Uses fixture evidence shape only; no engineering IR is assembled.
    """
    root = Path(__file__).resolve().parents[1]
    item = json.loads((root / "fixtures/ir/v1.2/valid/0402.json").read_text())[
        "evidence"
    ][0]
    records = []
    for index in range(count):
        record = copy.deepcopy(item)
        record["id"] = f"ev-local-{index}"
        record["extracted"]["text"] = text
        record["interpretation"]["status"] = "UNKNOWN"
        record["candidate_targets"] = []
        records.append(record)
    session = Session(tmp_path / "session")
    extraction = {
        "document": {"sha256": item["source"]["document_hash"]},
        "selected_pages": [1],
        "evidence": records,
    }
    session.update(
        setup={"part_number": "FULL-SUFFIX-R"},
        extraction=session.put(canonical_json(extraction)),
    )
    return session


def test_exact_selection_and_trusted_targets(tmp_path):
    """@brief Checks requests contain exactly the selected records.
    @param tmp_path Temporary session directory.
    @return None.
    @details Unsupported target paths fail without changing retained evidence.
    """
    session = evidence_session(tmp_path)
    before = session.extraction()
    request = selected_request(session, "identify_package", ["ev-local-1"])
    assert [record["id"] for record in request.data["evidence"]] == [
        "ev-local-1"
    ]
    assert request.data["part_number"] == "FULL-SUFFIX-R"
    assert len(request._snapshot) <= 512 * 1024
    with pytest.raises((AIError, ValueError)):
        selected_request(
            session,
            "identify_package",
            ["ev-local-1"],
            ["/package/not-trusted"],
        )
    with pytest.raises(ValueError, match="Select evidence"):
        selected_request(session, "identify_package", [])
    assert session.extraction() == before


@pytest.mark.parametrize("count,text", [(129, "original"), (64, "x" * 12000)])
def test_oversized_request_keeps_all_local_evidence(tmp_path, count, text):
    """@brief Checks actual adapter count and canonical byte limits.
    @param tmp_path Temporary session directory.
    @param count Number of retained records.
    @param text Original evidence text.
    @return None.
    @details No truncation, first-record selection or silent splitting occurs.
    """
    session = evidence_session(tmp_path, count, text)
    before = session.extraction()
    with pytest.raises(AIError):
        selected_request(
            session,
            "identify_package",
            [item["id"] for item in before["evidence"]],
        )
    assert session.extraction() == before
    assert len(session.extraction()["evidence"]) == count


@pytest.mark.parametrize(
    "matrix",
    [
        [[0.5, 0, 20], [0, -0.5, 180], [0, 0, 1]],
        [[0, 0.25, 20], [0.25, 0, 30], [0, 0, 1]],
    ],
)
def test_native_text_overlay_uses_recorded_page_mapping(matrix):
    """@brief Checks shifted, cropped and rotated native-text overlays.
    @param matrix Recorded pixel-to-original-page affine transform.
    @return None.
    @details Native evidence inherits the correct page render without guessing.
    """
    from partsmith.extraction.coordinates import bounds

    region = bounds(matrix, (12, 24, 80, 60))
    source = {"page": 3, "region": region, "render_transform": None}
    extraction = {
        "pages": [{"page": 3, "render_transform": {"pixel_to_page": matrix}}]
    }
    render, box = evidence_overlay(extraction, {"source": source})
    assert render["pixel_to_page"] == matrix
    assert box == {"x": 12, "y": 24, "width": 68, "height": 36}
    assert source["render_transform"] is None
