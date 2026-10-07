# Phase 13.2 source IPC and inspector evidence

Recorded 2026-10-06. This report covers source tests, installed official binding
geometry and exact frozen PCM payload/schema parity. It does not declare the
milestone complete or substitute injected clients for a running PCB Editor.

The [machine-readable record](phase-13.2-ipc-source-evidence-2026-10-06.json)
contains exact file hashes, versions, cases, limits, unit examples and the live
acceptance handoff. The [JUnit result](phase-13.2-ipc-source-results-2026-10-06.xml)
records **110 passed**, with no failures, errors or skips: 58 IPC adapter cases,
24 controller/window-handler cases and 28 PCM cases, in 9.74 seconds.

```text
.venv/Scripts/python.exe -m pytest tests/test_integration_ipc.py tests/test_ipc_inspection.py tests/test_pcm.py -q --junitxml=docs/gates/phase-13.2-ipc-source-results-2026-10-06.xml
```

The frozen `dist/partsmith-0.1.3-pcm.zip` has SHA-256
`966e046d8b3b1a6aafc3f410ee942aaf9ab712b5544358551ad3c1fe131ca1ef`.
All four IPC/units/controller/wx source modules match its installed-layout
members exactly. Its integration schema matches the current source schema;
the API and PCM schema bytes match the installed KiCad 10.0.6 schemas. Package
construction and lifecycle evidence are recorded separately by the root and
packaging agents. The archive was read without modification.

The adapter pins native KiCad 10.0.6, official `kicad-python` 0.8.0 and API build
`10.0.6-0-gcaf7377e9c`. The [released binding metadata](https://pypi.org/pypi/kicad-python/0.8.0/json)
and [tagged source](https://gitlab.com/kicad/code/kicad-python/-/tree/0.8.0)
govern its API. It supports version discovery, explicit PCB-document discovery
and actual footprint inspection. It requires an explicit endpoint, nonempty
token and exactly one matching expected board, repeats context/version checks,
and invalidates a failed session. Required read timeouts remain bounded at
15 seconds under resource policy 1.0. Schematic IPC, headless IPC, dirty-state
queries, editor close/reopen and native mutations are not advertised.

The [tagged geometry wrapper](https://gitlab.com/kicad/code/kicad-python/-/blob/0.8.0/kipy/geometry.py)
represents PCB distances as integer nanometres and angles as floating degrees.
The exact-decimal coordinate adapter uses `x_nm = x_mm * 1,000,000` and
`y_nm = -y_mm * 1,000,000`; angle sign stays unchanged. Local official-wrapper
cardinal rotations and exact source fixtures confirm the mapping. Tests reject
sub-nanometre distances, native overflow, nonfinite values, engineering floats
and unsupported angle precision. Model placement and bottom-side transforms
remain separate, explicit conventions.

The controller performs no read during construction. Each deliberate Refresh
re-reads the verified board, reports actual immutable footprint data or a closed
failure code/reason, and clears stale rows on failure. Failed sessions cannot
retry or reconnect through the inspector. Closing the inspector or its owning
main window closes the session; late read/UI delivery is discarded. Diagnostic
write failure keeps the actual read outcome and emits a separate fixed warning.
Tests invoke real wx handler functions against Python doubles without opening
a window. These tests do not prove visual behavior on the live desktop.

Live acceptance uses the installed inspector's **Refresh PCB inspection**
button and safe `ipc_inspection` record in
`LOCALAPPDATA/PartSmith/runtime/last-launch.json`. A changed board can produce
`WRONG_BOARD` or `CONTEXT_CHANGED`; restart/loss can produce `TOKEN_MISMATCH`,
`DISCONNECTED` or bounded `TIMEOUT`, according to the old pipe's state. Capture
the failed record while the action remains open, since its later deliberate
close records `CLOSED`. These are expected observable outcomes, not claimed
live results in this source report. Root-owned evidence must show the actual
selected board, native session and negative operations.

The evidence builder is `.tools/phase13-discovery/build_ipc_evidence.py`. It
reads only explicitly selected source/schema/ZIP/JUnit bytes and public package
versions. It does not access a launch endpoint/token or enumerate environment
values. Ruff validation covers the new helper and the implementation modules.
