<p align="center">
  <img src="resources/PartSmail-Banner.png" alt="PartSmith — AI-Driven Component Builder" width="100%">
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
Project installation will assemble approved components into a separately
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

The current specification is **v0.9.6**. Phases 0–9 have recorded gate evidence.
The deterministic release pipeline includes scoped dependency projections,
immutable input review, native KiCad validation, exact-byte release approval,
and history-complete revision/inventory import and export. Revision bundles
remain `RETRIEVAL_REQUIRED`. Phase 9 adds separate verified `OFFLINE_COMPLETE`
replay bundles, network-disabled multi-revision rebuild tests, clean-build hash
comparisons, and selective reuse with scoped invalidation. The Phase 9 gate
passes locally on Windows AMD64; shared-library installation remains Phase 13
work. See the [Phase 9 gate report](docs/gates/phase-9.md) and
[Phase 8 revalidation](docs/gates/phase-8-revalidation.md).

AI-assisted document interpretation is intentionally later in the plan. The
first end-to-end component path must be deterministic and AI-free.

## Setup GUI (Phase 9.5)

The optional wxPython setup window displays the PartSmail banner across the
top, secure **Set AI API Key** entry, a local PDF chooser, **Required Part
Number**, **Start**, **Cancel**, and a live log panel. Enter the complete
manufacturer order number, including package suffixes: one datasheet can cover
multiple package styles. The number is passed intact to the processing service.
Start currently performs PDF/input preflight and reports that Phase 10 extraction
and Phase 11 interpretation are unavailable; it does not build a component.

With the existing Python 3.12 environment, install the optional Windows runtime:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gui-windows.txt
.\.venv\Scripts\python.exe -m pip install -e ".[gui]" --no-deps
.\.venv\Scripts\python.exe scripts\partsmith_gui.py
```

After installation, `python -m partsmith.gui` or `partsmith-gui` also launches
the window. All launch paths resolve the packaged banner independently of the
working directory. Keys are saved in the operating system's secure credential
store (Windows Credential Manager on the verified Windows runtime). The key
dialog always opens blank, masks new input, saves on **OK**, and preserves the
existing key on **Cancel**. Saved keys are never displayed or written to logs.

For KiCad 10.0.6 on Windows, install the launch-only action plugin:

```powershell
.\.venv\Scripts\python.exe -m partsmith.gui.install_kicad --plugin-dir "$env:APPDATA\kicad\10.0\scripting\plugins"
```

Restart the PCB Editor, then select **Tools → External Plugins → PartSmith
Setup**. If your KiCad uses another configuration directory, use the scripting
plugin directory reported by the PCB Editor's Action Plugins preferences.
The entry starts PartSmith's Python 3.12 environment as a separate process;
it imports no PartSmith CAD dependencies into KiCad's embedded Python.
Reinstall the entry if the PartSmith environment moves. The installed
`launcher.json` contains only the interpreter path. The installer also works
from a wheel using `partsmith-kicad-setup --plugin-dir <directory>`.

The launch entry follows KiCad's
[documented action-plugin interface](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html);
broader IPC integration remains Phase 13. This desktop runtime is verified on
Windows AMD64; Linux/macOS GUI installation and native keyring availability
have not been verified. For desktop integration checks, run
`python -m pytest scripts/verify_gui.py -v`; the ordinary test suite also checks
the processing and launch contracts without needing wxPython or a desktop.
See [Phase 9.5 verification](docs/gates/phase-9.5.md) for evidence and scope.

## For contributors

PartSmith currently supports **Python 3.12.x** (`>=3.12,<3.13`). Create a
development environment and install the pinned project tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-ci.txt
python -m pip install -e . --no-deps
.\scripts\setup_kicad.ps1
```

Phase 8 and later release validation requires native KiCad 10.0.6. Internal
PartSmith syntax parsers cannot replace `kicad-cli`; `partsmith doctor` fails
when the pinned target runtime is missing or incompatible.

PartSmith uses its own Python 3.12.x environment and invokes KiCad through the
native CLI. The installed Windows KiCad 10.0.6 bundles Python 3.11.5; its
embedded interpreter is separate from PartSmith's supported Python baseline.
Release snapshots record the actual Python patch/build and executable hash,
the pinned KiCad CLI version/hash, and the verified CadQuery/OCP/OCCT tuple.
The packaged runtime lock contains Windows/Linux CAD wheel hashes and file
identities; release generation rejects mismatched installed runtime bytes.

Run the local quality checks before contributing:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
partsmith version
partsmith doctor --json
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

`partsmith doctor` verifies the Phase 0 runtime foundation: supported Python,
installed package version, and command-line availability.

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

Migration SQL lives in `migrations/001_initial.sql` and is included in wheels.
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

## Specification

The v0.9.6 implementation contract is maintained in
[the PartSmith Implementation Specification](resources/BFT_PartSmith_Implementation_Spec.md).
It defines the phase gates, engineering authority model, deterministic output
requirements, and CadQuery-based 3D architecture.

## License

This project is distributed under the terms in [LICENSE](LICENSE).
