# Gate audit through Phase 9

Reviewed 2026-10-03 against specification v0.9.6 and commit
`0b2fc25` (working tree initially clean).

This is the original audit of the pre-fix code. The
[Phase 8 revalidation](phase-8-revalidation.md) records subsequent corrections.
Phase 9 remains pending; its missing implementation is expected at this stage.

**Verdict: all gates through Phase 9 have not passed.** The repository records
historical PASS results through Phase 8. Phase 9 has no recorded PASS and a
fresh two-process comparison fails engineering-manifest byte determinism.
Current tests pass, but passing tests alone do not satisfy the specification's
phase-gate policy (specification lines 66–77).

## Phase assessment

| Phase | Recorded evidence | Current verification / qualification |
| --- | --- | --- |
| 0 | `phase-0.md`: PASS | Version, doctor, lint, formatting, dependency consistency, tests, and wheel build pass. CI defines Windows/Linux checks. A fresh checkout and fresh dependency environment were not recreated during this audit. |
| 1 | `phase-1.md`: PASS | Persistence tests pass, including foreign keys, migration idempotence, reopen, and project/component/build records. |
| 2 | `phase-2-v0.9.6.md`: PASS | IR 1.0/1.1/1.2 tests and projection/migration negatives pass. Its historical manifest no longer matches current source files; it is not current-code evidence. |
| 3 | `phase-3.md`: PASS | PDL schema, golden bindings, topology negatives, loader/versioning, and CLI tests pass. Historical source hashes do not match current HEAD. |
| 4 | `phase-4-artifacts.json`: PASS | Symbol determinism, structure, input validation, and dependency tests pass. Historical symbol/source/test hashes are stale; no separate `phase-4.md` exists. The JSON and JUnit evidence provide the recorded PASS. |
| 5 | `phase-5.md`: PASS | Footprint/pad/graphics/projection tests pass; manifest hashes match both current HEAD and disk. |
| 6 | `phase-6.md`: PASS | CAD, STEP, transform, and independent-process STEP tests pass; manifest hashes match HEAD and disk. |
| 7 | `phase-7.md`: PASS | Geometry fault, symmetry, applicability, and alignment tests pass. Committed manifest hashes match; four checkout JSON files have CRLF byte differences. |
| 8 | `phase-8.md`: PASS | Native KiCad 10.0.6 pipeline, approval/export negatives, immutable review, rollback, and bundle import tests pass. Committed hashes and rebuilt wheel match recorded evidence. Three checkout files have CRLF byte differences. Snapshot and offline-completeness contract gaps are described below. |
| 9 | No gate report, manifest, or dedicated test module | FAIL / incomplete: engineering manifests differ between clean processes; selective reuse and network-disabled imported-bundle replay are not established. |

## Blocking and incomplete requirements

1. **Engineering manifests contain build-specific validation IDs.**
   `src/partsmith/release/pipeline.py:470` prefixes result IDs with the random
   build ID, then line 535 puts these full results into the engineering manifest.
   The semantic hash correctly removes audit IDs, but manifest serialization does
   not. Two fresh processes with identical fixture bytes, the same stable
   component identity, pinned runtime, separate empty databases/work directories,
   and hash seeds 11/97 produced equal input snapshots, dependency hashes,
   artifact hashes, and semantic-validation hashes, but different manifests:

   - Build A: `f4ab88a39d5a907a3e440998104846385e519d462f66c1757ad35c8179f3ee01`
   - Build B: `80c2a3613e15b44cdfcada6edaf70502c30883d9788be37a11f66ce56251e4ab`

   The only 31 differing manifest fields were `/validation/results/<n>/id`.
   This directly fails Phase 9 and sections 166/188. Keep execution identities
   in audit records and serialize deterministic validation content in manifests.

2. **Selective reuse and whole-build configuration invalidation are incomplete.**
   `KnownGoodReleasePipeline.run` constructs default contexts and calls all
   three generators unconditionally (`pipeline.py:259–264`). There is no retained
   artifact lookup/action plan that proves reuse, nor a pipeline configuration
   interface exercising validator-only and CAD-only updates. Existing projection
   and silkscreen tests prove hash isolation/unchanged STEP bytes, not avoidance
   of unnecessary regeneration. Phase 9 requires complete graph tests for
   CAD-only, validator-only, placement-only, and audit-only changes.

