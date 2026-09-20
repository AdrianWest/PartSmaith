# Revised Phase 2 — Component IR 1.1: PASS

Recorded 2026-09-19 on `Phase-02-Development`, against specification v0.9.4,
section 121. This is local Windows evidence. The updated Linux/Windows GitHub
Actions workflow has not been run remotely during this task.

Prerequisite: [Phase 1 PASS](phase-1.md); all 12 persistence tests pass in both
installations. The [original IR 1.0 gate](phase-2.md), its JUnit reports, schema,
fixtures, and frozen hashes remain preserved. This revised PASS completes the
Phase 2 alignment required before Phase 3. Phase 3 has not started.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, jsonschema 4.26.0,
pytest 8.4.2, Ruff 0.16.8. Checks loaded the existing `.env` and used its `.venv`;
`.env` was not modified. Python required execution outside the sandbox to access
the existing base interpreter. The installed-wheel check used a fresh virtual
environment and verified imports came from `site-packages`.

| Phase 2 requirement | Implemented and checked |
| --- | --- |
| Versioned schema | Strict Draft 2020-12 IR 1.1 schema; 16 root domains including resolutions; both supported schemas validate against the meta-schema and load offline |
| Candidate quantities | Explicit null values/units and reasons; no fabricated numbers; exact known-unit conversion; contradictory normalization/bounds rejected |
| Active provenance | Required input closure includes referenced evidence, standards, approved overrides and resolutions; unresolved inactive history remains stored and hashed |
| Generation requirements | Versioned adapter context required; empty/incomplete declarations rejected; leaf paths cannot bypass value status; optional-zero declarations cannot waive physical body dimensions |
| Identity and enums | Document/revision agreement, hash-based unversioned identity, canonical electrical and land-pattern enums, convention-1.1 placement records |
| Structured evidence | Standards metadata and retained evidence; translations retain original text; dangling references and dependency cycles rejected |
| Explicit migration | New immutable record and canonical history; missing placement/revision/source-category evidence blocks migration; original data preserved |
| Canonicalization and hashing | Existing profile 1.0; frozen IR 1.1 canonical bytes/hash; round-trip and independent-process/hash-seed checks; old hashes preserved |
| Packaging and CI | Both schemas included in the wheel and byte-compared with repository files; CI runs the full suite against the installed wheel |

Results:

- Development installation: **182 passed**, zero failures or skips.
- Fresh installed wheel: **182 passed**, zero failures or skips.
- Includes 84 IR 1.1 tests, 80 IR 1.0 regressions, 12 persistence tests, and 6
  CLI/project tests. All 12 full IR 1.1 negative fixtures fail with their exact
  recorded rule/path; the original 13 negative fixtures also continue to pass.
- Ruff lint and formatting checks PASS; dependency checks PASS.
- Installed CLI version and doctor checks PASS.

Reports: [development JUnit](phase-2-ir-1.1-tests.xml),
[installed-wheel JUnit](phase-2-ir-1.1-wheel-tests.xml),
[artifact and input hashes](phase-2-ir-1.1-artifacts.json).

Recorded commands (after loading `.env`):

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-ir-1.1-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .tools/phase-2-ir11-dist
.venv/Scripts/python.exe -m venv .tools/phase-2-ir11-env
.tools/phase-2-ir11-env/Scripts/python.exe -m pip install -r requirements-ci.txt
.tools/phase-2-ir11-env/Scripts/python.exe -c "import pathlib, subprocess, sys; wheels = list(pathlib.Path('.tools/phase-2-ir11-dist').glob('*.whl')); assert len(wheels) == 1; subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', str(wheels[0])], check=True)"
.tools/phase-2-ir11-env/Scripts/python.exe -c "import partsmith.ir; from pathlib import Path; from importlib.resources import files; from partsmith.ir import SUPPORTED_VERSIONS; assert 'site-packages' in str(Path(partsmith.ir.__file__).resolve()); assert all(files('partsmith.ir').joinpath(f'component-ir-{v}.schema.json').read_bytes() == Path(f'schemas/component-ir-{v}.schema.json').read_bytes() for v in SUPPORTED_VERSIONS)"
.tools/phase-2-ir11-env/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-ir-1.1-wheel-tests.xml
.tools/phase-2-ir11-env/Scripts/python.exe -m pip check
.tools/phase-2-ir11-env/Scripts/partsmith.exe version
.tools/phase-2-ir11-env/Scripts/partsmith.exe doctor --json
```

The synthetic contexts and fixtures do not establish production PDL support,
physical accuracy, KiCad compatibility, or approval. Actual transforms,
generator-specific contexts, frozen build snapshots/dependency projections,
artifact validation and approval services remain in their specified later
phases. This gate validates whole-record hashes, not later build cache hashes.
