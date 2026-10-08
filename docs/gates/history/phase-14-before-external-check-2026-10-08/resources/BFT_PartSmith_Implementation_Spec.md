# PartSmith Implementation Specification

**Specification version:** v0.9.8
**Status:** Phase 13 PASS; Phase 14 online PCM candidate, gate OPEN
**Document date:** 2026-10-08

**Revision purpose:** Target KiCad 10.0.6's bundled Windows AMD64 Python
3.11 for online PCM candidate 0.3.1. No external Python installation or offline
dependency supply is required. Historical Python 3.12 receipts and their lock
retain their original scope. This migration does not grant Phase 14 PASS.

**Previous revision purpose:** Incorporate the project owner's requested R13-01 work
into Phase 13, review the current launch plugin and retained data, and make
installation contracts, plugin/IPC boundaries, publication and acceptance
explicit. Phase 13 now proceeds through eight ordered milestones. Its first
milestone delivers the missing contracts and their revalidation; later
installation work depends on that milestone's recorded PASS.
Component IR 1.2, canonical JSON profile 1.0, snapshot profile 1.2, placement
convention 1.1 and the CadQuery runtime selection retain their existing
versions. This revision changes delivery ownership and fills integration
requirements; implementation evidence retains its recorded runtime scope.
The [v0.9.6 specification snapshot](history/BFT_PartSmith_Implementation_Spec_v0.9.6_before_Phase13_2026-10-05.md)
preserves the previous contract assignment and gate requirements.

**Phase 13 PCM correction, 2026-10-05:** KiCad's Plugin and Content Manager
(PCM) ZIP is the customer plugin installation artifact. Milestone 13.2 now
defines package/runtime preparation and the PCM lifecycle; 13.7/13.8 require
real installed-package acceptance. The subsequent project-owner correction
removes PartSmith wheel builds/tests from Phase 13; source, PCM payload and
installed PCM runtime checks are its validation paths. This is an addendum to
v0.9.7; that requirements revision did not itself assert runtime implementation
or Phase 13 PASS. Current implementation receipts are listed below. See the
[installation correction](../docs/spec-phase-13-pcm-installation-update-2026-10-05.md)
and [pre-correction snapshot](history/BFT_PartSmith_Implementation_Spec_v0.9.7_before_PCM_2026-10-05.md).
The [PCM-only validation update](../docs/spec-phase-13-pcm-only-update-2026-10-05.md)
and [pre-retirement snapshot](history/BFT_PartSmith_Implementation_Spec_v0.9.7_before_PCM_only_2026-10-05.md)
preserve the explicit removal of the former internal wheel requirement.

## v0.9.8 Normative Baseline

Current sections and numbered phase gates are authoritative. Abbreviated
YAML/JSON and directory examples explain those contracts; they are not
alternative schemas. Historical material is preserved unchanged in the
[non-normative archive](history/BFT_PartSmith_Historical_Appendix_v0.9.4.md).
Version labels inside that archive describe its original context only.

**Implementation status:** Repository receipts cover the implemented Phases
0–13 within their stated platforms and test scopes. Phase 12's R12-01/R12-02
corrections have source and installed-wheel regression evidence. The existing
legacy KiCad entry is a launch-only action plugin; native CLI validation, immutable
release/revision bundles and desktop session transport are implemented.
Phase 13.1 installation contracts, golden/negative fixtures, trusted source
resolution and isolated offline PCM-layout checks are implemented. The
[13.1 receipt](../docs/gates/phase-13.1-artifacts.json) records their scoped PASS.
A customer PCM package, pinned managed runtime and official PCB IPC client are
implemented in 13.2. Planning, exact native staging and fresh installation
authorization are implemented in 13.3–13.5; complete owned NTFS publication,
reconciliation and rollback in 13.6; deliberate desktop controls and actual
native/IPC round trips in 13.7. Final source/PCM/desktop/offline acceptance,
three PDF stability rounds, exact final PCM lifecycle and affected-hash closeout
are recorded in [13.8](../docs/gates/phase-13.8.md) and the
[full Phase 13 gate](../docs/gates/phase-13.md), 2026-10-07.
See the
[current plugin/data review](../docs/spec-phase-13-review-v0.9.7.md) and
[Phase 12 handoff](../docs/gates/phase-12.md).

Earlier [IR 1.1](../docs/gates/phase-2-ir-1.1.md),
[IR 1.2](../docs/gates/phase-2-ir-1.2.md), PDL and later gate receipts retain
their original specification versions, fixture limitations and runtime scopes.
Refreshing a current input map does not recertify their historical binaries or
test runs. Phase 14 still owns production packaging and the full package matrix.

## Current-section navigation

Section numbers are stable identifiers, not a continuous implementation checklist.
The numbered phase plan is the sole gate/order authority.

