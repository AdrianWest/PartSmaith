"""@package partsmith.extraction.native_page
@brief Read native PDF content with pdfminer and pdfplumber.
@details Preserve text, tables and object bounds without importing MuPDF.
"""

from io import BytesIO

import pdfplumber
from pypdf import PdfWriter


def _clusters(boxes, tolerance):
    """@brief Cluster graphics whose bounding rectangles touch.
    @param boxes Graphics bounds in unrotated pdfminer coordinates.
    @param tolerance Maximum separation in raw canvas units.
    @return Cluster bounding boxes.
    @details Merge transitively and preserve complete original object extents.
    """
    groups = []
    for box in sorted(boxes):
        pending = list(box)
        changed = True
        while changed:
            changed = False
            remaining = []
            for group in groups:
                if (
                    pending[0] <= group[2] + tolerance
                    and group[0] <= pending[2] + tolerance
                    and pending[1] <= group[3] + tolerance
                    and group[1] <= pending[3] + tolerance
                ):
                    pending = [
                        min(pending[0], group[0]),
                        min(pending[1], group[1]),
                        max(pending[2], group[2]),
                        max(pending[3], group[3]),
                    ]
                    changed = True
                else:
                    remaining.append(group)
            groups = remaining
        groups.append(pending)
    return sorted(groups)


def read_page(source_page, geometry):
    """@brief Extract one page's native text, tables, images and graphics.
    @param source_page Original pypdf page, left unchanged.
    @param geometry Original MediaBox, CropBox, rotation and UserUnit.
    @return JSON-safe content with bounds in physical crop coordinates.
    @details Clone content/resources, excluding links and article chains.
    Remove rotation on the clone; account for pdfminer's raw units explicitly.
    """
    writer = PdfWriter()
    clone = writer.add_page(source_page, excluded_keys=["/Annots", "/B"])
    clone.rotation = 0
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    media, crop, unit = (
        geometry["media_box"],
        geometry["crop_box"],
        geometry["user_unit"],
    )
    height = media[3] - media[1]
    visible = (crop[0], height - crop[3], crop[2], height - crop[1])

    def native(box):
        """@brief Map raw parser bounds to physical unrotated crop bounds.
        @param box Raw x0/top/x1/bottom bounds.
        @return Physical crop-coordinate bounds.
        @details Preserve UserUnit and original crop offsets.
        """
        return [
            (box[0] - crop[0]) * unit,
            (box[1] - height + crop[3]) * unit,
            (box[2] - crop[0]) * unit,
            (box[3] - height + crop[3]) * unit,
        ]

    result = {
        "blocks": [],
        "tables": [],
        "images": [],
        "graphics": [],
        "envelopes": [],
    }
    with pdfplumber.open(stream) as pdf:
        original = pdf.pages[0]
        page = original.crop(visible)
        for line in page.extract_text_lines(return_chars=False):
            result["blocks"].append(
                {
                    "bbox": native(
                        (line["x0"], line["top"], line["x1"], line["bottom"])
                    ),
                    "text": line["text"] + "\n",
                }
            )
        graphics = [
            (o["x0"], o["top"], o["x1"], o["bottom"])
            for o in [*original.rects, *original.curves, *original.lines]
        ]
        regions = _clusters(graphics, 3 / unit)
        result["graphics"] = [native(r) for r in regions]
        result["images"] = [
            native((o["x0"], o["top"], o["x1"], o["bottom"]))
            for o in original.images
        ]
        envelopes = [
            r
            for r in regions
            if any(
                c["text"].strip()
                and c["x0"] < r[2]
                and c["x1"] > r[0]
                and c["top"] < r[3]
                and c["bottom"] > r[1]
                for c in page.chars
            )
        ]
        result["envelopes"] = [native(r) for r in envelopes]
        edges = {
            "explicit_vertical_lines": [],
            "explicit_horizontal_lines": [],
        }
        for box in envelopes:
            x0, top = max(box[0], visible[0]), max(box[1], visible[1])
            x1, bottom = min(box[2], visible[2]), min(box[3], visible[3])
            if x1 <= x0 or bottom <= top:
                continue
            for x in (x0, x1):
                edges["explicit_vertical_lines"].append(
                    {
                        "object_type": "line",
                        "x0": x,
                        "x1": x,
                        "top": top,
                        "bottom": bottom,
                        "width": 0,
                        "height": bottom - top,
                    }
                )
            for y in (top, bottom):
                edges["explicit_horizontal_lines"].append(
                    {
                        "object_type": "line",
                        "x0": x0,
                        "x1": x1,
                        "top": y,
                        "bottom": y,
                        "width": x1 - x0,
                        "height": 0,
                    }
                )
        for table in page.find_tables(edges):
            if not table.rows or len(table.rows[0].cells) < 2:
                continue
            box = list(table.bbox)
            clipped = [
                max(box[0], visible[0]),
                max(box[1], visible[1]),
                min(box[2], visible[2]),
                min(box[3], visible[3]),
            ]
            if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
                continue
            result["tables"].append(
                {
                    "bbox": native(clipped),
                    "rows": table.extract(),
                    "original_bbox": box,
                    "visible_intersection": box != clipped,
                }
            )
    return result
