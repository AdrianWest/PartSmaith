"""@package partsmith.extraction.ocr
@brief Runs local Tesseract with bounded execution and cancellation.
@details Uses the same executable discovery policy as startup prerequisites.
"""

import csv
import io
import subprocess
import tempfile
import time
from pathlib import Path

from partsmith.external_dependencies import find_tesseract


class ExtractionCancelled(Exception):
    """The caller cancelled extraction."""


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise ExtractionCancelled()


class TesseractOCR:
    def __init__(self, executable=None, *, timeout=120, page_segmentation=3):
        """@brief Resolves Tesseract and records its native version.
        @param executable Optional explicit OCR executable or command name.
        @param timeout Maximum seconds for each OCR operation.
        @param page_segmentation Supported layout mode: 3, 6 or 11.
        @return None.
        @details Explicit selection, environment, PATH and standard Windows
        discovery match the startup check; missing engines raise ValueError.
        """
        if page_segmentation not in (3, 6, 11):
            raise ValueError("Supported OCR segmentation modes are 3, 6, 11.")
        self.page_segmentation = page_segmentation
        self.executable = find_tesseract(executable)
        if not self.executable:
            raise ValueError("BFT-E002: Tesseract OCR is not installed.")
        self.timeout = timeout
        self.version = self._run(["--version"]).splitlines()[0]

    def _run(self, arguments, cancel=None):
        check_cancel(cancel)
        with (
            tempfile.TemporaryFile() as stdout,
            tempfile.TemporaryFile() as err,
        ):
            process = subprocess.Popen(
                [str(self.executable), *arguments],
                stdout=stdout,
                stderr=err,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            start = time.monotonic()
            try:
                while process.poll() is None:
                    check_cancel(cancel)
                    if time.monotonic() - start > self.timeout:
                        raise ValueError("BFT-E002: OCR timeout.")
                    time.sleep(0.05)
                if process.returncode:
                    raise ValueError("BFT-E002: OCR execution failed.")
                stdout.seek(0)
                return stdout.read().decode("utf-8")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()

    def recognize(self, image, language_hints, cancel=None):
        available = set(self._run(["--list-langs"], cancel).splitlines()[1:])
        if not language_hints or not set(language_hints) <= available:
            raise ValueError(
                "BFT-E002: Required OCR language data is missing."
            )
        with tempfile.TemporaryDirectory(prefix="partsmith-ocr-") as directory:
            source = Path(directory) / "page.png"
            source.write_bytes(image)
            data = self._run(
                [
                    str(source),
                    "stdout",
                    "-l",
                    "+".join(language_hints),
                    "--psm",
                    str(self.page_segmentation),
                    "tsv",
                ],
                cancel,
            )
        words = []
        for row in csv.DictReader(io.StringIO(data), delimiter="\t"):
            if row["level"] != "5" or not row["text"].strip():
                continue
            x, y, w, h = (
                int(row[k]) for k in ("left", "top", "width", "height")
            )
            words.append(
                {
                    "text": row["text"],
                    "box": [x, y, x + w, y + h],
                    "confidence": max(0, min(1, float(row["conf"]) / 100)),
                    "line": [
                        row[k] for k in ("block_num", "par_num", "line_num")
                    ],
                }
            )
        return words
