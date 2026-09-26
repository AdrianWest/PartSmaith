# Specification v0.9.5 downstream impact review

Reviewed 2026-09-20 on `Phase-02-Development`.

Source: [implementation specification](../resources/BFT_PartSmith_Implementation_Spec.md),
SHA-256 `3da7d27391edceaf1c98bde4ec678c8aeaa9a589d4251221d51656b6c8efb40f`.
Section numbers below refer to that snapshot.

The revised design affects every remaining phase. Most effects are already
specified, but six downstream contracts or verification points need attention.
The most consequential are approval versus shared-library installation, the
input-review service, and preservation of revision history during export/import.

This is a review, not a specification amendment or a new gate result. The
absence of Phase 3–14 implementations is expected. The recorded Phase 2 tests
establish their stated IR scope; they do not establish these later integrations.

| ID | Priority / classification | Resolve before |
| --- | --- | --- |
| D095-01 | High — artifact identity/integration contract gap | Freeze export identities in Phase 8; exercise shared-library updates in Phase 13 |
| D095-02 | High — service and workflow contract gap | Phase 8 review service; connect extraction in Phases 10–12 |
| D095-03 | High — persistence and portable-rebuild contract gap | Phase 8 persistence/packaging, Phase 9 offline replay |
| D095-04 | Medium — confirmed projection integration risk | Generator configuration in Phases 4–6; selective reuse in Phase 9 |
| D095-05 | Medium — conflicting invalidation guidance | Phase 8 final-byte checks and Phase 9 reuse |
| D095-06 | Medium — late discovery risk in gate placement | Phase 6 CAD spike, ahead of Phase 9 acceptance |

**D095-01 — Exact-byte approval needs a shared-library installation contract.**

Sections 166–167 approve exact artifact hashes and prohibit export from rewriting
approved files. Section 212 selects a packed `BFT_Symbols.kicad_sym` for the MVP;
sections 214 and 216–218 require updating existing libraries and rollback.
Adding a second component to that shared file necessarily creates different
library bytes from either original per-component symbol artifact. The spec does
not distinguish the installed aggregate's identity from the approved component
artifact or assign validation/approval to that new aggregate.

Consequently, a Phase 8 component can pass its own byte checks while a naive
Phase 13 installer either violates those bindings or refuses a legitimate
library addition. The same boundary matters when project integration changes
library nicknames, footprint assignments, or model reference paths.

Define the installation artifact and its manifest explicitly. One solution is
an immutable approved component bundle plus a separately validated installation
aggregate with its own hashes, source-component bindings, authorized integration
decision, and rollback record. An alternative is independently installed packed
files per component, with a corresponding amendment to section 212. Neither
choice should silently substitute semantic equality for approved byte equality.
Test installation of two components, update of one while preserving the other,
relocation without broken references, and rollback after a failed update.

**D095-02 — Evidence approval and release approval are different operations.**

Sections 121.2 and 121.7 require an approved acquisition-inventory review before
`IR_VALIDATED`. Section 121.8 requires approval of pending decisions by appending
new records. Section 172 lists build approval, rejection, and override proposal
operations, but no explicit input-review approval, evidence disposition,
resolution approval, or revision-commit operations. Section 2.1's workflow also
puts its single visible review step after generation.

The normative text already permits recovery and new revisions; this is not a
claim that the state machine forbids early review. The missing detail is how
the service performs that review before artifacts exist. Implementing only the
listed release-approval method leaves a fresh extracted candidate unable to
reach generation without a separate, unspecified operation.

Specify typed input-review operations bound to the exact revision and inventory,
with stale-base rejection and atomic persistence of new decisions/selectors.
Keep release approval bound to the final manifest and artifact hashes. Make
the CLI and UI expose both stages and test that input approval cannot approve
artifacts, release approval cannot bypass unresolved inputs, and approving a
proposal preserves the original pending record.

**D095-03 — A rebuild now needs revision ancestry and inventories, not just current IR.**

Sections 121.2 and 121.6–121.8 require historical snapshots for acquisition,
old-value validation, supersession, and pointer rebinding. Section 163 lists
storage domains but leaves their immutable storage/transaction contract open.
Section 175 requires frozen inputs or controlled retrieval references without
enumerating the revision/inventory closure. Sections 186 and 199 require
offline operation once inputs are prepared.

The current [revision store](../src/partsmith/ir/history.py) actually walks
parents and checks retained inventory hashes. Exporting only the latest IR and
its selected evidence therefore does not suffice for an ordinary non-root
revision. A portable import can be structurally valid yet fail generation with
missing history. A retrieval reference alone does not establish offline access.

Define required bundle objects and hash/index bindings for retained revisions,
inventories, decisions, source references, and pinned PDL/configuration. Define
an explicit reviewed-root import when full ancestry is intentionally unavailable;
do not silently erase parents to make validation pass. Distinguish a fully
materialized offline bundle from a distribution that needs controlled retrieval.
Add a forward database migration rather than rewriting migration 001, and
specify immutable insertion and transaction boundaries. Test a multi-revision
export/import/rebuild, missing/tampered ancestors, inventory mismatch, and a
failed transaction that must leave no partially approved revision.

**D095-04 — Per-generator projections currently carry global runtime configuration.**

Sections 89, 103, 162, and 166 require isolated generator inputs and selective
reuse. The full build snapshot correctly includes the complete runtime tuple.
However, [dependency_projection](../src/partsmith/ir/projection.py) also requires
CadQuery/OCP/OCCT versions for every artifact context and includes the entire
supplied configuration in each dependency projection.

A read-only probe used the existing valid IR and a synthetic symbol context
requiring only identity, electrical data, and pins. Changing only the CadQuery
version changed its dependency hash:

