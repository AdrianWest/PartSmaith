"""@package partsmith.extraction.tables
@brief Read conservative ruled-grid OCR candidates with Pillow and NumPy.
@details Preserve recognized cells without importing a native PDF parser.
"""

from io import BytesIO

import numpy as np
from PIL import Image


def _centers(indices):
    groups = []
    for value in indices:
        if groups and value <= groups[-1][-1] + 1:
            groups[-1].append(int(value))
        else:
            groups.append([int(value)])
    return [sum(group) / len(group) for group in groups]


def ruled_tables(image, words):
    """@brief Recognize a complete ruled grid only when its lines intersect.
    @param image Rendered PNG bytes.
    @param words Recognized OCR words and their pixel boxes.
    @return List of ruled-grid candidates containing rows and pixel bounds.
    @details Empty cells stay empty; never fabricate engineering values.
    Borderless, merged, damaged, or disconnected grids remain image/OCR
    candidates. Empty cells stay empty and carry no invented engineering data.
    """
    with Image.open(BytesIO(image)) as decoded:
        samples = np.asarray(decoded.convert("RGB"))
    _, width = samples.shape[:2]
    ink = np.max(samples[:, :, :3], axis=2) < 160
    ys = _centers(np.flatnonzero(ink.sum(axis=1) > width * 0.4))
    if len(ys) < 3:
        return []
    top, bottom = int(ys[0]), int(ys[-1])
    xs = _centers(np.flatnonzero(ink[top : bottom + 1, :].mean(axis=0) > 0.8))
    if len(xs) < 3:
        return []
    for x in xs:
        for y in ys:
            if not ink[
                max(0, int(y) - 2) : int(y) + 3,
                max(0, int(x) - 2) : int(x) + 3,
            ].any():
                return []
    rows = []
    for y0, y1 in zip(ys, ys[1:], strict=False):
        row = []
        for x0, x1 in zip(xs, xs[1:], strict=False):
            cell = [
                w
                for w in words
                if (
                    x0 < (w["box"][0] + w["box"][2]) / 2 < x1
                    and y0 < (w["box"][1] + w["box"][3]) / 2 < y1
                )
            ]
            cell.sort(key=lambda w: (w["box"][1], w["box"][0]))
            row.append(" ".join(w["text"] for w in cell))
        rows.append(row)
    return [{"box": [xs[0], ys[0], xs[-1], ys[-1]], "rows": rows}]
