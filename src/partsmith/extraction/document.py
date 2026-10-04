"""@package partsmith.extraction.document
@brief Extract PDF content into provenance-linked evidence candidates.
@details Preserve original source coordinates, table cells and render assets.
"""

import base64
import json
import math
import re
from collections import defaultdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import RLock

import pdfminer
import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader

from partsmith.extraction.coordinates import bounds, validate_region
from partsmith.extraction.native_page import read_page
from partsmith.extraction.ocr import TesseractOCR, check_cancel
from partsmith.extraction.tables import ruled_tables
from partsmith.ir.canonical import canonical_json
from partsmith.pdl.profiles import load_release_profile, release_profile_hash

_RENDER_LOCK = RLock()


def languages(text, hints):
    """Conservative language candidates; do not assert semantic detection."""
    found = []
    if re.search(r"[\u3400-\u9fff]", text):
        found.append("zh-Hans")
    if re.search(r"[äöüÄÖÜß]|\b(?:Spannung|Gehäuse|Strom)\b", text):
        found.append("de")
    if re.search(
        r"\b(?:voltage|package|current|device|features)\b", text, re.I
    ):
        found.append("en")
    return {
        "candidates": found or list(hints),
        "basis": "script/keyword hints",
    }


def classify(text):
    text = text.lower()
    for label, words in (
        ("ORDERING_INFORMATION", ("ordering", "order number")),
        ("PACKAGE_DIMENSIONS", ("dimensions", "mechanical", "gehäuse")),
        ("PIN_DESCRIPTION", ("pin description", "pin function")),
        ("PINOUT", ("pinout", "pin configuration")),
        ("BLOCK_DIAGRAM", ("block diagram",)),
        ("ELECTRICAL_CHARACTERISTICS", ("electrical characteristics",)),
        ("FEATURES", ("features",)),
    ):
        if any(word in text for word in words):
            return label
    return "OTHER"


class PDFDocument:
    """Immutable byte snapshot, including the original source identity."""

    def __init__(self, source):
        """@brief Snapshot and validate original PDF bytes with pypdf.
        @param source PDF filesystem path.
        @return None.
        @details Enforce byte/page limits and reject password-required input.
        """
        with Path(source).open("rb") as stream:
            self.data = stream.read(100 * 1024 * 1024 + 1)
        if len(self.data) > 100 * 1024 * 1024:
            raise ValueError("PDF exceeds the 100 MiB ingestion limit.")
        if b"%PDF-" not in self.data[:1024]:
            raise ValueError("The selected source is not a PDF.")
        self.sha256 = sha256(self.data).hexdigest()
        self.id = "pdf-" + self.sha256
        try:
            self.reader = PdfReader(BytesIO(self.data), strict=True)
            if self.reader.is_encrypted and not self.reader.decrypt(""):
                raise ValueError("Encrypted PDF requires a password.")
            self.page_count = len(self.reader.pages)
            if not 0 < self.page_count <= 5000:
                raise ValueError(
                    "PDF page count is outside the supported limit."
                )
        except ValueError:
            raise
        except Exception:
            raise ValueError(
                "PDF ingestion failed: malformed source."
            ) from None

    def geometry(self, index):
        page = self.reader.pages[index]
        media = [float(v) for v in page.mediabox]
        crop = [float(v) for v in page.cropbox]
        unit = float(page.get("/UserUnit", 1))
        rotation = int(page.get("/Rotate", 0)) % 360
        values = [*media, *crop, unit]
        if (
            not all(math.isfinite(v) for v in values)
            or unit <= 0
            or rotation not in (0, 90, 180, 270)
            or media[2] <= media[0]
            or media[3] <= media[1]
            or crop[2] <= crop[0]
            or crop[3] <= crop[1]
            or crop[0] < media[0]
            or crop[1] < media[1]
            or crop[2] > media[2]
            or crop[3] > media[3]
        ):
            raise ValueError("Unsupported PDF page geometry.")
        return {
            "media_box": media,
            "crop_box": crop,
            "user_unit": unit,
            "rotation_deg": rotation,
        }

    def inspect(self):
        return {
            "id": self.id,
            "sha256": self.sha256,
            "page_count": self.page_count,
            "pages": [self.geometry(i) for i in range(self.page_count)],
        }


