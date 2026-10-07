"""@package partsmith.extraction.isolated
@brief Keeps native PDF and OCR failures outside the desktop process.
@details Supervised output preserves origin, pre-failure diagnostics and exit
status through the caller's redacting sink; descendants are contained.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from partsmith.extraction.ocr import ExtractionCancelled, check_cancel
from partsmith.process import run_process


def extract_isolated(
    source,
    *,
    cancel=None,
    log=lambda _: None,
    output_budget=2 * 1024 * 1024,
    **options,
):
    """@brief Extracts local evidence in a fresh supervised process.
    @param source Acquired PDF snapshot path.
    @param cancel Optional cancellation event.
    @param log Redacting origin/stage progress callback.
    @param output_budget Maximum native log transport bytes.
    @param options Explicit extraction page, rendering and OCR options.
    @return Complete local result with original source assets.
    @details Cancellation and timeout kill/reap the worker and OCR children;
    native crashes leave the parent and acquired source usable.
    """
    check_cancel(cancel)
    with tempfile.TemporaryDirectory(prefix="partsmith-extract-") as directory:
        root = Path(directory)
        request = {"source": str(Path(source).resolve()), "options": options}
        (root / "request.json").write_text(
            json.dumps(request), encoding="utf-8"
        )
        package_root = str(Path(__file__).resolve().parents[2])
        bootstrap = (
            "import sys; sys.path.insert(0,sys.argv[1]); "
            "from partsmith.extraction.isolated import _worker; "
            "_worker(sys.argv[2])"
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if not any(
                token in key.upper()
                for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
            )
        }

        def progress(origin, text):
            """@brief Forwards structured progress and preserves other output.
            @param origin stdout or stderr stream identity.
            @param text Complete bounded output line.
            @return Whether the structured progress line was consumed.
            @details The caller redacts messages before display/persistence.
            """
            if origin == "stdout" and text.startswith("PARTSMITH_EXTRACT "):
                log(
                    "[extraction] "
                    + json.loads(text.removeprefix("PARTSMITH_EXTRACT "))
                )
                return True
            return False

        try:
            result = run_process(
                [sys.executable, "-c", bootstrap, package_root, str(root)],
                log=log,
                cancel=cancel,
                timeout=1200,
                env=environment,
                on_line=progress,
                output_budget=output_budget,
            )
        except InterruptedError as error:
            raise ExtractionCancelled() from error
        except TimeoutError as error:
            raise ValueError("PDF extraction exceeded 20 minutes.") from error
        check_cancel(cancel)
        if result.returncode:
            raise ValueError(
                "The PDF parser process failed. "
                "The application is still running; try fewer pages."
            )
        path = root / "result.json"
        if not path.is_file() or path.stat().st_size > 512 * 1024 * 1024:
            raise ValueError("Extraction result exceeds transport budget")
        response = json.loads(path.read_bytes())
        if "error" in response:
            raise ValueError(response["error"])
        return response["result"]


def _worker(directory):
    """@brief Owns native PDF/OCR resources for one complete acquisition.
    @param directory Parent-created private operation directory.
    @return None.
    @details Disables Windows crash dialogs only in the child; publishes the
    full result only after completion, without reading stored credentials.
    """
    if os.name == "nt":
        import ctypes

        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    from partsmith.extraction.document import extract_document
    from partsmith.extraction.ocr import TesseractOCR

    root = Path(directory)
    request = json.loads((root / "request.json").read_bytes())
    options = request["options"]
    layout = options.pop("ocr_layout", None)

    def log(message):
        """@brief Emits complete local-stage progress to the supervised pipe.
        @param message Extraction progress detail.
        @return None.
        @details The parent handles redaction before display or persistence.
        """
        print("PARTSMITH_EXTRACT " + json.dumps(str(message)), flush=True)

    try:
        result = extract_document(
            request["source"],
            log=log,
            ocr=TesseractOCR(page_segmentation=layout)
            if layout is not None
            else None,
            **options,
        )
        response = {"result": result}
    except (ValueError, OSError) as error:
        response = {"error": str(error)}
    (root / "result.json").write_text(json.dumps(response), encoding="utf-8")
