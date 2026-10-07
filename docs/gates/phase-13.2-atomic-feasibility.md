# Phase 13.2 NTFS complete-generation feasibility

The local NTFS prototype passed its scoped feasibility checks. One
`FSCTL_SET_REPARSE_POINT` replaces an exclusively owned directory junction's
complete mount-point payload. Readers that open the root once and use
`NtCreateFile` with that `RootDirectory` handle continue seeing the selected
complete generation after the junction changes. Reopened roots select the new
generation. This result establishes a candidate publication boundary for
Phase 13.6; it does not complete Phase 13.2 or implement a production publisher.

[The machine receipt](phase-13.2-atomic-feasibility.json) records the actual
filesystem, token elevation state, runtime, native executable identity,
inventories, command results and output hashes. The measured process is not
elevated and the helper never enables privileges, invokes a shell or requests
elevation. The target is the same local fixed NTFS volume for both complete
generations and the owned junction.

The [16 real NTFS tests](phase-13.2-atomic-tests.xml) pass. They include 120
complete paired snapshots through four readers during 60 switches, raw payload
readback, stable junction file identity, tampered/extra files, stale expected
targets, ownership changes, foreign reparse destinations, generation containment,
resource limits, cancellation before replacement, reverse selection and repeated
no-op rollback. An actual reparse-object handle denying write sharing produces
`ERROR_SHARING_VIOLATION` (32); its exact old payload remains intact and the
switch succeeds after that blocking handle closes.

The native helper independently records 160 complete eight-file snapshots
through four readers during 80 real switches. Every snapshot matches one
declared inventory. The old and new generations each contain both project-local
library tables, the symbol library, footprint library, exact STEP model,
disposable PCB/project files and pinned default local project settings. KiCad
10.0.6 CLI exports the old entry, then the new entry, then the old entry after
reverse selection. Symbol/footprint SVG output, footprint-table DRC resolution
and PCB STEP model loading succeed at all three points. There are no library
lookup or library mismatch DRC findings. Imported exported STEP geometry contains
all source model solids plus the board solid. All generation file hashes stay
unchanged through these operations.

Both table files have different old/new bytes through declared owned-entry
descriptions. A dedicated root-handle test verifies that an old root reads both
old tables after replacement and a reopened root reads both new tables. Native
checks exercise those actual changed table bytes alongside the changed libraries.

KiCad writes missing `.kicad_prl` files while inspecting a project. The probe
preincludes [the native default local settings](phase-13.2-atomic-default-project-local.json)
so this disposable fixture remains byte-stable. These empty/default operational
settings are fixture evidence, and do not define an engineering contract or
contain a credential. Production project/session persistence remains separate.

An explicit test also reads one file through the active path, switches, then
reads a second file through the active path. The pair contains old and new
content. Therefore a production service must quiesce KiCad and external writers
and explicitly reopen/refresh its libraries. Independent path lookups and
cached editor state do not inherit the consistency of a single opened root.
The editor refresh evidence belongs to the separate real editor workflow.

The supported prototype scope requires a fresh, exclusively owned disposable
project root. Existing ordinary directories, imported/foreign reparse objects,
filesystem roots, nested generation reparses, remote/removable volumes and other
filesystems are refused. Every managed table, library and reference must resolve
inside the complete selected root. Immutable generations remain available for
reverse selection. External writers, hostile concurrent filesystem replacement,
editor dirty-state handling, authorization, persisted publication journals,
process/power-loss recovery and the filesystem/SQLite commit gap remain Phase
13.3–13.6 production obligations. An interrupted or uncertain production switch
will require exact readback and journal reconciliation, not inferred success.

Validation commands:

```text
.venv/Scripts/python.exe -m pytest tests/test_atomic_target.py -q --junitxml=docs/gates/phase-13.2-atomic-tests.xml
.venv/Scripts/python.exe scripts/verify_atomic_target.py --evidence docs/gates/phase-13.2-atomic-feasibility.json
.venv/Scripts/python.exe -m ruff check src/partsmith/integration/atomic_target.py scripts/verify_atomic_target.py tests/test_atomic_target.py
.venv/Scripts/python.exe -m ruff format --check src/partsmith/integration/atomic_target.py scripts/verify_atomic_target.py tests/test_atomic_target.py
```

API definitions follow Microsoft's
[FSCTL_SET_REPARSE_POINT](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_set_reparse_point),
[mount-point REPARSE_DATA_BUFFER](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_reparse_data_buffer),
[CreateFileW directory/reparse/sharing flags](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
and [NtCreateFile root-relative opens](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile).
The observed complete-generation selection is experimental evidence on the
recorded target, not a claim that these references guarantee crash durability or
multi-open editor transactions.
