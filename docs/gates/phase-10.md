# Phase 10 — Document extraction

**Gate: PASS**, verified 2026-10-04 against specification v0.9.6.
Prerequisite: [Phase 9.5 PASS](phase-9.5.md).
Scope: local Windows AMD64, Python 3.12.10, native KiCad 10.0.6,
PyMuPDF 1.26.7, pypdf 6.1.3, Tesseract 5.5.0.20241111. No remote CI or
Linux/macOS result is claimed.

| Phase work item | Implementation and evidence |
| --- | --- |
| PDF ingestion | `PDFDocument` snapshots and hashes original bytes, reads raw MediaBox/CropBox/UserUnit/rotation, rejects malformed or password-required PDFs, and supports manufacturer PDFs that open with an empty password. The input limit is 100 MiB/5,000 pages. |
| Page selection | Validated, unique one-based indices; extraction preserves original page numbers and document identity. Missing, duplicate, fractional, boolean, zero and out-of-range selections fail. CLI `--pages` selects relevant pages from large manuals. |
| OCR | Cancellable local Tesseract adapter with bounded execution, child cleanup on cancellation/timeout, language-data checks, word boxes and confidence. Automatic OCR on pages without native text; explicit `--ocr` also processes native pages. Page segmentation 3/6/11 is explicit and retained in the supporting records. |
| Tables | Native table cells/merged nulls retained without numeric interpretation. Scanned ruled grids retain OCR cell text and render provenance. Borderless, merged, damaged or disconnected scanned grids remain image/OCR candidates. |
| Diagrams/images | Vector clusters and embedded-image regions reference lossless, content-addressed page PNGs. Objects bleeding outside the page retain their original object extent alongside their visible source intersection. Actual Evidence regions must remain inside the physical original MediaBox. |
| Evidence conversion | IR 1.2-compatible Evidence records plus language/table/word/image supporting records. Original document hash, page, physical source region, acquisition revision, extractor version and confidence are retained. Quantities and engineering interpretation remain UNKNOWN; adapters create no Component IR, symbol, footprint or STEP. |
| Corpus and provenance tests | All 24 supplied PDFs ingest; 279 selected pages from 4,102 original pages are exercised. Short documents (through 32 pages) use every page; longer documents use first/middle/last. The [corpus inventory](phase-10-corpus.json) pins filenames, original hashes, page counts and selections. Native ordering/electrical tables also have explicit content oracles. |

The versioned `mvp-1@1.1` extraction profile pins English, German and Simplified
Chinese (`eng`, `deu`, `chi_sim`). Earlier engineering fixtures retain the
unchanged `mvp-1@1.0` profile. The retained synthetic language corpus includes
native and image-only scanned pages for each language and a mixed sample;
reference OCR uses 300 DPI and text-block segmentation mode 6. Tests require
known source-language tokens and numerals and retain recognition confidence;
they do not claim perfect OCR. Original text and explicit manual translations
are retained separately with provider/model/timestamp provenance. Language
candidates use script/keyword hints and may remain uncertain. No translation
provider or live AI credential is used.

Coordinate tests cover every orthogonal rotation, two DPI settings, shifted
MediaBox/CropBox and UserUnit 1/2. They compare canonical bounds with independent
known physical coordinates and check overlay pixels against a rendered black
marker. Affine inverse tests additionally cover deskew-like shear/rotation;
the adapter does not deskew or perform non-affine dewarping. Canonical source
regions use PDF points, not engineering mm. All four box corners are transformed;
out-of-page Evidence and singular/non-finite mappings fail.

The full part number is preserved through the GUI worker and CLI. Recognized
ordering-table headers plus an exact complete order-number match produce an
unreviewed package candidate. Synthetic multi-package tests distinguish full
QFN/TSSOP suffixes and block family-only, unknown and conflicting mappings.
The real LM2575 table maps `LM2575TV-ADJG` to its TO-220 entry. This does not
assert universal recognition of every manufacturer table or production package
approval. Start logs extraction progress and package status, then reports the
remaining Phase 11 interpretation boundary without a false build success.

Verification records:

- Full source suite, including real wx, native KiCad and credential restart:
  **570 passed**, no failures/errors/skips.
