# PartSmith PCM installation

PartSmith's customer plugin artifact is a KiCad Plugin and Content Manager
(PCM) ZIP. The customer target is Windows AMD64, KiCad 10.0.6 and its bundled
CPython 3.11 (verified locally as 3.11.5). The [full Phase 13 gate](gates/phase-13.md)
passed on its historical Python 3.12 target; its receipts retain that scope. Its final package is `dist/partsmith-0.1.9-pcm.zip`; actual PCM lifecycle,
prepared runtime, native editors and official PCB IPC have separate supervised
evidence. There is no public production release. Clean-machine online production
acceptance remains Phase 14.

## Supported online installation

Candidate **0.3.2** uses Python IPC and KiCad's private managed environment.
PartSmith supplies source, resources and pinned `requirements.txt`; KiCad
installs the upstream binary wheels, including the CAD DLLs. Installation,
updates and **Recreate Plugin Environment** require internet access. There is
no supported offline installer, dependency mirror or optional offline edition.
Normal local processing and recorded component replay remain available after
successful environment preparation.

Install `dist/partsmith-0.3.2-pcm.zip` using PCM **Install from File**. Use
KiCad's bundled Python 3.11. No external Python installation is needed.
Compatible pins are NumPy 2.4.6, SciPy 1.17.1 and contourpy 1.3.3, with three
3.11 backports. The CAD tuple remains unchanged. Tesseract 5 and
`eng`, `deu`, `chi_sim` language data are external OCR prerequisites; the existing
adapter discovers the standard Windows installation, PATH or
`PARTSMITH_TESSERACT`, with `TESSDATA_PREFIX` selecting language data. The Python
package manager does not provision that standalone OCR executable.

