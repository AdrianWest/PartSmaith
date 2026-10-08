<p align="center">
  <img src="resources/PartSmith-Banner.png" alt="PartSmith — AI-Driven Component Builder" width="100%">
</p>

<p align="center">
  <strong>COMING SOON</strong><br>
  PartSmith is in active development. The first public release is not available yet.
</p>

# PartSmith

PartSmith is the Board Forge Tools component builder for KiCad. It is being
built to turn authoritative component information into reviewable, native
KiCad library assets: a schematic symbol, PCB footprint, and a dimensionally
validated STEP 3D model.

The goal is not to generate a library item that merely looks plausible. Each
component follows a traceable engineering path from source evidence through
structured component data, package definitions, deterministic generation,
validation, and human approval.

## What PartSmith will produce

For a supported, approved component, PartSmith will create a package suitable
for KiCad 10.x containing:

- A native KiCad symbol (`.kicad_sym`)
- A native KiCad footprint (`.kicad_mod`)
- A STEP 3D model (`.step`)
- A manifest with artifact hashes, runtime metadata, and validation results
- Evidence and provenance links used to support engineering decisions

## How it works

```text
Authoritative documentation and evidence
                ↓
Component IR + Package Definition Library
                ↓
Input review and evidence approval
                ↓
Independent deterministic generators
                ↓
Symbol + footprint + CadQuery STEP model
                ↓
Validation and cross-validation
                ↓
Human review and explicit release approval
                ↓
Immutable component bundle
```

PartSmith treats source evidence, structured Component IR, and package
definitions as the engineering inputs. Generated artifacts never become the
source of truth for another generator. This separation makes discrepancies
visible instead of silently correcting one artifact to match another.
Project installation assembles approved components into a separately
validated library, with explicit integration authorization for the installed
files. The approved source bundles retain their original bytes and hashes.

## Engineering principles

- **Deterministic results:** Identical approved inputs should produce identical
  artifacts and recorded hashes.
- **Evidence first:** Manufacturer documentation and explicitly recorded
  standards references support package and land-pattern decisions.
- **Independent validation:** Symbols, footprints, and 3D models are generated
  independently, then checked against one another.
- **STEP is required:** Every MVP production release must include a valid
  STEP model alongside its symbol and footprint.
- **CadQuery 3D runtime:** CadQuery, OCP, and OCCT provide the selected
  parametric CAD path for STEP generation.
- **Human approval:** Automation assists engineering work; it does not replace
  explicit review when evidence is incomplete or conflicting.

## Development status

Phase 12 provides durable **Save Session / Load Session**, local evidence
inspection, deliberate selected-evidence AI requests, typed input proposals,
native generation/previews, and a separate exact release decision. Start with
a PDF and its full ordering number; select pages/DPI/OCR explicitly. Local
extraction retains original evidence before any optional AI request. Missing
engineering facts remain missing until supplied and reviewed. Component Data
accepts explicit engineering sections and provenance assignments, followed by
typed override, pin reorder/removal, exclusion and conflict-resolution requests.
Select an exact compatible PDL and **Approve Inputs** before generation.
After assembly, **Required Part Number** stays bound to that component. Use
**New / Clear Component** to process another ordering number from the same PDF;
the transition offers Save, Discard, or Cancel. A recovery checkpoint warning
does not undo or relabel a committed input or release approval.

**Open 3D Placement Viewer** becomes available for an actual retained footprint,
STEP and explicit placement. Its window has no banner and provides camera
presets, layers, pin/pad selection, measurements and exact decimal placement
drafts. A **Symbol / Pin Mapping** page also displays the actual generated
symbol, native preview, pin names/electrical types, mapping discrepancies and
bound validation results for a complete part inspection. Missing or stale
symbol data remains labeled. **Propose Placement** requires explicit input
review; draft preview and camera changes
grant no approval. **Approve Exact Release** separately checks final artifact,
manifest and validation bindings against the authenticated OS reviewer.
Archives restore unfinished work into fresh operational sessions, including
source assets, immutable history, proposals, artifacts, camera and draft state.
Loading never runs a provider, generation or an approval automatically.

