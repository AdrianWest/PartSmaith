# Phase 13.1 — integration contracts and R13-01 closure

Result: **PASS**, 2026-10-06. **R13-01 is RESOLVED**. This checkpoint permits
13.2; the complete Phase 13 installation gate remains pending.

Scope: local Windows AMD64, Python 3.12.10, native KiCad 10.0.6 and the existing
reviewed CAD tuple. Source checks and a checkout-independent, offline PCM-layout
contract fixture are validated. This fixture is not an installed customer plugin
or evidence of its preparation/lifecycle/IPC behavior. No PartSmith wheel was
built, installed or tested.

The current Phase 12 handoff remains PASS in its recorded scope. R12-01/R12-02
correction evidence was reviewed and affected identity/decision/session checks
were rerun. The launch-only ActionPlugin, one-field legacy launcher, component
release/replay formats and session 1.0 remain distinct from these contracts.
Read-only [pinned target discovery](phase-13-discovery-2026-10-06.md) records
KiCad schemas, runtime and prospective IPC/publication capabilities; it claims
no 13.2 PASS.

Implemented `partsmith.integration` supplies frozen plan, installation manifest,
validation report, authorization binding, audit envelope and recovery journal
contracts with closed offline Draft 2020-12 schemas. Exact within/cross-object
validation separates engineering content from actor/time/session metadata,
resolves the acyclic hash graph, preserves unchanged STEP bytes and rejects
unsafe/colliding paths, undeclared operations, stale bindings and failed checks.
The resource policy is frozen at 1.0. See
[contract details](../integration-contracts.md).

Trusted release resolution rechecks original manifests, final artifacts,
validation and immutable approvals without writing component state. Export and
replay import preserve original engineering, approval and history bytes. The
rebuilt release still needs fresh release approval; unfinished sessions and
reviewed revisions cannot substitute for approved installation sources.

Validation commands use the repository Python 3.12 environment with `src` on
PYTHONPATH, without invoking an editable or release build backend:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
.venv/Scripts/python.exe -m pytest tests/test_integration_contracts.py tests/test_integration_sources.py tests/test_phase8_bundle.py tests/test_phase8_release_workflow.py tests/test_phase8_input_review.py tests/test_phase8_persistence.py tests/test_release_contracts.py tests/test_desktop_session.py tests/test_desktop_review.py tests/test_desktop_release.py tests/test_desktop_generation.py -q --junitxml=docs/gates/phase-13.1-final-source-results.xml
.venv/Scripts/python.exe scripts/verify_phase13_contracts.py --archive dist/phase13-contract-payload.zip --evidence docs/gates/phase-13.1-pcm-payload.json --junit docs/gates/phase-13.1-pcm-results.xml
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
```

The source regression passes with zero failures/errors/skips. The isolated
payload runs all 98 contract cases with networking disabled and asserts its
import/resource roots are inside the extracted payload. All package Python,
schema, migration, asset, PDL and launch-plugin resource bytes match their
declared source inventory. Two clean ZIP constructions have identical bytes.
Positive/negative/golden cases cover unknown/omitted fields, unsupported
versions, malformed digests, stale target/base/source/staged hashes,
case/Unicode/Windows aliases, duplicate identities, forbidden self-hashes,
cycles, complete removal, mandatory checks and audit/journal bindings.

Final identities and exact test counts are in
[phase-13.1-artifacts.json](phase-13.1-artifacts.json). Prior finding/specification
and active manifests are preserved under `history/`. The
[hash closeout](phase-13.1-hash-closeout-2026-10-06.json) records every affected
input and active-manifest change with old/new hashes and verifier results,
including all CI manifests. Historical tests/distributions retain their original
scope and identities. Hashes bind finalized uncommitted checkout bytes; Git-blob
verification is due once those changes are committed. No remote CI or other
platform acceptance is claimed.