- Expanded extraction/service corpus checks: **82 passed**.
- Installed-wheel extraction/service, wx, native KiCad and credential checks:
  **98 passed**, no failures/errors/skips. Exact totals and hashes are recorded
  in [the artifact manifest](phase-10-artifacts.json).
- Lint, format, dependency consistency and packaged extraction profile: PASS.
- [Source results](phase-10-source-results.xml),
  [corpus/service results](phase-10-extraction-results.xml),
  [wheel results](phase-10-wheel-results.xml),
  [native/desktop diagnostic rerun](phase-10-native-results.xml).

The first restricted regression attempt triggered native KiCad crash dialogs.
Its stderr recorded denied access to KiCad's configuration directories and HKCU
registry. The native credential test was also denied. After user authorization,
native/desktop checks passed outside the sandbox and the full source run passed.
No KiCad runtime workaround or native-validator substitution was introduced.
Use a normal desktop shell with access to the existing KiCad configuration and
OS credential store when reproducing these checks.

The expanded corpus adds five PDFs and exercises all 72 of their pages.
Restricted installed-wheel runs crashed inside PyMuPDF native graphics/table
extraction; the same expanded checks passed with normal desktop access.
The GUI and CLI now isolate extraction in a separate process, relay progress,
and cooperatively cancel and reap the worker. Native worker failure returns
an extraction error while the application remains alive. Only the worker
disables blocking Windows crash dialogs. Four regression checks cover result
and progress delivery, abrupt worker exit, cancellation, and input errors.
A separate PyMuPDF 1.28.2 trial missed the existing drain-current table oracle;
production retains the validated 1.26.7 pin. No newer-parser PASS is claimed.
The prior 19-document evidence is archived under `docs/gates/history/`.
An intermediate full-suite run had 569 passes and a replay resource-read
failure because the agent replaced the installed wheel during that run.
The final full suite was rerun after installation finished. The intermediate
failure and newer-parser trial results are retained separately.

The final wheel and LM2575 CLI evidence sample are local generated outputs under
`.tools/phase10/`; their exact SHA-256 values are recorded in the artifact
manifest. The sample includes its referenced PNG assets and 48 Evidence records.
Frozen CAD constraints and all deterministic generators remain unchanged.
Shared CLI/GUI/packaging/documentation hashes in older manifests are refreshed
only after retaining their prior manifests under `docs/gates/history/`.
Those histories preserve the original evidence scope and wheel identities.

Reproduce with the project-local Python 3.12 runtime used for this gate:

```powershell
.tools/python/python.exe -m pip install -r requirements-ci.txt -r requirements-extraction.txt -r requirements-gui-windows.txt
.tools/python/python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir .tools/phase10/dist
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase10/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys; sys.path[:0]=['src','.']; import pytest; raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','-q','--basetemp=.tools/phase10/full-source-tmp','-o','cache_dir=.tools/phase10/unrestricted-cache','--tb=short','--junitxml=docs/gates/phase-10-source-results.xml']))"
.tools/python/python.exe -c "import sys; sys.path.insert(0,'.'); import partsmith.extraction; assert 'site-packages' in partsmith.extraction.__file__; import pytest; raise SystemExit(pytest.main(['tests/test_extraction.py','tests/test_extraction_isolation.py','tests/test_gui.py','tests/test_kicad_runtime.py','scripts/verify_gui.py','-q','--basetemp=.tools/phase10/final-wheel-tmp','-o','cache_dir=.tools/phase10/unrestricted-cache','--tb=short','--junitxml=docs/gates/phase-10-wheel-results.xml']))"
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
.tools/python/python.exe -m partsmith extract test_data_sheets/LM2575-D.PDF --pages 24 --dpi 100 --part-number LM2575TV-ADJG --output .tools/phase10/LM2575-evidence.json
```

The installed-wheel checks assert an installed import location. On a standard
Python installation, editable source installation and the normal `python -m
pytest` entry point also work. The wrapper above accommodates the repository's
embedded local Python runtime. Tesseract and the three trained-data files must
be installed; hashes of the observed native runtime/model files are recorded.
