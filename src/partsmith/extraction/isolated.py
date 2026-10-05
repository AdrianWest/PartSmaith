"""Keep native PDF failures outside the desktop application process."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from partsmith.extraction.ocr import ExtractionCancelled, check_cancel


def extract_isolated(source, *, cancel=None, log=lambda _: None, **options):
    """Extract in a fresh process; propagate progress and cancellation."""
    check_cancel(cancel)
    with tempfile.TemporaryDirectory(prefix="partsmith-extract-") as directory:
        root = Path(directory)
        request = {"source": str(Path(source).resolve()), "options": options}
        (root / "request.json").write_text(
            json.dumps(request), encoding="utf-8"
        )
        package_root = str(Path(__file__).resolve().parents[2])
        bootstrap = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from partsmith.extraction.isolated import _worker; "
            "_worker(sys.argv[2])"
        )
        with (root / "stderr.txt").open("wb") as stderr:
            process = subprocess.Popen(
                [sys.executable, "-c", bootstrap, package_root, str(root)],
                stdout=subprocess.DEVNULL,
                stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            position = 0
            started = time.monotonic()

            def drain():
                nonlocal position
                progress = root / "progress.jsonl"
                if progress.exists():
                    with progress.open(encoding="utf-8") as stream:
                        stream.seek(position)
                        for line in stream:
                            # A concurrent final write may be incomplete.
                            if not line.endswith("\n"):
                                break
                            log(json.loads(line))
                            position += len(line.encode("utf-8"))

            try:
                while process.poll() is None:
                    drain()
                    check_cancel(cancel)
                    if time.monotonic() - started > 1200:
                        raise ValueError("PDF extraction exceeded 20 minutes.")
                    time.sleep(0.05)
                drain()
                check_cancel(cancel)
                if process.returncode:
                    raise ValueError(
                        "The PDF parser process failed. "
                        "The application is still running; try fewer pages."
                    )
                response = json.loads(
                    (root / "result.json").read_text(encoding="utf-8")
                )
                if "error" in response:
                    raise ValueError(response["error"])
                return response["result"]
            finally:
                if process.poll() is None:
                    (root / "cancel").touch()
                    try:
                        # OCR cooperatively kills its child before exiting.
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                process.wait()


def _worker(directory):
    if os.name == "nt":
        import ctypes

        # A native failure belongs in the parent's error report, not a
        # blocking Windows crash dialog. This affects only this worker.
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    from partsmith.extraction.document import extract_document
    from partsmith.extraction.ocr import TesseractOCR

    root = Path(directory)

    class Cancellation:
        def is_set(self):
            return (root / "cancel").exists()

    with (root / "progress.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as progress:

        def log(message):
            progress.write(json.dumps(str(message)) + "\n")
            progress.flush()

        request = json.loads(
            (root / "request.json").read_text(encoding="utf-8")
        )
        options = request["options"]
        layout = options.pop("ocr_layout", None)
        try:
            result = extract_document(
                request["source"],
                cancel=Cancellation(),
                log=log,
                ocr=TesseractOCR(page_segmentation=layout)
                if layout is not None
                else None,
                **options,
            )
            response = {"result": result}
        except ExtractionCancelled:
            return
        except (ValueError, OSError) as error:
            response = {"error": str(error)}
        (root / "result.json").write_text(
            json.dumps(response), encoding="utf-8"
        )
