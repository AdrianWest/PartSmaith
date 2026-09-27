# Phase 3 — Package Definition Library: PASS

Recorded 2026-09-26 on `Phase_03_Implmentation` against specification v0.9.6.
This is local Windows verification; no remote GitHub Actions run is claimed.
The prerequisite [Phase 2 PASS](phase-2-v0.9.6.md) remains unchanged.

## Delivered contract

| Requirement | Implemented and verified |
| --- | --- |
| PDL schema | Strict offline Draft 2020-12 PDL 1.0 schema with closed records for identity, mechanics, topology, terminal groups, pad shapes, reference features, observables, tolerances, sources, revision history, and the pinned release profile |
| Loader and versioning | Exact ID/revision loading, safe identifiers, deterministic listing, explicit revision selection when multiple versions exist, immutable canonical records, and SHA-256 content verification |
| Validation | Stable schema and topology diagnostics; peripheral/exposed/pin counts, terminal numbers and positions, side distribution, terminal-to-group bindings, globally unique shape IDs, dimensions, source references, complete/bijective symmetry terminal mappings, feature-applicability/observable-measurement-mode consistency, release profile, and content hashes |
| Resolution | Exact family/variant/terminal matching with deterministic not-found and ambiguous failures; no textual similarity fallback |
| Bootstrap entry | `synthetic-0402@1.0`, bound to `mvp-1@1.0` and the exact synthetic engineering source; `GOLD-0402-001` binds exact IR and PDL bytes |
| IR compatibility | Deterministic package family, variant, pin count, terminal number, side, and topology-index comparison |
| CLI | `partsmith pdl list`, `partsmith pdl inspect <pdl-id>`, and `partsmith pdl validate <pdl-id>` |
| Packaging | PDL schema, entry, and release profile included in the wheel and byte-compared with repository sources |

The bootstrap source and PDL are explicitly synthetic. They establish the Phase 3
loader, validation, and topology contract without claiming manufacturer authority.
Manufacturer-backed production entries for all eight variants remain Phase 14 work.

## Results

- Source installation: **324 passed**, no failures or skips.
- Fresh installed wheel: **324 passed**, no failures or skips.
- Phase 3 adds 32 PDL tests and 2 CLI tests.
- The invalid corpus covers unsupported versions, unknown/missing fields,
  contradictory dimensions, count and side mismatches, duplicate terminal/shape
  identities, bad group bindings, unresolved source/feature references, broken
  symmetry terminal mappings, absent-feature/measured-observable mismatches,
  stale profile hashes, and stale PDL hashes.
- The golden fixture binds the synthetic source file bytes, the Component IR
  bytes, the PDL bytes, and the release-profile bytes to one another.
- `load_release_profile` rejects malformed release-profile structure instead of
  raising an uncaught `KeyError`, and `list_pdls` rejects an installed entry
  whose filename disagrees with its declared id/revision.
- Ruff lint and formatting checks pass; package dependencies are consistent.
- The installed PDL schema, 0402 entry, and release profile match repository bytes.
- Installed `partsmith pdl validate synthetic-0402` reports PASS.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, jsonschema 4.26.0,
pytest 8.4.2, and Ruff 0.16.8.

Evidence:

- [Source JUnit report](phase-3-tests.xml)
- [Installed-wheel JUnit report](phase-3-wheel-tests.xml)
- [Artifact and input hashes](phase-3-artifacts.json)

Fresh wheel SHA-256:
`723d958d4da5e200cf61c49203e15e68131e6315784f5aab926ac795fe2c681e`.

Verification commands:

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-3-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir <temporary-dist>
<fresh-env>/Scripts/python.exe -m pip install -r requirements-ci.txt
<fresh-env>/Scripts/python.exe -m pip install --no-deps <wheel>
<fresh-env>/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-3-wheel-tests.xml
<fresh-env>/Scripts/partsmith.exe pdl validate synthetic-0402
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-3-artifacts.json
```

This PASS satisfies the Phase 4 prerequisite. It does not implement symbol,
footprint, or 3D generation, snapshot profile 1.2, production review services,
or manufacturer-backed release entries.