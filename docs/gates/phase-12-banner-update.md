# Phase 9.5 / 12 banner amendment

PASS, 2026-10-05, local Windows AMD64. The Phase 9.5 main GUI now loads the
exact `resources/PartSmith-Banner3.png` asset. The banner starts at client
`(0, 0)`, reaches both client edges without margins, and grows or shrinks with
the window while preserving the complete image and its aspect ratio. It stays
above the scrolling controls. The separate Phase 12 placement viewer has no
banner and its scrolling scene/controls occupy the full available client area.

The specification now states this placement in the Phase 9.5 requirements,
Phase 12 workflow/milestone/window contract, acceptance checks and section 12
viewer description. README usage and desktop/launch checks match the change.

Verification:

- Source desktop/service/prototype workflow: **44 passed**;
  [results](phase-12-banner-source-results.xml).
- Installed-wheel equivalent: **44 passed**;
  [results](phase-12-banner-wheel-results.xml).
- Main window resized to 620×740, 1050×900 and 1280×960: the banner's client
  origin and full width match the frame, and proportional height differs by
  at most one pixel. Bitmap geometry checked at 100%, 125%, 150% and 200%.
- Viewer resized to 540×420, 1000×800 and 740×620: no banner exists and the
  scrollable content fills the client area. Actual generation, placement
  controls, singleton/reopen, native failures and resource cleanup still pass.
- Actual standalone entry/main loop from an unrelated working directory:
  [source](phase-12-banner-source-launch.json) and
  [installed](phase-12-banner-wheel-launch.json). Camera retention and native
  child cleanup pass with explicit offline fixture data.
- Missing main banner logs a clear message; setup/save and the viewer remain
  usable: [resource failure check](phase-12-banner-missing-resource.json).
- **102 source/wheel/installed package files** match exactly. Wheel and sdist
  contain the exact Banner3 bytes: [package evidence](phase-12-banner-package-evidence.json).
- Ruff lint/format, tagged Python documentation, dependency consistency and
  whitespace checks pass. Affected active input maps and CI Phase 5/6/8 maps
  are refreshed and verified from final disk bytes.

This is a scoped GUI amendment. The earlier full Phase 12 source/wheel suites,
PDF stability runs, native KiCad menu capture and prior distributions retain
their original acceptance scope. Their identities are retained in archived
manifests; the active Phase 12 receipt records the new distribution and this
revalidation separately. The original full-gate/checkpoint reports are preserved
under `docs/gates/history/*-before-banner-update-2026-10-05.*`.

Commands used:

```powershell
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-banner-source-results.xml']))"
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase12-banner/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-banner-wheel-results.xml']))"
.tools/python/python.exe scripts/verify_phase12_launch.py --source --transport .tools/phase12-full/launch-fixture.partsmith --output docs/gates/phase-12-banner-source-launch.json
.tools/python/python.exe scripts/verify_phase12_launch.py --transport .tools/phase12-full/launch-fixture.partsmith --output docs/gates/phase-12-banner-wheel-launch.json
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
git diff --check
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each affected active sha256-map receipt> --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-5-artifacts.json --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-6-artifacts.json --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-8-artifacts.json --source disk
```
