# Phase 8 — First Complete Deterministic Component: PASS

Recorded 2026-10-02 on `Implment-phase-8` against specification v0.9.6.
This is local Windows verification; no remote GitHub Actions run is claimed.
The Phase 7 prerequisite remains satisfied.

## Delivered contract

| Requirement | Implemented and verified |
| --- | --- |
| Persisted orchestration | Every build transition is validated and retained; review waiting uses an explicit INPUT or RELEASE stage |
| Immutable inputs | Exact IR revisions, acquisition inventories, reviewed heads, snapshots, and dependency hashes are persisted and rehashed |
| Independent generation | Symbol, preliminary footprint, and STEP are generated independently from the reviewed IR and pinned PDL |
| Final association | The portable STEP path and placement are attached only during final footprint construction |
| Final-byte validation | Symbol, finalized footprint, STEP, strict 3D checks, and footprint-to-3D checks run against released bytes |
| KiCad compatibility | The declared `10.x` target must pass the PartSmith headless KiCad-format parser adapter; the evidence does not claim a native `kicad-cli` run |
| Manifest ordering | Exact final hashes and validation semantics are frozen before the engineering manifest; post-manifest results remain separate |
| Human review | Authenticated approval and rejection are immutable and approval binds the snapshot, manifest, semantic results, final artifacts, and post-manifest report |
| Approved export | Only APPROVED builds export; every persisted byte and approval binding is rehashed before atomic publication |
| Invalidation | Silkscreen edits preserve STEP but invalidate footprint checks and approval; path changes invalidate snapshots, dependencies, manifests, and approval; invalid placement blocks review |
| Input review | Evidence, inventory, typed override, conflict resolution, exclusion, and stable-terminal reorder proposals use immutable events and stale-head rejection |
| Persistence safety | Review, approval, bundle import, and head changes use atomic SQLite transactions/savepoints with rollback tests |
| Portable bundles | History-complete revision and inventory closure round trips with path, hash, ancestry, identity, and tamper validation |

The compatibility gate uses the repository's explicit headless parser adapter
because `kicad-cli` is not installed in the verification environment. The
manifest records the target, adapter identity, format-validation status, and
the absence of a native KiCad CLI rather than representing syntax validation
as a native application run.

## Results

- Source installation: **447 passed**, no failures or skips.
- Fresh installed wheel: **447 passed**, no failures or skips.
- Focused Phase 8 suites: **47 passed**.
- Ruff lint and format checks pass.
- `pip check` reports no broken requirements.
- Fresh-wheel `partsmith doctor --json` reports PASS for Python, package, and
  CLI availability.
- Blocking results, stale approval bindings, changed final bytes, and
  post-approval tampering cannot become exported releases.
- Silkscreen-only, association-path, and placement changes exercise selective
  reuse and required invalidation.
- Stale review bases, immutable pending proposals, failed transaction rollback,
  incomplete bundles, and tampered parents or inventories fail explicitly.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, CadQuery 2.8.0,
jsonschema 4.26.0, pytest 8.4.2, and Ruff 0.16.8.

## Evidence

- [Source JUnit report](phase-8-tests.xml)
- [Installed-wheel JUnit report](phase-8-wheel-tests.xml)
- [Implementation, report, and wheel hashes](phase-8-artifacts.json)

## Verification commands

```powershell
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\python.exe -m pytest --junitxml=docs\gates\phase-8-tests.xml
.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir <temporary-dist>
<fresh-env>\Scripts\python.exe -m pip install -r requirements-ci.txt
<fresh-env>\Scripts\python.exe -m pip install --no-deps <wheel>
<fresh-env>\Scripts\python.exe -m pytest --junitxml=docs\gates\phase-8-wheel-tests.xml
<fresh-env>\Scripts\python.exe -m pip check
<fresh-env>\Scripts\partsmith.exe doctor --json
.venv\Scripts\python.exe scripts\verify_phase2_manifest.py --manifest docs\gates\phase-8-artifacts.json --source disk
```

This PASS satisfies the Phase 8 blocking gate. Phase 9 may begin; Phase 12
still owns the review UI, and Phase 13 still owns expanded installation and
project round-trip integration.
