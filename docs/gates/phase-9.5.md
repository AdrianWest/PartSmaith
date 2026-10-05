# Phase 9.5 — wxPython setup and processing GUI

**Gate: PASS**, verified 2026-10-04 against the Phase 9.5 addition to
specification v0.9.6.
Prerequisite: [Phase 9 PASS](phase-9.md). Local Windows AMD64 runtime:
Python 3.12.10, wxPython 4.3.1, keyring 25.7.0, native KiCad 10.0.6.
Final status, wheel identity, input hashes, and check totals are recorded in
[the artifact manifest](phase-9.5-artifacts.json).

| Requirement | Implementation and evidence |
| --- | --- |
| Standalone and KiCad launch | `scripts/partsmith_gui.py`, `python -m partsmith.gui`, `partsmith-gui`, and the installed launch-only action plugin. The real PCB Editor's Tools → External Plugins → PartSmith Setup entry was invoked and opened the GUI. The standalone script was launched with the Windows temporary directory as its working directory. The KiCad plugin uses its installed plugin directory as the child's working directory and strips KiCad's embedded Python paths. |
| Banner at the top | Original `resources/PartSmail-Banner.png` is packaged in the wheel, starts at x/y zero, spans the full client width, and scales its height proportionally. Source and wheel tests verify dimensions and resizing; screenshots record visual inspection. A scrollable body keeps controls accessible if the full-width banner leaves less vertical space. |
| Secure API-key configuration | Blank, masked wx dialog with OK/Cancel; native OS credential backend selected explicitly, with no plaintext fallback. Tests cover repeated opening, successful replacement, blank rejection, cancellation, safe storage failures, provider isolation, and no credential echo. A dummy key in a unique test service survives a separate Python process restart; the test removes that service afterwards without touching user credentials. |
| Datasheet selection | Native local-PDF chooser and read-only selected path. Dialog open/cancel was inspected in the running GUI; wx tests exercise selection and preserved selection after cancellation. Input preflight rejects missing/unreadable files, wrong extensions, and missing PDF headers. |
| Required part number | Full manufacturer order number, including package suffixes, is mandatory and passed unchanged to the worker. Offline requests for QFN and TSSOP variants of one synthetic multi-package datasheet remain distinct. Actual datasheet package mapping remains Phase 10. |
| Bottom log box | Read-only multiline scrolling wx text control. A worker queue is drained by a GUI-thread timer. Tests observe logs during work and redact a dummy stored key; errors use fixed, non-secret messages. No GUI log file or component artifact is created. |
| Start, Cancel, window close | One non-daemon worker at a time; job inputs and key configuration are disabled while running. Duplicate jobs are blocked. Cancel signals the worker; window close waits for cooperative cleanup before destroying the frame. Tests cover live progress, cancellation, success/failure/unavailable status, restart after cancellation, and cleanup before close. No processing subprocess exists in this phase. |
| Processing boundary | Immutable datasheet/part-number request, log callback, cancellation event, and explicit terminal status. The production worker performs preflight and reports Phase 10/11 unavailable without a false build success. Offline workers exercise the future service boundary without a network call. |

Screenshots:

- [Standalone GUI from an external working directory](phase-9.5-standalone-launch.png)
- [GUI launched by the native KiCad menu](phase-9.5-kicad-launch.png)

Test evidence:

- Full final source suite: **490 passed**, no failures/errors/skips.
- Source service and real-wx integration checks: **26 passed**.
- Installed-wheel service and real-wx integration checks: **26 passed**.
- Repository lint, formatting, dependency consistency, packaged banner and
  launch resources: PASS.
- [Full source regression suite](phase-9.5-source-results.xml)
- [Source service and real-wx integration checks](phase-9.5-gui-results.xml)
- [Installed-wheel service and real-wx checks](phase-9.5-wheel-gui-results.xml)

The wx tests are separate from the ordinary suite so the headless core does not
require desktop dependencies. They use a real wx event loop and controls, fake
workers/storage for error cases, and the native Windows store only for the
unique dummy-service restart check. No live provider key or AI call was used.
Optional GUI dependency pins are in `requirements-gui-windows.txt`; existing
deterministic runtime constraints remain unchanged. No Linux/macOS GUI or
remote CI result is claimed.

The user-level launch-only plugin is installed in KiCad 10's configuration
directory. Its `launcher.json` contains only the PartSmith interpreter path.
The bundled KiCad Python interpreter cannot register an action plugin when run
outside the PCB Editor host (`PgmOrNull()` assertion); native verification
therefore used the actual PCB Editor menu rather than treating a standalone
`import pcbnew` as host integration evidence.

Shared documentation and `pyproject.toml` changes affect older exact-byte
manifests without changing any deterministic generator/runtime inputs. Previous
manifests are retained under `docs/gates/history/*-before-phase-9.5-2026-10-04.json`.
Current manifests record this revalidation explicitly. The Phase 8 manifest
also had two pre-existing report-byte mismatches (`phase-8.md` and
`phase-8-revalidation.md`); their current report bytes are recorded without
rewriting those reports or claiming a new historical run. Core regressions
retain the deterministic/offline build checks in the full source suite.

Reproduce using the project Python 3.12 environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gui-windows.txt
.\.venv\Scripts\python.exe -m pip install -e ".[gui]" --no-deps
.\.venv\Scripts\python.exe -m pytest --junitxml=docs/gates/phase-9.5-source-results.xml
.\.venv\Scripts\python.exe -m pytest tests/test_gui.py scripts/verify_gui.py --junitxml=docs/gates/phase-9.5-gui-results.xml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir .tools/phase95/dist
.\.venv\Scripts\python.exe -m pip install --upgrade --no-deps --target .tools/phase95/wheel-site .tools/phase95/dist/partsmith-0.1.0-py3-none-any.whl
$env:PYTHONPATH = (Resolve-Path .tools/phase95/wheel-site).Path
.\.venv\Scripts\python.exe -m pytest tests/test_gui.py scripts/verify_gui.py --junitxml=docs/gates/phase-9.5-wheel-gui-results.xml
```

The wheel checks assert the import location and compare the packaged banner
bytes with the source image. Both editable and installed-wheel installers are
exercised. This gate covers setup, input routing, and the worker boundary;
PDF extraction, package resolution from manufacturer ordering tables, external
AI submission, and component generation from a PDF require Phases 10/11.
