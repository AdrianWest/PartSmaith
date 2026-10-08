# Phase 14 online PCM candidate

**Phase 14 remains OPEN.** Candidate **0.3.2** targets Windows AMD64,
KiCad 10.0.6 and KiCad's bundled Python **3.11** (locally verified as 3.11.5).
Specification v0.9.8 removes the external Python 3.12 customer prerequisite.
The owner also removed offline installation from scope on 2026-10-08.

The PCM ZIP contains PartSmith source/resources, Python IPC registration,
70 pinned requirements and an installed-file inventory. It contains no Python
interpreter, native DLLs, dependency wheels, Conda archives or OCR executable.
KiCad downloads upstream binary wheels into a private per-plugin environment.
Installation, updates and environment recreation require internet access;
no offline edition or wheel mirror is maintained. Normal local processing and
recorded component replay remain available after preparation.

## Runtime migration and installation

NumPy changes from 2.5.3 to **2.4.6**, SciPy from 1.18.1 to **1.17.1**, and
contourpy from 1.4.0 to **1.3.3**. Python 3.11 also needs pinned
backports.tarfile 1.2.0, importlib_metadata 9.0.1 and zipp 4.1.1. CadQuery 2.8.0,
OCP distribution 7.9.3.1.1 and OCCT 7.9.3 remain the selected tuple.
The new Windows cp311 CAD lock verifies upstream wheel hashes and installed
members/notices. [Wheel identity proof](phase-14-python311-cad-lock.json)
records its sources. The original 3.12 lock remains byte-for-byte unchanged.
Runtime snapshots, replay resources and installation plans select the matching
lock and constraints; Python baseline changes remain reproducibility inputs.

