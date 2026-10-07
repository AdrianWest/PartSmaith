# Phase 12 — human review and application UI

Complete part inspection amendment, 2026-10-05: the separate viewer now includes
**Symbol / Pin Mapping** alongside **3D / Footprint**. Actual symbol bytes,
native preview, pin fields and mapping diagnostics share the displayed artifact
binding. See the [scoped verification](phase-12-symbol-viewer.md), including the
final source/wheel checks, screenshots and preserved historical evidence.

Banner layout amendment, 2026-10-05: the Phase 9.5 main GUI now displays
Banner3 edge to edge and scales it with the window. The Phase 12 viewer has
no banner. See the [scoped revalidation](phase-12-banner-update.md). The full
gate evidence below retains its original acceptance scope and earlier layout.

Status: **PASS**, 2026-10-05. Milestones 12.1–12.10 are implemented and
revalidated against the final source and installed package. The Phase 11 PASS
and correction evidence were reviewed at startup; see [startup](phase-12-startup.md).
This gate covers the local Windows AMD64 desktop and deterministic supported
0402 workflow, with explicit local extraction and selected AI-candidate review.

The main application now retains complete acquisition data, engineering drafts,
proposals, generated artifacts, validation and separate input/release decisions
in an isolated working SQLite database and content-addressed asset store.
Save/Load uses a versioned, bounded, atomic `.partsmith` archive and validates
database/CAS/canonical identities before replacing the active session. Loading
and recovery preserve history while creating a new operational instance and
re-establishing the current OS reviewer. Immutable PDF snapshots remain usable
when the original path disappears or its contents change.

Evidence displays original text, page imagery and provenance regions. Page
ranges, DPI, OCR settings and resource budgets are explicit. Selected AI
requests disclose provider/model, exact record and byte counts, task/targets,
cost responsibility and `store=false`; oversized selections fail explicitly.
Initial assembly represents missing facts without supplying a fixture fallback.
Explicit typed proposals preserve Decimal values, original evidence, terminal
identity and exact-base bindings. Unsupported or incomplete package data stays
inspectable and blocks generation.

Generation uses the existing review/orchestration services in an isolated child.
The main GUI receives live redacted stdout/stderr, actual exit status, attempt
identities, committed stages and artifact references. Cancellation, timeout,
native failure, log/image/mesh/archive limits and stale events preserve truthful
outcomes. Worker connections remain owned by their threads. Native KiCad SVG
previews come from the actual generated symbol and footprint.

The owned modeless placement viewer opens the current attempt's actual STEP,
footprint and explicit placement, including failed-but-parseable final artifacts.
Banner3 is packaged unchanged, pinned above scrolling controls and resized from
its actual aspect ratio. Camera presets, pan/rotate/zoom/fit, independent layers,
pin/pad mappings, dimensions and measurements leave engineering bytes and
approval bindings intact. Exact numeric placement drafts, mirrors, preview,
discard and reason/evidence-bound proposals retain scale and immutable history.
Accepted placement changes invalidate release approval and rerun affected checks;
unchanged STEP reuse follows its declared dependency.

Final release review shows the actual validation results, blockers and exact
build/revision/manifest bindings. It requires a separate explicit OS-authenticated
decision. Save/Discard/Cancel applies to close, clear and session/source changes.
Offline restoration includes unfinished forms, proposals, native previews,
artifacts, decisions, history, viewer camera and pending placement drafts.

| Milestone | Completion evidence |
| --- | --- |
| 12.1 | [Rendering decision](phase-12.1.md); final prototype checks cover known dimensions/orientation, native errors/timeouts, unavailable graphics, pure GUI imports and repeated cleanup. |
| 12.2 | [Session foundation](phase-12.2.md); archive integrity/budgets, source replacement, offline independent loads, atomic failure and recovery checks. |
| 12.3 | [Evidence review](phase-12.3.md); original-region transforms, local/AI candidates, explicit page/AI selection, oversized-request and resource checks. |
| 12.4 | [Input review](phase-12.4.md); missing-fact roots/inventory, exact PDL selection, typed overrides, pin reorder/renumber/removal, stale heads and authenticated decisions. |
| 12.5 | [Generation](phase-12.5.md); actual native previews, progress, retained partial stages, failure/cancellation and declared boundaries. |
| 12.6 | [Owned viewer](phase-12.6.md); readiness, singleton/reopen, failed-attempt diagnostics, Banner3 and both launch paths. |
| 12.7 | [Inspection](phase-12.7.md); seven presets/layers, 1 mm pad-centre distance, 0.35 mm height, mapping and unchanged engineering bindings. |
| 12.8 | [Placement](phase-12.8.md); offset/height/rotation/mirror diagnostics, exact Decimal transport, preserved nonuniform scale, stale proposals and actual association failure after accepted offset. |
| 12.9 | [Release/recovery](phase-12.9.md); distinct decisions, forged/stale approval rejection, offline workflow, unfinished state and unsaved-work policy. |
| 12.10 | Final checks below and [exact-byte receipt](phase-12-artifacts.json). |

Final acceptance:

- Full source: **750 passed**, zero failures/errors/skips; [XML](phase-12-source-final-results.xml), [output](phase-12-source-final-output.txt).
- Full installed wheel: **750 passed**, zero failures/errors/skips; [XML](phase-12-wheel-final-results.xml), [output](phase-12-wheel-final-output.txt).
- Repeated installed PDF/core/desktop regression: **3 rounds, 194 passed each**;
  [raw attempt manifest](phase-12-pdf-stability/manifest.json). Attempts are retained
  individually and the runner stops at the first failure without retries.
