# Phase 2 — Component IR, specification v0.9.6: PASS

Recorded 2026-09-20. This is fresh local Windows verification of the unchanged
Phase 2 contract in [specification v0.9.6](../../resources/BFT_PartSmith_Implementation_Spec.md#phase-2--component-ir).
Prerequisite: [Phase 1 PASS](phase-1.md). The existing IR 1.2 implementation
satisfies this scope; no additional production code was needed. A formatting
failure in the IR documentation's Python example was corrected before the
successful source gate run.

| Phase 2 requirement | Implemented and verified |
| --- | --- |
| Component IR and migration | Strict IR 1.2 schema and immutable model; explicit 1.0→1.1→1.2 migration with retained source records and failure for missing supplied evidence |
| Canonical serialization | Canonical JSON profile 1.0, exact decimal numbers, normalized Unicode/paths, immutable copies, and independent-process hash-seed checks |
| Schema validation | Offline packaged schemas for IR 1.0/1.1/1.2; invalid fixtures match expected stable diagnostic codes and paths |
| Units and numeric normalization | Explicit units, exact conversion, precision/range limits, unresolved candidate quantities without fabricated values |
| IR hashing | Frozen whole-record hashes and snapshot-profile-1.1 dependency projections with content references and active decision bindings |
| Revised IR contract | Typed pin/placement overrides, candidate relevance independent of selection, immutable decision history, revision/inventory checks, applicability records, source-coordinate metadata, and real-cycle rejection |

Results:

- Source installation: **280 passed**, no failures or skips.
- Fresh wheel in a new isolated environment: **280 passed**, no failures or skips.
- Test coverage: 97 IR 1.2, 85 IR 1.1/schema-packaging, 80 IR 1.0,
  12 persistence, and 6 CLI/project tests.
- Ruff lint and formatting checks passed; dependency checks passed in both
  environments. Version and doctor commands passed in both environments.
- Wheel imports resolved to `site-packages`; all three packaged schemas and
  migration 001 matched repository bytes.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, pytest 8.4.2,
Ruff 0.16.8, and jsonschema 4.26.0. The existing `.env` was loaded into the
verification process without changing it or displaying its values. Access to
the existing base Python interpreter outside the workspace was approved.
Dependencies were installed from `requirements-ci.txt` into a new environment.
The Linux/Windows GitHub Actions workflow was not run remotely during this task.

Evidence:

- [Source JUnit report](phase-2-v0.9.6-tests.xml)
- [Installed-wheel JUnit report](phase-2-v0.9.6-wheel-tests.xml)
- [Input/artifact hashes and exact verification commands](phase-2-v0.9.6-artifacts.json)
- [Source checks log](phase-2-v0.9.6-source.log), including the corrected initial formatting failure
- [Wheel checks log](phase-2-v0.9.6-wheel.log)

The freshly built wheel is
`.tools/phase-2-v096/dist/partsmith-0.1.0-py3-none-any.whl`, SHA-256
`23bbc6ab98c4269f9908b1dd1c09b282a6d1c9505c60512b9b7e010460292976`.
Wheel selection used the sole file from a newly created build directory, with
no hardcoded package version in the installation command. Its isolated
environment is `.tools/phase-2-v096/env`.

The successful commands included:

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-v0.9.6-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m partsmith version
.venv/Scripts/python.exe -m partsmith doctor --json
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .tools/phase-2-v096/dist
.venv/Scripts/python.exe -m venv .tools/phase-2-v096/env
.tools/phase-2-v096/env/Scripts/python.exe -m pip install -r requirements-ci.txt
.tools/phase-2-v096/env/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-2-v0.9.6-wheel-tests.xml
.tools/phase-2-v096/env/Scripts/python.exe -m pip check
.tools/phase-2-v096/env/Scripts/partsmith.exe version
.tools/phase-2-v096/env/Scripts/partsmith.exe doctor --json
```

The command inventory includes the resolved wheel installation and exact
resource-verification code. Earlier [IR 1.0](phase-2.md),
[IR 1.1](phase-2-ir-1.1.md), and [IR 1.2/v0.9.5](phase-2-ir-1.2.md) reports,
schemas, fixtures, and golden hashes retain their original scope and contents.

This PASS satisfies the Phase 3 prerequisite. It does not claim Phase 3 PDL
implementation, snapshot profile 1.2, production review/persistence services,
CAD generation, or release readiness. Specification v0.9.6 assigns profile 1.2
to Phases 4–6 and 8–9. Phase 2 uses synthetic requirements/revision fixtures
and verifies the IR contracts, not later production adapters.
