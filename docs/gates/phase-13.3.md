# Phase 13.3 — planning and immutable integration storage

PASS, 2026-10-06, after 188 passing source checks and final hash closeout.
This checkpoint covers planning and persistence. Staging, authorization and
publication follow the ordered 13.4–13.8 milestones.

`Planner.plan` resolves complete approved release packages from the authoritative
application database and treats the requested builds as the complete desired
component set. It freezes exact source, target, namespace and expected-base
bindings. Its dry-run result lists create, modify and delete operations without
writing project files or SQLite records. Source sizes are checked cumulatively
before content hydration.

The project inventory rejects unsafe Windows paths, aliases, reparses, reserved
unmanaged files/directories and conflicting table entries. It preserves unrelated
project files and complete unrelated library-table entries. A frozen operational
snapshot covers all project files and directories; any edit invalidates it.
The installation base separately covers managed library content and table bytes,
with explicit expected absences. Mutable project files do not enter a generation
identity.

Migration 005 adds immutable typed content objects, append-only references,
attempts/events and decision/publication records. The mutable published head is
separate from component BuildState. Stores use normal caller-owned transactions
and rollback-safe savepoints. Explicit source retention records original bytes
and historical approval objects without granting installation authority.

Acceptance includes real native-generated, reviewed and approved source releases,
two-source planning, one-source update/removal, identical no-op, target concurrency,
namespace/path failures, bounded hydration, explicit save/reopen/rollback, storage
faults, immutable triggers and a real migration-004 approved release preserved
through migration 005. Prior-head fixtures in pure planner tests are synthetic;
they supply no publication or native installation acceptance claim.

The initial failed results remain recorded as fixture setup failures: acquisition
revision references, nonexistent database columns and the compare-and-swap hash
argument were corrected in the fixture. Production approval checks stayed enabled.
The later source run retained two fixture failures (Windows text encoding and
shared-manifest reference counts); the final run corrects these assumptions.

Validation: `.venv/Scripts/python.exe -m pytest` on the planner, store, tree
parser, persistence, approved-source, contract and PCM suites produced
`phase-13.3-final-source-results.xml`: 188 passed, no skips. Ruff lint and
format checks pass. `scripts/close_integration_gate.py --phase 13.3` verifies
all active/CI manifests and records previous/new hashes in
`phase-13.3-hash-closeout.json`. Git-blob verification follows a user commit.