3. **The revision bundle's OFFLINE_COMPLETE claim exceeds verified closure.**
   `release/bundle.py:77–170` exports IR ancestors and acquisition inventories
   and labels the result OFFLINE_COMPLETE. It does not materialize/verify source
   document bytes, PDL/profile/configuration/runtime replay objects, or the final
   release/report/approval objects listed in section 175. The bundle tests import
   history but do not rebuild it with network disabled. Implement and verify the
   declared replay closure before claiming offline completeness, then record the
   imported multi-revision replay comparison required by Phase 9.

4. **Phase 8's frozen snapshot does not implement the complete section 166 contract.**
   `pipeline.py:273–289` records the full IR hash and revision ID rather than the
   specified engineering-content projection. Consequently audit-only IR changes
   affect the snapshot. Its configuration lacks the full validator/rule runtime,
   OCCT/archive identities, release-profile content/hash, and explicit exporter
   settings. Python is a context default (`ThreeDContext.python_version =
   "3.12"`), rather than the actual interpreter version. The snapshot is also
   persisted after generation, contrary to the required freeze-before-generation
   order. These are specification compliance gaps despite the recorded Phase 8
   PASS and green tests; Phase 8 should be revalidated after correction.

## Evidence integrity and documentation

The verifier reports real committed-source drift for historical Phase 2/3/4
manifests. For example, Phase 4 records symbol hash `25e1017a...`, while the
current golden artifact and passing test use `1e68b04c...`. Preserve historical
evidence and add a current revalidation report rather than merely refreshing
hashes and assuming old results apply.

Phase 7/8 disk mismatches are checkout line-ending differences, confirmed using
`git ls-files --eol`; committed Git blobs match their manifests. Phase 8 affected
files are `scripts/setup_kicad.ps1`,
`schemas/phase8-contracts-1.0.schema.json`, and `migrations/002_phase8.sql`.
Do not change historical migration content. The CI verifier uses disk bytes,
so this checkout cannot pass that exact-byte check until it honors LF.

README development-status claims and the specification's introductory
implementation status lag the implemented Phase 8 code. CI verifies only
Phase 5/6/8 manifests; the local pre-push hook checks only Phase 5/6.
No remote CI run or real production component approval was verified here.

## Fresh validation results

- Editable/source suite: **452 passed**, zero failures/errors/skips, 51.46 seconds.
- Separately installed current wheel: **452 passed**, zero failures/errors/skips,
  47.90 seconds. The installed package import path was explicitly checked.
  This installation reused the existing pinned dependency environment; it was
  not a new fully isolated dependency installation.
- Ruff lint: PASS. Format check: PASS, 85 files.
- `pip check`: PASS. `partsmith version`: `0.1.0`.
- Doctor: PASS for Python 3.12.10, package, CLI, and native KiCad 10.0.6.
- Wheel build with the standard isolated backend: PASS; SHA-256
  `459a7558855baaabc2666fe14554d109f8a082f7792714ac1286af840f895cd1`,
  identical to the recorded Phase 8 wheel. An initial `--no-build-isolation`
  attempt lacked Hatchling; the standard build succeeded.
- Two clean build processes: input snapshot, all dependency hashes, all three
  artifact hashes, and validation semantics MATCH; engineering manifest FAIL.

Commands used the existing environment after loading `scripts/load-env.ps1`
without displaying its values:

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --junitxml=.tools/gate-audit/source-tests.xml
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m partsmith version
.venv/Scripts/python.exe -m partsmith doctor --json
# Each recorded artifact manifest was checked against disk;
# phases 3–8 were additionally checked against committed Git blobs.
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-8-artifacts.json --source git
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir .tools/gate-audit/dist
.venv/Scripts/python.exe -m pip install --no-deps --target .tools/gate-audit/wheel-site .tools/gate-audit/dist/partsmith-0.1.0-py3-none-any.whl
# With PYTHONPATH set to the absolute wheel-site path:
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --junitxml=.tools/gate-audit/wheel-tests.xml
# PYTHONHASHSEED=11 and 97 respectively:
.venv/Scripts/python.exe .tools/gate-audit/probe.py .tools/gate-audit/build-a
.venv/Scripts/python.exe .tools/gate-audit/probe.py .tools/gate-audit/build-b
```

Local generated evidence is under the ignored `.tools/gate-audit/` directory:
source/wheel JUnit XML, rebuilt wheel, probe script, two manifests/databases,
`comparison.json`, and `manifest-differences.json`. No implementation files,
historical reports/manifests, or approved artifact bytes were changed by this audit.
