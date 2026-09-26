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

The current specification is **v0.9.6**. The recorded IR 1.2 Phase 2 PASS covers
the implementation against v0.9.5 and remains the prerequisite for Phase 3.
The revised specification assigns new dependency projections, review services,
portable rebuild bundles, and installation behavior to later phases; these
features are not yet implemented.

AI-assisted document interpretation is intentionally later in the plan. The
first end-to-end component path must be deterministic and AI-free.

## For contributors

PartSmith currently supports **Python 3.12.x** (`>=3.12,<3.13`). Create a
development environment and install the pinned project tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements-ci.txt
python -m pip install -e . --no-deps
```

Run the local quality checks before contributing:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
partsmith version
partsmith doctor --json
```

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
to each generator and validation step. Its implementation and verification are
assigned to Phases 4–6 and 8–9; the current helpers still produce profile 1.1.

Run `python -m pytest tests/test_ir.py tests/test_ir_v11.py tests/test_ir_v12.py`
for all IR versions.
See the [IR contract](docs/component-ir.md) and
[IR 1.2 Phase 2 gate evidence against v0.9.5](docs/gates/phase-2-ir-1.2.md). The earlier
[IR 1.1 PASS](docs/gates/phase-2-ir-1.1.md) retains its v0.9.4 baseline.

## Specification

The v0.9.6 implementation contract is maintained in
[the PartSmith Implementation Specification](resources/BFT_PartSmith_Implementation_Spec.md).
It defines the phase gates, engineering authority model, deterministic output
requirements, and CadQuery-based 3D architecture.

## License

This project is distributed under the terms in [LICENSE](LICENSE).
