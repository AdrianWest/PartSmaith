# Phase 12 — complete part inspection in the separate viewer

PASS, 2026-10-05, local Windows AMD64 / Python 3.12.10 / wxPython 4.3.1 /
KiCad 10.0.6. The separate viewer now provides **Symbol / Pin Mapping** alongside
**3D / Footprint**. The main Symbol/Footprint tab remains available.

The symbol page shows the actual generated native SVG, exact symbol bytes and
SHA-256, properties, pin numbers/names/electrical types, and independently parsed
footprint pad mapping. It compares actual pin fields with the displayed revision's
immutable IR and shows missing, duplicate, extra and mismatched identities.
Retained validation results must bind these symbol bytes. Selection highlights
the existing corresponding footprint pad without changing engineering data.

Stage/build/revision/hash matching prevents another attempt's symbol or preview
from substituting the displayed artifacts. Preliminary symbols never use final
previews. Missing, malformed or unsupported symbols preserve diagnostic 3D
inspection. An unreadable or absent SVG preserves textual symbol inspection.
Stale labels update without replacing an open viewer's snapshot. The selected
review page survives close/reopen and saved camera-state restoration. These are
read-only diagnostics; existing authenticated release services retain authority.

Verification:

- Source regression: **94 passed**, [results](phase-12-symbol-viewer-source-results.xml).
- Installed-wheel regression: **94 passed**, [results](phase-12-symbol-viewer-wheel-results.xml).
- After preview-read fallback and minimum-width corrections, final source and
  installed-wheel symbol/desktop checks each passed **18 tests**, with zero
  failures/errors/skips: [source](phase-12-symbol-viewer-final-source-results.xml),
  [installed](phase-12-symbol-viewer-final-wheel-results.xml).
- Final standalone source/wheel entry and actual wx main loop, from an unrelated
  working directory, load an explicit offline archive, inspect native symbol/pad
  mapping, retain the symbol tab on reopen and clean up native children:
  [source](phase-12-symbol-viewer-source-launch.json),
  [installed](phase-12-symbol-viewer-wheel-launch.json).
- Actual native drawing, table, validators and exact text are visible at normal
  size: [symbol page](phase-12-symbol-viewer-display/phase-12-symbol-inspection-accepted.png).
  At 540×420 the complete drawing fits the page width; remaining review content
  is reachable by vertical scrolling:
  [minimum size](phase-12-symbol-viewer-display/phase-12-symbol-inspection-minimum.png),
  [scrolled text](phase-12-symbol-viewer-display/phase-12-symbol-inspection-scrolled.png).
  Desktop checks also cover 1000×800 and 740×620. These captures are source UI
  evidence at the actual 96 DPI display; installed functional checks cover the
  same code without claiming a new physical multi-monitor/DPI acceptance.
- **101 Python source files** match wheel and installation byte for byte. Banner3
  matches source/wheel/sdist/installation: [package receipt](phase-12-symbol-viewer-package-evidence.json).
- Ruff lint/format, tagged documentation on all seven changed Python files,
  dependency consistency and `git diff --check` pass. Active input maps and
  CI-required Phase 5/6/8 manifests are refreshed and verified from final disk
  bytes; previous/new hashes and scope are in the [active receipt](phase-12-artifacts.json).

Visual inspection reveals overlapping reference/value labels in the existing
fixture's generated native symbol. The page faithfully displays that SVG; this
UI amendment does not claim a symbol-generator layout correction.

The initial oversized-byte pytest parameter produced an overlong Windows test
environment variable, and the initial desktop check assumed the previous
non-notebook origin. Their [original failed XML](history/phase-12-symbol-viewer-initial-source-results.xml.gz)
is retained losslessly as gzip. Later failed checks exposed an invalid attempt
to inject a missing CAS reference through the validating session API and a
native list-control minimum width that clipped the preview:
[preview fault](history/phase-12-symbol-viewer-preview-fault-source-results.xml),
[resize fault](history/phase-12-symbol-viewer-resize-source-results.xml).
The fault injection now targets the read boundary, and the table's explicit
minimum width permits internal column scrolling. Final checks passed after
those corrections; failed attempts are not relabeled as success.

The initial automated capture was occluded by VS Code and is not accepted visual
evidence. The accepted captures use a temporarily topmost offline QA window;
production window behavior is unchanged.

Closeout also found pre-existing Banner3 drift: the recorded banner was
`4e6762730e8fa39804f3e19595ff49fb66446dce53b0f30163e9cdfd8554a8bd`,
while the preserved current source image is
`080c313c8befd231672174a5ad2473a5ba6ab388ba1c2b977d3fea9377e8a5c8`.
The [previous recorded bytes](history/phase-12-banner3-before-symbol-viewer.png)
were recovered from the previous accepted wheel. Current resize/resource tests
and package parity validate the current image; its original source file was not
edited by this amendment. The specification derives banner dimensions from the
loaded asset rather than recording a stale pixel width.

This is a scoped viewer amendment. Original full-gate, banner-amendment, PDF
stability and native KiCad menu evidence retain their historical scope. The
previous active manifest/report are preserved under `docs/gates/history/`.
No new full 750-test run, native KiCad menu launch, other-OS GUI or remote CI
acceptance is claimed.

Commands, using the project Python 3.12 environment:

```powershell
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','tests/test_desktop_generation.py','tests/test_desktop_release.py','tests/test_desktop_placement.py','tests/test_viewer_scene.py','tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-symbol-viewer-source-results.xml']))"
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','tests/test_desktop_generation.py','tests/test_desktop_release.py','tests/test_desktop_placement.py','tests/test_viewer_scene.py','tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-symbol-viewer-wheel-results.xml']))"
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-symbol-viewer-final-source-results.xml']))"
.tools/python/python.exe -c "from hatchling.build import build_wheel,build_sdist;print(build_wheel('.tools/phase12-symbol-viewer/dist'));print(build_sdist('.tools/phase12-symbol-viewer/dist'))"
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase12-symbol-viewer/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-symbol-viewer-final-wheel-results.xml']))"
C:/GIT_HUB/PartSmaith/.tools/python/python.exe C:/GIT_HUB/PartSmaith/scripts/verify_phase12_launch.py --source --transport C:/GIT_HUB/PartSmaith/.tools/phase12-full/launch-fixture.partsmith --output C:/GIT_HUB/PartSmaith/docs/gates/phase-12-symbol-viewer-source-launch.json
C:/GIT_HUB/PartSmaith/.tools/python/python.exe C:/GIT_HUB/PartSmaith/scripts/verify_phase12_launch.py --transport C:/GIT_HUB/PartSmaith/.tools/phase12-full/launch-fixture.partsmith --output C:/GIT_HUB/PartSmaith/docs/gates/phase-12-symbol-viewer-wheel-launch.json
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
git diff --check
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each active sha256-map manifest> --source disk
```