def _native_mapping(geometry):
    media, crop, unit = (
        geometry["media_box"],
        geometry["crop_box"],
        geometry["user_unit"],
    )
    return [
        [1, 0, (crop[0] - media[0]) * unit],
        [0, -1, (crop[3] - media[1]) * unit],
        [0, 0, 1],
    ]


def _render(page, geometry, dpi, assets):
    """@brief Render the original cropped, rotated page with PDFium.
    @param page PDFium page handle.
    @param geometry Original page geometry, including UserUnit.
    @param dpi Physical rendering resolution.
    @param assets Content-addressed PNG collection to extend.
    @return PNG bytes and a pixel-to-original-page affine transform.
    @details Close bitmap handles explicitly and retain physical DPI in PNGs.
    """
    scale = dpi / 72
    if (
        page.get_width()
        * page.get_height()
        * (scale * geometry["user_unit"]) ** 2
        > 40_000_000
    ):
        raise ValueError("Rendered page exceeds the 40 megapixel limit.")
    bitmap = page.render(scale=scale * geometry["user_unit"], draw_annots=True)
    try:
        stream = BytesIO()
        bitmap.to_pil().save(stream, format="PNG", dpi=(dpi, dpi))
        png = stream.getvalue()
        width_px, height_px = bitmap.width, bitmap.height
    finally:
        bitmap.close()
    digest = sha256(png).hexdigest()
    assets[digest] = base64.b64encode(png).decode("ascii")
    # Pixel edges -> rotated page -> unrotated crop -> canonical MediaBox.
    native = _native_mapping(geometry)
    crop, unit = geometry["crop_box"], geometry["user_unit"]
    width = (crop[2] - crop[0]) * unit
    height = (crop[3] - crop[1]) * unit
    rotation = geometry["rotation_deg"]

    def convert(x, y):
        rx, ry = x / scale, y / scale
        # Use physical crop dimensions for every orthogonal page rotation.
        nx, ny = {
            0: (rx, ry),
            90: (ry, height - rx),
            180: (width - rx, height - ry),
            270: (width - ry, rx),
        }[rotation]
        return (nx + native[0][2], -ny + native[1][2])

    origin, px, py = convert(0, 0), convert(1, 0), convert(0, 1)
    matrix = [
        [px[0] - origin[0], py[0] - origin[0], origin[0]],
        [px[1] - origin[1], py[1] - origin[1], origin[1]],
        [0, 0, 1],
    ]
    return png, {
        "image_sha256": digest,
        "width_px": width_px,
        "height_px": height_px,
        "dpi_x": dpi,
        "dpi_y": dpi,
        "renderer": "PDFium",
        "version": str(pdfium.PDFIUM_INFO),
        "pixel_to_page": matrix,
    }


