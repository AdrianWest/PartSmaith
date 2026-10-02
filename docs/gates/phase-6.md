# Phase 6 — CadQuery 3D Backend Spike: PASS

Recorded 2026-09-27 on `Implment-phase-06` against specification v0.9.6.
This is local Windows verification; no remote GitHub Actions run is claimed.
The Phase 5 prerequisite remains satisfied.

## Delivered contract

| Requirement | Implemented and verified |
| --- | --- |
| Coordinate transform library | Section 92/150 `Placement`/`AffineTransform`: `to_affine`, `compose`, `invert`, `apply_point`, `apply_vector`, `apply_bbox`, `equivalent_within_tolerance`, `simple_placement_from_affine` |
| Transform rejection | Non-positive scale, singular inversion, frame mismatch, and genuine shear (nonrepresentable simple placement) all raise `UnsupportedTransformError` |
| CadQuery/OCP/OCCT backend | `partsmith.threed` builds CHIP_BODY + END_TERMINATIONS solids from PDL mechanical dimensions and reference features |
| STEP export | Deterministic, normalized STEP artifact from the 0402 IR/PDL fixture |
| STEP parsing/validation | Reparse via `cadquery.importers.importStep`; measure solid count, body dimensions, body center, and terminal anchor positions against PDL tolerances |
| Dependency projection | Snapshot-profile-1.2 `MODEL_3D` node hash covers package mechanical data, PDL mechanical/model_3d/reference_features, and CAD backend/runtime configuration |
| Association separation | Placement-only IR edits do not change the `MODEL_3D` dependency hash; they only change the separate association dependency hash |
| Determinism gate | Two STEP exports in separate fresh `python` processes produce byte-identical SHA-256, after documented metadata normalization is verified not to alter measured geometry |
| Packaging | Fresh wheel imports `partsmith.threed` and passes the complete test suite |

The bootstrap source and PDL are synthetic. This gate establishes the CadQuery
3D backend, deterministic STEP export, and the section 92/150 transform
library; it does not claim Phase 7 footprint-to-3D cross-validation, Phase 8
end-to-end orchestration, or production-package coverage.

## Nondeterministic OCCT metadata (normalized, not geometry)

OCCT's STEP writer embeds two fields that vary run-to-run and are not
geometry: the `FILE_NAME` creation timestamp, and per-export entity ID
counters (`PRODUCT`'s translator-version suffix and
`NEXT_ASSEMBLY_USAGE_OCCURRENCE`'s ID). `partsmith.threed.step_backend`
normalizes both to fixed, first-appearance-order values before returning
STEP bytes, then reparses the normalized bytes and confirms the measured
solid count is unchanged, so normalization cannot conceal a real geometry
difference.

## Results

- Source installation: **357 passed**, no failures or skips.
- Fresh installed wheel: **357 passed**, no failures or skips.
- Phase 6 transform-library tests: **16 passed**.
- Phase 6 3D-generation tests: **6 passed**.
- Ruff lint and format checks pass.
- `pip check` reports no broken requirements.
- Fresh wheel `partsmith-0.1.0-py3-none-any.whl` installs into an isolated
  Python 3.12.10 environment.
- Fresh installed `partsmith doctor --json` reports PASS for Python, package,
  and CLI availability.
- Generated artifact: `TEST-R-0402.step` (3 solids: 1 body + 2 terminations).
- Generated artifact SHA-256:
  `789ee84bd00e5fa7adfec322191eeb678f849c82b990b30a41f1bb51da839c92`.
- 3D dependency hash:
  `89fd56fe704f918f927ecc00006a50ccaee8f3e1e9668dc2615f18adb3b16283`.
- Separate association dependency hash (shared with Phase 5 footprint):
  `1f4f176f96b93f6a916801ea71ef75cdcb90b6e2e1342a63c4a1de766c3b27e3`.
- Determinism gate: two exports, two fresh processes, identical SHA-256 (see
  `phase-6-artifacts.json`).

Environment: Windows, Python 3.12.10, PartSmith 0.1.0, CadQuery 2.8.0,
cadquery-ocp 7.9.3.1.1, jsonschema 4.26.0, pytest 8.4.2, and Ruff 0.16.8.

## Evidence

- [Source JUnit report](phase-6-tests.xml)
- [Installed-wheel JUnit report](phase-6-wheel-tests.xml)
- [Artifact and input hashes](phase-6-artifacts.json)

## Verification commands

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-6-tests.xml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir <temporary-dist>
<fresh-env>/Scripts/python.exe -m pip install -r requirements-ci.txt
<fresh-env>/Scripts/python.exe -m pip install --no-deps <wheel>
<fresh-env>/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-6-wheel-tests.xml
<fresh-env>/Scripts/partsmith.exe doctor --json
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-6-artifacts.json
```

This PASS satisfies the Phase 6 prerequisite for the deterministic CadQuery
3D backend. It does not claim Phase 7 footprint-to-3D cross-validation,
Phase 8 end-to-end orchestration, or Phase 14 production-package coverage.
