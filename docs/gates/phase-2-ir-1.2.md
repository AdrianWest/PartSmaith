# Revised Phase 2 — Component IR 1.2: PASS

Recorded 2026-09-20 on `Phase-02-Development`, against specification v0.9.5,
section 121. This is local Windows verification. The Linux/Windows GitHub Actions
workflow was not run remotely during this task.

Prerequisite: [Phase 1 PASS](phase-1.md). The 12 persistence tests pass in both
installations. The earlier [IR 1.0 gate](phase-2.md) and
[IR 1.1 gate](phase-2-ir-1.1.md), their reports, schemas, and fixtures retain
their original versions. This revised PASS satisfies the v0.9.5 Phase 2
prerequisite for Phase 3; Phase 3 has not been implemented by this change.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, jsonschema 4.26.0,
pytest 8.4.2, Ruff 0.16.8. Checks used the existing `.env` and `.venv` without
changing `.env` or exposing its values. Python required access to the existing
base interpreter outside the sandbox. Wheel checks used a fresh virtual
environment and verified that imports came from `site-packages`.

| Requirement | Implemented and verified |
| --- | --- |
| Versioned schema | Strict offline Draft 2020-12 IR 1.2 schema; all three versioned schemas packaged and byte-compared against repository sources |
| Typed overrides | Trusted path/type registry; pin, quantity, value, placement and array records; scalar/vector/mirror edits; exact new-value and base-value binding; overlapping/incorrect targets rejected |
| Evidence relevance | Candidate targets independent of selected evidence; unresolved relevant candidates require explicit resolutions even after selection links are removed |
| Reviewed history | Read-only revision/inventory protocol; detached in-memory implementation; immutable retained records, exact inventory hashes, parent/component identity, explicit removal/supersession and terminal rebindings |
| Resolution lifecycle | Explicit active selectors; successive approvals retain immutable earlier decisions and original selection snapshots |
| Applicability | Strict result stage, applicability/basis/reason, nullable status for declared exclusions, and measurement mode; fabricated PASS for NOT_APPLICABLE rejected |
| Source regions | Document-page-1.0 fields, MediaBox bounds, crop/rotation metadata, positive units/DPI, invertible pixel transforms and explicit OCR localization |
| Migration | Explicit 1.1→1.2 migration with supplied relevance, coordinates, review bindings, accuracy class and result classifications; original record/hash preserved; missing information fails |
| Canonicalization | Existing canonical profile 1.0; frozen record bytes/hash and cross-process hash-seed checks; null candidate quantities remain explicit |
| Dependency projections | Snapshot profile 1.1; recursive content references with self-binding exceptions, audit/history exclusions, retained decision rationale and rebindings; frozen baseline and quantity-override projections |
| Compatibility | IR 1.0/1.1 behavior retained; the legacy unknown-version test now uses 99.0 because 1.2 is supported |

Results:

- Development installation: **280 passed**, zero failures or skips.
- Fresh installed wheel: **280 passed**, zero failures or skips.
- Includes **97 IR 1.2 tests**, 85 IR 1.1/schema-packaging tests, 80 IR 1.0
  tests, 12 persistence tests, and 6 CLI/project tests.
- All 12 IR 1.2 negative files match their recorded diagnostic codes and paths.
- Ruff lint and formatting checks PASS; dependency checks PASS.
- Installed CLI version and doctor checks PASS.

Reports: [development JUnit](phase-2-ir-1.2-tests.xml),
[installed-wheel JUnit](phase-2-ir-1.2-wheel-tests.xml),
[artifact and input hashes](phase-2-ir-1.2-artifacts.json).

Recorded verification commands, after loading `.env` into the process:

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-ir-1.2-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .tools/phase-2-ir12-dist
.venv/Scripts/python.exe -m venv .tools/phase-2-ir12-env
.tools/phase-2-ir12-env/Scripts/python.exe -m pip install -r requirements-ci.txt
.tools/phase-2-ir12-env/Scripts/python.exe -c "import pathlib, subprocess, sys; wheels = list(pathlib.Path('.tools/phase-2-ir12-dist').glob('*.whl')); assert len(wheels) == 1; subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', str(wheels[0])], check=True)"
.tools/phase-2-ir12-env/Scripts/python.exe -c "import partsmith.ir; from pathlib import Path; from importlib.resources import files; from partsmith.ir import SUPPORTED_VERSIONS; assert 'site-packages' in str(Path(partsmith.ir.__file__).resolve()); assert all(files('partsmith.ir').joinpath(f'component-ir-{v}.schema.json').read_bytes() == Path(f'schemas/component-ir-{v}.schema.json').read_bytes() for v in SUPPORTED_VERSIONS); assert files('partsmith.persistence').joinpath('001_initial.sql').is_file()"
.tools/phase-2-ir12-env/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-ir-1.2-wheel-tests.xml
.tools/phase-2-ir12-env/Scripts/python.exe -m pip check
.tools/phase-2-ir12-env/Scripts/partsmith.exe version
.tools/phase-2-ir12-env/Scripts/partsmith.exe doctor --json
```

Scope: the in-memory revision store and contexts are synthetic fixtures, not a
production persistence/review service. Phase 3 supplies production PDL declarations;
Phase 6 implements affine transform execution and CAD measurements; Phase 7 verifies
applicability against actual pinned features; Phases 8–9 implement orchestration,
final-byte validation, manifests, approvals, and complete-build reproducibility.
Phase 10 implements PDF/OCR coordinate conversion. This gate verifies their IR and
projection contracts, not those later-phase implementations or production geometry.
