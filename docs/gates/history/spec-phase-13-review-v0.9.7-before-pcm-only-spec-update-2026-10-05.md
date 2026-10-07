# Phase 13 specification, plugin and data review — v0.9.7

Reviewed and revised 2026-10-05 at the project/specification owner's request.
The subsequent [PCM installation correction](spec-phase-13-pcm-installation-update-2026-10-05.md)
updates 13.2/13.7/13.8 and runtime configuration: the customer artifact is a
KiCad PCM ZIP, with actual package lifecycle acceptance. This original review's
tests and implementation observations retain their recorded scope.
The [current specification](../resources/BFT_PartSmith_Implementation_Spec.md)
now assigns the R13-01 contracts and their closure checks to **Phase 13.1**,
followed by seven integration milestones. The previous full specification is
[preserved](../resources/history/BFT_PartSmith_Implementation_Spec_v0.9.6_before_Phase13_2026-10-05.md).

**Current sequencing result:** Phase 12's two implementation findings remain
resolved. R13-01 is **REASSIGNED_OPEN**, an explicit first Phase 13 deliverable.
It no longer blocks entry to 13.1 under v0.9.7; it must be implemented, tested
and hash-closed before installation-dependent milestones proceed. The current
Gate 12 handoff is PASS within its recorded Windows AMD64 scope; Phase 13 is
NOT_STARTED. This revision does not declare the missing contracts implemented.

## Review scope and actual implementation

The review covers the numbered phase plan through Phase 13, its gate policy,
runtime/API boundaries, installation/bundle contracts and publication rules.
It examines the launch plugin/installer, native KiCad adapter, packaged schemas,
release/bundle contracts, desktop transport and current evidence. Core sources
and installed plugin data were read; no user project or live connection was
modified. No provider call or KiCad IPC operation was made.

| Surface | Verified current behavior | Phase 13 obligation |
| --- | --- | --- |
| [KiCad entry](../integrations/kicad/partsmith_setup/__init__.py) | Legacy `pcbnew.ActionPlugin` registration; fixed external `python -m partsmith.gui` argument vector; strips embedded Python path overrides; source/installed plugin bytes match | Version-tested launch/IPC action boundary; supported runtime and registration metadata; clear launch failures |
| [Plugin installer](../src/partsmith/gui/install_kicad.py) | Copies owned launch files/resources and writes a one-field `launcher.json`; CLI runs under Python 3.12 | Versioned launcher schema and explicit legacy compatibility; selected runtime verification, safe install/update/removal |
| Installed launcher data | Only `python`; absolute existing `.venv/Scripts/python.exe`; no version or target/approval/session fields | Keep legacy data launch-only; introduce closed `partsmith-launcher-1.0` separately from KiCad IPC `plugin.json` |
| [Native adapter](../src/partsmith/kicad/runtime.py) | Pins 10.0.6; native symbol/footprint parse/upgrade/render checks; bounded process calls | Recorded CLI/IPC capability/units matrix, complete installation/reference checks and real project round trips |
| IPC environment | Installed 10.0.6 CLI help lists no `api-server`; official `kicad-python` distribution is absent from the reviewed environment | Pin released bindings and test a real PCB Editor session, instance/board identity, disconnect and transient token handling |
| [Phase 8 schema](../schemas/phase8-contracts-1.0.schema.json) and [types](../src/partsmith/release/contracts.py) | 19 definitions for existing review/release/bundle contracts; engineering manifest 2.0 and audit/bundle contracts 1.0; no installation objects | Dedicated offline integration schema/types, deterministic identities and cross-object checks in 13.1 |
| [Revision bundles](../src/partsmith/release/bundle.py) | Verified history/inventory closure, exact object bytes and transactional import; revision-only bundles remain RETRIEVAL_REQUIRED | Resolve complete approved final releases before installation; verify original source bytes/approvals remain unchanged |
| [Desktop transport](../src/partsmith/gui/session-index-1.0.schema.json) | `partsmith-session-1.0` stores unfinished component work and verified DB/assets; strict state-field inventory has no integration field | Explicit transport extension/migration for integration references; no saved token, live authority or rewind of installed generation |
| [Phase 12 corrections](gates/phase-12-finding-fixes-2026-10-05.md) | Bound component MPN and actual committed outcomes have passing source/wheel regressions | Carry those same identity, cancellation and recovery rules into installation services |

The installed plugin Python bytes match the source SHA-256
`c2d83596eac735dea5999aa66b1fdb111955ece8f981b6cba9b6872967a189e5`.
Its external runtime location is audit metadata, not an engineering identity.
The receipt records the local configuration observation without capturing
environment tokens or credentials.