def extract_document(
    source,
    *,
    pages=None,
    dpi=200,
    ocr=None,
    force_ocr=False,
    language_hints=None,
    acquisition_revision_id="extraction-1",
    cancel=None,
    log=lambda _message: None,
):
    """@brief Return JSON-safe Evidence and content-addressed PNG assets.
    @param source Original PDF filesystem path.
    @param pages Unique one-based pages, or None for every page.
    @param dpi Rendering resolution between 72 and 600.
    @param ocr Optional local OCR adapter.
    @param force_ocr Recognize text even on pages containing native text.
    @param language_hints Release-profile OCR languages, or None for defaults.
    @param acquisition_revision_id Identity retained on every Evidence record.
    @param cancel Optional cancellation event.
    @param log Progress callback.
    @return Dictionary of Evidence, supporting records and lossless PNG assets.
    @details Validate page selection first and fail on table detection errors.
    Native tables and vector clusters are candidates, never engineering truth.
    Scanned ruled tables retain OCR cells; other diagrams remain candidates.
    """
    check_cancel(cancel)
    if (
        not isinstance(dpi, int)
        or isinstance(dpi, bool)
        or not 72 <= dpi <= 600
    ):
        raise ValueError("DPI must be an integer between 72 and 600.")
    if not acquisition_revision_id:
        raise ValueError("An acquisition revision identity is required.")
    profile = load_release_profile("mvp-1", "1.1")
    pinned = profile["document_extraction"]
    hints = (
        pinned["ocr_languages"] if language_hints is None else language_hints
    )
    if not hints or not set(hints) <= set(pinned["ocr_languages"]):
        raise ValueError("Language hints must belong to the release profile.")
    document = PDFDocument(source)
    selected = (
        list(range(1, document.page_count + 1))
        if pages is None
        else list(pages)
    )
    if (
        not selected
        or len(selected) != len(set(selected))
        or any(
            type(p) is not int or not 1 <= p <= document.page_count
            for p in selected
        )
    ):
        raise ValueError("Select unique, valid one-based PDF pages.")
    result = {
        "schema_version": "document-extraction-1.0",
        "document": document.inspect(),
        "selected_pages": selected,
        "profile": {
            "id": "mvp-1",
            "version": "1.1",
            "sha256": release_profile_hash(profile),
        },
        "evidence": [],
        "records": [],
        "assets": {},
        "pages": [],
    }

    def emit(
        kind,
        page_number,
        geometry,
        region,
        text,
        *,
        payload=None,
        render=None,
        confidence=1,
        method="pdfminer/native",
        version=None,
    ):
        validate_region(region, geometry)
        evidence = {
            "type": kind,
            "source": {
                "document_id": document.id,
                "document_hash": document.sha256,
                "page": page_number,
                "region": region,
                "coordinate_convention": "document-page-1.0",
                "page_geometry": geometry,
                "render_transform": render,
            },
            "extracted": {"text": text, "value": None, "unit": None},
            "interpretation": {"normalized_value": None, "status": "UNKNOWN"},
            "extractor": {
                "method": method,
                "version": version or pdfminer.__version__,
            },
            "confidence": {
                "score": confidence,
                "basis": "extraction fidelity; unreviewed",
            },
            "acquisition_revision_id": acquisition_revision_id,
            "candidate_targets": [],
        }
        record = {
            "language": languages(text, pinned["languages"]),
            "payload": payload,
        }
        identity = sha256(
            canonical_json({"evidence": evidence, "record": record})
        ).hexdigest()
        evidence["id"] = "ev-" + identity
        record["evidence_id"] = evidence["id"]
        if evidence["id"] not in ids:
            ids.add(evidence["id"])
            result["evidence"].append(evidence)
            result["records"].append(record)

    ids = set()
    # Serialize PDFium within a process and close every native handle.
    with _RENDER_LOCK, pdfium.PdfDocument(document.data, password="") as pdf:
        pdf.init_forms()
        for number in selected:
            check_cancel(cancel)
            log(f"Extracting page {number} of {document.page_count}.")
            check_cancel(cancel)
            page = pdf[number - 1]
            geometry = document.geometry(number - 1)
            mapping = _native_mapping(geometry)
            try:
                content = read_page(
                    document.reader.pages[number - 1], geometry
                )
            except Exception as error:
                raise ValueError(
                    f"PDF content extraction failed on page {number}."
                ) from error
            blocks = content["blocks"]
            texts = []
            for block in blocks:
                if block["text"].strip():
                    texts.append(block["text"])
                    emit(
                        "TEXT",
                        number,
                        geometry,
                        bounds(mapping, block["bbox"]),
                        block["text"],
                    )
            vector_regions = content["graphics"]
            envelopes = content["envelopes"]
            tables = content["tables"]
            for table in tables:
                check_cancel(cancel)
                rows = table["rows"]
                emit(
                    "TABLE",
                    number,
                    geometry,
                    bounds(mapping, table["bbox"]),
                    json.dumps(rows, ensure_ascii=False),
                    payload={
                        "rows": rows,
                        "detection": {
                            "strategy": "lines",
                            "graphics_envelopes": envelopes,
                            "coordinate_convention": "unrotated-crop-top-left",
                        },
                        "detector_region": {
                            "bbox": table["original_bbox"],
                            "coordinate_convention": "pdfminer-page-top-left",
                            "visible_intersection": table[
                                "visible_intersection"
                            ],
                        },
                    },
                    method="pdfplumber/lines",
                    version=pdfplumber.__version__,
                )
            images = content["images"]
            # Render original crop/rotation. Parser rectangles are unrotated.
            png, render = _render(page, geometry, dpi, result["assets"])
            page.close()
            visual = [("IMAGE", box) for box in images]
            visual += [
                ("DIAGRAM", tuple(r))
                for r in vector_regions
                if r[2] - r[0] > 2 and r[3] - r[1] > 2
            ]
            for kind, box in visual:
                check_cancel(cancel)
                # PDF image/drawing objects may bleed beyond the visible page.
                # Extract their visible region, retaining the complete object
                # extent explicitly. Evidence stays inside the original page.
                crop = geometry["crop_box"]
                unit = geometry["user_unit"]
                visible = (
                    max(0, box[0]),
                    max(0, box[1]),
                    min((crop[2] - crop[0]) * unit, box[2]),
                    min((crop[3] - crop[1]) * unit, box[3]),
                )
                if visible[2] <= visible[0] or visible[3] <= visible[1]:
                    continue
                emit(
                    kind,
                    number,
                    geometry,
                    bounds(mapping, visible),
                    "",
                    payload={
                        "image_sha256": render["image_sha256"],
                        "representation": "page region",
                        "original_object_region": bounds(mapping, box),
                        "visible_intersection": tuple(box) != visible,
                    },
                    render=render,
                )
            if force_ocr or not texts:
                adapter = ocr or TesseractOCR()
                words = adapter.recognize(png, list(hints), cancel)
                settings = {
                    "language_hints": list(hints),
                    "page_segmentation": getattr(
                        adapter, "page_segmentation", None
                    ),
                }
                lines = defaultdict(list)
                for word in words:
                    lines[tuple(word["line"])].append(word)
                for line in lines.values():
                    box = [
                        min(w["box"][0] for w in line),
                        min(w["box"][1] for w in line),
                        max(w["box"][2] for w in line),
                        max(w["box"][3] for w in line),
                    ]
                    emit(
                        "OCR",
                        number,
                        geometry,
                        bounds(render["pixel_to_page"], box),
                        re.sub(
                            r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
                            "",
                            " ".join(w["text"] for w in line),
                        ),
                        payload={"words": line, **settings},
                        render=render,
                        confidence=sum(w["confidence"] for w in line)
                        / len(line),
                        method="Tesseract",
                        version=adapter.version,
                    )
                if not words:
                    log(f"Page {number}: OCR found no readable text.")
                if not tables:
                    for table in ruled_tables(png, words):
                        emit(
                            "TABLE",
                            number,
                            geometry,
                            bounds(render["pixel_to_page"], table["box"]),
                            json.dumps(table["rows"], ensure_ascii=False),
                            payload={"rows": table["rows"], **settings},
                            render=render,
                            method="Tesseract/ruled-grid-1.0",
                            version=adapter.version,
                            confidence=min(
                                (w["confidence"] for w in words), default=0
                            ),
                        )
            result["pages"].append(
                {
                    "page": number,
                    "classification": classify("\n".join(texts)),
                    "render_transform": render,
                }
            )
    check_cancel(cancel)
    return result
