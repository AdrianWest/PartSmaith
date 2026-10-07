# Phase 13.2 — PCM, runtime, IPC and publication feasibility

Recorded 2026-10-06. **PASS**, with final affected-manifest hash verification
recorded in [the closeout receipt](phase-13.2-hash-closeout.json). This covers
Windows AMD64, Python 3.12.10 and KiCad 10.0.6. Production planning, staging,
authorization, publication and project workflows remain the subsequent ordered
milestones; this report does not declare the full Phase 13 gate complete.

PartSmith starts from the PCB Editor's **Open PartSmith** IPC toolbar action.
Customers install the ZIP through KiCad's Plugin and Content Manager. The exact
final checkpoint archive is `dist/partsmith-0.1.6-pcm.zip`, SHA-256
`0fd43032e969b1041cb78e6e1d919310e2d0f9d31f77642f24adc9f48d2c3d2c`.
The PCM listing uses the owner's unchanged `PartSmith_Logo_64x64.png`; the
toolbar uses the unchanged 24/64 pixel anvil assets.

## Validation scopes

The [source result](phase-13.2-016-source-results.xml) has 231 passing tests:
98 contracts, four trusted source-resolution cases, 58 IPC cases, 24 inspector
cases, 31 PCM cases and 16 real NTFS feasibility cases. Ruff checks and format
checks pass for the complete checkout. No PartSmith wheel was built, installed
or used for these checks.

The [isolated final ZIP result](phase-13.2-pcm016-isolated-revalidated.json)
has 211 passing tests. Python runs isolated from an unrelated working directory;
DNS and connection attempts fail, and all 44 loaded PartSmith modules originate
in the extracted PCM payload. Declared schemas, SQL, fixtures, PDL, assets,
requirements and entry metadata have exact byte identities. Tests reconstruct
builder inputs from archive-owned bytes with explicitly declared test tooling.
The initial harness omitted two original icon-resource copies and the builder;
its two failed resource assertions remain in the earlier
`phase-13.2-pcm016-isolated-acceptance.*` records. The corrected harness changes
no archive or production bytes.

The [final ZIP PDF revalidation](phase-13.2-pcm016-pdf-stability/manifest.json)
passes three fresh rounds of 180 tests each. The earlier 0.1.6 attempt crashed
with a Windows access violation during PDF processing. Its incomplete result
and raw output remain in
`history/phase-13.2-pcm016-pdf-native-crash/`. The intermittent native crash is
still **UNKNOWN**; passing fresh runs establish the recorded revalidation and
do not establish a root-cause repair. The earlier 0.1.4 three-round acceptance
is separately retained in `phase-13.2-pcm014-pdf-stability/`.

## Actual KiCad and PCM acceptance

Evidence distinguishes real desktop actions from isolated loader simulations.
The [lifecycle record](phase-13.2-lifecycle.json) names the exact archive scope
for each native operation, including local-file install, configured-repository
Pending/Apply install and updates, removal and reinstall. Historical 0.1.0–0.1.4
receipts retain their original versions; 0.1.5 has no native-install claim.

The 0.1.6 installed action completes version discovery and exact-board footprint
inspection. [Initial read](phase-13.2-live-ipc-initial-016.json) and deliberate
[Refresh](phase-13.2-live-ipc-refresh-016.json) show the intended R1 instance and
the second read sequence. Closing that PCB Editor and refreshing the still-open
inspector produces a bounded [failed session](phase-13.2-live-ipc-disconnected-016.json),
clears rows and disables further reads. PCM uninstall/reinstall while the old
action remains open does not reconnect it. A deliberate launch after reopening
the editor creates a [distinct verified session](phase-13.2-live-ipc-restarted-016.json).
The native wrong-board result remains scoped to
[0.1.4](phase-13.2-live-wrong-board-014.json), whose adapter bytes match 0.1.6.

Removing PCM while an action holds its package directory produces a Windows
directory-removal warning. PCM nevertheless removes its payload/resources and
registration; reinstall restores the exact inventory. Normal closed-action
update and failed-preparation removal complete without that warning. The
documentation directs users to close action windows before ordinary updates.
No application database, saved session, journal, credential or generated
library is stored in the disposable plugin directory or Python cache. An
explicitly owned application-data sentinel remains byte-identical through the
native lifecycle; this test makes no claim to inspect private user data.

The offline preparation fixture has only a local pip wheel when KiCad's real
**Recreate Plugin Environment** control runs. Actual preparation fails with
`PINNED_DEPENDENCY_MISSING_OR_CHANGED`; PartSmith disappears from the toolbar
and preferences action list. PCM removal and reinstall still succeed. The
full pinned binary supply is then provisioned and the actual loader is restarted
for retry. KiCad's context menu is available on a registered IPC action at
**Preferences → PCB Editor → Plugins**, not the top-level API settings page.
The failed action has no row on which to invoke that menu. The lifecycle record
states the exact observed recovery sequence rather than claiming an unavailable
control was used. Independent owned loader-sequence evidence also covers denied
index access, incompatible/missing binaries, interrupted preparation and retry.

IPC endpoints/tokens remain transient and are absent from durable diagnostics,
contracts, test receipts and hashes. Read operations are bounded at 15 seconds.
KiCad 10.0.6 and the official 0.8 binding provide the required PCB read surface;
schematic IPC, dirty-state discovery, save/close and board mutation capabilities
are not advertised. Their negative and timeout cases are separately tested.

## Supported publication candidate

The [actual NTFS feasibility receipt](phase-13.2-atomic-feasibility.json) records
one whole-project junction retarget on the local fixed NTFS volume, without
elevation. Native CLI checks resolve both changed project-local library tables,
symbols, footprints and unchanged STEP models in old, new and reverse-selected
generations. Root-handle readers observe complete old or new inventories.
Independent path opens can mix generations, so the supported candidate requires
an explicitly closed/quiesced project and reopening to refresh KiCad caches.

The [mechanism report](phase-13.2-atomic-feasibility.md) records the measured
boundary, sharing failure and exact limitations. Global tables, foreign
reparse roots, network/removable filesystems and ordinary existing-directory
replacement are refused. The later production service must explicitly register
an owned managed copy of an existing project and implement locking, durable
intent/journal, authorization, recovery and rollback before claiming publication.

## Hash closeout

The current gate map is [phase-13.2-artifacts.json](phase-13.2-artifacts.json).
The command `scripts/close_integration_gate.py --phase 13.2 --reason ...`
runs after finalizing these records. It archives changed active maps, refreshes exact disk
hashes in dependency order, verifies all active and CI maps, and verifies the
final ZIP, inventory, member count and listing icon outside the input hash map.
Committed-blob verification is due after the user commits the prepared changes.
