# Publication implementation design preparation

Design only; 13.6 implementation waits for 13.5 PASS. This supplies no production
publication, crash recovery or rollback acceptance.

The supported boundary remains one owned NTFS junction retarget covering the
complete managed project, paired tables, libraries and STEP files. Logical
generation identity is the manifest hash; physical slot IDs are independent.
Each forward/rollback slot copies current mutable project files, then replaces
only the complete managed content. Old physical slots are never reused to undo
later board/project edits.

Registration explicitly creates a managed copy of an ordinary closed project,
preserving its original. The owned copy establishes both project-local table
files, inserting empty version-7 tables only where absent. This declared initial
managed-copy state permits complete first-install rollback using a zero-source
manifest with paired table bytes; original source-project absences stay unchanged.
Existing unrelated table entries retain exact initial bytes/structural content.

The database owns immutable target metadata including container/link identity,
volume, owner marker and logical root. Refuse foreign reparses, aliases, nested
links, remote/non-NTFS roots, changed ownership and unsupported platforms.
Resolve an owned logical junction to its physical current slot before planning;
recheck that selection under the publication lock independently of SQLite head.

Require a fresh explicit closed/exclusive-editor assertion and a live absence
check for KiCad PCB/schematic editor processes. Advisory .lck markers alone are
insufficient. External writers and hostile replacement remain outside the declared
exclusive managed-copy policy; detect concurrent file/directory edits and reject.
Current KiCad 10 IPC supplies no verified dirty/save/close API, so the GUI offers
save/close/reopen or Cancel and preserves the running PartSmith window.

Before the one switch, durably retain the full verified new slot, an immutable
journal and a separately versioned execution intent with physical slot/reparse
payload identities. Revalidate exact stage/source/check/decision/current-principal
bindings and expected base under lock. After switching, resolve/read back the exact
complete selected slot, then compare-and-swap the trusted head and record one
publication receipt. A SQLite/filesystem gap reports committed/recovery-required
truthfully; it never reports an unchanged old generation after a completed switch.

Restart recovery reconciles only a complete verified recorded old/new selection.
Never infer a successful generation from a marker string or imported journal.
Fault injection must cover disk/permission/lock/base changes and process death on
both sides of the boundary. Rollback builds a fresh plan, checks and authorization
for historical source packages against the current base, preserving latest mutable
project files and all earlier immutable decisions/attempt history.

The later desktop workflow should keep authoritative installation state in a
durable application integration database separate from archived working sessions.
Saved session extension 1.0 holds drafts/object references only. Reject imported
live target/decision/publication rows on session load; never let a copied SQLite
approval row become current installation authority. Source and integration service
connections may be distinct; source bytes/approvals must be freshly resolved from
the selected complete source closure on resume.
