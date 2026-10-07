# Phase 12.4 working increment

Initial assembly now registers a component identity, an unreviewed structural
IR root, retained source documents, exact acquisition identity and complete
inventory before permitting an evidence-only child proposal. Assembly reads
retained acquisition data and explicitly entered engineering sections. Missing
pins, mechanical facts, manufacturer and placement remain empty or null.
IR 1.2 permits these incomplete inspection records; generation explicitly
rejects them with `IR_INCOMPLETE`. Existing complete IR behavior is retained.

Explicit evidence assignments create newly identified derivative records;
original source evidence stays unchanged. Field provenance records link the
assigned interpretations and statuses. Typed proposals, approvals and rejection
use the existing InputReviewService and immutable store. Numeric JSON text uses
Decimal. Pin reorder and renumber use existing contracts; typed pin removal
adds explicit retirement and shifted-index bindings without rewriting historical
evidence. Every decision retains its exact base and audit history.

The Component Data tab exposes initial assembly, typed edits, evidence review,
separate input approval/rejection and explicit local PDL selection. PDL bindings
include ID, revision and content hash and recheck family, variant and topology.
Package labels never select a PDL. Unfinished form text and reasons are retained.

Current reviewer authority comes from the Windows process token SID (POSIX UID
on that platform), refreshed for every operation and after loading. Saved names
and provider/document actors have no authentication authority. Missing identity
blocks decisions while inspection and saving remain available. Input approval
does not approve a release.

Recorded checks before Phase 12.5: `phase-12.4-source-results.xml`, **309 passed**
on Python 3.12.10, including source IR 1.0/1.1/1.2 and existing review contracts,
actual wx assembly/input review, pure acquisition assembly without a fixture
IR, explicit assignment, exact Decimal overrides, real OS identity, missing
identity, rejection, PDL hashes and historical pin bindings.

Failure injection found that SQLite savepoint release can commit without an
outer transaction. Session connections now begin an explicit transaction, and
desktop pointers and review decisions write in that same transaction. The
rollback test verifies no approval or head advance survives a failed state write.

Full Phase 12 and installed-wheel/hash closeout remain open at milestone 12.10.