At startup, PartSmith checks Tesseract 5 and the three required OCR languages
before opening setup or recovering a session. If something is missing or
unusable, an error dialog lists only the affected manual prerequisites, with
clickable links to the [Windows Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
or the individual official language files. Install the listed items and restart
PartSmith. The dialog also closes if the launching KiCad process exits.
KiCad installation and packages provisioned by `requirements.txt` are excluded
from this manual-install checklist. Existing engineering readiness checks still
validate the managed runtime separately. Startup does not open download pages
or run installers automatically.

For this prepared repository, `install_partsmith.bat` builds and installs the
current managed package. `install_production.bat` installs the prebuilt online
candidate using the repository's Python environment; `-Archive`, `-DryRun` and
`-Uninstall` are supported. Customer installation and removal use PCM and do not
require this checkout or these helpers.

The [Phase 14 report](gates/phase-14.md) records current checks and remaining
online acceptance work. The 0.2.x bundled executable experiment and its receipts
are retained as historical evidence, with no ongoing offline maintenance.
The production gate remains open; this policy change does not grant a PASS.

## Install and prepare

1. In KiCad's Python/IPC preferences, select bundled Python 3.11, for example
   `C:/Program Files/KiCad/10.0/bin/python.exe`. This is KiCad's default on
   Windows; replace any old external 3.12 override. Enable the PCB Editor API.
   PartSmith runs in a separate managed venv, outside the legacy ActionPlugin host.
2. Open PCM from the KiCad project manager. Choose **Install from File** and
   select the released PartSmith PCM ZIP. For a configured repository, select
   the package/version, inspect Pending actions and choose **Apply Pending
   Changes**. The tested local-file install applies immediately; it does not
   use the same Pending queue as configured repository actions.
3. KiCad prepares the plugin's private Python environment in the background.
   First preparation normally downloads pip and the pinned binary dependencies.
   Wait for preparation to finish, then reload/restart the PCB Editor as needed
   for registration. After switching interpreters, recreate any existing 3.12
   plugin cache: right-click **Open PartSmith** under
   **Preferences → PCB Editor → Plugins** and select **Recreate Plugin Environment**.
   If the failed action is absent, restart KiCad after installing the package
   and correcting the interpreter preference. Recreation requires internet.
   A successful pip job alone does not establish engineering
   readiness: the action verifies the actual Python, CAD/native bytes, dependency
   pins, schemas and full installed resource inventory again.
4. With the intended board open, use the **Open PartSmith** IPC toolbar action
   in the PCB Editor. The pinned 10.0.6 **Tools → External Plugins** menu is for
   legacy ActionPlugins; it does not list IPC actions. Version **0.1.11** opens
   the setup window directly, without a board chooser or automatic PCB read.
   To inspect the PCB, press **Inspect PCB...** and deliberately select the
   board already open in the launching editor. PartSmith verifies that instance
   and exact board before opening the read-only inspector. **Refresh** reads it;
   session loss or changed context disables further inspection until a new launch.

The startup fix is packaged separately as `dist/partsmith-0.1.10-pcm.zip`.
The frozen 0.1.9 Phase 13 acceptance archive and evidence retain their scope.
Version 0.1.11 also closes PartSmith when the launching KiCad process exits,
retaining unfinished work in recovery without a save/discard prompt. Closing
editors while the project manager remains open permits library publication.
The setup window no longer exposes the 0402 rendering prototype button.

## Local repository batch installer

For this prepared development checkout, close KiCad and PartSmith, then
double-click [`install_partsmith.bat`](../install_partsmith.bat). It uses the
repository's producer `.venv` (Python 3.11 or 3.12), builds and verifies the PCM
ZIP, and installs it into the configured KiCad 10 third-party directory. It
selects the bundled Python beside the verified KiCad 10.0.6 CLI for Python IPC.
This preference applies to every Python IPC plugin. The exact old settings are
retained in the install backup; other preferences remain intact, and publication
failure restores the original settings. For custom locations, set
`PARTSMITH_KICAD_CLI` to KiCad's `kicad-cli.exe`. Reopen KiCad afterward and
allow preparation to finish. Recreate any old 3.12 plugin cache as described above.

The installer updates PartSmith's local PCM registration, preserves other
packages and unrelated settings, and retains the previous plugin, icon and registry in
`PartSmith-install-backups` beside the third-party root. Staging and backups
stay outside KiCad's recursive plugin discovery. A failed publication restores
the prior payload. `install_partsmith.bat --no-pause --dry-run` checks the target
without changing installation files. This repository helper does not replace
Phase 14 clean-machine online installation acceptance.

The final 0.1.9 package uses the project owner's `resources/PartSmith_Logo_64x64.png`
unchanged for the package manager listing. The PCM ZIP includes it as
`resources/icon.png`. Configured-repository fixtures provide the same logo in
their separate `resources.zip` at `com.boardforgetools.partsmith/icon.png`,
with its hash and URL in `repository.json`, so the listing can show it before
installation. These locations follow [KiCad's addon packaging](https://dev-docs.kicad.org/en/addons/)
and the [pinned 10.0.6 resource loader](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/kicad/pcm/pcm.cpp).

Version 0.1.5 added the project owner's PartSmith anvil toolbar artwork, copied
unchanged
from `resources/PartSmith_Anvil_Icon_24x24.png` and its 64x64 variant. Both light
and dark toolbar themes use these packaged PNGs. Version 0.1.4 retains the
earlier PS placeholder in its frozen local acceptance fixture.
The earlier 0.1.3 local fixture exposed an empty clickable toolbar tool because
the pinned KiCad loader does not provide an icon fallback; its recorded launch
and context evidence retain that exact scope.

Customers do not install a PartSmith wheel, clone its repository or run pip.
PCM owns the plugin files and KiCad owns the managed Python environment. A
machine-specific interpreter path is never embedded in the portable ZIP.
The managed-runtime mechanism uses IPC `plugin.json`; the old manually copied
ActionPlugin and `launcher.json` are development/legacy launch-only data.

## Project libraries

Open **Project Libraries** in PartSmith after the KiCad action verifies the
selected board. Use **Add Approved Session** to select exact approved releases.
**Create Managed Project Copy** registers a complete copy on fixed local NTFS
with project-local libraries. The original project remains the registration
source.

Use **Plan / Dry Run**, **Stage / Check** and **Inspect Installation** to review
the complete target/base, packed library content, semantic comparisons and
final hashes. **Authorize Exact Installation** records a separate deliberate
installation decision with a fresh OS principal and reason. Component input
approval and release approval remain separate actions. Changed sources,
project files, checks or target/base require a new plan and exact review.

Before **Publish / Update**, save and close PCB/schematic editors and native
CLI operations, then confirm exclusive use of the managed copy. Cancel
preserves unsaved editor work. Reopen the managed project after publication to
refresh libraries. **Plan Rollback** requires fresh staging, checks and exact
authorization against the current base. **Reconcile Interrupted Publication**
resolves the actual complete old/new generation and durable receipt.

Saved sessions contain versioned installation references without live
authority. Loading them requires fresh source selection, plan and review.
Disconnecting or switching the selected board invalidates execution. Native
schematic/PCB use and PCB inspection are verified; library installation does
not write or place PCB instances automatically.

## Historical offline supply

The prior Python 3.12 wheel supply, site `pip.ini` policy and offline recovery
experiments are retired. Their original instructions remain in the
[pre-migration archive](gates/history/phase-14-before-python311-2026-10-08/docs/pcm-installation.md).
Use online KiCad preparation and recreation for the current package.

Safe action diagnostics are in
`%LOCALAPPDATA%/PartSmith/runtime/last-launch.json`. They contain stable readiness
and inspection codes and exact resource/runtime identities. IPC endpoints,
tokens, credential values and raw provider error messages are excluded.
`PYTHON_311_REQUIRED`, dependency/resource errors and IPC context-loss codes
require correcting the indicated boundary before retrying.

## Update, uninstall and durable data

Use PCM for plugin updates and removal. Configured-repository operations use
Pending/Apply; verify the resulting installed version and reload the action.
Close the PartSmith/inspector windows before a normal update or removal.
Active-action and failed-preparation lifecycle cases are separately exercised
by the implementation gate.

Databases, OS credentials, journals, saved component sessions, immutable source
bundles and generated project libraries live outside disposable PCM files and
managed environment caches. Plugin code updates/removal/reinstallation preserve
that durable data and do not publish or roll back a component library. An
invalidated inspector retains no live authority and requires a deliberate new
launch rather than reconnecting automatically.

## Contributor build and verification

The active Phase 13 workflow reads `src` directly and builds PCM without a
PartSmith build backend or installation. Third-party dependency wheels remain
permitted. The historical resource declaration in `pyproject.toml` is consumed
by the PCM builder; all engineering resource assertions are retained.

| Retired active entry | Replacement |
| --- | --- |
| `python -m pip install -e . --no-deps` | Declared source path / pytest `pythonpath = ["src"]` |
| `python -m pip wheel . --no-deps --wheel-dir dist` and PartSmith wheel reinstall | `python scripts/build_pcm.py --output dist/partsmith-pcm.zip` |
| Installed-wheel resource assertions and wheel regression run | `python scripts/verify_pcm.py dist/partsmith-pcm.zip --evidence pcm-payload-results.json` and `python scripts/verify_pcm_acceptance.py dist/partsmith-pcm.zip --output pcm-acceptance-results --desktop` |
| Installed-wheel PDF stability harness | `python scripts/verify_pdf_stability.py --archive dist/partsmith-pcm.zip --rounds 3 --output pdf-stability-results` |
| `dist/*.whl` CI artifact upload | PCM ZIP/receipt/repository metadata and verification reports |

For local repository lifecycle fixtures, the builder accepts an explicit version,
HTTP fixture base and prior frozen archives:

```text
python scripts/build_pcm.py --output dist/partsmith-0.1.9-pcm.zip --version 0.1.9 --repository-url http://127.0.0.1:8765 --previous-archive dist/partsmith-0.1.8-pcm.zip
```

Root archive metadata has one version and no download fields. Repository
metadata adds each frozen ZIP's URL, size and SHA-256 afterward, avoiding a
self-hash. Package/repository/API documents are validated offline against the
exact schemas shipped with the pinned KiCad build and closed PartSmith checks.
Local fixtures do not claim a hosted release or official repository listing.

See [packaging evidence](gates/phase13.2-packaging-2026-10-06.md) and the
[implementation specification](../resources/BFT_PartSmith_Implementation_Spec.md).
