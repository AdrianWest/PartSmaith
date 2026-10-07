# Phase 13.5 — exact authenticated installation decisions

PASS, 2026-10-07, after final native fixture evidence and affected-hash closeout.
Installation approval is separate from component input/release approval and
does not publish files.

The review service displays the frozen plan, historical source bindings, expected
base, final inventory, manifest/check identities and exact mechanical differences.
Inspection remains available when authentication is unavailable or the target
becomes stale. Blocking categories remain visible; inspection grants no authority.

Every deliberate decision requests a fresh AuthenticatedPrincipal from a trusted
live adapter. Production uses the current OS process token SID or POSIX UID. A
supplied reviewer must match that principal. Saved subjects, source release actors,
raw imported binding/audit objects and a matching manifest string cannot create
the trusted decision record.

Approval requires a persisted exact staged attempt, fresh complete source approval
resolution, actual native/semantic revalidation, reconstructed deterministic
checks/manifest and current selected target/root/base. Approval binds the exact
plan, installation manifest, all required pre-checks and separate post-check.
Actor, UTC time, reason and execution metadata remain in a separate immutable
audit. Rejection may record a plan without a completed stage and grants no
installation authority.

The service owns an idle-connection decision transaction and refuses to commit
unrelated caller work. A write/storage failure rolls back all pending authority.
Cancellation before commit records CANCELLED; cancellation after commit preserves
AUTHORIZED/REJECTED with a separate warning. Checkpoint/log failures cannot relabel
a durable decision. A simulated SQLite driver exception after its actual COMMIT
resolves the exact stored row and reports the real decision with a warning.
Exact retries retain one audit, actor/time/reason and authorization, including
canonical Unicode reasons. Rejection cannot be silently changed into approval.

Validation: `phase-13.5-final-source-results.xml` records 121 passing tests (23
review and 98 contract checks), with no failures, errors or skips. Cases cover
fresh OS authentication, exact retry/reopen, unauthenticated and wrong/stale
targets, missing/changed/failed checks, plan-only and unstaged approval, raw imports,
rejection, caller transactions, storage faults, before/after-commit exceptions,
cancellation during write and after commit, checkpoint failure and stale inspection.
The initial audit timestamp failure is retained separately; the final timestamp
uses the required UTC `Z` encoding without weakening the closed schema.

`scripts/verify_integration_review.py --approve-fixture` records the real native
stage, exact fresh OS-authenticated audit/binding, review view and independent
reopen/retry checks in `phase-13.5-native-review/`. Its copied application database
contains one decision. The original retained source database and every source
binding remain unchanged; no target library files are published.

Ruff lint/format pass. `scripts/close_integration_gate.py --phase 13.5` refreshes
all affected active/CI manifests and verifies native receipt identities outside
their input maps. Historical receipts remain scoped to their original execution.
Disk hashes describe these uncommitted bytes; Git-blob verification follows a
user commit. Full Phase 13 remains pending through publication/recovery/workflow
and final PCM acceptance in 13.6–13.8.
