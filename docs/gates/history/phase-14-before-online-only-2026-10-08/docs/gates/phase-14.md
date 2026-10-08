# Phase 14 acceptance candidate

The production implementation is present; **the Phase 14 gate remains OPEN**.
The candidate is Windows AMD64, embedded CPython 3.12.10 and KiCad 10.0.6.
Clean supported-machine acceptance and a complete audit of native libraries
embedded inside third-party wheels still block production release.

The PCM ZIP registers an `exec` action. `PartSmith.exe` starts its own isolated
interpreter relative to the launcher, with user site, current-directory imports
and Python environment overrides excluded. Runtime validation checks every owned
file and original notice before application imports. The pinned CAD tuple remains
CadQuery 2.8.0, OCP distribution 7.9.3.1.1 and OCCT 7.9.3. Tesseract 5.5.1 and
`eng`, `deu`, `chi_sim` models are bundled. No customer pip, Conda, compiler,
separate Python or separate CAD installation is used.
Unverified application bytecode caches and links are rejected before imports;
the launcher disables bytecode writes to the installed runtime.

Dependency extraction uses the reviewed
[production lock](../../resources/runtime/production-lock.json), including
original archive and member hashes. The builder produces `dependencies.json`,
`bundle.json`, native launchers and a complete installed-file inventory.
Original wheel/Conda notices, OCCT LGPL/exception and CasADi LGPL/GPL texts retain
their bytes. Packaging limits are independent of the unchanged IPC resource
limits. Missing files, altered notices, undeclared files, aliases and unsafe ZIP
members fail closed. CAD, Python and Visual C++ DLLs must load from the bundle;
Windows DLLs and signed, registered AMSI extensions are recorded separately.

The dependency manifest validates declared ownership and exact retained notices.
That structural validation does **not** establish a complete native vendor SBOM.
The OCP wheel bundles image/codec DLLs in `cadquery_ocp.libs` without a full
vendor notice inventory. FreeImage, FreeType, OpenEXR/Imath, LibRaw and their
embedded codecs require corresponding version/source/license/notice records.
Other native wheels require the same vendor-level audit. This is an explicit
remaining INSTALL-004/005 requirement, not an approved exception.
The [native binary audit](phase-14-native-license-audit.json) records exact wheel
and binary hashes plus declared PE version strings for 30 native wheels. Those
strings do not prove upstream source provenance or enumerate static dependencies.

## Package corpus

The [frozen source facts](../../fixtures/production/packages.json) bind retained
manufacturer PDFs, package drawings, recommended pads and pin tables.
[Golden identities](../../fixtures/production/golden.json) bind the final
symbol, associated footprint and STEP bytes for every variant.

| Variant | Frozen manufacturer input | Package drawing |
| --- | --- | --- |
| 0402 | Vishay CRCW040210K0FKEA | D/CRCW e3, page 11 |
| 0603 | Vishay CRCW060310K0FKEA | D/CRCW e3, page 11 |
| 0805 | Vishay CRCW080510K0FKEA | D/CRCW e3, page 11 |
| SOT-23 | Diodes MMBT3904-7-F | SOT23, page 6; pinout page 1 |
| SOIC-8 | TI LM358DR | D0008A, pages 54–55 |
| TSSOP-16 | TI SN74HC595PWR | PW0016A, pages 34–35 |
| QFN-16-3x3-0.5P | TI TPS62140RGTR | RGT0016C, pages 39–40 |
| QFN-24-4x4-0.5P | TI TPS65131RGER | RGE0024B, pages 36–37 |

PDL 1.1 provides distinct exposed-pad dimensions and explicit lead profiles.
Parsed STEP solids and cylindrical faces supply the dimensional/alignment/index
measurements. Polynomial terminal matching replaces factorial permutations.
Footprints use KiCad's downward Y axis, courtyards enclose copper and body, and
IC symbols have separate terminal rows. Active-low pins retain their meaning.
Historical synthetic 0402 references remain intact and do not count as production
evidence. Ambiguous package resolution requires an explicit PDL selection.

Each variant runs the complete release pipeline with native KiCad round trips,
exact-byte regeneration and independently malformed artifacts: missing terminals,
offset, wrong units, body height, terminal width, wrong pad numbers and rotation;
indexed packages also test reflection, and QFN packages test exposed-pad size.
The pinned `mvp-1@1.1` profile is unchanged. Rendering choices, including selected
seated heights, simplified bend profiles and index recesses, are explicitly
recorded separately from manufacturer tolerances. A recess representing an index
area is not claimed as manufacturer-specified recess geometry.

Corpus inputs are reviewed **test fixtures** in disposable databases. Acceptance
does not create an engineering approval in a user's database. Golden creation is
an explicit maintainer command; normal tests only compare frozen references.

## Build and installation

Producer commands, using the project's Python 3.12 environment:

```powershell
.venv/Scripts/python.exe -m pip install zstandard==0.25.0
.venv/Scripts/python.exe scripts/prepare_production_runtime.py --output .tools/production-runtime
.venv/Scripts/python.exe scripts/build_production_pcm.py --runtime .tools/production-runtime --output dist/partsmith-0.2.0-pcm.zip
.venv/Scripts/python.exe scripts/verify_phase14_packages.py --output corpus-results.json
```

Preparation accepts a preprovisioned `--cache`, verifies every original artifact,
and reconstructs exact files without dependency resolution. The builder makes no
network request and verifies the final archive before publishing it. A second
candidate version, 0.2.1, is used only to test upgrade behavior.

