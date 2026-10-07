"""@file verify_production_engines.py
@brief Exercises bundled PDF rendering and each required OCR model offline.
@details Run with the installed embedded interpreter and -I. Only hashes and
word counts are retained; source text and application state are not published.
"""

import argparse
import io
import json
import os
import sys
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path


def main() -> int:
    """@brief Renders a frozen source page and runs all three OCR languages.
    @return Zero after owned runtime and engine execution verification.
    @details Requires the exact installed isolated interpreter. Uses a retained
    manufacturer drawing, temporary raster files and the normal OCR adapter.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.dont_write_bytecode = True
    for folder, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(folder) / name
            if path.is_symlink() or path.is_junction():
                raise ValueError("BUNDLE_LINK_FORBIDDEN")
            if path.suffix.lower() in {".pyc", ".pyo"}:
                raise ValueError("BUNDLE_BYTECODE_FORBIDDEN")
    from partsmith.pcm.bundle import file_identity, verify_bundle

    verify_bundle(root)
    os.environ["PARTSMITH_TESSERACT"] = str(root / "ocr/bin/tesseract.exe")
    os.environ["TESSDATA_PREFIX"] = str(root / "ocr/tessdata")
    with os.add_dll_directory(str(root / "ocr/bin")):
        import pypdfium2

        from partsmith.extraction.ocr import TesseractOCR
        from partsmith.pcm.native import verify_native_origins

        corpus = root / "partsmith/pcm/corpus"
        facts = json.loads((corpus / "packages.json").read_bytes())
        source = next(
            item["source"]
            for item in facts["packages"]
            if item["variant"] == "0402"
        )
        pdf_path = corpus / "sources" / Path(source["file"]).name
        if file_identity(pdf_path)["sha256"] != source["sha256"]:
            raise ValueError("ENGINE_SOURCE_CHANGED")
        with ExitStack() as resources:
            document = pypdfium2.PdfDocument(pdf_path)
            resources.callback(document.close)
            page = document[10]
            resources.callback(page.close)
            bitmap = page.render(scale=2)
            resources.callback(bitmap.close)
            image = bitmap.to_pil()
            resources.callback(image.close)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
        raster = buffer.getvalue()
        engine = TesseractOCR(timeout=60, page_segmentation=11)
        outcomes = {}
        for language in ("eng", "deu", "chi_sim"):
            words = engine.recognize(raster, (language,))
            if len(words) < 20:
                raise ValueError("ENGINE_OCR_EMPTY: " + language)
            outcomes[language] = {
                "state": "PASS",
                "recognized_words": len(words),
                "result_sha256": sha256(
                    json.dumps(words, sort_keys=True).encode("utf-8")
                ).hexdigest(),
            }
        report = {
            "schema_version": "partsmith-engine-acceptance-1.0",
            "state": "PASS",
            "scope": "Isolated engine execution; host provenance is separate",
            "inventory_sha256": file_identity(root / "inventory.json")[
                "sha256"
            ],
            "source_sha256": source["sha256"],
            "source_page": 11,
            "raster_sha256": sha256(raster).hexdigest(),
            "ocr_version": engine.version,
            "languages": outcomes,
            "native_libraries": verify_native_origins(root),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", "utf-8"
    )
    print("PASS: bundled PDF renderer and eng/deu/chi_sim OCR execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
