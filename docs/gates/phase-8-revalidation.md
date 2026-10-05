# Phase 8 revalidation — 2026-10-03

This revalidation addresses the Phase 8 findings from the
[pre-fix audit](audit-through-phase-9.md). It uses specification v0.9.6,
Python 3.12.10, KiCad CLI 10.0.6, CadQuery 2.8.0, cadquery-ocp 7.9.3.1.1,
and OCCT 7.9.3.1 on Windows AMD64. Phase 9 remains pending.

## Corrections

- The pipeline validates engineering inputs and freezes the full profile 1.2
  input projection and generator/association dependency hashes before invoking
  any generator. Generated dependencies must match the frozen declarations.
- Snapshots retain projected active provenance and decision content, exact PDL
  and release-profile content/hashes, actual Python patch/build/executable
  identity, KiCad CLI identity, CAD tuple/archive/file hashes, installed pinned
  dependency versions, generator configuration, validator/rule versions and
  tolerances, finalizer/manifest versions, and explicit STEP exporter settings.
  Full IR hashes and revision identities remain in separate persistence records.
- The original profile 1.1 API and golden hashes are preserved. Profile 1.2
  uses the same tested content-reference/history edge rules and additionally
  retains the active provenance objects needed to inspect the frozen inputs.
- Deterministic manifests contain projected identity/provenance/decision content
  and validation semantics without execution IDs. Persisted validation results
  and post-manifest reports retain truthful build identities outside manifests.
- Forward migration 003 allows multiple immutable build bindings to identical
  snapshot/manifest hashes. Migration 001/002 content is preserved, and a
  populated-database test proves historical snapshot/manifest bytes survive.
- Revision/inventory bundles are explicitly RETRIEVAL_REQUIRED. Import preserves
  this status and rejects unsupported OFFLINE_COMPLETE claims before publication.
  History closure still imports transactionally. Verified full replay hydration
  and network-disabled rebuilds remain Phase 9 work.

## Python and KiCad boundary

PartSmith remains standardized on its supported Python 3.12.x baseline and
the pinned native KiCad CLI 10.0.6. The locally installed Windows KiCad 10.0.6
actually embeds Python 3.11.5, as verified by its `bin/python.exe --version`.
PartSmith does not import its Python bindings or use that embedded interpreter.
Using KiCad's bundled interpreter would require a separate compatibility and
dependency migration; the existing Python 3.12 code/dependencies are preserved.

The packaged runtime lock includes exact PyPI CAD wheel SHA-256 values for
Windows AMD64 and Linux x86_64. Before release generation it verifies installed
versions, wheel-content file hashes, license identities, and OCCT version.
Executable paths are not deterministic snapshot content.

## Verification

- Full source suite: **459 passed**, no failures/errors/skips.
- Full separately installed current wheel: **459 passed**, no failures/errors/skips.
  It uses the existing pinned dependency environment, not a new dependency
  installation. Import location and packaged migration/runtime resources are
  checked explicitly against repository bytes.
- Source snapshot/pipeline regressions repeated after LF normalization:
  **7 passed**. LF normalization changes physical checkout bytes to the
  repository's committed text convention, not engineering values or SQL logic.
- Ruff lint and format checks, `pip check`, and `partsmith doctor --json`: PASS.
- Two fresh processes, separate empty databases/work directories, identical
  canonical fixture/component identity, no generated-artifact cache, and Python
  hash seeds 11/97: input snapshots, all dependencies, all three artifact hashes,
  semantic validation hashes, and engineering manifest hashes MATCH.
- Same-database repeated builds and an audit-only reviewed child revision also
  preserve deterministic content while retaining distinct build/report IDs.
- Runtime version drift, modified CAD bytes, unsupported offline-completeness
  claims, stale release bindings, changed artifact bytes, and blocking validation
  are covered by negative tests.

Evidence:

- [Source JUnit](phase-8-revalidation-tests.xml)
- [Installed-wheel JUnit](phase-8-revalidation-wheel-tests.xml)
- [LF source regressions](phase-8-revalidation-lf-tests.xml)
- [Independent-build comparison](phase-8-revalidation-comparison.json)
- [Current hashes, wheel identity, and commands](phase-8-artifacts.json)

Original Phase 8 reports remain historical. The archived artifact manifests and
revalidation metadata distinguish previous evidence from newly verified inputs.
The Phase 6/7 hash manifests are refreshed because explicit STEP defaults changed
its adapter source; its golden STEP bytes and existing CAD gate tests still pass.
No remote Windows/Linux GitHub Actions run is claimed. This report verifies the
Phase 8 corrections and does not claim completion of the Phase 9 dependency
reuse/offline replay gate or production package coverage.
