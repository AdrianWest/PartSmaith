# Phase 7 — 3D Validation and Cross-Validation: PASS

Recorded 2026-10-02 on `Implment-Phase-7` against specification v0.9.6.
This is local Windows verification; no remote GitHub Actions run is claimed.
The Phase 6 prerequisite remains satisfied.

## Delivered contract

| Requirement | Implemented and verified |
| --- | --- |
| STEP existence and parsing | `validate_step_file` distinguishes a missing file from malformed existing bytes; `validate_model_3d` reparses STEP through CadQuery/OCP |
| Unit scale and coordinates | Raw STEP SI length declarations are checked before OCCT normalization; all measured bounds must be finite |
| Dimensions and height | CLASS_A body and terminal length, width, and height are measured; body dimensions also compare against independent IR evidence normalized from every supported length unit |
| Mounting plane | Every required terminal must meet the declared PCB mounting plane within the package height tolerance; body penetration is rejected |
| Orientation and mirror | A scalene, non-collinear terminal constellation measures rotation and signed chirality; 90/180-degree and X/Y mirror artifacts fail their intended rules |
| Scale and offset | Inter-terminal distance ratios measure 2x/0.5x geometry scale; body/reference centers measure geometry shifts |
| Terminal identity | Scale-invariant distance signatures produce a deterministic assignment; incomplete or ambiguous assignments fail explicitly |
| Footprint ↔ 3D alignment | Exact pad/terminal inventory, transformed pad offsets, physical lead/pad overlap, clearance relationships, and pin-1 labels are checked |
| Symmetry | A separately declared 0402 180-degree symmetry passes with its complete terminal mapping and is not counted as detected fault coverage |
| Applicability | Exposed-pad non-applicability has null status and measurements, `NONE` mode, and an exact PDL ID/revision/hash/ABSENT-feature binding; stale bindings become applicable failures |
| Result contract | Every pinned required observable has exactly one strict IR 1.2 result; structural results have stable rule IDs and exact artifact hashes |
| API compatibility | Phase 6 `SolidMeasurement(center, size)` and `StepMeasurement(solids)` constructors remain supported with derived/default Phase 7 fields |
| Fault corpus | Committed offset, 90/180-degree rotation, X/Y mirror, 2x/0.5x scale, wrong-height, and wrong-unit STEP bytes regenerate deterministically |

The Phase 7 PDL subjects live under `fixtures/phase7/pdl`, not the packaged
production PDL root. Earlier Phase 3/5/6 PDL bytes, resolution behavior, golden
artifacts, and evidence remain unchanged.

## Results

- Source installation: **393 passed**, no failures or skips.
- Fresh installed wheel: **393 passed**, no failures or skips.
- Phase 7 3D suite: **38 passed**.
- Ruff lint and format checks pass.
- `pip check` reports no broken requirements.
- Fresh-wheel `partsmith doctor --json` reports PASS for Python, package, and
  CLI availability.
- Missing files, malformed STEP, missing/extra pads, swapped pin-1 labels, and
  stale applicability bindings fail explicitly.
- Oversized, PCB-penetrating, and floating terminal geometry fails explicitly.
- Position, orientation, height, and clearance have deterministic
  just-inside/just-outside tolerance tests.

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, CadQuery 2.8.0,
cadquery-ocp 7.9.3.1.1, jsonschema 4.26.0, pytest 8.4.2, and Ruff 0.16.8.

## Evidence

- [Source JUnit report](phase-7-tests.xml)
- [Installed-wheel JUnit report](phase-7-wheel-tests.xml)
- [Fixture, artifact, fault-rule, and input hashes](phase-7-artifacts.json)

## Verification commands

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pytest --junitxml=docs\gates\phase-7-tests.xml
.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir <temporary-dist>
<fresh-env>\Scripts\python.exe -m pip install -r requirements-ci.txt
<fresh-env>\Scripts\python.exe -m pip install --no-deps <wheel>
<fresh-env>\Scripts\python.exe -m pytest --junitxml=docs\gates\phase-7-wheel-tests.xml
<fresh-env>\Scripts\python.exe -m pip check
<fresh-env>\Scripts\partsmith.exe doctor --json
.venv\Scripts\python.exe scripts\verify_phase2_manifest.py --manifest docs\gates\phase-7-artifacts.json --source disk
```

This PASS satisfies the Phase 7 blocking gate. It does not claim Phase 8
orchestration, required-rule aggregation, final artifact association,
approval, packaging policy, or export.
