# Phase 13.6 — publication and recovery

Implementation and validation completed on Windows fixed local NTFS. The
checkpoint receipt and hash closeout record the exact validated bytes.

The production target is an explicitly registered complete project copy on
Windows fixed local NTFS. Immutable ownership records bind its marker, container,
lock, junction and physical directory identities. Original project files stay
unchanged. Registration establishes missing paired library tables in the copy.
Unsupported scope/filesystem/platform, nested reparses, foreign destinations,
aliases and changed ownership fail before publication.

Publication holds a native exclusive target lock, freezes existing old and
candidate files with Windows sharing, rechecks the complete snapshot and fresh
OS subject, and repeats source, semantic and native SVG/STEP validation. A new
physical UUID slot contains the complete project, paired tables and approved
libraries. File data is flushed; the PREPARED journal and physical execution
intent commit with SQLite synchronous FULL before one junction retarget. Complete
payload/file/directory readback precedes compare-and-swap head/receipt commit.
Old slots, failed attempts and immutable decisions are retained.

A fresh explicit confirmation requires all PCB/schematic editors and KiCad CLI
processes to be closed and exclusive use of the copy. PartSmith never saves or
closes user editors. External writers that ignore this policy are unsupported;
absence of lock files alone is insufficient. Existing-file writes are denied by
real kernel sharing. New-file/directory races are checked before and after the
boundary. This validates process-crash recovery, not power-loss durability or
hostile administrator filesystem changes.

Staging and recovery also validate managed symbol/footprint/model references in
the copied schematic and PCB. Removal cannot strand an existing design instance
with a missing managed library or STEP file. Cached symbols and board bytes stay
unchanged; unrelated external libraries and ordinary user text are retained.

Recovery does not switch. It reconciles a trusted PREPARED attempt against the
actual complete old/new selection and independently resolves the decision,
current principal, sources, check graph, ownership and installed inventory.
A filesystem commit with a missing SQL receipt reports RECOVERY_REQUIRED and
preserves the new generation. Restart can finish one receipt while retaining
new mutable user files. Pre-switch cancellation cleans the verified candidate
and isolated stage; late cancellation reports the committed outcome with a
warning. Driver exceptions after a real receipt commit resolve the durable row.

Rollback creates a fresh plan against the current base for a trusted historical
source set, stages and checks it, and requires a new exact approval. It creates
a new physical slot containing current mutable project files and restores prior
managed content/tables. Historical slots and approvals are never reused as live
publication permission. Initial-state rollback restores the registered copy's
empty paired tables; original project table absences remain intact.

Tests use real native junctions and validation. Child processes call os._exit
after PREPARED and after the actual switch, then the parent reconciles the result.
Fault cases cover write/permission failures, real lock and file-sharing conflicts,
stale whole-project snapshots, receipt gaps, COMMIT exceptions and cancellation.
The native evidence script uses production OS authentication for two-component
installation, update, fresh rollback, exact retry and independent database reopen.
It removes only its verified fixture junction after collecting evidence;
retained database records are historical artifacts, not imported authority.

`phase-13.6-final-source-results.xml` records 165 passing checks, no failures,
errors or skips. `phase-13.6-final-revalidation-results.xml` records 31 passing
checks for staging, project references and both process-crash cases after the
final reference guard. These are 196 test executions; the two crash cases were
repeated, so this is not a claim of 196 unique cases. The initial nine-case
publication run is retained separately with its original scope.

`phase-13.6-native-publication/receipt.json` records production OS authentication,
three actual complete switches, exact retries and an independent reopen. The
copied source packages and original database SHA-256 remain unchanged. The
installation manifest is `8280ac17b1ef27c2889010a7f601e2a64cb7010ff6c1def9b69c9d3e78c69f78`;
the update is `79de22ae73561eb309a1aa24b13ee6ecf08b5ca3a404b908fb6cd6df8487c928`;
the fresh rollback is `16f7f5fd41f534bb757c12afe3897941d95a31a2ac236c1b093f849616f6960f`.
Retained manifests, checks, authorization, audit, journals, SQL history and all
physical slot files support those identities.

Ruff lint/format and tagged documentation checks pass. Hash closeout uses
`scripts/close_integration_gate.py --phase 13.6`, including affected active/CI
maps and current native receipt identities outside input maps. Historical
acceptance remains scoped to its original bytes. Git-blob verification is due
after the user commits the finalized inputs.

The complete Phase 13 gate remains pending through 13.7–13.8.
