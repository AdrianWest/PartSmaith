# Phase 13 — KiCad integration

PASS, 2026-10-07, on the declared Windows target, after all eight ordered
milestones and final affected-hash closeout. [13.8](phase-13.8.md) records the
complete acceptance: 1,104 source tests, 14 source desktop tests, 1,118 isolated
PCM tests, 98 offline contract tests and three 194-test stability rounds,
without failures, errors or skips. All 33 active hash maps verify.

PartSmith installs through KiCad PCM and opens from the PCB Editor's anvil
action. The declared target is Windows AMD64, external CPython 3.12.10 and
KiCad 10.0.6 with official kicad-python 0.8.0. The final package is
`dist/partsmith-0.1.9-pcm.zip`; the package manager listing uses the owner's
unchanged `PartSmith_Logo_64x64.png`. Customer use does not require a repository
checkout, PartSmith wheel or customer pip commands.

| Numbered work item | Implementation and retained acceptance |
| --- | --- |
| 1. Deliver versioned installation contracts | [13.1](phase-13.1.md): closed schema/types and canonical/golden/negative fixtures |
| 2. Preserve source bundles and close R13-01 | [13.1](phase-13.1.md), [13.3](phase-13.3.md) and final regressions: immutable approved-source resolution, bundle/history preservation and affected Phase 8/12 checks |
| 3. Extend the pinned KiCad adapter | [13.2](phase-13.2.md), [13.4](phase-13.4.md) and [13.7](phase-13.7.md): exact KiCad/SDK locks, bounded native validation and actual official PCB IPC |
| 4. Implement PCM registration/runtime/lifecycle and retire wheels | [13.2](phase-13.2.md) and [13.8](phase-13.8.md): deterministic ZIP, schema/resource identities, actual managed preparation/recovery and lifecycle, source/PCM verification |
| 5. Plan and persist immutable integration | [13.3](phase-13.3.md): dry run, bounded target inventory, complete approved sources, conflicts and independent integration store |
| 6. Stage and validate exact semantics | [13.4](phase-13.4.md), final native pin guard in [13.7](phase-13.7.md): packed symbols, footprints/STEP references, deterministic checks/manifest and actual native SVG/STEP validation |
| 7. Authorize, publish, reconcile and roll back complete generations | [13.5](phase-13.5.md) and [13.6](phase-13.6.md): fresh exact OS-authenticated decisions, exclusive lock, complete project slots, one NTFS junction switch, real process-crash recovery and fresh rollback |
| 8. Integrate deliberate desktop/headless operations | [13.7](phase-13.7.md): project controls, data-only saved references, separate component approval, safe Cancel/disconnect/context invalidation |
| 9. Prove usability and close regressions/evidence | [13.7](phase-13.7.md) and [13.8](phase-13.8.md): actual two-component update, native saved/relocated projects, official IPC comparison, full source/PCM/desktop and repeated PDF tests, final lifecycle and affected active/CI/outside-map identities |

Two approved components are usable in one installed packed symbol library.
The final approved update changes one component while preserving the other
complete engineering content, source binding and mapping. Original component
database bytes and release approvals remain immutable. Installation authority
is separate from component approval and from saved sessions.

The final installed manifest is
`5b0c7810cd2ab9ef9317edd25029d0ade266c952d5b892006f2c6bbcf749232e`;
its publication receipt is
`00dffc02447eb43cf43256d5e35acfcc69b63e5993372de9930e36769e409caf`.
Saved board edits survive publication. Native schematic/PCB reopening and
relocation work with project-relative libraries and models. Actual official
IPC records match both approved sources and the declared final mappings.
Unsaved-work Cancel, session load, disconnect and wrong-board cases preserve
user data and invalidate execution.

Publication requires an explicitly registered project copy on fixed local
NTFS, exclusive use, saved/closed PCB and schematic editors, and fresh exact
review. The manager can remain open. PartSmith never discards or silently saves
editor changes. Process-crash recovery is proven; power-loss durability and
external writers that ignore the exclusive-use contract are not advertised.
Global-library mutation, schematic IPC and PCB writes are not offered.

The full gate receipt is `phase-13-artifacts.json`; ordered checkpoint receipts
retain their original execution scope. `phase-13-hash-closeout.json` records
final active/CI input verification and outside-map identities. Earlier candidate
failures and historical Phase 0–12 evidence are preserved. Source/PCM automated
checks and separately supervised native desktop evidence are distinguished in
[13.8](phase-13.8.md). Production clean/offline installation remains Phase 14.
