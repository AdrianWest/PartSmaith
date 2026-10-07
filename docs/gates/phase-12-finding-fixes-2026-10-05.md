# Phase 12 finding corrections — 2026-10-05

Sequencing update under v0.9.7, 2026-10-05: the project owner explicitly assigns
the still-open R13-01 contracts to Phase 13.1. The current
[Phase 12 handoff](phase-12.md) permits entry to that milestone; installation
work depends on its contract/tests/hash PASS. See the
[specification revision](../spec-phase-13-review-v0.9.7.md). The original verdict
below describes v0.9.6 and is preserved unchanged in the archived report.

Result: **R12-01 and R12-02 resolved; scoped correction checks PASS.**
The overall Gate 12 handoff remains **FAIL** and Phase 13 **NOT READY** solely
because **R13-01**, the missing Phase 8 installation contracts, remains open.
This correction does not implement or waive that earlier prerequisite.

## R12-01: component identity stays bound to its ordering number

After assembly, **Required Part Number** is disabled and displays the immutable
component MPN. Event handling restores that value if an edit event attempts to
change it; Start rejects a bypassed text change before acquisition. Processing
another number uses **New / Clear Component**, whose existing transition
offers Save, Discard, or Cancel and creates a fresh isolated session.

Generation compares setup with the trusted immutable revision before creating
a build. Release approval and archive loading independently reject a mismatched
setup identity. An archive produced with the previously defective mismatched
setup is rejected; its original file and immutable component history remain
available. No identity or approval is silently reassigned.

Real wx callbacks cover the same PDF with two ordering numbers, edit/Start
bypasses, Cancel, Discard, successful Save, failed Save and cancelled Save.
They verify the old revision/history remains immutable, while a fresh session
has no old component, PDL or release binding. Service regressions verify that
mismatched generation creates no build and release/load refuse stale bindings.

## R12-02: committed outcomes survive recovery persistence failures

The action controller handles a successful service result separately from
later log/checkpoint persistence. It emits a warning for a recovery failure
and still emits success with the original result payload. Late cancellation
does not change the committed engineering status. The main wx status label
reflects that result after a late cancellation request.

Real authenticated input approvals are tested with log and checkpoint errors,
with and without late cancellation. Actual validated release approvals are
tested with failed checkpoints and both cancellation timings. Save/load retains
each exact decision and binding; retry cannot duplicate the input decision.
A checkpoint-only action still reports failed checkpoint creation while
preserving the engineering status. Save operation failures remain failures
and do not advance a component transition.

## Validation and scope

- Complete source regression: **778 passed**, zero failures/errors/skips;
  [XML](phase-12-finding-fixes-2026-10-05-source-results.xml),
  [transcript](phase-12-finding-fixes-2026-10-05-source-output.txt).
- Complete installed-wheel regression: **778 passed**, zero failures/errors/skips;
  [XML](phase-12-finding-fixes-2026-10-05-wheel-results.xml),
  [transcript](phase-12-finding-fixes-2026-10-05-wheel-output.txt).
- **101 package Python files** and **20 forced resources/plugin files**
  match source, wheel, sdist and installed bytes, including Banner3 and the
  launch-only KiCad plugin. See [package evidence](phase-12-finding-fixes-2026-10-05-package-evidence.json).
- Actual standalone source and installed main loops pass from an unrelated
  working directory, reopen the actual symbol/3D viewer and reap native children:
  [source](phase-12-finding-fixes-2026-10-05-source-launch.json),
  [installed](phase-12-finding-fixes-2026-10-05-wheel-launch.json).
- Ruff lint/format, all 50 new/modified Python files' tagged documentation
  (including the archived original probe),
  dependency consistency, doctor and whitespace checks pass;
  [quality checks](phase-12-finding-fixes-2026-10-05-quality-checks.json).
- All **19 active input maps**, including CI's Phase 5/6/8 manifests, are verified
  after final hash refresh. The Phase 10 custom source map is also checked.
  Current Gate 12 identities outside its input map are checked against exact
  files. The [receipt](phase-12-finding-fixes-2026-10-05.json) records paths,
  identities, counts, preserved snapshots and refreshed manifest scope.

Commands use Python 3.12.10 on Windows AMD64. Regression selection is `tests`
plus `scripts/verify_gui.py`, `scripts/verify_viewer_prototype.py`,
`scripts/verify_phase12.py` and `scripts/verify_phase11_review.py`. Source
imports prepend `src`, repository and `tests`; the installed run prepends only
repository and `tests` and asserts the package resolves under `site-packages`.
No live provider request was made. Native KiCad menu clicks, other-platform
desktop acceptance, remote CI and new PDF stability rounds are not claimed.
Earlier native-menu, screenshots and PDF stability evidence retain their scope.

## Hash closeout and remaining prerequisite

Original reports and every affected active manifest are preserved under
`docs/gates/history/`. Each refresh records its reason, scope and previous/new
hashes. Historical tests and wheel identities remain bound to their original
acceptance; refreshed active input maps describe this corrected checkout.
The original failed review and its probe observations are retained.

Verification command for each active map:

```text
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each active manifest> --source disk
```

The updater is invoked with `--source disk --update`; JSON is normalized to LF
before dependent hashing. Git-blob verification is due after the uncommitted
input changes are committed. No commit or remote CI result is claimed here.

R13-01 still requires versioned installation-plan, installation-manifest and
integration-authorization contracts assigned to Phase 8 item 10, §174.1 and
D095-01 in specification v0.9.6, followed by affected prerequisite validation.
See the [original finding](phase-12-readiness-review-2026-10-05.md#r13-01--p1-the-installation-contracts-assigned-to-phase-8-are-absent).