From the contributor environment, launch `python -m partsmith.gui` using the
declared source path. The 12.1 synthetic rendering experiment remains available
as a separate diagnostic control. See the [Phase 12 gate](docs/gates/phase-12.md)
and [12.1 rendering decision](docs/gates/phase-12.1.md). Desktop acceptance is
scoped to Windows AMD64; other desktop platforms and remote CI are not claimed.

PartSmith is currently advancing through a gated implementation plan. The
foundation provides the Python package, command-line entry point, formatting,
linting, tests, continuous integration, and SQLite persistence for projects,
components, and builds, plus versioned Component IR validation, normalization,
canonical serialization, and hashing. Package definitions, generators,
artifact validation, KiCad integration, and the review
experience follow in controlled phases.

Shared infrastructure remains intentionally narrow. `partsmith.schema_support`
provides offline schema loading, Decimal-compatible validator construction,
and value-free error paths while each domain owns its validation policy.
`partsmith.persistence.database` provides common UTC audit timestamps and
rollback-safe SQLite savepoints while callers retain transaction ownership.

The current specification is **v0.9.8**. Phases 0–9 have recorded gate evidence.
The deterministic release pipeline includes scoped dependency projections,
immutable input review, native KiCad validation, exact-byte release approval,
and history-complete revision/inventory import and export. Revision bundles
remain `RETRIEVAL_REQUIRED`. Phase 9 adds separate verified `OFFLINE_COMPLETE`
replay bundles, network-disabled multi-revision rebuild tests, clean-build hash
comparisons, and selective reuse with scoped invalidation. The Phase 9 gate
passes locally on Windows AMD64; shared-library installation is implemented
under the [Phase 13 gate](docs/gates/phase-13.md). See the
[Phase 9 gate report](docs/gates/phase-9.md) and
[Phase 8 revalidation](docs/gates/phase-8-revalidation.md).

Phase 13 now has eight ordered milestones, beginning with the installation
contracts, fixtures, source regressions and isolated PCM contract-payload checks
needed to close **R13-01**.
The project-owner specification revision assigns those contracts to Phase 13.1;
later planning, installation and publication work requires that checkpoint's
PASS. The [13.1 contracts checkpoint](docs/gates/phase-13.1.md) now implements
those contracts and closes R13-01 after source, isolated offline PCM payload and
hash checks. The complete [Phase 13 integration gate](docs/gates/phase-13.md)
now passes on the declared Windows AMD64/KiCad 10.0.6 target. See the
[plugin/data review and revised plan](docs/spec-phase-13-review-v0.9.7.md).

The [2026-10-05 PCM correction](docs/spec-phase-13-pcm-installation-update-2026-10-05.md)
requires a KiCad Plugin and Content Manager ZIP and real install, preparation,
launch, update, uninstall and reinstall checks in Phase 13. The subsequent
[PCM-only validation update](docs/spec-phase-13-pcm-only-update-2026-10-05.md)
removes PartSmith wheel builds/tests from that phase. Phase 13.2 now implements
a deterministic PCM ZIP, pinned managed Python runtime diagnostics, exact
schema/resource checks and a read-only IPC inspector; active wheel automation
has been replaced by source/PCM checks. The
[13.2 checkpoint](docs/gates/phase-13.2.md) records actual PCM lifecycle,
offline preparation/recovery, live PCB inspection and local NTFS publication
feasibility acceptance with affected-manifest hash closeout.
The [13.3 checkpoint](docs/gates/phase-13.3.md) adds pure approved-source
planning, bounded project inventory and immutable integration persistence.
The [13.4 checkpoint](docs/gates/phase-13.4.md) packs deterministic libraries
with exact engineering comparisons and real native SVG/STEP validation.
The [13.5 checkpoint](docs/gates/phase-13.5.md) provides fresh authenticated
installation decisions bound to exact content, with durable retry/cancellation
handling. The [13.6 checkpoint](docs/gates/phase-13.6.md) adds complete owned
NTFS project publication, real process-crash recovery and freshly authorized
rollback that preserves current user files. The
[13.7 checkpoint](docs/gates/phase-13.7.md) adds deliberate project controls,
safe saved references and actual two-component native/IPC round trips with
the PCM-installed 0.1.9 runtime. The [13.8 closeout](docs/gates/phase-13.8.md)
records 1,104 source checks, 14 source desktop checks, 1,118 isolated PCM checks,
98 offline contract checks and three 194-check PDF/native/desktop rounds, all
passing without skips, alongside supervised PCM/native/IPC evidence and final
affected-manifest hash verification.
Customers install through PCM; see [PCM installation](docs/pcm-installation.md).
The [Phase 14 online candidate](docs/gates/phase-14.md) uses KiCad's managed
Python environment and pinned `requirements.txt`. KiCad downloads the upstream
binary wheels, including their CAD DLLs; the PartSmith ZIP contains source and
resources. Installation, updates and environment recreation require internet.
Offline installation and an optional offline edition are out of scope.
KiCad's bundled Python 3.11 and external Tesseract 5 with `eng`, `deu` and
`chi_sim` models are prerequisites. All eight MVP variants retain their frozen
release corpus. The gate remains open for clean Windows online PCM acceptance
and dependency/license manifest review. No public release is asserted.