- [Implementation strategy and phases](#implementation-strategy--small-testable-increments)
- [Standards and runtime baseline](#v097-standards-lock-and-implementation-baseline)
- [Scope and release matrix](#31-component-package-types)
- [Independent artifact workflow](#11-independent-footprint-and-3d-generation)
- [IR contract, migration, and provenance](#121-component-ir-json-schema-and-contract)
- [Transforms](#92-transform-contract)
- [Evidence regions](#1241-canonical-source-regions-document-page-10)
- [Validation results](#152-validation-result-contract)
- [Build hashes and finalization](#166-reproducible-build-algorithm)
- [Input and release review services](#172-review-decision-api)
- [Installation aggregates](#1741-installation-aggregates-and-approval-boundaries)
- [Phase 13 milestones](#phase-13--kicad-integration)
- [Portable replay bundles](#175-project-packaging)
- [Release milestones](#235-implementation-milestones)
- [Finding resolutions](#246-consistency-resolution-register)
- [External references](#247-external-reference-register)
- [Historical archive](history/BFT_PartSmith_Historical_Appendix_v0.9.4.md)

# Implementation Strategy — Small, Testable Increments

PartSmith implementation shall proceed in small increments with a
working, testable result at every step. The project shall not begin with
the AI interpretation layer.

## Phase-gate policy

Every phase has a **blocking phase gate**. A phase gate passes only when
every numbered work item in that phase is complete, every listed gate
condition passes, and the commands, artifact hashes where applicable,
and test results are recorded in the repository or CI evidence.

Implementation work for the next listed phase shall not begin until the
preceding listed phase has a recorded PASS. Phase 9.5 follows Phase 9 and
must pass before Phase 10 begins. A failing, skipped, unrecorded, or manually assumed
check is a gate failure. A waived gate requires an explicit specification
revision that identifies the risk owner, scope, rationale, and expiry;
a waiver is not a PASS.

The v0.9.7 sequencing decision moves section 174.1's installation-contract
delivery from Phase 8 to Phase 13.1, at the project/specification owner's
request on 2026-10-05. Phase 8 retains immutable release and bundle verification;
Phase 12 retains its full desktop gate. R13-01 was reassigned to 13.1 and is
**RESOLVED** by the [13.1 contract checkpoint](../docs/gates/phase-13.1.md),
2026-10-06, after source/isolated-PCM validation and affected-hash closeout.
The [13.2 adapter/PCM checkpoint](../docs/gates/phase-13.2.md) records real
PCM lifecycle, prepared-runtime recovery, live PCB reads and complete-project
NTFS feasibility with final affected-hash closeout. The
[13.3 planning/store checkpoint](../docs/gates/phase-13.3.md) records pure
planning, safe target inventory and forward-migration preservation, with 188
passing checks and affected-hash closeout. The
[13.4 semantic staging checkpoint](../docs/gates/phase-13.4.md) adds
deterministic packed libraries and actual native SVG/STEP validation with
exact engineering preservation. The
[13.5 review checkpoint](../docs/gates/phase-13.5.md) adds exact fresh
authenticated installation decisions, durable cancellation/retry semantics and
native fixture evidence with affected-hash closeout. The
[13.6 publication checkpoint](../docs/gates/phase-13.6.md) implements complete
owned NTFS publication, real process-crash reconciliation and fresh rollback
with current mutable-file preservation. Its source/native evidence and affected
hash closeout permit 13.7. The
[13.7 workflow checkpoint](../docs/gates/phase-13.7.md) adds deliberate desktop
controls, authority-free saved references and actual two-component native/IPC
round trips through PCM-installed 0.1.9. The
[13.8 acceptance checkpoint](../docs/gates/phase-13.8.md) and
[full Phase 13 receipt](../docs/gates/phase-13-artifacts.json) record all final
source/PCM/desktop/offline/PDF checks and affected active/CI hash verification.
The complete gate permits Phase 14; clean-machine online installation
remains that separate phase's responsibility.
The subsequent PCM 0.1.10 startup correction opens setup directly. Board
selection and read-only PCB inspection require the deliberate **Inspect PCB...**
action; **Refresh** performs the component read after exact-instance and
exact-board verification. Startup never selects or inspects a board, and an
inspection failure leaves setup available. The frozen 0.1.9 acceptance evidence
retains its original scope.
PCM 0.1.11 binds PartSmith to the exact launching KiCad process. Closing editors
while its project manager remains open permits the existing library publishing
workflow. Host process exit closes owned windows without a save/discard prompt and
retains unfinished work through recovery and cooperative worker cleanup.
The setup window excludes the 0402 rendering prototype launcher; the prototype
remains available to its development verification harness. The repository's
`install_partsmith.bat` builds and installs the current verified PCM payload
with KiCad closed, retaining backups outside plugin discovery and preserving
other packages and the managed runtime. This prepared-checkout helper does not
claim Phase 14 clean-machine production installation acceptance.
Historical v0.9.6 findings remain
available in the archived specification and review receipts.

## Phase 0 — Repository and build foundation

1. Create the independent `partsmith` repository structure.
2. Establish versioning, formatting, linting, and test execution.
3. Establish CI and deterministic test commands.
4. Add a minimal application entry point.
5. Add `partsmith version` and `partsmith doctor`.

**Phase 0 gate (blocking):** From a clean checkout, supported Python can
install the project and development dependencies; the test suite, linter,
and format check pass; `partsmith version` reports the packaged version;
and `partsmith doctor` returns PASS. CI runs these commands.

## Phase 1 — Persistence foundation

1. Create SQLite connection handling.
2. Enable foreign keys.
3. Create migration 001.
4. Implement projects/components/build records.
5. Add migration tests.

**Phase 1 gate (blocking):** Automated tests create an empty database,
enable and verify foreign-key enforcement, apply migration 001 exactly
once, reopen it, and create/query project, component, and build records.

## Phase 2 — Component IR

The authoritative Phase 2 contract is
[section 121](#121-component-ir-json-schema-and-contract), including the
versioned machine-readable schema and canonical profile 1.0.

1. Implement Component IR 1.2 and explicit migration from IR 1.0/1.1 per section 121.
2. Implement canonical serialization.
3. Implement schema validation.
4. Implement units and numeric normalization.
5. Implement IR hashing.

**Phase 2 gate (blocking):** A known-good IR fixture passes schema,
unit/number normalization, canonical serialization, and stable-hash
tests. Each invalid IR fixture fails the intended validator
deterministically. The gate also covers missing quantities without fabricated
numbers, active-versus-historical evidence, the canonical enums, documentation
revision identity, structured provenance, and explicit migration failure when
required information cannot be recovered. Old-version fixtures remain intact.
IR 1.2 coverage additionally includes typed pin/placement overrides, independent
candidate relevance, successive immutable decisions with active selectors,
revision-transition validation, applicability/result fields, and document-page
coordinates. Negative cases prove that dropping an evidence selection cannot
dismiss a relevant conflict. Hash-projection golden cases in section 166 must
also pass; this does not require implementing the Phase 8 orchestrator.

## Phase 3 — PDL

1. Implement PDL schema.
2. Implement PDL loader/versioning.
3. Implement PDL validation.
4. Add the first PDL entry: 0402.
5. Add PDL inspection CLI support.

**Phase 3 gate (blocking):** The PDL entry referenced by golden component
fixture `GOLD-0402-001` loads through the versioned PDL loader;
`partsmith pdl inspect <pdl-id>` reports that entry; valid PDL tests pass; and
each invalid/topologically incorrect PDL fixture fails deterministically.
The schema distinguishes peripheral leads, exposed terminals, terminal groups,
and pad shapes under section 93 and pins the section 31 release profile.

## Phase 4 — Deterministic symbol generation

1. Define symbol generator interface.
2. Implement deterministic KiCad symbol serialization.
3. Generate a known-good 0402 component symbol.
4. Validate pin numbering and symbol structure.
5. Implement the input-only validation path in section 137 before generation.
6. Implement the symbol's trusted IR/configuration projection under snapshot
   profile 1.2 (section 166), preserving the profile 1.1 API and golden evidence.

**Phase 4 gate (blocking):** The known-good 0402 IR/PDL input generates
a syntactically valid KiCad symbol with valid pin numbering and structure.
At least two independent runs produce byte-identical output.
Projection tests prove that symbol inputs and declared serializer/generator
convention changes invalidate its dependency hash, while unrelated CAD-only
settings do not. Symbol
generation requires no fabricated or installed CAD runtime tuple.

## Phase 5 — Deterministic footprint generation

1. Define footprint generator interface.
2. Implement 0402 land-pattern generation.
3. Generate native `.kicad_mod`.
4. Validate pads, numbering, courtyard, and required graphics.
5. Implement the footprint's snapshot-profile-1.2 dependency declaration.

**Phase 5 gate (blocking):** The known-good 0402 input generates a native
`.kicad_mod`; all pad, numbering, courtyard, required-graphic, and
footprint-format validators pass.
Changing a consumed land-pattern input invalidates the footprint dependency;
CAD-only settings do not. Association dependencies are tracked separately.

Phase 5 is the deterministic 0402 bootstrap gate, not the completion gate for
the full footprint feature list in section 8. Its required subset is SMT pad
count, numbering, supported pad shape, dimensions, positions, copper/paste/
solder-mask layers, courtyard, fabrication graphics, silkscreen reference and
value fields, native format markers, and land-pattern provenance. Thermal and
exposed pads, through-hole drills, custom pad geometry, advanced mask/paste
settings, and general footprint properties remain later extensions unless a
PDL fixture explicitly supplies and tests them. Phase 14 is the production
acceptance gate for the complete package matrix; the 0402 bootstrap must not be
described as production coverage for all package variants.

## Phase 6 — CadQuery 3D backend spike

This phase answers the critical CAD-runtime questions before broader
implementation.

1. Implement the versioned CadQuery 3D-generator adapter.
2. Create a minimal 0402 PDL geometry fixture.
3. Prototype the CadQuery/OCP/OCCT backend.
4. Produce a valid STEP artifact directly from CadQuery geometry.
5. Parse and validate STEP.
6. Compare dimensions and reference geometry against PDL using defined
   measurement tolerances and the coordinate contract.
7. Record backend/runtime versions and dependency hashes.
8. Measure installation/runtime packaging feasibility.
9. Implement sections 92/150 placement-to-affine conversion, composition,
   inversion, nonuniform-scale/shear, adapter-rejection, and round-trip tests.
10. Implement the model's snapshot-profile-1.2 dependency declaration and compare
    STEP bytes from two clean independent exports under the same pinned tuple.

**Phase 6 gate (blocking):** The CadQuery backend consumes the 0402 IR/PDL
and exports a parseable, dimensionally valid STEP artifact from the intended
packaged PartSmith environment. The recorded comparison includes body
length, width, height, terminal/pin-1 anchor positions, orientation,
expected-solid count, reference coordinate system, comparison algorithm, and
explicit tolerances. All CadQuery/OCP/OCCT runtime versions, dependency
hashes, and packaging-feasibility results are recorded.
The two exports run in separate fresh processes/work directories with the same
frozen fixture and settings, without a generated-artifact cache. Final STEP
SHA-256 values must match exactly. Record the algorithm/version/settings of any
deterministic metadata normalization and reparse/remeasure its output before hashing; normalization
must not conceal geometry changes. A byte mismatch fails Phase 6 even when
geometry is equivalent. CAD settings invalidate model dependencies; placement-only
edits preserve canonical STEP dependencies. Phase 9 still tests the whole build.

## Phase 7 — 3D validation and cross-validation

1. Implement STEP parsing/validation.
2. Implement scale validation.
3. Implement height validation.
4. Implement orientation validation.
5. Implement pin-1 validation.
6. Implement footprint-to-3D alignment validation.
7. Add deliberate offset/rotation/mirror/scale fault fixtures.

**Phase 7 gate (blocking):** Valid STEP geometry passes scale, height,
orientation, pin-1, and footprint-alignment validation. Every injected
offset, rotation, mirror, scale, height, and pin-1 fault that changes a
required observable or declared placement fails with its intended result.
Symmetry-equivalent geometry is tested separately under sections 148–149; it
is not counted as a detected fault. Section 152 applicability records must
validate, bind to pinned declarations, and distinguish measured success from
justified non-applicability.

## Phase 8 — First complete deterministic component

1. Validate IR/PDL and freeze input/dependency hashes under section 166.
2. Generate symbol, footprint, and STEP independently; run preliminary checks.
3. Implement the orchestrator and persisted states in section 159.
4. Finalize associations, then run final artifact, mapping, cross-validation,
   and mandatory native target-KiCad CLI compatibility checks on the released
   bytes under section 167. Internal syntax parsers are preliminary checks and
   cannot satisfy this requirement.
5. Freeze artifact hashes and construct the deterministic engineering manifest.
6. Run post-manifest verification; store its results outside that manifest.
7. Implement headless approval/rejection bound to exact manifest/artifact hashes.
8. Package/export only verified, explicitly approved bytes; test invalidation
   when associations, paths, geometry, or approval bindings change.
9. Implement section 172's input-review/proposal/revision operations and section
   163's immutable SQLite store using a forward migration.
10. Implement section 175's history-complete bundle index and import validation,
    preserving immutable source bytes. Section 174.1's installation contracts
    are delivered and revalidated in Phase 13.1 under the v0.9.7 sequencing
    decision; they are not a Phase 8 or Phase 12 entry prerequisite.

**Phase 8 gate (blocking):** One known-good component completes the pipeline
without AI, passes all applicable validators and native target-KiCad CLI
compatibility checks, and receives explicit recorded human approval through
the headless service. The gate environment shall contain the requested KiCad
major version. Missing or wrong-version `kicad-cli` is a blocking failure;
PartSmith's internal parsers cannot be substituted for native compatibility.
The Phase 8 reference gate pins KiCad 10.0.6. A different patch version
requires regenerating native compatibility and gate evidence.
The approved package and manifest exist. Negative approval tests prove that
blocking results or stale final-byte checks cannot become APPROVED. CI may replay a recorded decision
only when it is bound to the exact input and artifact hashes being checked.
Phase 12 adds UI to these services; Phase 13 expands integration.
Tests also cover review before artifacts exist, stale-base rejection, immutable
pending proposals, transaction rollback, multi-revision bundle export/import,
and missing/tampered parents or inventories. A silkscreen-only edit preserves
STEP but invalidates checks bound to old footprint bytes and release approval.

## Phase 9 — Reproducible builds

Extend the snapshot/hash recording established in Phase 8 with selective reuse,
invalidation, and clean-build reproducibility verification.

1. Hash all required inputs.
2. Canonicalize structured inputs.
3. Record generator/backend/runtime versions.
4. Implement dependency invalidation.
5. Rebuild identical fixtures.
6. Compare hashes.
7. Rebuild an imported multi-revision OFFLINE_COMPLETE bundle with network
   disabled, and test per-node configuration invalidation under section 166.

**Phase 9 gate (blocking):** Two clean builds with identical canonical
inputs and pinned runtime have identical input-snapshot, artifact, semantic
validation-result, and engineering-manifest hashes under sections 166/188.
Measured geometry equivalence cannot substitute for byte identity at this gate.
The comparison report is post-manifest audit evidence. Run IDs and
wall-clock timestamps are compared as audit metadata, not deterministic content.
CAD-only updates preserve unrelated generator dependencies; validator-only
updates rerun affected checks without regenerating unchanged engineering files.
Required replay objects must be available locally and verified before execution.

## Phase 9.5 — wxPython setup and processing GUI

Provide a launchable setup GUI using **wxPython (wx)**. The same GUI shall
launch either from KiCad through a supported, version-tested launch integration
or independently through a Python script. Keep processing in shared PartSmith
services so both launch paths use the same configuration and workflow.

1. Add a standalone Python launcher and a KiCad launch entry. Document the
   commands, installation steps, and supported runtime for both launch paths.
   The KiCad entry shall launch the PartSmith runtime defined by the runtime
   baseline; it shall not require loading CAD dependencies into KiCad's Python
   process. This phase covers launching the setup GUI; broader live KiCad
   operations remain in Phase 13.
2. Display `resources/PartSmith-Banner3.png` as a banner at the top of the
   Phase 9.5 main window, spanning its complete client-area width at `(0, 0)`
   without side margins or padding. The banner shall reach both client edges
   and expand or shrink with the GUI while preserving the entire image and
   its aspect ratio. Size its height proportionally from the loaded image.
   Keep the banner outside scrollable controls and resolve its packaged
   location independently of the current working directory for both launch
   paths. The separate Phase 12 viewer shall have no banner.
3. Add a **Set AI API Key** button. Clicking it opens a modal dialog with a
   password-style text box and **OK** and **Cancel** buttons. The text box
   shall always open blank, including when a key has already been saved;
   never prefill, retrieve for display, or reveal the saved key. Typed input
   shall be masked, with no reveal control. **OK** with a nonblank key shall
   save or replace the configured provider's key in the operating system's
   secure credential store under AI-001–AI-003 and section 34. Blank input
   shall show a validation message without changing the saved key. **Cancel**
   shall discard the input without changing the saved key. Close the dialog
   only after a successful save or cancellation; report save failures without
   exposing credentials. The main window may show only a configured/not
   configured status and the provider identity. Never log entered or saved
   keys, include them in exception text, or persist them in ordinary settings.
4. Add a **Select Datasheet** button that opens a file chooser for a local PDF
   datasheet to be processed. Show the selected file path in a read-only field.
   Cancelling the chooser shall preserve any previous selection. Check that
   the selected file exists and is readable before starting processing.
5. Add a labeled **Required Part Number** text box for the full manufacturer
   part/order number the user needs from the selected datasheet, including
   suffixes that identify the package variant. A datasheet may cover multiple
   package styles; the required part number determines which package, pinout,
   and package dimensions to extract and use. Require a nonblank value before
   Start and preserve the complete part number when passing it with the
   selected source to the processing service. Once extraction is available,
   resolve the package using the datasheet's ordering information or
   part-number/package mapping. An unrecognized or ambiguous mapping shall
   produce a clear review/error status and block package-dependent generation
   until resolved; never silently choose the first or a default package.
6. Add a read-only, multiline, scrollable log text box at the bottom of the
   GUI. Route script/service progress, warnings, errors, and completion or
   cancellation messages to this box while work is running. Include captured
   subprocess output where scripts are used, applying credential redaction
   before display or persistence. Update wx controls on the GUI thread and
   run processing outside that thread so the window remains responsive.
7. Add **Start** and **Cancel** buttons above the bottom log box. Start shall
   validate the inputs and launch at most one processing job at a time;
   prevent duplicate starts and changes to job inputs or credentials while
   running. Cancel shall request cancellation of the active job, stop managed
   child work safely, log the resulting status, and return the GUI to an idle
   state. Disable Cancel when no job is running. Closing the window during a
   job shall use the same cancellation and cleanup path.
8. Define a processing-service boundary accepting the datasheet path, part
   number, progress/log callback, and cancellation signal. This phase shall
   demonstrate it with an offline test worker and any already available
   services. PDF extraction and AI interpretation remain Phase 10 and Phase 11
   deliverables; Start shall report unavailable stages explicitly until they
   are implemented and shall not claim a successful component build. Once
   available, connect those stages through the same boundary, retaining all
   existing validation and review gates. Before any external AI submission,
   identify the selected provider/model and data-handling configuration under
   AI-004.

**Phase 9.5 gate (blocking):** Both the standalone Python script and the
supported KiCad launch entry open the same wxPython GUI from a working
directory outside the repository, with the packaged banner at the top.
Record launch commands and runtime/version evidence. Verify that the API-key
dialog opens blank on every invocation, masks typed input, saves on OK,
preserves the prior key on Cancel or blank input, handles save failures, and
retains the saved key across application restarts without displaying it.
Use a dummy credential for tests and verify it is absent from logs, errors,
ordinary settings, and generated artifacts. Datasheet selection and part-number
validation work; Start passes the full required part number, including package
suffixes, and the exact selected source to the worker and blocks duplicate
jobs. Offline fixtures representing a datasheet with multiple package styles
verify that distinct full part numbers remain distinct processing requests.
Actual datasheet-to-package resolution is verified when extraction becomes
available in Phase 10; its tests must cover correct package selection and
blocked unrecognized or ambiguous mappings. An offline worker demonstrates live log updates,
responsive controls, success and failure reporting, cancellation, and cleanup
on window close. Unavailable processing stages produce a clear status rather
than a false success. Record automated checks and manual GUI/launch evidence;
no live AI credential or provider call is required for this gate.

## Phase 10 — Document extraction

Only after the deterministic component path works:

1. Add PDF ingestion.
2. Add page selection.
3. Add OCR.
4. Add table extraction.
5. Add diagram/image extraction.
6. Convert extraction results into Evidence objects.
7. Add evidence tests using the document corpus.

The repository-root `test_data_sheets/` directory contains real-part PDF
datasheets supplied as representative examples for Phase 10 testing. Use
these PDFs as the document corpus for ingestion and extraction tests,
including page selection, tables, diagrams/images, and Evidence provenance
where applicable. Add targeted fixtures where these datasheets do not
cover required OCR, language, or crop/rotation/DPI cases.

**Phase 10 gate (blocking):** The document corpus tests demonstrate PDF
ingestion, selected-page extraction, OCR, tables, and diagram/image
extraction into structured Evidence records with provenance. The tests
verify that extraction creates no engineering artifact directly. The language
matrix in section 31 and crop/rotation/DPI coordinate fixtures in section 124
are mandatory; evidence overlays must resolve to the same original-page region.

## Phase 11 — AI provider adapter

1. Implement normalized provider interface.
2. Implement user API-key configuration.
3. Implement provider/model metadata.
4. Implement extraction/interpretation tasks.
5. Attach AI results only to Evidence/IR workflows.
6. Add prompt-injection/security tests.
7. Add conflict and ambiguity handling.

Live GPT/OpenAI provider tests shall use the testing credential defined in
the repository-root `.env` file as `BFT_TOKEN`, as specified in AI-005.

**Phase 11 gate (blocking):** The configured provider produces typed,
provenance-linked Evidence/IR candidates with provider/model metadata;
credential-handling and prompt-injection tests pass; conflicts and
ambiguities are surfaced; and tests prove AI cannot bypass deterministic
validation or human review. Section 31 requires one released provider adapter;
additional providers are optional and must pass the same contract suite.

## Phase 12 — Human review and application UI

Extend the Phase 9.5 setup and processing GUI as the main application window
and central scripting-log surface. Open the section 12 viewer as a separate
popup owned by that GUI.

1. Display evidence.
2. Display conflicts.
3. Display IR.
4. Display generated symbol/footprint.
5. Display the generated symbol, its pin-to-pad mapping, and 3D placement
   in the separate section 12 viewer window for a complete part inspection.
6. Support explicit overrides.
7. Connect the UI to the existing Phase 8 review/approval states and services.
8. Use `resources/PartSmith-Banner3.png` across the full width of the Phase 9.5
   main GUI under the following packaging and resize contract. The section 12
   viewer popup shall have no banner.
9. Route all Phase 12 scripting logs to the existing read-only, multiline,
   scrollable log box in the Phase 9.5 GUI under the following logging contract.
10. Add a button in the Phase 9.5 GUI that appears or becomes enabled when the
    Phase 12 viewer is ready to display the current session, and lets the user
    reopen it after closing it under the following main-window control contract.
11. Add **Save** and **Load** buttons to the Phase 9.5 GUI to preserve and
    restore all session data collected or produced up to that point under the
    following saved-session contract. These additions are Phase 12 deliverables.
12. Implement the input-assembly, document-selection, worker-execution,
    session-recovery, and reviewer-identity contracts below. Inspection of
    incomplete or failed work shall remain separate from permission to generate
    or approve it.

### Phase 12 UI layout and workflow

- The Phase 9.5 main window shall retain its setup controls, display Banner3
  edge to edge at the top with proportional scaling as the GUI resizes, add
  **Save**, **Load**, and **Open 3D Placement Viewer**, and provide review tabs
  for **Evidence**, **Conflicts**, **Component Data**, **Symbol/Footprint**, and
  **Validation/Release Review**. Keep processing status and the existing shared
  log box visible and usable while review or viewer work is running.
- The separate viewer shall have no banner. Its client area shall contain a
  large 3D viewport, camera and visibility controls, placement controls,
  measurements, validation feedback, and a **Symbol / Pin Mapping** review
  page alongside **3D / Footprint**. All controls shall remain accessible
  under the viewer's minimum-size, scrolling, resize, and DPI contract.
- Follow the workflow: inspect evidence, review inputs, generate artifacts,
  inspect symbol, footprint and 3D placement, validate, then explicitly approve
  or reject the release.
  Evidence/input review shall be available before generated artifacts exist;
  opening the viewer requires the data needed to display footprint/model
  placement, not release approval. Retain unresolved issues and incomplete
  stages without presenting them as successful builds.
- Begin integration with the existing deterministic 0402 fixture, then connect
  local extraction and AI-assisted sessions. Use the existing generation,
  validation, persistence, and review services; UI actions shall not directly
  advance build states or grant approval. Keep processing, CAD preparation,
  and subprocess reading outside the GUI thread, with UI updates dispatched
  onto that thread under the shared logging and cancellation contracts.

### Phase 12 implementation milestones

Implement Phase 12 in the following order. Each milestone shall produce a
working increment with recorded completion checks before the next milestone
begins. These are checkpoints within Phase 12, not replacements for the numbered
phase-gate policy. Confirm the preceding Phase 11 PASS and applicable correction
evidence before starting implementation. No rendering backend is selected by
this specification; milestone 12.1 establishes and records that decision.

#### 12.1 — Prove the 3D rendering approach

Build a small wxPython prototype displaying an existing STEP model together
with its independently generated footprint. Establish the scene's units,
origin, axes, orientation, placement transform, and rendering adapter. Record
the selected rendering dependency, pinned version, supported runtime,
distribution/license implications, and feasibility of installed-wheel use.
Establish the native-failure containment and graphics-resource lifecycle under
the worker-execution contract below.

**Completion check:** The known 0402 fixture displays with correct physical
scale, orientation, pin-1 relationship, and footprint/model placement. Rotation,
zoom, resizing, and repeated window open/close work in an installed-wheel
prototype without blocking the main window or changing source artifacts.
Malformed STEP input, native preparation-worker termination, unavailable
graphics support, and renderer initialization/context errors leave the main
GUI and session usable. Repeated close/reopen releases native resources.

#### 12.2 — Session foundation and Save/Load

Retain complete local extraction results in both local-only and AI-assisted
processing, rather than retaining only AI candidates or log messages. Introduce
one shared session containing available inputs, results, draft edits, history,
and UI/viewer state. Add the main-window **Save** and **Load** buttons under the
saved-session contract below. Extend the versioned session schema and round-trip
coverage as each later milestone adds data.
Define a session-specific transport schema, isolated working database, immutable
source/asset store, worker-owned database connections, and recovery checkpoints
under the contracts below; reviewed revision bundles alone are insufficient.

**Completion check:** Setup-only and extracted sessions survive save, application
restart, and load with their original source paths unavailable. Local mode
retains its full extraction data. Busy-state disabling, cancellation, atomic
save/load failure handling, and dummy-credential exclusion pass; loading does
not restart processing or submit data to a provider.
Repeated loading of the same save and loading an older save after newer work
restore separate working sessions without identity collisions or rewriting
retained history. Source-file replacement after extraction cannot change saved
source bytes or provenance. Interrupted checkpoint writes preserve recovery.

#### 12.3 — Evidence and conflict review

Add the Evidence, Conflicts, and Component Data tabs. Show source pages/crops,
extracted values, provenance, AI candidates, and unresolved ambiguities or
conflicts. Link displayed facts to the original document-page regions under
section 124, retaining original text alongside translations where present.
Add page-range, OCR/DPI, and evidence-selection controls with visible processing
and provider limits under the document-selection contract below.

**Completion check:** Selecting evidence highlights the correct original-page
region, including the existing crop/rotation/DPI fixtures. Conflicting values
and unavailable information remain visible and cannot silently become accepted
engineering inputs. Both local-only and AI-candidate sessions are inspectable.
Large-document and oversized-AI-selection cases remain responsive and report
limits without silently dropping evidence or submitting an altered request.

#### 12.4 — Editable IR and input approval

Connect extracted facts and AI candidates to Component IR through explicit
user actions and the existing input-review services. Add supported field edits,
pin reorder/renumber/removal, typed overrides with evidence and reasons,
proposals, approval, and rejection. Separate unapplied drafts, pending proposals,
and reviewed revisions; preserve immutable history and exact-base bindings.
Implement initial IR/root and inventory creation plus exact PDL selection under
the input-assembly contract below. Obtain reviewer identity from the trusted
desktop adapter, and use exact decimal editors under the control contract.

**Completion check:** A user can assemble and review a valid input revision.
Missing required information or unresolved blockers prevent generation. Stale
edits fail without partial changes; pin edits obey section 121.7 without
retargeting historical evidence. Input approval does not grant release approval.
An extracted session can enter initial review without pre-existing fixture IR;
unsupported/ambiguous PDL cases remain inspectable and blocked. Unchanged
decimal fields round-trip exactly, and missing/mismatched identity blocks a
decision without partial writes.

#### 12.5 — Generation and 2D previews

Expose generation after input approval through the existing orchestrator. Add
symbol and footprint previews, pin/pad mappings, dimensions, and validation
results. Stream progress to the main log box and keep generation cancellable.
Previews shall derive from the actual generated artifacts and identify their
bound build/revision, rather than substitute idealized package graphics.
Add progress/cancellation adapters at the service boundary. Publish attempt
identities, completed artifacts, and structured outcomes even when a later
stage fails, under the worker-execution contract.

**Completion check:** The reviewed fixture generates through the existing
pipeline. Symbol/footprint previews match the generated files and their pin/pad
identities. Failure and cancellation preserve truthful states and retained data;
logs update live and the main window remains responsive.
Cross-thread connection misuse is prevented; cancellation before and after a
commit reports the actual outcome. Native timeout/failure preserves inspectable
completed artifacts. Events from superseded sessions/revisions are ignored.

#### 12.6 — Integrate the viewer window

Turn the rendering prototype into the separate resizable, modeless viewer owned
by the main GUI. Implement Banner3 packaging and main-window layout, the
banner-free viewer, the viewer-button
readiness rule, singleton popup ownership, and retained close/reopen state.
Connect the scene to the current session's actual footprint, STEP model, and
explicit placement metadata. Include the bound generated symbol and its native
2D preview on the viewer's separate **Symbol / Pin Mapping** page.

**Completion check:** The viewer button becomes available when required data
exists. Closing/reopening retains session data and edits; clicking while open
foregrounds the existing popup. Banner, resize/DPI, missing-resource, standalone,
and KiCad launch checks pass without rerunning processing to reopen the viewer.
Parseable footprint/model pairs from failed validation attempts remain available
for diagnostic viewing, with stage/failure labels and release approval blocked.
Missing, malformed, unsupported or stale symbol data remains explicitly labeled;
it cannot substitute another attempt's symbol or prevent diagnostic 3D inspection.

#### 12.7 — Navigation, layers, and inspection

Implement the camera presets, visibility toggles, pin/pad selection, axes,
package dimensions, and distance measurement under the viewer-control contract
below. Inspect actual symbol pin numbers, names and electrical types against
reviewed IR and the displayed footprint pads, with explicit missing, extra,
duplicate and mismatched mapping diagnostics. Keep camera and review-page state
separate from engineering placement metadata.

**Completion check:** All navigation and visibility controls work on the known
fixture. Selected pin/pad identities and measured distances/dimensions match
known geometry within recorded tolerances. View changes leave IR, engineering
artifact bytes, dependency hashes, and approval bindings unchanged.
The full placement, including unit and nonuniform X/Y/Z scale and mirror flags,
is displayed accurately without modifying stored values.
The separate viewer displays actual symbol bytes/properties and a native preview
bound to the same build/revision/stage as the footprint/model. Symbol pin
selection highlights its existing footprint pad; it never changes pin data.

#### 12.8 — Placement editing and feedback

Add X/Y/Z position, X/Y/Z rotation, and supported mirror controls under sections
121.6/177. Preview draft edits, display discrepancies, allow draft discard, and
submit explicit typed proposals with reasons for review. On accepted revisions,
rerun affected association/final-byte checks and invalidate the applicable
manifest and release approval under sections 166–167. Placement edits update
metadata rather than the underlying canonical STEP geometry.
Numeric placement edits shall preserve canonical decimal semantics; scale shall
remain visible even when its editing is unsupported.

**Completion check:** Injected offset, rotation, mirror, and height faults
produce their intended diagnostics. Draft edits never silently become approved
build data. Accepted changes retain history and invalidate affected results;
unchanged STEP geometry is reused only when its declared dependency permits it.

#### 12.9 — Final review and complete recovery

Add the final review screen with artifact previews, validation results,
blockers, and explicit release approval/rejection through the existing services.
Complete saved-session coverage for artifacts, pending edits/proposals, review
decisions, immutable history, and viewer state introduced by milestones 12.3–12.8.

**Completion check:** Input and release approvals remain distinct. Changed
inputs or artifact bytes cannot inherit stale approval. A restart restores
unfinished review work and a ready viewer without provider calls or automatic
approval; restored approvals retain exact valid bindings. An offline fixture
completes the inspect/review/generate/validate/release-review workflow.
Main-window close, session clear/replacement, and starting another component
exercise Save/Discard/Cancel behavior. Recovery after process termination opens
the last complete checkpoint for inspection without restarting work or decisions.

#### 12.10 — Full Phase 12 gate

Run the entire Phase 12 gate below, including source and installed-wheel checks,
both supported launch paths, visual inspection, resize/DPI checks, credential
redaction, and failure/cancellation cases. Record commands, runtime scope, test
results, screenshots where applicable, and input/artifact identities. Apply the
repository's gate-closeout instructions to preserve historical evidence,
refresh applicable active manifest hashes, and verify the required manifests.

**Completion check:** All milestone checks and the complete Phase 12 gate pass
against the final bytes. Only this completed closeout may record the overall
Phase 12 PASS; individual checkpoint results do not authorize Phase 13 work.

### Phase 12 viewer controls and engineering state

- **Complete part inspection:** The separate viewer shall provide a generated
  symbol review page as well as footprint/3D inspection. Show the actual KiCad
  symbol drawing, exact symbol bytes and hash, symbol properties, pin numbers,
  names, electrical types, and mapping to actual footprint pad numbers. Compare
  generated pin fields with the immutable reviewed IR for the displayed revision;
  show missing, extra, duplicate and mismatched identities without replacing
  actual generated fields with expected values. Show retained validation results
  bound to these symbol bytes. Display build, revision, stage and stale status;
  never mix artifacts or previews from different attempts or use final previews
  for preliminary bytes. Missing or unreadable previews preserve textual
  inspection, and unavailable symbol data remains diagnostic. Camera/page/pin
  selection grants no approval and leaves engineering bytes unchanged.

- **Camera:** Rotate, pan, zoom, fit/reset view, and top, bottom, front, back,
  left, right, and isometric presets. Camera movement and reset shall change
  only the view, leaving engineering placement and review decisions intact.
- **Visibility:** Toggle the 3D model body, footprint pads, silkscreen,
  courtyard, fabrication graphics, origin, coordinate axes, and pin-1 marker.
  Show the independently generated model and footprint in the same scene.
- **Inspection:** Select/highlight individual pins and pads, display their
  identities and mapping, inspect package dimensions, and measure distances
  with explicit units. Rendered-mesh measurements shall declare their tolerance;
  geometric validators remain authoritative under sections 178–179.
- **Placement:** Show X/Y/Z offsets in millimetres, X/Y/Z rotations in degrees,
  dimensionless X/Y/Z scale factors, and the supported explicit mirror settings.
  Scale shall be visible at least read-only; editing it requires the supported
  typed override path and its normal review/validation. Preserve nonunit scale
  on load, display, draft discard, and unrelated edits. Distinguish draft values
  from reviewed placement. Reject unsupported transforms instead of silently
  approximating them; retain the coordinate contract in sections 92/150.
- **Numeric values:** Parse engineering edits from text into exact Decimal
  values under section 121.3, with explicit units and input syntax. Reject
  ambiguous, non-finite, and out-of-profile values. Display rounding, locale
  formatting, or float-based wx controls shall not rewrite unchanged inputs.
  Convert to rendering floats only at the display boundary; never reconstruct
  stored engineering values from a mesh, camera matrix, or formatted label.
- **Actions:** Discard draft placement changes, propose changes with a reason
  and required evidence through the typed review service, and run placement
  checks. Draft discard restores the current reviewed values; it shall not
  erase reviewed decisions or silently reset approved placement to zero.
- **Feedback:** Show model floating/below-board, unexpected orientation or
  mirror, pin-1 mismatch, centre mismatch, height mismatch, and pin-to-pad
  alignment results as applicable. Identify draft or stale results, preserve
  discrepancies, and display blocking, failed, passed, and justified
  non-applicable results distinctly. Visual appearance cannot override checks.

### Phase 12 input assembly and reviewer identity

- Create the initial Component IR through an explicit assembly operation that
  registers the component identity, structural IR/root revision, source
  documents, evidence, acquisition revision, and exact acquisition inventory
  under sections 121/163. Allow structurally valid incomplete candidates with
  missing values explicitly represented. Field/pin assignment shall record
  supporting evidence and interpretation status; never fabricate facts, units,
  pins, review metadata, or approved decisions to make a candidate buildable.
- Persist the unreviewed initial root and matching inventory before submitting
  an evidence-review child to the existing input-review service. That service's
  EVIDENCE_REVIEW operation cannot change engineering content. Initial assembly
  precedes it; subsequent engineering changes use typed proposal/revision
  operations under sections 121.6–121.8/172, preserving history and head checks.
- Bind **Required Part Number** to the assembled immutable component identity.
  Disable editing after assembly; processing another ordering number requires
  **New / Clear Component** and the Save/Discard/Cancel transition. Reject a
  bypassed setup/identity mismatch before extraction, generation, release
  approval or archive restoration can act on the old reviewed component.
- Distinguish a datasheet's package label from a validated PDL selection. Resolve
  the exact family, variant, and terminal topology against supported PDL entries,
  then retain the selected entry's ID, revision, and content hash. Present
  missing/ambiguous matches and unsupported generator strategies with the
  missing information and affected artifacts. Permit review and saving while
  generation is blocked. The Phase 12 bootstrap shall not imply support for
  arbitrary datasheets or completion of Phase 14's production package matrix.
- The trusted desktop adapter shall obtain the current reviewer's stable
  identity from the authenticated operating-system session and supply the
  corresponding AuthenticatedPrincipal and mechanism to the review services.
  Display the actor and require an explicit reason for approval/rejection.
  Editable display names, document/AI content, saved-session fields, and
  historical audit actors cannot authenticate the current user. Re-establish
  current identity after load/recovery; identity failure blocks decisions while
  inspection and saving remain available. Record historical actor/time unchanged.

### Phase 12 document selection and resource limits

- Provide explicit one-based page/range selection, an **All Pages** option,
  OCR/force-OCR and supported language options, and DPI selection before
  extraction or deliberate re-extraction. Show the page count and selected
  settings, validate them before starting, and retain them with the acquisition
  identity. Re-extraction creates separately bound results and cannot silently
  replace evidence referenced by retained review decisions.
- Let the user select the Evidence records and trusted target fields for each
  supported AI task. Show provider/model, selected record count, serialized
  request size, and data-handling disclosure before submission. The current
  adapter permits 1–128 Evidence records and at most 512 KiB of canonical request
  bytes; use its actual declared limits if a versioned adapter changes them.
  Oversized selections shall remain local and produce an actionable message.
  Never silently truncate, take the first 128 records, or split submissions.
  Any future batching requires an explicit operation with retained request and
  provenance bindings for each batch. Unselected evidence/conflicts remain in
  the session and retain their applicable review obligations.
- Apply recorded, configurable limits under section 190 to aggregate decoded
  images, render/mesh caches, STEP preparation, log display, session transport
  size/object count, and archive expansion where compression is used. Load
  page thumbnails/images and display meshes on demand; eviction may remove
  derived display caches but not the session's retained source/artifact bytes.
  Store bulk assets by content hash instead of duplicating them in every UI
  record. Validate sizes before allocation/import, report limit failures with
  retained data, and record responsiveness/resource checks for large fixtures.

### Phase 12 worker execution and failure inspection

- Serialize mutating processing/review/build work for each working session.
  Create and close each SQLite connection in its owning worker/thread; do not
  pass a GUI-thread connection to another thread or bypass ownership by merely
  disabling SQLite's thread check. Use separate read connections or immutable
  snapshots for inspection, and keep transaction/commit ownership in the service
  adapter. Schema migrations and session switching require an idle database.
- Extend/adapt the build and native-tool service boundaries to expose progress,
  safe cancellation, bounded timeouts, and structured outcomes. Include action,
  session-instance, revision, and build-attempt identities where available,
  stage, outcome/error code, credential-redacted diagnostic detail, and retained
  artifact/result references. Publish an attempt ID when created and completed
  artifact references at consistent stage boundaries, including before later
  failure. GUI callbacks shall discard events for superseded sessions/revisions
  or destroyed windows. A generic failure message alone is insufficient.
- Check cancellation at declared safe points and stop managed native child work
  with bounded cleanup. A review/approval commit is non-cancellable once its
  atomic transaction starts: finish or roll back the transaction and report its
  actual outcome. Cancellation arriving after successful completion shall not
  relabel committed work as cancelled. Track operational cancelled/interrupted
  status separately from the existing engineering BuildState enum, retaining
  the last consistent build stage and audit history. Retry/resume is explicit
  through the orchestrator with rechecked bindings; startup/load never resumes
  a worker or replays a decision automatically.
- Separate a completed operation from subsequent log/recovery persistence.
  A failed checkpoint after an input or release commit emits a recovery warning
  while preserving the actual decision, engineering status and result payload.
  Late cancellation cannot reclassify that commit. A checkpoint-only failure
  still reports failed checkpoint creation without changing engineering state.
- Retain completed artifacts and diagnostics from failed or interrupted
  attempts, with exact revision/hash/stage bindings. Expose 2D previews whenever
  their corresponding artifacts are parseable, and enable the 3D viewer whenever
  a parseable footprint/STEP pair and placement metadata exist, even if validation
  failed. Label preliminary, failed, draft, or stale content; keep release
  approval blocked. Missing or unparseable artifacts produce a clear inspection
  status, never substitute geometry or a false valid scene.
- Prepare native STEP imports/tessellation in a bounded isolated process so a
  malformed input or CAD worker termination cannot kill the desktop application.
  Record the chosen renderer's native-failure boundary and resource ownership.
  Graphics initialization/context failures shall disable or close the affected
  viewport with a logged error, leaving the main session inspectable/saveable.
  Release subprocesses, CAD handles, meshes, textures, graphics contexts, and
  callbacks on failure/close/session change. Inject preparation crashes/timeouts
  and renderer initialization/context errors in acceptance checks; UI-thread
  separation alone is not native-failure containment.

### Phase 12 main-window controls and saved sessions

- The **Open 3D Placement Viewer** action shall be a button on the Phase 9.5
  main GUI. It may initially be hidden or disabled, but shall appear or become
  enabled as soon as the viewer's required data is available for the current
  session, including failed attempts with parseable artifacts under the worker
  contract above. Readiness shall not require successful validation or final
  release approval. Keep the button
  available while that session remains ready, including after the popup is
  closed. Clicking it shall reopen the popup with the current session's data
  and retained review/placement state, without rerunning extraction, AI
  interpretation, or generation. If the popup is already open, bring it to the
  foreground instead of creating a duplicate. Closing the popup shall not
  discard session data, review edits, or log history. Recompute availability
  when the current session changes, is cleared, or is loaded.
- **Save** shall open a destination chooser and write a versioned session file
  or bundle containing all data available at the time of saving. Support
  partially completed and unapproved sessions, including setup-only sessions;
  saving shall not require a generated component or release approval. Include
  the selected source PDF and its identity, full required part number, non-secret
  processing settings, extraction results and source regions/images, Evidence,
  AI candidates and provider/model metadata, conflicts, IR and revision history,
  pending review proposals and unapplied edits, overrides and review/approval
  records, build/progress states, generated artifacts, validation results and
  manifests where present, review/placement UI state, and the redacted log
  history. Retain immutable identities, provenance, hashes, and decision bindings
  under sections 163/175. Stages that have not run remain incomplete; saving
  shall not fabricate results or approvals. Embed or package the session's
  source and data files so restoration does not depend on their original paths.
- **Load** shall open a saved-session chooser and restore the saved inputs,
  results, unfinished work, review/placement state, and log history, including
  after an application restart. Restore available data without automatically
  rerunning processing or submitting data to an AI provider. Validate the session
  format/schema versions, required objects, hashes, and retained references
  before replacing the current session. Restore approval bindings only when
  their exact inputs/artifacts remain valid under the existing review services;
  loading shall not grant approval or bypass validation. Recompute viewer-button
  readiness from the restored session so a ready popup can be opened again.
- Disable **Save** and **Load** while a processing or review/build worker is
  changing session data; re-enable them after completion, failure, or cancellation
  cleanup so saves capture a consistent state. Loading shall never restart an
  in-flight worker automatically. Confirm before replacing unsaved session
  changes. Cancelled choosers leave the current session unchanged. Write saves
  atomically and stage/validate loads before applying them; a failed save leaves
  any previous saved file intact, and a failed load leaves the current session
  intact. Report success, cancellation, and read/write or validation failures
  through the main GUI and its existing log box.
- Saved sessions shall exclude API keys and other credentials, including from
  settings, logs, errors, and provider metadata. Keep credentials in the existing
  secure credential store; loading a session shall not overwrite or reveal them.

### Phase 12 session format, source snapshots, and recovery

- Define a versioned saved-session transport schema/index that supports every
  stage, including no IR, incomplete/unreviewed IR, drafts, pending proposals,
  and failed/interrupted builds. Separate mutable draft/UI/task state from exact
  immutable engineering/history objects, with paths, object kinds, lengths,
  versions, and hashes. Reuse sections 163/175's verified immutable contracts
  where applicable, but do not require a reviewed head or an approved release
  to save. Existing revision/replay bundles alone cannot represent this scope.
  Reject incompatible versions or use an explicit, audited migration that
  retains original bytes; never silently reinterpret approved content.
- Each working session shall own an isolated local SQLite database and asset
  store in a user-writable application location independent of the checkout or
  current directory. Stage a load into a fresh working database/store, validate
  the entire transport, then switch the UI atomically. Repeated loads and older
  saves open separate working instances; preserve saved engineering/audit IDs
  and hashes, assigning a fresh operational instance ID for callbacks. Loading
  shall not collide with or rewind a newer retained database/head. Imports into
  another existing project's history remain separate explicit service operations
  with normal identity/head checks, not implicit effects of **Load**.
- Capture immutable source PDF bytes into the session asset store no later than
  processing or the first setup-only save, and process that snapshot. Its SHA-256
  shall match the document identity referenced by extraction/evidence. Save the
  retained snapshot, never reread a mutable original path to reconstruct an
  extracted session. Original-path modification/deletion leaves old provenance
  intact; accepting changed source bytes requires an explicit new acquisition.
- Track unsaved changes and offer **Save**, **Discard**, or **Cancel** before
  main-window close, session clear/replacement, or starting another component.
  Cancel aborts the requested transition. Save completes successfully before
  switching/destroying; failure retains the session. Discard affects unsaved
  draft/session changes, not retained reviewed history. Closing during work
  shall finish the safe cancellation/commit-cleanup path before final teardown;
  the viewer's close alone never discards the main session.
- Write atomic recovery checkpoints at consistent boundaries after extraction,
  completed build stages, review commits, and failure/cancellation cleanup, plus
  idle draft-edit checkpoints under a recorded policy. Internal checkpointing
  uses the owning worker's stable snapshot/transaction boundary even while the
  manual **Save**/**Load** controls are disabled. A checkpoint is not an explicit
  user save and does not clear unsaved-change status. On restart after abnormal
  termination, offer inspection/recovery of the last complete verified checkpoint;
  ignore incomplete writes and retain the preceding good checkpoint. Recovery
  re-establishes session/principal/readiness bindings without automatically
  starting processing, provider calls, retries, or review/approval actions.

### Phase 12 viewer window and banner

- An **Open 3D Placement Viewer** action in the main GUI shall open section
  12's viewer in a separate, resizable, modeless wx window owned by the Phase
  9.5 GUI. The main GUI remains usable while the popup is open. The popup
  has its own client dimensions and resize handling; closing it closes only
  the viewer. The Phase 12 viewer popup shall have no banner; its scrollable
  viewport and review controls shall use the complete available client area.
- Display the complete `resources/PartSmith-Banner3.png` banner at the top of
  the Phase 9.5 main GUI at client coordinates `(0, 0)`. Its displayed width
  shall equal the main window's full **client-area width**, excluding
  operating-system borders, with no left/right padding or margins. It shall
  reach both client edges and expand or shrink with the GUI. Keep the banner
  outside split panes and scrollable content so scrolling or adjusting the
  controls does not narrow or move it.
- Preserve the source image's aspect ratio and show the entire image without
  cropping, tiling, or stretching either axis independently. For positive
  client width `W` and source dimensions `Iw` by `Ih`, set the displayed width
  to `W` and height to `max(1, round(W * Ih / Iw))`. Here `W` is the main GUI's
  client width. Derive source dimensions from the loaded image rather than
  hard-coding them. Resample from
  the original image with high-quality scaling, including when enlarging it.
- Recompute banner dimensions on initial layout, main-window resize, maximize,
  restore, and display/DPI changes. Update layout and painting on the wx GUI
  thread; use consistent client-coordinate units for width and height and
  account for the display scale when creating the bitmap. Ignore transient
  zero-size events during minimization and restore the correct dimensions
  when the window becomes visible. Resize the content below the banner to
  use the remaining height and provide scrolling where needed to keep review
  controls accessible at the supported minimum window size.
- Include the exact `PartSmith-Banner3.png` asset in source distributions and
  installed wheels as the `partsmith.gui` package resource
  `partsmith/gui/PartSmith-Banner3.png`, and carry it into the production
  application bundle in Phase 14. Load installed assets through package
  resources; a source-checkout launch may resolve `resources/PartSmith-Banner3.png`
  relative to the application files. Both the standalone and KiCad launch
  paths shall work from an unrelated current working directory, without
  requiring a repository checkout or downloading the image. A missing or
  unreadable asset shall produce a clear main-GUI log message identifying the
  resource and leave setup, review and the banner-free viewer usable; do not
  silently substitute an older banner.

### Phase 12 scripting logs

- Use the Phase 9.5 GUI's existing log box as the shared destination for all
  scripts and services invoked by Phase 12 actions, whether started from the
  main GUI or the viewer popup. This includes extraction/AI processing,
  generation, validation, review/override operations, and placement checks.
  Connect every worker and managed subprocess to the same logging sink.
- Stream progress, informational messages, warnings, errors, exceptions,
  completion, and cancellation/cleanup messages while work is running.
  Capture both subprocess stdout and stderr incrementally, including output
  produced before a failure or nonzero exit; report the resulting exit status.
  Identify the originating action or worker so popup activity is recognizable
  in the main log box. Keep the existing log history when opening, closing,
  or reopening the viewer.
- Apply the Phase 9.5 credential-redaction rules before displaying or
  persisting messages from any source, including captured subprocess output
  and exceptions. Dispatch log updates onto the wx GUI thread and keep work
  and pipe reading outside that thread so both windows remain responsive.
  A viewer-open failure or missing/unreadable main banner shall also be
  reported in the Phase 9.5 log box.

**Phase 12 gate (blocking):** End-to-end UI tests demonstrate that a user
can inspect evidence, conflicts, IR, symbol, footprint, 3D placement,
overrides, and validation results, then explicitly approve the
deterministic build.
All milestones 12.1–12.10 require recorded completion evidence, including the
viewer navigation/inspection controls and placement fault checks above.
Complete part checkout includes the generated symbol, footprint and 3D model;
footprint/model placement inspection alone is insufficient. Source and installed
wheel checks shall cover actual symbol previews/pin mapping in the separate
viewer, missing/malformed/stale symbol diagnostics, mapping faults, and offline
restoration with retained viewer page selection and unchanged approval bindings.
Tests start with unreviewed evidence, approve inputs before generation, and
approve final outputs separately. Pin edits exercise section 121.7's supported
reorder, renumber, and removal operations without retargeting historical evidence.

Main-window control tests shall cover the viewer button before readiness, its
appearance/enabling when ready, closing and reopening with retained data and
edits, foregrounding an existing popup without duplication, and readiness
changes after clearing or loading a session. Save/load round trips shall cover
setup-only, extracted/AI-candidate, pending-review, and generated/validated
sessions. After an application restart, restore all saved data and bindings,
unfinished edits, and log history with the original source paths unavailable;
verify no automatic processing/provider call or new approval occurs and that a
ready viewer can be reopened. Cover busy-state disabling, cancelled choosers,
unsaved-change confirmation, unsupported versions, missing/tampered objects,
and read/write failures with no partial replacement or loss of prior data.
Use dummy credentials and verify they are absent from saved session content.

Additional integration checks shall cover all of the following:

- Initial component/root/inventory assembly from extracted evidence without
  fixture IR; exact supported PDL binding; incomplete, missing/ambiguous PDL, and
  unsupported-strategy cases that remain inspectable but cannot generate.
- Per-worker SQLite ownership and rollback, streamed structured stage outcomes,
  cancellation before/during/after atomic commits, late callbacks from replaced
  sessions, native timeout/termination, and retained failed-build artifacts.
- Diagnostic viewer access after deliberate validation failure, with exact
  artifact/stage bindings and no release approval or substituted geometry.
- Exact decimal no-change save/load/review round trips, deliberate unit edits,
  invalid numeric input, and displayed unit/nonuniform scale and mirror values.
- Selected-page/OCR/DPI retention and original-page overlays, provider selections
  at and above record/byte limits without automatic truncation/submission, and
  bounded large-document/cache/session-load behavior under recorded budgets.
- Source modification/deletion after extraction, repeated loads, older-save
  loads after newer work, incompatible versions, and object/identity integrity.
- Malformed STEP, isolated CAD preparation failure, unavailable graphics,
  renderer context errors, repeated viewer close/reopen, resource cleanup, and
  continued main-window inspection/save access.
- Save/Discard/Cancel on main close, clear, replacement, and new-component start;
  termination during checkpoint writes and after review commits; recovery of
  the last complete checkpoint with no automatic work or duplicated decisions.
- Trusted local reviewer identity, mismatched/missing principal, nonempty
  decision reasons, and forged session/document actor fields that cannot grant
  current authority or change retained audit identities.

Verify that source distributions and installed wheels contain Banner3 with
bytes matching the repository asset, then launch the installed GUI through
both supported launch paths from outside the repository and open the separate
viewer popup. Automated layout checks and recorded visual inspection shall
cover initial display, minimum supported size, enlargement, repeated resizing,
maximize/restore, closing/reopening the popup, and supported display/DPI changes.
The main GUI's Banner3 remains at `(0, 0)`, reaches both client edges, spans its
full client width, shows the complete image, and has proportional height within
one client pixel as the GUI expands or shrinks. The separate Phase 12 viewer
contains no banner and uses its available client area for the scene and controls.
Placement controls remain accessible and both windows remain responsive. Closing
the popup leaves the main GUI running. Negative resource checks verify the
reported missing/unreadable main-banner log message and continued usability.
Phase 14 shall repeat the packaging and launch checks against the production
application bundle.

Log-routing tests shall start work from both the main GUI and viewer popup and
demonstrate live messages in the Phase 9.5 log box before completion. Cover
service callbacks, subprocess stdout/stderr, failure/nonzero exit, cancellation
and cleanup, and viewer-open errors. Verify action/source identification,
preserved log history after popup close/reopen, responsive controls, and dummy
credential redaction before display or persistence.

## Phase 13 — KiCad integration

Extend the verified launch-only entry, native CLI adapter and immutable release
services into an explicit project/library integration workflow. Installation
creates separately validated and authorized aggregate bytes under section 174.1.
The Phase 12 viewer and input/release decisions remain component review surfaces;
opening them or loading a saved session does not authorize project installation.

**Entry check:** Record a current Phase 12 PASS, review its R12-01/R12-02
correction evidence, and inventory the actual plugin/runtime/data formats.
Under v0.9.7, missing installation contracts are Phase 13.1 work, so R13-01 does
not block entry to that milestone. Its obligation remains open until 13.1 PASS.
Record the exact KiCad build, platform, PartSmith Python/CAD tuple and existing
source/runtime and historical evidence identities. Distinguish implementation
evidence from planned work.

**Phase 13 build/test scope — PCM only:** Build the KiCad PCM ZIP and validate
its payload and installed/prepared runtime. Phase 13 does not build, install or
test a PartSmith wheel, require a wheel artifact, or use wheel resource-parity
results as its acceptance path. Supersede earlier Phase 13 source/wheel language,
including overlapping packaging clauses in referenced sections, with source/
PCM checks. Earlier Phase 0–12 test results and distributions retain their
historical identities and scope; affected engineering regressions are rerun
through the Phase 13 validation paths without rebuilding historical wheels.
Third-party binary dependencies remain part of the selected runtime provision.

### Phase 13 numbered work items

1. Deliver the closed, versioned integration-plan, installation-manifest,
   authorization-binding, validation/audit and journal contracts in section
   174.1, with typed Python APIs, canonical hashes, fixtures and packaged schemas.
2. Prove source bundle/export/import byte preservation and revalidate affected
   Phase 8/12 contracts. Close R13-01 only after source and isolated PCM contract-
   payload checks, evidence archival and all affected input/artifact hashes pass.
3. Extend the versioned KiCad adapter with a tested capability matrix, bounded
   native CLI checks and real supported PCB Editor IPC operations.
4. Define and validate plugin registration, versioned launcher configuration,
   PCM ZIP metadata/layout, dependency/runtime provisioning, install/update/
   uninstall, runtime isolation, IPC session identity and transient credentials.
   Retire the PartSmith wheel build/test path from active Phase 13 automation
   and replace its resource coverage with PCM ZIP/installed-runtime checks.
5. Implement read-only planning/dry run, exact target/base checks, collision
   detection, immutable integration persistence and explicit scoped targets.
6. Stage deterministic packed symbols, footprints and unchanged STEP bytes;
   validate all references and semantic preservation against approved sources.
7. Implement explicit integration authorization, complete-generation publication,
   recoverable journaling, concurrent-edit rejection and complete rollback.
8. Connect the desktop/headless services to deliberate install/update/rollback
   operations, preserving component review and source-bundle identities.
9. Prove real target-KiCad usability, CLI/IPC round trips, two-component update
   preservation, negative cases, fault recovery and final source/PCM closeout.

### Phase 13 ordered implementation milestones

Complete these checkpoints in order. A checkpoint PASS authorizes the next
milestone, not the overall Phase 13 PASS. Preparatory capability discovery may
remain read-only; target-mutating work starts only after its dependencies pass.

#### 13.1 — Integration contracts and R13-01 closure

Implement section 174.1's schema-version-1.0 objects as closed Draft 2020-12
schemas and frozen typed contracts. Declare the canonical profile, deterministic
identities, ordering and null/absence rules before adding a planner or publisher.
Package every schema and fixture dependency needed to validate offline.
Authorization binds exact plan/content/target/base/check identities; actor/time
are separate audit data. Component release approval cannot supply that binding.

Add valid, invalid and golden fixtures covering unknown/omitted fields,
unsupported versions, bad digests, changed source/installed hashes, stale bases,
wrong targets, duplicate/colliding paths, forbidden self-hashes and hash cycles.
Test that identical deterministic inputs produce identical canonical bytes and
hashes while new audit actor/time/attempt IDs do not change engineering content.
Verify export/import preserves approved source manifests/artifacts/history
byte-for-byte; revision-only and unfinished desktop archives cannot masquerade
as approved installation sources.

Re-run affected Phase 8 bundle/release and Phase 12 identity/decision checks
against source. Also exercise the contract/schema/resource checks from an
isolated PCM payload fixture, without a repository fallback or PartSmith wheel;
compare exact schema/resource bytes and verify offline reference resolution.
This contract-only fixture uses the intended PCM payload layout and the declared
test runtime. It does not require the complete installed plugin/IPC runtime
which 13.2 delivers; full installed-runtime regressions remain due in 13.8.
Archive the prior finding and receipts, record commands/results/current artifact
identities, refresh all affected active hashes including CI's manifests, and
verify them under the repository closeout instructions. Existing distributions
and historical checks retain their scope. Document any remaining failure.

**Completion check:** Every contract case, immutable-source check, affected
regression and final hash check passes. Record 13.1 PASS and mark R13-01 RESOLVED.
Defining requirements or refreshing a hash alone cannot close the finding.

#### 13.2 — Pinned adapter, plugin and target feasibility

Record installed KiCad CLI/API capabilities, adapter/serializer versions and a
pinned official Python IPC binding with its locked dependencies. The initial
desktop target remains Windows AMD64 and KiCad 10.0.6. Additional platforms or
KiCad patches require separate executable evidence before being advertised.
KiCad 10 IPC checks use a running PCB Editor. Do not require a headless IPC
server or schematic-editor IPC based on newer-development documentation.
Record native/API units and coordinate frames; version the conversion to the
exact-decimal IR/placement conventions in STD-005 and section 92. Known-unit,
angle/orientation and conversion round-trip fixtures detect scale/axis mistakes.

Run PartSmith in KiCad's private Python 3.11/CAD environment, created from
the bundled interpreter. Keep CAD imports out of the legacy ActionPlugin host. Choose and document the
supported launch mechanism for the pinned build and PCM package: the current
legacy ActionPlugin is a development launch entry; an IPC action uses KiCad's
version-matched `plugin.json` and a tested Python or executable runtime boundary.
Keep that registration separate from PartSmith's versioned launcher configuration
in section 174.1.5. A KiCad-managed private Python environment is acceptable
only after the interpreter, dependencies and CAD tuple pass the same engineering
runtime checks; generation cannot use the embedded legacy `pcbnew` interpreter.

##### PCM package and runtime installation contract

Use KiCad PCM as the primary plugin installation/update/removal path. Deliver
an exact-layout ZIP with root `metadata.json` and plugin content directly under
`plugins/`; PCM creates the installed package namespace. Include only owned
payload/resources and validate against the schemas shipped with KiCad 10.0.6.
The package manifest and IPC `plugins/plugin.json` are distinct contracts.
The PCM version entry declares `runtime: "ipc"` for an IPC package; the action
registration separately declares Python or executable launch behavior. Existing
manual-copy/`partsmith-kicad-setup` instructions remain development/legacy paths.
Customers do not install a PartSmith wheel, clone the repository, or run pip.
Phase 13 builds and tests the PCM package directly; there is no internal
PartSmith wheel build, install, regression run or required wheel receipt.
Carry schema/migration/asset/plugin byte-parity and offline loading coverage
into PCM payload and installed-runtime checks so that resource omissions fail.

Retire the active `Verify installed wheel and packaged resources` CI step,
PartSmith wheel build/reinstall commands and wheel-specific verification harness
paths when implementing this milestone. Include the installed-wheel PDF
stability job, `dist/*.whl` upload, and the wheel-resource assumptions in
`scripts/verify_pdf_stability.py` and `scripts/verify_viewer_prototype.py`.
Source-test setup must also avoid creating an editable/release PartSmith wheel;
load the declared source tree directly. Replace these paths with deterministic PCM ZIP
construction, inventory/schema checks and checkout-independent payload/runtime
tests. Retarget shared tests rather than deleting engineering assertions. Record
the retired entry points and replacement commands; no active Phase 13 command
may invoke PartSmith wheel generation or depend on a wheel installation. Retain
historical gate logs/artifacts and their hashes. Third-party dependency wheels
may still supply the verified runtime; they are not PartSmith release artifacts.

Use a stable package identity and explicit version, license, compatible KiCad/
platform range and packaged-size inventory. Archive metadata has exactly one
version; repository metadata adds download URL/size/SHA-256 after ZIP creation.
Exclude `download_*` fields from archive metadata to avoid a self-hash. Build
ZIPs deterministically and record final inventory/hash. Validate repository
fixtures offline; hosted release/submission is separate work and not required
for the local PCM test. Official repository listing is not assumed.

For Python IPC, ship `plugins/requirements.txt` with pinned dependency closure;
KiCad prepares the per-plugin environment in the background. Verify its actual
Python 3.11 interpreter and binary-package availability for the declared OS/ABI.
The pinned 10.0.6 loader uses pip's binary-only requirement installation, so a
source-build fallback cannot satisfy readiness. Do not rely on `min_version`
alone to enforce the interpreter. The supported production mechanism is Python
IPC with KiCad-managed requirements. Executable bundles are historical prototypes,
not a supported alternative. A separate customer runtime installer is not supplied.

Declare first-load internet/download behavior and dependency provenance.
Installation, dependency updates and environment recreation require internet
access. Offline installation, dependency mirrors, runtime bundles and an offline
edition are out of scope. Existing local processing and recorded component replay
remain available after successful preparation. Show preparation, ready and failed
states; actions become usable only after runtime/schema/CAD diagnostics pass.
Test denied network, incompatible/missing binaries, interrupted preparation,
environment recreation and retry without touching component history or secrets.

Exercise **Install from File** and configured-repository fixtures where offered.
For repository install/update/removal, exercise the Pending/Apply workflow;
record the actual local-file behavior rather than assuming identical queuing.
Verify PCM's installed version and the plugin action after restart/reload.
Test update, uninstall and reinstall through PCM, including an active action
and failed preparation. Keep databases, credentials, journals and generated
project libraries outside disposable package/environment paths. Updating plugin
code must not publish or roll back a component library. Document environment
cache cleanup and recovery; do not edit PCM's installed-package registry directly.

Documentation basis: [KiCad addon packaging](https://dev-docs.kicad.org/en/addons/index.html),
[KiCad 10 PCM workflow](https://docs.kicad.org/10.0/en/kicad/kicad.html#_installing_packages)
and [IPC runtime guide](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/).
Use the [10.0.6 loader](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp)
and installed schemas to resolve version-specific behavior; current web schemas
and development documentation cannot add unsupported capabilities to that target.

Bind an IPC connection to the launching/explicitly selected KiCad instance,
verified project/board context and API version. Multiple instances, changed
boards, restart, missing API, denied access and connection loss fail clearly.
Endpoint/token values remain transient; redact the IPC token from logs and
exclude it from plans, archives, manifests, hashes and journals. Standalone
launch without an IPC session retains inspection/export/planning; connection is
explicit and missing live capabilities are shown without inventing a session.

Before committing an installer layout, prove a feasible publication boundary
covering the whole library/reference/table set on the claimed filesystem.
Declare how KiCad resolves the active generation and refreshes cached libraries.
A prototype that only rejects UNSUPPORTED_ATOMIC_INSTALL cannot pass the final
gate; at least one real supported target must work through publication/recovery.

**Completion check:** Source and installed launch/resource checks pass; a real
PCM ZIP install, first-load preparation, launch, update, uninstall and reinstall
pass on the declared target, with metadata/schema/layout/dependency parity,
failure/recreation checks and separate plugin/project-data ownership recorded.
A real PCB Editor session completes capability/version discovery and a supported
read/inspection operation against the intended board. Wrong-session, restart,
token-redaction, unavailable-operation and timeout cases pass. The publication
feasibility result and exact supported target matrix are recorded.

#### 13.3 — Plan, target inventory and immutable integration store

Use a complete approved release package, resolving immutable source approval,
manifest, all three final artifact hashes and required validation objects.
Never infer approval from a saved GUI label, a reviewed IR or a proposal.
Keep source-object hydration/import explicit, bounded and hash-verified.

Snapshot the exact target identity, installed generation, file/table hashes and
expected absences. Detect project/global table scope, nickname/name collisions,
unmanaged content, existing/concurrent edits, unsafe path aliases and removals.
The first supported installation scope is project-local; global-table mutation
requires its own explicit scope/capability and publication proof. Existing
unrelated entries and components remain intact.

Freeze/hash the plan before staging. Dry run reports create/modify/delete,
nickname/path/table changes, source identities, conflicts and intended generation
without altering target files, library tables, component BuildState or approvals.
Persist immutable plan/manifest/check/decision objects and append-only attempt
events in an application-owned integration store via a forward migration.
Migrations preserve existing releases and use normal SQLite transaction ownership.
Keep publication state separate from component BuildState and desktop task state.

**Completion check:** First install, two-source plan, update/removal, identical
no-op and stale/concurrent-base fixtures have explicit results. Unsafe paths,
duplicate aliases and unmanaged collisions are rejected. Dry-run hashes of the
entire target and component store remain unchanged, and migration/reopen tests
preserve prior immutable records.

#### 13.4 — Deterministic staging and exact semantic validation

Stage the complete proposed generation in an owned isolated directory. Combine
the declared components into `BFT_Symbols.kicad_sym`, assemble the declared
`.pretty` library and STEP/reference layout, and preserve unmanaged entries only
under a declared, verified policy. Apply only the versioned namespace/path
relocation allowlist; retain component originals in their content-addressed store.

Verify native KiCad parsing, required symbol-to-footprint/pin-to-pad mappings,
model path resolution, placement and versioned semantic comparisons on exact
staged bytes. Compare engineering fields, including geometry and symbol/pin
properties, for all source and previously installed retained components. Copy
STEP bytes unchanged. A changed electrical/geometry/placement value requires a
new component release; integration cannot silently repair it. Diagnostic renders
or previews do not become the source of replacement engineering data.

Produce the deterministic installation manifest after final files/checks are
fixed; verify it separately and retain post-manifest results in audit. The
generation identity is its external canonical hash, not a self-field or random
run ID. Do not embed that hash into file bytes which determine the same hash.
Any staged-byte or mapping change invalidates bound checks and authorization.

**Completion check:** Two clean staging runs with fixed source/target/base inputs
have identical file, deterministic-check and manifest hashes. Allowed relocations
pass; pin/type/mapping, geometry, placement, reference, extra/missing entry and
tampered STEP faults fail. Updating one of two components preserves the other's
engineering content/source bindings and all immutable source hashes.

#### 13.5 — Exact integration review and authorization

Show the frozen plan, source approvals, expected base, semantic differences,
final file/manifest hashes and required check results. Obtain a fresh trusted
AuthenticatedPrincipal and a deliberate approve/reject decision with a reason.
Store the authorization binding and actor/time/decision in separate immutable
audit objects. Block approval for stale/incomplete/failed or wrong-target content.

Reusing authorization requires identical plan, manifest, target, expected base
and required check bindings. Changes require a new plan/staging/check/review
cycle. An idempotent retry resolves the existing exact decision/publication
receipt; it does not duplicate an approval or silently approve changed content.
Late cancellation and checkpoint/log failure report the actual committed outcome
with separate recovery warnings, applying the Phase 12 decision rule.

**Completion check:** Input approval, release approval, saved actor/label and
inspection alone cannot authorize installation. Authenticated decisions bind the
exact content; stale-base/changed-target/hash/check failures are rejected.
Decision rollback, storage failure, late cancellation and retry cases preserve
one truthful immutable decision and the prior recoverable state.

#### 13.6 — Atomic publication, conflict handling and rollback

Implement the supported complete-generation mechanism from 13.2 under sections
216–218. Lock the installation target, recheck expected base and all staged
hashes/check/authorization bindings, persist a recoverable journal, and perform
one declared publication boundary covering files and library-table references.
Sequential per-file replacements cannot be reported as atomic publication.
Unknown files, external edits or a changed base fail without overwriting them.

Journal previous/new manifest/generation hashes, authorization and publication
intent before switching. On restart, reconcile only a complete verified old or
new generation, preserve failed attempts, and complete audit consistently.
Rollback checks the current base under the same lock and restores the complete
prior generation and table/reference state, recording a new audit event.
Cancellation before publication cleans owned staging; once the publication
boundary starts, resolve its real committed outcome before reporting or closing.

**Completion check:** Test faults before staging, after checks, before/during
publication and after the switch before audit completion. Inject process crash,
disk/write/permission failure, lock conflict and concurrent target edits. Every
case retains or recovers a complete verified generation without partial success,
duplicate authorization or lost history. Complete rollback and unsupported-target
rejection pass on the declared platform/filesystem.

#### 13.7 — Project workflow, IPC round trips and safe recovery

Expose deliberate plan/dry-run, stage/inspect, authorize, publish/update and
rollback through shared headless/desktop services. Keep their controls and status
separate from **Approve Inputs** and **Approve Exact Release**. Save/load may
retain integration object references and unfinished drafts under an explicit
versioned session extension; it never restores live authority or auto-publishes.
Recheck source approvals, current target/base and current principal on resume.

Before target changes, detect an unsaved or actively edited KiCad project. Offer
an explicit save/reload/close or Cancel policy for supported operations; never
discard editor changes or trust only an old on-disk snapshot. Refresh/reopen
libraries using the declared tested mechanism, and invalidate readiness when
the connected board/project or source release changes. Keep blocking reasons
visible while allowing inspection and session saving.

In a disposable real project, install and use the component in the schematic
and PCB with its installed footprint and STEP references. Check native save/
reopen and CLI compatibility, then use supported PCB Editor IPC to inspect the
installed component instance and compare its pin/pad/placement semantics to the
declared source/mapping. Schematic usability is native-editor/CLI evidence for
KiCad 10, not an invented schematic IPC operation. Board writes, if offered,
need an explicit supported transaction/undo contract and extra acceptance cases.

**Completion check:** Source and installed entries exercise standalone and
PCM-installed KiCad workflows without a repository checkout or PartSmith wheel
installation. Correct-session IPC, native save/reopen, two-component
installation/update and project-relative relocation. Unsaved-work Cancel,
disconnection, switched board, session load and repeated invocation preserve
project data, immutable approvals and truthful installation state.

#### 13.8 — Full Phase 13 gate and evidence closeout

Run all milestone checks plus relevant Phase 8/9/12 regressions against final
source and installed PCM runtime bytes. Keep offline contract/CLI checks and
real PCM/desktop/IPC integration evidence distinct. Test the exact final PCM ZIP,
its payload and prepared/bundled runtime,
resource identities, upgrade/removal/reinstall and declared network/offline path.
Mocks are useful negative tests;
they cannot replace the required real supported KiCad target. Record commands,
runtime/capability locks, schema/plugin/data resource parity, target fixtures,
canonical/golden hashes, semantic results, authorization/publication/rollback
receipts and failure-injection evidence. Capture usable installed components
and native project round trips. Apply the repository's hash closeout, including
all affected active and CI manifests and artifact identities outside input maps.
Record the 13.1 contract checkpoint in `docs/gates/phase-13.1-artifacts.json`
and the full gate in `docs/gates/phase-13-artifacts.json`. Add their implemented
offline contract/native-CLI source/PCM checks and input-map verification to
CI when those receipts exist. Real desktop/IPC acceptance needs separately
recorded supervised target evidence; a headless CI skip is not that evidence.

**Phase 13 gate (blocking):** All numbered work items and milestones 13.1–13.8
pass. Two approved components are usable in one installed packed symbol library;
one can be updated while the other remains semantically unchanged. Source bundle
bytes/approvals remain immutable. Required CLI/PCB IPC/native-editor round trips,
exact authorization, stale-plan/concurrent-edit rejection, complete atomic
publication, crash recovery and rollback pass on at least one declared target.
All mandatory negative cases and final source/PCM/hash checks pass. Only this
complete recorded gate permits Phase 14; 13.1 PASS alone closes R13-01. PCM package
install/prepare/launch/update/uninstall/reinstall acceptance is mandatory; a
successful manual plugin copy cannot substitute for it. Verify that Phase 13
automation and gate receipts contain no new PartSmith wheel build/test dependency.

## Phase 14 — Packaging and clean installation

Build on Phase 13's verified Python IPC mechanism. The production artifact is
one PCM ZIP containing PartSmith source, resources and pinned requirements.txt.
KiCad installs upstream binary wheels into its per-plugin Python environment.
The PartSmith ZIP does not carry Python, CAD/native DLLs, a wheel cache or Conda.
Installation, updates and environment recreation require internet access.
No offline installer or offline edition is maintained. Phase 14 adds clean-machine
online lifecycle acceptance and the complete production-matrix proof.

1. Build the production application.
2. Pin the selected CAD runtime in KiCad-managed requirements.
3. Verify the online binary dependency closure for Python 3.11/Windows AMD64.
4. Generate dependency/license manifest.
5. Test clean-machine installation.
6. Test upgrade/uninstall.
7. Test runtime diagnostics.
8. Expand the validated 0402 pipeline to all eight STD-010 package variants.
9. Run the full manufacturer-backed golden, negative, reproducibility, and
   KiCad compatibility corpus for each variant; record results per variant.

**Phase 14 gate (blocking):** A clean supported machine passes automated
install, launch, runtime-diagnostic, upgrade, and uninstall tests. The
production package declares the pinned CAD/runtime dependencies and validated
dependency/license manifest. KiCad provisions the binary wheels online without
manual CadQuery/OCP/OCCT/Conda installation. KiCad's bundled Python 3.11 and
Tesseract 5 with eng/deu/chi_sim language data are explicit prerequisites.
An external Python 3.12 installation is not required. The optional
`runtime.min_version` field is not an enforcement boundary; the action verifies
Python 3.11 and the actual pinned dependencies before engineering work.
All eight production variants pass the complete release
corpus; single-component success is insufficient for this gate.

**Installation policy revision, 2026-10-08:** The project owner removed offline
installation from scope. Production now uses Python IPC and KiCad-managed
requirements; the 0.2.x executable bundle and its receipts are historical only.
The 0.3.1 online candidate targets bundled Python 3.11. The retired 0.3.0
Python 3.12 candidate and its receipts remain historical. PDL schema 1.1 adds
explicit
per-terminal dimensions, bent-lead profiles and measured index geometry;
symbol serializer 2.0 spaces IC pins. Historical PDL 1.0 and serializer 1.0
contracts retain their bytes. The pinned `mvp-1@1.1` profile still requires all
eight STD-010 variants. See [Phase 14 evidence and remaining blockers](../docs/gates/phase-14.md).
This checkpoint does not assert clean-machine acceptance or Phase 14 PASS.

# B.F.T. --- PartSmith

## Product Specification --- PartSmith

**Project:** Board Forge Tools (B.F.T.)\
**Product:** PartSmith\
**Tool:** AI-Driven Component Builder\
**Repository:** `partsmith` (independent repository)\
**Status:** Current engineering specification; implementation status above
with a deferred Component Acquisition extension\
**Version:** 0.9.6\
**Target EDA:** KiCad\
**Primary output:** Native KiCad symbol + footprint + 3D model, packaged
as a usable component library through the PartSmith build workflow.
Purchase from B.F.T. is a post-MVP extension, outside Phases 0–14.\
**Original product-description date:** 2026-09-18; revised baseline date: 2026-10-05

------------------------------------------------------------------------

# PartSmith Product and Repository Identity

**B.F.T. --- Board Forge Tools** is the overall suite of tools.

**PartSmith** is the name of this tool.

**PartSmith function:** AI-Driven Component Builder.

**Repository:** `partsmith`

PartSmith is developed, versioned, tested, and released in its own
independent repository. Other B.F.T. tools will have their own
independent repositories.

The descriptive name **AI-Driven Component Builder** identifies
PartSmith's function; it is not a separate product name.

``` text
B.F.T.
Board Forge Tools
│
├── PartSmith
│   AI-Driven Component Builder
│   Repository: partsmith
│
├── Tool 02
│   TBD
│   Independent repository
│
└── ...
```

# AI Provider Authentication and Billing

## AI-001 — User-supplied provider credentials

PartSmith shall support user-supplied credentials for configured external
AI providers. The user owns and controls the provider account and API key.

## AI-002 — AI usage billing

External AI inference charges are paid directly by the user to the
selected AI provider under that provider's applicable account, plan, and
pricing terms. PartSmith shall not represent provider usage as included
in the PartSmith application unless a future commercial offering
explicitly changes this model.

## AI-003 — Credential security

API keys and other provider credentials are secrets. They shall never be
written to Component IR, evidence, generated artifacts, manifests,
build hashes, exported component packages, ordinary logs, or diagnostic
reports.

## AI-004 — Provider transparency

Before external documents or document-derived content are sent to an AI
provider, PartSmith shall identify the selected provider/model and the
applicable data-handling configuration.

## AI-005 — GPT API credential for testing

For development and testing, `BFT_TOKEN` in the repository-root `.env`
file is the GPT/OpenAI API key. Live GPT/OpenAI provider tests shall load
this variable into the test process and use its value to authenticate
with the OpenAI provider adapter. This credential is for testing only;
customer credentials remain user-supplied under AI-001.

The `.env` file and the value of `BFT_TOKEN` shall not be committed to
source control or copied into the specification, test fixtures, logs,
or generated outputs. AI-003 applies to this testing credential. Tests
requiring live provider access shall report a missing credential clearly
when `BFT_TOKEN` is unset or empty; offline tests shall not require it.

# PartSmith Runtime, Dependencies, Licensing, and Installation

## INSTALL-001 — Single-product installation

The customer installs one PartSmith PCM package. KiCad provisions its exact
pinned Python/CAD dependencies online in the plugin's managed environment.
Users do not manually install CadQuery, OCP, OCCT, Conda or individual DLLs.

Supported prerequisites are KiCad 10.0.6 on Windows AMD64 with its bundled
Python 3.11 (verified locally as 3.11.5), and external Tesseract 5 with
eng/deu/chi_sim language data. PartSmith does not package either prerequisite.
KiCad creates a private per-plugin venv and installs pinned upstream wheels;
PartSmith never installs dependencies into KiCad's base interpreter.

The 3.11 closure pins NumPy 2.4.6, SciPy 1.17.1 and contourpy 1.3.3, plus
backports.tarfile 1.2.0, importlib_metadata 9.0.1 and zipp 4.1.1 for the 3.11
dependency graph. CadQuery 2.8.0 / OCP distribution 7.9.3.1.1 / OCCT 7.9.3
remain the selected CAD tuple. Windows cp311 wheel and installed member
identities are in `runtime-lock-1.1.json`; historical cp312
`runtime-lock-1.0.json` remains unchanged. Snapshots, replay and project plans
select the lock and constraints matching the running Python. A Python baseline
change is a build-input change; old approvals must never be relabeled as 3.11.

PCM customers select bundled Python in KiCad's Python/IPC preferences. The
repository batch installer discovers it beside the verified KiCad CLI and sets
`api.interpreter_path`, preserving other settings and retaining the exact old
preferences in its transactional backup. This preference applies to all Python
IPC plugins. Dry runs change no preferences or files. Close KiCad and PartSmith
before installation. Existing 3.12 plugin caches must be recreated through
KiCad's **Recreate Plugin Environment** action. The helper does not delete
caches, durable sessions or user data. External Python is not a customer
prerequisite. Producer tooling may retain Python 3.12 for historical checks
and gate hash closeout.

Installation, updates and environment recreation require internet access.
Offline installation, runtime bundles and an optional offline edition are not
supported. Phase 14 proves the clean-machine online path through PCM.

## INSTALL-002 — Development versus customer runtime

Development environments may use package managers, Conda/Miniforge,
system Python, KiCad development installations, or other
developer tooling. Those development requirements shall not become
customer installation requirements unless explicitly approved.

## INSTALL-003 — Backend packaging

Production PartSmith shall declare the selected CAD runtime and its native
Python dependencies in pinned requirements.txt. KiCad downloads their upstream
binary wheels into its per-plugin environment. PartSmith does not extract or
repackage those DLLs into its release ZIP. The verified runtime is invoked
through the PartSmith backend adapter.

Missing or corrupt runtime files shall produce a specific runtime error;
users shall not be instructed to manually discover dependency packages.

## INSTALL-004 — Dependency manifest

The distribution shall maintain a machine-readable dependency manifest:

```yaml
dependency:
  name:
  version:
  source:
  license:
  license_files:
  platform:
  architecture:
  sha256:
```

The manifest shall distinguish PartSmith-shipped files, upstream packages fetched
by KiCad, and external Python/OCR prerequisites. Record source, version, license
and available archive identities for the supported dependency closure. Downloaded
wheels are not counted as files redistributed inside the PartSmith PCM ZIP.

## INSTALL-005 — License compliance

PartSmith shall preserve required license notices, attribution, and
license texts for redistributed open-source dependencies. Production
release checks shall compare the dependency manifest against packaged
files. Preserve integration compatibility review and upstream package provenance
for downloaded dependencies; changing the installation method does not itself
establish license compliance or approve an unresolved review.

## INSTALL-006 — Runtime reproducibility

The selected 3D backend and all runtime components capable of affecting
generated STEP geometry shall be recorded in the build manifest and
included in reproducibility metadata.

# v0.9.7 Standards Lock and Implementation Baseline

## v0.9.7 External Reference Baseline

The v0.9.6 standards lock is retained, with KiCad plugin/IPC capability references
reviewed on 2026-10-05 for the Phase 13 plan. Its roles remain:

- KiCad 10 documentation — native KiCad component/library concepts and
  KiCad 10 CLI behavior.
- KiCad official Python bindings documentation — IPC API integration.
- IPC-7351 — Generic Requirements for Surface Mount Design and Land
  Pattern Standard.
- Applicable JEDEC package-outline documentation for the supported PDL
  package variants.

These references establish the implementation boundary; they do not
replace the authoritative manufacturer documentation for an exact part.

This release locks the roles and integration boundaries of external
references. Package-specific evidence completeness and executable standards
reproducibility are separate milestones under STD-014; neither is claimed
complete merely by publication of this specification.

## STD-001 — KiCad baseline

PartSmith's initial native-artifact target remains **KiCad 10.x**.

The implementation shall treat KiCad's native symbol and footprint
formats as version-sensitive artifacts and shall validate generated
artifacts against the supported KiCad version rather than claiming
universal forward compatibility.

The repository shall maintain a versioned KiCad adapter boundary so that
future KiCad format/API changes do not require rewriting the core IR,
PDL, generators, or validators.

## STD-002 — Native KiCad artifacts

The initial native outputs are:

```text
Symbol:
*.kicad_sym

Footprint library:
*.pretty/
    *.kicad_mod

3D model:
*.step
```

PartSmith may generate these formats directly only through deterministic,
version-tested serializers/generators.

The generated artifacts shall not be labeled as if KiCad itself created
them.

### Mandatory STEP rule and 3D backend architecture

Every initial MVP production component release **MUST contain a valid STEP
(`.step`) artifact**, symbol, footprint, and their required validation.
Partial symbol-only or footprint-only production releases are outside this
MVP contract. `model_3d.required` may be false in a candidate, but must be true
for the MVP release profile; the flag cannot waive STEP or cross-validation.

A component requiring 3D that lacks a valid STEP artifact cannot receive
an engineering/release PASS.

PartSmith owns the engineering geometry definition through the
Component IR and PDL. 3D-generation implementations consume those
authoritative structures through a versioned 3D-generator interface.

PartSmith uses **CadQuery/OCP/OCCT** as its sole 3D-generation runtime.
It is an implementation of the authoritative geometry definition, not a
competing source of engineering truth.

```text
                    Component IR
                         │
                         ▼
                        PDL
                         │
                         ▼
                 PartSmith 3D API
                         │
                 ┌───────┴────────┐
                 │                │
                 ▼                ▼
             CadQuery/OCP/OCCT Backend
                 │                │
                 ▼                ▼
           CadQuery geometry       OCCT
                 │                │
                 │                ▼
                 │              STEP
                 │                │
                 └───────┬────────┘
                         ▼
                 STEP Validation
                         │
                         ▼
              Footprint ↔ 3D
              Cross-Validation
```

#### CadQuery backend

The CadQuery backend shall consume Component IR and PDL directly,
generate CAD geometry programmatically, use the supported
CadQuery/OCP/OCCT runtime, and generate STEP directly from CAD geometry.
It shall record CadQuery, OCP, and OCCT runtime versions and validate the
resulting STEP artifact.

CadQuery is the selected implementation runtime, not the authoritative
engineering source.

#### CadQuery runtime boundary

CadQuery shall be integrated through a PartSmith backend adapter. The
customer runtime shall declare required CadQuery/OCP/OCCT components in
KiCad-managed requirements so users do not install the CAD runtime manually.

The adapter shall expose deterministic geometry construction and STEP export
through a controlled interface. Runtime versions, exact dependency archive
hashes, exporter settings, and the Python version shall be recorded for
reproducibility. The CadQuery, OCP, and OCCT versions shall be pinned as one
tested compatibility tuple in a reviewed lockfile or constraints file.
The tuple shall also record the supported operating system, architecture,
actual Python 3.11 patch/build, dependency source, archive SHA-256, and redistributable
license files. A different tuple is a reproducibility-relevant build input
and requires fresh Phase 6 validation.

#### Generator independence

[Section 11](#11-independent-footprint-and-3d-generation) defines the mandatory
independence rule; section 89 specifies allowed generator inputs.

#### Runtime identity

The CadQuery runtime shall be recorded in build metadata:

```yaml
three_d_backend:
  name: CADQUERY
  version:
  adapter_version:
  runtime_versions:
    python:
    cadquery:
    ocp:
    occt:
```

The CadQuery/OCP/OCCT/Python runtime versions are mandatory.

The pinned runtime tuple is a build input and participates in reproducibility
metadata and dependency invalidation.

#### Mandatory final artifact

```text
STEP (.step) = REQUIRED FINAL 3D ARTIFACT
```

CadQuery source code is not a substitute for STEP.

STL, VRML, GLB, and other visualization/mesh formats are not substitutes
for the required STEP artifact and are not part of the normative
PartSmith 3D output contract unless explicitly added by a future
specification revision.

## STD-003 — KiCad IPC API

The repository shall include an IPC adapter boundary for live KiCad
interaction and validation.

The preferred integration path for supported live KiCad operations is
the official KiCad IPC API and its maintained Python bindings.

The adapter shall isolate KiCad-specific API objects from the core
Component IR and validation model.

For the pinned KiCad 10.0.6 target, IPC acceptance uses a running PCB Editor;
the installed CLI does not offer `api-server`. Schematic-editor IPC and headless
IPC available in a later KiCad release are outside this target's acceptance.
Any future target requires a fresh installed-build capability record before
using those operations. Supported CLI validation remains a separate boundary.

The IPC adapter is an integration mechanism; it is not the authoritative
source of engineering geometry.

## STD-004 — KiCad CLI validation

The repository shall use `kicad-cli` where it provides deterministic
validation, conversion, export, rendering, or compatibility checks that
are appropriate to the PartSmith acceptance pipeline.

Phase 8 and later release gates shall use the native CLI for symbol and
footprint parse/round-trip and render checks. Passing an internal PartSmith
syntax parser is necessary but not sufficient for KiCad compatibility.

CLI availability and version shall be recorded in the validation
manifest.

Tests shall distinguish:
- generator correctness
- KiCad parser/open compatibility
- KiCad rendering/export behavior
- IPC integration behavior

## STD-005 — KiCad internal API units

The PartSmith internal engineering coordinate convention remains:

```text
length = millimeters
angle  = degrees
```

The KiCad IPC adapter shall explicitly convert between PartSmith
millimeters and KiCad IPC distance units. No implicit conversion is
permitted.

The adapter shall round-trip representative geometry through the
conversion layer and verify that tolerance remains within the configured
validation limits.

## STD-006 — KiCad symbol/footprint relationship

KiCad's documented model remains authoritative for the integration
boundary:

```text
Schematic Symbol
      │
      │ footprint assignment
      ▼
PCB Footprint
      │
      │ 3D model association
      ▼
3D Model
```

The electrical relationship between symbol pins and footprint pads shall
remain a PartSmith validation responsibility. A syntactically valid KiCad
file is not sufficient for engineering PASS.

## STD-007 — IPC-7351 role

IPC-7351 is adopted as a **land-pattern methodology/reference**, not as
an unrestricted source of component-specific truth.

IPC-7351 addresses surface-mount land-pattern geometry and associated
design elements such as clearances and courtyard concepts. It also
recognizes that mounting/process conditions can affect land-pattern
choices.

PartSmith shall therefore record which land-pattern source was selected:

```text
MANUFACTURER_RECOMMENDED
IPC_DERIVED
PDL_DERIVED
```

Manufacturer-recommended land patterns remain preferred when available
for the exact component/package.

IPC-derived dimensions must retain their derivation inputs and rule
version in evidence/provenance.

PartSmith shall not silently substitute an IPC-derived pattern for an
authoritative manufacturer recommendation.

## STD-008 — IPC does not define electrical behavior

IPC package/land-pattern methodology shall never be used to infer:
- pin function
- electrical type
- active-low behavior
- alternate electrical function
- power classification

Those remain manufacturer-evidence/IR responsibilities.

## STD-009 — JEDEC role

JEDEC package-outline standards shall be used selectively for physical
package identity and geometry for the supported package corpus.

The JEDEC layer may establish or corroborate:
- package family
- package dimensions
- dimensional tolerances
- terminal/pin topology
- numbering/orientation conventions
- package-body geometry

JEDEC data shall not invent electrical behavior.

When manufacturer-specific package drawings differ from a generic package
standard, the manufacturer-specific evidence for the exact part/package
takes precedence and the discrepancy shall be preserved in provenance.

## STD-010 — Initial package-standard corpus

Before production support is declared for each package variant, the PDL
entry shall identify the applicable manufacturer/package-standard
references.

Initial PartSmith production corpus:

```text
0402
0603
0805
SOT-23
SOIC-8
TSSOP-16
QFN-16-3x3-0.5P
QFN-24-4x4-0.5P
```

The repository shall not claim that a package variant is standards-backed
merely because it belongs to a familiar family. Each concrete PDL
variant requires an explicit standards/reference record or a documented
manufacturer-specific basis.

## STD-011 — Standards evidence is versioned

Every standards-derived value shall record, where available:

```yaml
standard_reference:
  organization:
  document:
  revision:
  section:
  table_or_figure:
  access_date:
```

A standards update shall not silently change an existing released PDL
entry. It shall create a PDL revision and trigger the normal dependency
invalidation/review process.

## STD-012 — Standards hierarchy

For package/land-pattern decisions, the normative resolution order is:

```text
Exact manufacturer evidence
        ↓
Applicable package standard
        ↓
Applicable IPC methodology
        ↓
PDL-derived rule
        ↓
INFERRED / UNKNOWN
```

This is domain-specific. The hierarchy must not be used to override
authoritative electrical evidence.

## STD-013 — Final standards review boundary

The repository bootstrap does not require importing the entire KiCad,
IPC, or JEDEC standards universe.

The implementation shall use:
- the supported KiCad 10 documentation/API surface,
- the applicable IPC land-pattern methodology,
- the applicable package-outline references for the eight supported PDL
  variants.

Additional standards are added only when a new supported package or
engineering requirement is introduced.

## STD-014 — Standards review completion criterion

Three separately recorded milestones govern standards readiness:

1. **Role baseline locked:** KiCad integration boundaries, domain-specific
   source precedence, and IPC/JEDEC roles are defined. This permits repository
   implementation to begin; it is not approval of a package entry.
2. **PDL entry complete:** each entry has exact manufacturer/standard citations,
   extracted values, revision identity, and validation. Phase 3 requires the
   first 0402 entry; Phase 14 requires all eight production variants.
3. **Executable reproducibility verified:** offline access to recorded inputs,
   version participation, and dependency invalidation pass Phase 9 and are
   repeated over the full Phase 14 corpus.

Neither a role baseline nor a reference-directory link substitutes for the
package-specific evidence records in STD-011 and section 121.5. The source
register in section 247 records documentation entry points, not completed
package-standard approval.

## CODE-001 — Python code quality standards

All production Python source code, test code, and executable maintenance
scripts in the PartSmith repository shall follow the
[PEP 8 Style Guide for Python Code](https://peps.python.org/pep-0008/)
and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

PEP 8 governs formatting and syntax where the guides conflict. The Google
guide supplies complementary naming, documentation, and design guidance where
it does not conflict with PEP 8 or this specification. Ruff 0.16.8, configured
in `pyproject.toml`, is the executable lint/format policy for the current
baseline; changing its version or selected rules requires reviewed configuration
and updated gate evidence. Python lines shall not exceed 79 characters,
excluding explicitly exempted generated files and third-party source material.

The repository shall configure automated linting and formatting checks
to enforce the automatable portions of these standards. CI shall fail if
those checks fail. Code review remains responsible for requirements that
cannot be verified automatically, including clear naming, public API
documentation, and maintainable design.

## CODE-002 — Reproducible dependency resolution

The repository shall use a reviewed lockfile or constraints file for CI and
release builds. Build, test, lint, and CAD-runtime dependencies shall be
resolved to exact versions; the resolver and Python version shall be recorded
in CI evidence. Version ranges may describe allowed user installation inputs,
but they shall not be the sole source of a release build's dependency set.
# 1. Scope of PartSmith

### In scope

-   Datasheet ingestion
-   PDF page selection
-   Text extraction
-   Table extraction
-   Diagram/image interpretation
-   Pinout extraction
-   Package/mechanical dimension extraction
-   Electrical pin-type interpretation
-   Symbol generation
-   Footprint generation
-   3D model generation
-   KiCad-native library generation
-   Cross-checking symbol pins against footprint pads
-   Validation
-   Visual inspection/testing
-   User review
-   Regeneration/correction
-   Provenance tracking

### Not initially in scope

-   Full BOM management
-   Lifecycle monitoring
-   Supplier inventory monitoring
-   Automatic part substitution
-   Complete PCB design-rule analysis

Component purchasing or distributor/manufacturer acquisition is also outside
Phases 0–14. These phases process user-supplied datasheets, evidence, IR, and
PDL; they do not place orders or claim procurement capability. Datasheet
evidence acquisition is distinct from purchasing a physical component.
-   Automatic schematic design
-   Automatic PCB placement/routing

Those may become separate B.F.T. tools.

------------------------------------------------------------------------

# 2. User Workflow

## 2.1 Start

User selects:

**B.F.T. → Component Builder**

The builder opens a workflow similar to:

``` text
Component Builder
────────────────────────────────────

1. Source
2. Extract
3. Interpret
4. Review inputs and resolve evidence
5. Generate
6. Validate
7. Review and approve release
8. Export / approve project integration
```

------------------------------------------------------------------------

# 3. Source Input

The minimum required input is:

### Datasheet

Supported initially:

-   PDF

Potential future inputs:

-   Manufacturer web page
-   HTML
-   Image
-   ZIP containing manufacturer documentation
-   CAD package information
-   IPC/JEDEC/package-standard documentation

### Page selection

The user must be able to specify pages.

Example:

``` text
Datasheet:
TPS62130.pdf

Relevant pages:
8, 9, 10, 34

Additional pages:
36
```

The user should also be able to specify what each page contains:

``` text
Page 8:
Pin configuration

Page 9:
Pin descriptions

Page 34:
Package dimensions

Page 36:
Recommended PCB land pattern
```

If the user does not know the relevant pages, B.F.T. may scan the
document and propose candidate pages.

The user must be able to accept or change the selection.

------------------------------------------------------------------------

# 4. Source-of-Truth and Evidence Precedence

No single source is authoritative for every engineering domain. B.F.T.
shall assign source authority according to the type of information being
established.

  ---------------------------------------------------------------------
  Engineering information            Preferred authority
  ---------------------------------- ----------------------------------
  Pin numbers and pin functions      Manufacturer datasheet

  Electrical behavior                Manufacturer datasheet and
                                     official manufacturer
                                     documentation

  Package mechanical dimensions      Manufacturer package/mechanical
                                     drawing

  Recommended land pattern           Manufacturer recommended land
                                     pattern

  Standard package geometry          Applicable JEDEC package standard

  Generic land-pattern methodology   Applicable IPC standard

  3D physical geometry               Manufacturer mechanical
                                     drawing/CAD data, then applicable
                                     package standard

  Symbol presentation                Manufacturer datasheet plus B.F.T.
                                     symbol conventions
  ---------------------------------------------------------------------

Manufacturer-specific data shall take precedence over generic standards
when the two describe different requirements for the specific
part/package. Standards shall not be used to invent electrical behavior
that is absent from manufacturer documentation.

B.F.T. must preserve the evidence and precedence used to establish every
important generated value.

For example:

``` text
U1.3
  Source: TPS62130 datasheet
  Page: 9
  Table: Pin Functions
  Row: 3
```

For footprint dimensions:

``` text
Footprint:
  Source: TPS62130 datasheet
  Page: 34
  Drawing: Package Dimensions
  Dimension: 3.00 ± 0.10 mm
```

For recommended land pattern:

``` text
Footprint:
  Source: datasheet
  Page: 36
  Section: Recommended Land Pattern
```

This provenance information is important for review and debugging.

------------------------------------------------------------------------

# 5. Information Extraction

B.F.T. shall extract, where available:

### Component identity

-   Manufacturer
-   Manufacturer part number
-   Part family
-   Description
-   Package name
-   Package code
-   Datasheet revision
-   Datasheet date
-   Datasheet URL
-   Manufacturer URL

### Pin information

-   Pin number
-   Pin name
-   Pin type
-   Electrical function
-   Pin group
-   Power classification
-   Active-low indication
-   Clock indication
-   No-connect indication
-   Exposed pad
-   Thermal pad
-   Alternate functions

### Package information

-   Package type
-   Package dimensions
-   Body length
-   Body width
-   Body height
-   Lead dimensions
-   Lead pitch
-   Pad dimensions
-   Pad spacing
-   Pin 1 location
-   Thermal pad dimensions
-   Tolerances
-   Recommended land pattern

### 3D information

Where sufficient mechanical information exists:

-   Body dimensions
-   Lead dimensions
-   Pin 1 marking
-   Exposed pad
-   Height
-   Chamfers
-   Rounded corners
-   Package orientation

------------------------------------------------------------------------

# 6. Intermediate Component Representation

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

B.F.T. shall NOT have the AI directly write final KiCad files from
unstructured text.

The system should first create a normalized intermediate representation
(IR).

Example:

``` yaml
component:
  manufacturer: Texas Instruments
  mpn: TPS62130RGTR
  package:
    name: VQFN
    body:
      length_mm: 3.0
      width_mm: 3.0
      height_mm: 0.95
    pitch_mm: 0.5
    peripheral_lead_count: 16
    exposed_terminal_count: 1
    pin_count: 17  # for a manufacturer-confirmed conductive exposed terminal
    exposed_pad: true

pins:
  - number: 1
    name: SW
    type: passive
  - number: 2
    name: PG
    type: output
  - number: 3
    name: VIN
    type: power_in

footprint:
  terminal_group_count: 17
  thermal_pad: true
```

The IR becomes the controlled contract between:

-   AI extraction
-   Symbol generator
-   Footprint generator
-   3D generator
-   Validation engine

------------------------------------------------------------------------

# 7. Symbol Generation

The generated symbol must follow KiCad's native symbol model.

KiCad 10 documents symbols as consisting of graphical items, pins, and
fields. Pins have both graphical properties and electrical properties
used by ERC. Symbol libraries use the `.kicad_sym` format.

## Symbol requirements

B.F.T. shall generate:

-   Symbol name
-   Reference designator
-   Value
-   Manufacturer
-   Manufacturer part number
-   Datasheet link
-   Description
-   Footprint association
-   Pins
-   Pin numbers
-   Pin names
-   Electrical pin types
-   Graphical pin properties
-   Units where required
-   Alternate representations where required
-   Hidden/power pins where appropriate

## Symbol quality rules

The generator must enforce:

-   Consistent pin placement
-   Logical grouping of pins
-   Correct pin numbering
-   Correct pin names
-   Correct electrical types
-   Correct orientation
-   Correct connection points
-   Readable symbol graphics
-   KiCad grid conventions
-   No disconnected pin graphics
-   No duplicate physical pin IDs; intentional repeated symbol representations
    must map explicitly to the same physical IR pin
-   No accidental pin-number/name changes during regeneration

------------------------------------------------------------------------

# 8. Footprint Generation

KiCad 10 describes footprints as the physical interface between a
component package and the PCB. Footprints can contain pads, graphical
shapes/text, 3D models, and metadata. Native footprint libraries use
`.pretty` directories containing `.kicad_mod` files.

B.F.T. shall generate native KiCad footprints.

## Footprint requirements

The footprint generator shall support:

-   Pad count
-   Pad numbering
-   Pad shape
-   Pad dimensions
-   Pad position
-   Pad layers
-   Through-hole drill dimensions where applicable
-   SMT pads
-   Thermal/exposed pads
-   Solder-mask settings
-   Paste settings
-   Courtyard
-   Fabrication layer
-   Silkscreen
-   Reference field
-   Value field
-   Description
-   Keywords
-   Footprint properties
-   3D model association (applied only after independent footprint and
    3D generation/validation)

## Land pattern source

When the manufacturer provides a recommended land pattern, B.F.T. should
prefer that information over attempting to infer a land pattern solely
from package dimensions.

The source and page of the selected land pattern must be recorded.

The PDL records source identity, revision, reference, and content hash. The
IR evidence record supplies the source document identity and page. A generated
footprint records both sets of provenance in its deterministic metadata and
dependency projection. If the selected source has no page, the artifact records
that the page is not available; it must not invent a page number.

If the datasheet contains insufficient information to safely generate a
footprint, B.F.T. must stop and request additional information rather
than silently inventing dimensions.

------------------------------------------------------------------------

# 9. Symbol-to-Footprint Mapping

This is a critical validation point.

B.F.T. shall automatically compare:

``` text
Symbol Pin
      ↓
Pin Number
      ↓
Footprint Pad
```

Example:

``` text
Symbol             Footprint

Pin 1  ─────────── Pad 1
Pin 2  ─────────── Pad 2
Pin 3  ─────────── Pad 3
...
Pin 16 ─────────── Pad 16
```

Validation must detect:

-   Missing pad
-   Extra pad
-   Duplicate pad shape or ungrouped repeated terminal number (section 93.1)
-   Incorrect numbering
-   Incorrect exposed-pad mapping
-   Pin/pad count mismatch
-   Pin-name/pad-number inconsistency

A component cannot receive a **PASS** result if this relationship has
unresolved errors.

------------------------------------------------------------------------

# 10. 3D Model Generation

B.F.T. shall generate a 3D representation when mechanical evidence is
sufficient. Insufficient evidence blocks the MVP production release; candidate
previews may remain available with explicit incomplete status.

KiCad supports 3D models associated with footprints. Current KiCad
documentation identifies STEP and VRML as supported component model
formats, with STEP appropriate where dimensional accuracy is important
and VRML useful for visual rendering.

PartSmith does not define those other formats as component-output requirements.

## Preferred component model

For B.F.T. component libraries:

**Primary:** STEP

**No alternate 3D output is required or accepted by the PartSmith MVP contract.**

## 3D model requirements

The generated model should represent:

-   Overall package dimensions
-   Body height
-   Body outline
-   Lead/pad geometry where appropriate
-   Pin 1 marker
-   Thermal/exposed pad where visible
-   Package orientation
-   Correct origin
-   Correct scale
-   Correct rotation

The 3D model generator must produce a model in the canonical B.F.T. 3D
coordinate convention and an explicit placement transform. The final
associated model must align with the footprint if cross-validation
passes. The footprint MUST NOT be used to determine the model geometry.

The footprint and 3D model are independent artifacts. They may share the
same Component IR and Package Definition Library inputs, but neither
artifact may be treated as the source of truth for constructing the
other. Final KiCad association follows independent generation and preliminary
geometry validation; final-byte checks then run under section 167.

------------------------------------------------------------------------

# 11. Independent Footprint and 3D Generation

This is a **hard architectural rule** for B.F.T.

> **The footprint and 3D model MUST be built independently of one
> another. Neither artifact may be generated by reading the other
> artifact's geometry and copying it.**

Both artifacts may use the same authoritative inputs:

``` text
                  Component IR
                       │
             Package Definition Library
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
   Footprint Generator        3D Model Generator
          │                         │
          ▼                         ▼
    *.kicad_mod                  *.step
          │                         │
          └────────────┬────────────┘
                       ▼
             Independent Cross-Check
                       │
                       ▼
                3D Placement Viewer
```

### Why this rule exists

Independent generation creates a useful engineering cross-check. If the
footprint and 3D model independently agree on package dimensions,
center, pin/pad locations, pin-1 orientation, and height, that agreement
provides evidence that the underlying package interpretation is correct.

If B.F.T. generated the 3D model directly from the footprint, the two
artifacts could agree simply because one copied the other. That would
eliminate much of the value of the comparison.

### Prohibited behavior

B.F.T. must not:

-   Generate a footprint by measuring or extracting geometry from its
    own 3D model.
-   Generate a 3D model by using generated footprint pads as the
    authoritative pin geometry.
-   Automatically move pads or reshape the model merely to make the two
    artifacts agree.
-   Hide an alignment discrepancy by applying an unexplained offset.

The only permitted shared source is the **Component IR / Package
Definition Library / authoritative source documentation**.

### Required workflow

1.  Extract package information from source documents.
2.  Normalize the information into Component IR.
3.  Identify the applicable Package Definition Library definition.
4.  Generate the footprint independently.
5.  Generate the 3D model independently.
6.  Validate each artifact independently against its source
    requirements.
7.  Apply the declared placement transform in the headless validation engine.
    The Phase 12 viewer displays this placement for interactive review; it is
    not a prerequisite for automated cross-validation.
8.  Perform automated cross-validation.
9.  If discrepancies remain, report them rather than silently correcting
    them.
10. After preliminary geometry validation, finalize the KiCad association,
    then validate final files/references before manifest creation and approval.
    Section 167 defines the required sequence and invalidation rules.

------------------------------------------------------------------------

# 12A. Independent Artifact Principle --- Mandatory Rule

The governing rule and rationale are in
[section 11](#11-independent-footprint-and-3d-generation); generator input
boundaries are in section 89. This section adds no separate contract.

# 12. 3D Viewer / Placement Validator

The first B.F.T. tool shall include a **3D Viewer / Placement
Validator**. Its purpose is not merely to display a model; it is an
engineering validation interface for determining whether the
independently generated 3D model correctly belongs on the independently
generated footprint.

Complete part inspection also includes the actual generated schematic symbol.
The same separate viewer shall provide **Symbol / Pin Mapping** alongside
**3D / Footprint**, showing the native symbol preview, exact bytes/properties,
pin numbers, names and electrical types, and correspondence to footprint pads.
Follow the [Phase 12 inspection contract](#phase-12-viewer-controls-and-engineering-state)
for artifact bindings, discrepancies, stale/missing data and read-only behavior.

## Viewer window and banner

The viewer shall open as a separate, resizable, modeless popup from the Phase
9.5 GUI extended in Phase 12. The viewer popup shall have no banner;
`resources/PartSmith-Banner3.png` shall span the main Phase 9.5 GUI's complete
client width, reaching both edges and scaling proportionally with that GUI. The
[Phase 12 viewer-window contract](#phase-12-viewer-window-and-banner) defines
the window behavior and banner placement, aspect ratio, packaging, resizing,
and acceptance checks. Placement controls and the 3D viewport occupy the
viewer's full available client area.

The main GUI's viewer button shall become available when the current session
is ready and remain available after popup close. Its reopen behavior and the
main GUI's **Save**/**Load** buttons follow the
[Phase 12 main-window control and saved-session contract](#phase-12-main-window-controls-and-saved-sessions).

All viewer-triggered scripting logs shall stream to the Phase 9.5 GUI's log
box under the [Phase 12 scripting-log contract](#phase-12-scripting-logs).

## Viewer capabilities

The viewer should provide:

-   Rotate, pan, and zoom
-   Top, bottom, front, side, and isometric views
-   Toggle footprint pads, silkscreen, courtyard, fabrication geometry,
    and 3D body
-   Highlight individual pads/pins
-   Highlight pin 1
-   Show coordinate origin and X/Y/Z axes
-   Measure distances
-   Inspect package dimensions
-   Inspect the generated symbol and its actual pin-to-pad mapping
-   Show symbol properties, pin names/electrical types and bound validation

## Placement controls

The user should be able to inspect and, where appropriate, adjust the 3D
model placement parameters:

``` text
Position:
  X offset
  Y offset
  Z offset

Rotation:
  X rotation
  Y rotation
  Z rotation
```

These values must be stored explicitly in the Component IR / generated
component manifest and must never be silently changed.

## Automated placement checks

The viewer/validation engine should check:

-   Model center relative to footprint center
-   Pin-to-pad alignment
-   Pin 1 orientation
-   Package rotation
-   X/Y offset
-   Z height above the PCB reference plane
-   Body width and length relative to package data
-   Lead/pin placement where represented by the model
-   Exposed/thermal pad alignment where applicable
-   Mirroring or unintended inversion
-   Scale

## Human-assisted validation

The user should be able to visually inspect the component while the
validation engine overlays or highlights discrepancies. The viewer
should make it obvious when a model appears shifted, rotated, mirrored,
too high/low, or inconsistent with the footprint.

## Full-board context

The initial implementation should focus on **component-on-footprint
validation**. Full PCB placement/context viewing may be supported later,
but it should not be required for the first release of the AI Component
Builder.

## Important rule

The viewer is a validation surface, not a mechanism for making
independently generated artifacts appear correct. If the model only
aligns after unexplained manual correction, B.F.T. should retain the
discrepancy, identify the correction, and require review.

------------------------------------------------------------------------

# 13. KiCad Compatibility

Generated libraries must be native KiCad libraries rather than
proprietary B.F.T. libraries that require conversion.

Primary native formats:

``` text
Symbol:
*.kicad_sym

Footprint:
*.pretty/
    *.kicad_mod

3D:
*.step
```

KiCad's developer documentation specifies the native s-expression
formats for symbol and footprint libraries. KiCad also explicitly
documents these formats for third-party generators. B.F.T. should
therefore identify itself as a third-party generator rather than falsely
identifying generated files as having been generated by KiCad.

## Generator metadata

B.F.T. should use a B.F.T.-specific generator identifier.

Example:

``` text
generator = partsmith
```

Never impersonate KiCad's own generator identifier.

------------------------------------------------------------------------

# 14. AI Provider Architecture

B.F.T. should NOT be hard-coded to one AI provider.

Use a provider abstraction:

``` text
                B.F.T. AI Interface
                       │
        ┌──────────────┼──────────────┐
        │              │              │
     OpenAI         Anthropic       Google
        │              │              │
      GPT             Claude         Gemini
```

Additional providers can be added later.

## Provider release scope

Section 31 requires one configured provider adapter for the MVP. OpenAI,
Anthropic, and Google Gemini are candidate adapters, not three mandatory
deliverables. Record the selected provider, API/model versions, capabilities,
authentication mechanism, and dated official references in its adapter manifest
before Phase 11 acceptance. All use the interface in section 133 and the
credential/billing rules AI-001–AI-004.

GitHub Copilot integration is optional and must use an officially supported
interface established at implementation time; a subscription is not evidence
of a general-purpose API entitlement. GitHub Models is not an integration target:
the dated retirement reference is maintained in section 247. Do not substitute
that retired API for Copilot.

# 15. Provider Interface

The typed interface in [section 133](#133-ai-provider-interface) is the
authoritative provider contract. Providers return structured interpretation
candidates to the Evidence/IR workflow. Deterministic generators and validators
own artifact production and engineering validation; providers cannot write
production KiCad files or grant approval.

# 16. AI + Deterministic Architecture

The architecture should deliberately separate:

### AI responsibilities

-   Read datasheet
-   Understand tables
-   Interpret diagrams
-   Extract component information
-   Resolve ambiguous terminology
-   Propose symbol structure
-   Propose footprint geometry
-   Propose 3D geometry
-   Explain uncertainty

### B.F.T. deterministic responsibilities

-   Validate schema
-   Validate dimensions
-   Validate pin numbering
-   Validate pad numbering
-   Generate KiCad files
-   Validate KiCad syntax
-   Validate library structure
-   Check symbol/footprint consistency
-   Check 3D/footprint alignment
-   Run KiCad validation tools where available
-   Produce final PASS/FAIL result

**AI output must never bypass deterministic validation.**

------------------------------------------------------------------------

# 17. Evidence, Confidence, and Uncertainty

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

Every extracted or derived value shall carry provenance and an evidence
status.

The user-facing system shall not rely solely on an AI-generated
confidence score. Confidence may be retained internally, but evidence
status and source provenance are the authoritative review signals.

Supported value/evidence statuses:

``` text
DIRECT
DERIVED
STANDARD
USER_OVERRIDE
INFERRED
UNKNOWN
AMBIGUOUS
CONFLICTING
MISSING
```

`HUMAN_REVIEW_REQUIRED` is a build/review state, not a value status.

Example:

``` yaml
pin:
  number: 7
  name: EN
  evidence_status: DIRECT
  confidence: 0.99
  source:
    document: datasheet.pdf
    page: 9
    region: "Pin Description Table"
```

Important engineering values shall never be promoted to APPROVED solely
because an AI model reports high confidence.

If B.F.T. cannot establish a value safely:

``` text
⚠ HUMAN REVIEW REQUIRED

Thermal pad width could not be determined.

Evidence status: AMBIGUOUS

Possible values:
  2.40 mm
  2.50 mm

Source pages:
  34
  36

B.F.T. will not generate a production-ready footprint
until this value is resolved.
```

# 18. Human Review

Before export, the user should see:

## Symbol preview

-   Symbol graphic
-   Pin names
-   Pin numbers
-   Electrical types

## Footprint preview

-   Pad geometry
-   Pad numbers
-   Courtyard
-   Silkscreen
-   Fabrication outline
-   Dimensions

## 3D preview

-   Component model
-   Footprint
-   Pin 1
-   Orientation
-   Height

## Source/provenance panel

Every important generated value should be traceable back to its source.

------------------------------------------------------------------------

# 19. Validation Levels

B.F.T. should have more than unit tests.

The validation system shall contain five explicit levels. The terms
below are normative and replace any interpretation that the earlier test
sections are merely an unordered list.

## Level 1 --- Unit validation

Test individual functions and deterministic primitives:

-   PDF extraction adapters
-   Dimension parsing
-   Pin parsing
-   Unit conversion
-   Canonicalization
-   KiCad serialization
-   Pad generation
-   Symbol generation
-   3D parameter generation
-   Coordinate transforms

## Level 2 --- Schema and domain validation

Verify that:

-   Component IR conforms to its frozen schema
-   Evidence conforms to its schema
-   PDL conforms to its schema
-   domain invariants hold
-   invalid IR never reaches artifact generators

## Level 3 --- Artifact validation

Validate each generated artifact independently:

-   symbol structure and semantics
-   footprint geometry and required metadata
-   STEP parseability and geometry requirements
-   artifact hashes and manifests

## Level 4 --- Integration and cross-validation

Validate relationships between independently generated artifacts:

-   symbol ↔ footprint pin mapping
-   footprint ↔ 3D placement
-   package topology ↔ generated geometry
-   KiCad parse/open/round-trip behavior
-   generated test-board connectivity where applicable

## Level 5 --- System/release validation

Validate the complete workflow:

-   golden components
-   negative/fault-injection corpus
-   reproducibility
-   security
-   resource limits
-   export/install behavior
-   approval/release rules
-   CI gates

A release is not considered validated merely because Levels 1--2 pass.

Example:

``` text
Component
 ├── identity
 ├── package
 ├── pins
 ├── footprint
 └── 3d
```

Invalid IR must never reach the file generator.

------------------------------------------------------------------------

# 20. KiCad File Tests

B.F.T. must generate actual KiCad files and then test that they can be
opened/parsed by the target KiCad version.

Tests include:

``` text
Generated .kicad_sym
        ↓
KiCad parser
        ↓
PASS / FAIL
```

and:

``` text
Generated .kicad_mod
        ↓
KiCad parser
        ↓
PASS / FAIL
```

The test environment should contain a pinned KiCad version.

------------------------------------------------------------------------

# 21. Functional End-to-End Tests

This is one of the most important requirements.

B.F.T. should maintain a corpus of real datasheets.

Each test case contains:

``` text
datasheet.pdf
expected component data
expected symbol characteristics
expected footprint characteristics
expected 3D characteristics
```

Example:

``` text
TEST CASE: TC-QFN-16-001

Input:
  manufacturer datasheet
  pages 8, 9, 34, 36

Expected:
  16 peripheral leads plus one manufacturer-confirmed conductive exposed terminal
  17 physical electrical terminals / logical conductive pad groups
  0.5 mm pitch
  exposed pad
  QFN package
```

The complete pipeline is tested:

``` text
PDF
 ↓
AI extraction
 ↓
Component IR
 ↓
Symbol
 ↓
Footprint
 ↓
3D model
 ↓
KiCad validation
 ↓
Visual validation
```

------------------------------------------------------------------------

# 22. Golden Component Tests

Maintain a collection of manually verified components.

Each golden component contains:

``` text
golden/
  component_001/
    source.pdf
    expected_ir.json
    expected_symbol.kicad_sym
    expected_footprint.kicad_mod
    expected_model.step
    expected_manifest.json
```

When B.F.T. changes, regenerate the components and compare the results.

Unexpected changes require review.

------------------------------------------------------------------------

# 23. Visual Regression Testing

The generated symbol, footprint, and 3D model should be rendered
automatically.

Compare the resulting images against approved reference images.

This catches problems that text/unit tests will miss:

-   Wrong pin orientation
-   Missing pin
-   Bad silkscreen
-   Incorrect pad placement
-   Wrong body dimensions
-   3D model rotation
-   Incorrect scale
-   Missing pin-1 marker

------------------------------------------------------------------------

# 24. Physical/Geometric Validation

Footprints should be tested mathematically.

Examples:

``` text
Pad pitch
Pad width
Pad height
Pad-to-pad clearance
Body clearance
Courtyard clearance
Thermal pad clearance
```

Where the datasheet supplies tolerances, B.F.T. should preserve the
tolerances rather than reducing them to unexplained single values.

------------------------------------------------------------------------

# 25. ERC-Oriented Symbol Testing

Generated symbols should be tested with representative schematic
connections.

Examples:

-   Power input connected correctly
-   Output connected correctly
-   Bidirectional pins correctly classified
-   No-connect pins behave correctly
-   Open-collector/open-drain pins represented correctly
-   Passive pins behave correctly

The goal is to detect an AI-generated symbol whose graphics look correct
but whose electrical semantics are wrong.

------------------------------------------------------------------------

# 26. PCB Connectivity Testing

A test board should automatically be generated for representative
components.

Example:

``` text
Symbol
  ↓
Schematic
  ↓
Update PCB
  ↓
Footprint
  ↓
Pad/net connectivity
```

B.F.T. should verify that:

``` text
Symbol Pin 1 → Footprint Pad 1 → PCB Net
```

remains intact.

------------------------------------------------------------------------

# 27. 3D Functional Tests

For each generated component:

1.  Load footprint.
2.  Load 3D model.
3.  Verify model exists.
4.  Verify model loads.
5.  Verify scale.
6.  Verify rotation.
7.  Verify origin.
8.  Verify alignment.
9.  Render from standard views.

Required views:

-   Top
-   Bottom
-   Front
-   Side
-   Isometric

------------------------------------------------------------------------

# 28. Regression Testing

Every bug discovered in production should become a permanent regression
test.

Example:

``` text
BUG-0042

Problem:
AI interpreted pin 5 as an input.

Actual:
Pin 5 is open-drain output.

Regression test:
TPSxxxx pin 5 must classify as open-drain output.
```

------------------------------------------------------------------------

# 29. Failure Policy

B.F.T. must prefer:

> **FAIL SAFE**

over:

> **MAKE SOMETHING UP**

Examples requiring human review:

-   Missing package dimensions
-   Conflicting datasheet information
-   Ambiguous pin numbering
-   Unreadable diagram
-   Missing recommended land pattern
-   Conflicting package drawings
-   Uncertain 3D height
-   Ambiguous thermal pad dimensions

The generated component should be marked:

``` text
INCOMPLETE — HUMAN REVIEW REQUIRED
```

rather than silently accepting an AI guess.

------------------------------------------------------------------------

# 30. JEDEC / Industry Standards

STD-007–STD-014 define the adopted roles and precedence of manufacturer,
JEDEC, IPC, and PDL evidence. Section 121.5 defines the required structured
citations. Section 247 maintains external entry points.

Each PDL entry must complete its applicable standards review before its gate.
An unknown edition or absent licensed reference remains an explicit evidence
gap; it is not a future promise, an assumed standard, or an implicit task
assigned to the user.

# 31. Component Package Types

## MVP release acceptance matrix

This is the single scope matrix for Phases 0–14; STD-010 supplies the exact
production variant names. The matrix is part of the pinned release profile
`mvp-1`, whose version/content hash enters the input snapshot and requirements
context. It cannot be weakened by IR or user configuration.

| Dimension | Required acceptance coverage | Gate |
| --- | --- | --- |
| Bootstrap package | 0402, using GOLD-0402-001 and its approved PDL | 3–9 |
| Production packages | All eight STD-010 variants; at least one manufacturer-backed golden component and relevant negative cases for each | 14 |
| Model accuracy | CLASS A for the 0402 bootstrap in Phases 6–8 and for every production variant in Phase 14; each applicable PDL lists required measured body/terminal/clearance observables; CLASS B/C are previews only | 6–8, 14 |
| AI providers | One selected, configured adapter with pinned interface/model metadata and full provider contract/security tests; others optional | 11, 14 |
| Languages | English and at least one named non-English language pinned in the release profile before Phase 10; native-text and scanned/OCR samples for each, plus a mixed-language sample; retain originals and translations | 10–12, 14 |
| Document difficulty | Every category in section 182, including expected blockers for incomplete/conflicting evidence | 10–11 |
| Reproducibility | Identical released bytes and deterministic hashes for equal frozen inputs and runtime | 9, 14 |
| Interaction | Headless build/review service first; UI over the same service later | 8, 12 |

Additional languages/providers do not become claimed supported capabilities
until their own fixtures pass the same suite. The language and provider choices
are recorded configuration decisions, not implicit expansion to every example.

The 0402 bootstrap row is a proof-of-pipeline scope for Phases 3–9. It does
not satisfy the production-package row, and no Phase 3–9 gate may claim MVP
production approval for the remaining seven STD-010 variants. Production
approval is evaluated only by the Phase 14 gate.
There is no requirement for every document difficulty to be crossed with every
package/language; the corpus manifest records explicit coverage and expected
outcomes. Each production package still needs its own full engineering corpus.

Through-hole axial/radial/DIP/TO parts, connectors, SOT-223, QFP, other QFN/DFN,
LGA, and BGA variants are future examples outside the MVP release gate. Adding
production variants requires a reviewed scope/PDL/corpus revision.

# 32. Output Package

A component release includes native symbol, footprint, STEP, manifest, and
validation/provenance records. Section 175 defines the reproducible component
bundle; section 174 defines the installed KiCad library layout. Those serve
different purposes and are not competing workspace directory schemas.

# 33. Component Manifest

Every generated component shall have a machine-readable manifest. This
abbreviated content example omits required hashes and the separate audit
envelope; sections 110 and 166–167 define the complete contract.

Example:

``` json
{
  "bft_version": "0.1",
  "component": {
    "manufacturer": "Example",
    "mpn": "ABC123"
  },
  "source": {
    "datasheet": "source.pdf",
    "pages": [8, 9, 34]
  },
  "outputs": {
    "symbol": "symbol/BFT_Component.kicad_sym",
    "footprint": "footprint/BFT_Component.pretty/BFT_Component.kicad_mod",
    "model_3d": "3d/BFT_Component.step"
  },
  "validation": {
    "symbol": "PASS",
    "footprint": "PASS",
    "pin_mapping": "PASS",
    "model_3d": "PASS"
  }
}
```

------------------------------------------------------------------------

# 34. API Key Security

B.F.T. must never store provider API keys in generated component files.

Keys should be stored through the host operating system's secure
credential mechanism where practical.

At minimum:

-   Never put keys into logs.
-   Never put keys into manifests.
-   Never put keys into generated libraries.
-   Never send keys to another AI provider.
-   Do not expose keys in error dialogs.
-   Support environment-variable configuration for developers.
-   Support per-provider configuration.
-   Clearly identify which provider is being used.

------------------------------------------------------------------------

# 35. Provider Configuration

Conceptual configuration:

``` text
AI Providers

[✓] OpenAI
    API Key: ************
    Model: [...........]

[ ] Anthropic
    API Key: ************
    Model: [...........]

[ ] Google Gemini
    API Key: ************
    Model: [...........]

[ ] GitHub Copilot
    Authentication: [...........]

Default provider:
[ OpenAI ▼ ]
```

The actual supported authentication mechanism must be implemented
according to each provider's current official API/integration
requirements.

------------------------------------------------------------------------

# 36. AI Model Independence

B.F.T. should never assume that one model is permanently superior.

The component-building pipeline should be model-independent:

``` text
              AI Provider
                   ↓
            Structured IR
                   ↓
       B.F.T. Validation Engine
                   ↓
      KiCad Component Generation
```

This makes it possible to change models without rewriting the
component-generation system.

------------------------------------------------------------------------

# 37. Auditability

For every generated component B.F.T. should be able to answer:

> Where did this number come from?

Example:

``` text
Footprint Pad 7 width
    ↓
2.15 mm
    ↓
Datasheet page 36
    ↓
Recommended Land Pattern
    ↓
Dimension X
```

Likewise:

``` text
Symbol Pin 4 electrical type
    ↓
power_in
    ↓
Datasheet page 9
    ↓
Pin description
```

This is a core engineering feature, not optional documentation.

------------------------------------------------------------------------

# 38. Acceptance Criteria for PartSmith

PartSmith is considered ready for release when B.F.T. can:

### Input

-   [ ] Accept a datasheet PDF.
-   [ ] Accept explicit page selections.
-   [ ] Display the selected source pages.
-   [ ] Extract component information.
-   [ ] Preserve source provenance.

### Symbol

-   [ ] Generate a valid native `.kicad_sym`.
-   [ ] Correctly represent pins.
-   [ ] Correctly assign electrical pin types.
-   [ ] Correctly associate the footprint.
-   [ ] Open successfully in KiCad.

### Footprint

-   [ ] Generate a valid native `.kicad_mod`.
-   [ ] Generate a valid `.pretty` library.
-   [ ] Correctly number pads.
-   [ ] Correctly implement the manufacturer's land pattern where
    available.
-   [ ] Include appropriate courtyard/silkscreen/fabrication
    information.
-   [ ] Open successfully in KiCad.

### 3D

-   [ ] Generate a usable 3D model.
-   [ ] Use correct dimensions.
-   [ ] Correctly align the model with the footprint.
-   [ ] Load successfully in KiCad's 3D viewer.

### Integration

-   [ ] Symbol pin ↔ footprint pad mapping passes.
-   [ ] Footprint ↔ 3D model alignment passes.
-   [ ] Generated libraries can be installed/used by KiCad.
-   [ ] Output is reproducible from the same frozen reviewed inputs and pinned runtime/configuration (section 166); live AI reruns are not deterministic replay.

### Testing

-   [ ] Unit tests pass.
-   [ ] Schema tests pass.
-   [ ] KiCad parser/integration tests pass.
-   [ ] End-to-end datasheet tests pass.
-   [ ] Golden component tests pass.
-   [ ] Visual regression tests pass.
-   [ ] ERC-oriented tests pass.
-   [ ] PCB connectivity tests pass.
-   [ ] 3D alignment tests pass.
-   [ ] Regression suite passes.

------------------------------------------------------------------------

# 39. Guiding Principle

The fundamental design principle for the PartSmith is:

> **AI proposes. B.F.T. verifies. B.F.T. generates the final KiCad
> files.**

The system should never equate "the AI produced an answer" with "the
component is correct."

A component is complete only when its:

``` text
Source
  ↓
Extracted Data
  ↓
Component IR
  ↓
Symbol
  ↓
Footprint
  ↓
3D Model
  ↓
Mappings
  ↓
KiCad Compatibility
  ↓
Functional Tests
  ↓
Human Review
  ↓
APPROVED COMPONENT
```

all agree.

------------------------------------------------------------------------

------------------------------------------------------------------------

# 40. Difficult Datasheet Input

B.F.T. must be designed around the reality that component documentation
is frequently imperfect.

The AI Component Builder must not assume that a datasheet is:

-   digitally generated
-   text-searchable
-   written in English
-   organized around a clearly visible symbol
-   limited to one relevant diagram
-   sufficiently complete to directly define the component

The document-processing pipeline must support several classes of
datasheet.

### 40.1 Native Digital PDF

Text, tables, vector graphics, and diagrams can be extracted directly.

``` text
PDF
 ↓
Text/Table extraction
 ↓
Image/diagram analysis where necessary
```

### 40.2 Scanned PDF

Some datasheets are essentially scanned images inside a PDF.

For these documents:

``` text
PDF
 ↓
Page rendering
 ↓
OCR
 ↓
Layout analysis
 ↓
Diagram/image analysis
 ↓
Component extraction
```

OCR must preserve, where possible:

-   Pin numbers
-   Pin names
-   Electrical symbols
-   Units
-   Decimal points
-   Minus signs
-   Package dimensions
-   Tolerances
-   Table structure

B.F.T. must detect likely OCR errors such as:

``` text
0.5 mm → 05 mm
10.0 kΩ → 100 kΩ
1 → I
```

through cross-checking and validation.

------------------------------------------------------------------------

# 41. Diagram and Symbol Discovery

The component symbol may not be presented cleanly in a datasheet.

Possible situations include:

1.  A clear standalone symbol.
2.  A symbol embedded in a larger functional block diagram.
3.  Multiple components shown in one diagram.
4.  The symbol is small or partially obscured.
5.  Pin numbers are difficult to read.
6.  The datasheet provides only a pinout table.
7.  The datasheet provides pin descriptions but no symbol.
8.  Several package variants are shown on the same page.
9.  The symbol representation is simplified rather than electrically
    complete.

B.F.T. must therefore **not depend on finding an existing symbol
graphic**.

The symbol drawing should be treated as supporting evidence rather than
the sole source of truth.

------------------------------------------------------------------------

# 42. Pinout-First Component Reconstruction

A component can be built even when the datasheet does not provide a
conventional schematic symbol.

The minimum useful information may be:

``` text
Pin Number
Pin Name
Pin Description
Electrical Function
```

Example:

``` text
1  VIN    Supply input
2  GND    Ground
3  EN     Enable input
4  SW     Switching node
5  FB     Feedback input
```

B.F.T. can construct the symbol from this information.

The generated symbol should be identified in the build report as:

``` text
SYMBOL GENERATED FROM PIN DATA
```

when no manufacturer symbol was available.

------------------------------------------------------------------------

# 43. Symbol Reconstruction States

B.F.T. should distinguish between:

### Manufacturer-provided symbol

The datasheet provides a usable schematic symbol.

### Reconstructed symbol

The datasheet provides enough pin/function information for B.F.T. to
create a symbol.

### Inferred symbol

Some symbol characteristics must be inferred from component conventions,
standards, or other authoritative documentation.

### Insufficient information

The available information is not sufficient to safely determine the
symbol.

These states must be visible to the user.

B.F.T. must never present an inferred symbol as though it were directly
copied from the manufacturer's documentation.

------------------------------------------------------------------------

# 44. Use of Package Standards When the Symbol Is Missing

Package standards should primarily establish **physical/package
information**, not arbitrary electrical behavior.

A package standard may establish:

-   Package dimensions
-   Pin count
-   Pin numbering convention
-   Pin arrangement
-   Pin pitch
-   Body geometry
-   Lead geometry
-   Pin-1 orientation

The component datasheet remains the authority for:

-   Pin names
-   Pin functions
-   Electrical characteristics
-   Alternate functions
-   Power/ground identification

The system should combine these sources explicitly:

``` text
                 Datasheet
                    │
          ┌─────────┴─────────┐
          │                   │
       Pin Data          Package Data
          │                   │
          │              JEDEC / IPC
          │                   │
          └─────────┬─────────┘
                    ▼
             Component IR
```

A package standard must not be incorrectly treated as a source for
component-specific electrical behavior.

------------------------------------------------------------------------

# 45. Relevant-Page Discovery

The user may provide page numbers, but B.F.T. should also be capable of
finding relevant pages.

The system should classify pages for likely relevance:

``` text
PINOUT
PIN DESCRIPTION
PACKAGE
MECHANICAL
LAND PATTERN
RECOMMENDED PCB LAYOUT
BLOCK DIAGRAM
TYPICAL APPLICATION
ORDERING INFORMATION
```

B.F.T. may propose:

``` text
Likely relevant pages:

Page 7  — Pin Configuration
Page 8  — Pin Description
Page 31 — Package Dimensions
Page 32 — Recommended Land Pattern
```

The user should be able to approve or modify the selection.

------------------------------------------------------------------------

# 46. Image-Based Page Analysis

For scanned or difficult PDFs, B.F.T. should render relevant pages at
sufficient resolution and use vision-capable AI/image processing to
analyze them.

``` text
PDF page
   ↓
High-resolution rendering
   ↓
OCR
   +
Visual analysis
   ↓
Candidate regions
   ↓
Pinout / package / dimension extraction
```

Text extraction and visual analysis should complement each other.

Neither should automatically be treated as authoritative when the two
disagree.

------------------------------------------------------------------------

# 47. Region Selection

B.F.T. should support selecting specific regions of a page.

This is particularly important when:

-   Multiple packages are shown.
-   Multiple components are shown.
-   A large application diagram contains the target component.
-   OCR incorrectly combines nearby labels.
-   A package drawing is surrounded by unrelated mechanical information.

The user should be able to identify the exact diagram or drawing that
B.F.T. should analyze.

------------------------------------------------------------------------

# 48. Multi-Source Evidence

A component build may combine information from multiple pages and
sources.

Example:

``` text
Page 7:
Pin configuration

Page 8:
Pin descriptions

Page 31:
Package dimensions

Page 32:
Recommended land pattern

JEDEC:
Package geometry/reference

Manufacturer:
Additional mechanical drawing
```

The Component IR must retain provenance for each extracted value.

------------------------------------------------------------------------

# 49. Conflicting Evidence

When sources disagree, B.F.T. should not silently choose a value.

Example:

``` text
CONFLICT DETECTED

Body width:

Datasheet page 31:
3.00 ± 0.10 mm

Manufacturer mechanical drawing:
3.05 ± 0.10 mm

Status:
HUMAN REVIEW REQUIRED
```

The system should preserve both values and identify their sources.

Apply the existing domain-specific policies in section 4 and STD-012.
Conflicting authoritative information remains visible, with explicit recorded
resolution under sections 96 and 121.2.

------------------------------------------------------------------------

# 50. Non-English Datasheets

The mandatory language coverage is defined by section 31's release matrix.
Extraction retains original text and explicit language metadata; translations
follow sections 51 and 121.5. Additional candidates include Simplified and
Traditional Chinese, Japanese, Korean, German, French, and Spanish. This list
does not claim that all are implemented or independently add gate requirements.
The architecture must allow language adapters and corpus coverage to expand.

# 51. Language-Aware Extraction

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

B.F.T. should identify the document language before extraction.

``` text
PDF
 ↓
Language Detection
 ↓
Language-aware OCR / text processing
 ↓
Normalized Component IR
```

The Component IR should remain language-neutral.

For example:

``` yaml
pin:
  number: 3
  name: EN
  function: enable_input
```

The original text must still be retained for provenance.

------------------------------------------------------------------------

# 52. Translation vs. Engineering Interpretation

Translation and engineering interpretation should be separate
operations.

Example:

``` text
Original:
使能输入

Translation:
Enable input

Normalized function:
enable_input
```

B.F.T. should preserve:

1.  Original text
2.  Translation
3.  Normalized engineering interpretation
4.  Source location

This allows a human reviewer to determine whether a translation or
interpretation introduced an error.

------------------------------------------------------------------------

# 53. Multilingual AI Validation

B.F.T. should not assume that the selected AI model handles every
language or technical document equally well.

The validation pipeline remains responsible for detecting errors
regardless of provider.

For example:

``` yaml
extraction:
  language: zh-CN
  translated_text: "Enable input"
  normalized_function: enable_input
  confidence: 0.96
```

The original Chinese source text must remain available.

------------------------------------------------------------------------

# 54. Multilingual OCR Validation

For non-English scanned documents, B.F.T. should use multiple checks
where practical:

``` text
OCR
 +
Vision analysis
 +
Package topology
 +
Pin-count validation
 +
Dimension validation
```

If OCR identifies 16 pins but the package drawing clearly shows 24 pins,
the result must be flagged for review.

------------------------------------------------------------------------

# 55. Datasheet Difficulty Classification

B.F.T. should classify source difficulty.

Example:

``` text
SOURCE QUALITY

Digital text       PASS
OCR required       YES
Diagram complex    YES
Symbol found       NO
Pin table found    YES
Package drawing    YES
Land pattern       YES
Language           Chinese

Overall:
REQUIRES ENHANCED EXTRACTION
```

This gives the user visibility into why a build may require additional
review.

------------------------------------------------------------------------

# 56. Human-in-the-Loop Escalation

B.F.T. should allow the AI to stop and ask the user for help when the
evidence is insufficient or ambiguous.

Examples:

> "I found three package drawings. Which one corresponds to the selected
> MPN?"

> "The pin-1 marker is unclear. Please select the correct orientation."

> "The datasheet contains two conflicting thermal-pad dimensions. Please
> select the authoritative drawing."

> "No symbol is provided. I can reconstruct the symbol from the pin
> table. Continue?"

The goal is not to eliminate human involvement. The goal is to make
human intervention occur only where it materially improves correctness.

------------------------------------------------------------------------

# 57. Updated Datasheet Processing Architecture

``` text
                    DATASHEET
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        Digital PDF          Scanned PDF
              │                   │
              │                  OCR
              │                   │
              └─────────┬─────────┘
                        ▼
                Layout Analysis
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
           Text      Tables     Images
              │         │         │
              └─────────┼─────────┘
                        ▼
                 AI Interpretation
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
        Pin / Electrical       Package /
           Information         Mechanical
             │                     │
             └──────────┬──────────┘
                        ▼
                 Standards / PDL
                        │
                        ▼
                  Component IR
                        │
                        ▼
             Symbol / Footprint / 3D
```

------------------------------------------------------------------------

# 58. Updated Datasheet Principle

The AI Component Builder must be designed for the **worst realistic
datasheet**, not the ideal datasheet.

The system should assume that:

> **The symbol may be missing, the PDF may be a scan, the relevant
> information may be buried in a complicated diagram, the pinout may be
> provided only as text, and the document may not be in English.**

B.F.T. should use multiple forms of evidence---datasheet text, OCR,
diagrams, package definitions, JEDEC/IPC standards, manufacturer
documentation, and deterministic validation---to reconstruct the
component.

When evidence is insufficient or contradictory, B.F.T. must stop and
request human review rather than inventing information.

------------------------------------------------------------------------
# Architecture Hardening — Current Normative Baseline

The following sections are normative additions to the prior
architecture.

# 84. Package Definition Library (PDL)

The **Package Definition Library (PDL)** is a first-class B.F.T.
subsystem.

The PDL is a structured engineering knowledge base for reusable physical
package definitions. It is **not** a footprint library or a generator-source
repository.

The PDL represents:

``` text
Package Definition
├── Identity
├── Family
├── Mechanical Geometry
├── Pin Topology
├── Pin-1 Convention
├── Land Pattern Definition
├── Exposed/Thermal Pad Definition
├── 3D Geometry Parameters
├── Coordinate Conventions
├── Validation Rules
├── Source Evidence
└── Revision Metadata
```

A PDL entry may be generic or manufacturer-specific.

## 84.1 PDL example

``` yaml
pdl:
  id: qfn-16-3x3-0p5
  revision: 1

  identity:
    family: QFN
    variant: QFN-16-3x3-0.5P
    peripheral_lead_count: 16
    exposed_terminal_count: 1
    pin_count: 17  # Illustrative manufacturer variant with conductive EP terminal

  mechanical:
    body_length_mm: 3.0
    body_width_mm: 3.0
    body_height_nominal_mm: 0.85
    body_height_min_mm: 0.75
    body_height_max_mm: 0.95

  topology:
    pitch_mm: 0.5
    numbering: counter_clockwise
    pin1_location: top_left
    pins_per_side:
      north: 4
      east: 4
      south: 4
      west: 4

  land_pattern:
    source: manufacturer_or_standard
    exposed_pad_present: true
    exposed_pad_terminal_number: "17"  # Must match the selected manufacturer drawing

  coordinate_system:
    origin: package_center
    x_positive: right
    y_positive: up
    z_positive: away_from_pcb
```

The exact values above are illustrative only.

## 84.2 PDL authority

A PDL entry is authoritative only for the facts explicitly supported by
its evidence.

A generic PDL must not override manufacturer-specific package evidence.

A manufacturer-specific package definition may override a generic
package family definition when the evidence establishes a real
difference.

## 84.3 PDL versioning

Every PDL entry shall have:

-   Stable PDL ID
-   Revision
-   Schema version
-   Source references
-   Effective date
-   Change history
-   Validation status
-   Hash

A PDL revision used by a released component shall remain immutable.

# 85. Component Variant Identity

B.F.T. shall not identify a component only by MPN or only by package
family.

The minimum identity tuple is:

``` text
Manufacturer
+
MPN
+
Package Variant
+
Documentation Revision
```

Where relevant, the identity shall also include:

-   Die revision
-   Temperature grade
-   Automotive grade
-   Ordering suffix
-   Package suffix
-   Lead finish
-   Special mechanical variant

The system shall distinguish:

``` text
same electrical part
different package
```

from:

``` text
same package
different electrical part
```

These are not interchangeable identities.

# 86. Exact Component IR Contract

The Component IR is the authoritative build input after evidence review.

It shall be schema-versioned.

Minimum top-level domains:

``` yaml
component_ir:
  schema_version:
  identity:
  source:
  electrical:
  pins:
  package:
  symbol:
  footprint:
  model_3d:
  evidence:
  standards:
  overrides:
  resolutions:
  validation:
  build:
  revision:
```

Every engineering value that can affect a generated artifact shall be
traceable to:

``` text
DIRECT evidence
DERIVED value
STANDARD value
USER override
```

Values marked only `INFERRED`, `AMBIGUOUS`, `CONFLICTING`, or `MISSING`
cannot silently become production inputs.

# 87. Value Status Model

Every important IR value shall have both a value and a status.

``` text
DIRECT
DERIVED
STANDARD
UNKNOWN
INFERRED
AMBIGUOUS
CONFLICTING
MISSING
USER_OVERRIDE
```

The distinction between `STANDARD` and `DIRECT` is important.

Example:

``` text
Package body width:
  3.00 mm
  status: DIRECT
  evidence: manufacturer drawing

Generic package corner radius:
  0.20 mm
  status: STANDARD
  evidence: package standard
```

An inferred value may be displayed to the user as a candidate, but it
must not be silently promoted to approved engineering data.

# 88. User Override Model

User overrides are explicit engineering decisions.

Each override shall record:

``` yaml
override:
  id:
  path: /package/mechanical/body_height
  value_type: QUANTITY_RECORD
  base_revision_id:
  supersedes_override_id:
  previous_value:
  new_value:
  reason:
  user:
  timestamp:
  evidence_reference:
  approval_state:
```

Rules:

1.  An override never deletes the original evidence.
2.  An override is visible in the review UI.
3.  Override history participates in the full IR record hash; active override
    content participates in snapshot/dependency hashes under section 166.
4.  Removing an override creates a new revision restoring the prior
    derived/source value and reruns validation; it never alters prior history.
5.  Overrides require explicit user action.
6.  An override that creates a validation failure cannot produce `PASS`.
7.  Overrides affecting package topology, pin mapping, or
    safety-critical geometry require human review.

Section 121.6 defines payload types, editable paths, and active bindings;
section 121.8 defines history selection. This abbreviated view is not a
second override schema.

# 89. Generator Input Isolation

Generator inputs are formally separated.

## Symbol generator may consume

-   Component identity
-   Electrical pin model
-   Symbol conventions
-   Approved symbol-specific evidence
-   Approved user overrides affecting symbol data

## Footprint generator may consume

-   Component identity
-   Package PDL
-   Approved mechanical dimensions
-   Approved land-pattern definition
-   Pin topology
-   Approved footprint-specific evidence
-   Approved footprint overrides

## 3D generator may consume

-   Component identity
-   Package PDL
-   Approved mechanical dimensions
-   Approved 3D geometry definition
-   Approved mechanical evidence
-   Approved 3D-specific overrides

## Forbidden cross-generator dependency

The following are prohibited:

``` text
Generated footprint → source geometry for 3D generation
Generated 3D model → source geometry for footprint generation
```

The generated artifacts may be compared after construction, but neither
is allowed to become the authoritative input to the other.

Symbol-to-footprint and footprint-to-3D mapping are owned by an independent
post-generation mapping validator, not by either generator. The validator
consumes the generated artifacts, the authoritative IR pin records, and the
PDL terminal/group definitions. It runs only after independent generation and
reports mapping status and diagnostics without becoming an input to a generator.

# 90. Independent Artifact Contract

Section 11 is the single normative independence rule. Sections 89 and
148 specify its input boundaries and cross-validation checks. Agreement is
evidence of consistency, not proof of source correctness. Both independent
source validation and cross-validation are required by the applicable gates.

# 91. Coordinate and Unit Contract

All internal engineering geometry shall use the units below. Source-document
page regions use the separate document coordinate contract in section 124.1.

``` text
Length: millimeters
Angle: degrees
```

Source documents may use:

-   mm
-   mil
-   inch
-   µm
-   other explicitly supported units

The extraction layer shall retain the original source unit and the
normalized value.

Example:

``` yaml
dimension:
  source_value: 118.1
  source_unit: mil
  normalized_value: 2.99974
  normalized_unit: mm
```

No generator may assume a source unit that was not explicitly
established.

# 92. Transform Contract

Coordinate convention version `1.1` is normative. Engineering frames are
right-handed, use mm/degrees, and use column vectors. In the top-side view,
look toward the PCB from +Z: +X is right, +Y is up, and +Z is away from the PCB.
The PCB surface is z=0. Component/model origin is the package reference-center
projection onto its nominal mounting plane, not a volume centroid. Footprint
origin is the corresponding package reference-center at the PCB surface.
Any package-specific mounting offset or center definition is explicit PDL data.

Canonical STEP geometry is in the model frame. Placement maps model-frame
points into the engineering footprint frame using homogeneous coordinates:

```text
p_destination = T * Rz(rz) * Ry(ry) * Rx(rx) * S * M * p_source
M = diag(mx, my, mz, 1), each m = -1 if mirrored, otherwise +1
S = diag(sx, sy, sz, 1), each s > 0
```

Rotations are active, right-hand positive, extrinsic about fixed source axes,
applied X then Y then Z. Mirror and scale act about the source origin before
rotation. Translation is expressed in destination-frame mm. Direction vectors
use homogeneous w=0 and points w=1. The record declares source/destination
frame IDs, translation, rotation, scale, mirror flags, units, `T*R*S*M`, and
convention version. Defaults may not conceal a frame conversion.

The versioned KiCad adapter owns conversions between these engineering frames
and native KiCad coordinate/angle conventions. Verify conversions against the
pinned KiCad build; never infer a native convention from a viewer orientation.
Bottom-side placement must use an explicit adapter transform and board plane.

Composition A→B→C is `T_BC * T_AB`; inverse reverses operation order.
Composition and inversion return section 150's full affine matrix, not an Euler/
scale/mirror placement record. Nonuniform scale combined with rotation can
produce shear. Preserve it in the matrix; never silently decompose/approximate
it into the simple placement record. An adapter unable to serialize the resulting
affine map must reject it with an unsupported-transform diagnostic. Inversion
or round-trip error beyond the configured tolerance fails input validation.
Phase 6 includes analytical fixtures for identity, basis vectors, 90-degree
rotations, mirror axes, combined noncommuting rotations, composition, inverse,
and bounding boxes. For example Rz(90) maps (1,0,0) to (0,1,0), and T(1,2,3)
maps the origin to (1,2,3). No generated footprint is needed to establish the
model frame or its geometry.

# 93. Package Topology Validation

Before footprint or 3D generation, B.F.T. shall validate:

-   Pin count
-   Pitch
-   Side distribution
-   Numbering direction
-   Pin-1 location
-   Corner behavior
-   Staggering
-   Exposed pad presence
-   Symmetry
-   Mirroring rules

Example failure:

``` text
Package topology invalid

Expected:
  16 pins
  4/4/4/4 distribution
  0.50 mm pitch

Extracted:
  16 pins
  4/4/4/4 distribution
  0.50 mm pitch
  numbering direction reversed

Result:
  HUMAN_REVIEW
```

## 93.1 Terminal and pad counting

`package.pin_count` is the number of physical electrical terminal records in
`pins`, including any conductive exposed terminal. Package marketing names such
as QFN-16 describe peripheral leads and do not override this count. A PDL requires
peripheral_lead_count, exposed_terminal_count, and a terminal map keyed by the
manufacturer's explicit terminal numbers. Do not infer EP numbering from a name.
The section 84.1 example is illustrative: a manufacturer-backed 16+EP variant
has 17 terminals, but a different manufacturer numbering scheme needs its own
mapping. A non-electrical mechanical feature is not an invented electrical pin.

One physical terminal maps to one logical numbered conductive pad group. A group
may contain multiple geometric pad shapes/serializer pad objects, all with the
same terminal number and explicit common group ID. Different terminal groups
cannot share a number; duplicate shape IDs and ungrouped repeated pad numbers
fail. Count groups against electrical terminals, shapes against their declared
group definition, and rendered symbol-unit representations against their explicit
terminal mapping. Non-electrical holes/features are counted separately.

MVP PDL and serializer support for a compound group is accepted only with a
pinned KiCad round-trip fixture. If that representation is unsupported, fail
explicitly rather than duplicate a terminal or merge shapes silently. Exposed
pad/thermal-via structures require declared grouping and electrical connectivity.

# 94. Land Pattern Safety Rules

Package body dimensions shall never be substituted automatically for
land-pattern dimensions.

The precedence order is:

1.  Manufacturer-recommended land pattern
2.  Manufacturer package-specific land-pattern documentation
3.  Applicable IPC methodology
4.  Validated B.F.T. package-family rule

If none is available, B.F.T. may enter `NOT_GENERATABLE`.

The system shall record the land-pattern source independently from
package mechanical evidence.

# 95. Electrical Pin-Type Rules

Canonical IR electrical types are:

```text
input
output
bidirectional
tri_state
passive
free
unspecified
power_in
power_out
open_collector
open_emitter
no_connect
```

These tokens are the single IR vocabulary. A power-flag symbol is a separate
symbol-level construct, not an electrical type of a physical component pin.
Do not synthesize it from a pin name or package standard. Target-format tokens
are mapped explicitly by the versioned serializer; manufacturer labels such as
`power_input` and `power_output` map to `power_in` and `power_out` only through
documented interpretation/migration rules. Retain the original source label.

`unspecified` is a legitimate candidate or explicitly approved pin type.
Electrical behavior must come from manufacturer evidence or recorded approved
rules, never from the spelling of names such as RESET, ENABLE, FAULT, or SENSE.

# 96. Evidence Conflict Resolution

Conflict resolution shall follow this sequence:

``` text
1. Detect conflict
2. Classify conflict
3. Identify authoritative domains
4. Present evidence side-by-side
5. Attempt deterministic derivation
6. Request human decision if unresolved
7. Record the decision
8. Rebuild affected downstream artifacts
```

The system shall not resolve a conflict merely by selecting the AI
answer with the highest confidence. Resolution creates a new active snapshot
and a resolution record; original candidates and audit records remain
immutable. Section 121.2 defines how superseded history is excluded from
active generation checks without deleting it.

# 97. Evidence Sufficiency Gates

Each artifact has a minimum evidence set.

## Symbol

Required:

-   Pin numbers
-   Pin names or explicit absence
-   Electrical types or approved `unspecified`
-   Component identity

## Footprint

Required:

-   Package identity
-   Pin topology
-   Land-pattern dimensions or a validated land-pattern rule
-   Pad count
-   Pad numbering
-   Pin-1 orientation

## 3D model

Required:

-   Package identity
-   Body dimensions sufficient for the target accuracy
-   Pin/lead geometry sufficient for the target accuracy
-   Height or a documented model-height rule
-   Pin-1 orientation

If the required evidence is missing, the artifact enters
`NOT_GENERATABLE` or `HUMAN_REVIEW`, depending on whether a human can
resolve it.

# 98. 3D Model Accuracy Classes

B.F.T. shall distinguish:

``` text
CLASS A — Engineering geometry
CLASS B — Placement geometry
CLASS C — Visual approximation
```

Class A requires dimensional evidence sufficient for engineering use.

Class B is suitable for placement/clearance visualization but may not
prove detailed mechanical dimensions.

Class C is visual-only and must never be presented as a dimensionally
validated model.

The MVP requires CLASS A for every production variant under section 31.
`model_3d.accuracy_class` is required in IR 1.2 and is one of CLASS_A, CLASS_B,
or CLASS_C. The trusted release profile requires CLASS_A for release; an IR
label alone does not prove it. Validators must measure the PDL's required
engineering observables. CLASS_B/C outputs are explicitly marked previews.

# 99. 3D Model Validation

The 3D validator shall check, where applicable:

-   File opens successfully
-   Units are correct
-   Bounding box is finite
-   No NaN/infinite coordinates
-   Scale is expected
-   Body dimensions are within tolerance
-   Height is within tolerance
-   Pin/lead count is correct where mechanically represented
-   Pin-1 marker is correct
-   Orientation is correct
-   Model origin is correct
-   Model is not mirrored unexpectedly
-   Model intersects the PCB plane unexpectedly
-   Model is not floating above the intended mounting plane

A visual preview alone is insufficient for PASS.

# 100. KiCad Compatibility Matrix

B.F.T. shall maintain a compatibility matrix:

``` yaml
kicad_compatibility:
  major_version:
  minimum_supported:
  maximum_tested:
  parser_test:
  open_test:
  round_trip_test:
  known_limitations:
```

The component manifest shall identify the KiCad major version against
which the artifact was validated.

B.F.T. shall not claim universal forward compatibility.

KiCad major releases can change file formats, so compatibility must be
tested rather than assumed. [Reference register: section 247](#247-external-reference-register).

# 101. Native Artifact Validation

For every generated artifact:

``` text
Generate
  ↓
Parse
  ↓
Schema/semantic validation
  ↓
Open with target KiCad version where practical
  ↓
Round-trip or re-save test where practical
  ↓
Compare semantic content
```

A file that merely exists on disk is not considered valid.

Phase 4–5 artifact validators shall perform deterministic structural parsing of
the supported native s-expression subset, including wrapper/version markers,
pad geometry and layers, required graphics, provenance metadata, and courtyard
bounds. KiCad parser, open, and round-trip checks remain compatibility checks
under later integration gates; balanced parentheses alone never constitutes
native-format validation.

# 102. Canonical Serialization and Hashing

For supported Component IR versions, canonical profile 1.0 and the whole-record
hash are defined in [section 121.3](#1213-canonical-profile-10). The whole
normalized record is hashed, including source metadata; equal physical
dimensions alone do not make records with different provenance the same IR.
Build snapshots and generator dependency projections have distinct hash scopes
under section 166; do not substitute the whole-record hash for those scopes.

Before hashing structured artifacts, B.F.T. shall canonicalize:

-   Key ordering
-   Number formatting
-   Units
-   Floating-point precision
-   Line endings
-   Unicode normalization
-   Path representation

The same logical IR must produce the same canonical hash.

Raw source files shall be hashed byte-for-byte.

Canonicalize generated text before finalizing the release artifact, then hash
the exact finalized bytes. Backend-equivalence results are separate from byte
hashes and follow section 166.

# 103. Build Dependency Invalidation

Each state has explicit dependencies.

Example:

``` text
Change pin mapping
    → invalidate symbol
    → invalidate footprint
    → invalidate 3D if pin geometry is affected
    → invalidate cross-validation
```

Example:

``` text
Change silkscreen text only
    → invalidate footprint
    → rerun footprint and applicable final-byte mapping/association/compatibility checks
    → replace results bound to changed footprint bytes, manifest, and release approval
    → do not invalidate 3D
```

Example:

``` text
Change body height
    → invalidate 3D
    → invalidate cross-validation
    → footprint may remain valid unless courtyard/clearance rules depend on height
```

B.F.T. shall not regenerate unrelated artifacts unnecessarily.
Geometry reuse does not preserve an approval or result bound to a different
released file hash. Reuse an independent check only when its declared inputs
and artifact hashes are unchanged (section 167). Final cross-validation involving
the changed footprint receives new exact-byte bindings even when pads are equal.

# 104. Human Review Gates

Human review is required for:

-   Conflicting pin evidence
-   Conflicting package evidence
-   Unsupported package variants
-   Inferred electrical behavior
-   Missing critical mechanical dimensions
-   User overrides affecting connectivity
-   User overrides affecting package topology
-   Cross-validation failures
-   Any artifact classified below its required accuracy class
-   Any release blocked by `HUMAN_REVIEW`

The reviewer must be able to see the evidence supporting the decision.

# 105. Review UI Requirements

The review interface shall expose:

``` text
Source
Evidence
Component IR
Generated artifacts
Validation results
Overrides
Differences
```

For a selected value:

``` text
Value:
  3.00 mm

Status:
  DIRECT

Source:
  Datasheet Rev F
  Page 34
  Region: Package Drawing

Extracted text:
  3.00 ± 0.10

Used by:
  PDL resolution
  Footprint generator
  3D generator
```

The user shall be able to trace both forward and backward:

``` text
Evidence → IR → Artifact → Validation
Artifact → IR → Evidence
```

# 106. AI Output Contract

AI providers shall return structured candidate data rather than
unrestricted final artifacts.

A normalized AI result shall include:

``` yaml
ai_result:
  provider:
  model:
  request_id:
  schema_version:
  candidates:
  evidence_references:
  ambiguities:
  conflicts:
  confidence:
```

AI confidence is advisory metadata only.

AI output must pass schema validation before entering the engineering
pipeline.

# 107. AI Failure Containment

AI failures shall be treated as untrusted input.

The system shall defend against:

-   Hallucinated dimensions
-   Hallucinated pins
-   Fabricated page references
-   Fabricated standards
-   Incorrect translations
-   Prompt injection inside documents
-   Malicious text embedded in PDFs
-   Unsupported file references
-   Overconfident extraction

A document shall be treated as data, not as an instruction to the AI
system.

Instructions embedded inside a datasheet, image, OCR result, or external
web page must not override B.F.T. system rules.

# 108. Source Privacy and Provider Disclosure

Before sending source material to an external AI provider, B.F.T. shall
make the provider boundary visible.

The user shall be able to determine:

-   Which provider receives the document
-   Which model is used
-   Whether the full document or selected pages are sent
-   Whether OCR occurs locally or remotely
-   What information is retained by B.F.T.
-   What provider-side handling is subject to the provider's terms

B.F.T. shall support a local-processing mode where practical.

API credentials shall never be included in source packages or generated
artifacts.

# 109. File and Path Portability

Generated component packages shall not depend on the creator's absolute
filesystem paths.

Use portable references such as:

``` text
${KIPRJMOD}
```

or an explicitly documented library-root convention where supported by
the target KiCad version.

The manifest shall preserve logical paths separately from local
filesystem paths.

# 110. Artifact Manifest v2

The package contains a deterministic engineering manifest and a separate audit
envelope. The following abbreviated field inventory is organized by those
boundaries; sections 166–167 define projection and hashing rules. Local record
IDs are audit metadata, while engineering references use content hashes.

``` yaml
engineering_manifest:
  schema_version:
  component_identity:

  source:
    documents:
    hashes:

  evidence:
    package:
    hashes:

  component_ir:
    schema_version:
    input_snapshot_hash:

  pdl:
    id:
    revision:
    hash:

  generators:
    symbol:
    footprint:
    model_3d:

  outputs:
    symbol:
    footprint:
    model_3d:

  validation:
    overall:
    results:

  compatibility:
    kicad:

  overrides:
    active_content_hashes:

  reproducibility:
    build_inputs_hash:
    dependency_hashes:

audit_envelope:
  schema_version:
  component_id:
  build_id:
  build_status:
  started_at:
  completed_at:
  ir_record_hash:
  engineering_manifest_hash:
  reviews:
  historical_evidence_and_override_refs:
```

# 111. Semantic Diff Requirements

Revision comparison shall compare engineering meaning, not only text
files.

The diff engine shall detect:

``` text
Pin added
Pin removed
Pin renamed
Pin electrical type changed
Pin topology changed
Package variant changed
Body dimension changed
Pitch changed
Land pattern changed
Thermal pad changed
Symbol graphics changed
Footprint graphics changed
3D geometry changed
Placement transform changed
Evidence changed
PDL revision changed
```

A file-level diff may be shown in addition to the semantic diff, but it
shall not replace it.

# 112. Negative-Test Philosophy

A component that is syntactically valid but semantically wrong is one of
the most important failure classes.

The test suite shall therefore contain deliberately plausible errors.

Examples:

``` text
QFN-16 generated as QFN-24
Pin 7 assigned to pin 8
0.5 mm pitch mirrored correctly but numbered incorrectly
3.0 mm package generated with 3.2 mm body
Correct footprint with wrong 3D rotation
Correct 3D model with wrong footprint origin
Correct dimensions with wrong pin-1 marker
Correct pad count with one duplicated pad number
```

Every such test must fail at the appropriate validation layer.

# 113. MVP Release Gate

PartSmith shall not be considered production-ready merely because it can
generate a component.

Production-ready requires:

``` text
Evidence sufficient
AND
IR valid
AND
PDL valid
AND
Symbol valid
AND
Footprint valid
AND
3D valid
AND
Pin mapping valid
AND
Footprint/3D cross-validation PASS
AND
KiCad compatibility PASS
AND
No unresolved blocking conflicts
AND
Required human review complete
```

# 114. Architecture vs. Implementation Acceptance

Architecture acceptance, distinct from implementation gate completion, means:

-   Interfaces are defined.
-   Data ownership is defined.
-   Evidence states are defined.
-   Generator independence is enforced.
-   Validation gates are defined.
-   State transitions are defined.
-   Reproducibility is defined.
-   Failure behavior is defined.

MVP implementation acceptance additionally requires:

-   Working parsers
-   Working generators
-   Working validators
-   Working viewer
-   Working KiCad integration
-   Passing golden corpus
-   Passing negative corpus
-   Passing supported-version compatibility tests

# 115. Executable Contract Completion

The numbered gates assign delivery of schemas, PDL records, generators,
validators, transform implementations, CLI/API behavior, fixtures, and runtime
packaging. A published requirement is not evidence of executable conformance.
Track required repository artifacts and tests against those gates; do not
declare specification publication or a single fixture equivalent to MVP release.

# Final Architecture and Build Specification Position — Current Normative Baseline

The architecture is now considered sufficiently constrained to move
toward implementation-level specification.

The most important architectural boundaries are:

``` text
AI
│
├── interprets documents
├── proposes structured candidates
└── explains ambiguity
        │
        ▼
Evidence Engine
        │
        ▼
Component IR
        │
        ▼
PDL + approved engineering rules
        │
        ├───────────────┐
        ▼               ▼
Footprint Generator   3D Generator
        │               │
        ▼               ▼
 .kicad_mod           STEP
        │               │
        └───────┬───────┘
                ▼
       Deterministic Validation
                │
                ▼
        Cross-Validation
                │
                ▼
          Human Approval
                │
                ▼
             Export
```

The governing rule remains:

> **AI interprets. B.F.T. represents. Deterministic generators
> construct. Deterministic validators decide. Humans resolve
> ambiguity.**

And the independent-artifact rule remains mandatory:

> **The footprint and 3D model are built independently. Their agreement
> is a cross-validation signal, never a license for one artifact to
> define or repair the other.**

------------------------------------------------------------------------

# Appendix A --- External Technical Reference Note

External references are maintained only in
[section 247](#247-external-reference-register). Exact installed-version
compatibility tests govern supported KiCad capabilities.

# Implementation Specification — Current Normative Baseline

## Purpose

v0.9.8 defines the current implementation contract and phase-gate requirements.

This document defines:

-   repository structure
-   runtime architecture
-   exact logical schemas
-   service boundaries
-   adapter interfaces
-   build orchestration
-   deterministic generators
-   validation algorithms
-   persistence
-   CLI/API behavior
-   UI states
-   KiCad integration
-   test fixtures
-   CI gates
-   security boundaries
-   MVP implementation order

The implementation must preserve the architectural rule:

> **AI interprets. B.F.T. represents. Deterministic generators
> construct. Deterministic validators decide. Humans resolve
> ambiguity.**

And:

> **Footprint and 3D model generation are independent. Cross-validation
> compares them; neither generator is allowed to repair or define the
> other.**

# 116. Implementation Goals

PartSmith shall accept authoritative component documentation and produce
a reviewable, reproducible KiCad library item.

Primary deliverables and their component-bundle/library layouts are defined in
sections 175 and 174. Section 118 describes the development repository, not an
exported library.

The implementation must support a headless build path so CI can generate
and validate components without opening the GUI.

# 117. Technology Baseline

The MVP reference implementation shall use:

``` text
Language: Python 3.11 for customer PCM; Python 3.12 retained for historical
producer verification
Data: JSON/YAML
Geometry: deterministic Python geometry + CadQuery/OCP/OCCT backend
3D exchange: STEP
OCR: pluggable adapter
AI: pluggable provider adapter
KiCad integration: KiCad-supported scripting/IPC mechanisms
Testing: pytest
Schema validation: JSON Schema
Hashing: SHA-256
Persistence: SQLite for MVP
```

KiCad 10 shall be the first explicit compatibility target for the MVP
unless the project later selects another target. Current KiCad
documentation identifies `.kicad_sym` symbol libraries, `.pretty`
footprint libraries containing `.kicad_mod` files, and KiCad 10's
IPC/Python API direction; KiCad also documents that major releases can
change file formats and that files saved by a newer major version may not be
backward-compatible with older major versions.
[Reference register: section 247](#247-external-reference-register).

The implementation shall isolate KiCad-version-specific behavior behind
adapters.

# 118. Repository Structure

Recommended repository:

``` text
partsmith/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── partsmith/
│       ├── cli/
│       ├── core/
│       ├── schemas/
│       ├── evidence/
│       ├── extraction/
│       ├── ai/
│       ├── ir/
│       ├── pdl/
│       ├── generators/
│       │   ├── symbol/
│       │   ├── footprint/
│       │   └── model3d/
│       ├── validation/
│       ├── kicad/
│       ├── integration/
│       ├── build/
│       ├── persistence/
│       ├── viewer/
│       └── reporting/
├── pdl/
│   ├── families/
│   └── variants/
├── schemas/
├── fixtures/
│   ├── golden/
│   ├── negative/
│   └── documents/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── system/
│   └── regression/
└── docs/
```

# 119. Module Ownership

  Module                   Responsibility
  ------------------------ ---------------------------------------------
  `core`                   IDs, units, transforms, result types
  `schemas`                Schema loading/versioning
  `evidence`               Evidence objects, provenance, conflicts
  `extraction`             PDF/OCR/table/diagram extraction
  `ai`                     Provider adapters and normalized AI output
  `ir`                     Component IR construction and validation
  `pdl`                    Package definitions and topology
  `generators.symbol`      Native symbol generation
  `generators.footprint`   Native footprint generation
  `generators.model3d`     CadQuery/STEP generation
  `validation`             Deterministic validators
  `kicad`                  Version-specific KiCad adapters
  `integration`            Plans, aggregate contracts, authorization/publication
  `build`                  State machine and dependency invalidation
  `persistence`            SQLite/project artifact storage
  `viewer`                 3D/2D review UI
  `reporting`              Human-readable and machine-readable reports

No module may bypass the Component IR and write production artifacts
from raw AI output.

# 120. Canonical Identifiers

Every object shall have a stable identifier.

Format:

``` text
component_id
evidence_id
pdl_id
build_id
artifact_id
validation_id
override_id
review_id
```

IDs should be UUIDv7 or another sortable UUID format.

Human-readable names are separate from stable IDs.
Integration plan and generation identities are canonical content hashes under
section 174.1. Operational attempt/decision IDs remain separate audit identities.

# 121. Component IR JSON Schema and Contract

## 121.1 Normative Component IR 1.2 contract

IR 1.2 remains the v0.9.8 target. Its implemented Draft 2020-12
[schema](../schemas/component-ir-1.2.schema.json) has ID
`bft://schemas/component-ir/1.2` and `schema_version: "1.2"`. The existing
[IR 1.0](../schemas/component-ir-1.0.schema.json) and
[IR 1.1](../schemas/component-ir-1.1.schema.json) schemas remain authoritative
for their own records; their previously recorded PASS does not cover IR 1.2.

The 16 top-level domains in section 86 are required, including `resolutions`.
IR 1.2 retains IR 1.1 fields except the additions and revised constraints below.
Objects reject unknown fields; named property maps require typed entries.
The root is the IR object, without a `component_ir` wrapper. Electrical,
symbol/footprint-property, standards, overrides, resolutions, and validation
result collections may be empty when not applicable. The immutable model and
canonical JSON profile 1.0 remain the API/serialization basis.

Identity includes raw and normalized manufacturer/MPN values, package variant,
`source_document_id`, and required `source_revision`. The referenced document
has required `revision`, original-file SHA-256, and a portable logical path.
Revision must agree with identity. An unversioned document uses `UNVERSIONED`
plus `revision_basis: {kind: "content_hash", sha256, captured_at}`; the hash
must match the document. It is not an invented publisher revision. Known
revision labels remain verbatim. Optional string identity qualifiers are
`die_revision`, `package_suffix`, `lead_finish`, and `mechanical_variant`, in
addition to the existing ordering/temperature/qualification fields.

Pin numbers remain strings. Electrical types are exactly section 95's enum.
`footprint.land_pattern_source` is exactly `MANUFACTURER_RECOMMENDED`,
`IPC_DERIVED`, or `PDL_DERIVED`; candidate `null` is allowed only with unresolved
footprint status. Override status and `override_id` are independent provenance,
not substitutes for the land-pattern source category. Generic `STANDARD`
must not erase the distinction between IPC and PDL derivation.

Scalar values retain value/status/evidence references. Quantities retain
`source_value`, `source_unit`, status, and evidence references. For unresolved
statuses UNKNOWN, INFERRED, AMBIGUOUS, CONFLICTING, or MISSING, source value/unit
may be null and an `unresolved_reason` string is required when either is null.
For MISSING, source value is null. Concrete unknown-unit numbers remain
candidates, never implicitly mm. Supported non-null units are listed in 121.3.
Normalized value/unit are null unless both source value and unit are known.
If both are known, conversion is exact and supplied normalization must agree.
No placeholder number or fabricated evidence is required to store a candidate.

For DIRECT, DERIVED, STANDARD, or USER_OVERRIDE quantities selected for
generation, values and units must be concrete and provenance must resolve.
Optional min/max bounds must be paired; when supplied, minimum <= nominal <=
maximum. Missing nominal values have no normalized bounds. Selected physical
lengths are positive; zero is permitted for PDL-declared optional geometric
features such as an absent chamfer. Placement follows convention 1.1 in
section 92 and retains translation, rotation, positive scale, and mirror flags.

## 121.2 Component IR API and validation behavior

`ComponentIR(data)`, `from_json`, and `from_file` validate and normalize a
supported declared version without mutating input. The model is immutable;
`.data` returns a detached Decimal-valued tree, `.canonical_bytes` is the exact
serialization, and `.sha256` is the full record hash. `normalize_ir`,
`canonical_ir`, and `ir_hash` retain these semantics.

`validate_ir` returns sorted stable Issue(path, code, message) records, using
JSON Pointer paths; throwing entry points use IRValidationError. Duplicate
keys, normalized key collisions, invalid UTF-8, non-JSON objects, and non-finite
numbers fail explicitly. Structural validation accepts incomplete candidates.

`for_generation=True` requires an explicit versioned requirements context:
`validate_ir(data, for_generation=True, requirements=context)`. The context
lists required IR paths and PDL/rule/generator versions for the artifact.
Missing context is an error; callers cannot select an empty requirement set
to waive a supported generator's declared mandatory inputs.

IR 1.2 generation validation additionally requires `revisions=revision_store`,
a read-only protocol exposing `get_revision(id)` and `get_inventory(sha256)`.
The validator checks the retained chain, inventory hashes, and approved review
bindings under sections 121.7–121.8. A missing store/snapshot or invalid transition
blocks generation. Structural candidate loading may omit the store but cannot
claim that external history is validated. Phase 2 implements this protocol with
detached fixture snapshots; Phase 8 connects it to persisted review records.

The active input closure consists of those paths plus their recursively
referenced active evidence, standards, derivations, translations, approved
overrides, and resolution decisions. Unresolved or null required values block
generation. DIRECT needs evidence; DERIVED needs derivation and input links;
STANDARD needs a versioned standard; USER_OVERRIDE needs a recorded approved
override bound to the target path and new value. Dangling references and cycles
in provenance/resolution dependencies fail structural validation.

Sections 121.6–121.8 define typed overrides, independent candidate relevance,
and immutable decision history. Required active values bind to the revision's
selected approved decisions. Unresolved historical records do not block solely
by status, but relevant unresolved candidates require an explicit disposition.
Only dependency edges participate in cycle detection; target-binding and
history edges have the exact projection rules in section 166.

This precheck does not itself assign build state. Input-only checks in section
137 establish IR_VALIDATED before generation. Output validators, compatibility,
and explicit review establish APPROVED afterwards. Phase 2 implements the
requirements-context protocol; later phases supply PDL/generator-specific
requirements and the review UI. No artifact validator is an input prerequisite.

## 121.3 Canonical profile 1.0

- UTF-8 without BOM or trailing newline; compact JSON separators.
- NFC Unicode and LF line endings in strings; object keys sorted by Unicode
  code point. Array order is significant and preserved.
- Numbers use exact decimal tokens without exponent notation or unnecessary
  fractional zeros. `1`, `1.0`, and `1e0` serialize as `1`; negative zero is `0`.
- JSON numbers are parsed directly as Decimal. Python floats use CPython's
  shortest round-trip decimal spelling (unchanged between 3.11 and 3.12).
  No tolerance-based rounding occurs:
  `0.1 + 0.2` and `0.3` are distinct inputs. Numeric tokens are limited to 100
  significant coefficient digits and an absolute decimal exponent of 100
  after removing redundant trailing zeros, before and after
  unit conversion; out-of-range values are rejected, never truncated.
- Unit arithmetic uses a local 256-digit Decimal context, independent of the
  caller's context. Explicit units: mm, mil (0.0254 mm), inch (25.4 mm),
  um/µm/μm (0.001 mm), and deg/degree/degrees. Radians and other units are
  rejected until deliberately added. Canonical geometry units are mm and deg.
- Document logical paths use `/`, collapse redundant separators and `.`
  segments, and retain case. Absolute paths, drive prefixes, and `..` segments
  fail. No filesystem resolution or machine-specific paths enter the hash.
- `ir_hash` / `ir_record_hash` is SHA-256 of the entire normalized IR record,
  including history and metadata. It is an audit/content-identity hash, not a
  generator cache key. Equal geometry with different provenance can have
  different record hashes. Section 166 defines input-snapshot, dependency,
  validation, and manifest hashes. Raw source hashes remain byte-for-byte.

This is a PartSmith canonical profile, not a claim of RFC 8785 compatibility.
JSON Schema validation uses pinned `jsonschema` 4.26.0 with local references;
see the [validator documentation](https://python-jsonschema.readthedocs.io/en/stable/validate/).
Schema loading and IR validation require no network access.


## 121.4 Fixtures, packaging, and Phase 2 scope

Preserve IR 1.0/1.1 schemas, fixtures, hashes, and original gate reports. Add
IR 1.2 fixtures for every revised constraint, with expected diagnostic codes
and paths. Test installed-wheel schema loading and offline reference resolution
for all supported versions. Synthetic fixtures are not manufacturer evidence.

Implement `migrate_v1_1_to_v1_2(ir, supplied_evidence)` returning the existing
MigrationResult shape: new immutable IR or null, migration history, and sorted
issues. IR 1.0 migrates through the existing explicit 1.0→1.1 path first.
Never relabel old records or overwrite their original hashes.

Migration requires evidence-backed candidate targets, active override/resolution
selectors and revision bindings, typed override payloads, model accuracy class,
and region coordinate conventions/conversion where regions exist. No candidate
relevance, coordinate units, history selection, or CLASS_A claim may be guessed.
Empty decisions permit empty active selectors. Existing validation results need
explicit stage and applicability classification; absent proof is a migration
issue, not default PASS or NOT_APPLICABLE. The supplied mapping, rationale,
source/target hashes, and migration version are preserved in migration history.

The revised Phase 2 gate includes the counterexamples V094-01–V094-06 where
they concern IR/projection contracts, plus coordinate schema and transition
checks. Mathematical transform execution remains Phase 6; OCR remains Phase 10.
The implementation must publish exact schema/API diagnostics and fixture hashes
before claiming PASS. Existing gate reports retain their earlier scope.

## 121.5 Structured provenance records

Standards records require `id`, `organization`, `document`, `revision`,
`reference` (URL or controlled citation), `access_date`, and `evidence_ids`.
Optional `section`, `table_or_figure`, and `content_sha256` refine the citation.
`name` remains an optional display label. Unknown editions cannot support a
STANDARD value for generation; use unresolved candidate status until identified.
Relevant extracted engineering values are retained in evidence so deterministic
builds do not fetch live standards. Licensed source text need not be redistributed.

Evidence may contain a `translation` object requiring `original_text`,
`translated_text`, `source_language`, `target_language`, `provider`, `model`,
and `timestamp`. Manual translations use explicit `provider: "manual"` and
`model: "not_applicable"`. Original text must agree with retained source text.
Translation is supporting interpretation, not independent engineering authority.
Translation records inherit the evidence ID and source links. Active derivations
reference evidence/standard IDs explicitly; the frozen input snapshot includes
the referenced records, so revision changes affect dependency hashes.

## 121.6 Typed overrides and target bindings

IR 1.2 overrides retain section 88's ID, path, reason, user, timestamp,
evidence_reference, and approval_state fields. Add required `value_type`,
`base_revision_id`, and nullable `supersedes_override_id`. A versioned trusted
editable-path registry maps engineering JSON Pointers to the exact IR schema
type and provenance owner. It is part of the schema implementation, not
caller-supplied data. IDs, source records, history, validation outputs, version
fields, and active selectors cannot be edited through this override API.

The closed `value_type` union is STRING, NUMBER, BOOLEAN, VALUE_RECORD,
QUANTITY_RECORD, PIN_RECORD, PIN_ARRAY, PLACEMENT_RECORD, VEC3, or MIRROR_RECORD.
`previous_value` and `new_value` must match the registered target schema,
including enum, units, length, and bounds constraints. This is typed replacement,
not unrestricted JSON Patch. Null is legal only where the target schema permits
it. Add/remove pins by replacing PIN_ARRAY and revalidating all mappings.

Examples: `/pins/0/electrical_type` uses STRING with section 95's enum;
`/pins/0/number` uses STRING; a mechanical quantity uses QUANTITY_RECORD;
`/model_3d/placement/translation_mm/0` uses NUMBER; its parent uses VEC3;
the complete placement uses PLACEMENT_RECORD. The path registry must include
these cases and the section 177 controls. Requests outside the registry fail.

`/footprint/land_pattern_source` is not an editable override path. A typed
override may adjust geometry while retaining the selected source category. A
replacement land-pattern definition requires a new approved resolution and a
new dependency/provenance projection; a silent source-enum change is invalid.

`revision.active_override_ids` selects current approved overrides. Effective
paths, after approved target rebindings, must be disjoint (no duplicate or
ancestor/descendant overlap), resolve in the current revision, and match their
new values after canonical normalization.
The old value must match the base revision's target. Editable records with their
own status use USER_OVERRIDE and the matching override_id; raw leaves/vectors
bind through the active selector and do not require a fabricated value wrapper.
Other fields retain their own provenance. Selecting an override pulls its evidence
and reason into the active input closure, including for raw pin/placement leaves.

Replacing/removing an override creates a revision and a recorded review decision.
The prior record is retained unchanged; the new selector and supersession link
identify the active decision. Historical old values validate against their base
snapshots; historical new values validate against snapshots that selected that
override, not against the latest target. Approval never waives topology, type,
provenance, or geometry checks. Snapshot binding references follow section 166.

## 121.7 Candidate relevance and revision transitions

Every evidence record requires `acquisition_revision_id` and `candidate_targets`:
a unique array of engineering JSON Pointers in that revision, separate from
selected evidence_ids. The acquisition revision is retained in the immutable
revision store; this back-reference is an audit binding, not a dependency edge.
These pointers use the same schema/provenance-owner registry as overrides;
pin-leaf relevance resolves to that pin and quantity relevance to that quantity.
Container requirements include candidate targets within their subtrees. Selected
evidence must have a compatible candidate target. Empty targets mean unassigned
evidence, not a reviewed assertion of irrelevance, and cannot support generation.

An acquisition revision may be shared by multiple components when the immutable
source inventory and evidence content are identical. Sharing is established by
content hash and does not make the acquisition revision a component identity;
component-specific candidate targets and review decisions remain separate.

Before IR_VALIDATED, `revision.evidence_review` covers every acquired candidate.
It is null for an unreviewed candidate revision; a reviewed revision requires an
object with inventory_sha256, reviewed_evidence_ids, reviewer, timestamp, and
approval_state. The immutable acquisition inventory lists source hashes and
all evidence IDs acquired for the component; its canonical bytes must be retained
and match the hash. Reviewed IDs must cover that inventory exactly, including
retained historical candidates. Only APPROVED reviews qualify for generation.
Review confirms target relationships or records an approved exclusion with reason.
Store exclusions in `revision.evidence_exclusions` as records requiring
evidence_id, replacement_evidence_ids (possibly empty), reason, reviewer,
timestamp, and approval_state. Assigning an initially unassigned record creates
a new evidence ID with known targets, preserves the original record, and records
the new ID in the original's exclusion as its reviewed replacement. Inventories
retain both IDs. It does not edit candidate_targets on an existing record.
The replacement retains the source hash/region and the unresolved status unless
a separate interpretation/resolution justifies a change. Missing coverage
blocks the reviewed snapshot. Unrelated evidence with assigned targets outside
the required closure need not block that generator. An exclusion cannot suppress
an already assigned relevant target; that requires a resolution.

For each required provenance owner, the validator examines all assigned
candidates independently of selected evidence_ids. A candidate with unresolved
status must either block or appear in the active approved resolution's
superseded_evidence_ids with an explicit rationale. Selecting another value,
unlinking the candidate, or approving a raw-leaf override alone cannot dismiss it.
The active resolution's selected evidence must match the selected target evidence
or its bound override evidence. Selected evidence must itself be sufficient;
approval does not fabricate a value from unresolved evidence.

Add `validate_revision_transition(previous, current)` before persisting a new
reviewed revision. It checks parent identity, immutable record retention,
unchanged candidate relationships, override old values, and selector transitions.
New evidence gets new IDs; correcting an existing interpretation creates new
evidence plus an explicit superseding decision. Old records are never edited.
`revision.target_rebindings` records old_path, new_path, base_revision_id, reason,
reviewer, timestamp, and approval_state for topology reorder/replacement; require
an unambiguous mapping to the same terminal identity. Retired targets are explicit
approved rebindings with new_path null and cannot remain generation inputs.
Ambiguous rebindings block. Historical pointers are interpreted in their bound
revision and translated by this retained chain, never by the latest array index.

For edits offered by section 172's service and the Phase 12 UI, IR 1.2 terminal
numbers identify pins across a reorder; renumbering is a separate typed in-place
edit. Each service-created revision may reorder/add/retire pins while preserving
retained terminal numbers, or renumber retained pins in place, but must not
combine those operations. Combined user requests require separately reviewed
revisions. This is a service mutation policy, not a reinterpretation of retained
IR 1.2 schema/gate fixtures. Reject number collisions or ambiguous swaps; do not
invent temporary terminal identities. Reordering creates all required approved
rebindings; retirement also removes active references through explicit decisions.
View-only sorting must not reorder the persisted pins array. Phase 12 tests
verify that each supported operation preserves evidence/override target identity
and that unsupported combinations fail before revision commit.

The gate checks both immutable snapshots and transitions. Standalone structural
validation cannot prove an unseen acquisition history was complete; generation
requires a retained, validated revision chain (or an explicitly reviewed imported
root with acquisition inventory). That provenance is part of the review service,
not a boolean callers may set to bypass checks.

## 121.8 Resolution history and active selections

Keep immutable resolution records inline and preserve prior revision snapshots.
Retain id, target_path, superseded_evidence_ids, selected_evidence_ids, override_id,
decision, reason, reviewer, timestamp, and approval_state. Add `base_revision_id`
and nullable `supersedes_resolution_id`. `revision.active_resolution_ids` is a
required unique array selecting at most one APPROVED resolution per current
provenance owner after approved target rebindings. Nonselected old approvals
remain approvals in history; only selected decisions must match the latest
value/evidence/override binding.

A later decision references the earlier one, changes the active selector in a
new revision, and supplies a reason. Approving a persisted pending proposal
appends a new APPROVED decision with a new ID and a supersession link; it does
not mutate the pending record. Replacing a decision must retain dispositions
for previously unresolved candidates still relevant to that owner. Validate old
selections against the retained snapshots whose active selectors selected them;
base_revision_id binds their prior target context, not their resulting new value.
Validate current selections against current values. Dangling IDs, supersession cycles, incompatible target rebindings,
and silently deleted/reclassified historical records fail transition validation.
Pending/rejected proposals cannot be active. History links never become active
hash dependencies merely because their historical status was APPROVED.

Required IR 1.2 revision additions are active_override_ids,
active_resolution_ids, evidence_exclusions, target_rebindings, and evidence_review.
Arrays may be empty only when their corresponding decisions/relations are absent;
evidence_review is nullable only before review. Section 152 defines the
validation-result additions; section 124 defines source regions.

# 122. Component Identity Schema

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

``` yaml
identity:
  manufacturer:
    name:
    normalized_name:
  mpn:
  ordering_suffix:
  package_variant:
  temperature_grade:
  qualification:
  source_revision:
```

Normalization shall not destroy the original manufacturer or MPN
spelling.

Both raw and normalized values are retained.

# 123. Pin Schema

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

``` yaml
pin:
  number: "5"
  name: "EN"
  electrical_type: input
  function: enable
  active_low: false

  alternate_functions: []

  physical:
    topology_side: west
    topology_index: 3

  flags:
    exposed_pad: false
    no_connect: false

  evidence_ids:
    - E-001
```

Pin numbers shall be strings internally to support values such as:

``` text
A1
A2
NC
EP
1
2
```

The generator shall convert them only where the target KiCad
representation requires a particular format.

# 124. Evidence Schema

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

``` yaml
evidence:
  id: E-001
  type: PINOUT_DIAGRAM

  source:
    document_id:
    document_hash:
    page:
    region:
      x:
      y:
      width:
      height:

  extracted:
    text:
    value:
    unit:

  interpretation:
    normalized_value:
    status: DIRECT

  extractor:
    method:
    version:

  confidence:
    score:
    basis:
```

Confidence is metadata and cannot override evidence status.

## 124.1 Canonical source regions (document-page-1.0)

IR 1.2 evidence.source adds required `coordinate_convention` and
`page_geometry`, each null exactly when region is null. For a region, convention
is `document-page-1.0`; page is a one-based index in the hashed original PDF.
Coordinates are PDF points (1/72 inch after applying PDF UserUnit), in the
unrotated MediaBox frame, origin at its lower-left, +X right and +Y up. Width
and height are positive; preserve decimal values without pixel rounding.

page_geometry requires media_box [llx,lly,urx,ury] in raw PDF user coordinates,
user_unit, crop_box in the same raw coordinates, and rotation_deg (0/90/180/270).
The canonical origin subtracts MediaBox llx/lly before applying user_unit.
Canonical regions are axis-aligned bounds within that physical MediaBox; page
rotation and CropBox do not redefine their coordinate frame. Out-of-page regions
fail instead of being silently clipped. Retain the original document hash.

Rendered/OCR evidence additionally records `render_transform` with image_sha256,
width_px, height_px, dpi_x, dpi_y, renderer/version, and a 3x3 invertible affine
`pixel_to_page` matrix. Pixels use top-left origin, +X right, +Y down, with integer
coordinates at pixel edges. Transform all four box corners into canonical page
coordinates and store their enclosing bounds. The matrix explicitly incorporates
crop, scale, page rotation, and any deskew; DPI alone is insufficient. Non-affine
dewarping is unsupported until a versioned mapping is defined. Native text
extraction uses null render_transform and the PDF page transform directly.

The strict IR 1.2 schema includes these fields. Phase 2 covers their structural
and numeric validation; Phase 10 covers extraction conversion and inverse-overlay
fixtures for changed DPI, rotated/cropped pages, and shifted MediaBox origins.
Phase 12 must reproduce the recorded source region using these same transforms.

# 125. Evidence Graph

Evidence relationships shall be explicit.

``` text
Document
  │
  ├── Page
  │    └── Region
  │          └── Evidence
  │                └── IR Value
  │                      └── Artifact
  │                            └── Validation
```

Each edge shall be queryable.

This enables:

``` text
"Why is pad 7 here?"
```

to resolve to the exact source evidence and transformation chain.

# 126. PDL Schema

The PDL schema shall be separate from Component IR.

The field inventory below is abbreviated. Phase 3's actual schema must also
encode sections 31/93.1/148: the pinned release-profile identity/version/hash,
peripheral and exposed counts, terminal/group/shape identities, reference
features, allowed label-preserving symmetries, required measured observables,
applicability declarations, and tolerances. Missing declarations cannot be
supplied retrospectively by a validator after generation fails.

``` yaml
pdl:
  schema_version:
  id:
  revision:

  family:
  variant:

  mechanical:
    body:
      length_mm:
      width_mm:
      height_mm:
    lead:
      length_mm:
      width_mm:
      thickness_mm:

  topology:
    pin_count:
    pitch_mm:
    numbering:
    pin1:
    sides:
    stagger:

  land_pattern:
    source:
    pads:
    thermal_pad:

  model_3d:
    body_strategy:
    lead_strategy:
    marker_strategy:

  coordinate_system:
    origin:
    x_positive:
    y_positive:
    z_positive:

  validation:
    tolerances:
```

# 127. PDL Resolution Algorithm

Given a component:

``` text
1. Normalize package description.
2. Search exact manufacturer/package variant.
3. Search validated generic package variant.
4. Compare topology.
5. Compare mechanical dimensions.
6. Reject candidates that violate hard constraints.
7. Select a PDL candidate.
8. Record candidate and evidence.
9. Require review if more than one candidate remains plausible.
```

The resolver shall never select a package solely from an AI textual
similarity score.

# 128. Package Candidate Scoring

Candidate scoring may be used for ranking, but release decisions remain
deterministic.

Candidate dimensions:

``` text
package family match
pin count match
pitch match
body size match
topology match
pin-1 match
manufacturer-specific evidence
```

Hard failures:

``` text
wrong pin count
wrong topology
wrong pitch outside tolerance
wrong package family
```

Soft differences may produce `HUMAN_REVIEW`.

# 129. Extraction Pipeline

The extraction pipeline shall be:

``` text
SOURCE_RECEIVED
      ↓
FILE_IDENTIFICATION
      ↓
PAGE_RENDERING
      ↓
TEXT_EXTRACTION
      ↓
OCR_IF_REQUIRED
      ↓
TABLE_EXTRACTION
      ↓
IMAGE/DIAGRAM EXTRACTION
      ↓
PAGE CLASSIFICATION
      ↓
EVIDENCE CANDIDATES
```

The pipeline shall preserve page numbers and source regions.

# 130. PDF Adapter Interface

``` python
class DocumentAdapter(Protocol):
    def inspect(self, source: SourceDocument) -> DocumentMetadata: ...
    def pages(self, source: SourceDocument) -> Iterable[Page]: ...
    def extract_text(self, page: Page) -> ExtractedText: ...
    def extract_images(self, page: Page) -> list[ImageRegion]: ...
    def extract_tables(self, page: Page) -> list[TableRegion]: ...
```

Adapters must not write Component IR directly.

# 131. OCR Adapter Interface

``` python
class OCRAdapter(Protocol):
    def recognize(
        self,
        image: ImageRegion,
        language_hints: list[str]
    ) -> OCRResult: ...
```

The result shall contain bounding boxes and confidence metadata.

# 132. Page Classification

Pages shall be classified into:

``` text
TITLE
FEATURES
ELECTRICAL_CHARACTERISTICS
PINOUT
PIN_DESCRIPTION
BLOCK_DIAGRAM
APPLICATION
PACKAGE_DRAWING
LAND_PATTERN
ORDERING
REVISION
UNKNOWN
```

Multiple classifications are allowed.

# 133. AI Provider Interface

``` python
class AIProvider(Protocol):
    def analyze(
        self,
        request: AIRequest
    ) -> AIResult: ...
```

The adapter shall normalize provider-specific output into B.F.T. schema.

Required metadata:

``` text
provider
model
request ID
timestamp
input hash
output hash
schema version
```

# 134. AI Task Decomposition

AI requests shall be narrow and typed.

Examples:

``` text
extract_pin_table
interpret_pin_description
identify_package
interpret_package_drawing
locate_land_pattern
identify_symbol
classify_conflict
translate_technical_text
explain_ambiguity
```

A single unrestricted "build the component" prompt shall not be the
production architecture.

# 135. Prompt Injection Defense

All document content is untrusted data.

Before AI submission:

``` text
document content
    ↓
content extraction
    ↓
untrusted-data wrapper
    ↓
typed AI task
```

Instructions found inside documents must never be treated as B.F.T.
instructions.

# 136. IR Construction

The IR builder consumes:

``` text
Evidence graph
+
AI candidates
+
PDL candidates
+
approved rules
+
approved overrides
```

It produces:

``` text
Component IR
+
unresolved issues
```

It must not generate KiCad files.

# 137. IR Validation

Validation before generation is input-only: schema, required active values,
reference/provenance resolution, unique physical pin IDs, supported PDL,
package topology, dimension consistency, units, and input transforms. Section
121.2 provides preliminary checks; PDL/generator contexts supply applicability.
These checks establish IR_VALIDATED. Unsupported or incomplete inputs enter
the appropriate failure/waiting state; no production generator accepts them.

After generation, separate artifact, electrical mapping, cross-validation,
KiCad compatibility, and reproducibility checks run. Passing these plus explicit
required review establishes APPROVED. Those output checks never gate the first
creation of the artifacts they must inspect. Physical IR pins have unique IDs;
intentional repeated representations across symbol units require explicit
mapping to that one physical pin, not duplicated physical IR pin records.

# 138. Symbol Generator API

``` python
class SymbolGenerator(Protocol):
    def generate(
        self,
        ir: ComponentIR,
        context: GeneratorContext
    ) -> GeneratedArtifact: ...
```

The output shall contain:

``` text
.kicad_sym
artifact metadata
source hash
generator version
```

# 139. Symbol Generation Rules

The symbol generator shall:

1.  Generate one or more units when required.
2.  Preserve exact pin numbers.
3.  Preserve pin names.
4.  Apply approved electrical types.
5.  Assign standard B.F.T. graphical conventions.
6.  Assign footprint reference metadata.
7.  Avoid adding unsupported electrical semantics.

# 140. Footprint Generator API

``` python
class FootprintGenerator(Protocol):
    def generate(
        self,
        ir: ComponentIR,
        pdl: PDL,
        context: GeneratorContext
    ) -> GeneratedArtifact: ...
```

Input must include approved land-pattern information.

The footprint generator shall not read the generated 3D artifact.

# 141. Footprint Generation Pipeline

``` text
PDL
 ↓
Land Pattern Resolver
 ↓
Pad Geometry
 ↓
Pad Numbering
 ↓
Pin-1 Marker
 ↓
Courtyard
 ↓
Fabrication Graphics
 ↓
Silkscreen
 ↓
Footprint artifact
 ↓
.kicad_mod (no authoritative 3D geometry dependency)
```

The final 3D reference path is attached after preliminary geometry validation,
then final-byte association/compatibility checks run under section 167. A preliminary footprint may
contain no 3D reference, or only a non-authoritative placeholder token.
In all cases, 3D geometry must never drive pad generation.

For Phases 4–5, the preliminary footprint contains no 3D model field. The
finalizer introduced by Phase 8 owns the optional model field and its portable
logical path. A placeholder is therefore not required by the bootstrap
serializer; if a later adapter uses one, it must be replaced before final-byte
hashing and may never be treated as a validated model reference.

# 142. Land Pattern Algorithm

For a package with a manufacturer land pattern:

``` text
Use manufacturer coordinates
→ normalize units
→ validate pad count
→ validate numbering
→ validate pin-1 and package/topology constraints
→ generate footprint
```

For an IPC-derived pattern:

``` text
Applicable IPC methodology + package/terminal dimensions
→ calculate candidate pad geometry
→ record the exact standard/revision and inputs
→ validate against package/topology constraints
→ require review when the result is not uniquely determined
→ generate
```

For a PDL-derived family rule:

``` text
PDL rules
→ calculate pad geometry
→ apply package-family rules
→ validate against package constraints
→ generate
```

The algorithm shall retain the calculation provenance. The resolver
shall not silently skip a higher-precedence available source.

# 143. Courtyard Generation

Courtyard geometry shall be derived from:

``` text
package body
+
lead/pad extent
+
required clearance rule
```

It shall not be copied blindly from silkscreen geometry.

The source of each clearance rule must be recorded.

# 144. 3D Generator API

``` python
class Model3DGenerator(Protocol):
    def generate(
        self,
        ir: ComponentIR,
        pdl: PDL,
        context: GeneratorContext
    ) -> GeneratedArtifact: ...
```

The generator shall produce:

``` text
STEP output
3D metadata
```

The 3D generator shall never inspect the generated footprint to decide
dimensions.

# 145. 3D Generation Pipeline

``` text
Mechanical Evidence
        +
PDL
        +
Component IR
        ↓
Geometry Parameters
        ↓
Body Generator
        ↓
Lead Generator
        ↓
Marking Generator
        ↓
Pin-1 Marker
        ↓
Assembly
        ↓
STEP Export
        ↓
Independent 3D Validation
```

# 146. CadQuery Backend

CadQuery/OCP/OCCT is the selected implementation runtime, not the
authoritative geometry definition.

The authoritative data is:

``` text
Component IR + PDL + evidence
```

The generated STEP artifact shall be reproducible from those inputs and the
pinned CadQuery/OCP/OCCT/Python compatibility tuple.

# 147. STEP Validation

STEP validation shall check:

-   file existence
-   parseability
-   unit scale
-   bounding box
-   body dimensions
-   height
-   orientation
-   expected component solids
-   no invalid coordinates

Where possible, the validator shall compare measured geometry to
independent IR dimensions.

# 148. Footprint ↔ 3D Cross-Validation

Cross-validation compares independent artifacts under section 92. Each PDL
revision declares `reference_features` with stable terminal IDs, nominal anchor
coordinates, expected representation (MEASURED or DECLARED_ONLY), physical
feature applicability, tolerances, and required observables. It also declares
allowed geometry symmetries as explicit transforms preserving terminal labels
and electrical meaning. Applicability is input data, not chosen after a failure.

Check physical pin count/positions, pin-1, body/reference-center, height,
orientation, mirror state, and exposed pad when the PDL requires those features.
Use measured geometry for MEASURED features; a missing required measured feature
fails. Intentionally absent features use DECLARED_ONLY anchors with a report
clearly stating that geometry was not measured. Such anchors cannot prove a
dimensionally required physical feature. The release accuracy class determines
which checks require actual geometry; MVP engineering dimensions must be measured.

Pad centers and lead centers need not coincide: land-pattern extensions are
intentional. Validate the expected PDL contact/overlap and offset relationship,
not unconditional equality. Section 93.1 defines terminal groups and shapes,
including explicit serializer support for compound pads.

Record whether each check is measured PASS/FAIL or justified NOT_APPLICABLE.
NOT_APPLICABLE is a separate applicability field, not a new PASS status. A gate
counts it only when its pinned fixture/PDL declared that non-applicability;
it is not a skipped or manually waived test. Section 152 defines null status,
declaration bindings, and measurement mode for this case. No validator repairs geometry.

# 149. Fault Injection for Cross-Validation

Fixtures inject shifts, 90/180-degree rotation, X/Y mirrors, 2x/0.5x scale,
wrong height, and wrong pin-1 mapping. Every injection that changes a required
observable or declared placement/terminal mapping must fail its intended rule.

For geometry symmetric under an allowed PDL transform, geometry alone cannot
prove that a rotation/mirror happened. Validate explicit placement and terminal
identities separately. Geometry-equivalent cases form positive equivalence
tests and never count as detected faults. The fault corpus must include
asymmetric reference fixtures that make each required fault observable; a
symmetric 0402 alone cannot establish rotation/mirror detection coverage.

# 150. Coordinate Transform Library

Two immutable types have different purposes:

```python
@dataclass(frozen=True)
class Placement:
    translation_mm: Vec3
    rotation_deg: Vec3
    scale: Vec3
    mirror: MirrorState
    source_frame: str
    destination_frame: str

@dataclass(frozen=True)
class AffineTransform:
    matrix: Matrix4x4
    source_frame: str
    destination_frame: str

def to_affine(placement: Placement) -> AffineTransform: ...
def compose(ab: AffineTransform, bc: AffineTransform) -> AffineTransform: ...
def invert(transform: AffineTransform) -> AffineTransform: ...
```

The placement record retains convention 1.1 from section 92. Affine matrices
use column vectors, mm translations, finite entries, last row [0,0,0,1], and
an invertible linear part. Frame IDs must match at composition boundaries;
composition returns bc.matrix * ab.matrix and inversion swaps frame IDs.
Reject singular or numerically unstable inversion outside pinned tolerances.
The internal affine format has convention `affine-1.0`; it does not replace
the persisted simple IR placement or require shear support from KiCad.

`apply_point`, `apply_vector`, `apply_bbox`, and `equivalent_within_tolerance`
operate on affine transforms. Bbox transformation uses all eight corners and
returns their destination-axis-aligned bounds. Vectors use w=0; points use w=1.
Numerical algorithms, precision, and tolerances are pinned runtime inputs.
Adapters may emit a simple placement only if its reconstructed matrix agrees
within the pinned serialization tolerance; otherwise fail, never drop shear.

Phase 6 tests include nonuniform S=diag(2,1,1) composed with a planar rotation
cos=3/5, sin=4/5, exact expected matrices, nonrepresentable simple-placement
rejection, inverse round trips, mirrors, and frame mismatch. No decomposition
to Euler angles is required for internal composition.

# 151. Tolerance Engine

Examples in this section are abbreviated explanatory views, not schema-valid
IR instances. Section 121 defines required fields and canonical tokens.

Tolerances shall be package-specific.

``` yaml
validation:
  xy_pin_pad_tolerance_mm: 0.01
  center_tolerance_mm: 0.01
  rotation_tolerance_deg: 0.1
  height_tolerance_mm: 0.02
```

Tolerance values are configuration, not hard-coded constants.

# 152. Validation Result Contract

IR 1.2 validation.results and build output reports use the same strict result
definition. In addition to id, category, rule_id, severity, message, evidence_ids,
artifact_ids, measured, expected, and tolerance, require:

| Field | Contract |
| --- | --- |
| stage | INPUT, ARTIFACT, FINAL_ARTIFACT, POST_MANIFEST, or REPRODUCIBILITY |
| applicability | APPLICABLE or NOT_APPLICABLE |
| applicability_reason | Nonempty justification for NOT_APPLICABLE; null otherwise |
| applicability_basis | For NOT_APPLICABLE: kind (PDL or FIXTURE), id, revision, sha256, and feature_id of the pinned declaration; null otherwise |
| status | PASS, FAIL, WARN, HUMAN_REVIEW, or NOT_GENERATABLE when APPLICABLE; null exactly when NOT_APPLICABLE |
| measurement_mode | MEASURED, DECLARED_ONLY, or NONE |

NOT_APPLICABLE is not PASS: measured/expected/tolerance are null and
measurement_mode is NONE. A gate counts it as a satisfied declared exclusion
only when the trusted fixture/PDL explicitly declares that feature absent.
Undeclared exclusions or incompatible basis hashes produce an applicable FAIL.
A missing required feature cannot become NOT_APPLICABLE after generation.

An applicable dimensional PASS requires MEASURED for CLASS_A observables.
DECLARED_ONLY can validate a declaration/mapping but cannot prove measured
geometry. Non-geometric checks use NONE. Preserve evidence and subject bindings
for all cases; section 166 includes applicability and measurement mode in hashes.
The result definition is packaged with the IR 1.2 schema and reused by output
report serialization. Standalone reports declare result schema version 1.2.
Output reports remain outside the frozen source IR; copying them into an audit
revision follows section 166 and cannot change a build's source snapshot.

Gate aggregation uses a pinned required-rule inventory for each stage and
subject. Missing, duplicate, or stale required results fail aggregation; an
empty result list is not success. Count declared NOT_APPLICABLE separately from
PASS/FAIL/WARN and preserve its null status in JSON and UI. Each exclusion must
match its trusted declaration; CLASS_A measurements and blocking statuses
remain mandatory. Phase 7 tests result semantics and Phase 8 tests aggregation,
including missing results and a fabricated exclusion.

# 153. Blocking Rules

FAIL, HUMAN_REVIEW, and NOT_GENERATABLE validation results block production
approval/export. Ordinary review cannot waive or rename them. Resolve the cause
and rerun affected validators; the old result remains in immutable history.

WARN may be accepted only by an explicit versioned warning policy identifying
the rule, scope, rationale, and required reviewer decision. It remains WARN in
reports; it is never silently converted to PASS. `--fail-on-warning` is stricter
than normal warning policy. Phase-gate waivers require the specification-level
process at the start of this document and are never a recorded gate PASS.

# 154. Validation Engine API

``` python
class Validator(Protocol):
    def validate(
        self,
        build: BuildContext
    ) -> list[ValidationResult]: ...
```

Validators shall be independently executable.

# 155. Validator Categories

Minimum validators:

``` text
SchemaValidator
EvidenceValidator
TopologyValidator
ElectricalValidator
SymbolValidator
FootprintValidator
Model3DValidator
MappingValidator
CrossArtifactValidator
KiCadCompatibilityValidator
ManifestValidator
ReproducibilityValidator
```

ManifestValidator runs POST_MANIFEST; ReproducibilityValidator runs in a separate
REPRODUCIBILITY comparison stage. Neither result is an input to the manifest it
verifies. Section 167 defines the acyclic ordering and release checks.

# 156. KiCad Adapter

``` python
class KiCadAdapter(Protocol):
    def version(self) -> KiCadVersion: ...
    def validate_symbol(self, path: Path) -> KiCadResult: ...
    def validate_footprint(self, path: Path) -> KiCadResult: ...
    def validate_project(self, path: Path) -> KiCadResult: ...
    def launch_headless(self, project: Path) -> KiCadProcess: ...
```

The adapter must be version-specific.
Phase 13 extends this boundary with a closed capability record and explicit
PCB IPC session operations. The protocol above is illustrative; its existence
does not prove that a particular KiCad build implements any listed operation.
Core integration services own plans, approval bindings and publication policy;
adapter code owns native serialization/comparison, target discovery and tested
filesystem/editor mechanisms. Neither the launch plugin nor API clients may
bypass those services to write approved installation content.

# 157. KiCad Integration Strategy

The implementation shall prefer supported KiCad interfaces over private
file manipulation when the required operation is available.

For the pinned KiCad 10 build, the implementation shall verify supported IPC
operations and Python bindings. Do not assume an `api-server` CLI command
exists merely because development-version documentation lists it. Record
capabilities from the installed build; use supported headless CLI operations
for Phase 8 and a live IPC test session where required in Phase 13.
[Reference register: section 247](#247-external-reference-register).

For native library artifact generation, B.F.T. may generate validated
native files directly where this is deterministic and stable, while
KiCad adapters handle version-specific validation and integration.

# 158. KiCad CLI Integration

The test harness shall discover:

``` text
kicad
kicad-cli
```

and record:

``` text
executable path
version
build information
platform
```

The build shall fail early with a clear compatibility error if the
requested KiCad target is unavailable.

Phase 8 requires native CLI discovery before a persisted build attempt starts.
The discovered major version shall equal the IR target major version. The
validation result and engineering manifest shall record the native CLI version
and operations. Executable paths and platform details are audit metadata and
shall not affect deterministic engineering hashes.

# 159. Build State Machine

Persisted progress states:

```text
SOURCE_RECEIVED
SOURCE_ANALYZED
EVIDENCE_COLLECTED
IR_BUILT
PACKAGE_IDENTIFIED
IR_VALIDATED
SYMBOL_GENERATED
FOOTPRINT_GENERATED
3D_GENERATED
ARTIFACT_VALIDATION
CROSS_VALIDATION
HUMAN_REVIEW_REQUIRED
APPROVED
EXPORTED
REJECTED
```

Failure states: EXTRACTION_FAILED, EVIDENCE_CONFLICT, IR_INVALID,
PACKAGE_UNSUPPORTED, NOT_GENERATABLE, ARTIFACT_VALIDATION_FAILED,
CROSS_VALIDATION_FAILED. HUMAN_REVIEW_REQUIRED is a waiting state, not failure.
HUMAN_REVIEW belongs only to the validation-result enum.

| Transition | Required condition |
| --- | --- |
| SOURCE_RECEIVED → SOURCE_ANALYZED → EVIDENCE_COLLECTED → IR_BUILT | Source processing succeeds; deterministic fixtures may enter IR_BUILT with recorded supplied inputs |
| IR_BUILT → PACKAGE_IDENTIFIED → IR_VALIDATED | PDL resolved; all applicable input checks pass |
| IR_BUILT or PACKAGE_IDENTIFIED → HUMAN_REVIEW_REQUIRED | Input review or resolution is missing; record review stage INPUT and the bound revision/inventory |
| HUMAN_REVIEW_REQUIRED (INPUT) → IR_BUILT | Section 172 atomically commits a reviewed child revision; input/PDL validation must rerun before generation |
| IR_VALIDATED → generation progress states → ARTIFACT_VALIDATION | Each artifact consumes its frozen declared inputs; all required artifacts complete |
| ARTIFACT_VALIDATION → CROSS_VALIDATION | Independent artifact/mapping checks pass |
| CROSS_VALIDATION → HUMAN_REVIEW_REQUIRED | Final-byte cross-validation and KiCad compatibility pass; manifest frozen and post-manifest verification passes under section 167; approval is pending |
| HUMAN_REVIEW_REQUIRED (RELEASE) → APPROVED | Explicit approval bound to exact snapshot/manifest/artifact hashes and successful required checks; no blockers |
| HUMAN_REVIEW_REQUIRED → REJECTED | Recorded rejection and reason |
| APPROVED → EXPORTED | Atomic export succeeds without changing approved engineering content |

Preliminary checks, finalization, and final-byte rechecks are distinct tracked
substeps within ARTIFACT_VALIDATION/CROSS_VALIDATION, in section 167 order.
Artifact completion is also tracked per node; progress states do not permit
skipping required nodes or force independent generators to read one another.
Recoverable failures may enter HUMAN_REVIEW_REQUIRED for resolution, but cannot
be approved while blocked. Changed inputs create a new immutable revision/build
attempt at IR_BUILT, invalidate affected descendants, and rerun checks. Retry
without changed inputs is permitted only for transient operational failures.
Previously approved releases and rejected attempts remain immutable.
Each review request records INPUT or RELEASE stage; section 167's post-manifest
waiting state uses RELEASE. Resolving an INPUT request never transitions directly
to APPROVED. A reviewed supplied fixture may bypass an interactive input-review
session only with its retained valid review/inventory bindings.

# 160. Build Orchestrator

``` python
class BuildOrchestrator:
    def run(self, request: BuildRequest) -> BuildResult: ...
    def resume(self, build_id: UUID) -> BuildResult: ...
    def invalidate(self, build_id: UUID, reason: str) -> None: ...
```

The orchestrator is the only module allowed to advance build/release
state. Validation results may use `HUMAN_REVIEW`; the persisted build
state uses `HUMAN_REVIEW_REQUIRED`.

# 161. Dependency Graph

Artifact dependencies shall be represented explicitly.

``` text
Source
 ↓
Evidence
 ↓
IR
 ├── Symbol
 ├── Footprint
 └── 3D
        ↓
Cross-validation
        ↓
Approval
```

A dependency graph shall be stored for each build.

The graph distinguishes regeneration, revalidation, and reuse. At minimum:

| Changed input | Regenerate | Revalidate | Reuse |
| --- | --- | --- | --- |
| Symbol-only graphics | Symbol | Mapping/manifest as applicable | Footprint, 3D |
| Pin mapping or terminal identity | Symbol, footprint | 3D when physical pin geometry changes; cross-validation | Unaffected evidence |
| Body height | 3D | Cross-validation; footprint only when courtyard/clearance rules consume it | Symbol |
| Footprint bytes or association path | None for independent geometry | Association, compatibility, cross-validation, manifest | Independent symbol/3D geometry |
| Audit-only metadata | None | None | Unaffected engineering artifacts |

Each graph edge records the dependency hash that caused the action. A retained
artifact may be reused only when its declared dependency and artifact hashes
still match the frozen build snapshot.

# 162. Incremental Regeneration

If only symbol graphics change:

``` text
symbol → regenerate
footprint → retain
3D → retain
```

If pin mapping changes:

``` text
symbol → regenerate
footprint → regenerate
3D → regenerate if physical pin geometry changes
cross-validation → rerun
```

If body height changes:

``` text
3D → regenerate
cross-validation → rerun
footprint → regenerate only if dependent courtyard/clearance rules change
```

# 163. Persistence Model

MVP uses SQLite.

Tables:

``` text
projects
components
documents
evidence
component_ir
pdl_entries
builds
artifacts
validation_results
overrides
reviews
providers
build_dependencies
```

All records shall include creation/update timestamps.

Immutable snapshots/events keep their original timestamps (an updated_at field,
where present, equals created_at); edits append records. Mutable current-head
indexes and orchestration progress are separate from approved snapshot bytes.

Phase 8 adds forward migrations after 001 for immutable IR revisions, canonical
acquisition inventories, review proposals/decisions, snapshot/dependency records,
bundle object indexes, and approval bindings. Physical table grouping may vary,
but the store must provide get_revision(id) and get_inventory(sha256) with the
exact bytes and identity checked under section 121.2. Preserve historical
schemas, migration checksums, and existing database contents.

Revision IDs are unique within their declared identity namespace; the same ID
with different bytes is a conflict. Store a canonical hash with every snapshot
and inventory. Parent/base/acquisition references and reviewed inventories must
resolve before a reviewed revision becomes current. Snapshots reachable from
retained releases, decisions, or replay bundles cannot be pruned or cascade-deleted.

Commit a reviewed revision, appended approved decisions, selected bindings,
inventory, audit event, and current-head compare-and-swap in one SQLite
transaction. Check the caller's expected head hash, retained base values, and
transition validation in that transaction. A stale head or validation failure
rolls back all changes. The review service owns this transaction; the
orchestrator alone subsequently advances build state. Phase 8 tests reopen,
concurrent stale-head rejection, immutability, and rollback without partial approval.

# 164. Build Record

``` yaml
build:
  id:
  component_id:
  state:
  started_at:
  completed_at:
  bft_version:
  schema_version:
  pdl_revision:
  ai_provider:
  ai_model:
  source_hash:
  ir_hash:
  build_inputs_hash:
```

# 165. Artifact Record

``` yaml
artifact:
  id:
  build_id:
  type:
  path:
  sha256:
  generator:
  generator_version:
  status:
```

# 166. Reproducible Build Algorithm

Each generation attempt freezes an input snapshot after input validation.
Validation results produced by that attempt are written to separate output
records, never appended to or substituted into its frozen input snapshot.
An IR editor may create a new full record containing those reports, but that
new audit record is not retroactively the source input of existing artifacts.

The following hashes have distinct meanings:

| Hash | Exact scope |
| --- | --- |
| ir_record_hash (`ir_hash` API) | Entire normalized versioned IR, including history and metadata |
| input_snapshot_hash | Canonical input snapshot defined below |
| dependency_hash per generator | Declared projection of consumed snapshot paths and recursively referenced active provenance plus only output-affecting generator/backend/configuration inputs |
| artifact_hash | SHA-256 of exact released artifact bytes; backend-equivalence results are recorded separately |
| validation_semantics_hash | Final retained ARTIFACT/FINAL_ARTIFACT results only: sorted rule/category/stage/applicability/basis/reason/status/severity/measurement_mode, engineering measurements, expected values/tolerances, stable subject identity and exact artifact hashes, and validator versions; excludes preliminary/superseded, POST_MANIFEST, and REPRODUCIBILITY results, IDs, and execution times |
| engineering_manifest_hash | Deterministic content manifest with snapshot, dependencies, artifacts, semantic validation, and target/runtime versions |
| audit_envelope_hash | Run IDs, reviewer identities/decisions, timestamps, full IR record hash, and references to deterministic content hashes |

The input snapshot includes schema/profile versions, raw/normalized component
identity (excluding local component_id), required engineering IR paths, active
evidence/standard/translation records, selected override new values and reasons,
resolution selections/reasons, PDL content/revision, all generator/validator and
CadQuery/OCP/OCCT/Python versions, exporter settings, and effective non-secret
engineering configuration, including the section 31 release profile. True
dependency references are replaced by recursively projected content hashes under
the edge rules below; acquisition/translation execution
timestamps, run/result IDs, reviewer identities/timestamps, display revision
IDs/descriptions, historical previous
values, and output validation results belong only to the audit envelope. Source
document revisions, source-file hashes, original/translated text, and engineering
source units remain content-significant. Cyclic dependency projections fail.

### Projection versions and configuration scope

Canonical JSON profile 1.0 is unchanged; the content projection is separately
versioned. Profile 1.1 remains readable with its original implementation and
golden hashes. Profile 1.2 retains the edge rules below but adds the scoped
configuration contract in this section. New Phase 4–6 generator projections
and Phase 8–9 snapshots use 1.2 and declare that version in canonical bytes.
Never relabel an existing 1.1 hash as 1.2 or replace its frozen golden evidence.

The complete build snapshot contains all actual runtime/configuration inputs
listed above. Each node's dependency projection contains only its versioned
trusted IR/provenance paths and configuration paths. A declaration has node
kind, declaration ID/version, required IR paths, required configuration paths,
and configuration schema/version. A declaration field participates in a node
dependency only when it is also a consumed input that can affect the node's
bytes or declared provenance. Declarations are shipped with the
adapter/generator/rules, not supplied or narrowed by an IR author, CLI flag,
or arbitrary caller.

| Node | Required configuration scope |
| --- | --- |
| Symbol | Python/serializer/generator versions, target symbol format, symbol conventions, naming and consumed assignment inputs |
| Footprint geometry | Only output-affecting target format, consumed PDL/land-pattern/graphics/clearance rules, and declared provenance |
| Canonical STEP | Complete tested CAD/Python tuple and archive hashes, geometry adapter/generator, consumed PDL mechanics, numeric and STEP exporter settings |
| Association/finalization | Finalizer and target format versions, input artifact hashes, logical reference paths/nicknames and placement conversion/settings |
| Validation | Validator/rule/runtime versions, applicable PDL/profile declarations, tolerances, exact subject input/artifact hashes |
| Manifest/release | Complete snapshot, retained validation semantics, finalized artifact hashes, release profile and manifest implementation version |

Each node includes consumed release-policy fields and their declaration versions;
the full release-profile content/hash is always in the complete snapshot. A
consumer of an entire configuration object declares the entire object as an
input. Do not drop dependencies merely because one fixture happens to produce
unchanged output. PDL content is projected by declared consumed fields while
retaining its identity/revision and applicable rule versions.

Symbol and footprint geometry projections must not require unused CAD versions,
STEP exporter settings, output-validator versions, Python versions, serializer
versions, generator versions, or naming versions. Early phase fixtures
declare only available actual inputs; they are not complete release snapshots
and cannot receive release approval. Missing required node inputs fail rather
than acquiring invented runtime placeholders. Phase 8 requires the full tuple.
Validator-only changes rerun affected checks and invalidate manifests/approval;
they regenerate engineering files only if a generator actually consumes changed
rules. CAD-only changes invalidate STEP and dependent checks/association as
needed, while preserving unrelated symbol/footprint geometry dependencies.

Phases 4–6 test each new declaration with consumed-input changes and unrelated
configuration changes. Phase 9 exercises the complete dependency graph,
including validator-only, CAD-only, placement-only, and audit-only changes.
Profile 1.1 remains the scope of the existing Phase 2 projection evidence;
profile 1.2 evidence is additional and records its own hashes.

For the Phase 4–5 bootstrap generators, the profile 1.2 dependency hash is the
SHA-256 of canonical JSON containing `snapshot_profile`, `node_kind`, and
`inputs`. The projection may expose declaration and configuration metadata for
auditability, but unused configuration metadata is excluded from the geometry
dependency hash. The separate association dependency includes the declared
symbol/pin and 3D-association inputs. This bootstrap rule is normative until a
later profile 1.2 schema expands it without changing the frozen profile 1.1
API or golden evidence.

### Projection edge rules (retained from profile 1.1)

- Dependency edges: selected evidence, standards, derivation/translation inputs,
  and active approved decision content. Resolve by content hash, never random IDs.
- Binding edges: override_id and active decision selectors connect a target to
  a selected decision. Project the binding once as that decision's content hash.
  While projecting an override's new_value, omit a self-binding override_id
  (only when it equals that override's own ID); retain target path, value type,
  typed new content, reason, and evidence content. Do not recursively hash the
  target object through its path. A mismatched binding is invalid, not omitted.
- History edges: previous_value, supersedes_override_id, supersedes_resolution_id,
  base_revision_id, acquisition_revision_id, prior evidence dispositions, and superseded_evidence_ids are
  audit links, not recursive dependency edges. Keep them in the full IR/audit
  hash. Active resolution projection contains current target identity, selected
  evidence hashes, override content hash if any, decision, and reason. Active
  exclusion/rebinding content needed to establish the current selection is
  retained without reviewer/time/parent-snapshot recursion.
- Record id, revision display labels, and reviewer/time fields are excluded
  from these content nodes. Source-document hash/revision and substantive
  engineering interpretation remain included. Candidate relationships used by
  the active selection remain significant; inactive historical record bodies
  do not become active solely through a supersession link.

Golden projection tests must prove that a valid self-bound quantity override
hashes without a cycle; changing its new value/reason/evidence changes the
affected dependency; changing only previous_value/reviewer/time affects the
audit hash; and a real derivation dependency cycle fails. A raw pin/placement
override must contribute its active decision content even without override_id
on the leaf. Approved historical decisions must not be compared to current values.
These edge cases remain required for profile 1.2 as it is implemented; the
existing Phase 2 cases retain their profile 1.1 baselines.

Each generator publishes a versioned required-path projection; omitting a
geometry-affecting parameter or active provenance dependency fails validation.
Placement-only edits invalidate association, cross-validation, and export, not
canonical STEP geometry. Audit-only changes alter the record/envelope hash but
not an unaffected generator's dependency hash. Sections 103/162 use these
dependency hashes rather than the whole-record hash for selective reuse.

Canonical profile 1.0 serializes each projection. `build_inputs_hash` is an
alias for `input_snapshot_hash`; SHA-256 hashes canonical bytes. A build record
stores both input_snapshot_hash and ir_record_hash. Release reproducibility
requires exact artifact bytes and dependent hashes. Backend equivalence may be
reported diagnostically with algorithm/version/tolerances and both byte hashes,
but cannot satisfy a reproducibility gate or replace any artifact hash. Runtime
or input changes define different build inputs, even when geometry is equivalent.
Replay uses frozen reviewed Evidence/IR and recorded provider responses; new live
AI interpretation is a new candidate acquisition, not a deterministic rebuild.

# 167. Manifest Generation

The build graph shall use this order:

1. Validate inputs and freeze the snapshot/dependency hashes.
2. Generate artifacts independently. Run preliminary geometry/mapping checks
   using declared transforms without requiring a viewer or final KiCad reference.
3. On preliminary success, attach the final model path/placement and finalize
   all released bytes. Paths are portable logical paths; export relocation must
   preserve their resolution without rewriting the approved files.
4. Run final artifact/mapping/cross-validation and native target-KiCad CLI
   compatibility checks against those bytes. Native checks shall parse,
   force-round-trip, and render the final symbol and footprint libraries.
   Internal format checks run first but cannot produce compatibility PASS.
   Also check referenced STEP existence/hash and association transform. Retain
   ARTIFACT/FINAL_ARTIFACT results bound to exact artifact hashes. Unchanged
   independent geometry checks may be reused only with exact declared
   input/artifact hash equality; changed footprint bytes require new
   footprint/association/compatibility checks. Preliminary results for different
   bytes do not enter validation_semantics_hash.
5. Freeze final artifact hashes and validation_semantics_hash. Construct/hash
   the engineering manifest from those hashes, input/dependency hashes, release
   profile, and target/runtime versions. No self-hash field is inside it.
6. Run ManifestValidator on the completed manifest and its content references.
   Store POST_MANIFEST results in the separate run/audit envelope, bound to the
   manifest hash. ReproducibilityValidator compares two already frozen builds
   at Phase 9 and writes a separate REPRODUCIBILITY report referencing both
   manifest/artifact hashes. Neither report changes either engineering manifest
   or validation_semantics_hash. Phase 8 does not depend on a future Phase 9 test.
7. Explicit human approval binds the frozen manifest/artifact hashes and the
   required successful post-manifest checks. The audit envelope has its own hash;
   approval does not include that eventual envelope hash in its own input.
   Headless operation uses the same service with an authenticated recorded
   reviewer/decision; CI replay is valid only for identical approved content.
8. Release/export rechecks bytes, references, approval bindings, and required
   gate evidence. A changed reference, path, placement, or file invalidates
   dependent checks, manifest, and approval and creates a new attempt.

This sequence governs the component release bundle. Project installation may
derive new aggregate files only through section 174.1's separate validation and
authorization contract; it never modifies the approved source bundle or treats
new aggregate bytes as if the component approval covered them.

The viewer is an optional presentation surface for the Phase 8 service and a
required Phase 12 UI deliverable. It cannot repair geometry or substitute visual
inspection for final-byte checks. All blockers apply equally to CLI and GUI.
The manifest never depends on a report that requires that same manifest's hash.

# 168. CLI

MVP commands:

``` bash
partsmith component inspect <source>
partsmith component extract <source>
partsmith component build <source>
partsmith component validate <build-id>
partsmith component review <build-id>
partsmith component review-inputs <component-id> --revision <revision-id>
partsmith component export <build-id>
partsmith component diff <build-a> <build-b>

partsmith pdl list
partsmith pdl inspect <pdl-id>
partsmith pdl validate <pdl-id>

partsmith doctor
partsmith version
```

# 169. Build Command

Example:

``` bash
partsmith component build TPS62130.pdf \
  --kicad 10 \
  --output ./generated \
  --review
```

The command shall never auto-export a blocked build.

# 170. Non-Interactive CI Mode

``` bash
partsmith component build source.pdf \
  --ci \
  --fail-on-review \
  --fail-on-warning
```

CI mode shall produce machine-readable JSON results.

# 171. Review Command

``` bash
partsmith component review BUILD-ID
```

The review interface shall show:

``` text
Evidence
IR
Package
Symbol
Footprint
3D
Validation
Diff
Overrides
```

# 172. Review Decision API

``` python
class InputReviewService:
    def propose(self, request: InputReviewProposal) -> ProposalResult: ...
    def approve_inputs(self, request: InputApprovalRequest) -> RevisionResult: ...
    def reject_inputs(self, request: InputRejectionRequest) -> ReviewResult: ...

class ReviewService:
    def approve(self, build_id: UUID, reviewer: str) -> ReviewResult: ...
    def reject(self, build_id: UUID, reviewer: str, reason: str) -> ReviewResult: ...
    def override(
        self,
        build_id: UUID,
        path: str,
        value: OverrideValue,
        reason: str,
        expected_revision_hash: str
    ) -> ProposalResult: ...
```

Input review is available before any generated artifact exists. Its operations
use closed, versioned request schemas with these mandatory bindings:

| Request | Required content |
| --- | --- |
| InputReviewProposal | Component ID, base revision ID and canonical hash, expected current-head hash, reason, and typed proposed actions |
| InputApprovalRequest | Component ID, exact candidate revision ID/hash, expected current-head hash, inventory SHA-256, exact proposal IDs/hashes being accepted, and review reason |
| InputRejectionRequest | Component ID, exact candidate revision ID/hash, proposal IDs where applicable, expected current-head hash, and reason |

Actions are typed override replacements, evidence acquisition/replacement,
unassigned-evidence exclusions, conflict resolutions, decision supersession or
removal, and topology rebindings under sections 121.6–121.8. Each action uses
its schema-defined payload and references; arbitrary patches to approval,
history, or active-selector fields are forbidden. OverrideValue is section
121.6's closed typed union selected by the trusted path registry. The service
captures old values and base bindings; clients cannot assert them as trusted.

propose persists an unreviewed candidate/proposal without applying an approval.
approve_inputs authenticates the reviewer, verifies the exact candidate and
complete inventory, validates every selected action and transition, then
atomically appends a reviewed child revision under section 163. Approving a
pending decision creates a new APPROVED record with a new ID and supersession
link; the pending record is retained unchanged. Rejecting records an immutable
rejection event and never alters prior approvals. Any stale hash fails with a
conflict requiring rereview; it is not silently rebased. The service derives
active selectors and review metadata from accepted decisions.

ReviewService.override delegates to this proposal workflow and never edits a
released build. ReviewService.approve/reject are RELEASE operations: approval
requires section 167's finalized hashes and successful checks. The reviewer
argument must match the authenticated principal; a caller-supplied name is not
authentication. All services capture actor/time server-side. Input approval
cannot grant release approval, and release approval cannot fill missing input
reviews or waive blockers. The orchestrator alone advances build states after
successful service results; interfaces and CLI must label the two review stages.

# 173. Approval Rules

Approval shall fail if:

``` text
blocking validation exists
required evidence is missing
required review is incomplete
artifact hashes do not match
build graph is inconsistent
```

# 174. Export Rules

Only:

``` text
APPROVED
```

builds may be exported as production library content.

Installed library layout (distinct from the component bundle in section 175):

``` text
library/
├── symbols/
├── footprints/
├── 3d/
└── manifest/
```

## 174.1 Installation aggregates and approval boundaries

The MVP retains the packed shared symbol library in section 212. An approved
component bundle is immutable and content-addressed. Installing one or more
bundles creates a separate installation aggregate; adding a symbol to a packed
library is a new aggregate, not a byte-preserving copy of a component artifact.

An integration plan schema version 1.0 records the target project/library
identity, expected installed generation and hashes, source component manifest
and artifact hashes, adapter/serializer versions, logical-to-installed path and
nickname mappings, proposed files/table changes, and any removals. Freeze/hash
the plan before staging. Logical component paths remain independent of absolute
local destinations; local paths and execution identities belong to integration
audit records, not component engineering hashes.

Only deterministic container assembly and explicitly declared namespace/path
relocation are permitted integration transformations. They must preserve pin
numbers/types, electrical mappings, footprint/STEP geometry, and placement
meaning. Compare each installed symbol and footprint to its approved source
using a versioned semantic comparison with a closed allowlist of relocation
fields. Unexpected changes fail. A requested engineering or placement change
requires a new component release under section 167, not integration authorization.

Stage all aggregate files and final references, then run target KiCad parsing,
mapping/association/path-resolution checks and semantic-preservation checks
against their exact hashes. STEP bytes are copied unchanged. Produce a
deterministic installation manifest schema version 1.0 with plan hash, source
component manifest/artifact hashes, final installed file hashes, target/runtime
versions, and semantic-validation hash. It has no self-hash field. Verify that
completed manifest separately; retain post-manifest results in integration audit.

Explicit integration authorization binds the plan hash, installation manifest
hash, expected previous installed generation, and successful required checks.
Record actor, time, and decision in a separate audit envelope. Component release
approval is a prerequisite, not authorization for new aggregate bytes. Reusing
authorization is allowed only for identical plan/content/target/base bindings.
Publish through section 216 after rechecking bytes and the expected base.
Changing the target mappings or base generation requires a new plan and checks.

Phase 8 retains verified immutable component export/import. Phase 13.1 defines
the following installation contracts and revalidates source byte preservation;
the rest of Phase 13 implements shared-library installation, semantic
preservation, authorization, conflict detection and rollback. Subsequent library
updates create new installation generations and retain earlier manifests/history
without rewriting source component releases.

### 174.1.1 Versioned objects and canonical identities

Deliver a dedicated `schemas/integration-contracts-1.0.schema.json` with closed
Draft 2020-12 definitions and typed `partsmith.integration` contracts. The schema
must be packaged for offline validation; loader behavior follows the shared
schema support conventions. New objects have explicit `schema_version: "1.0"`.
Unknown fields/versions, missing required data, malformed hashes and invalid
cross-object bindings fail. Existing Phase 8 and desktop schemas retain their
identities; the integration schema does not silently extend their old meanings.

Use canonical JSON profile 1.0 and lowercase SHA-256. Declare sorted unique
ordering for source components, normalized relative files, nicknames, required
rules and removals. Ordered engineering arrays retain their declared semantics.
An object's identity is the hash of its canonical bytes in an external reference;
plan/manifest objects have no own-hash field. The published generation identity
is the installation-manifest hash. Run IDs, actor/time, temporary/absolute paths
and IPC state are operational audit fields, excluded from deterministic objects.
Filename/reference rules must avoid embedding a generation/manifest digest into
artifact bytes whose hashes determine that same digest. Record logical mappings
in the plan and runtime root resolution in audit.

Freeze/hash in this dependency order: plan, staged files and deterministic
pre-manifest checks, installation manifest, separate post-manifest verification,
authorization binding and decision audit, then publication journal/receipt.
Post-manifest results bind the finished manifest and remain outside it.

| Object | Required identity/content bindings |
| --- | --- |
| IntegrationPlan | Stable project/library target IDs and scope; expected base generation/manifest, managed file/table hashes and absences; approved component IDs/revisions, release-manifest and all three artifact hashes; adapter/serializer/comparison versions; logical-to-target relative paths/nicknames; create/modify/delete and table operations |
| InstallationManifest | Plan hash and same target IDs; complete retained/added source-component bindings; exact final relative file/table hashes and lengths; target/runtime/adapter versions; required deterministic validation and semantic-validation identities |
| IntegrationAuthorizationBinding | Plan hash, installation-manifest hash, target identity, expected base generation/manifest and exact successful required-check identities; no editable actor or implicit component approval |
| IntegrationValidationReport | Rule-set/comparator versions; source, target and staged content bindings; applicability and measured results for every required native/mapping/path/semantic rule; deterministic result content separated from run telemetry |
| IntegrationAuditEnvelope | Unique decision/event/attempt IDs, operation sequence, authenticated subject/mechanism, time, reason, decision/outcome, object/check references and local execution/root-resolution metadata; no credentials |
| IntegrationJournal | Target, exact expected previous and intended new generation/manifest/check/authorization references, owned staging location, recoverable publication intent/state and audit attempt identity; validated under its own version |

For initial installation, expected base generation/manifest are paired nulls
and newly created managed files declare expected absence; a file already present
violates that precondition. Existing project library tables and unrelated
content still require an exact pre-change inventory/hash and preservation under
declared table operations. Null generation does not authorize clearing them.
An existing owned installation without a resolvable manifest is an unknown base
and must not be overwritten. For an update, both base values resolve to a
verified generation and its complete inventory. A mixed null/present pair is
invalid. Empty removal/check arrays are explicit; required checks cannot be
omitted or empty merely to permit approval. Reject duplicate component identities
with different releases, duplicate/colliding normalized paths and nicknames, and
manifest files which lack a declared plan/source/managed-content basis.

### 174.1.2 Binding validation and approval boundaries

Schema validation verifies shape; services independently resolve referenced
bytes/approvals and compare cross-object identities. Require complete exact
final component releases and their successful required checks before staging.
Verify the plan, manifest, validation report and authorization all refer to the
same target, source set, mappings and expected base. A copied hash string or
saved approval label is not evidence that the referenced object exists/passes.

Approved source releases are immutable installation inputs. The revision bundle
index may contain only history/inventories; RETRIEVAL_REQUIRED is not proof of
locally available final artifacts. Resolve and hash-verify every object needed
for the requested installation/validation before proceeding. Explicit bounded
hydration may supply missing data without changing source bytes or approvals.
Unfinished desktop session/proposal data cannot substitute for those releases.

Actor/time/decision are authenticated through an immutable audit envelope bound
to the authorization object. An imported historical actor, CLI text field, IPC
token, launch action or component release approval cannot authenticate a new
integration reviewer or authorize changed aggregate bytes. Reject unsupported
versions or perform an explicit audited migration retaining the original object;
migrated content requires fresh applicable checks/authorization.

### 174.1.3 Persistence, state and idempotent recovery

Use a forward SQLite migration for immutable integration objects, current-target
generation bindings, authorization events and publication/recovery attempts.
Do not edit applied migrations or rewrite existing build/review records.
Current-generation updates use compare-and-swap on the exact expected base;
an unrelated newer generation is a conflict. Store typed/hash-verified object
references and retain the full prior generation/table state needed for rollback.

Keep integration lifecycle separate from component BuildState. Its minimum
operational states are PLANNED, STAGED, VALIDATED, AUTHORIZED, PUBLISHING,
PUBLISHED, REJECTED, FAILED, CANCELLED, RECOVERY_REQUIRED and ROLLED_BACK.
Record legal transitions and immutable sequence events. A later step cannot be
claimed before its bound predecessor succeeds. Inspection and saving do not
advance authorization/publication state; rollback preserves the failed attempt.

The filesystem publication boundary and SQLite/audit commit are not one database
transaction. Persist the journal/intent first and reconcile interruption into a
complete verified old or new generation before recording final outcome. Bind
retry keys to exact operation/plan/target/base/content identities. A repeated
request for an already committed identical operation returns its verified receipt
without duplicating decisions; changed bindings require a new attempt/review.
Uncertain publication status is RECOVERY_REQUIRED, never an inferred success.

### 174.1.4 Target, path and semantic validation

Use stable logical target IDs and declared project/global library scope.
Resolve local roots through the trusted adapter and bind that execution to the
selected target in audit; a matching relative layout cannot authorize another
project. Default Phase 13 acceptance is project-local. Changes to global tables
or other scopes require explicit selection and separate capability/publication
tests. Retain unrelated table entries, source bindings and installed components.

Normalize relative path spelling, reject parent/absolute/drive paths and escaping
symlink/reparse destinations, and test case/Unicode aliases on the actual target
filesystem. Refuse nickname/filename collisions or unmanaged overwrites instead
of silently renaming. Every relocation/removal is declared before plan freezing.
Each final reference resolves within the declared complete generation/root scope.
Recheck concurrent changes and editor dirty state before publication.

Version the semantic comparator and its closed relocation-field allowlist.
Implemented comparator 1.0 permits outer symbol/footprint entry names, derived
symbol-unit name prefixes, the symbol `Footprint` mapping property and the model
URI. A missing `Footprint` property may be inserted using the frozen plan's
declared library/entry identity. Existing nonmapping properties and all geometry,
electrical, layer and model-placement tokens remain exact. These mechanical
changes do not alter or replace the approved source artifacts.
Cover every retained symbol/footprint entry, pin number/type and mapping,
engineering property/graphic, pad shape/location/layer, model association and
placement. Define measured decimal/tolerance rules from the pinned source/PDL
and native-unit convention; do not loosen tolerances during installation.
STEP bytes remain exact. Unrecognized or changed engineering fields fail,
including changes to the unmodified component in a packed-library update.

### 174.1.5 Plugin configuration, IPC and saved integration data

The current `integrations/kicad/partsmith_setup` ActionPlugin and
`launcher.json` containing only `python` are legacy launch-only data. They grant
no live session identity, project scope, authorization or installed generation.
Where PartSmith manages an external interpreter launcher, Phase 13 introduces
a closed PartSmith launcher schema with
`schema_version: "partsmith-launcher-1.0"`, an absolute verified `python` path,
a declared `launch_mode` (`standalone` or `ipc`) and adapter compatibility version.
It contains no provider/IPC credentials or implicit target/approval flags.
Read the legacy one-field form only as standalone launch configuration; upgrading
it is an explicit installer operation. Reject unknown versions or unsafe runtime
commands. Keep interpreter/local-path metadata out of engineering hashes.
Verify the selected Python 3.11 runtime, PartSmith/package compatibility and
declared dependency lock before engineering operations; existence of a file
alone is insufficient. Use fixed argument vectors without a shell, strip embedded
Python path overrides and report moved/missing/incompatible runtimes clearly.

PCM packaging follows milestone 13.2, with root `metadata.json`, installed
package ownership and actual lifecycle checks. Production Python IPC uses
KiCad's verified per-plugin environment and online requirements preparation.
Executable runtime bundles are retained only as historical prototypes.
Do not generate a machine-specific launcher path inside a portable release ZIP.
If a PartSmith launcher is needed, provision it as local non-secret operational
data and retain explicit legacy migration; `plugin.json` alone is sufficient
for registration and does not require a second PartSmith launcher file.

IPC actions provide `plugin.json` satisfying the pinned KiCad
registration schema. Record stable plugin/action identifiers, compatible target
version, runtime entry and declared dependencies; validate source/PCM/installed
metadata/resource parity. KiCad's registration file and PartSmith's launcher file
are distinct formats, and neither replaces PCM package metadata. PartSmith
verifies its Python/CAD tuple regardless of who provisions it. Any first-load
dependency download follows the declared pinned provenance/network policy.
PCM manages package files; persistent application state and generated libraries
stay outside its disposable directories. Plugin install/update/removal never
removes component history, API credentials or unrelated plugins.

IPC endpoint/token/session values are transient process state. Bind version and
board/project/instance before use, recheck after restart or context changes, and
fail disconnected/ambiguous requests without selecting an arbitrary default
socket. Bound worker deadlines/cleanup; use existing central redacted logs and
service event identities. Required KiCad 10 IPC operations are discovery and a
real PCB/component read/inspection; additional mutations require supported API
transaction/undo and dirty-state tests. Standalone operation remains useful when
the user has not explicitly connected to an IPC instance.

The Phase 12 desktop index `partsmith-session-1.0` currently has no integration
fields. Extend saved integration drafts/references through an explicit new
transport version, retaining a supported 1.0 reader and original bytes during
migration. Reference immutable plan/manifest/audit objects by hash; never save
IPC tokens, active connections or a reusable live publication permission.
Load creates a fresh operational session and rechecks target/base/source/principal
before any resumed decision. The installation store/journal is authoritative
for publication recovery; an older desktop save cannot rewind an installed
generation, replay a decision or automatically reconnect/publish.

### 174.1.6 Bounded operations and error outcomes

Freeze an integration resource policy during Phase 13.1 and include its version
in implementation evidence. Initial defaults reuse the desktop limits: 128 MiB
per object, 1 GiB total staged/expanded data, 10,000 declared objects and 2 MiB
of retained redacted logs. Record bounded IPC/native-worker deadlines and owned
staging cleanup, with explicit non-secret configuration overrides. Limit tests
cover cumulative sizes, object counts, malformed data, timeouts and disk failure;
overrides do not bypass semantic or authorization requirements.

Provide stable machine-readable failure categories for invalid schema/version,
missing/unapproved/tampered source, stale base, target/namespace/path conflict,
failed semantic/native checks, unavailable/wrong IPC session, authentication
failure, resource limit, UNSUPPORTED_ATOMIC_INSTALL, publication failure and
RECOVERY_REQUIRED. Each includes its action/attempt/target and safe object/check
references. Preserve exact committed outcomes when later diagnostics/recovery
writes fail; show recovery warnings independently. No failure path overwrites
unrelated target content or presents a partial installation as successful.

### 174.1.7 Service and acceptance surface

Provide typed internal operations for plan/dry run, stage/validate, approve/reject
integration, publish, inspect current generation, recover and rollback. Headless
and GUI adapters call the same services; optional HTTP endpoints in section 203
do not require a network server for the desktop MVP. A source package export is
distinct from installation/publication of an aggregate.

Acceptance evidence maps every contract and failure category to Phase 13.1–13.8
fixtures/checks, with source, PCM payload and installed-runtime identities. Include an
initial install, two-component aggregate, unchanged no-op, one-component update,
explicit removal and full rollback; repeat deterministic staging, actual CLI/
PCB IPC/native-editor round trips and fault recovery. Skip/unsupported/mocked
success cannot satisfy a required real operation. Historical Phase 8/12 receipts
remain available and shared-file hashes are refreshed at each relevant closeout.

# 175. Project Packaging

A generated component bundle shall contain the frozen inputs or controlled
retrieval references, outputs, and evidence needed for reproducibility. This is
the portable audit/build bundle, distinct from section 174's installed library
and section 118's development repository. The following relative layout is
illustrative; its manifest is authoritative for paths and hashes:

``` text
BFT_COMPONENT/
├── source/
├── evidence/
├── ir/
├── pdl/
├── generated/
├── validation/
├── manifest/
└── README.md
```

Sensitive source documents may be excluded from a distributable package
while preserving their hashes and provenance references.

The bundle index schema version 1.0 is separate from the deterministic
engineering manifest. A separate bundle transport envelope records its canonical
hash and delivery metadata; neither the approved component manifest nor its
frozen audit envelope is changed. The index may include the already frozen
component audit records, but never itself or the transport envelope that hashes
it. This ordering prevents a packaging hash cycle.
Each entry declares object kind, schema/profile version, identity where present,
relative path or controlled retrieval locator, byte length, and SHA-256. Reject
duplicate identities with different bytes, unsafe paths, and hash mismatches.

The required replay closure includes:

- The exact source IR and every ancestor snapshot to its retained root, with
  base/acquisition references and decision history resolvable in that chain.
- Every inventory referenced by retained reviews, exact canonical bytes and
  reviewed evidence IDs; retained evidence, standards, translations, and decisions
  within snapshots or indexed immutable objects.
- Frozen input snapshots, node declarations/projections, PDL content/revisions,
  release profile, non-secret configuration, runtime lock/archive identities,
  recorded provider responses used for replay, and required source/raster objects.
- Final component artifacts, deterministic manifests, output/post-manifest
  reports, review/approval audit records, and versioned schemas needed to load them.

Bundle availability is OFFLINE_COMPLETE only after every object needed for the
declared rebuild and evidence inspection is materialized and hash-verified
locally, and the matching executable runtime is locally available and verified.
Runtime archives may be supplied by the installed runtime rather than duplicated
inside every bundle. A bundle with controlled retrieval dependencies is
RETRIEVAL_REQUIRED and cannot claim offline completeness until hydration succeeds.
Excluding sensitive documents preserves distribution utility but must not claim
unavailable source inspection or a complete offline replay. Credentials are
never part of the bundle or its locators.

Import stages and verifies the entire declared closure before publishing it to
the revision store. Missing history, incompatible schemas, ID conflicts, or
invalid transitions fail; do not clear parent IDs or invent review approvals.
An explicit reviewed-root import is a separate operation: preserve the original
import bytes/hash in audit, create a new root with fresh evidence identities and
an acquisition inventory, retain original facts/provenance, and obtain a new
input review. Inherited override/resolution approvals cannot be transferred as
new approvals; any required decisions are reapplied through reviewed children.
If valid provenance cannot be established without unavailable information, the
import remains an incomplete candidate and cannot generate. It is not a replay
of the old release and cannot inherit its release approval.

Phase 8 tests closure verification and transactional import. Phase 9 rebuilds
an imported multi-revision OFFLINE_COMPLETE fixture with network disabled,
matching deterministic component hashes while permitting truthful new audit IDs.

# 176. 3D Viewer Implementation

The MVP viewer shall support:

``` text
rotate
pan
zoom
top
bottom
front
back
left
right
isometric
measure
toggle pads
toggle courtyard
toggle silkscreen
toggle fabrication
show origin
show axes
show pin 1
```

The viewer shall display the independently generated footprint and model
together.

# 177. Placement Editing

Placement editing shall expose:

``` text
X offset
Y offset
Z offset
X rotation
Y rotation
Z rotation
mirror
```

Placement edits use section 121.6's typed override path and require a new
reviewed revision. They update placement metadata, not the underlying STEP
geometry. Association, final-byte cross-validation, manifest, and approval are
invalidated under sections 166–167; approved canonical geometry may be reused
only when its declared dependency hash is unchanged.

# 178. Placement Validation

The viewer shall immediately flag:

``` text
model floating
model below PCB
unexpected mirror
unexpected rotation
pin 1 mismatch
center mismatch
height mismatch
```

Interactive edits shall not silently become approved build data.

# 179. Visual Regression

Golden components shall have expected renders:

``` text
top
front
side
isometric
```

CI may compare rendered images using a defined tolerance.

Visual regression is supplemental. It cannot replace geometric
validation.

# 180. Golden Component Fixture

Each golden fixture shall contain:

``` text
fixture/
├── source/
├── expected/
│   ├── component_ir.json
│   ├── symbol/
│   ├── footprint/
│   ├── 3d/
│   └── validation.json
└── metadata.yaml
```

# 181. MVP Golden Corpus

Section 31 defines bootstrap and production coverage; STD-010 supplies exact
variant names. At least one manufacturer-backed golden component is required
per production variant. Generic family labels cannot substitute for those
variants or waive the per-variant negative and reproducibility corpus.

# 182. Document Difficulty Corpus

The test corpus shall include:

``` text
native digital PDF
scanned PDF
poor scan
rotated page
multilingual PDF
diagram-heavy PDF
image-only pin table
package drawing separated from pin table
symbol present
symbol absent
symbol embedded in block diagram
multiple package variants
conflicting revisions
incomplete mechanical information
```

# 183. Negative Corpus

Mandatory negative fixtures:

``` text
wrong pin number
wrong pin name
wrong electrical type
missing pin
extra pin
duplicate pin
wrong package
wrong pitch
wrong pad size
wrong pin-1
mirrored footprint
rotated 3D
shifted 3D
scaled 3D
wrong height
wrong thermal pad
conflicting evidence
missing land pattern
missing body dimensions
```

# 184. Unit Tests

Unit tests cover:

-   schema validators
-   unit conversion
-   coordinate transforms
-   PDL resolution
-   topology calculations
-   pad generation
-   symbol pin mapping
-   geometry measurements
-   hashes
-   dependency invalidation

# 185. Integration Tests

Integration tests shall cover:

``` text
PDF → evidence
evidence → IR
IR → PDL
IR → symbol
IR → footprint
IR → 3D
artifacts → validators
artifacts → cross-validation
build → manifest
```

# 186. System Tests

System tests shall run the complete path:

``` text
source PDF
→ extraction
→ evidence
→ AI candidate interpretation
→ IR
→ generators
→ validation
→ review
→ export
```

At least one complete test shall execute without network access after
required model/evidence fixtures are prepared.

# 187. Provider Contract Tests

Every AI provider adapter shall run against the same normalized fixture
suite.

The test verifies:

``` text
provider output
→ normalization
→ schema
→ evidence references
→ ambiguity handling
```

Provider differences must not change B.F.T. downstream schemas.

# 188. Determinism Tests

Run two clean builds with equal input snapshots and pinned runtime. Compare
input_snapshot_hash, generator dependency hashes, exact artifact byte hashes,
validation_semantics_hash,
and engineering_manifest_hash. Full run envelopes are not expected to be equal:
new build IDs, timestamps, and approval event IDs remain truthful audit data.
Compare their bindings to identical deterministic content instead. An equivalent
but byte-different STEP file fails this gate; equivalence diagnostics do not
make downstream manifest hashes equal. Normalize exporter metadata deterministically
before final-byte validation or select a runtime/exporter that passes the gate.
Store the comparison as section 167's separate post-manifest report.

Tests include different process hash seeds, replayed prepared evidence,
audit-only changes, placement-only changes, and an engineering-value change.
The first two preserve deterministic content, audit-only changes preserve
generator dependencies, placement changes preserve STEP geometry, and changed
engineering inputs invalidate the declared affected outputs. A reused full IR
record also retains an equal ir_record_hash; different audit histories need not.

# 189. Security Tests

Test:

``` text
malicious PDF text
prompt injection
path traversal
oversized PDF
zip bomb if archives are accepted
malformed STEP
malformed KiCad files
invalid YAML/JSON
unsafe CadQuery parameters
shell injection
provider credential leakage
```

# 190. Resource Limits

External documents shall be processed under configurable limits:

``` text
maximum file size
maximum page count
maximum extracted image size
maximum OCR time
maximum AI request size
maximum CadQuery generation time
maximum STEP size
maximum concurrent builds
```

A resource limit failure is a controlled build failure, not a crash.

# 191. Sandbox Requirements

External tools such as:

``` text
OCR
CadQuery runtime
KiCad
PDF converters
```

shall run with least privilege where practical.

Never execute arbitrary commands extracted from a document.

# 192. Logging

Logs shall use structured events:

``` yaml
event:
  timestamp:
  build_id:
  component_id:
  stage:
  severity:
  event:
  message:
  metadata:
```

Secrets must be redacted.

# 193. Error Model

All errors shall map to stable B.F.T. codes.

Examples:

``` text
BFT-E001 SOURCE_UNREADABLE
BFT-E002 OCR_FAILED
BFT-E003 EVIDENCE_CONFLICT
BFT-E004 IR_INVALID
BFT-E005 PDL_NOT_FOUND
BFT-E006 PACKAGE_UNSUPPORTED
BFT-E007 GENERATION_FAILED
BFT-E008 VALIDATION_FAILED
BFT-E009 CROSS_VALIDATION_FAILED
BFT-E010 KICAD_INCOMPATIBLE
BFT-E011 HUMAN_REVIEW_REQUIRED
BFT-E012 NOT_GENERATABLE
BFT-E013 REPRODUCIBILITY_FAILED
```

# 194. NOT_GENERATABLE Contract

A `NOT_GENERATABLE` result shall state:

``` text
what is missing
why it matters
which artifact is blocked
what evidence would unblock it
```

Example:

``` text
Footprint cannot be generated safely.

Missing:
  manufacturer land pattern
  package dimensions sufficient to derive a validated land pattern

Needed:
  package mechanical drawing or manufacturer land-pattern recommendation
```

# 195. Configuration

Configuration shall be layered:

``` text
built-in defaults
→ system configuration
→ project configuration
→ command-line overrides
```

The effective non-secret engineering configuration shall be stored in the
engineering manifest; operational/run settings belong in the audit envelope.
Credentials are excluded from both and from all hashes (AI-003).

# 196. Provider Configuration

Provider settings shall include:

``` yaml
provider:
  name:
  model:
  endpoint:
  timeout_seconds:
  max_retries:
  local_processing:
```

Credentials must come from secure environment/credential storage, never
project YAML.

Provider name, model identifier, pinned provider/model version, and provider
schema version are engineering inputs when they can affect interpreted output;
they belong in the frozen input snapshot and relevant dependency projections.
Endpoint, timeout, retry policy, and local-processing execution mode are
operational settings; they belong in the audit envelope and do not invalidate
deterministic engineering artifacts unless a provider contract explicitly
declares that they affect output. Credential material is never included in
either category.

# 197. Retry Policy

Retry only transient failures:

``` text
network timeout
provider rate limit
temporary process failure
```

Do not retry deterministic failures such as:

``` text
schema invalid
unsupported package
missing evidence
geometry invalid
```

# 198. Caching

Cache immutable expensive operations:

``` text
PDF extraction
OCR
AI requests
PDL resolution
3D generation
```

Cache keys must include all relevant inputs.

AI cache keys must include:

``` text
provider
model
prompt/task schema
input hash
provider configuration affecting output
```

# 199. Offline Mode

Offline mode shall support:

``` text
local document parsing
local OCR
local PDL
local deterministic generation
local validation
local KiCad validation where installed
```

AI interpretation may be unavailable unless a local provider is
configured.

# 200. Human-in-the-Loop UX Principle

The UI should ask humans only about unresolved engineering questions.

Bad:

``` text
"Do you want to continue?"
```

Good:

``` text
Pin 5 is EN in the pin table but FB in the block diagram.

Which source is authoritative?

[Pin table]
[Block diagram]
[Inspect evidence]
```

# 201. Review Queue

The application shall maintain a review queue:

``` text
build
issue
severity
evidence
proposed resolution
status
reviewer
decision
```

Issues shall be independently resolvable where possible.

# 202. Audit Trail

Every human decision shall record:

``` text
reviewer
timestamp
decision
old value
new value
reason
evidence
```

Audit records are immutable.

# 203. API Layer

The service layer should expose typed operations:

``` text
POST /components
POST /components/{id}/input-review/proposals
POST /components/{id}/input-review/approve
POST /components/{id}/input-review/reject
POST /builds
GET  /builds/{id}
POST /builds/{id}/validate
POST /builds/{id}/review
POST /builds/{id}/approve
POST /builds/{id}/export
POST /integration-plans
POST /integration-plans/{id}/authorize
POST /integration-plans/{id}/publish
POST /integration-targets/{id}/recover
POST /integration-targets/{id}/rollback
GET  /integration-targets/{id}/generation
GET  /builds/{id}/manifest
GET  /builds/{id}/evidence
GET  /builds/{id}/artifacts
```

The API is optional for the first desktop MVP but the internal service
boundaries shall support it.
Input-review endpoints use section 172's typed requests and stale-head checks;
build approval remains release approval. Integration endpoints use section
174.1's exact plan/content/target bindings and section 216's publication checks.
Integration service operations are Phase 13 deliverables. Planning, staging,
authorization, publication and recovery are distinct requests/results; loading a
component/session cannot implicitly invoke them. Rollback carries an expected
current-generation binding and uses the same authenticated, journaled boundary.

# 204. Event Model

Build events:

``` text
BuildCreated
SourceAnalyzed
EvidenceAdded
IRBuilt
IRValidated
PackageResolved
ArtifactGenerated
ValidationCompleted
ReviewRequested
OverrideApplied
Approved
Rejected
Exported
```

Events should contain build ID and monotonic sequence number.
Integration events additionally bind attempt/target/plan/generation identities
and an immutable per-attempt sequence. Distinguish planned, staged, validated,
authorized, publishing, published, conflicted, failed, recovery-required and
rolled-back outcomes. After a committed decision/switch, later cancellation or
log/checkpoint failure cannot rewrite the event as an uncommitted cancellation.

# 205. Plugin/Extension Model

The following shall be replaceable:

``` text
AI provider
OCR engine
PDF parser
3D adapter implementation within the approved CadQuery/OCP/OCCT runtime
KiCad adapter
storage backend
```

Core schemas and validation rules remain B.F.T.-owned. Adapter replaceability
does not authorize another CAD runtime. A different runtime requires an
explicit specification revision; a changed approved runtime tuple requires
fresh Phase 6 validation before release use.
The PartSmith KiCad launch plugin is a separate adapter entry, not a schema,
component-release service or installation authorization. Phase 13.2/174.1.5
define its runtime/configuration/IPC data boundaries and compatibility evidence.

# 206. Version Compatibility

Every build shall record:

``` text
B.F.T. version
schema version
PDL revision
generator versions
KiCad target
AI provider/model
```

A build made with a newer schema shall not be silently loaded as an
older schema. IR 1.0/1.1 remain readable under their own versioned rules;
v0.9.7 production inputs require explicit migration to IR 1.2 (section 121.4).
Specification v0.9.7 is distinct from IR/PDL/schema versions. The new integration
contracts start at 1.0; existing Component IR, PDL, replay and session versions
change only through their own explicit schema/migration decisions.

# 207. Schema Migration

Schema migration shall be explicit:

``` text
v1 → v2
```

with:

``` python
migrate_v1_to_v2(ir)
```

Migration shall produce a new canonical object and record the migration
history.

# 208. Backward Compatibility

The implementation shall support reading the immediately previous IR
schema version where practical.

It shall never silently reinterpret old fields with new semantics.

# 209. Artifact Naming

Recommended:

``` text
<manufacturer>_<mpn>_<package>.<ext>
```

Sanitize filesystem-invalid characters.

Keep a canonical component ID separately from the display filename.

# 210. Library Naming

Recommended:

``` text
BFT_<Manufacturer>
BFT_<PackageFamily>
```

The exact organizational strategy may evolve, but library nickname
uniqueness is mandatory.

KiCad documents project and global symbol-library tables and the
requirement for unique library nicknames within a table.
[Reference register: section 247](#247-external-reference-register).

# 211. Footprint Library Layout

MVP:

``` text
BFT_Footprints.pretty/
    <footprint>.kicad_mod
```

The generated footprint shall remain a normal KiCad footprint artifact
rather than a proprietary container.

# 212. Symbol Library Layout

MVP:

``` text
BFT_Symbols.kicad_sym
```

An unpacked symbol-library layout may be supported later.
This file is the installation aggregate defined by section 174.1; its hash and
authorization differ from those of each immutable source component bundle.

KiCad 10 documentation supports both packed `.kicad_sym` libraries and
unpacked symbol-library directories. [Reference register: section 247](#247-external-reference-register).

# 213. 3D Library Layout

MVP:

``` text
BFT_3D/
    <component>.step
```

Use project-relative references where supported.

# 214. Project Integration

When adding a generated component to a project, B.F.T. shall be able to:

1.  Create or update project-local libraries.
2.  Update library tables if authorized.
3.  Assign the symbol's footprint.
4.  Reference the 3D model.
5.  Preserve project portability.
6.  Record the integration operation in the audit trail.

# 215. Dry Run

All mutating commands shall support:

``` bash
--dry-run
```

Dry run shall show:

``` text
files to create
files to modify
files to delete
library-table changes
build-state changes
```

No project files may be modified during dry run.

# 216. Atomic Export

Component bundle export shall use:

``` text
temporary directory
→ validate
→ hash
→ atomic rename
```

A partially generated library shall never be presented as a successful
export.

Installation aggregates use immutable staged generations and one publication
boundary covering the complete file/reference set. Acquire an installation
lock, verify the plan's expected base hashes, stage and validate all changes,
obtain section 174.1 authorization, then recheck the base and staged hashes.
Publish only the complete generation. Independent sequential file replacements
are not an atomic multi-file publication algorithm.

The versioned installation adapter must declare and test its publication
mechanism on each supported filesystem/platform, including how KiCad resolves
the active generation and how library-table changes are included. Use a single
atomic generation switch where supported. If the target cannot provide the
required publication boundary, report UNSUPPORTED_ATOMIC_INSTALL before changing
the project; do not silently degrade to partial installation. Phase 13 acceptance
requires a working supported target, not only this rejection path.

Persist a recoverable journal binding previous/new generation hashes and
authorization before publication. Crash recovery must resolve to a complete
verified previous or new generation, reconcile the integration audit event,
and never mark a partial generation EXPORTED. Test faults before staging,
after validation, during publication, and before audit completion. Dry run
produces the plan without writing target files or changing build state.

# 217. Rollback

Before modifying an existing library, B.F.T. shall create a rollback
record containing:

``` text
previous artifact hash
previous file content or backup reference
library table state
timestamp
build ID
```

For an aggregate update, retain the entire previous installation manifest,
generation, exact library-table/reference state, and source-component bindings.
Rollback restores that complete verified generation under the same lock and
publication rules. Check the expected current generation first: unrelated
concurrent edits cause a conflict, not an overwrite. Record rollback as a new
audit event; never delete the failed attempt or rewrite component approvals.

# 218. Existing-Component Update

If a component already exists:

``` text
inspect
→ compare
→ show semantic diff
→ require approval
→ backup
→ atomic replacement
```

Never overwrite an approved component silently.
The approval above is section 174.1 integration authorization for the exact
staged installation and expected base. Updating one component preserves all
unmodified components' engineering content and source bindings; verify this
before publishing the packed library. Engineering changes require a separately
approved new component release before installation planning.

# 219. Duplicate Detection

Duplicate detection shall compare:

``` text
MPN
normalized MPN
pin map
package
symbol hash
footprint geometry hash
```

Near-duplicates shall be flagged for review.

# 220. Manufacturer Naming Normalization

Manufacturer names may be normalized for search, but original spelling
remains authoritative metadata.

Example:

``` text
Texas Instruments
Texas Instruments Incorporated
TI
```

may normalize to a common search identity while preserving the source
string.

# 221. Translation Layer

Multilingual extraction shall preserve:

``` text
original text
translated text
source language
translation provider
translation model
translation timestamp
```

Never discard the original technical text.

# 222. Technical Translation Rule

Translated text may assist interpretation.

It shall not independently establish a mechanical or electrical fact
when the original evidence is available and materially clearer.

# 223. Standards Adapter

Standards data shall be accessed through a versioned standards adapter.

``` python
class StandardsProvider(Protocol):
    def lookup_package(self, package_id: str) -> StandardsResult: ...
    def lookup_land_pattern_rule(self, package_id: str) -> StandardsResult: ...
```

Standards must be identified by:

``` text
organization
standard number
revision
source
```

# 224. Standards Use Restrictions

Standards may provide:

``` text
generic geometry
land-pattern methodology
terminology
package-family constraints
```

Standards shall not invent:

``` text
pin function
electrical type
manufacturer-specific dimensions
MPN-specific behavior
```

# 225. Geometry Measurement Engine

The geometry engine shall expose:

``` python
measure_bbox()
measure_center()
measure_height()
measure_distance()
measure_angle()
count_solids()
count_leads()
intersects_plane()
```

All measurements return:

``` text
value
unit
tolerance
source geometry
```

# 226. Geometry Reference Frames

All generated artifacts shall expose reference geometry:

``` text
package_center
footprint_origin
pcb_plane
model_origin
pin1_reference
pad_centers
body_bbox
```

This is required for cross-validation and viewer overlays.

# 227. Pin Mapping Engine

The mapping engine shall compare, using section 148 applicability and declared
reference features when physical geometry is intentionally absent:

``` text
IR pin
↔ symbol pin
↔ footprint pad
↔ physical model pin/lead
```

A mapping table shall be produced:

``` yaml
mapping:
  pin: "5"
  symbol_pin: "5"
  footprint_pad: "5"
  model_lead: "5"
  status: PASS
```

The mapping report records MEASURED versus DECLARED_ONLY evidence and does not
claim physical measurement for an absent model feature.

The mapping engine is an independent post-generation validator. It consumes
the generated symbol and footprint artifacts, authoritative IR pins, and PDL
terminal/group definitions. It does not become an input to either generator,
and it runs only after both independent artifacts pass their own validators.

# 228. Mapping Failure Rules

Failures include:

``` text
missing mapping
duplicate mapping outside an explicitly declared terminal group (section 93.1)
renumbered mapping
ambiguous mapping
physical mismatch
pin-1 mismatch
```

No component may pass if a required physical/electrical mapping is
ambiguous.

# 229. Electrical Sanity Checks

B.F.T. shall perform non-simulation sanity checks:

``` text
power pin naming consistency
duplicate power pins
obvious missing ground pin
NC conflicts
input/output contradictions
```

These are review aids, not replacements for manufacturer electrical
specifications.

# 230. Symbol Quality Rules

MVP symbol checks:

``` text
all pins visible or intentionally hidden
no duplicate physical pin IDs; repeated symbol-unit representations require explicit mapping
no duplicate pin names unless explicitly permitted
pin orientation valid
pin lengths valid
reference/value fields present
footprint field valid
```

# 231. Footprint Quality Rules

MVP footprint checks:

``` text
all logical terminal groups have unique numbers; shapes obey section 93.1
terminal/group/shape counts correct
pad shapes valid
pad positions valid
pin-1 marker present where required
courtyard present
fabrication information present
silkscreen does not violate required constraints
```

# 232. 3D Quality Rules

MVP 3D checks:

``` text
solid geometry parseable
expected scale
expected center
expected height
expected orientation
expected marker
expected lead/pin geometry where modeled
```

# 233. Release Report

Every approved build shall produce:

``` text
Executive summary
Source documents
Evidence summary
Package determination
Pin mapping
Generated artifacts
Validation results
Overrides
Compatibility
Hashes
Review decisions
```

# 234. Machine-Readable Report

JSON report shall contain:

``` yaml
summary:
  status:
  errors:
  warnings:
  review_items:

artifacts:
validation:
evidence:
mapping:
compatibility:
reproducibility:
```

# 235. Implementation Milestones

The numbered Phases 0–14, including Phase 9.5 between Phases 9 and 10, are the
sole implementation order and gate authority.
These milestones summarize them and create no competing prerequisites:

| Milestone | Phases and scope |
| --- | --- |
| Foundation | 0–2: repository, persistence, versioned IR and normalization |
| First PDL | 3: the entry referenced by GOLD-0402-001, loader and validation |
| Deterministic component | 4–8: input checks, generators, CAD spike, validators, minimal approval and KiCad compatibility |
| Reproducibility | 9: snapshots, dependency invalidation, deterministic comparisons |
| Setup GUI | 9.5: wxPython GUI, standalone/KiCad launch, secure API-key entry, datasheet and part-number inputs, live logs and cancellation |
| Document intelligence | 10–11: extraction, evidence, provider adapter |
| Review UI | 12: UI over existing review/approval services |
| Extended integration | 13.1–13.8: installation contracts/R13-01 closure, PCM package/lifecycle and verified runtime, planning, semantic staging, authorization, atomic publication/recovery, project/IPC workflow and full gate |
| Production release | 14: packaging plus all eight production variants and full release corpus |

# 236. MVP Definition of Done

PartSmith MVP is complete only when all Phases 0–14, including Phase 9.5, pass and at least one
manufacturer-backed golden component for each of the eight STD-010 variants can:

``` text
start from manufacturer PDF
↓
extract evidence
↓
produce reviewed IR
↓
resolve PDL
↓
generate symbol
↓
generate footprint independently
↓
generate 3D independently
↓
validate all artifacts
↓
cross-validate footprint and 3D
↓
pass KiCad compatibility tests
↓
receive human approval
↓
export a portable library package
```

and the complete process is reproducible under section 166. The negative,
compatibility, and clean-installation gates also pass. A single 0402 component
is the Phase 8 engineering bootstrap, not the full production MVP.

# 237. MVP Non-Goals

The first MVP does not require:

-   arbitrary package families
-   perfect automatic interpretation
-   full PCB autorouting
-   board-level thermal analysis
-   electrical simulation
-   automatic manufacturer web crawling without explicit source control
-   fully autonomous conflict resolution
-   automatic approval of ambiguous parts
-   production-grade mechanical CAD for every package

# 238. First Implementation Priority

Follow the numbered phase plan: repository → persistence → Component IR →
first PDL → deterministic generators/validators → first complete approved
component → reproducibility → extraction → AI → full review UI → expanded
KiCad integration → full corpus/packaging. Minimal input validation, approval,
and compatibility work occurs at the early gates explicitly assigning it.
The project does not start with AI. One component proves the deterministic
bootstrap; Phase 14 proves the declared eight-variant production scope.

# 239. First Package Definition Set

Create the first 0402 PDL record in Phase 3; expand and validate all of these
records by the Phase 14 production gate:

``` text
0402
0603
0805
SOT-23
SOIC-8
TSSOP-16
QFN-16-3x3-0.5P
QFN-24-4x4-0.5P
```

These records should be treated as versioned engineering assets.

# 240. First Golden Components

Select at least one real manufacturer component for each PDL variant.

Each golden component shall have:

``` text
manufacturer datasheet
approved evidence package
approved IR
approved symbol
approved footprint
approved STEP
expected hashes
expected validation results
```

# 241. First Fault-Injection Set

The first CI fault suite shall inject:

``` text
wrong pin
wrong pitch
wrong pad
wrong pin-1
wrong package
3D shift
3D rotation
3D mirror
3D scale
wrong height
```

Every injected change to a required observable or declared placement/terminal
mapping must fail its intended deterministic rule. Under section 149, an allowed
symmetry-equivalent geometry is a separate positive equivalence case, never
counted as a detected fault. Include asymmetric fixtures to prove each required
rotation/mirror fault is observable.

# 242. CI Pipeline

Recommended:

``` text
lint
↓
schema tests
↓
unit tests
↓
PDL tests
↓
generator tests
↓
validator tests
↓
golden components
↓
negative corpus
↓
determinism tests
↓
security tests
↓
KiCad integration tests
```

A release cannot proceed if any blocking stage fails.

# 243. CI Artifacts

CI shall retain:

``` text
test logs
validation reports
generated artifacts
hash manifests
failure reproductions
rendered regression images
```

for failed builds.

# 244. Engineering Review Checklist

Before declaring the v0.9.8 production implementation release-ready after Phase 14:

-   [ ] Component IR schema frozen
-   [ ] Evidence schema frozen
-   [ ] PDL schema frozen
-   [ ] Transform contract tested
-   [ ] Generator interfaces frozen
-   [ ] Validator interfaces frozen
-   [ ] Build state machine implemented
-   [ ] Dependency invalidation tested
-   [ ] First PDL records approved
-   [ ] Golden fixtures approved
-   [ ] Negative fixtures approved
-   [ ] KiCad target version selected
-   [ ] KiCad adapter tested
-   [ ] Viewer architecture accepted
-   [ ] Reproducibility test passes
-   [ ] Security baseline passes
-   [ ] Input and release approval stages are independently tested
-   [ ] Portable revision/inventory closure and offline import/rebuild pass
-   [ ] Snapshot profile 1.2 per-node invalidation passes
-   [ ] STEP byte determinism passed in Phase 6 and full-build Phase 9
-   [ ] Shared-library aggregate publication, authorization, and rollback pass

# 245. Implementation Boundary and Repository Bootstrap

PartSmith is independently packaged as `partsmith` with `src/partsmith` and
the `partsmith` executable. The hosting repository URL/path spelling is external
metadata and does not change product identity. No `bft` launcher is required.

Component acquisition/purchase is explicitly deferred beyond the Phases 0–14
MVP. Current scope is the deterministic build workflow with later AI-assisted
interpretation. Historical ACQ requirements are not current implementation
requirements. A future acquisition revision must define exact identity matching,
immutable released-package verification, acquisition metadata separate from
engineering hashes, and a commerce boundary outside the engineering core.

The IR/PDL, profile 1.2 pipeline, immutable review/bundle services and desktop
workflow have scoped Phase 0–13 evidence; review the recorded source, PCM and
installed-runtime bindings. Earlier wheel and gate identities remain historical.
The Phase 13 installation contracts and execution checkpoints have recorded PASS.
The Phase 14 eight-variant corpus is implemented. Production installation now
uses the online managed-Python candidate under the 2026-10-08 owner decision.
Clean-machine online PCM lifecycle acceptance and the dependency/license manifest
review for this distribution remain blocking Phase 14 requirements. The retired
executable bundle's incomplete vendor-source audit is retained at its historical
scope and is not a requirement to maintain or release an offline edition. Refreshing current input
hashes does not broaden historical execution scope or grant a new gate PASS.

# 246. Consistency Resolution Register

The following decisions resolve the 2026-09-19 review at specification level.
They do not assert that pending implementation work or tests have completed.

| Finding | Normative resolution |
| --- | --- |
| R01 | Sections 88, 96, 121.2: active closure and explicit resolution records; immutable superseded history does not block by status alone |
| R02 | Section 121.1: null candidate values/units and unresolved reasons, concrete values required only for selected generation inputs |
| R03 | Sections 95/121.1: one power_in/power_out electrical enum; power flag is not a physical pin type |
| R04 | STD-007/121.1: manufacturer-recommended, IPC-derived, PDL-derived source enum; overrides are separate provenance |
| R05 | Phase 8: minimal orchestrator, headless approval and KiCad adapter precede later UI/IPC expansion |
| R06 | Sections 121.2/137: input-only IR_VALIDATED versus post-generation APPROVED |
| R07 | Sections 159/160: HUMAN_REVIEW_REQUIRED waiting state, HUMAN_REVIEW validation result |
| R08 | Sections 121.3/166–167/188: frozen inputs, dependency projections, deterministic content versus audit envelope |
| R09 | Section 92: complete frame, handedness, Euler/matrix, origin, and adapter-conversion contract |
| R10 | Section 153: blockers cannot be warning-waived; WARN policy and phase waivers are distinct |
| R11 | Section 13: STEP-only PartSmith output list |
| R12 | STD-002/10/113: all MVP production releases require STEP; partial previews are not releases |
| R13 | Sections 148–149/227: declared applicability, measured versus declared anchors, contact relations, and symmetry tests |
| R14 | Sections 118/168–171/245: partsmith package/repository/executable vocabulary |
| R15 | Sections 85/121.1: required revision/document link and explicit content-hash basis for unversioned sources |
| R16 | Product header/245: purchase explicitly deferred to a separately specified post-MVP extension |
| R17 | STD-014: role baseline, per-entry evidence, and executable reproducibility are separate milestones |
| R18 | Phase 14/235–240: numbered plan is authoritative; all eight production variants required at release |
| R19 | Section 205: adapter replacement within CadQuery runtime; new runtime requires specification revision |
| R20 | Section 121.5/221/223: structured standards and translation records with explicit hash/provenance inclusion |

Editorial resolutions: version/readiness/date labels distinguish current baseline
from original authorship; section 245 has operative content; explanatory
examples are labeled; current citation placeholders are replaced by section 247.

## v0.9.5 review resolutions

All V094 findings are resolved at specification level by the decisions below.
Implementation and gate status is recorded in the header and phase reports. The
[original review](../docs/spec-consistency-review-v0.9.4.md) and probes are
preserved as evidence of the reviewed v0.9.4 baseline.

| Finding | Decision | Normative sections |
| --- | --- | --- |
| V094-01 | Typed overrides | 88, 121.6; typed registry and active bindings including pin/placement leaves |
| V094-02 | Evidence relevance | 121.7; candidate targets independent of selection, review inventory and transition checks |
| V094-03 | Decision history | 121.8; immutable inline decisions, bound snapshots and explicit active selectors |
| V094-04 | Hash binding cycles | 166; snapshot profile 1.1 distinguishes dependency, binding, and history edges |
| V094-05 | Transform closure | 92/150; full affine composition/inversion, explicit adapter rejection |
| V094-06 | Applicability | 148/152; strict IR 1.2 fields, null status for declared exclusions |
| V094-07 | Final bytes | Phase 8/141/167; final association checks, exact-byte invalidation and approval |
| V094-08 | Manifest graph | 155/166/167; post-manifest/comparison results outside deterministic manifests |
| V094-09 | Backend equivalence | Phase 9/166/188; byte identity is mandatory; equivalence diagnostic only |
| V094-10 | Headless workflow | 11/167; automated placement and CLI review precede UI |
| V094-11 | Release scope | 31/50/98/181; one release matrix, eight variants, CLASS_A, provider/language coverage |
| V094-12 | Terminal counts | 84.1/93.1/148/228/231; exposed terminals and compound group/shape counts |
| V094-13 | Source rectangles | 124.1; document-page-1.0 and retained render transforms |
| V094-14 | Historical material | linked unchanged archive; no obsolete contracts in the active text |
| V094-15 | Duplicate prose | 11/15/30/32/90/116/142/174/175/247; authoritative definitions and cross-references |
| V094-16 | Stale navigation | v0.9.5 labels, current-section navigation, canonical examples and dated sources |

## v0.9.6 downstream review resolutions

The [v0.9.5 downstream review](../docs/spec-downstream-impact-review-v0.9.5.md)
is retained unchanged. The following decisions resolve its findings at
specification level; implementation and test evidence remain due at the named
gates. The earlier resolution tables describe their original revision scopes.

| Finding | Concrete solution | Sections and delivery gates |
| --- | --- | --- |
| D095-01 | Preserve immutable component bundles; separately hash, validate, authorize and atomically publish packed installation aggregates with source bindings and rollback | 167/174.1/175/212/216–218; v0.9.7 moves installation contracts to Phase 13.1, followed by shared installation in 13.2–13.8; Phase 8 retains source-bundle verification |
| D095-02 | Typed input proposal/approval/rejection services bound to revision/inventory hashes, distinct from release approval; append approved decisions and reject stale heads | 2.1/159/163/168/172/203; service Phase 8, UI Phase 12 |
| D095-03 | Retain immutable ancestry/inventories, transactional forward migrations, versioned bundle object index, verified closure import and explicit offline availability | 163/175; persistence/import Phase 8, offline replay Phase 9 |
| D095-04 | Snapshot profile 1.2 scopes trusted configuration per generator/validator/finalizer while the full snapshot retains complete runtime inputs; retain profile 1.1 hashes unchanged | 166; incremental projection implementation Phases 4–6, whole-build integration Phases 8–9 |
| D095-05 | Silkscreen edits invalidate results bound to changed footprint bytes, final checks, manifest and approval while preserving independent STEP geometry | 103/167; Phases 8–9 negative/reuse tests |
| D095-06 | Two clean independent STEP exports must be byte-identical in the CAD spike, with deterministic settings and revalidated normalization | Phase 6 gate; whole-build Phase 9 test retained |
| Metadata remnants | Current product/spec headers identify v0.9.8 and 2026-10-08; the archived v0.9.6 header/date and earlier review/gate versions remain historical | Header/product description/245/246 |
| Count/fault examples | QFN examples distinguish peripheral leads, conductive exposed terminals and groups; blanket fault language excludes allowed symmetry-equivalence positives | 6/21/93.1/241 |
| Downstream checkpoints | Define supported pin-edit sequencing, complete PDL feature declarations, and required-rule result aggregation | 121.7/126/152; Phases 3/7–8/12 |

## v0.9.7 Phase 13 and plugin/data review resolutions

The full v0.9.6 snapshot is retained in resources/history. D095-01's current
delivery column above reflects the explicit project-owner sequencing revision;
the original Phase 8 assignment is preserved there and in the R13-01 finding.

| Finding/gap | Current requirement and owner |
| --- | --- |
| R13-01 | RESOLVED by Phase 13.1 PASS, 2026-10-06: closed schemas/frozen types, canonical/golden/negative checks, exact source preservation, affected Phase 8/12 source regressions, isolated offline PCM contract payload and final archived hash closeout; see `docs/gates/phase-13.1-artifacts.json`. Complete Phase 13 PASS is separately recorded in `docs/gates/phase-13-artifacts.json`, 2026-10-07. |
| Broad Phase 13 bullets | Nine numbered work items and eight ordered milestones with explicit prerequisites, per-milestone checks and final gate |
| Plugin/configuration gap | Launch-only legacy data distinguished from IPC registration; versioned runtime configuration, packaged metadata, explicit migration and transient session/credential rules in 13.2/174.1.5 |
| PCM installation correction, 2026-10-05 | PCM ZIP/metadata and IPC registration are separate; verified managed-Python or bundled-executable runtime; real install/preparation/update/uninstall/reinstall in 13.2/13.7/13.8; Phase 14 proves clean online production installation; the 2026-10-08 owner decision retires runtime bundles |
| Phase 13 wheel retirement, 2026-10-05 | No PartSmith wheel build/install/test or required wheel receipt in Phase 13; isolated contract payload in 13.1, retire wheel automation and prove PCM resource/runtime parity in 13.2, full source/PCM acceptance in 13.8; historical Phase 0–12 evidence retained |
| Native/API target gap | Pinned-build capability/units tests; real KiCad 10 PCB Editor IPC; CLI/native-editor schematic evidence and tested target publication mechanism in 13.2/13.7 |
| Installation data gap | Closed plan/manifest/authorization/check/audit/journal objects, initial-base/null rules, source closure, content identities and acyclic hash order in 174.1.1–174.1.3 |
| Target/semantic gap | Scoped target/path/nickname safety, complete mapping/comparison allowlist, exact source/STEP preservation, unmanaged/unchanged component handling in 13.3–13.4/174.1.4 |
| Publication/recovery gap | Separate integration state, authenticated exact authorization, idempotency, lock/base checks, complete-generation switch/journal and fault-tested rollback in 13.5–13.6 |
| Desktop/acceptance gap | Explicit install controls and versioned saved references without live authority, dirty-project policy, real two-component use/round trips, resource/error coverage and full source/PCM/hash closeout in 13.7–13.8 |

# 247. External Reference Register

Documentation entry points checked 2026-09-19:

| Reference | Entry point and limits |
| --- | --- |
| KiCad native formats | [Official s-expression format overview](https://dev-docs.kicad.org/en/file-formats/sexpr-intro/index.html) and [footprint format](https://dev-docs.kicad.org/en/file-formats/sexpr-footprint/index.html); capture the exact format/version used in compatibility evidence |
| KiCad 10 CLI | [Version 10.0 CLI manual](https://docs.kicad.org/10.0/en/cli/cli.pdf); installed-version capability tests govern available commands, not master documentation |
| KiCad 10 symbol storage | [Official schematic editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html); packed/unpacked capability checked 2026-09-20; adapter fixtures establish supported operations |
| GitHub Models retirement | [Official 2026-07-01 announcement](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/); retirement dated 2026-07-30, checked 2026-09-20; not a supported provider target |
| IPC-7351 | [Official published contents/reference](https://www.ipc.org/TOC/IPC-7351.pdf); this entry is not a licensed full standard or approval of any derived land pattern |
| JEDEC | [Official standards organization](https://www.jedec.org/); each PDL entry must supply its exact applicable document/edition or manufacturer-specific evidence |

Additional plugin/IPC entry points checked 2026-10-05:

| Reference | Entry point and limits |
| --- | --- |
| KiCad IPC plugin/runtime boundaries | [Official add-on developer guide](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/); distinguishes running-GUI KiCad 10 PCB IPC from later headless/schematic capabilities and describes plugin registration/session variables; installed 10.0.6 capability tests govern acceptance |
| Official IPC Python bindings | [Version-selectable binding documentation](https://docs.kicad.org/kicad-python/); pin a released binding/dependency set in Phase 13.2 and use matching documentation; latest-development examples are not acceptance evidence |
| KiCad PCM package format | [Official addon packaging guide](https://dev-docs.kicad.org/en/addons/index.html); package ZIP, archive/repository metadata and layout; validate the schema shipped with the pinned KiCad build |
| KiCad 10 plugin lifecycle | [Version 10 PCM manual](https://docs.kicad.org/10.0/en/kicad/kicad.html#_installing_packages); local ZIP and repository installation plus managed update/removal |
| Pinned Python IPC preparation | [KiCad 10.0.6 plugin loader](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp) and [registration schema](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/api/schemas/api.v1.schema.json); requirements.txt preparation uses binary-only installation; min_version is not enforced by the schema's documented behavior |

These entry points establish traceable documentation sources, not final
package evidence. Every implementation/PDL review records exact edition or
build version, relevant section/table, access date, and retained engineering
values per STD-011/121.5. Runtime-specific facts and provider interfaces must
be rechecked when implementing their adapter; publication of this register
does not claim universal support or completion of the eight-package review.

# Appendix --- Historical Material

The unchanged v0.8/v0.8.x appendix extracted from v0.9.4 is available in
[the archive](history/BFT_PartSmith_Historical_Appendix_v0.9.4.md). It contains
superseded drafts and review logs, not active requirements. Current section IDs
are retained for stable references; reserved IDs 59–83 are not missing MVP work.
Earlier reviews remain available in [the review history](../docs/spec-consistency-review.md)
and [the v0.9.4 review](../docs/spec-consistency-review-v0.9.4.md).
