# Phase 12.1 — Rendering approach

Scope: Phase 12 startup and the 12.1 increment on local Windows AMD64,
Python 3.12.10. This checkpoint does not close the full Phase 12 gate or
claim Linux/macOS or remote CI execution. The [startup checkpoint](phase-12-startup.md)
records prerequisite verification before implementation.

The existing setup window opens **Open 0402 Rendering Prototype (12.1)** as a
separate, resizable modeless wx frame. Processing controls, status, credential
handling and the shared redacted log remain available. The known synthetic
fixture is explicitly labelled and separate from extracted-session data. The
prototype cannot generate artifacts, edit engineering inputs or grant approval.
Production session integration and Banner3 belong to milestones 12.2–12.6.

## Rendering decision

Select the **PartSmith CPU mesh adapter 1.0**: NumPy **2.5.3** implements
orthographic projection and per-pixel depth testing; Pillow **12.3.0** produces
RGB frames and inspection labels; wxPython **4.3.1** displays bounded raw RGB
bytes in a buffered paint context. These dependencies were already pinned in
the local runtime; the GUI extra now explicitly pins NumPy/Pillow as well.
There is no GPU/OpenGL context or driver extension requirement. An unavailable
rasterizer or failing display context produces a failed viewport with retained
main-window data. The fixed-size RGB transport avoids image decoding in wx.

CPU rendering is sufficient for this bounded fixture experiment. Every frame
runs in a fresh rendering child; camera updates are coalesced, and only one
completed frame is retained pending GUI dispatch. This trades peak frame rate
for an explicit native-failure boundary. Large models and production navigation
remain subject to later milestones; there is no claim of interactive CAD-scale
performance or engineering measurement accuracy from the raster image.