AI-assisted document interpretation is intentionally later in the plan. The
first end-to-end component path must be deterministic and AI-free.

## Setup GUI (Phase 9.5)

The optional wxPython setup window displays PartSmith-Banner3.png across the
top, secure **Set AI API Key** entry, a local PDF chooser, **Required Part
Number**, **Start**, **Cancel**, and a live log panel. Enter the complete
manufacturer order number, including package suffixes: one datasheet can cover
multiple package styles. The number is passed intact to the processing service.
Start performs local PDF extraction and reports the exact ordering-table package
mapping or a blocked unrecognized/ambiguous mapping. The optional OpenAI
checkbox adds unreviewed Phase 11 interpretation candidates. Phase 12 human
review/application remains required before a component can be built.

For development in a Python 3.11 environment, install the pinned
Windows customer runtime and load the declared source tree:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary :all: -r requirements-pcm.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m partsmith.gui
```

`python -m partsmith.gui` launches from the contributor environment. The PCM
action loads its installed package directly. These paths resolve the banner independently of the
working directory. Keys are saved in the operating system's secure credential
store (Windows Credential Manager on the verified Windows runtime). The key
dialog always opens blank, masks new input, saves on **OK**, and preserves the
existing key on **Cancel**. Saved keys are never displayed or written to logs.

For historical development of the launch-only entry, use:

```powershell
.\.venv\Scripts\python.exe -m partsmith.gui.install_kicad --plugin-dir "$env:APPDATA\kicad\10.0\scripting\plugins"
```

Restart the PCB Editor, then select **Tools → External Plugins → PartSmith
Setup**. If your KiCad uses another configuration directory, use the scripting
plugin directory reported by the PCB Editor's Action Plugins preferences.
The entry starts PartSmith's Python 3.12 environment as a separate process;
it imports no PartSmith CAD dependencies into KiCad's embedded Python.
Reinstall the entry if the PartSmith environment moves. The installed
`launcher.json` contains only the interpreter path. This manual-copy entry is a
legacy development path; the customer IPC plugin uses PCM and separate
version-matched `plugin.json` registration.

The launch entry follows KiCad's
[documented action-plugin interface](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html);
the expanded integration gate is recorded in [Phase 13](docs/gates/phase-13.md).
This desktop runtime is verified on
Windows AMD64; Linux/macOS GUI installation and native keyring availability
have not been verified. For desktop integration checks, run
`python -m pytest scripts/verify_gui.py -v`; the ordinary test suite also checks
the processing and launch contracts without needing wxPython or a desktop.
See [Phase 9.5 verification](docs/gates/phase-9.5.md) for evidence and scope.

## For contributors

Customer PCM targets **Python 3.11.x**, bundled with KiCad 10.0.6 (locally
verified as 3.11.5). No external customer Python is required. The project permits
`>=3.11,<3.13`; existing Python 3.12 producer tools and historical verification
remain supported. Create a Python 3.12 producer environment with its pinned tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-ci.txt
python -m pip install --requirement requirements-extraction.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\scripts\setup_kicad.ps1
```

Phase 8 and later release validation requires native KiCad 10.0.6. Internal
PartSmith syntax parsers cannot replace `kicad-cli`; `partsmith doctor` fails
when the pinned target runtime is missing or incompatible.

