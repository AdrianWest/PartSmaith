# Specification consistency review — v0.9.4

Reviewed: 2026-09-20.

Source: [BFT PartSmith Implementation Specification](../resources/BFT_PartSmith_Implementation_Spec.md), version 0.9.4.

Reviewed source SHA-256: `489a9b64230cc2d1d44fbc7fc295a711c0cf1a5c812ef2fafd0430caf20fd466`.

## Result and scope

The current specification still has contract inconsistencies, underspecified behavior, and stale material. This review records **13 substantive findings and 3 editorial findings**. It does not change the specification, implementation, schemas, or existing gate reports.

All current sections, lines 1–6993, were reread. The historical appendix was reviewed for precedence, structure, relevance, and selected obsolete contracts; its legacy implementations were not independently revalidated. Historical requirements explicitly marked non-normative are not counted as current contradictions. Line references below refer to the source hash above.

The review also compared relevant contracts with the IR 1.1 schema and implementation. Small probes used detached copies of the synthetic `0402` fixture; results are recorded in [the probe evidence](spec-consistency-review-v0.9.4-probes.json). These are targeted counterexamples, not a replacement for the test suite or a full implementation audit.

Priority means:

- **P1:** Resolve before implementing or relying on the affected engineering workflow.
- **P2:** Clarify before accepting the affected phase gate.
- **P3:** Editorial cleanup; no independent reason to fail an engineering gate.

## Substantive findings

### V094-01 — Overrides cannot represent all promised edits — P1

**Type:** Contract/schema mismatch. **Affected work:** IR, override API, pin mapping, placement editing.

Section 88 explicitly covers topology and pin-mapping overrides (lines 3319–3349); sections 172 and 177 provide override and placement-editing interfaces. Section 121.2 requires old/new values to use the target's scalar/quantity type (lines 4444–4446). However, the strict IR schema's override payloads are value/quantity records, while pin electrical types are plain enum strings and placement coordinates are plain numbers. The implementation also requires the target itself to be a value/quantity record.

**Evidence:** Overriding `/pins/0/electrical_type` and `/model_3d/placement/translation_mm/0` both produce `IR_OVERRIDE` at `/overrides/0/path`. Changing the pin's status and binding it to the override does not bridge that mismatch.

**Resolution:** Define the supported override target types and their approval/provenance bindings. Either standardize editable fields as typed records or define a typed patch contract for enum, boolean, numeric, vector, and topology edits. Coordinate any schema revision with migration and gate tests; do not solve this by accepting arbitrary untyped JSON.

### V094-02 — Evidence relevance is required but has no enforceable representation — P1

**Type:** Missing contract. **Affected work:** IR generation precheck and evidence selection.

Section 121.2 says selection cannot dismiss unresolved evidence relevant to a required value without an explicit resolution (lines 4428–4446). Section 124's evidence contract does not identify the engineering targets to which a piece of evidence is a candidate. The selected value's evidence references therefore serve both as selection and, in practice, as the available relevance information.

**Evidence:** A required body width linked to conflicting evidence blocks generation with `IR_UNRESOLVED`. Removing only that evidence link makes generation validation pass, while the conflicting evidence remains in the IR and `resolutions` remains empty.

Unrelated historical evidence is intentionally allowed and should remain allowed. The gap is the inability to distinguish unrelated history from a relevant conflict silently removed from the active selection.

**Resolution:** Define candidate evidence-to-target relationships independently of selected evidence, or define a revision-transition validator that detects dismissal. Specify how relevance is established, retained, and explicitly resolved.

### V094-03 — Successive resolution decisions have no defined history lifecycle — P2

**Type:** Ambiguous lifecycle with an implementation limitation. **Affected work:** IR revisions and repeated human review.

Section 121.2 preserves immutable historical records and creates a new IR revision for approved decisions (lines 4436–4446). Its resolution fields have no active decision selector, revision binding, or reference to a superseded resolution. It does not say whether old resolutions remain in the new IR's `resolutions` array or exist only in prior revision snapshots.

**Evidence:** One approved resolution for a target validates. Retaining it while adding a second approved decision selecting newly acquired evidence produces `IR_RESOLUTION` errors: the old selection no longer matches the current value and the target has multiple approved resolutions.