Distribution implications: Pillow uses the [MIT-CMU license](https://pillow.readthedocs.io/en/stable/about.html#license),
and NumPy uses [BSD terms requiring notices with binary redistribution](https://numpy.org/doc/stable/license.html).
The project wheel references these as dependencies; it does not vendor their
binaries. Bundled distributions must retain their dependency notices, together
with the existing wxPython/wxWidgets and CadQuery/OCP/OCCT license obligations.
wxPython uses the [wxWindows Library Licence](https://wxpython.org/pages/license/);
CadQuery uses [Apache 2.0](https://github.com/CadQuery/cadquery), as does the OCP
wrapper's installed distribution metadata. The underlying OCCT remains
[LGPL with its additional exception](https://dev.opencascade.org/doc/occt-6.9.0/overview/html/).
NumPy's installed wheel also declares its bundled MIT, 0BSD, Zlib and CC0
components; redistributors must retain that wheel's complete notices.
The existing native CAD stack remains CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1
and OCCT 7.9.3.1; this increment introduces no new CAD backend.

## Coordinate and artifact contract

The wheel packages the exact existing `fixtures/threed/expected/0402.step` and
`fixtures/footprint/expected/0402.kicad_mod`, plus a canonical placement snapshot
from `fixtures/ir/v1.2/valid/0402.json`. STEP and footprint remain independent
generator outputs. Resource loading is independent of the working directory;
the source fallback is resolved relative to the module, never the current cwd.

The scene is right-handed in millimetres, with its origin at the footprint
reference centre, +X right, +Y up in the engineering plane, and +Z away from
the board. Pads are on Z=0. STEP import yields mm coordinates through OCP.
The existing convention-1.1 service applies column-vector placement as
`T * Rz * Ry * Rx * S * M`. Nonuniform scale, mirror, rotation and translation
are retained; unsupported frame/unit/convention records fail explicitly.
Rendering floats are derived only at the display boundary; camera updates
never reconstruct or write the original exact placement bytes.

The actual model bounds are 1.000 × 0.500 × 0.350 mm, centred on X/Y with
bottom Z=0. Pad 1 is west at X=-0.500 mm and pad 2 east at X=+0.500 mm;
actual pad sizes are 0.550 × 0.600 mm with their serialized roundrect radius.
The west model terminal centre is (-0.400, 0, 0.050) mm. The intentional
0.100 mm pad/terminal X difference remains visible; the viewer cannot snap
one artifact to the other. The 0402 model is symmetric and has no pin-1 marker:
the west relationship is checked against its known independent topology;
the viewer does not infer a unique pin identity from a symmetric mesh.
Linear fixture geometry is checked within 1e-9 mm; general tessellation uses
0.01 mm linear deflection and 0.1 rad angular tolerance. Engineering geometric
validators remain authoritative.

## Failure boundary and resource lifecycle

The GUI imports no CadQuery, OCP, VTK or Pillow drawing backend. A controller
thread supervises each hidden child, drains results outside wx, and publishes
events with viewer-instance ID, stage, outcome and camera revision. The GUI
timer discards obsolete or closing-window events. Child environments exclude
credential-shaped variables; stdout/stderr never enter saved logs.

Preparation owns STEP parser/CAD handles and tessellation. Rendering owns
NumPy arrays, depth buffers and Pillow images. Each child releases its native
resources on exit, including abrupt failure. No CAD handle, graphics context,
texture or database connection crosses into wx. The GUI owns only the current
wx bitmap and a temporary paint DC. Closing or failure clears the bitmap,
releases mouse capture, cancels work, kills/reaps any active child, removes all
private snapshots/mesh/frame files, and stops callbacks before window teardown.
The main window asynchronously waits for owned viewer cleanup when closing.

Admission limits are 8 MiB STEP, 1 MiB footprint, 16 KiB placement, 256 solids,
100,000 mesh vertices/triangles, 16 MiB scene transport, 4,000,000 pixels with
maximum 4096 per axis. Native preparation is limited to 30 seconds and each
render to 10 seconds; controller deadlines are injectable for acceptance.
Cancellation checks occur every 20 ms while a child runs, with bounded reaping.
Mesh-count checks occur after native tessellation in the isolated worker;
this prototype does not claim an OS-level CAD memory quota.

## Completion evidence

**Milestone rendering checks: PASS. Combined full regression: FAILED. Full
Phase 12 gate: OPEN.** Verified 2026-10-04 on the runtime stated above.

| Final check | Result |
| --- | --- |
| Startup source/native prerequisite checks | 122 passed; no failures/errors/skips |
| Final source geometry and desktop prototype checks | 43 passed; no failures/errors/skips |
| Final installed-wheel geometry, GUI, CLI and desktop checks | 63 passed; no failures/errors/skips |
| Installed package and packaged resources | All 99 package files match the final wheel; all three fixture resources match checkout bytes |
| Lint, format, dependencies, whitespace and tagged docstrings | PASS |

The [default viewport](phase-12.1-viewport.png) and
[rotated/resized viewport](phase-12.1-rotated-viewport.png) are actual bitmap
captures from the final installed-wheel prototype. The
[display evidence](phase-12.1-display-evidence.json) records measured wx
heartbeat spacing during preparation/rendering, immutable source identities,
main-control usability, retained camera, and child/cache cleanup.

The milestone manifest binds final source/native and installed-wheel results,
actual displayed viewport images, packaged fixture identities and the wheel.
Checks cover physical scale/orientation, west pin-1 relationship, independent
pad placement, full affine placement, actual roundrect geometry, rotation,
zoom, resizing, three repeated close/reopen cycles, singleton foregrounding,
main controls and session retention, malformed STEP, real preparation/render
process termination/timeouts, missing rasterizer, bitmap/context errors,
stale callbacks, main close during native work, and cache/child cleanup.

Broader regression evidence is recorded separately: **616 source/native tests
passed with `tests/test_extraction.py` excluded**, and **79 PDF extraction and
isolation tests passed in a separate process**. The initial combined full-source
run terminated with a Windows native access violation during
`test_supplied_corpus_ingestion_and_selected_pages`, with the active stack in
the pre-existing pypdf page-copy path. It published no complete JUnit report.
The [retained stack excerpt](history/phase-12.1-combined-source-crash.txt)
remains failed evidence. The isolated pass does not resolve or replace that
failure; no clean combined regression or full Phase 12 PASS is claimed. The
failure preceded execution of the new viewer tests, and this increment makes
no changes to PDF extraction or its dependencies.

Reproduction uses the project runtime, installing the wheel before wheel tests:

```powershell
.tools/python/python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir .tools/phase12/dist
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase12/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys; sys.path[:0]=['src','.']; import pytest; raise SystemExit(pytest.main(['tests/test_viewer_scene.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','-q','--junitxml=docs/gates/phase-12.1-source-results.xml']))"
.tools/python/python.exe -c "import sys; sys.path.insert(0,'.'); import partsmith.gui.scene; assert 'site-packages' in partsmith.gui.scene.__file__; import pytest; raise SystemExit(pytest.main(['tests/test_viewer_scene.py','tests/test_gui.py','tests/test_cli.py','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','-q','--junitxml=docs/gates/phase-12.1-wheel-results.xml']))"
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
```

Closeout refreshes finalized disk bytes with `scripts/verify_phase2_manifest.py
--manifest <manifest> --source disk --update`, then verifies each affected active
manifest and the Phase 5/6/8 manifests checked by CI. Archived manifests and
explicit old/new input hashes retain the original test/wheel/golden scope.
Because changes remain uncommitted, HEAD/Git verification of these new bytes
requires a later commit; this checkpoint verifies final LF checkout bytes.
The [artifact manifest](phase-12.1-artifacts.json) lists every refreshed active
manifest and its verification command; each archived baseline and explicit
old/new input digest is included. All refreshed hash maps, the current
checkpoint manifest, and CI's Phase 5/6/8 manifests verify successfully.
The dated Phase 10 correction's separate `source_sha256` map is also verified;
its original wheel/test identities and the failed review evidence are preserved.
Phase 9.5's obsolete `resources/PartSmail-Banner.png` entry is rebound to the
previously committed `PartSmith-Banner.png` rename, whose actual wheel bytes
and layout pass the desktop checks. The archive and refresh record preserve
the old path/hash; no historical wheel is relabelled.
