# Phase 2 Component IR: PASS

Recorded 2026-09-19 on `Phase-02-Development` against implementation
specification v0.9.3. Prerequisite: [Phase 1 PASS](phase-1.md); its 12
persistence tests were rerun successfully before Phase 2 implementation.

**Applicability after the v0.9.4 revision:** This PASS and the unchanged reports
below cover IR 1.0 only. IR 1.1 implementation and verification are recorded in
the separate [revised Phase 2 PASS](phase-2-ir-1.1.md).
See the [resolution register](../../resources/BFT_PartSmith_Implementation_Spec.md#246-consistency-resolution-register).

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, jsonschema 4.26.0,
pytest 8.4.2, Ruff 0.16.8. Development checks loaded the user's `.env` settings
and used its `.venv`; `.env` was not modified. The interpreter required
execution outside the sandbox to access its existing base Python.

## Work items and gate evidence

| Phase 2 work item | Implementation and checks |
| --- | --- |
| Normative Component IR schema | Complete Draft 2020-12 schema, version 1.0, all 15 required top-level domains, structured identity/pins/evidence/values/placement/overrides; checked against the meta-schema and included in the wheel |
| Canonical serialization | Sorted keys, exact decimal JSON, UTF-8/NFC/LF, normalized logical paths, significant array order; frozen expected bytes and round-trip tests |
| Schema validation | Strict types, required fields, supported schema version, unknown-field rejection, deterministic error codes/JSON Pointer paths, reference and basic dimensional/topology checks |
| Units/numbers | Exact mm/mil/inch/micrometer and degree conversions, source preservation, no implicit units or float rounding, bounded finite numbers, min/nominal/max consistency, caller-context independence |
| IR hashing | SHA-256 of the full normalized record; frozen expected digest, fresh-process/hash-seed equality, provenance/content change sensitivity |

The [IR contract](../../resources/BFT_PartSmith_Implementation_Spec.md#121-component-ir-json-schema-and-contract)
was integrated into normative section 121 in v0.9.3, making the Phase 2 choices
explicit requirements for that revision. The v0.9.4 revisions are not covered
by the results below. Schema validity does not
establish PDL support or grant production approval. Phase 3 has not started.

`test_phase_two_gate` checks the known-good synthetic 0402 fixture through
schema validation, unit normalization, canonical bytes, stable hash, and
reload. All 13 full negative fixtures fail with exactly their recorded code
and path. Additional tests cover malformed JSON, non-finite numbers, Unicode
collisions, numeric boundaries, provenance, status containment, path safety,
immutability, and independent-process determinism.

## Recorded commands

All commands below completed successfully. The wheel environment was newly
created for this phase and imports were verified to come from `site-packages`.

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-ci.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-tests.xml
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .tools/phase-2-dist
.venv/Scripts/python.exe -m venv .tools/phase-2-env
.tools/phase-2-env/Scripts/python.exe -m pip install -r requirements-ci.txt
.tools/phase-2-env/Scripts/python.exe -c "import pathlib, subprocess, sys; wheels = list(pathlib.Path('.tools/phase-2-dist').glob('*.whl')); assert len(wheels) == 1; subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', str(wheels[0])], check=True)"
.tools/phase-2-env/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-wheel-tests.xml
.tools/phase-2-env/Scripts/python.exe -m pip check
.tools/phase-2-env/Scripts/partsmith.exe version
.tools/phase-2-env/Scripts/partsmith.exe doctor --json
```

Results:

- Editable installation: **98 passed**, 0 failures, 0 skipped; 80 IR tests.
- Fresh installed wheel: **98 passed**, 0 failures, 0 skipped.
- Lint PASS; format PASS (20 files); dependency compatibility PASS.
- Version `0.1.0`; doctor PASS for Python, package, and CLI.
- Installed schema bytes equal repository schema bytes; both schema and
  migration 001 are present in the installed wheel.

Reports: [editable JUnit](phase-2-tests.xml),
[installed-wheel JUnit](phase-2-wheel-tests.xml),
[artifact hashes](phase-2-artifacts.json).

Known-good canonical IR SHA-256:
`7a90c2784528ee872a1ea206b34282104909c1b9020cf7da8ca9520871521868`

Tested wheel SHA-256:
`db78ed459c546ba860e9089475dbe7c04df8fc1ba591f08e6e58f3ba76ec0e21`

Hashes were recorded with Python `hashlib.sha256(path.read_bytes()).hexdigest()`;
the IR hash was also obtained through `ComponentIR.from_file(...).sha256`.

CI now checks the packaged schema and runs both persistence and IR tests
against the installed wheel on Windows and Ubuntu, retaining JUnit reports
and wheel artifacts. This is a recorded local PASS; no new remote CI run is
claimed.