**Resolution:** Choose and document one history model. Either retain decisions inline with explicit active/superseded resolution relationships, or keep only current decisions in each snapshot and define immutable prior-revision retrieval. Historical approvals must not be rewritten to make the latest revision validate.

### V094-04 — Override binding creates a cycle under the stated recursive hash rule — P1

**Type:** Contradictory reference semantics. **Affected work:** Phase 8 snapshot construction and Phase 9 dependency hashing.

Section 121.2 binds a `USER_OVERRIDE` value to its approved override. Section 166 includes selected override new values in the input snapshot, replaces reference IDs with recursively referenced content hashes, and rejects cycles (lines 5538–5549).

**Evidence:** A valid quantity override is accepted with `overrides[0].new_value.override_id` equal to that override's own ID. Applying the stated recursive replacement to this reference creates a self-cycle. The current provenance traversal already treats this binding differently from ordinary dependencies, but the hash projection contract does not state that exception.

**Resolution:** Define which references are dependency edges, target bindings, and history links. Specify precisely how binding references appear in canonical projections without recursive self-hashing, and add golden projection examples. This finding concerns future snapshot/dependency hashing, not the existing whole-record `ir_hash` function.

### V094-05 — The transform record cannot represent every required composition or inverse — P1

**Type:** Mathematical representation gap. **Affected work:** Phase 6 transform library.

Section 92 permits independent positive X/Y/Z scale factors and defines composition/inversion (lines 3463–3488). Section 150 offers only translation, Euler rotation, scale, and mirror fields while requiring `compose()` and `invert()` (lines 5191–5215). Return types and handling of nonrepresentable results are unspecified.

**Evidence:** In two dimensions, let `S = diag(2, 1)` and let `R` have rows `(3/5, -4/5)` and `(4/5, 3/5)`. Both are allowed transforms. Their composition `S * R` has rows `(1.2, -1.6)` and `(0.8, 0.6)`; its column dot product is `-1.44`. A rotation-times-diagonal-scale/mirror matrix has orthogonal columns, so this composition cannot be stored in the declared record. The same issue occurs in three dimensions and can affect inverses.

**Resolution:** Use an affine matrix for composed/inverse transforms, or restrict allowed scaling/composition and explicitly reject results that cannot be represented. Define the public return types and round-trip behavior. Do not silently approximate shear with Euler angles and scale.

### V094-06 — Required applicability cannot be stored in the validation-result contract — P1

**Type:** Contradictory result contracts. **Affected work:** IR validation reports and Phase 7 cross-validation.

Section 148 requires justified `NOT_APPLICABLE` in a separate applicability field, explicitly not a new status (lines 5173–5176). Section 152's result contract omits that field (lines 5234–5259). The strict IR 1.1 result schema also omits it and rejects additional fields.

**Evidence:** Adding `applicability: NOT_APPLICABLE` to an otherwise valid result produces `IR_SCHEMA` at `/validation/results/0`.

**Resolution:** Define applicability, justification, and fixture/PDL binding in the result schema, including its relationship to status and measurements. If artifact validation uses a separate output schema, version and reference it explicitly and define how reports are copied into a later IR audit record. Neither an invented PASS nor an omitted check satisfies section 148.

### V094-07 — Validation order does not clearly cover finalized artifact bytes — P2

**Type:** Incomplete workflow contract. **Affected work:** Phase 8 association, validation, and release.

Section 11's required workflow validates before creating/finalizing the KiCad 3D association (lines 1415–1429). Section 141 likewise attaches the final reference after validation (lines 5005–5008). That operation changes the footprint bytes. Sections 166–167 bind validation and approval to exact released artifact hashes (lines 5533–5535 and 5566–5572), but do not explicitly distinguish preliminary geometry validation from checks of the finalized association and released files.

**Impact:** One implementation may validate the final reference path and placement; another may attach them after its last compatibility check and reuse an earlier result. Section 167 allows a correct interpretation but does not make the required sequence explicit.

**Resolution:** Specify: independent geometry checks, association/finalization, validation of final files and references, hash freezing, manifest creation, and approval. Define which results can be reused and which become stale when finalization changes bytes.

### V094-08 — Manifest validation has an unspecified dependency cycle — P2

**Type:** Incomplete hash/validation graph. **Affected work:** Phases 8–9.

