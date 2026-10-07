# Phase 12 viewer performance amendment — 2026-10-05

The placement viewer now retains one isolated rendering child for the lifetime
of a scene. Previously it launched Python, loaded NumPy/Pillow and parsed the
mesh for every camera frame. Both the controller and desktop also rejected a
completed frame whenever another mouse movement had requested a newer camera,
which prevented visible progress during continuous dragging.

The worker caches the mesh, pad outlines and lit material colours. The
controller permits one frame in flight, retains only the latest pending camera
and caps submissions at 60 Hz. The desktop polls at 16 ms and displays
monotonically newer completed frames while movement continues. The final
requested camera converges after movement stops. Nested pan/layer state is
snapshotted; changed viewport sizes, layer selections, selected pads, replaced
instances and closing windows cannot restore obsolete output. Placement preview
replacement resets the displayed revision for its new worker.

Preparation remains an isolated bounded native operation. Render startup and
each requested frame have independent deadlines; an idle window can remain
open beyond the frame timeout. Closing, failure and scene replacement still
reap owned native process trees and remove private snapshots, meshes and
frames. CAD, NumPy and Pillow drawing stay outside the wx process. The shared
process supervisor adds optional polling and unlimited stream lifetime only
for callers that enforce their own operation deadlines; existing bounded
callers retain their defaults and incremental output budgets.

Request and acknowledgement messages are bounded and published atomically.
Short Windows sharing locks are handled by bounded publication retries and
retryable reads, outside the GUI thread. Each acknowledgement follows complete
RGB output, and the worker waits for the next request before changing that
output. Source STEP/footprint/placement bytes and prepared scene bytes remain
unchanged during navigation.

Local controller measurements on Windows AMD64, Python 3.12.10:

| Viewport | Fresh process, median | Persistent request to frame, median | Continuous-motion frame events |
| --- | --- | --- | --- |
| 400 × 300 | 194.34 ms | 32.96 ms | 60 in 2.00 s (30.0/s) |
| 880 × 480 | 201.67 ms | 33.82 ms | 53 in 2.00 s (26.5/s) |

The request-to-frame result includes transport and supervision, excluding
initial CAD preparation. It is approximately six times faster for the local
36-triangle 0402 fixture. These are controller frame events, not a universal
desktop frame-rate guarantee. The actual wx main-loop regression separately
checks visible bitmap progress during continuous camera requests. Models,
viewport sizes and machine load can change the resulting frame rate.

Evidence and validation:

- [Source regression](phase-12-viewer-performance-source-results.xml):
  109 passed, zero failures/errors/skips.
- [Installed-wheel regression](phase-12-viewer-performance-wheel-results.xml):
  109 passed, zero failures/errors/skips.
- [Measurements](phase-12-viewer-performance-measurements.json): real CPU
  rendering, intermediate/final camera delivery, worker reuse, unchanged
  inputs and native/cache cleanup.
- [Package evidence](phase-12-viewer-performance-package-evidence.json):
  105 Python/JSON package files match source, wheel and installation byte for
  byte; final wheel and sdist identities are recorded separately.
- Ruff lint/format, tagged Python documentation, dependency consistency and
  `git diff --check` pass. Active input maps, their dependent manifests and
  CI-required Phase 5/6/8 manifests are refreshed from final disk bytes and
  verified. The [amendment receipt](phase-12-viewer-performance-artifacts.json)
  records the affected/verified manifests; each affected active manifest records
  its archive and previous/new hashes.

Failed development checks are retained under `docs/gates/history/`: the first
two continuous-motion attempts exposed Windows transport sharing races. A
subsequent broad run used the incomplete `.venv` environment and lacked
PDFMiner/PyMuPDF. Final acceptance uses the complete project `.tools/python`
Python 3.12 runtime. The first desktop-motion check used only `wx.Yield`, which
does not dispatch the required native timer events on this runtime; it now
drives continuous requests within the actual wx main loop, with the original
failed result preserved. None of those failed attempts are relabelled as PASS.

This is a scoped viewer amendment. Earlier full-gate, PDF stability, native
KiCad launch and distribution evidence retain their historical scope. There
is no new full-project, other-OS, remote-CI or large-model acceptance claim.

Commands use the complete project Python 3.12 runtime:

```powershell
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','tests/test_desktop_generation.py','tests/test_desktop_release.py','tests/test_desktop_placement.py','tests/test_viewer_scene.py','tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-viewer-performance-source-results.xml']))"
.tools/python/python.exe -c "from hatchling.build import build_wheel,build_sdist;print(build_wheel('.tools/phase12-viewer-performance/dist'));print(build_sdist('.tools/phase12-viewer-performance/dist'))"
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase12-viewer-performance/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests/test_symbol_inspection.py','tests/test_desktop_generation.py','tests/test_desktop_release.py','tests/test_desktop_placement.py','tests/test_viewer_scene.py','tests/test_gui.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','-q','--tb=short','--junitxml=docs/gates/phase-12-viewer-performance-wheel-results.xml']))"
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.'];from scripts.verify_viewer_performance import main;raise SystemExit(main())" --output docs/gates/phase-12-viewer-performance-measurements.json
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
git diff --check
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each active sha256-map manifest> --source disk
```

Git-blob verification applies after these uncommitted input changes are
committed; `--source git --update` would hash HEAD rather than this amendment.
