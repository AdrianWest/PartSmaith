# Phase 13 PCM-only build and validation update

Specification v0.9.7 addendum, 2026-10-05, requested by the project owner.
The [updated Phase 13](../resources/BFT_PartSmith_Implementation_Spec.md#phase-13--kicad-integration)
removes PartSmith wheel builds, wheel installation, wheel-specific test runs
and required wheel receipts. This supersedes the original Phase 13 review and
the first PCM correction's requirement to retain internal wheel validation.
The [pre-update specification](../resources/history/BFT_PartSmith_Implementation_Spec_v0.9.7_before_PCM_only_2026-10-05.md)
and affected input maps are preserved. The change updates requirements; no
Phase 13 implementation or milestone PASS is claimed.

## Replacement checks and sequencing

| Milestone | Required validation |
| --- | --- |
| 13.1 | Source contract/bundle/identity regressions plus isolated PCM contract-payload fixtures with exact schema/resource bytes and offline resolution; no complete installed plugin prerequisite |
| 13.2 | Retire the active CI wheel-build/reinstall/resource step and wheel-specific harness paths; build the deterministic PCM ZIP and prove its inventory, resources, actual runtime and PCM lifecycle |
| 13.7 | Standalone and PCM-installed user workflows without a checkout or PartSmith wheel installation |
| 13.8 | Relevant source regressions and final PCM payload/installed-runtime checks, exact resource identities, real KiCad use, negative/recovery cases and hash closeout |

Keep the engineering assertions and move their packaged-resource coverage to
PCM. In particular, validate schemas and offline references, migration SQL,
PDL/runtime locks, GUI assets and plugin registration/data through the payload
and installed runtime. No source-tree fallback may hide a missing packaged file.
Record the retired automation entry points and replacement commands at 13.2.

The complete PCM installer/runtime belongs to 13.2, so 13.1 uses an isolated
contract-only payload fixture in the intended layout. This preserves the
contract-first dependency order. R13-01 remains REASSIGNED_OPEN until those
13.1 source/payload checks and hash closeout pass. Final installed-runtime
regressions remain due at 13.8.

Third-party binary dependencies remain valid runtime inputs, including dependency
wheels used by KiCad's managed environment. The removed process is building and
testing a PartSmith wheel as the application release/acceptance artifact.
Earlier Phase 0–12 wheel evidence keeps its original hashes and acceptance scope.
The current workflow still contains the legacy wheel step; this specification
assigns its actual replacement to Phase 13.2 and does not claim it removed now.

## Closeout scope

This update changes documentation and current gate metadata only. Source code,
packaging configuration, CI execution and installed plugin data are unchanged.
No wheel is built or tested for this edit. Prior runtime results are preserved,
not rerun or relabelled as PCM acceptance. Structural/link/ownership checks,
unchanged runtime/resource identities, active and CI input maps, and explicit
current-gate artifact references are verified from final disk bytes.

See the [update receipt](gates/phase-13-pcm-only-spec-update-2026-10-05.json).
Git-blob verification remains due after committing the current inputs.