The IPC plugin uses KiCad's private venv based on bundled Python 3.11, outside
the legacy ActionPlugin host. Native validation invokes the CLI. Existing 3.12
plugin caches require **Recreate Plugin Environment** after switching Python.
The repository installer selects bundled Python with a preference backup;
customer installation uses PCM.
Release snapshots record the actual Python patch/build and executable hash,
the pinned KiCad CLI version/hash, and the verified CadQuery/OCP/OCCT tuple.
The 3.11 lock contains Windows AMD64 cp311 CAD wheel and file identities;
the unchanged historical 3.12 lock covers Windows/Linux; release generation rejects mismatched installed runtime bytes.

For Windows PCM runtime and desktop checks, create a separate Python 3.11
venv and install the pinned third-party closure with `python -m pip install --only-binary :all:
--requirement requirements-pcm.txt`. This is contributor setup; customers use
KiCad's managed preparation and do not run pip or install a PartSmith package.

Run the local quality checks before contributing:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m partsmith version
python -m partsmith doctor --json
python scripts/build_pcm.py --output dist/partsmith-pcm.zip
python scripts/verify_pcm.py dist/partsmith-pcm.zip --evidence pcm-payload-results.json
python scripts/verify_pdf_stability.py --archive dist/partsmith-pcm.zip --rounds 3 --output pdf-stability-results
```

Enable the repository's pre-push gate once per clone:

```powershell
git config --local core.hooksPath .githooks
```

When a committed phase-gate input changes, refresh its recorded hashes from
Git blobs, commit the affected manifest, and then push. For example:

```powershell
python scripts/verify_phase2_manifest.py --manifest docs/gates/phase-6-artifacts.json --source git --update
git add docs/gates/phase-6-artifacts.json
git commit -m "Refresh Phase 6 input hashes"
```

The hook is local to clones that enable it; CI still verifies the recorded
phase manifests and native KiCad compatibility on both operating systems. A
failed gate requires investigation, not bypassing the check.

`python -m partsmith doctor` verifies the Phase 0 runtime foundation: supported
Python, package version and command-line availability. The PCM action adds
strict installed resource, dependency, CAD and exact IPC session checks.

## Persistence (Phase 1)

```python
from partsmith.persistence import Repository, database

with database("partsmith.sqlite3") as connection:
    records = Repository(connection)
    project = records.create_project("Example board", "/projects/example")
    component = records.create_component(
        "Example manufacturer", "R-0402", "0402", project_id=project.id
    )
    build = records.create_build(component.id, "DRAFT")
    assert records.get_build(build.id) == build
```

`database` enables foreign keys, applies migration 001 once, commits successful
work, rolls back failed work, and closes the connection. For explicit lifecycle
control, use `connect` and `migrate`, then commit/roll back and close yourself.
Repository methods never commit independently. Missing ID queries return `None`;
invalid references raise `sqlite3.IntegrityError`. Parent deletion is restricted.
Build state is stored as supplied; later phases implement validation and approval.

Migration SQL lives in `migrations/001_initial.sql` and the PCM payload.
Applied migrations are checksum-verified and must never be edited. Future schema
changes require new migrations. Every domain record has UTC creation/update
timestamps; Phase 1 exposes creation and queries, not editing workflows.

Run `python -m pytest tests/test_persistence.py` for the Phase 1 tests.
See [Phase 1 gate evidence](docs/gates/phase-1.md) for recorded verification.

## Component IR (Phase 2)

```python
from partsmith.ir import ComponentIR, validate_ir