- Real standalone entry/main loop from an unrelated working directory:
  [source](phase-12-source-launch.json) and [installed wheel](phase-12-wheel-launch.json).
  Explicit offline test data and credential-free test adapters exercise owned
  viewer reopen/camera retention and child cleanup through the actual entry.
- Actual KiCad 10.0.6 PCB Editor: **Tools → External Plugins → PartSmith Setup**
  launched the unmodified installed runtime; an explicit offline archive restored
  a ready viewer, displayed its actual generated model, then saved and closed.
  [Launch receipt](phase-12-kicad-launch.json), [parent/child identity](phase-12-kicad-process-evidence.json).
  The temporary launcher interpreter selection was restored to its original bytes.
- Wheel/source/installed parity: **102 package source files**; exact Banner3
  bytes in wheel, sdist and installation. [Distribution receipt](phase-12-package-evidence.json).
  Gate receipts remain in the repository to avoid circular sdist hashes.
- Ruff lint/format, dependency consistency, required tagged documentation on
  **45 delivered Python files**, and `git diff --check`: PASS.

Visual inspection accepted the complete Banner3, current generated scene,
placement controls and readable release results in the source captures, plus
the actual installed viewer launched by the native KiCad host:
[viewer](phase-12-display/phase-12-viewer.png),
[placement controls](phase-12-display/phase-12-viewer-controls.png),
[release review](phase-12-display/phase-12-release-review.png),
[native KiCad viewer](phase-12-display/phase-12-kicad-launch-viewer.png).
The automated installed-wheel desktop capture was occluded by VS Code; those
images are retained under history and excluded from visual acceptance.
Functional installed-wheel checks still completed successfully.

Resize checks cover 540×420, 1000×800 and 740×620 viewer sizes, scrolling and
the banner's full-width `(0,0)` position. Bitmap/DPI geometry is checked at
100%, 125%, 150% and 200%. The physical desktop measured 3440×1440, 96 DPI,
scale 1.0; higher-scale bitmap checks do not claim physical multi-monitor tests.
The CPU mesh adapter uses NumPy 2.5.3 and Pillow 12.3.0 with wxPython 4.3.1;
CAD preparation/tessellation/rendering stays outside the GUI process.
Mesh distance tolerance is 0.01 mm. Geometric validators remain authoritative.

The historical Phase 12.1 combined run had a native access violation in the
PDF corpus path. Its [failure output](history/phase-12.1-combined-source-crash.txt)
and original acceptance scope remain preserved. The final full source/wheel
runs and three repeated installed PDF gates did not reproduce it. Root cause
remains **UNKNOWN**; these results do not establish a known parser repair.
The two initial standalone QA attempts omitted display restoration in their
test adapter; corrected adapters passed. Original attempt receipts are retained
under history. No failed attempt is relabeled as successful.

The closeout also found pre-existing Phase 4 input/golden drift from the
committed Phase 6 symbol adaptation. [Five symbol checks](phase-12-symbol-revalidation-results.xml)
and both full regressions validate the current fixture. The original accepted
symbol is retained [here](history/phase-4-original-0402.kicad_sym) with its original
SHA-256. Older receipts keep historical tests/wheels/golden identities; refreshed
input maps explicitly reference this current revalidation and previous/new hashes.

Final hash closeout archives affected active receipts, refreshes their input maps
in dependency order, verifies every active map and the CI-required Phase 5/6/8
maps, and records current wheel/sdist/test/evidence identities outside the map.
The manifest binds exact final uncommitted disk bytes; Git-blob verification
applies after committing. The user's specification edit is retained.

Reproduce with the project Python 3.12 environment (explicit `sys.path` is
needed for this isolated Windows interpreter):

```powershell
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','scripts/verify_phase11_review.py','-v','--tb=short']))"
.tools/python/python.exe -c "from hatchling.build import build_wheel,build_sdist;print(build_wheel('.tools/phase12-full/dist'));print(build_sdist('.tools/phase12-full/dist'))"
.tools/python/python.exe -m pip install --force-reinstall --no-deps .tools/phase12-full/dist/partsmith-0.1.0-py3-none-any.whl
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','scripts/verify_phase11_review.py','-v','--tb=short']))"
.tools/python/python.exe scripts/verify_pdf_stability.py --rounds 3 --desktop --output <new-attempt-directory>
.tools/python/python.exe scripts/verify_phase12_launch.py --source --transport <explicit-generated-offline-test-session> --output <source-launch-receipt>
.tools/python/python.exe scripts/verify_phase12_launch.py --transport <explicit-generated-offline-test-session> --output <wheel-launch-receipt>
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
git diff --check
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each active sha256-map receipt> --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-5-artifacts.json --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-6-artifacts.json --source disk
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-8-artifacts.json --source disk
```

Supported runtime: Windows 11 AMD64, Python 3.12.10, CadQuery 2.8.0, OCCT
7.9.3.1 and KiCad 10.0.6, with pinned PDF and GUI dependencies recorded in the
distribution receipt. AI tests use dummy credentials/transports; the offline
release workflow makes no provider calls. This gate does not claim remote CI,
Linux/macOS GUI acceptance or Phase 14's arbitrary-datasheet/package coverage.
