# Phase 13.2 PCM packaging and runtime checks — 2026-10-06

Status: **IMPLEMENTATION_AND_SCOPED_CHECKS_RECORDED**. This report does not
claim milestone 13.2 or the Phase 13 gate has passed. Actual PCM lifecycle,
live IPC/native target acceptance and final hash closeout are separate evidence.

The production artifact is `dist/partsmith-0.1.4-pcm.zip`, package identifier
`com.boardforgetools.partsmith`, version `0.1.4`, SHA-256
`862cff04151d22c87529f63102fa000f0afc8a8d0b2fff4bb39cd3d2f8aa4cf9`.
It contains 152 regular stored ZIP members, has 6,767,558 downloaded bytes and
6,744,598 extracted bytes. Timestamps, permissions, member ordering and JSON
serialization are fixed. Earlier local lifecycle versions remain frozen;
their receipts retain their exact identities and do not substitute for 0.1.4.

## Payload and registration

Root `metadata.json` advertises development status, GPL-3.0-only, Windows
AMD64 and KiCad minimum/maximum 10.0.6. Its one version declares PCM runtime
`ipc` and omits download fields. `plugins/plugin.json` is the separate IPC
registration: stable identifier, Python runtime, PCB-only `open` action and
relative `entry.py`. `min_version` is descriptive in KiCad 10.0.6; the action
enforces actual Python 3.12 before importing CAD. There is no machine-specific
launcher path in the ZIP and this managed-runtime mechanism needs no second
PartSmith launcher configuration.

Version 0.1.3's real action launch exposed an empty toolbar button: the pinned
loader supplies no icon fallback. Version 0.1.4 adds an owned PS vector source
and fixed 24/48-pixel PNG derivatives, declared for both light and dark toolbar
themes. The API schema accepts PNG paths; the SVG is retained as owned source.
The visible icon, dimensions and exact resource parity are tested. Earlier
iconless fixture bytes and failure/context evidence remain unchanged. IPC
actions use the toolbar; the 10.0.6 External Plugins menu lists legacy actions.

The source tree is delivered directly under `plugins/partsmith/`. The retained
`pyproject.toml` force-include map supplies the resource declaration, including
all IR/PDL/release/integration schemas, SQL migrations, banners, viewer fixtures,
runtime lock/constraints, PDL data and legacy development launcher resources.
The inventory hashes every owned payload file except its own document; root
metadata records the total archive extraction size. No database, credential,
journal, generated project library, PartSmith distribution or runtime wheel is
included in disposable package content.

The bundled API v1 and PCM v2 schemas are the exact installed Windows KiCad
10.0.6 schema bytes recorded by preparatory discovery. Their hashes are checked
before offline schema validation. These files retain their original CRLF bytes
through a scoped binary Git attribute. Validation adds closed PartSmith metadata
and registration checks because upstream schemas permit some extra properties.
Pre-extraction checks reject aliases, path traversal, invalid Windows names,
nonregular/encrypted/compressed members and cumulative resource-limit overflow.
Installed resource checks reject drift, omissions, undeclared files and escapes.

## Runtime and live action boundary

The entry launches through a fixed Python `-I` argument vector and imports only
the installed package root. It removes `KICAD_API_SOCKET` and `KICAD_API_TOKEN`
from the environment before engineering checks spawn native processes. Safe
diagnostics contain readiness codes, dependency versions, resource identities
and reviewed CAD/native runtime identities, without endpoint/token values or
provider exception messages. Operational launch diagnostics are written outside
the package/environment in `%LOCALAPPDATA%/PartSmith/runtime/last-launch.json`.

After readiness, the user deliberately selects the board open in the launching
PCB Editor. The selected path and transient credentials bind the exact IPC
session. A separate read-only inspector refreshes actual board/footprint data,
records safe context-loss/disconnection outcomes, and requires a new launch
after invalidation. Closing the inspector or its parent clears the session.
This action supplies inspection; it grants no component-library publication
authority.

`requirements-pcm.txt` pins the full CAD/schema/PDF/GUI dependency closure plus
official `kicad-python==0.8.0`, `protobuf==5.29.6`, `pynng==0.9.0` and
`sniffio==1.3.1`. Existing reviewed `cffi==2.0.0` and `pycparser==2.23` are
preserved. Binary dependency resolution exposed `propcache==0.5.4`, which is
also pinned. Third-party wheels supply the managed runtime; PartSmith itself
is never built or installed as a wheel in these checks.

Initial Python environment preparation normally downloads pip/dependencies in
KiCad's background loader. A ZIP alone does not establish offline preparation.
The recorded owned-environment helper used an exact local binary supply and
per-environment `pip.ini` with `no-index` and `find-links`; pip's isolated
requirement installation still reads that site configuration. It exercised pip
upgrade, denied-index/missing-binary failure, terminated preparation and retry,
fresh recreation and `pip check`. This is executable loader-sequence evidence;
real PCM preparation/recovery remains separately recorded by the root gate.

## Replacement commands and scoped evidence

Active CI no longer calls `pip install -e .`, `pip wheel .`, PartSmith wheel
reinstallation, installed-wheel resource assertions or `dist/*.whl` uploads.
Source tests use the declared `src` path. Engineering assertions remain in the
source and PCM checks. The PDF stability harness supports a verified PCM ZIP or
declared source tree; its subprocesses verify exact package/resource bytes.
The desktop viewer harness checks source/PCM resources without a site-packages
or installed-wheel assumption.

Replacement commands:

```text
python -m pytest
python scripts/build_pcm.py --output dist/partsmith-pcm.zip
python scripts/verify_pcm.py dist/partsmith-pcm.zip --evidence pcm-payload-results.json
python scripts/verify_pdf_stability.py --archive dist/partsmith-pcm.zip --rounds 3 --output pdf-stability-results
python -m partsmith version
python -m partsmith doctor --json
```

Evidence files:

- `phase13.2-packaging-014-test-results-2026-10-06.xml`: 0.1.4 PCM/inspection
  tests, including visible icon and exact SVG/PNG resource checks.
- `phase13.2-packaging-014-payload-2026-10-06.json`: exact final source/resource
  parity and isolated offline imports from an unrelated working directory.
- `phase13.2-packaging-014-runtime-2026-10-06.json`: extracted 0.1.4 reports READY
  under CPython 3.12.10 and rejects installed embedded 3.11 with
  `PYTHON_312_REQUIRED`; this is not an actual PCM-launch receipt.
- `phase13.2-packaging-offline-2026-10-06.json`: exact third-party binary supply
  inventory and owned loader-sequence preparation/recovery results.
- `phase13.2-packaging-pdf-stability-2026-10-06/manifest.json`: preserves the
  completed 0.1.3 three-round PDF checks with stdout/stderr/JUnit identities.
  Final 0.1.4 checks are recorded separately when complete.

Repository fixtures are schema-tested offline and served locally for the gate.
`repository.json` points to hash-identified `packages.json`; package download
URL/size/hash fields are added after each ZIP is finalized. A hosted release or
official repository listing is not claimed. Persistent project/library and
component state remain outside the PCM code/environment lifecycle.
