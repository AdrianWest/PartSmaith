# Phase 13.7 — project workflow and native round trips

The desktop Project Libraries page uses the same planning, staging, inspection,
review, publication, rollback and reconciliation services as headless callers.
Installation authority resides in an application-owned database outside
component sessions. Loaded sessions retain versioned object references only;
they require explicit source selection, a fresh plan and exact review.
Installation controls remain separate from input and component approvals.

The final supported target is Windows AMD64, CPython 3.12.10, KiCad 10.0.6,
official kicad-python 0.8.0 and the pinned PCM dependency closure. Customer entry
starts with PCM installation and the PCB Editor's anvil action. The PCM listing
uses the owner's unchanged PartSmith logo. The final package is
`dist/partsmith-0.1.9-pcm.zip`, SHA-256
`a52e0ce3ecbc12aec3a5a79c8c95327529a3b2903c5e6d118596d0e59749fca7`.
Source entry remains a contributor workflow. No PartSmith wheel was built or
installed for this milestone.

The owned actual project contains two approved components in one packed symbol
library, their installed footprints and project-relative STEP references.
`phase-13.7-native-final/` retains three actual publication chains: initial
shared-service installation, desktop update, and final desktop publication of
an independently approved native-compatible revision. The final manifest is
`5b0c7810cd2ab9ef9317edd25029d0ade266c952d5b892006f2c6bbcf749232e`;
its publication receipt is
`00dffc02447eb43cf43256d5e35acfcc69b63e5993372de9930e36769e409caf`.
The unchanged source binding and mapping remain exact. The saved board's
SHA-256 remains
`637069b6bbf1a01fb9f4c27e70d463ba5307a4a8f93350666f765c7a6220333e`,
including the user's simulated R1 placement edit. Original source database
bytes and approvals remain immutable; the revised source was created and
approved in a separate data-only session.

Native acceptance exposed a real issue: KiCad converts pin-name spaces to
underscores, documented in the
[KiCad 10 symbol editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html).
The earlier approved fixture named a pin `Revised terminal`; native schematic
refresh saved `Revised_terminal`. That mismatch was rejected by the new
round-trip check and is not passing final evidence. Staging now compares every
native-upgraded pin's unit/body, type, style, name, number, position, orientation
and length with the exact approved library. A native rewrite that changes these
fields fails `SEMANTIC_CHECK_FAILED`. Two actual native negative tests cover
spaces in names and numbers. The separately approved final revision uses
`Revised_terminal`; source bytes were never silently rewritten.

`phase-13.7-native-roundtrip-final/receipt.json` records isolated imports from the
actual PCM installation and its READY managed interpreter. Saved and relocated
projects both export actual native schematic SVG and board STEP. Both contain
two exact cached/installed symbols and six model solids with total volume
0.39 mm3. Separate screenshots show the relocated schematic and PCB reopening
in native editors. `phase-13.7-instance-comparison-relocated-019.json` compares
actual official live IPC records with both approved sources and the final
mapping, including pin/pad identities, placement, pad centers and local model
transforms. This evidence does not claim schematic IPC or PCB write support.

Supervised native checks exercised unsaved-work Cancel without losing the edit,
save/close followed by stale-base rejection, fresh replanning, separate exact
authorization and atomic publication. Loading the saved final session leaves
execution disabled and displays the need for a new plan/review. Disconnecting
the PCB Editor clears instance rows and invalidates project execution. Repeated
KiCad invocation followed by selecting another board produces IPC_WRONG_BOARD.
Native project data and durable publication records remain unchanged by these
read-only actions. The original user project was restored in KiCad afterward.

`phase-13.7-final-source-results.xml` contains 125 passing focused checks with
zero failures, errors or skips. Ruff lint and formatting pass. Historical 0.1.7
and 0.1.8 candidate evidence retains its original scope. Final full source,
isolated PCM, desktop and PDF regression acceptance belongs to 13.8. The
checkpoint is closed only after the recorded affected-manifest hash closeout.
