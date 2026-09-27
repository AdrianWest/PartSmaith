# Phase 5 — Deterministic Footprint Generation: PASS

Recorded 2026-09-27 on `Phase-05-Development` against specification v0.9.6.
This is local Windows verification; no remote GitHub Actions run is claimed.
The Phase 4 prerequisite remains satisfied.

## Delivered contract

| Requirement | Implemented and verified |
| --- | --- |
| Footprint interface | `FootprintGenerator`, `FootprintContext`, and deterministic concrete generator |
| 0402 land pattern | Synthetic `synthetic-0402@1.0` PDL groups become deterministic SMT pads |
| Native artifact | KiCad `.kicad_mod` s-expression with PartSmith generator metadata |
| Pad validation | Count, numbering, shape, dimensions, positions, and copper/paste/mask layers |
| Graphics validation | Courtyard bounds, fabrication rectangle, silkscreen reference/value, format markers, and provenance description |
| Provenance | PDL source records and IR evidence page references are projected and emitted in artifact metadata |
| Dependency projection | Snapshot profile 1.2 footprint geometry projection hashes consumed inputs only |
| CAD-only behavior | Generator, serializer, naming, Python, and unrelated 3D settings do not invalidate footprint geometry |
| Association separation | Symbol/pin and 3D association inputs use a separate dependency hash |
| Packaging | Fresh wheel imports the footprint package and passes the complete test suite |

The bootstrap source and PDL are synthetic. This gate establishes deterministic
0402 footprint generation and validation; it does not claim manufacturer-backed
production coverage or completion of all package variants in section 31.

## Results

- Source installation: **335 passed**, no failures or skips.
- Fresh installed wheel: **335 passed**, no failures or skips.
- Phase 5 footprint tests: **5 passed**.
- Ruff lint and format checks pass.
- `pip check` reports no broken requirements.
- Fresh wheel `partsmith-0.1.0-py3-none-any.whl` installs into an isolated
  Python 3.12.10 environment.
- Fresh installed `partsmith doctor --json` reports PASS for Python, package,
  and CLI availability.
- Generated artifact: `TEST-R-0402.kicad_mod`.
- Generated artifact SHA-256:
  `7d250cb886b21f3b40088cd884e3892bb585185ee05c718160a147b16077da54`.
- Footprint dependency hash:
  `ff16242f9605238d4b439744741773496b1a5e2723b26a7636c6b004342886e2`.
- Separate association dependency hash:
  `1f4f176f96b93f6a916801ea71ef75cdcb90b6e2e1342a63c4a1de766c3b27e3`.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, jsonschema 4.26.0,
pytest 8.4.2, and Ruff 0.16.8.

## Evidence

- [Source JUnit report](phase-5-tests.xml)
- [Installed-wheel JUnit report](phase-5-wheel-tests.xml)
- [Artifact and input hashes](phase-5-artifacts.json)

## Verification commands

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-5-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir <temporary-dist>
<fresh-env>/Scripts/python.exe -m pip install -r requirements-ci.txt
<fresh-env>/Scripts/python.exe -m pip install --no-deps <wheel>
<fresh-env>/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-5-wheel-tests.xml
<fresh-env>/Scripts/partsmith.exe doctor --json
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-5-artifacts.json
```

This PASS satisfies the Phase 6 prerequisite for the deterministic 0402
footprint bootstrap. It does not claim Phase 6 3D generation, Phase 7
cross-validation, or Phase 14 production-package coverage.
