# Phase 9 — Reproducible builds

**Gate: PASS**, verified 2026-10-03 against specification v0.9.6.
Scope: current working tree on local Windows AMD64, Python 3.12.10,
native KiCad CLI 10.0.6, CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1,
and OCCT 7.9.3.1. No remote CI or cross-platform byte identity is claimed.

## Required work and gate evidence

| Phase 9 requirement | Implementation and verified evidence |
| --- | --- |
| 1. Hash all required inputs | Frozen snapshots include engineering inputs, active provenance, PDL/profile content, configuration, and runtime identities; replay preflight verifies required object hashes before execution. |
| 2. Canonicalize structured inputs | Canonical JSON profile 1.0 and release projection profile 1.2 separate engineering content from execution/revision audit metadata; audit-only revision tests preserve deterministic hashes. |
| 3. Record generator/backend/runtime versions | Snapshots retain generator/validator/finalizer versions, actual Python identity, KiCad identity, CAD tuple, archive/content hashes, exporter settings, and the pinned dependency environment. Runtime mismatch fails before replay import. |
| 4. Implement dependency invalidation | Verified node cache and trusted scoped declarations reuse unchanged producers. CAD-only changes regenerate STEP and dependent association; validator-only changes revalidate without regenerating engineering files. Placement-only changes invalidate association/checks while preserving geometry. |
| 5. Rebuild identical fixtures | The source and installed-wheel suites each run two independent clean subprocesses with hash seeds 11 and 97, separate empty databases, and no inherited artifact cache. |
| 6. Compare hashes | Input-snapshot, artifact-byte, dependency, validation-semantics, and engineering-manifest hashes match. Run IDs/timestamps remain separate audit metadata. Geometry equivalence does not replace byte identity. |
| 7. Offline imported multi-revision replay and per-node invalidation | A verified OFFLINE_COMPLETE bundle retains two reviewed IR revisions and inventories, source bytes, schemas, runtime/configuration inputs, artifacts, manifests, and approval audit. Replay into an empty database verifies closure, rebuilds without cache, and compares hashes. Missing/tampered objects and runtime/schema mismatch fail before execution; replay does not inherit release approval. |

Implementation is in `release/pipeline.py`, `dependencies.py`,
`reproducibility.py`, `replay.py`, `runtime.py`, and IR projection support.
Tests in `test_phase9.py`, `test_phase9_failures.py`, and
`test_phase8_snapshot.py` exercise these contracts with the full suite.
The offline test denies Python socket connection and DNS operations; it does
not establish an operating system firewall boundary for arbitrary subprocesses.

## Verification results

- Current source: **476 passed**, no failures/errors/skips, 180.58 seconds.
- Separately installed recorded wheel: **476 passed**, no failures/errors/skips,
  179.24 seconds. Each suite includes all **17 Phase 9 cases**.
- Ruff lint and formatting: PASS; 94 files formatted.
- Dependency consistency: PASS. Doctor: PASS for Python, package, CLI,
  and native KiCad 10.0.6.
- Recorded wheel SHA-256:
  `af3ec2a76bf7a257dfa611791fe8af0c01eaa3ac99ed6e51dd313cb47f65cf60`.
  All 53 current Python/runtime-lock implementation files match its bytes.
  The wheel predates this documentation closeout; its packaged README metadata
  is historical. No runtime code changed during closeout.
- [Comparison evidence](phase-9-comparison.json): source clean builds,
  installed-wheel clean builds, source/wheel comparison, and all four offline
  replays PASS with every required deterministic hash equal.
- Repository input hashes: PASS using the exact-byte manifest verifier after
  resolving the findings in [the verification report](phase-9-verification.md).

The installed-wheel suite explicitly imported PartSmith from
`.tools/phase9/wheel-site/partsmith/__init__.py`. Both suites used the existing
pinned dependency environment, not a newly installed dependency environment.
The comparison JSON and original JUnit records are preserved. Fresh source
and wheel results from the verification are retained as
[source results](phase-9-verification-source-results.xml) and
[wheel results](phase-9-verification-wheel-results.xml).

## Commands

These commands were executed during verification. Python runs outside the
execution sandbox because the sandbox cannot access its base installation.
No environment repair was needed.

```powershell
$env:PARTSMITH_KICAD_CLI = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --junitxml=.tools/phase9-verification/source-results.xml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m partsmith doctor --json
# Separately installed wheel, in a separate process:
$env:PYTHONPATH = (Resolve-Path .tools/phase9/wheel-site).Path
.\.venv\Scripts\python.exe -c "import partsmith; print(partsmith.__file__)"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --junitxml=.tools/phase9-verification/wheel-results.xml
# Closeout evidence validation:
.\.venv\Scripts\python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-9-artifacts.json --source disk
.\.venv\Scripts\python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-8-artifacts.json --source disk
```

## Evidence closeout

Created the previously missing gate report and reconciled README and CI
workflow hashes against the verified working tree. README now describes
Phase 9 and distinguishes history-only revision bundles from full replay
bundles. The CI workflow retains the locally verified Phase 9 migrations,
replay schema, runtime-resource checks, and full source/wheel suites.
The Phase 8 manifest's shared README/CI references and stale hashes for its
existing historical/revalidation reports were reconciled as well. Those reports
were reviewed and retained without edits; their historical results remain
distinct from the fresh 476-test verification.
Previous Phase 8/9 manifests are archived under `docs/gates/history/`.

The closeout changes documentation and evidence only. The passing source/wheel
tests remain applicable because implementation, tests, schemas, fixtures,
runtime locks, and migrations are unchanged. Phase 9 is complete for the
stated local scope. Files remain in the working tree; this report does not
claim a commit, push, remote CI run, or production release.