ir = ComponentIR.from_file("fixtures/ir/v1.2/valid/0402.json")
assert validate_ir(ir.data) == ()
print(ir.sha256)
```

Component IR 1.0, 1.1, and 1.2 have packaged offline schemas, exact decimal
normalization, canonical JSON profile 1.0, and SHA-256 record hashing. IR 1.2
adds typed overrides, independent evidence relevance, active decision selectors,
immutable revision checks, applicability records, and document-page coordinates.
Generation prechecks require both a trusted `RequirementsContext` and a read-only
revision/inventory store. Explicit 1.0→1.1→1.2 migration preserves source records
and returns issues when required evidence is missing.

Snapshot-profile 1.1 dependency projections distinguish engineering content from
audit history, including self-bound overrides. The fixtures and contexts are
synthetic, not production approvals. Production PDL contexts, affine transforms,
CAD generation, artifact validators, the build orchestrator, and approval services
remain in their specified later phases.
Specification v0.9.6 introduces snapshot profile 1.2 for configuration scoped
to each generator and validation step. The Phase 8 pipeline freezes complete
profile 1.2 release snapshots before generation. The original profile 1.1
helpers and golden hashes remain supported.

Run `python -m pytest tests/test_ir.py tests/test_ir_v11.py tests/test_ir_v12.py`
for all IR versions.
See the [IR contract](docs/component-ir.md) and
[IR 1.2 Phase 2 gate evidence against v0.9.5](docs/gates/phase-2-ir-1.2.md). The earlier
[IR 1.1 PASS](docs/gates/phase-2-ir-1.1.md) retains its v0.9.4 baseline.

## Package Definition Library (Phase 3)

```python
from partsmith.pdl import load_pdl, resolve_pdl