This uses [KiCad's documented managed Python IPC environment](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
and the [10.0.6 binary-only requirements installer](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp).
The action enforces Python 3.11 itself; `runtime.min_version` is informational
in the pinned loader. Dependencies are never installed into KiCad's base Python.

Install `dist/partsmith-0.3.2-pcm.zip` through PCM **Install from File**.
Select bundled Python in KiCad's Python/IPC preferences and enable the PCB
Editor API. An existing external 3.12 override must be replaced. Recreate any
3.12 per-plugin environment using **Recreate Plugin Environment** after the
switch; changing the interpreter preference alone does not migrate a cache.
OCR still requires external Tesseract 5 plus `eng`, `deu` and `chi_sim` data.
See [installation instructions](../pcm-installation.md).

The prepared-checkout batch helpers discover bundled Python beside the
verified KiCad CLI, select it for Python IPC, and retain the original preference
bytes alongside the payload/registry backup. This is a global KiCad IPC
preference; other settings and plugin files are preserved. Failed publication
restores the previous settings and payload. Dry runs change no installation
files or preferences. The helpers do not delete environment caches or durable
sessions. The producer helper may run in its existing Python 3.12 environment;
customers use PCM and need no checkout or external Python.

```powershell
.venv/Scripts/python.exe scripts/build_production_pcm.py --output dist/partsmith-0.3.2-pcm.zip
./install_production.bat -Archive C:/path/partsmith-0.3.2-pcm.zip -DryRun
```

## Manual prerequisite startup checks

Both IPC and standalone desktop startup now check Tesseract major version 5
and availability of `eng`, `deu` and `chi_sim` before setup or session recovery.
The check honors the same executable and language-directory selection as OCR.
A missing, unsupported or unresponsive engine shows the Windows installer link;
missing languages each show their official traineddata link. The modal dialog
blocks startup until the user closes PartSmith and repairs the listed items.
It closes automatically if the launching KiCad host exits. Links open only on
click; no download or installer runs at startup.

This manual checklist excludes KiCad and every Python dependency installed by
requirements. Existing engineering readiness remains separate. Diagnostic and
self-test modes report safe issue codes and links without opening a GUI.

Current evidence includes [source and installer tests](phase-14-external-source-results.xml),
[native dialog/startup tests](phase-14-external-gui-results.xml),
[rendered language dialog](phase-14-external-dialog.png),
[extraction regressions](phase-14-external-extraction-results.xml),
[payload parity](phase-14-external-payload.json),
[healthy readiness](phase-14-external-readiness.json),
[GUI smoke](phase-14-external-gui-smoke.json),
[missing engine](phase-14-external-missing-engine.json),
[missing languages](phase-14-external-missing-languages.json),
[exact-payload corpus](phase-14-external-corpus.json), and
[code/documentation checks](phase-14-external-checks.json).
The source and native startup checks run under actual KiCad Python 3.11.5;
the extraction suite and artifact producer use the retained Python 3.12 venv.
Real missing-executable and empty-language-directory launches show the native
blocking popup without creating setup/recovery state. The installed Windows
`tesseract v5.5.0.20241111` banner is accepted alongside upstream numeric banners.
The [initial investigation](history/phase-14-external-check-investigation-2026-10-08/README.md)
preserves the corrected banner failure and an installer-test concurrency error.

## Verification scope

The eight manufacturer-backed variants retain their original frozen golden
bytes: 0402, 0603, 0805, SOT-23, SOIC-8, TSSOP-16, QFN-16-3x3-0.5P and
QFN-24-4x4-0.5P. They pass CLASS A measurement, native KiCad compatibility,
exact regeneration and all 63 negative cases under the actual KiCad Python
3.11.5 in a separately prepared test venv. The exact 0.3.2 PCM payload also
reports READY and passes a local GUI smoke launch. Startup remains deliberate,
follows the launching KiCad host and excludes the retired 0402 prototype button.
The smoke launch does not prove a real IPC toolbar launch or host lifecycle.

The earlier 0.3.1 migration evidence includes [source/runtime checks](phase-14-python311-source-results.xml),
[producer checks](phase-14-python311-producer-results.xml),
[producer runtime regressions](phase-14-python311-producer-runtime-results.xml),
[installer checks](phase-14-python311-installer-results.xml),
[payload parity](phase-14-python311-payload.json),
[readiness](phase-14-python311-readiness.json),
[GUI smoke](phase-14-python311-gui-smoke.json), and
[exact-payload corpus](phase-14-python311-corpus.json).
The [current manifest](phase-14-artifacts.json) binds finalized artifacts and
records current check counts. Two independent 0.3.2 ZIP builds have identical bytes.
The current-user installed package and interpreter preference were not migrated.

The [candidate workflow](../../.github/workflows/phase14.yml) creates a venv
using KiCad's bundled interpreter and downloads the 3.11 binary closure.
It provisions manual OCR prerequisites for its candidate test environment too.
The general CI retains its historical 3.12 producer baseline. No remote workflow
execution or clean-machine PCM acceptance is claimed by editing these files.
Exploratory failures are retained in the [migration investigation archive](history/phase-14-python311-pytest-capture/README.md).

The [pre-migration report](history/phase-14-before-python311-2026-10-08/docs/gates/phase-14.md)
and manifest preserve 0.3.0/Python 3.12 evidence. Historical Phase 13 and 0.2.x
executable receipts retain their exact original scope. They do not establish
acceptance of the current candidate. The
[pre-startup-check report and manifest](history/phase-14-before-external-check-2026-10-08/docs/gates/phase-14.md)
preserve the exact 0.3.1 scope. No offline executable release is maintained.

## Remaining production requirements

- Clean Windows online PCM preparation, real toolbar launch, lifecycle,
  upgrade/removal/recreation and denied-network/interruption retry evidence.
- Dependency/license manifest and integration review for shipped resources,
  KiCad-downloaded wheels and external KiCad/Python/OCR prerequisites.

The earlier native-library forensic audit remains research evidence. Its
[ledger](../../resources/licensing/cad-native/vendors.json) and
[verification](phase-14-license-audit/cad-verification.json) retain their scope;
the broader retired executable-bundle source audit is incomplete. Wheel hash
verification and online delivery do not by themselves complete license review.

Hash refresh verifies current bytes while preserving historical execution
scope; it does not close the production gate.