Section 155 includes `ManifestValidator` and `ReproducibilityValidator` among minimum validators (lines 5285–5302). Section 167 creates the manifest after validation, and section 166 includes semantic validation in its hash (lines 5534–5535 and 5566–5571). Neither defines which validator results are inside that manifest and which validate it afterward.

**Impact:** Including the manifest's own validation result in its input hash can create an indirect cycle, even though section 167 correctly forbids a direct self-hash field. Reproducibility validation also needs a defined comparison stage and output location.

**Resolution:** Define an acyclic sequence of pre-manifest checks, manifest construction, and post-manifest verification. Explicitly list the result categories included in each content hash and place later verification records outside the object they verify.

### V094-09 — Backend equivalence is not reconciled with downstream hash equality — P2

**Type:** Conflicting determinism criteria. **Affected work:** Phase 9 reproducibility gate.

Section 188 permits measured backend equivalence instead of matching artifact bytes, while comparing `validation_semantics_hash` and `engineering_manifest_hash` and referring to identical deterministic content (lines 5933–5940). Section 166 defines artifact hashes over exact bytes and includes those hashes in validation semantics and the manifest (lines 5533–5535).

**Impact:** Two equivalent STEP files with different bytes have different artifact hashes. Under the stated scopes, those differences propagate to the validation and manifest hashes. The artifact-equivalence exception does not explain how the downstream comparisons should pass.

**Resolution:** Either require byte identity for builds whose downstream hashes must match, or define the exact comparison/projection used for permitted equivalence and its effect on all dependent hashes. Preserve original byte hashes and measured equivalence evidence in either case.

### V094-10 — A required viewer step conflicts with the headless build path — P2

**Type:** Workflow/scope inconsistency. **Affected work:** Phase 8 headless pipeline and Phase 12 UI.

Section 11 requires placement in the B.F.T. 3D Viewer before automated cross-validation (lines 1424–1425). Section 116 requires a headless build, while the numbered plan implements the headless pipeline before the UI. The current workflow does not label its viewer step as interactive-only.

**Resolution:** Define automated placement/cross-validation as the required engineering operation and make viewer inspection part of the interactive review path. State how explicit approval is recorded in CLI/headless operation. Keep the numbered phase plan authoritative.

### V094-11 — Advisory MVP lists still imply a broader acceptance scope — P2

**Type:** Scope ambiguity, not equal-authority hard contradictions. **Affected work:** PDL, acquisition, and provider acceptance planning.

The locked eight-variant release scope is narrower than section 31's “Initial MVP” / “Suggested initial test families,” which include through-hole packages, connectors, QFP, BGA, and others (lines 2204–2234). Section 14 calls multiple AI providers initial targets, while Phase 11 gates a configured provider. Section 50 lists eight initial languages without making clear which are mandatory gate coverage versus intended capability. Section 98's recommendation to target accuracy class A also needs an explicit relationship to the release-class-dependent measurements in section 148.

The phase/standards precedence rules help resolve the package conflict, but readers still have to infer which introductory promises apply to the first release. Historical scope resolutions cannot supply missing current requirements.

**Resolution:** Provide one release acceptance matrix for variants, accuracy class, providers, languages, and fixtures. Label broader lists as future examples or optional coverage, and link them to that matrix. Do not expand the implemented scope merely because an advisory list remains in the document.

### V094-12 — Terminal count, exposed-pad count, and pad-shape count are conflated — P2

**Type:** Topology/counting ambiguity and conditional rule conflict. **Affected work:** Phase 3 PDL and footprint/mapping validators.

Section 84.1's QFN example has `pin_count: 16`, four pins on each side, and thermal-pad support (lines 3134–3163), without specifying whether an exposed conductive pad becomes an additional numbered terminal. Section 148 conditionally permits multiple grouped pad shapes for one terminal (lines 5170–5171), while section 231 unconditionally requires every pad to have a unique number and a correct pad count (lines 6650–6656). The IR separately equates package pin count with the pin records.

**Impact:** Implementations can disagree on QFN terminal counts and whether a compound terminal represented by several pad shapes is legal. A single compound serialized pad might satisfy both rules, but that required representation is not stated.

**Resolution:** Define separate physical terminal, symbol pin, numbered conductive pad, and geometric pad-shape concepts. Specify exposed-pad numbering and mapping for every supported PDL variant, and qualify the uniqueness/count rules for explicitly supported compound representations.

### V094-13 — Evidence rectangles have no coordinate convention — P2

