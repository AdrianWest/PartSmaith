# Phase 12.8 — exact placement drafts

Offset/rotation editors preserve exact decimal semantics; mirrors use supported
explicit flags, while all XYZ scales remain visible and read only. Draft and
reviewed previews transform unchanged canonical STEP. Discard restores actual
reviewed values. Saved drafts bind the exact base revision/hash; stale editors
cannot submit against a later head. Unfinished editor text is also retained.

Explicit reasons/evidence create typed placement proposals through the existing
input-review service. Acceptance records immutable history, clears current
release state and requires a new generation/validation attempt. The existing
dependency declarations govern any canonical STEP reuse.

Source checks: 10 passed (`phase-12.8-source-results.xml`), including exact
decimal save/load, offset/height/rotation/mirror discrepancies, discard,
separate proposal/approval, invalid numbers and stale-base rejection. Later
desktop checks also preview/discard real native scene transforms. Authoritative
geometry and final-byte validators remain the release authority. Overall
Phase 12 remains open pending 12.10.
