# Phase 12.9 — final release review and recovery

The final review tab shows exact artifact/manifest bindings, retained validation
and post-manifest results, and blockers. Approval/rejection requires an explicit
reason and a freshly authenticated OS principal through `ReviewService`.
Input and release decisions remain separate atomic transactions.

Session transport retains the acquired source, complete extraction, AI results,
draft editor text, placement/camera state, proposals, immutable database history,
actual artifacts and native previews. Loading creates a fresh operational
instance, verifies CAS/database/canonical record hashes, current heads and
proposal/approval identities, and makes no provider or engineering decisions.
Changed artifacts or a forged saved approval label are rejected.

Save/Discard/Cancel precedes close, clear, source replacement and archive
selection. Busy close first cancels/reaps work, then applies unsaved policy.
Source-image decoding and metadata preparation occur outside the wx event
thread with bounded, coalesced display caches. Viewer closure during active
work defers display-state persistence until idle.

Source checks: 22 passed (`phase-12.9-desktop-results.xml`), including actual
native generation/preview, offline review/release/reload, forged approval and
artifact rejection, missing identity, separate release rejection, stale input
invalidation, legacy desktop/credential checks and unsaved policies. The final
expanded source/wheel suite and gate closeout are recorded in 12.10.
Overall Phase 12 remains open until that closeout.