## Gaps integrated into the specification

1. **Delivery ownership:** Update Phase 8 item 10, the gate policy, §174.1,
   D095-01, the implementation-status text and the milestone table together.
   Keep the original omission/failure and spec bytes in history. Moving its
   delivery phase changes entry sequencing; R13-01 closes only at 13.1 PASS.
2. **Contract completeness:** Define plan, manifest, authorization binding,
   validation report, audit envelope and recovery journal; closed versioned
   shapes/types, canonical ordering, first-install null/absence preconditions,
   cross-object source/target/base checks and acyclic hash ordering.
3. **Plugin/runtime data:** Distinguish current launch data, versioned PartSmith
   configuration and KiCad IPC registration. Add legacy handling, isolated
   Python/CAD execution, runtime/dependency checks, source/wheel/installed metadata
   parity, session identity and transient-token redaction.
4. **Target and source safety:** Require full approved releases, bounded verified
   hydration, project-local scope, unmanaged/table/name collisions, escaping
   path/reparse aliases, target/base inventories and dry-run immutability.
5. **Semantic preservation:** Specify a versioned closed relocation allowlist,
   complete retained-component comparison, unit/frame/tolerance conventions,
   unchanged STEP/source bytes and invalidation after any staged-byte change.
6. **Authorization and recovery:** Separate integration state from component
   BuildState, authenticate fresh reviewers, bind exact checks/content/base,
   retain immutable decisions and retry receipts, preserve committed outcomes,
   and journal a complete-generation switch with concurrency/fault/rollback tests.
7. **Project/editor workflow:** Address dirty projects, explicit install controls,
   cached-library refresh, multiple/disconnected/switched editor instances and
   saved-session references which carry no live publication permission.
8. **Executable acceptance:** Require real two-component installation/update/use,
   native CLI/editor and supported PCB IPC round trips, deterministic staging,
   resource/error cases, source/wheel validation and each milestone's hash closeout.

## Revised implementation sequence

| Milestone | Completion boundary |
| --- | --- |
| 13.1 | Contracts, positive/negative/golden tests, source preservation, affected Phase 8/12 regressions, packaged schemas and final hash closeout; resolves R13-01 |
| 13.2 | Pinned adapter/plugin/IPC capabilities, units/runtime/session checks and a viable target publication mechanism |
| 13.3 | Read-only planning/dry run, exact inventories/conflicts and immutable integration persistence |
| 13.4 | Deterministic complete staging, exact source/semantic/native checks and installation manifest |
| 13.5 | Explicit authenticated integration authorization and truthful idempotent decision outcomes |
| 13.6 | Atomic publication, recoverable journal, concurrent-edit protection and complete rollback |
| 13.7 | Desktop/headless project workflow, safe saved-data recovery and real native/PCB IPC use/round trips |
| 13.8 | Full source/wheel/real-target acceptance and gate hash closeout before Phase 14 |

The initial acceptance scope remains Windows AMD64 and KiCad 10.0.6, with
project-local installation and supported PCB IPC read/inspection. Global-table
changes, other targets and optional board mutations require separately declared
capability/transaction tests. Phase 14's production package matrix remains due.

The installed CLI capability was checked locally. KiCad's
[official add-on guide](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
also separates KiCad 10's GUI/PCB IPC support from later headless/schematic
capabilities. The revised §247 records this source and the
[version-selectable official bindings documentation](https://docs.kicad.org/kicad-python/).
Published documentation guides the plan; 13.2 still needs installed-build proof.

## Validation and evidence scope

The specification/documentation revision changes no runtime Python, schema,
migration or plugin bytes. All 101 package Python files and 20 packaged
resources/plugin files remain identical to the previously validated correction
builds, which each passed 778 full source/installed-wheel tests. Those full runs
retain their original scope and identities; they were not rerun for this edit.

Focused existing plugin, native CLI, release-contract, bundle and desktop-session
checks are rerun against source and installed package: **41 passed each**, with
zero failures/errors/skips. This checks the reviewed implementation and data,
not the planned Phase 13 installer/IPC contracts. New specification structure,
phase ownership, local links, current source/resource identities, lint/format,
dependency consistency and gate input hashes are checked at closeout.

See [the revision receipt](gates/phase-13-spec-revision-v0.9.7-2026-10-05.json)
for exact input/evidence identities, check commands, archived prior manifests
and current sequencing status. Every affected active map is refreshed with
previous/new hashes; historical reports, tests and distribution identities
retain their original scope. Git-blob verification is due after committing
the current checkout. No commit, remote CI or Phase 13 implementation PASS is
claimed by this specification revision.
