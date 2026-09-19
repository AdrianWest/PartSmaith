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
Independent deterministic generators
                ↓
Symbol + footprint + CadQuery STEP model
                ↓
Validation and cross-validation
                ↓
Human review and explicit approval
```

PartSmith treats source evidence, structured Component IR, and package
definitions as the engineering inputs. Generated artifacts never become the
source of truth for another generator. This separation makes discrepancies
visible instead of silently correcting one artifact to match another.

## Engineering principles

- **Deterministic results:** Identical approved inputs should produce identical
  artifacts and recorded hashes.
- **Evidence first:** Manufacturer documentation and explicitly recorded
  standards references support package and land-pattern decisions.
- **Independent validation:** Symbols, footprints, and 3D models are generated
  independently, then checked against one another.
- **STEP is required:** Released components with 3D geometry must include a
  valid STEP model.
- **CadQuery 3D runtime:** CadQuery, OCP, and OCCT provide the selected
  parametric CAD path for STEP generation.
- **Human approval:** Automation assists engineering work; it does not replace
  explicit review when evidence is incomplete or conflicting.

## Development status

PartSmith is currently advancing through a gated implementation plan. The
foundation provides the Python package, command-line entry point, formatting,
linting, tests, continuous integration, and SQLite persistence for projects,
components, and builds. Component IR,
package definitions, generators, validation, KiCad integration, and the review
experience follow in controlled phases.

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

## Specification

The implementation contract is maintained in
[the PartSmith Implementation Specification](resources/BFT_PartSmith_Implementation_Spec.md).
It defines the phase gates, engineering authority model, deterministic output
requirements, and CadQuery-based 3D architecture.

## License

This project is distributed under the terms in [LICENSE](LICENSE).