Install the candidate ZIP through KiCad PCM, or use
[install_production.bat](../../install_production.bat) with KiCad closed. The batch
uses Windows PowerShell, verifies all ZIP member hashes, stages a spare bundle
outside plugin discovery and invokes its own native installer. The older
`install_partsmith.bat` remains the developer-source installation path.
Its development version is now 0.1.12 so it cannot overwrite the frozen 0.1.11
startup/lifecycle acceptance archive. The production candidate is separate.

```powershell
./install_production.bat -Archive C:/path/partsmith-0.2.0-pcm.zip
# Explicit removal preserves rollback bytes and unrelated packages:
./install_production.bat -Archive C:/path/partsmith-0.2.0-pcm.zip -Uninstall
```

Installation retains transactional backups outside `3rdparty`; uninstall removes
owned discovery paths and registration while retaining rollback bytes and user
application state. Installation rejects running KiCad/PartSmith windows and
concurrent registry changes. Use a spare extracted bundle for update/removal,
never the installed runtime as its own updater.

Installed diagnostics and the offline release corpus use the console executable:

```powershell
./PartSmith-diagnostics.exe --diagnostics
./PartSmith-diagnostics.exe --self-test --output C:/acceptance/corpus.json
```

Normal startup retains deliberate PCB selection, follows the exact launching
KiCad process and does not expose the retired rendering-prototype button.
The executable entry also corrects KiCad's inherited hidden-window startup flag.
GUI acceptance verifies actual Windows visibility before entering the event loop.

## Acceptance scope

The [acceptance workflow](../../.github/workflows/phase14.yml) builds candidates
on a producer runner and transfers only ZIPs and acceptance helpers to a separate
customer runner. It installs KiCad only, then blocks external Python settings and
PATH before install, GUI launch, diagnostics, corpus, upgrade, corruption rejection
and uninstall. `clean_runner=true` selects a freshly provisioned Windows 11 AMD64
self-hosted runner labelled `partsmith-clean`. Its administrator must retain clean
image provenance and absence of independently installed Python/CAD/Conda runtimes.
The installed embedded interpreter also renders a frozen PDF page and performs
OCR independently with `eng`, `deu` and `chi_sim`. This exercises the retained
Tesseract TSV configuration as well as the engine and language models.

The default hosted-runner mode proves process isolation on a provisioned image;
it does not satisfy the clean supported-machine requirement. Local development
machine receipts have the same narrower scope. A workflow file alone is not
execution evidence. No hosted or clean runner execution is claimed here.

Local acceptance used fresh profiles with spaces in their paths. The final
[installation receipt](phase-14-runtime/install-upgrade-uninstall.json) records
0.2.0 installation, 0.2.1 upgrade, READY diagnostics, corruption/missing-model/
untracked-bytecode rejection, uninstall and preservation of an unrelated package.
The [installed corpus](phase-14-runtime/corpus.json) records CLASS A, native KiCad
compatibility and exact bytes for all eight variants. The
[engine receipt](phase-14-runtime/engines.json) records successful PDF rendering
and 335 English, 369 German and 319 simplified-Chinese OCR words.

The [current-profile GUI receipt](phase-14-native-gui/receipt.json) binds the
0.2.0 installed inventory, 10,858 verified owned files and captured setup controls.
The setup is visible, starts without board inspection and has no retired 0402
rendering button. Closing the PCB Editor while the KiCad manager remains alive
keeps PartSmith open; closing the manager closes PartSmith and its interpreter.
The board's before/after identity is unchanged. Session recovery was declined
with its No option; no processing, export or engineering approval was requested.

The 0.2.0 archive is byte-identical when rebuilt using the minimal producer
environment containing only schema/extraction build tools instead of the richer
development environment. Original runtime input bytes and all 24 golden artifact
bytes remain frozen. The earlier source-suite failure caused by overlapping
native KiCad acceptance processes is retained in
[historical results](history/phase-14-concurrent-native-process-results.xml);
the final source run is performed separately with KiCad closed.

Final source acceptance covers **1,154 unique cases**, with no outstanding
failures. The full run passed 1,144 cases and found ten failures in an outdated
PCM orchestration fixture. Its fake frame lacked the recovery argument and native
visibility interface now required by the entry point. Updating that fixture
changed only `tests/test_pcm.py`; the application and candidate bytes stayed the
same. Complete revalidation of that module passed all 38 cases. The other 1,116
cases passed in the full run. The
[revalidation receipt](phase-14-runtime/source-revalidation.json) binds both
captures and the original/updated test fixtures. The original failing capture is
retained; no single all-pass full run is claimed. The separate
[desktop run](phase-14-runtime/desktop-results.xml) passed all 18 cases.
Ruff lint, formatting of 304 files and tagged docstrings also passed.

Exact final receipts and test identities are recorded in
[phase-14-artifacts.json](phase-14-artifacts.json). Historical Phase 13 package and
execution identities remain frozen at their original scope; affected active input
maps are refreshed and archived separately.

Hash closeout commands verify the candidate identities and every active/CI input
map. The subsequent committed-input receipt checks both Git blobs and checkout
bytes; these checks record the candidate and do not close its remaining blockers.

```powershell
.venv/Scripts/python.exe scripts/close_integration_gate.py --phase 14 --reason "Phase 14 candidate; historical acceptance scope retained"
.venv/Scripts/python.exe scripts/verify_committed_gate_inputs.py --closeout docs/gates/phase-14-hash-closeout.json --output docs/gates/phase-14-committed-verification.json
```

See [hash closeout](phase-14-hash-closeout.json) and
[committed verification](phase-14-committed-verification.json).