pdl = load_pdl("synthetic-0402", "1.0")
assert pdl.data["identity"]["variant"] == "0402"
assert resolve_pdl("chip_resistor", "0402", {"1", "2"}) == pdl
```

PDL 1.0 provides a strict offline schema, immutable canonical records,
content hashing, exact revision loading, deterministic package resolution,
terminal/group/pad-shape topology validation, release-profile binding, and
Component IR compatibility checks. The packaged `synthetic-0402@1.0` entry and
`GOLD-0402-001` are deterministic bootstrap fixtures, not manufacturer evidence
or production package approval.

Inspect the installed catalog with `partsmith pdl list`,
`partsmith pdl inspect synthetic-0402`, or
`partsmith pdl validate synthetic-0402`. See the
[Phase 3 gate evidence](docs/gates/phase-3.md).

## AI interpretation (Phase 11)

PartSmith includes one released provider adapter: OpenAI Responses API using
the pinned `gpt-4.1-mini-2025-04-14` model. It sends selected extracted Evidence
text and provenance, with local OCR and `store=false`. OpenAI account retention
and abuse monitoring terms still apply; the user pays API charges directly.
It sends no PDF files, page images, local paths, or tools.

Set a customer key through **Set AI API Key** in the GUI (native OS credential
storage), or set `OPENAI_API_KEY` securely in the process environment. Keys are
never command arguments, project settings, candidate exports, logs, or hashes.
The GUI defaults to local extraction. Its OpenAI disclosure checkbox and
**Send Selected Evidence** action authorize only the previewed selection;
candidates remain unreviewed in the saved session for later application.

```powershell
partsmith extract test_data_sheets/LM2575-D.PDF --pages 24 --dpi 100 --output extraction.json
partsmith ai analyze extraction.json --task identify_package --part-number LM2575TV-ADJG --output candidates.json
```

Use `--evidence-ids` to restrict records, and `--targets` for IR value tasks.
Supported narrow tasks cover pins, packages, mechanical/land-pattern text,
symbol properties, conflict/ambiguity explanations, and English/German/Chinese
translation. Drawing tasks use supplied text/OCR; image-only interpretation is
not implemented. `--local` sends nothing and reports AI unavailable.

Results contain typed, source-linked candidates, exact source quotations,
provider/model/request metadata, input/output hashes, and conflicts or
ambiguities. The adapter rejects unrequested targets, fabricated references,
approval fields, invalid value types, and credential material. Confidence is
advisory; candidates cannot approve an IR or generate production artifacts.
Phase 12 review/application remains required. `RecordedProvider` reuses a
validated immutable `AIResult` offline, retaining its original audit envelope
and rejecting changed request or adapter bindings.

Offline tests run with the normal suite. The opt-in live gate loads only
`BFT_TOKEN` from repository `.env` for development testing (AI-005); the app
does not load that file. Missing credentials fail the live gate clearly.

```powershell
.tools/python/python.exe -c "import sys; sys.path[:0]=['src','.']; import pytest; raise SystemExit(pytest.main(['scripts/verify_ai_live.py','-q']))"
```

See [Phase 11 gate evidence](docs/gates/phase-11.md) and the packaged
[adapter manifest](src/partsmith/ai/adapter-manifest-1.0.json).

## Document extraction (Phase 10)

The GUI and CLI run PDF extraction in a separate worker process. A native
parser failure reports an extraction error without closing the application.
Progress and cancellation cross the process boundary; cancellation reaps the
worker. Windows crash dialogs are disabled only inside that worker. Run native
PDF/KiCad checks from a normal desktop shell with access to installed libraries
and configuration files.

```powershell
partsmith extract test_data_sheets/LM2575-D.PDF --pages 24 --dpi 200 --part-number LM2575TV-ADJG --output evidence.json
partsmith extract scanned.pdf --dpi 300 --languages chi_sim eng --ocr-layout 6 --output evidence.json
```

`extract_document()` snapshots and hashes the original PDF, validates one-based
page selection, and produces IR 1.2-compatible, unreviewed Evidence records for
native text, tables, vector diagrams, images, and local OCR. Its JSON result
retains table cells, word boxes/confidence, language candidates, and embedded
content-addressed PNGs. Engineering quantities stay unknown; no Component IR,
symbol, footprint, or STEP is generated. Package candidates are resolved only
from exact full order numbers in recognized table columns; unrecognized and
ambiguous mappings remain blocked.

Install the pins in `requirements-ci.txt` and `requirements-extraction.txt`.
OCR also needs
Tesseract 5 with `eng`, `deu`, and `chi_sim` trained data. On Windows the adapter
checks `C:/Program Files/Tesseract-OCR/tesseract.exe`; on other systems use PATH,
or set `PARTSMITH_TESSERACT`. `TESSDATA_PREFIX` can select a model directory.
For a short text block, choose `--ocr-layout 6`; default mode 3 analyzes a full
page and mode 11 extracts sparse text. Use 300 DPI for the multilingual OCR
reference fixtures. Language candidates use script/keyword hints and may remain
uncertain. Explicit translations retain original text and provider/model/time
provenance; this phase does not call a translation provider.

The versioned `mvp-1@1.1` extraction profile pins English, German, and Simplified
Chinese. Earlier deterministic package fixtures retain `mvp-1@1.0`. Canonical
source regions use physical PDF points in the original unrotated MediaBox;
render mappings preserve crop, rotation, UserUnit, DPI, and pixel-edge offsets.
Image/vector objects extending beyond a page retain their original object bounds
alongside the visible source region. PDFs that open with an empty password are
supported; password-required PDFs fail explicitly. Ingestion permits up to
100 MiB and 5,000 pages, with a 40 megapixel limit per rendered page. Use
`--pages` to select relevant pages from long manuals.
Scanned ruled grids can become OCR table candidates; borderless/merged/damaged
grids remain image/OCR candidates for later interpretation. Non-affine dewarping
is unsupported.

The supported PDF runtime uses PDFium via pypdfium2 5.14.0 for rendering and
pdfplumber 0.11.10/pdfminer.six 20260107 for native text, graphics and tables.
Production extraction does not import MuPDF. Text-containing graphics bounds retain
open outer parameter/unit columns; cell text, merged-cell nulls, source
coordinates and detection settings are preserved. Detector errors fail
extraction explicitly.

See [Phase 10 parser correction and revalidation](docs/gates/phase-10-parser-fix-2026-10-04.md)
and [the original Phase 10 evidence](docs/gates/phase-10.md). Run
`python -m pytest tests/test_extraction.py` for the corpus and targeted fixtures.
After building the PCM ZIP, run
`python scripts/verify_pdf_stability.py --archive dist/partsmith-pcm.zip --rounds 3 --output pdf-stability-results`.
Add `--desktop` to include native wx and credential checks in a Windows desktop
session with the GUI dependencies installed. Each round retains its JUnit
report and raw output; a failure stops the gate without retrying. Use a fresh
output directory for each invocation.

## Specification

The v0.9.7 implementation contract is maintained in
[the PartSmith Implementation Specification](resources/BFT_PartSmith_Implementation_Spec.md).
It defines the phase gates, engineering authority model, deterministic output
requirements, and CadQuery-based 3D architecture.

## License

This project is distributed under the terms in [LICENSE](LICENSE).