**Type:** Missing provenance contract. **Affected work:** Phase 10 extraction and Phase 12 evidence overlays.

Section 124 stores a page and `region` containing X, Y, width, and height (lines 4591–4609). Sections 130–131 require OCR and bounding boxes. The current contract does not bind these rectangles to units, origin, page rotation/crop, or the transform from rendered-image pixels to the original page.

**Impact:** Identical numbers can refer to different page areas after rendering at a different DPI, rotating a page, or changing the crop. The source hash alone cannot disambiguate these coordinate systems.

**Resolution:** Choose a canonical document-page coordinate system and define page numbering, units, origin, axis directions, rotation, crop handling, and pixel conversion. Record any needed render/transform metadata so an evidence overlay is reproducible.

## Editorial and relevance findings

### V094-14 — Historical material dominates the active implementation document — P3

The historical appendix occupies **5,467 of 12,460 lines (43.9%)**. Its old SQL, schemas, architecture drafts, alternative backends, and conflict-resolution logs retain traceability value, but are irrelevant as instructions for current implementation. They are explicitly non-normative and are not new technical contradictions.

**Resolution:** Move the appendix intact into a versioned archive and link it from the current spec. Preserve the previous review and resolution history. Do not delete useful source evidence or treat the archive's old requirements as active scope.

### V094-15 — Repeated explanations and obsolete planning prose obscure the governing contracts — P3

Examples include:

- Independent-artifact rules repeated across STD-002, sections 10–12A, and sections 89–90.
- Provider interfaces presented at different abstraction levels in sections 15 and 133 without a clear explanatory-versus-implementation distinction.
- Standards “eventually” / investigation language in section 30 despite the later locked standards decisions and section 121.5.
- The manufacturer land-pattern flow repeated consecutively in section 142.
- Output trees in sections 32, 116, 174, and 175 without consistently distinguishing a workspace, component bundle, and exported library.
- Repeated reference lists instead of a single maintained reference register.

These are not all independent contradictions: many examples are explicitly illustrative. Their duplication increases the chance of the next revision fixing only one copy.

**Resolution:** Keep one normative definition per contract and replace other copies with short explanations and links. Label output layouts by purpose, remove duplicate prose, and replace completed planning notes with decisions or explicit remaining work.

### V094-16 — Version labels, examples, and navigation still carry stale details — P3

The historical boundary calls the controlling current baseline v0.9.3 (lines 7000 and 7010), although the document is v0.9.4. Older “Proposed” and documentation-complete language can be mistaken for current implementation status. Current section numbering jumps from 58 to 84, while the missing numbers appear in historical material. Illustrative electrical-type tokens such as `power_input` and `POWER_INPUT` differ from the current canonical `power_in` token.

The explanatory-example exemption prevents those token examples from overriding the schema, but they remain poor implementation examples.

**Resolution:** Update boundary/status labels, align examples with current tokens, add a current-section table of contents, and preserve stable section identifiers when improving navigation. Date volatile provider-capability statements and link their primary sources.

## Items checked but not flagged as false

- The GitHub Models retirement statement is supported by GitHub's [official retirement announcement](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/). Its presence is not a factual contradiction; its date and reference should remain explicit.
- KiCad 10 packed/unpacked symbol-library support is documented in the [official schematic editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html). Do not remove the requirement on the assumption that it is obsolete or invented.
- Non-normative historical OpenSCAD/VRML wording does not override the current backend and artifact decisions.
- Future-phase functionality being unimplemented is not, by itself, a defect in the specification or a failed Phase 2 gate.

## Consequences for development and gates

The existing Phase 2 IR 1.1 gate records remain evidence that their recorded tests passed. This review identifies coverage and contract gaps; it does not retroactively change those results or establish that every promised workflow is supported.

Resolve V094-01 through V094-04 and V094-06 when revising the IR contract, then update the schema, migration policy, implementation, fixtures, and gate coverage together as applicable. Settle the release matrix and terminal-count rules before accepting Phase 3. Settle transform representation before Phase 6, applicability before Phase 7, and the finalization/hash graph before Phases 8–9. Define evidence coordinates before acquisition and overlay acceptance.

Recommended order: agree on the contract decisions, revise their single authoritative definitions, update dependent code and tests, and then refresh affected gate evidence. Archive and navigation cleanup can proceed separately without changing engineering requirements.
