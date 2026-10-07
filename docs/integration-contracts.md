# Integration contracts 1.0

These contracts implement specification section 174.1 for Phase 13.1.
They describe reviewed aggregate content. They do not publish files or supply
a live authenticated principal. The customer PCM runtime is implemented at
13.2; planning/persistence at 13.3 and native semantic staging at 13.4.
Authorization, publication/recovery and desktop/native workflows are implemented
at 13.5–13.7. Final source/PCM acceptance and affected-hash closeout are recorded
in the [full Phase 13 gate](gates/phase-13.md).

`schemas/integration-contracts-1.0.schema.json` contains closed Draft 2020-12
definitions; all references are internal. `partsmith.integration` exposes frozen
typed wrappers that validate shapes and semantic invariants before storing an
independent canonical byte representation. Returned dictionaries are copies.

Canonical JSON uses existing PartSmith profile 1.0: NFC UTF-8, sorted object
keys, exact decimal tokens, no insignificant whitespace or final newline.
External lowercase SHA-256 identifies those bytes. Arrays of components,
relative files, rules, removals and operation bases are sorted and unique.
Measurements retain named expected/observed/tolerance strings from their
versioned comparator; contract validation cannot replace that comparator.

| Object | Deterministic dependencies |
| --- | --- |
| IntegrationPlan | Logical project/library IDs, project-local scope, exact previous inventory/absences, complete source releases, versions, mappings, operations, removals and all four required rules |
| IntegrationValidationReport, PRE_MANIFEST | Plan, sources, base, mappings, exact staged files, comparator and measured rule results; manifest is explicitly null |
| InstallationManifest | Plan, sources, base, mappings, final file lengths/hashes and exact pre-manifest check hashes; its external hash is the generation identity |
| IntegrationValidationReport, POST_MANIFEST | Finished manifest plus the same plan/source/base/staged-file bindings; retained separately |
| IntegrationAuthorizationBinding | Exact plan/manifest/target/base/pre-check/post-check identities; no actor or implicit component approval |
| IntegrationAuditEnvelope | Independent event/attempt/sequence, authenticated-subject metadata, UTC timestamp, decision/reason/outcome, safe object references and local execution paths |
| IntegrationJournal | Exact old/new generation and authorization references, owned staging location, attempt, strategy, intent and recovery state |

Initial generation and manifest preconditions are paired nulls. Each absent
file uses paired null hash/length. Existing project table bytes need explicit
inventory and preservation; a null generation cannot clear them. Existing base
generation equals its manifest hash. An update needs an independently verified
base; matching user-supplied strings do not prove a current target.

The required rules are MAPPING, NATIVE_PARSE, PATH_RESOLUTION and
SEMANTIC_PRESERVATION. Every required check resolves to exact supplied report
bytes and must be applicable PASS before binding validation accepts it.
Pre-manifest reports cannot refer to a finished manifest. Post-manifest reports
remain outside the manifest, avoiding hash cycles. No deterministic document
contains its own digest, actor, time, temporary root, credentials or IPC state.

Target paths are normalized POSIX-relative spellings. Absolute/drive/parent
paths, Windows reserved names, control characters, case/Unicode aliases,
file-directory collisions and generation-digest filenames fail. Actual
filesystem reparse containment, dirty-editor checks, locks and concurrent-base
verification remain mandatory responsibilities of the later target adapter.

`resolve_approved_source` reads the authoritative component store, rechecks
exact release approval, final manifest/artifacts and successful validation,
then returns original bytes. `verify_source_bindings` compares their complete
bindings against planned inputs. Reviewed revisions, unfinished desktop sessions
and imported historical approval labels cannot authorize a new installation.
Replay import preserves the original objects and creates a new release awaiting
fresh approval. Integration authority remains a separate deliberate decision.

Resource policy 1.0 fixes 128 MiB per object, 1 GiB expanded data, 10,000 objects,
2 MiB retained redacted logs, 120-second native deadlines and 15-second IPC
deadlines. Source limits are checked using SQLite blob lengths before loading
content. Explicit positive policy overrides cannot bypass engineering checks.
Stable failure codes distinguish malformed contracts, unapproved/tampered
sources, stale bases, conflicts, failed checks, IPC/authentication failures,
resource limits, unsupported publication and recovery requirements.

`fixtures/integration` contains valid, invalid and golden contract fixtures.
Their synthetic reports are contract test data, not native validation evidence.
The isolated `scripts/verify_phase13_contracts.py` fixture uses the intended
`plugins/partsmith` PCM layout, includes all declared schemas/resources, compares
exact bytes, repeats deterministic ZIP creation and validates with networking
disabled and no repository fallback. It does not register a plugin or claim
PCM install/prepare/update/removal acceptance.

The 13.4 comparator's closed relocation rules cover symbol/footprint entry names,
derived symbol-unit prefixes, symbol Footprint mapping property insertion or
relocation, and model URI relocation. All other complete tree tokens and STEP
bytes remain exact. Native KiCad parses/render-checks each entry and exports
project-relative STEP models into a disposable board. Solid/volume readback
verifies loaded models. Actual checks precede deterministic report construction;
revalidation reconstructs reports and manifest rather than trusting imported
PASS text. Mutable project files and empty unrelated directories are preserved
operationally outside installation content identity.
