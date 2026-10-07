"""@package tests.test_extraction
@brief Verify Phase 10 PDF content, OCR, coordinates and failure behavior.
@details Exercise real manufacturer tables and the multilingual corpus.
"""

import base64
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from threading import Event, Timer

import pdfplumber
import pymupdf
import pytest
from jsonschema import Draft202012Validator

from partsmith.cli import main
from partsmith.extraction import (
    ExtractionCancelled,
    PDFDocument,
    TesseractOCR,
    extract_document,
    resolve_package,
)
from partsmith.extraction.coordinates import (
    bounds,
    inverse,
    overlay_box,
    region_box,
    transform_point,
    validate_region,
)
from partsmith.extraction.translation import attach_translation
from partsmith.gui.processing import ProcessingRequest, process_datasheet
from partsmith.ir.schema import load_schema
from partsmith.pdl.profiles import load_release_profile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = sorted(
    p
    for p in (ROOT / "test_data_sheets").iterdir()
    if p.suffix.lower() == ".pdf"
)


def validate_evidence(result):
    schema = load_schema("1.2")
    validator = Draft202012Validator(
        {
            "$defs": schema["$defs"],
            "$ref": "#/$defs/evidence",
        }
    )
    assert len({e["id"] for e in result["evidence"]}) == len(
        result["evidence"]
    )
    for evidence in result["evidence"]:
        validator.validate(evidence)
        assert evidence["interpretation"]["status"] == "UNKNOWN"
        assert evidence["interpretation"]["normalized_value"] is None
        assert (
            evidence["source"]["document_hash"] == result["document"]["sha256"]
        )
        validate_region(
            evidence["source"]["region"], evidence["source"]["page_geometry"]
        )
        render = evidence["source"]["render_transform"]
        if render:
            asset = base64.b64decode(result["assets"][render["image_sha256"]])
            assert sha256(asset).hexdigest() == render["image_sha256"]
            pix = pymupdf.Pixmap(asset)
            assert (pix.width, pix.height) == (
                render["width_px"],
                render["height_px"],
            )


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.name)
def test_supplied_corpus_ingestion_and_selected_pages(
    path, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    count = PDFDocument(path).page_count
    selected = (
        list(range(1, count + 1)) if count <= 32 else [1, count // 2, count]
    )
    result = extract_document(path, pages=selected, dpi=100)
    assert (
        result["document"]["sha256"] == sha256(path.read_bytes()).hexdigest()
    )
    assert result["selected_pages"] == selected
    assert result["evidence"]
    assert {"TEXT", "OCR", "IMAGE", "DIAGRAM"} & {
        e["type"] for e in result["evidence"]
    }
    assert all(
        e["source"]["page"] in result["selected_pages"]
        for e in result["evidence"]
    )
    validate_evidence(result)
    assert (
        set(tmp_path.iterdir()) == before
    )  # No IR, symbol, footprint or STEP.


@pytest.mark.parametrize(
    "path,page,token",
    [
        (
            ROOT
            / "test_data_sheets"
            / "DS_16911_RGB_LED_Clear_Lens_Common_Cathode_5mm.pdf",
            4,
            "Forward Voltage",
        ),
        (
            ROOT / "test_data_sheets/infineon_iaucn04s7n010g_datasheet_en.pdf",
            3,
            "Continuous drain current",
        ),
        (ROOT / "test_data_sheets/KA324-D.pdf", 3, "Ordering Information"),
        (ROOT / "test_data_sheets/LM2575-D.PDF", 24, "LM2575TV"),
    ],
)
def test_selected_page_and_table_content(path, page, token):
    result = extract_document(path, pages=[page], dpi=100)
    assert {e["source"]["page"] for e in result["evidence"]} == {page}
    tables = [e for e in result["evidence"] if e["type"] == "TABLE"]
    assert any(token in e["extracted"]["text"] for e in tables)


def test_open_table_preserves_parameter_value_and_unit_columns(monkeypatch):
    """@brief Keep all five columns of an open manufacturer table.
    @param monkeypatch Pytest patch helper.
    @return None.
    @details Check parameter/value/unit associations and merged-cell nulls.
    """

    def native_crash(*args, **kwargs):
        """@brief Reject the formerly crashing MuPDF table path.
        @param args Positional arguments.
        @param kwargs Keyword arguments.
        @return None.
        @details Fail if extraction attempts to use the retired detector.
        """
        raise AssertionError("MuPDF table detection must not be called")

    monkeypatch.setattr(pymupdf.Page, "find_tables", native_crash)
    result = extract_document(
        ROOT / "test_data_sheets/infineon_iaucn04s7n010g_datasheet_en.pdf",
        pages=[3],
        dpi=100,
    )
    rows = next(
        record["payload"]["rows"]
        for record in result["records"]
        if record["payload"]
        and "Continuous drain current" in str(record["payload"].get("rows"))
    )
    assert rows[0] == ["Parameter", "Symbol", "Conditions", "Value", "Unit"]
    assert rows[1][0] == "Continuous drain current"
    assert rows[1][3] == "252"
    assert rows[1][4] == "A"
    assert rows[2][0] is None  # Preserve merged cells, do not fill them.
    assert [row[3] for row in rows[1:5]] == ["252", "175", "37", "748"]
    avalanche = next(
        row for row in rows if row[0] == "Avalanche energy, single pulse2)"
    )
    assert avalanche[3:] == ["140", "mJ"]
    validate_evidence(result)


def test_native_table_failure_does_not_return_partial_success(
    language_pdf, monkeypatch
):
    """@brief Reject extraction when native table detection fails.
    @param language_pdf Native/scanned language fixture path.
    @param monkeypatch Pytest patch helper.
    @return None.
    @details An internal detector error must not silently drop table evidence.
    """
    monkeypatch.setattr(
        pdfplumber.page.Page, "find_tables", lambda *a, **kw: None
    )
    with pytest.raises(
        ValueError, match="content extraction failed on page 1"
    ):
        extract_document(language_pdf, pages=[1], dpi=100)


@pytest.fixture(scope="module")
def language_pdf():
    return ROOT / "fixtures/extraction/language-matrix.pdf"


@pytest.mark.parametrize(
    "native,scanned,language,token",
    [
        (1, 2, "eng", "voltage"),
        (3, 4, "deu", "Spannung"),
        (5, 6, "chi_sim", "产品规格"),
        # Chinese dominates this page; Tesseract's primary language matters.
        (7, 8, "chi_sim+eng+deu", "产品规格"),
    ],
)
def test_real_native_and_scanned_language_matrix(
    language_pdf, native, scanned, language, token
):
    hints = language.split("+")
    original = extract_document(
        language_pdf, pages=[native], language_hints=hints, dpi=300
    )
    assert token in " ".join(
        e["extracted"]["text"] for e in original["evidence"]
    )
    assert not any(e["type"] == "OCR" for e in original["evidence"])
    scan = extract_document(
        language_pdf,
        pages=[scanned],
        language_hints=hints,
        dpi=300,
        ocr=TesseractOCR(page_segmentation=6),
    )
    ocr = [e for e in scan["evidence"] if e["type"] == "OCR"]
    assert ocr
    text = " ".join(e["extracted"]["text"] for e in ocr)
    assert token in text
    assert "5" in text
    if native == 7:
        assert "Package" in text
        assert "TEST-32R" in text
    assert any(e["confidence"]["score"] > 0.5 for e in ocr)
    validate_evidence(original)
    validate_evidence(scan)
    source = next(
        e for e in original["evidence"] if token in e["extracted"]["text"]
    )
    fixture = json.loads(
        language_pdf.with_suffix(".json").read_text(encoding="utf-8")
    )
    assert sha256(language_pdf.read_bytes()).hexdigest() == fixture["sha256"]
    sample = next(s for s in fixture["samples"] if s["native_page"] == native)
    translation = sample["translation"]
    translated = attach_translation(source, translation)
    assert "translation" not in source
    assert translated["extracted"] == source["extracted"]
    assert translated["source"] == source["source"]
    assert translated["translation"] == translation


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("dpi", [100, 200])
@pytest.mark.parametrize("unit", [1, 2])
def test_shifted_mediabox_crop_rotation_dpi_overlay(
    tmp_path, rotation, dpi, unit
):
    path = tmp_path / "coordinates.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.draw_rect(
        pymupdf.Rect(100, 200, 180, 240), color=None, fill=(0, 0, 0)
    )
    page.insert_text((100, 120), "MARK 5 mm")
    doc.xref_set_key(page.xref, "MediaBox", "[20 30 420 530]")
    doc.xref_set_key(page.xref, "CropBox", "[70 80 370 480]")
    doc.xref_set_key(page.xref, "UserUnit", str(unit))
    page.set_rotation(rotation)
    doc.save(path)
    doc.close()
    result = extract_document(path, dpi=dpi)
    diagram = next(e for e in result["evidence"] if e["type"] == "DIAGRAM")
    source = diagram["source"]
    assert source["page_geometry"] == {
        "media_box": [20, 30, 420, 530],
        "crop_box": [70, 80, 370, 480],
        "rotation_deg": rotation,
        "user_unit": unit,
    }
    assert source["region"] == pytest.approx(
        {
            "x": 80 * unit,
            "y": 230 * unit,
            "width": 80 * unit,
            "height": 40 * unit,
        }
    )
    pixel = overlay_box(source)
    recovered = bounds(
        source["render_transform"]["pixel_to_page"], region_box(pixel)
    )
    assert recovered == pytest.approx(source["region"], abs=1e-5)
    # Independent visual oracle: overlay center lies inside the black marker.
    png = base64.b64decode(
        result["assets"][source["render_transform"]["image_sha256"]]
    )
    pix = pymupdf.Pixmap(png)
    x = int(pixel["x"] + pixel["width"] / 2)
    y = int(pixel["y"] + pixel["height"] / 2)
    assert max(pix.pixel(x, y)) == 0
    validate_evidence(result)


def ordering_pdf(path, ambiguous=False):
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    rows = [
        ["Part Number", "Package"],
        ["EXAMPLE-QFN-32R", "QFN-32"],
        ["EXAMPLE-TSSOP-28R", "TSSOP-28"],
    ]
    if ambiguous:
        rows.append(["EXAMPLE-QFN-32R", "QFN-24"])
    for y in range(len(rows) + 1):
        page.draw_line((20, 40 + y * 40), (400, 40 + y * 40))
    for x in [20, 230, 400]:
        page.draw_line((x, 40), (x, 40 + len(rows) * 40))
    for i, row in enumerate(rows):
        for x, text in zip([28, 238], row, strict=True):
            page.insert_text((x, 65 + i * 40), text)
    doc.save(path)
    doc.close()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("unit", [1, 2])
def test_native_table_shift_crop_rotation_and_user_unit(
    tmp_path, rotation, unit
):
    """@brief Preserve table coordinates across the alternate parser boundary.
    @param tmp_path Pytest temporary directory.
    @param rotation Original display rotation in degrees.
    @param unit Original physical PDF point scale.
    @return None.
    @details Check independent table bounds with shifted MediaBox and CropBox.
    """
    original = tmp_path / "ordering.pdf"
    ordering_pdf(original)
    source = tmp_path / "shifted.pdf"
    with pymupdf.open(original) as pdf:
        page = pdf[0]
        pdf.xref_set_key(page.xref, "MediaBox", "[10 20 430 320]")
        pdf.xref_set_key(page.xref, "CropBox", "[15 25 415 315]")
        pdf.xref_set_key(page.xref, "UserUnit", str(unit))
        page.set_rotation(rotation)
        pdf.save(source)
    result = extract_document(source, dpi=100)
    evidence = next(e for e in result["evidence"] if e["type"] == "TABLE")
    assert evidence["source"]["region"] == pytest.approx(
        {
            "x": 10 * unit,
            "y": 120 * unit,
            "width": 380 * unit,
            "height": 120 * unit,
        },
        abs=0.01,
    )
    assert evidence["extractor"]["method"] == "pdfplumber/lines"
    assert resolve_package(result, "EXAMPLE-QFN-32R")["package"] == "QFN-32"
    validate_evidence(result)


def test_multi_package_exact_mapping_and_gui_boundary(tmp_path):
    path = tmp_path / "ordering.pdf"
    ordering_pdf(path)
    result = extract_document(path, dpi=100)
    for part, package in [
        ("EXAMPLE-QFN-32R", "QFN-32"),
        ("EXAMPLE-TSSOP-28R", "TSSOP-28"),
    ]:
        mapping = resolve_package(result, part)
        assert mapping["status"] == "RESOLVED"
        assert mapping["part_number"] == part
        assert mapping["package"] == package
        assert mapping["candidates"][0]["evidence_id"] in {
            e["id"] for e in result["evidence"]
        }
    for part in ["EXAMPLE", "EXAMPLE-QFN-32", "EXAMPLE-QFN-32R-X"]:
        assert resolve_package(result, part)["status"] == "UNRECOGNIZED"
    logs = []
    assert (
        process_datasheet(
            ProcessingRequest(path, "EXAMPLE-QFN-32R"), logs.append, Event()
        )
        == "unavailable"
    )
    assert "Ordering-table package: QFN-32" in logs
    assert any("No component was built" in line for line in logs)
    assert any("Extracting page" in line for line in logs)
    ambiguous = tmp_path / "ambiguous.pdf"
    ordering_pdf(ambiguous, ambiguous=True)
    assert (
        resolve_package(extract_document(ambiguous), "EXAMPLE-QFN-32R")[
            "status"
        ]
        == "AMBIGUOUS"
    )


def test_real_ordering_table_maps_full_lm2575_suffix():
    result = extract_document(
        ROOT / "test_data_sheets/LM2575-D.PDF", pages=[24], dpi=100
    )
    mapping = resolve_package(result, "LM2575TV-ADJG")
    assert mapping["status"] == "RESOLVED"
    assert "TO-220" in mapping["package"]
    assert resolve_package(result, "LM2575")["status"] == "UNRECOGNIZED"


def test_scanned_ruled_table_has_ocr_cell_provenance(tmp_path):
    native = tmp_path / "table.pdf"
    ordering_pdf(native)
    scanned = tmp_path / "scan.pdf"
    with pymupdf.open(native) as original, pymupdf.open() as doc:
        png = original[0].get_pixmap(dpi=300).tobytes("png")
        page = doc.new_page(width=420, height=300)
        page.insert_image(page.rect, stream=png)
        doc.save(scanned)
    result = extract_document(scanned, dpi=300, language_hints=["eng"])
    tables = [e for e in result["evidence"] if e["type"] == "TABLE"]
    assert tables
    assert all(e["source"]["render_transform"] for e in tables)
    assert "EXAMPLE-QFN-32R" in tables[0]["extracted"]["text"]
    validate_evidence(result)


def test_force_ocr_on_native_page_and_translation_rejections(language_pdf):
    result = extract_document(
        language_pdf, pages=[1], force_ocr=True, language_hints=["eng"]
    )
    assert {"TEXT", "OCR"} <= {e["type"] for e in result["evidence"]}
    with pytest.raises(ValueError, match="provenance"):
        attach_translation(result["evidence"][0], {})


@pytest.mark.parametrize(
    "pages", [[], [0], [-1], [10000], [1, 1], [True], [1.5]]
)
def test_invalid_selection(pages):
    with pytest.raises(ValueError, match="one-based"):
        extract_document(CORPUS[0], pages=pages)


def test_corrupt_encrypted_and_bad_options(tmp_path, language_pdf):
    malformed = tmp_path / "bad.pdf"
    malformed.write_bytes(b"%PDF-1.7\nnot a document")
    with pytest.raises(ValueError):
        PDFDocument(malformed)
    encrypted = tmp_path / "encrypted.pdf"
    with pymupdf.open(language_pdf) as doc:
        doc.save(
            encrypted,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="reader",
        )
    with pytest.raises(ValueError, match="Encrypted"):
        PDFDocument(encrypted)
    for dpi in [0, 1000, float("nan"), True]:
        with pytest.raises(ValueError, match="DPI"):
            extract_document(language_pdf, dpi=dpi)
    with pytest.raises(ValueError, match="Language"):
        extract_document(language_pdf, language_hints=["not-installed"])
    with pytest.raises(ValueError, match="missing"):
        TesseractOCR().recognize(b"unused", ["not-installed"])


def test_cancel_before_start_and_between_pages(language_pdf):
    cancel = Event()
    cancel.set()
    with pytest.raises(ExtractionCancelled):
        extract_document(language_pdf, cancel=cancel)
    assert (
        process_datasheet(
            ProcessingRequest(language_pdf, "TEST"), lambda _: None, cancel
        )
        == "cancelled"
    )
    cancel.clear()
    with pytest.raises(ExtractionCancelled):
        extract_document(
            language_pdf, cancel=cancel, log=lambda _: cancel.set()
        )


def test_ocr_timeout_and_cancel_kill_child(monkeypatch):
    adapter = TesseractOCR()
    native_popen = subprocess.Popen
    children = []

    def slow_child(*_args, **kwargs):
        child = native_popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", slow_child)
    adapter.timeout = 0.1
    with pytest.raises(ValueError, match="timeout"):
        adapter._run(["--version"])
    adapter.timeout = 5
    cancel = Event()
    timer = Timer(0.1, cancel.set)
    timer.start()
    try:
        with pytest.raises(ExtractionCancelled):
            adapter._run(["--version"], cancel)
    finally:
        timer.cancel()
        timer.join()
    assert all(child.poll() is not None for child in children)


def test_deskew_affine_and_invalid_region():
    matrix = [[0.3, 0.04, 10], [0.02, -0.3, 500], [0, 0, 1]]
    inv = inverse(matrix)
    for x, y in [(0, 0), (40, 80), (123.4, 234.5)]:
        assert transform_point(
            inv, *transform_point(matrix, x, y)
        ) == pytest.approx((x, y))
    with pytest.raises(ValueError, match="Singular"):
        inverse([[0, 0, 0], [0, 0, 0], [0, 0, 1]])
    with pytest.raises(ValueError, match="outside"):
        validate_region(
            {"x": -1, "y": 0, "width": 5, "height": 5},
            {
                "media_box": [20, 30, 420, 530],
                "user_unit": 1,
            },
        )


def test_profile_and_deterministic_evidence_cli(tmp_path, capsys):
    profile = load_release_profile("mvp-1", "1.1")
    assert profile["document_extraction"]["languages"] == [
        "en",
        "de",
        "zh-Hans",
    ]
    one = extract_document(CORPUS[0], pages=[1], dpi=100)
    two = extract_document(CORPUS[0], pages=[1], dpi=100)
    assert one == two
    output = tmp_path / "evidence.json"
    assert (
        main(
            [
                "extract",
                str(CORPUS[0]),
                "--pages",
                "1",
                "--dpi",
                "100",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8")) == one
    assert (
        main(["extract", str(CORPUS[0]), "--pages", "1", "--dpi", "100"]) == 0
    )
    assert json.loads(capsys.readouterr().out) == one
    assert main(["extract", str(CORPUS[0]), "--pages", "0"]) == 2
