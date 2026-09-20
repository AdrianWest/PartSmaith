# PartSmith v0.9.3 specification consistency review

Reviewed 2026-09-19, after integration of the Component IR 1.0 contract.

**Resolution status (2026-09-19):** R01–R20 and the editorial findings are
resolved at specification level in v0.9.4. The
[resolution register](../resources/BFT_PartSmith_Implementation_Spec.md#246-consistency-resolution-register)
maps each finding to its revised requirements. Subsequent IR 1.1 implementation
is verified by the [revised Phase 2 PASS](gates/phase-2-ir-1.1.md); later-phase
requirements remain assigned to their respective gates. Findings below preserve the original
v0.9.3 observations; links now lead to the revised sections.

**Original result: the reviewed v0.9.3 specification was not internally consistent.**
The findings below distinguish direct conflicts from missing implementation
contracts. The original review changed neither the specification nor application code.

Scope: all current normative sections and phase gates, the JSON Schema
incorporated by section 121, and the historical appendix's precedence and prior
resolution logs. Historical requirements were not treated as current rules.
External product/API availability and standards accuracy were not independently
revalidated; this is an internal consistency review.

P1 means resolve before implementing the affected workflow; P2 means reconcile
before the relevant feature/release gate. Neither label changes an existing
phase-gate result automatically. Passing fixture tests does not establish that
all requirements in the larger specification agree.

## P1 findings

### R01 — Preserved conflict history can permanently block generation

**Workflow conflict.** [Section 121.2](../resources/BFT_PartSmith_Implementation_Spec.md#1212-component-ir-api-and-validation-behavior)
rejects unresolved statuses anywhere, explicitly including evidence and
override history. [Section 88](../resources/BFT_PartSmith_Implementation_Spec.md#88-user-override-model)
preserves original evidence; [section 96](../resources/BFT_PartSmith_Implementation_Spec.md#96-evidence-conflict-resolution)
requires recording a resolution and rebuilding, and
[section 202](../resources/BFT_PartSmith_Implementation_Spec.md#202-audit-trail)
makes audit records immutable.

An approved replacement does not remove the old CONFLICTING/MISSING record.
Retaining that record inside IR therefore continues to block generation even
when no selected engineering input remains unresolved. The newly incorporated
rule acknowledges its strictness but does not define a resolution path.

**Observed:** adding unreferenced historical CONFLICTING evidence to the valid
fixture produces `IR_UNRESOLVED` at `/evidence/1/interpretation`.

**Proposed resolution:** distinguish active engineering inputs from immutable
history, with explicit resolution/supersession references. Validate the active
dependency closure for generation while retaining and hashing history. If the
strict policy is retained, specify a separate immutable history store and an
explicit snapshot transition that permits the resolved build to proceed.

### R02 — A genuinely missing dimension cannot be represented

**Contract conflict.** [Sections 17 and 87](../resources/BFT_PartSmith_Implementation_Spec.md#87-value-status-model)
provide MISSING/UNKNOWN states; sections 29, 97, 136, and 194 require incomplete
engineering information to be represented and explained without inventing it.
The incorporated schema's [quantity definition](../schemas/component-ir-1.0.schema.json:498)
requires a numeric `source_value` and an explicit supported `source_unit`, even
when status is MISSING.

**Observed:** `source_value: null, status: MISSING` fails `IR_SCHEMA`. Supplying
a placeholder number misrepresents missing evidence; omitting the whole named
quantity loses the explicit missing-value status and reason.

**Proposed resolution:** define candidate quantities that allow absent/null
values and unknown units, with status-dependent constraints. Require concrete,
normalized values only when the quantity is needed for generation.

### R03 — Required electrical types are rejected by the normative schema

**Direct conflict.** [Section 95](../resources/BFT_PartSmith_Implementation_Spec.md#95-electrical-pin-type-rules)
requires at least `power_input`, `power_output`, and `power_flag`.
The [pin enum](../schemas/component-ir-1.0.schema.json:610) instead contains
`power_in` and `power_out`, with no `power_flag`.

**Observed:** all three section-95 values fail `IR_SCHEMA` at
`/pins/0/electrical_type`.

**Proposed resolution:** define one canonical IR vocabulary and a separate,
explicit target-format mapping. Decide whether a power flag is an IR pin type
or a symbol-level construct, and align the requirements and schema accordingly.

### R04 — Land-pattern source vocabularies are incompatible

**Direct conflict.** [STD-007](../resources/BFT_PartSmith_Implementation_Spec.md#std-007--ipc-7351-role)
requires recording `MANUFACTURER_RECOMMENDED`, `IPC_DERIVED`, or `PDL_DERIVED`.
[Section 142](../resources/BFT_PartSmith_Implementation_Spec.md#142-land-pattern-algorithm)
distinguishes those derivation paths. The incorporated
[footprint schema](../schemas/component-ir-1.0.schema.json:140) accepts only
`MANUFACTURER`, `STANDARD`, and `USER_OVERRIDE`.

**Observed:** each STD-007 value fails `IR_SCHEMA` at
`/footprint/land_pattern_source`.

**Proposed resolution:** adopt a shared source enum that preserves the IPC/PDL
distinction. Keep user override status separate from the original source of the
land pattern, or document an explicit lossless mapping.

### R05 — Phase 8 requires capabilities scheduled for Phases 12 and 13

**Phase dependency conflict.** The [phase-gate policy](../resources/BFT_PartSmith_Implementation_Spec.md#phase-gate-policy)
prohibits beginning later phases before earlier gates pass.
[Phase 8](../resources/BFT_PartSmith_Implementation_Spec.md#phase-8--first-complete-deterministic-component)
requires an APPROVED package and KiCad compatibility validation, but
[Phase 12](../resources/BFT_PartSmith_Implementation_Spec.md#phase-12--human-review-and-application-ui)
introduces review/approval states and
[Phase 13](../resources/BFT_PartSmith_Implementation_Spec.md#phase-13--kicad-integration)
introduces the versioned KiCad adapter and CLI validation.

**Impact:** the plan does not authorize the prerequisite implementation early
enough to satisfy its own blocking gate. An assumed or hardcoded APPROVED flag
would not satisfy sections 173–174.

**Proposed resolution:** explicitly place minimal headless approval, build-state
handling, and KiCad compatibility checks in Phase 8 or earlier. Reserve Phase 12
for the full review UI and Phase 13 for expanded IPC, installation, and
round-trip integration. Update the numbered work items as well as gate text.

### R06 — The boundary between input validation and artifact validation is unclear

**Lifecycle ambiguity.** [Section 137](../resources/BFT_PartSmith_Implementation_Spec.md#137-ir-validation)
requires IR_VALIDATED before generation. The new section 121 discussion defers
geometry/artifact validators to later phases and then says those later-phase
validators must run before IR_VALIDATED or APPROVED. Read literally as one
combined condition, validation of outputs becomes a prerequisite for creating
the outputs.

**Proposed resolution:** specify two separate transitions: schema, provenance,
PDL/topology, and input-transform checks establish IR_VALIDATED; generated
artifact, cross-validation, compatibility, and review checks establish
APPROVED. Later implementation phases do not imply later runtime stages for
every validator.

### R07 — The persisted review state has two incompatible names

**Direct conflict.** [Section 159](../resources/BFT_PartSmith_Implementation_Spec.md#159-build-state-machine)
lists HUMAN_REVIEW as an implementation state and HUMAN_REVIEW_REQUIRED as a
failure state. [Section 160](../resources/BFT_PartSmith_Implementation_Spec.md#160-build-orchestrator)
says persisted build state uses HUMAN_REVIEW_REQUIRED and HUMAN_REVIEW is a
validation result.

**Proposed resolution:** publish one build-state enum and transition table.
Keep validation-result status in a separate enum. Clarify whether required
review is a waiting state or a failure, and how approval/rejection resumes it.

### R08 — Whole-record hashing has no immutable build-input boundary

**Contract gap affecting reproducibility.** [Section 121.3](../resources/BFT_PartSmith_Implementation_Spec.md#1213-canonical-profile-10)
hashes the entire IR, including validation results and revision/build metadata.
[Section 166](../resources/BFT_PartSmith_Implementation_Spec.md#166-reproducible-build-algorithm)
uses IR as a build input; sections 103 and 162 require selective invalidation;
[section 188](../resources/BFT_PartSmith_Implementation_Spec.md#188-determinism-tests)
requires the same manifest content between builds. The manifest includes a
build ID, while validation records can reference generated artifact IDs.

**Impact:** appending output validation to the same IR changes its input hash.
Different run identities can also change supposedly identical manifests.
Whole-record hashes alone cannot implement the specified selective reuse.
This is not proof that reproducibility is impossible; the necessary snapshot
and hash distinctions are simply not specified.

**Proposed resolution:** freeze an input IR revision per build, distinguish
whole-record/audit hashes from generator-specific dependency hashes, and define
which run metadata is excluded from deterministic comparisons. Specify when
validation results attach to a new record or to a separate report.

### R09 — The coordinate contract is insufficient for independent implementations

**Implementation gap.** [Section 92](../resources/BFT_PartSmith_Implementation_Spec.md#92-transform-contract)
fixes T×R×S×M; section 121 fixes units and three rotation values. Neither
establishes Euler axis order, intrinsic/extrinsic rotation, vector/matrix
convention, or a complete mapping between component, footprint, and model
frames. [Section 84.1](../resources/BFT_PartSmith_Implementation_Spec.md#841-pdl-example)
has illustrative axis directions but explicitly labels its values illustrative.
Phase 6 requires dimensional/orientation comparison against this contract.

**Proposed resolution:** make handedness, axis directions, origin, PCB plane,
view convention, Euler order, mirror axes, and matrix application explicit.
Add analytical transform fixtures before the first cross-artifact gate.

### R10 — The release-blocker exception is attached to non-warning statuses

**Safety-relevant ambiguity.** [Section 153](../resources/BFT_PartSmith_Implementation_Spec.md#153-blocking-rules)
lists FAIL, HUMAN_REVIEW, and NOT_GENERATABLE as blocking, followed by an
exception for an approved rule allowing a specific warning. The exception
grammatically applies to the blocking list, although none of its entries is
WARN. Sections 113 and 173 prohibit approval with blocking failures; the phase
policy separately defines specification-level waivers.

**Proposed resolution:** make those three statuses unconditionally blocking
under ordinary review. Attach warning allowances only to WARN, and distinguish
product warning policy from a specification/phase-gate waiver.

## P2 findings

### R11 — VRML remains in the normative output list

**Direct conflict.** [Section 13](../resources/BFT_PartSmith_Implementation_Spec.md#13-kicad-compatibility)
lists `*.wrl` under primary native 3D formats. STD-002 and section 10 explicitly
exclude alternate formats from the PartSmith output contract.

**Proposed resolution:** remove `.wrl` from the PartSmith output list, or label
it solely as background about KiCad capabilities. Retain STEP as mandatory.

### R12 — Whether a release may omit 3D is undefined

**Scope ambiguity.** STD-002 and [section 10](../resources/BFT_PartSmith_Implementation_Spec.md#10-3d-model-generation)
use conditional language about components requiring 3D or having sufficient
mechanical information. The IR has `model_3d.required`. In contrast,
[section 113](../resources/BFT_PartSmith_Implementation_Spec.md#113-mvp-release-gate)
and section 236 unconditionally require valid 3D and cross-validation for MVP
completion/release.

**Proposed resolution:** state whether every initial supported release requires
3D. If partial symbol/footprint releases are allowed, define their release
class, required checks, manifest status, and export rules explicitly. The
boolean alone must not bypass release validation.

### R13 — Physical-feature checks are unconditional where geometry is conditional

**Contract conflict.** Sections 10, 99, and 232 qualify lead/pin geometry as
applicable or modeled. [Section 148](../resources/BFT_PartSmith_Implementation_Spec.md#148-footprint--3d-cross-validation)
requires physical counts/positions and thermal-pad comparisons without that
qualification; section 227 expects mapping to physical model leads.
Section 149 also requires every rotation/mirror fault to be detected without
defining treatment of symmetric, geometrically indistinguishable cases.

**Proposed resolution:** define PDL-declared observable features and reference
anchors, applicability rules, and a symmetry policy. Distinguish measured STEP
features from unmeasured declared anchors in reports. The related historical
CR-006 explanation cannot supply current requirements by itself.

### R14 — Repository/package/CLI names are inconsistent

**Direct interface inconsistency.** Product identity and Phase 0 specify
`partsmith`; section 121 imports `partsmith.ir`.
[Section 118](../resources/BFT_PartSmith_Implementation_Spec.md#118-repository-structure)
still describes `board-forge-tools/src/bft`, and
[sections 168–171](../resources/BFT_PartSmith_Implementation_Spec.md#168-cli)
specify `bft component`, `bft pdl`, and `bft doctor`.

**Proposed resolution:** standardize the executable/package on `partsmith` and
rewrite examples, or explicitly define a separately scoped B.F.T. launcher.
Resolve the PDL command spelling before Phase 3 implementation.

### R15 — The minimum identity revision is optional in the schema

**Direct constraint mismatch.** [Section 85](../resources/BFT_PartSmith_Implementation_Spec.md#85-component-variant-identity)
requires Manufacturer + MPN + Package Variant + Documentation Revision.
The incorporated [identity definition](../schemas/component-ir-1.0.schema.json:390)
does not require `source_revision`; source document `revision` is optional too.

**Observed:** deleting both revision fields from the fixture still validates.

**Proposed resolution:** require a resolved documentation revision or an
explicit, provenance-backed policy for unversioned documents. Also specify
where the additional identity qualifiers from section 85 are represented when
applicable, since arbitrary identity fields are rejected.

### R16 — Acquisition is promised, but its operative contract is historical

**Normative coverage gap.** The [product header](../resources/BFT_PartSmith_Implementation_Spec.md:279)
still advertises building with AI or purchasing a released component. The
purchase workflow, exact matching, acquisition states, release verification,
and commerce boundary are specified only in historical ACQ-001–013 and
CR-020–022. The historical boundary explicitly removes their authority.

**Proposed resolution:** either restore the intended acquisition requirements
to current normative sections with a phase/release assignment, or explicitly
defer the feature and update the current product promise. Do not silently
treat the historical purchase rules as executable requirements.

### R17 — Standards review is both completed and contingent on future PDL work

**Readiness inconsistency.** The standards-lock introduction says the final
review was performed before implementation. [STD-014](../resources/BFT_PartSmith_Implementation_Spec.md#std-014--standards-review-completion-criterion)
requires all supported PDL references, schema hierarchy, and hash/invalidation
participation before review completion. Phase 3 starts with the first PDL
entry, and Phase 9 implements dependency invalidation.

**Proposed resolution:** separate a locked standards-role baseline from
package-entry evidence completeness and executable reproducibility checks.
The historical CR-014 resolution already described this distinction but is
not the current governing rule.

### R18 — Multiple roadmaps and corpus gates disagree on scope/order

**Planning gap.** Phases 2–3 implement IR before PDL; section 238 recommends PDL
before IR. Section 235 introduces eight variants in its PDL milestone, whereas
Phase 3 requires one. STD-010 and sections 181/239/240 require an eight-variant
production corpus, but no numbered phase explicitly expands the single 0402
path and verifies all eight before release. Section 236's definition of done
speaks of a single supported golden component.

**Proposed resolution:** designate the numbered phase plan as authoritative,
map the broad milestones to it, and add an explicit corpus expansion/release
gate. Clarify that a single golden component proves the bootstrap, not the
entire declared production corpus. Also identify whether `GOLD-0402-001` in
Phase 3 is the golden fixture or its referenced PDL entry.

### R19 — Replaceable 3D backend is not reconciled with the sole-runtime rule

**Extension-policy ambiguity.** STD-002 selects CadQuery/OCP/OCCT as the sole
3D runtime, while [section 205](../resources/BFT_PartSmith_Implementation_Spec.md#205-pluginextension-model)
says the 3D backend shall be replaceable.

**Proposed resolution:** retain an adapter boundary but specify that supported
replacements must still use the approved runtime, or require an explicit
specification revision and fresh Phase 6 validation for another runtime.

### R20 — Required provenance metadata lacks a structured storage contract

**Schema coverage gap.** STD-011/section 223 require structured standards
identification; [section 221](../resources/BFT_PartSmith_Implementation_Spec.md#221-translation-layer)
requires original/translated text, language, provider, model, and timestamp.
The incorporated standard record permits only `id`, `name`, `revision`, and
`reference`; evidence has no translation record, and unknown fields are
rejected. Separate later stores could satisfy these requirements, but their
linkage to IR/provenance and hashes is unspecified.

**Proposed resolution:** define dedicated versioned records and references,
or extend the schema deliberately. Do not rely on packing multiple mandatory
fields into an opaque name/text string.

## Editorial and traceability issues

- Current normative sections 114–115, the implementation-purpose paragraph,
  and section 244 still describe v0.8/v0.8.2 readiness, despite the v0.9.3
  baseline and integrated Phase 2 contract.
- The document has a 2026-09-19 header and a 2026-09-18 product date without
  distinguishing revision date from original authorship date.
- Section 245 is an empty heading immediately followed by an appendix heading.
- Some current source citations are unresolved tool-generated placeholders,
  not usable references. A standards lock needs retrievable titles, editions,
  URLs or controlled citations, and recorded review dates.
- CODE-001 contains an encoding artifact. Current YAML examples in sections
  6, 17, 51, 122–124, and 151 are not valid instances of the incorporated
  schema; explicitly label abbreviated examples or replace them with valid
  referenced fixtures. Section 121 precedence limits the ambiguity but does
  not make those examples suitable for copy/paste.

## Checks performed and resolution order

Read-only probes used the existing `.env` virtual environment and a deep copy
of `fixtures/ir/valid/0402.json`. They verified the failures and acceptance
described in R01–R04 and R15. No fixtures, application source, or specification
requirements were modified. The existing phase-gate reports were not rewritten.

Recommended order:

1. Resolve the IR/schema conflicts and evidence-resolution lifecycle
   (R01–R04, R06, R15).
2. Fix phase dependencies and canonical state naming (R05, R07, R14, R18).
3. Define build snapshots, hashes, coordinate/reference conventions, and
   release-blocking semantics (R08–R10, R12–R13).
4. Reconcile the remaining output, scope, provenance, and editorial items.
5. Update affected schemas/fixtures/code under the approved contract and rerun
   the relevant gates. Record a specification revision/addendum identifying
   the resolutions rather than relying on a generic precedence statement.

Some conflicts were introduced or exposed by the Phase 2 schema and its
integration. The earlier local PASS proves the recorded fixture checks, not
that these full-spec consistency findings have already been resolved.

## v0.9.4 resolution verification

The subsequent specification revision resolves all 20 findings through the
section 246 decision register. Documentation checks verified all 20 entries,
67 local links across the revised documents, balanced code fences, removal of
current citation placeholders and WRL output, and an unchanged historical
appendix compared with Git HEAD. `git diff --check` passes.

These are documentation checks. Application code, the IR 1.0 schema, fixtures,
and recorded test artifacts were not changed by this resolution pass. IR 1.1
implementation and fresh Phase 2 gate evidence were required at that point;
they are now recorded separately in the [IR 1.1 gate report](gates/phase-2-ir-1.1.md).
