# Gate 12 and Phase 13 readiness review â€” 2026-10-05

Correction update, 2026-10-05: **R12-01 and R12-02 are resolved** in the
[Phase 12 correction report](phase-12-finding-fixes-2026-10-05.md), with 778
source and 778 installed-wheel checks passing. **R13-01 remains open**;
Phase 13 is not ready. The review and probes below describe the earlier
implementation; their exact original report/manifest bytes are archived under
`docs/gates/history/` and their original test/wheel identities are retained.

Verdict: **Gate 12 revalidation FAIL; Phase 13 NOT READY.** The earlier
recorded PASS remains historical evidence. Two reproduced Phase 12 contract
violations and one missing earlier integration prerequisite prevent a current
handoff. This review changes evidence and gate status; it does not repair the
implementation or start Phase 13.

Scope: specification v0.9.6, the current uncommitted checkout based on
`4df84f6`, the packaged KiCad action plugin, and the current installed wheel.
Runtime: Windows AMD64, Python 3.12.10, wxPython 4.3.1, KiCad 10.0.6.
Existing user changes were preserved. No provider request was made.

## Blocking findings

### R12-01 â€” P1: another ordering number retains the previous reviewed component

At [app.py:963](../../src/partsmith/gui/app.py#L963), **Start** takes the current
part-number text and starts processing in the existing session. The text-change
handler at [app.py:416](../../src/partsmith/gui/app.py#L416) updates setup data
without replacing or invalidating the existing component/reviewed revision.
Start does not call the existing Save/Discard/Cancel transition policy.
The generation adapter at
[generation.py:89](../../src/partsmith/gui/generation.py#L89) checks the reviewed
head but does not compare its part identity with the changed setup request.

The real wx Start callback was exercised with a credential-free recording
worker. Starting `DIFFERENT-ORDERING-NUMBER` after reviewing `FULL-SUFFIX-R`
sent the new number to processing while retaining the old component ID,
reviewed revision and IR MPN. The unsaved-policy callback was never called;
after processing returned, generation was still enabled against the old PDL
and reviewed inputs. This reproduced in both source and installed code.

This violates the Phase 9.5 required-part-number contract and Phase 12's
new-component/unsaved-session policy. A different ordering number may identify
another package or pinout, so silently continuing with the former reviewed
component is unsafe engineering behavior.

Required correction: make a different ordering number an explicit component
transition with Save/Discard/Cancel and a fresh isolated acquisition/review
session, or prevent changing the bound identity until that transition is made.
Add a generation guard and real UI coverage for two ordering numbers from the
same datasheet, including Cancel and failed Save. Preserve the old history.

### R12-02 â€” P1: checkpoint failure reports a committed approval as cancelled

At [actions.py:114](../../src/partsmith/gui/actions.py#L114), an action can commit
successfully before recovery checkpointing at line 120. A checkpoint exception
enters the same handler as an operation failure at line 122. If cancellation
has arrived, that handler emits `cancelled` and persists `status=cancelled`,
even though the review transaction already committed.

The probe used the real `DesktopReview.decide_inputs` service and authenticated
OS principal. It committed an INPUT_APPROVE event and a new reviewed revision,
then requested cancellation and injected an OSError from checkpointing.
The immutable approval remained persisted, but the controller emitted
`outcome=cancelled`, discarded the successful result payload, and stored a
cancelled session status. Both source and installed code reproduced this.

This violates Phase 12's requirement to report the actual committed outcome
and keep late cancellation distinct from completed atomic decisions.

Required correction: report the successful committed operation independently
from a checkpoint/recovery warning. Preserve its result and engineering status;
do not turn a post-commit persistence problem into cancellation. Cover failed
checkpointing after input/release decisions, with and without late cancellation,
and verify that retry/recovery cannot duplicate decisions.

### R13-01 â€” P1: the installation contracts assigned to Phase 8 are absent

The specification's Phase 8 item 10 and
[section 174.1](../../resources/BFT_PartSmith_Implementation_Spec.md#1741-installation-aggregates-and-approval-boundaries)
assign versioned installation identities/schemas to Phase 8. The section
requires an integration plan, deterministic installation manifest, and separate
integration authorization; the D095-01 resolution explicitly places contracts
in Phase 8 and shared installation in Phase 13.

The complete schema/source inventory and
`schemas/phase8-contracts-1.0.schema.json` were checked. Its 19 definitions
include component release/review and bundle contracts, but no installation
plan, installation manifest, or integration authorization. The typed release
contracts and contract tests likewise do not implement those objects.
This is an omitted prerequisite, rather than the expected absence of Phase 13's
publisher or live IPC operations. Earlier Phase 8 receipts do not demonstrate
this numbered requirement.

Required correction: implement and validate the closed versioned contracts,
canonical identities, exact source/base/target bindings and separate audit
authorization, then revalidate the affected Phase 8 prerequisite and hashes.
Do not silently move this requirement to Phase 13 or treat component release
approval as authorization for packed-library bytes.

## Verification and plugin review

- Full current source regression: **763 passed**, zero failures/errors/skips;
  [XML](phase-12-readiness-review-2026-10-05-source-results.xml),
  [LF transcript](phase-12-readiness-review-2026-10-05-source-output.txt).
- Full current installed-wheel regression: **763 passed**, zero
  failures/errors/skips;
  [XML](phase-12-readiness-review-2026-10-05-wheel-results.xml),
  [LF transcript](phase-12-readiness-review-2026-10-05-wheel-output.txt).
- Both independent probes reproduced R12-01 and R12-02; probe-runner exit zero
  means observations were collected, not that the required behavior passed.
- All **17 active input hash maps**, including CI's Phase 5/6/8 maps, matched
  before the review changes. **39 path/SHA-256 identities outside the Gate 12
  input map** matched, including historical and current distributions/evidence.
- All **101 package Python files** matched source, current wheel and installed
  package. The packaged plugin matched its source. Banner3 matched source,
  wheel, sdist and installation.
- Actual standalone source and installed entries/main loops passed from an
  unrelated temporary working directory, inspecting the real retained symbol,
  footprint/model, reopening the viewer and reaping native children:
  [source](phase-12-readiness-review-2026-10-05-source-launch.json),
  [installed](phase-12-readiness-review-2026-10-05-wheel-launch.json).
- Ruff lint/format, dependency consistency, tagged documentation and
  `git diff --check` passed before review closeout; final results are recorded
  in the accompanying receipt.
- The earlier three PDF/desktop stability rounds each recorded 194 passing
  tests. Their manifest and all nine output/XML identities were verified.
  These are retained historical runs, not three new review runs.

The KiCad plugin is a launch-only ActionPlugin. It validates its configured
absolute interpreter path, removes embedded PYTHONHOME/PYTHONPATH, and launches
the external PartSmith GUI without importing its CAD runtime into KiCad.
The current suite exercises registration, launch arguments/environment and
installation. The recorded native KiCad menu/parent-child evidence was checked
and retained; this review does not claim another native menu click.
Live IPC and project/library installation remain Phase 13 deliverables.

The existing accepted normal/minimum-width symbol screenshots were inspected.
The viewer shows actual generated content and mapping. The acknowledged
reference/value/pin-label overlap is a pre-existing generated-symbol layout
issue; it remains a usability follow-up and is not presented as a new viewer
defect. The older unexplained PDF crash remains UNKNOWN, with its original
failure preserved. Remote CI and other-platform desktop acceptance are not
claimed by this review.

## Required handoff after corrections

Resolve R12-01/R12-02, deliver R13-01's earlier contracts, add the missing
negative checks, and rerun affected source/installed-wheel gates with final
hash closeout. A current recorded Gate 12 PASS is required before Phase 13
implementation under the phase-gate policy.

Phase 13 then owns the versioned adapter/capability boundary and explicit IPC
unit conversions; supported native CLI/IPC round trips; two approved components
in one packed symbol library; updating one without changing the other; exact
semantic preservation/relocation and immutable source bundles; stale-plan and
concurrent-base rejection; explicit integration authorization; dry run;
filesystem-specific atomic publication with locks/journals; crash recovery and
complete rollback. Sections 174.1 and 216â€“218 define the publication contract.
These expected Phase 13 deliverables are not counted as Gate 12 defects.

## Evidence and reproduction

- [Source observations](phase-12-readiness-review-2026-10-05-source-probes.json)
- [Installed observations](phase-12-readiness-review-2026-10-05-wheel-probes.json)
- [Independent probe runner](phase-12-readiness-review-2026-10-05-probes.py)
- [Review receipt](phase-12-readiness-review-2026-10-05.json)

Use the project Python 3.12 runtime:

```powershell
.tools/python/python.exe docs/gates/phase-12-readiness-review-2026-10-05-probes.py --output <new-source-observations.json>
.tools/python/python.exe docs/gates/phase-12-readiness-review-2026-10-05-probes.py --installed --output <new-wheel-observations.json>
.tools/python/python.exe -c "import sys;sys.path[:0]=['src','.','tests'];import pytest;raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','scripts/verify_phase11_review.py','-q','--tb=short','--junitxml=<new-source-results.xml>']))"
.tools/python/python.exe -c "import sys;sys.path[:0]=['.','tests'];import partsmith;assert 'site-packages' in partsmith.__file__;import pytest;raise SystemExit(pytest.main(['tests','scripts/verify_gui.py','scripts/verify_viewer_prototype.py','scripts/verify_phase12.py','scripts/verify_phase11_review.py','-q','--tb=short','--junitxml=<new-wheel-results.xml>']))"
.tools/python/python.exe -m ruff check .
.tools/python/python.exe -m ruff format --check .
.tools/python/python.exe -m pip check
.tools/python/python.exe .tools/check_phase12_docs.py
git diff --check
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <affected-manifest> --source disk --update
.tools/python/python.exe scripts/verify_phase2_manifest.py --manifest <each-active-manifest> --source disk
```

Final lint and format checks passed; all 49 new/modified Python files passed
the required tagged-documentation check.
Dependency consistency, doctor and `git diff --check` passed. All 18 active
maps, including the new review receipt and CI's Phase 5/6/8 maps, were verified
after refresh. The receipt records commands, hashes and results.

New evidence is stored with LF line endings for Git checkout parity. Original
raw test transcripts remain in `.tools/gate12-review-20261005/`.
The current reviewed implementation and distributions were left unchanged.
Earlier Gate 12 report/manifest bytes are archived under `docs/gates/history/`.
Current manifest refresh records the status/evidence changes and previous/new
hashes; it does not turn these reproduced defects into passing checks.
The checkout remains uncommitted, so Git-blob closeout verification remains due
after committing the implementation and evidence.