| Probe | SHA-256 |
| --- | --- |
| Baseline | `ec68974c75f28a7808ff6c2cb3c30d53a7ffafdfedd77162c944377aa8f8f4e6` |
| Only CadQuery version changed | `f83efe2ec49b9652687ffe341bb68e722678652ffa65a666f5b27a7785c0c296` |

This is confirmed helper behavior, not a production symbol-generator test.
Used directly as the Phase 9 cache key, it conservatively invalidates unrelated
outputs and makes early symbol generation depend on a CAD configuration that
is only validated in Phase 6. It does not demonstrate unsafe cache reuse.

Specify trusted per-generator configuration projections separately from the
complete build snapshot. Keep all actual output-affecting dependencies, but
assign CAD/exporter/validator configuration to the nodes that consume it. Test
both affected and unaffected hashes for each change. Any change to frozen
projection semantics needs explicit versioning and updated evidence; do not
silently replace existing golden hashes.

**D095-05 — The silkscreen invalidation example understates final-byte consequences.**

Section 103 says a silkscreen-only change invalidates cross-validation only if
footprint geometry changes. Section 167 requires new footprint, association,
and compatibility checks whenever footprint bytes change, and binds final
results, manifest, and approval to exact bytes.

An implementation following the shorter example could retain a final result
bound to the old footprint or reuse its approval. Clarify the distinction
between reusable independent geometry work and checks/results bound to the
released file. A silkscreen edit can preserve canonical STEP geometry while
requiring new footprint checks, applicable final-byte checks, manifest, and
approval. Test this with identical pad/STEP geometry but different footprint
text and hashes; stale final-byte results must block approval.

**D095-06 — STEP byte determinism should be exercised during the CAD spike.**

Phase 6 establishes the selected runtime and validates STEP geometry and
packaging feasibility. Phase 9 requires byte-identical STEP and rejects geometry
equivalence as a substitute (sections 166/188). Phase 6's listed gate does not
require two clean STEP exports to have identical bytes.

This is a sequencing risk, not an assertion that CadQuery currently fails:
backend/exporter nondeterminism could first be discovered after validators and
the complete Phase 8 pipeline have been built around it. Add an early clean-run
byte comparison to the Phase 6 spike and record deterministic exporter settings
and any permitted pre-finalization metadata normalization. Keep Phase 9's broader
whole-build test; the early check does not replace it.

The remaining major design effects are already covered, or require carrying a
known constraint into their assigned implementation phase:

| Design choice | Downstream consequence | Coverage / implementation checkpoint |
| --- | --- | --- |
| IR 1.2 typed overrides and immutable history | Editors, CLI, migrations, semantic diffs, and replay must create new records and preserve base bindings | Sections 121.6–121.8 and 177 cover this; service/storage details are D095-02/03 |
| JSON Pointer targets rebound across pin edits | PDL terminal IDs, mapping reports, and UI sorting must preserve physical identity | Sections 93.1/121.7/148/227 cover identity; current history code uses terminal numbers for reorder matching and treats in-place renumbering separately. Document supported combined edits and test reorder/renumber/removal before exposing them in the editor; no schema redesign is presumed here |
| CLASS_A and declared reference features | Phase 3 PDL schema must include required observables, tolerances, symmetry, representation, and applicability; later CAD checks must measure them | Sections 31/98/148–152 and Phases 6–7/14 cover it. Section 126's abbreviated field list alone is insufficient to implement the PDL schema |
| Exposed terminals versus pad shapes | Generators, mapping validators, and fixtures must compare terminal groups, not serializer-object counts | Sections 93.1/148/228/231 cover it; compound-group round-trip evidence is required before claiming support |
| Affine composition with possible shear | Shared transform code, CAD adapters, KiCad conversion, and viewer controls must preserve or explicitly reject the transform | Sections 92/150 specify execution, tolerances, and rejection; Phases 6/12/13 must use that same contract |
| NOT_APPLICABLE with null status | Reporting, gate aggregation, and UI must retain applicability/basis and measurement mode rather than count every result as PASS/FAIL | Sections 148/152/153 cover semantics; Phases 7–8/12 need aggregation and serialization checks, including missing required results |
| Canonical page coordinates | PDF/OCR adapters and overlays must retain crop/rotation/deskew mappings and keep document points separate from engineering mm | Section 124.1 and Phase 10 expressly cover this; non-affine dewarping remains unsupported |
| Deterministic content separated from audit | Reports, manifests, approval replay, and caches must use the correct hash scope | Sections 110/155/166–167/188 cover the acyclic order and separate post-manifest reports; Phases 8–9 implement it |
| Pinned release profile | PDL/configuration versions, supported languages/providers, packaging, and CI corpus must agree | Section 31 and Phase 14 cover the scope. Complete/pin named choices by their assigned gates and version later changes rather than mutating a published profile |

Two smaller consistency remnants can mislead downstream work:

- The product-description header still says version 0.9.4 and revised baseline
  date 2026-09-19, while the authoritative header says v0.9.5 / 2026-09-20.
  Label these explicitly as historical metadata or align them before generating
  release documentation from this text.
- Sections 6 and 21 still use “16 pins” with an exposed pad without explicitly
  distinguishing peripheral count from total conductive terminals. Section 21's
  sample test expectation should use section 93.1 terminology before becoming
  a QFN fixture. Section 241's blanket “all must fail” also needs the observable
  fault versus symmetry-equivalence qualification already present in section 149.

Verification: reread the current specification and traced contracts into the
implemented IR/history/projection APIs and recorded gate scope. The focused
projection probe used the existing `.env` without displaying or changing its
values. All 50 file hashes in the IR 1.2 gate manifest still match. No full test
suite, live CAD/KiCad experiment, or remote CI run was performed for this review.
The specification, production code, fixtures, and existing gate reports were
left unchanged.
