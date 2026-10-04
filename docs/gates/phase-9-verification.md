# Phase 9 gate verification

Verified 2026-10-03 against specification v0.9.6 and the current working tree.

**Current verdict: PASS for the local Windows AMD64 working tree.**
The [Phase 9 gate report](phase-9.md) records the completed closeout below.

**Initial verdict: technical checks pass locally, but the recorded Phase 9 gate is
incomplete.** Do not treat the existing manifest's PASS as a fully verified
gate until its evidence integrity issues are resolved. Specification section
"Phase-gate policy" requires recorded commands, applicable artifact hashes,
and test results; failing or unrecorded checks are gate failures.

## Fresh checks

| Check | Result |
| --- | --- |
| Current source suite | 476 passed, no failures/errors/skips; 180.58 seconds |
| Separately installed recorded wheel suite | 476 passed, no failures/errors/skips; 179.24 seconds |
| Phase 9 cases included in each suite | 17 passed |
| Ruff lint | PASS |
| Ruff formatting | PASS; 94 files already formatted |
| Dependency consistency (`pip check`) | PASS |
| Doctor | PASS; Python 3.12.10, PartSmith 0.1.0, native KiCad CLI 10.0.6 |
| Recorded wheel identity | PASS; SHA-256 `af3ec2a76bf7a257dfa611791fe8af0c01eaa3ac99ed6e51dd313cb47f65cf60` |
| Wheel implementation versus current source | PASS; all 53 Python/runtime-lock files checked match exact bytes |
| Phase 9 evidence manifest | FAIL; 167 of 170 referenced files match, two hashes differ, one file is missing |

The installed-wheel run explicitly imported PartSmith from
`.tools/phase9/wheel-site/partsmith/__init__.py`. It used the existing pinned
dependency environment, rather than a new dependency installation. The source
and wheel suites both exercised independent clean subprocesses with hash seeds
11/97, imported two-revision offline replay, cache corruption, missing/tampered
closure, runtime/schema mismatch, and CAD/validator/placement/audit invalidation.
The offline test blocks Python socket/DNS operations; this is not an operating
system firewall guarantee for arbitrary subprocesses.

The existing [comparison evidence](phase-9-comparison.json) matches its recorded
hash. Its source clean-build comparison, installed-wheel clean-build comparison,
and source/wheel comparison all report PASS for input snapshots, dependencies,
artifact bytes, semantic validation, and engineering manifests. Its four offline
replays also report PASS. Fresh runs verified those behaviors through the suite;
the existing comparison JSON was not overwritten.

## Remaining evidence issues

**Resolved 2026-10-03:** The [Phase 9 gate report](phase-9.md) now exists,
README/CI hashes have been reconciled, and the exact-byte manifest verifier
passes. The initial findings below are retained as audit history. Fresh test
results are now also retained in the repository as
[source results](phase-9-verification-source-results.xml) and
[wheel results](phase-9-verification-wheel-results.xml). The current local
gate verdict is PASS; the initial incomplete verdict above describes the
state before this closeout.

1. `docs/gates/phase-9.md` does not exist, although
   `phase-9-artifacts.json` references and hashes it as the gate report.
2. `.github/workflows/ci.yml` differs from the recorded Phase 9 hash.
3. `README.md` differs from the recorded Phase 9 hash.

The manifest therefore fails the repository's exact-byte evidence verifier.
This verification report does not substitute for the missing report or alter
the existing PASS declaration. Complete the gate report with the actual
commands and scope, reconcile the changed files with verified evidence, then
rerun the manifest verifier. No implementation changes or historical evidence
rewrites were made during this verification.

Phase 9 implementation and evidence files are currently untracked, alongside
other existing working-tree changes. This assessment applies to this working
tree, not a committed release. No remote CI result or cross-platform artifact
identity was verified.

## Commands and fresh evidence

Commands used the existing project environment outside the execution sandbox,
which could not access its base Python installation. No environment repair
was required. Each test process set the native KiCad executable explicitly.

```powershell
$env:PARTSMITH_KICAD_CLI = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --junitxml=.tools/phase9-verification/source-results.xml
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m partsmith doctor --json
.\.venv\Scripts\python.exe scripts/verify_phase2_manifest.py --manifest docs/gates/phase-9-artifacts.json
# In a separate process for the installed-wheel run:
$env:PYTHONPATH = (Resolve-Path .tools/phase9/wheel-site).Path
.\.venv\Scripts\python.exe -c "import partsmith; print(partsmith.__file__)"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --junitxml=.tools/phase9-verification/wheel-results.xml
```

Fresh JUnit files are retained locally in `.tools/phase9-verification/`.
