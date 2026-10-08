# Phase 14 online PCM candidate

**Phase 14 remains OPEN.** On 2026-10-08 the project owner removed offline
installation from scope. The supported production path is Python IPC with
KiCad-managed online requirements. There is no offline edition to maintain.

The candidate is **0.3.0**, Windows AMD64, KiCad 10.0.6 and Python 3.12.
The PCM ZIP contains PartSmith source, resources, `plugin.json`, pinned
`requirements.txt` and an installed-file inventory. It contains no Python
interpreter, DLLs, dependency wheels, Conda archives or OCR executable.
KiCad creates its per-plugin environment and downloads upstream binary wheels.
The CAD DLLs, including FreeImage/FreeType/OpenEXR, are supplied inside the
upstream `cadquery-ocp` wheel. The selected CAD tuple remains CadQuery 2.8.0,
OCP distribution 7.9.3.1.1 and OCCT 7.9.3.

This follows [KiCad's IPC plugin documentation](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
and its [10.0.6 requirements installer](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp).
The pinned loader requires binary wheels; source compilation is not a fallback.
Installation, updates and environment recreation require internet access.
Denied network or interrupted preparation must report a failure and allow retry.
Local extraction, deterministic generation and recorded component replay retain
their existing behavior after successful dependency preparation.

## Prerequisites and installation

Select a Python 3.12 interpreter in KiCad and enable the PCB Editor API.
The installed KiCad Python is 3.11.5; NumPy 2.5.3, SciPy 1.18.1 and
contourpy 1.4.0 require Python 3.12 or newer. The PartSmith runtime contract
currently supports 3.12 only. `runtime.min_version` alone does not enforce it.

OCR requires an external Tesseract 5 installation and `eng`, `deu`, `chi_sim`
language files. Use its standard Windows installation or configure
`PARTSMITH_TESSERACT` and `TESSDATA_PREFIX`. It is not bundled in the PCM ZIP.

Install the candidate through PCM **Install from File**, allow background
preparation to finish, then use **Open PartSmith**. PCM owns customer update and
removal. See [installation instructions](../pcm-installation.md).
Repository helpers retain transactional backups outside plugin discovery.

```powershell
.venv/Scripts/python.exe scripts/build_production_pcm.py --output dist/partsmith-0.3.0-pcm.zip
.venv/Scripts/python.exe scripts/verify_pcm.py dist/partsmith-0.3.0-pcm.zip --evidence online-payload-results.json
./install_production.bat -Archive C:/path/partsmith-0.3.0-pcm.zip
```

The production build now uses the same managed-Python builder as Phase 13.
It does not reconstruct the retired runtime lock or download a runtime for the
producer. The production batch is a prepared-checkout helper; it requires the
project Python environment. It is not a separate customer installer.
The old offline acceptance harness is retired.

## Engineering and evidence scope

The eight manufacturer-backed STD-010 variants and their frozen goldens remain:
0402, 0603, 0805, SOT-23, SOIC-8, TSSOP-16, QFN-16-3x3-0.5P and
QFN-24-4x4-0.5P. [Source facts](../../fixtures/production/packages.json) and
[golden identities](../../fixtures/production/golden.json) are unchanged.
Acceptance still requires CLASS A, native KiCad round trips, exact regeneration
and the complete per-variant negative corpus. Fixtures grant no user approval.
Startup remains deliberate, follows the launching KiCad host and excludes the
retired 0402 rendering button.

The [online candidate workflow](../../.github/workflows/phase14.yml) downloads
the pinned Windows binary dependencies, builds/verifies the source PCM ZIP,
runs installer/resource regressions and the complete eight-variant corpus.
These automated candidate checks are not proof of an actual clean-host PCM
preparation, toolbar launch or customer upgrade/removal. No workflow execution
or new clean-machine acceptance is claimed by changing the workflow file.

Current local verification passed 97 affected source/installer/license checks,
Ruff lint and formatting, tagged docstrings and identical independent ZIP builds.
The exact 0.3.0 payload reports READY in the existing KiCad-managed Python
3.12.10 environment. Its installed-resource self-test passes all eight variants
with CLASS A, native compatibility, exact bytes and 63 negative cases. See
[source results](phase-14-online-source-results.xml),
[payload verification](phase-14-online-payload.json),
[managed-runtime diagnostics](phase-14-online-managed-runtime.json) and
[exact-payload corpus](phase-14-online-corpus.json). This reused an existing
prepared environment: network preparation and actual GUI/PCM lifecycle were not
executed for this candidate. The installed current-user plugin was not changed.

[Current artifact and validation identities](phase-14-artifacts.json) distinguish
this candidate from historical executable acceptance. The previous full report,
manifest and installer/workflow bytes are retained in
[the policy-change archive](history/phase-14-before-online-only-2026-10-08/docs/gates/phase-14.md).
Original 0.2.0/0.2.1 package identities, local installation/corpus/engine/GUI
receipts and historical test results retain their original execution scope.
They do not establish acceptance of the new 0.3.0 online candidate.

## Remaining production requirements

- Retained clean Windows 11 online PCM install/preparation, real toolbar launch,
  diagnostics, upgrade/removal/recreation and denied-network retry evidence.
- A validated dependency/license manifest distinguishing PartSmith-shipped
  files, upstream wheels downloaded by KiCad, and external Python/OCR tools.
  Review integration compatibility and retained notices for the shipped files.

The forensic CAD audit verified the versions and repaired bytes of 24 additional
DLLs, including FreeImage 3.18.0, FreeType 2.12.1 and OpenEXR 3.4.12. Its
[ledger](../../resources/licensing/cad-native/vendors.json), original notices,
source identities and [proof](phase-14-license-audit/cad-verification.json)
remain research evidence. The broader executable-bundle source audit is still
incomplete and is recorded as such in [its audit](phase-14-native-license-audit.json).
The retired bundle is not being approved for redistribution or maintained as an
offline release. Online delivery does not by itself settle license compliance.

Hash refresh records the current policy and candidate bytes without broadening
historical evidence or closing this gate:

```powershell
.venv/Scripts/python.exe scripts/close_integration_gate.py --phase 14 --reason "Owner removed offline installation; managed online PCM candidate"
```
