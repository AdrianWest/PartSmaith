# Historical Appendix — v0.8 / v0.8.x Material

This appendix is retained **for traceability only**.

**NON-NORMATIVE:** Nothing in this appendix is an implementation requirement
unless the same requirement is explicitly incorporated into the current
v0.9.3 normative sections above.

The appendix preserves prior v0.8/v0.8.x reviews, release notes, architecture
drafts, implementation specifications, contradiction-resolution logs, and
other historical material. Some entries intentionally contain obsolete or
superseded statements (including earlier OpenSCAD/VRML wording). Those
statements document what the specification said at that point in its history;
they are not current PartSmith requirements.

When a historical statement conflicts with the current specification, the
current v0.9.3 normative baseline controls.

---

# v0.8.8 Full-Spec Conflict Review

A full consistency review was performed against the v0.8.9 specification.
The following conflicts/ambiguities were found and resolved. No new
product feature is introduced by this revision.

## CR-013 — Standards section placement and release identity

**Finding:** The v0.8.9 standards-lock section was inserted inside the
PartSmith product-identity section, which made the document structure
ambiguous and interrupted the identity definition.

**Resolution:** The standards-lock material is now a standalone normative
section immediately after the product/repository identity. The release is
renamed v0.8.8.

## CR-014 — Standards-lock vs standards-review completion

**Finding:** The document said the standards review was both complete and
dependent on future PDL reference records being added.

**Resolution:** Distinguish the two states:

- **Standards baseline locked:** the external standards roles and
  implementation boundaries are fixed.
- **PDL entry complete:** each concrete supported package entry contains
  its applicable manufacturer/standard evidence before that package is
  production-supported.

The repository may begin implementation while individual PDL entries are
being completed.

## CR-015 — 3D output format scope

**Finding:** Earlier text described STEP as primary while also mentioning
VRML and other visualization formats.

**Resolution:** **STEP is mandatory for every PartSmith component that
requires a 3D model.** VRML is not part of the PartSmith output contract
and is removed from the normative specification. No alternate 3D format
may substitute for STEP.

## CR-016 — KiCad CLI vs IPC responsibilities

**Finding:** Both `kicad-cli` and IPC were described as validation paths
without a clear ownership boundary.

**Resolution:**

```text
Core deterministic validators
        ↓
PartSmith artifact validation

KiCad CLI adapter
        ↓
Headless KiCad compatibility/render/export checks

KiCad IPC adapter
        ↓
Live KiCad integration and interactive inspection
```

Neither KiCad interface replaces PartSmith's core deterministic
engineering validators.

## CR-017 — Direct native serialization vs KiCad validation

**Finding:** Native KiCad files may be generated directly, but some text
could be interpreted as requiring KiCad to generate them.

**Resolution:** PartSmith may directly serialize documented native formats.
KiCad is then used as an independent compatibility/round-trip check.
PartSmith remains responsible for deterministic artifact construction.

## CR-018 — IPC-7351 vs PDL land-pattern ownership

**Finding:** The standards hierarchy could be interpreted as allowing
IPC-derived geometry to override an existing PDL definition.

**Resolution:** PDL is the stored engineering rule set used by the
generator. The PDL entry must itself identify the authoritative evidence
and derivation basis. IPC is an input/reference methodology; it is not a
runtime override of a package-specific PDL entry.

## CR-019 — JEDEC applicability for every package

**Finding:** The specification requires an applicable JEDEC reference for
the eight package variants, but some package nomenclature may be
manufacturer-specific or may not map cleanly to one JEDEC outline.

**Resolution:** Each PDL variant must have either:

1. an applicable JEDEC/package-standard reference, **or**
2. authoritative manufacturer package/mechanical evidence with the
   absence of a directly applicable JEDEC outline explicitly recorded.

A JEDEC document shall never be fabricated or assumed solely from a
package family name.

## CR-020 — Purchase path and engineering release state

**Finding:** Purchased components are described as released and validated,
while the general component state machine is centered on AI generation.

**Resolution:** Purchased components enter PartSmith through a distinct
`PURCHASED_RELEASE` acquisition state referencing an immutable B.F.T.
release. They do not pass through the AI generation states and cannot
alter the AI build state machine.

The purchased release must still satisfy the B.F.T. released-component
contract.

## CR-021 — Purchase order vs component release

**Finding:** Commerce order state and engineering component-release state
could be conflated.

**Resolution:** They are separate state machines:

```text
Commerce:
CART → ORDER_CREATED → PAYMENT_AUTHORIZED → FULFILLING → FULFILLED
                              │
                              ├→ PAYMENT_FAILED
                              └→ CANCELLED/REFUNDED

Engineering:
B.F.T. RELEASED COMPONENT
          ↓
     Purchased by user
          ↓
     Delivered artifact
```

An order never changes the engineering release itself.

## CR-022 — Acquisition metadata and reproducibility

**Finding:** Acquisition metadata was described as manifest metadata,
while reproducibility could be read as hashing transaction-specific
data into the engineering artifact.

**Resolution:** Engineering artifact hashes cover the released component
contents and engineering manifest. Commerce transaction identifiers are
audit metadata and are not part of the deterministic component-content
hash unless a future commercial requirement explicitly requires it.

## CR-023 — AI generation of final symbol/footprint data

**Finding:** Historical sections still use language such as AI
generation of symbol/footprint data even though the architectural rule
says deterministic generators own final artifacts.

**Resolution:** Current normative behavior is:

```text
AI → structured proposal / evidence interpretation
       ↓
Component IR
       ↓
Deterministic generator
       ↓
Native KiCad artifact
```

Historical review text is retained for traceability, but current
implementation requirements take precedence.

## CR-024 — MVP package support vs architectural package families

**Finding:** Broad package-family references can still be mistaken for
MVP production support.

**Resolution:** Only these eight concrete variants are production
supported for the initial release:

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

All other package families are unsupported unless a future release adds
them explicitly.

## CR-025 — Validation PASS vs human review

**Finding:** Validation PASS and human approval could be interpreted as
equivalent.

**Resolution:**

```text
Validation PASS
    ≠
Human Approval
    ≠
Released Component
```

Blocking validation failures prevent approval. A component requiring
human review cannot be released until the required review is completed.

## CR-026 — Placement transform and STEP hash

**Finding:** Placement is editable metadata while STEP is immutable, but
the dependency/hash relationship was not always explicit.

**Resolution:** Placement metadata has its own canonical hash and is
included in the final component manifest. A placement change invalidates
the association/cross-validation/export-dependent outputs as defined by
the dependency graph, but does not rewrite the STEP geometry artifact.

## CR-027 — Standards source access vs reproducibility

**Finding:** A standards reference may be identified by URL/revision, but
the external source may later change or become inaccessible.

**Resolution:** The PDL/evidence record shall store the identifying
citation, revision, relevant section/table/figure, and extracted
engineering values needed for reproducibility. Redistribution of
copyrighted standards text is not required. The repository shall not
depend on live retrieval of a standards document during a deterministic
build.

## CR-028 — Repository name vs supplied GitHub URL

**Finding:** The specification names the repository `partsmith`, while
the supplied GitHub URL uses `PartSmaith`.

**Resolution:** The user's supplied GitHub repository is the target
repository for this implementation. The product/repository identity in
the engineering specification remains `PartSmith` / `partsmith`.
Repository hosting/URL spelling is treated as external hosting metadata,
not the product's canonical identifier.

# v0.8.9 Release Note

v0.8.9 is a correction-only revision. It resolves the 3D-output
ambiguity identified in the previous review.

Normative rule:

> **STEP is always required for PartSmith 3D component output. VRML is
> not a PartSmith output requirement and is removed from the contract.**

No other product feature is added or removed.

The next implementation version remains:

> **v0.9 — Executable PartSmith Repository Specification**

## CR-029 — 3D backend selection and clean installation

**Finding:** The prior specification described OpenSCAD in the 3D chain
without defining whether it was mandatory, while CadQuery was considered
separately. This could create an unnecessary multi-application
installation requirement.

**Resolution:** PartSmith defines a backend abstraction and supports
OpenSCAD and CadQuery as alternative implementation options. The
customer-facing application shall not require users to manually install
multiple CAD applications. The selected production backend and its
runtime dependencies shall be packaged and managed by PartSmith's
installer/runtime distribution.

# v0.8.1 Contradiction Review and Resolution Log

This release is a contradiction-correction pass over v0.8. The purpose
is to remove statements that could cause two competent implementers to
build incompatible behavior.

## CR-001 --- AI generation vs deterministic generation

**Contradiction:** The purpose section said the AI was responsible for
"interpretation and generation," while later architecture rules required
B.F.T. deterministic generators to construct final KiCad artifacts.

**Resolution:** AI may interpret source material and produce structured
proposals. Deterministic B.F.T. generators own final artifact
construction. AI output never bypasses the IR, generator contracts, or
deterministic validation.

**Severity:** BLOCKING architectural contradiction.

## CR-002 --- v0.8 implementation-ready vs v0.9 executable specification

**Contradiction:** v0.8 described itself as a direct build
specification, while later sections said v0.8 should merely recommend
that the next version become the implementation specification.

**Resolution:** v0.8.1 is the corrected direct build specification. v0.9
is explicitly the executable repository/bootstrap specification
containing committed schemas, code skeletons, migrations, generators,
validators, fixtures, and CI.

**Severity:** BLOCKING release-definition contradiction.

## CR-003 --- Build-state `HUMAN_REVIEW` vs `HUMAN_REVIEW_REQUIRED`

**Contradiction:** Validation results used `HUMAN_REVIEW`, while
build-state examples used both `HUMAN_REVIEW` and
`HUMAN_REVIEW_REQUIRED`.

**Resolution:** `HUMAN_REVIEW` is a validation result.
`HUMAN_REVIEW_REQUIRED` is the persisted build/release state. They are
related but not interchangeable.

**Severity:** HIGH.

## CR-004 --- 3D association timing

**Contradiction:** The footprint-generation pipeline appeared to insert
a 3D model reference before the independent 3D artifact had been
validated, while another rule required final association only after
validation.

**Resolution:** Footprint generation produces an artifact independent of
the 3D model. Final 3D association is a separate post-validation
finalization step. A placeholder may exist internally, but it has no
geometry authority.

**Severity:** HIGH.

## CR-005 --- 3D model "must align" before validation

**Contradiction:** The 3D section could be read as requiring alignment
as an input condition even though alignment is one of the outputs of
cross-validation.

**Resolution:** The 3D generator emits canonical geometry plus an
explicit placement transform. Cross-validation determines whether the
resulting associated placement aligns. B.F.T. does not force alignment
by editing either artifact.

**Severity:** HIGH.

## CR-006 --- Cross-validation assumes every STEP model contains visible pins/leads

**Contradiction:** "All pad centers ↔ corresponding lead/pin centers"
was stated as a universal requirement. Some package models may not
expose every electrical termination as a distinct 3D feature.

**Resolution:** The PDL declares expected 3D reference features.
Cross-validation uses model features when present and PDL/IR reference
coordinates when a physical feature is intentionally not represented.
Missing visual geometry is not automatically a failure.

**Severity:** HIGH.

## CR-007 --- Evidence-status enum was incomplete

**Contradiction:** Early text omitted `USER_OVERRIDE` and `UNKNOWN`,
while the frozen schema later required them.

**Resolution:** The normative value-status set is now centralized as
`DIRECT`, `DERIVED`, `STANDARD`, `USER_OVERRIDE`, `INFERRED`, `UNKNOWN`,
`AMBIGUOUS`, `CONFLICTING`, and `MISSING`.

**Severity:** MEDIUM.

## CR-008 --- Validation levels were promised but not defined

**Contradiction:** The document promised "at least five levels" but
initially defined only Levels 1 and 2, leaving the remaining levels
implicit.

**Resolution:** Five normative levels are now defined: Unit,
Schema/Domain, Artifact, Integration/Cross-Validation, and
System/Release.

**Severity:** MEDIUM.

## CR-009 --- Land-pattern precedence exceeded the explicit algorithm

**Contradiction:** Source precedence allowed manufacturer → IPC → PDL
resolution, but the algorithm only described manufacturer and
PDL-derived patterns.

**Resolution:** The land-pattern resolver now explicitly defines
manufacturer, IPC-derived, and PDL-derived paths and requires provenance
for the selected path.

**Severity:** HIGH.

## CR-010 --- Section numbering contained stale subsection labels

**Contradiction:** The document claimed normalized numbering but
retained stale labels such as `3.1` and `54.1`.

**Resolution:** These labels are corrected to `2.1`, `40.1`, and `40.2`.
The v0.8.1 document treats numbering as editorially normative so
implementation references remain stable.

**Severity:** LOW, but corrected.

## CR-011 --- MVP end-to-end flow vs AI-free first milestone

**Potential contradiction:** The MVP definition starts from a
manufacturer PDF, while the first implementation priority deliberately
excludes AI and begins from known-good structured IR.

**Resolution:** These are explicitly two different milestones. The
**engineering bootstrap** proves deterministic generation/validation
without AI. The **Tool 01 MVP** adds document extraction and AI
interpretation after that foundation is proven.

**Severity:** MEDIUM.

## CR-012 --- Placement editing vs immutable generated geometry

**Potential contradiction:** The viewer permits placement edits while
the STEP artifact is immutable after generation.

**Resolution:** Placement editing changes only explicit placement
metadata. It does not rewrite STEP geometry. Any changed placement is
hashable, diffable, reviewable, and causes the appropriate
validation/release dependencies to rerun.

**Severity:** NONE after clarification; retained as an explicit design
rule.

------------------------------------------------------------------------

# v0.8.2 Feature-Set Review and Recommendations

This release reviews the **existing feature set only**. It does not add
product features. The objective is to make the current scope coherent,
implementable, and measurable without allowing optional capabilities to
accidentally become MVP requirements.

## FS-001 --- Separate MVP requirements from supporting engineering infrastructure

**Recommendation:** Keep the existing feature set, but classify it into
three buckets:

### A. PartSmith user-facing MVP

These are the capabilities the user directly experiences:

-   PDF source ingestion
-   explicit page selection
-   source/evidence inspection
-   component extraction
-   Component IR review
-   package selection/review
-   symbol generation
-   footprint generation
-   independent 3D generation
-   2D footprint preview
-   3D placement/validation viewer
-   deterministic validation
-   human review/approval
-   native KiCad export

### B. Required engineering infrastructure

These are not optional product features; they are foundations required
to make the MVP trustworthy:

-   Component IR schema
-   PDL
-   evidence/provenance
-   coordinate/transform system
-   deterministic generators
-   validation engine
-   dependency graph
-   reproducible build system
-   audit trail
-   SQLite persistence
-   test fixtures
-   KiCad compatibility adapter

### C. Supporting capabilities that should remain secondary

The specification already contains these, but they should not be allowed
to delay the first deterministic end-to-end component:

-   multiple AI providers
-   multilingual translation
-   provider failover
-   caching
-   offline AI/local provider support
-   duplicate/near-duplicate detection
-   broad standards integration
-   full API exposure
-   extensive rollback tooling
-   broad document-format expansion

**No new capability is introduced by this classification.**

------------------------------------------------------------------------

## FS-002 --- Narrow the first user-visible package scope without removing package support from the architecture

The document currently lists a very broad package-family set while the
first PDL/golden corpus contains eight concrete variants.

**Recommendation:** Treat the eight existing variants as the only **MVP
production-supported package set**:

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

The broader package list remains an architectural expansion target, not
an MVP promise.

This prevents the phrase "support QFP, BGA, LGA, DFN, connectors, TO
packages, etc." from being interpreted as an immediate implementation
commitment.

------------------------------------------------------------------------

## FS-003 --- Make the 3D viewer a validation tool, not a general CAD feature

The current feature set is appropriate, but it risks growing into a
general 3D editor.

**Recommendation:** Freeze the MVP viewer around:

-   view/navigation
-   footprint/model overlay
-   measurement
-   reference axes/origin
-   pin-1 highlighting
-   discrepancy visualization
-   explicit placement transform inspection/editing

Do not treat arbitrary mesh editing, CAD remodeling, or general-purpose
3D authoring as part of PartSmith.

This preserves the existing viewer feature set while preventing scope
drift.

------------------------------------------------------------------------

## FS-004 --- Treat AI provider breadth as an implementation concern, not a reason to expand the product workflow

The current specification names OpenAI, Anthropic, Google Gemini, and
GitHub Copilot.

**Recommendation:** Keep the provider abstraction, but make **one
provider sufficient for MVP acceptance**.

The other adapters remain supported architecture targets and
contract-test targets when implemented.

MVP success must therefore mean:

``` text
one working provider
+
provider-independent normalized result
+
same deterministic downstream pipeline
```

rather than requiring simultaneous production readiness for every
provider.

------------------------------------------------------------------------

## FS-005 --- Do not make every listed document-intelligence capability an MVP gate

The specification contains a strong and valuable difficult-document
feature set:

-   scanned PDFs
-   OCR
-   multilingual documents
-   diagram-heavy documents
-   image tables
-   symbol discovery
-   page classification
-   conflict detection
-   translation

**Recommendation:** Keep these capabilities in PartSmith, but establish
a progression:

``` text
MVP acceptance:
PDF → evidence → reviewed IR

Then:
scanned/OCR
multilingual
diagram-heavy
translation
difficult-document edge cases
```

The deterministic component-building path should not be considered
incomplete merely because the AI cannot yet solve every difficult
document class.

------------------------------------------------------------------------

## FS-006 --- Keep validation breadth; prioritize validation depth

The current feature set has many validators:

-   schema
-   evidence
-   topology
-   electrical
-   symbol
-   footprint
-   3D
-   mapping
-   cross-artifact
-   KiCad
-   manifest
-   reproducibility

**Recommendation:** Do not remove any of these categories from the
architecture. However, MVP release should require **complete correctness
for the supported package corpus**, rather than shallow support across
every conceivable package.

This is particularly important for:

-   pin mapping
-   pin 1
-   package topology
-   land pattern
-   coordinate transforms
-   3D placement
-   KiCad compatibility

------------------------------------------------------------------------

## FS-007 --- Keep the current export/install feature set, but make "portable package" the primary MVP deliverable

The specification supports:

-   standalone component package
-   project-local library installation
-   library-table updates
-   backup
-   rollback
-   atomic export

**Recommendation:** Define the portable generated component package as
the primary MVP output.

Project-local installation should remain part of PartSmith, but
library-table mutation should not become a prerequisite for proving that
the builder works.

The core success criterion remains:

``` text
approved component
→ portable native KiCad library package
```

------------------------------------------------------------------------

## FS-008 --- Keep API architecture without making the API a product dependency

The specification correctly says the API is optional for the desktop
MVP.

**Recommendation:** Preserve that decision consistently.

The internal service boundaries should be typed and API-ready, but the
first usable PartSmith build should not require a network service layer.

This prevents architecture from becoming product overhead.

------------------------------------------------------------------------

## FS-009 --- Keep duplicate detection informational and out of the critical build path

The current duplicate/near-duplicate feature is useful but is not
necessary to prove component construction.

**Recommendation:** Keep it exactly as an informational review
capability. It should never block:

``` text
IR → generators → validators → approval
```

unless a separate explicit duplicate policy is later adopted.

------------------------------------------------------------------------

## FS-010 --- Keep standards support constrained to evidence and package/land-pattern resolution

The existing standards feature is appropriately scoped, but the
standards adapter could otherwise become a large independent subsystem.

**Recommendation:** For PartSmith, standards support should remain
limited to the existing roles:

-   package geometry
-   package topology
-   land-pattern methodology
-   terminology/constraints

Do not turn PartSmith into a general standards-management system.

------------------------------------------------------------------------

## FS-011 --- Preserve the current feature set but eliminate duplicate requirements in implementation planning

The specification repeats several capabilities in multiple sections,
especially:

-   3D viewer
-   validation
-   footprint generation
-   3D generation
-   golden testing
-   KiCad integration
-   export

**Recommendation:** Treat the normative section and the implementation
backlog as the authoritative sources for feature commitment. Repeated
descriptive sections should explain the capability but must not
introduce additional requirements.

This prevents accidental scope growth when the same feature appears with
slightly different wording.

------------------------------------------------------------------------

## FS-012 --- Make "production-ready" mean supported-corpus correctness

The current acceptance language can be read as requiring the builder to
be broadly correct for arbitrary components.

**Recommendation:** Define production readiness for PartSmith as:

``` text
Supported package
+
sufficient authoritative evidence
+
valid Component IR
+
all blocking validators PASS
+
required human review complete
+
KiCad compatibility PASS
+
reproducibility PASS
```

For unsupported packages or insufficient evidence, the correct result
remains:

``` text
NOT_GENERATABLE
```

This is not a reduction in engineering rigor; it makes the existing
failure policy operationally meaningful.

------------------------------------------------------------------------

# v0.8.3 Component Acquisition Feature

This release adds exactly **one product feature** to the v0.8.2 feature
set:

> **When B.F.T. identifies a component, the user may choose to build it
> with the AI workflow or purchase an already-built B.F.T. component
> from B.F.T.**

This is an acquisition-path feature. It does not change the engineering
authority model, the Component IR, PDL, deterministic generators,
validation system, or approval requirements.

## ACQ-001 --- Acquisition Choice

PartSmith shall present an explicit choice, when applicable:

``` text
Component identified
        │
   ┌────┴────┐
   │         │
 BUILD      PURCHASE
 WITH AI    FROM B.F.T.
   │         │
   ▼         ▼
AI + IR    B.F.T. Component
Pipeline   Package
   │         │
   └────┬────┘
        ▼
Validated KiCad Component
```

The purchase option shall not be presented as available unless B.F.T.
has a matching purchasable component offering for the requested
component/package variant.

## ACQ-002 --- AI Build Path

The existing AI build workflow remains unchanged:

``` text
Source
↓
Evidence
↓
Component IR
↓
PDL
↓
Deterministic Generators
↓
Validation
↓
Human Review / Approval
↓
Export
```

The acquisition feature does not allow AI output to bypass any existing
engineering validation.

## ACQ-003 --- Purchased Component Path

A purchased B.F.T. component shall be delivered as a versioned, native
KiCad component package containing the artifacts required by the
purchased offering.

Where applicable, the package shall identify:

-   component identity
-   manufacturer
-   manufacturer part number
-   package variant
-   B.F.T. component/release version
-   supported KiCad version
-   symbol
-   footprint
-   3D model
-   manifest
-   validation/release metadata

## ACQ-004 --- Common Component Contract

AI-generated and purchased components shall conform to the same core
B.F.T. component contract wherever the purchased offering supplies the
corresponding artifacts.

The acquisition method shall never alter:

-   pin numbering
-   pin mapping
-   package identity
-   coordinate conventions
-   artifact relationships
-   validation semantics
-   provenance rules
-   release-state rules

## ACQ-005 --- Purchased Components Are Not a Validation Bypass

A purchased component is a B.F.T. released product, not an instruction
to trust an unvalidated artifact.

Purchased components shall originate from B.F.T.'s released component
inventory and carry the applicable release/validation identity.

A purchased component shall not be allowed to enter the user's project
as an untracked or unverifiable artifact.

## ACQ-006 --- Acquisition Availability

PartSmith shall distinguish at least these states:

``` text
PURCHASE_AVAILABLE
PURCHASE_NOT_AVAILABLE
PURCHASE_SELECTED
AI_BUILD_SELECTED
```

If purchase is unavailable, the AI path remains available when the
component is otherwise generatable.

If AI generation is not possible but a matching purchased component is
available, the purchase path remains available.

## ACQ-007 --- Component Identity Matching

A purchase offer shall be associated with an exact component identity,
including the applicable manufacturer part number and package variant.

A generic family match such as:

``` text
QFN-16
```

shall not be sufficient to represent an exact purchasable component when
the component identity or package variant could differ.

The purchase path shall use the same exact-identity discipline already
required by Component IR and PDL.

## ACQ-008 --- Purchased Component Versioning

A purchased component shall have an immutable release identity.

Updates to a purchased component shall create a new release/version
rather than silently changing an already-released package.

The user's installed component shall remain identifiable by its
purchased B.F.T. release.

## ACQ-009 --- Acquisition Metadata

The acquisition method shall be recorded in build/release metadata where
applicable:

``` yaml
acquisition:
  method: AI_BUILD | PURCHASE
  product_id:
  product_version:
  component_identity:
  package_variant:
```

For an AI-built component, `method` is `AI_BUILD`.

For a purchased component, `method` is `PURCHASE`.

The acquisition metadata is metadata about how the component was
obtained; it does not replace engineering provenance.

## ACQ-010 --- Purchase Boundary

The commercial purchase mechanism shall remain outside the deterministic
component-generation core.

The engineering architecture shall expose a clean boundary:

``` text
PartSmith
  │
  ├── AI Build
  │
  └── Purchase
          │
          ▼
   B.F.T. Component Store
```

Payment processing, account management, checkout, taxation, fulfillment,
and other commerce implementation details are outside the PartSmith
engineering core unless separately specified.

## ACQ-011 --- Portable Purchased Package

A purchased component shall be usable independently of the purchase
transaction after successful delivery.

The delivered engineering artifact shall not require the user to repeat
the purchase process merely to load the component into KiCad.

## ACQ-012 --- Purchase and Export Separation

Purchase and export are separate concepts:

``` text
Purchase
   ↓
Obtain released component
   ↓
Install/use in KiCad

AI Build
   ↓
Generate/review/approve
   ↓
Export/install in KiCad
```

The acquisition feature shall not weaken the existing atomic export,
compatibility, or rollback rules.

## ACQ-013 --- No New Engineering Authority

The B.F.T. store/catalog shall not become an engineering authority.

The engineering authority remains:

``` text
Authoritative Evidence
        +
Component IR
        +
PDL
        +
Deterministic Generation
        +
Deterministic Validation
        +
Human Approval
```

The store identifies and distributes released components; it does not
redefine their engineering truth.

# v0.8.8 Release Note

v0.8.8 is a full-spec conflict-review revision. It adds no new product capability.
It records the final KiCad/IPC/JEDEC implementation baseline and makes
those standards/reference responsibilities explicit before v0.9
repository bootstrap.

The acquisition/e-commerce boundary from v0.8.6 remains unchanged.

The next implementation version remains:

> **v0.9 — Executable PartSmith Repository Specification**

# v0.8.3 Full-Spec Review

The complete v0.8.2 specification was reviewed with the new acquisition
feature in mind. The existing engineering architecture remains coherent.

The review produces the following decisions.

## REVIEW-001 --- Core architecture remains unchanged

No change is required to:

-   Component IR
-   PDL
-   evidence hierarchy
-   provenance graph
-   coordinate systems
-   independent footprint/3D generation
-   deterministic validation
-   cross-validation
-   human review
-   reproducible builds
-   KiCad compatibility architecture

The new feature is an additional path into the released-component
experience.

## REVIEW-002 --- MVP feature set is updated by one feature

The PartSmith user-facing MVP now includes:

-   PDF source ingestion
-   explicit page selection
-   source/evidence inspection
-   component extraction
-   Component IR review
-   package selection/review
-   symbol generation
-   footprint generation
-   independent 3D generation
-   2D footprint preview
-   3D placement/validation viewer
-   deterministic validation
-   human review/approval
-   native KiCad export
-   **AI build vs. B.F.T. purchase choice**

No other product feature is added by this release.

## REVIEW-003 --- Purchase is a parallel acquisition path, not a second generator

The purchase path must not create a competing engineering pipeline.

``` text
                         Component
                            │
                 ┌──────────┴──────────┐
                 │                     │
             AI BUILD              PURCHASE
                 │                     │
        Interpretation + IR       Released B.F.T.
                 │                 Component
                 │                     │
        Deterministic Build           │
                 │                     │
                 └──────────┬──────────┘
                            ▼
                    Usable KiCad
                     Component
```

The purchased component is already a released engineering artifact.

## REVIEW-004 --- Acquisition does not change NOT_GENERATABLE semantics

`NOT_GENERATABLE` continues to mean that B.F.T. cannot safely generate
the requested component from the available evidence.

If a purchasable released component exists, the user may still purchase
it.

Therefore:

``` text
AI path:       NOT_GENERATABLE
Purchase path: AVAILABLE
```

is a valid state.

Likewise:

``` text
AI path:       GENERATABLE
Purchase path: NOT_AVAILABLE
```

is valid.

The two availability states are independent.

## REVIEW-005 --- Acquisition does not change release gates

AI-generated components still require all existing release gates.

Purchased components are distributed only from the released B.F.T.
component inventory.

The purchase mechanism must never be used to mark an unvalidated AI
build as approved.

## REVIEW-006 --- Acquisition must participate in reproducibility and auditability

For purchased components, reproducibility applies to the released B.F.T.
package itself.

For AI-built components, the existing reproducible-build inputs remain
authoritative.

Acquisition metadata is included in the manifest/audit trail but does
not replace the engineering input hashes.

## REVIEW-007 --- Existing UI needs one additional decision point

The existing workflow:

``` text
Source → Extract → Interpret → Generate → Validate → Review → Export
```

is extended only where a matching purchased component exists:

``` text
Source / Component Identification
              │
        Acquisition Choice
          ┌───┴────┐
          │        │
        Build   Purchase
          │        │
          ▼        ▼
       Existing  Released
       workflow  component
          │        │
          └───┬────┘
              ▼
          Use in KiCad
```

The purchase choice should appear after B.F.T. has enough identity
information to determine whether a matching released component exists.

## REVIEW-008 --- CLI/API impact is intentionally minimal

The existing build APIs remain valid.

The acquisition boundary may expose:

``` text
GET /components/{identity}/availability
POST /components/{identity}/purchase
```

and corresponding CLI behavior may be added when the commerce
integration is implemented.

These are acquisition interfaces, not replacements for the existing
build APIs.

They should not be required for the deterministic engineering bootstrap.

## REVIEW-009 --- Purchased component identity must be exact

The existing Component Variant Identity rules are sufficient.

No new identity system is required.

Purchase lookup shall reuse the same identity fields rather than
inventing a separate commercial naming system.

## REVIEW-010 --- Feature-set conclusion

The full review confirms that the existing architecture remains
appropriate.

The only product feature added in v0.8.3 is:

> **User choice between building the component with AI and purchasing
> the component from B.F.T.**

No additional feature expansion is recommended in this release.

# Feature-Set Decision

After reviewing the complete v0.8.2 specification, **one explicitly
requested product feature is added in v0.8.3: Component Acquisition
Choice**.

No other major product feature needs to be added. The existing
engineering feature set remains sufficient for PartSmith.

The primary recommendation is to **freeze the feature set and reduce
ambiguity about priority**, rather than continuing to expand it.

The implementation target should therefore be:

``` text
                    TOOL 01
                       │
             ┌─────────┴─────────┐
             │                   │
       Understand Source     Build Component
             │                   │
             ▼                   ▼
        Evidence + IR      Symbol + Footprint
                                 +
                              3D Model
                                 │
                                 ▼
                         Deterministic Validation
                                 │
                                 ▼
                         Human Review / Approval
                                 │
                                 ▼
                         Native KiCad Export
```

The eight existing PDL variants form the first supported production
corpus. Everything else in the current architecture remains available as
infrastructure or subsequent implementation depth without becoming a new
feature commitment.

# v0.8.1 Consistency Rules

The following rules take precedence if an older paragraph elsewhere in
this document is accidentally read differently:

1.  **AI interprets; deterministic B.F.T. generators construct final
    artifacts.**
2.  **Component IR + PDL + authoritative evidence are the engineering
    inputs.**
3.  **Footprint and 3D generation are independent.**
4.  **Cross-validation compares artifacts; it never repairs them
    silently.**
5.  **`HUMAN_REVIEW` is a validation result; `HUMAN_REVIEW_REQUIRED` is
    a build state.**
6.  **Final 3D association occurs only after independent artifact
    validation and cross-validation.**
7.  **Placement metadata is separate from STEP geometry.**
8.  **Manufacturer-specific land-pattern evidence outranks generic
    derivation when applicable.**
9.  **No inferred/unknown/ambiguous/conflicting/missing release-critical
    value may silently become approved.**
10. **v0.8.3 is the feature-set-refined build specification with
    Component Acquisition; v0.9 is the first executable repository
    implementation specification.**

------------------------------------------------------------------------

# Review of v0.8 --- Required Corrections Incorporated in v0.8

The prior architecture was directionally sound, but it was **not yet
implementation-safe**. The following issues are explicitly corrected in
v0.8.

## Critical issues found

1.  **Section numbering was inconsistent.**\
    v0.5 contained duplicated and stale section numbers such as `3.1`,
    `54.1`, and `42.1`. v0.8 normalizes the primary section sequence and
    removes stale version references.

2.  **The PDL was described but not specified as a first-class
    subsystem.**\
    v0.8 defines the Package Definition Library as a versioned,
    schema-controlled engineering database with package-family, variant,
    topology, mechanical, land-pattern, 3D, and validation data.

3.  **Package identity was under-specified.**\
    A generic package name such as `QFN-16` is not sufficient. v0.8
    requires an unambiguous package variant identity, including body
    size, pitch, pin count, topology, and manufacturer-specific
    deviations where applicable.

4.  **Electrical pin semantics needed stronger boundaries.**\
    Standards and package geometry must never be allowed to invent
    electrical behavior. Pin electrical type is a manufacturer-evidence
    problem, with explicit `UNKNOWN` and `HUMAN_REVIEW` states.

5.  **User overrides were not sufficiently controlled.**\
    v0.8 makes overrides explicit, typed, attributable, reviewable,
    hashable, and distinct from source-derived values. An override
    cannot silently replace provenance.

6.  **Generated-artifact ownership was ambiguous.**\
    v0.8 defines exactly which inputs each generator may consume. A
    generated footprint may not become the geometric source for the 3D
    generator, and vice versa.

7.  **The 3D model validation plan needed a stronger definition of what
    can actually be proven.**\
    v0.8 separates geometric correctness, placement correctness, and
    visual plausibility. A visually attractive model is not evidence of
    dimensional correctness.

8.  **KiCad compatibility needed versioned validation rather than a
    generic "KiCad-compatible" claim.**\
    v0.8 requires a supported KiCad-version matrix and actual
    parse/open/round-trip tests. Native file formats are treated as
    version-sensitive artifacts.

9.  **Units and coordinate transforms needed to be explicit at every
    boundary.**\
    v0.8 requires millimeter-normalized internal geometry, explicit
    source units, explicit transforms, and no implicit unit conversion.

10. **Evidence conflict handling needed a formal decision model.**\
    v0.8 distinguishes direct evidence, derivation, inference, conflict,
    ambiguity, and absence, and defines which states block release.

11. **Reproducibility needed canonical serialization.**\
    Hashes alone are insufficient if serialization order is
    nondeterministic. v0.8 requires canonical JSON/YAML-like
    representations before hashing.

12. **The acceptance criteria needed to distinguish architecture
    readiness from MVP implementation readiness.**\
    v0.8 separates architecture acceptance from implementation exit
    criteria.

13. **Security and privacy boundaries needed to include source-document
    handling.**\
    Datasheets may contain proprietary or customer-supplied material.
    v0.8 defines provider disclosure, retention expectations,
    local-processing options, and redaction requirements.

14. **The test strategy needed negative tests for "wrong but
    syntactically valid" components.**\
    v0.8 makes semantic fault injection mandatory, including mirrored
    packages, plausible-but-wrong pin maps, wrong package variants, and
    incorrect 3D transforms.

15. **The build state machine needed artifact dependency rules.**\
    v0.8 defines what may be regenerated independently and what
    downstream states must be invalidated when an upstream value
    changes.

These corrections are architectural requirements, not optional
enhancements.

------------------------------------------------------------------------

## 1. Purpose

PartSmith is the first named B.F.T. tool and is an **AI-driven component
builder**.

The user provides:

1.  A component datasheet, preferably as a PDF.
2.  The page number(s) containing the relevant package, pinout,
    mechanical, and/or electrical information.
3.  Optionally, additional manufacturer documentation or images.

B.F.T. analyzes the supplied information and generates a complete KiCad
component consisting of:

-   Schematic symbol
-   PCB footprint
-   3D model
-   Component metadata
-   Correct relationships between symbol pins and footprint pads
-   A native KiCad library representation

The generated files must be usable by KiCad without conversion to
another EDA format.

### Core objective

> **Turn authoritative component documentation into a complete,
> KiCad-compatible component library item.**

The AI is responsible for interpretation and for producing structured
proposals where useful. B.F.T.'s deterministic generators construct the
final KiCad artifacts, and deterministic validation decides whether
those artifacts are acceptable. AI output can never by itself constitute
an accepted component.

------------------------------------------------------------------------

# 59. Architecture & Data Model Specification --- v0.8

This version establishes the engineering architecture required before
implementation of the MVP begins.

## 42.1 System Architecture

``` text
                         AUTHORITATIVE SOURCES
                                  │
                                  ▼
                           DOCUMENT ENGINE
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
                Text/OCR                  Images/Diagrams
                     │                         │
                     └────────────┬────────────┘
                                  ▼
                           EVIDENCE ENGINE
                                  │
                                  ▼
                            COMPONENT IR
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
           SYMBOL               PACKAGE              3D
             IR                  PDL              Definition
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
            Symbol Engine   Footprint Engine   3D Engine
                 │                │                │
                 ▼                ▼                ▼
             .kicad_sym      .kicad_mod       OpenSCAD / CadQuery → STEP
                 │                │                │
                 └────────────────┼────────────────┘
                                  ▼
                         VALIDATION ENGINE
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
            Syntax           Connectivity          Geometry
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                         3D PLACEMENT VIEWER
                                  │
                                  ▼
                           HUMAN REVIEW
                                  │
                                  ▼
                          APPROVED COMPONENT
```

## 42.2 Design Principle

> AI interprets. B.F.T. represents. Deterministic generators construct.
> Deterministic validators decide. Humans resolve ambiguity.

AI must never be the final authority for whether a generated component
is production-ready.

------------------------------------------------------------------------

# 60. Component IR Specification

The Component IR is the central contract between document
interpretation, package knowledge, generators, validation, review, and
export.

## 43.1 Required IR domains

``` text
Component IR
├── Identity
├── Electrical
├── Pins
├── Package
│   ├── Mechanical Definition
│   ├── Pin Topology
│   └── Land Pattern Definition
├── Symbol
├── 3D Geometry
├── Evidence
├── Standards
├── Confidence / Evidence Status
├── Validation
├── Build Metadata
└── Revision Metadata
```

## 43.2 Identity

``` yaml
identity:
  manufacturer:
  manufacturer_part_number:
  family:
  description:
  datasheet_revision:
  datasheet_date:
  package_name:
  package_code:
```

## 43.3 Electrical model

Electrical information shall remain independent from physical package
information.

``` yaml
electrical:
  operating_voltage:
  functions:
  notes:
```

No package standard may be used to infer electrical behavior.

## 43.4 Pin model

``` yaml
pin:
  number: 5
  name: EN
  electrical_type: input
  function: enable
  active_low: false
  alternate_functions: []
  exposed_pad: false
  no_connect: false
  topology_position:
    side: left
    sequence: 3
```

Pin topology is separate from electrical semantics.

## 43.5 Package model

``` yaml
package:
  family: QFN
  variant: QFN-16-3x3-0.5P

  mechanical:
    body_length_mm: 3.0
    body_width_mm: 3.0
    body_height_mm: 0.85

  topology:
    pin_count: 16
    pitch_mm: 0.5
    numbering_scheme: counter_clockwise
    pin1_orientation: top_left

  land_pattern:
    source_type: manufacturer_recommended
    pad_length_mm:
    pad_width_mm:
    pad_spacing_mm:
    thermal_pad:
      enabled: true
      length_mm:
      width_mm:
```

## 43.6 Symbol model

The IR shall contain symbol intent, not raw KiCad serialization.

``` yaml
symbol:
  reference: U
  units:
  graphics:
  pins:
  fields:
```

## 43.7 3D model

``` yaml
model_3d:
  format: STEP
  geometry_source: PDL
  body:
    length_mm:
    width_mm:
    height_mm:
  pin1_marker:
  placement:
    offset_mm:
      x:
      y:
      z:
    rotation_deg:
      x:
      y:
      z:
```

------------------------------------------------------------------------

# 61. Evidence and Provenance Model

## 44.1 Evidence object

``` yaml
evidence:
  id: E-000123
  source:
    document: TPS62130.pdf
    revision: Rev F
    page: 34
    region: "Package Drawing"
  evidence_type: drawing_dimension
  extracted_value: "3.00 ± 0.10 mm"
  interpretation:
    nominal_mm: 3.00
    min_mm: 2.90
    max_mm: 3.10
```

## 44.2 Evidence types

``` text
DATASHEET_TEXT
OCR_TEXT
TABLE
PACKAGE_DRAWING
BLOCK_DIAGRAM
PINOUT_DIAGRAM
LAND_PATTERN
MANUFACTURER_CAD
MANUFACTURER_WEB_DOCUMENT
JEDEC_STANDARD
IPC_STANDARD
USER_PROVIDED_VALUE
DERIVED_VALUE
```

## 44.3 Provenance graph

``` text
Source
  ↓
Evidence
  ↓
IR value
  ↓
Generated artifact
  ↓
Validation result
```

The UI shall be able to answer why an important value exists and show
the supporting evidence and derivation.

------------------------------------------------------------------------

# 62. Package Model: Mechanical Geometry vs. Land Pattern

A package definition shall explicitly distinguish:

``` text
PACKAGE MECHANICAL GEOMETRY
            +
PIN TOPOLOGY
            +
LAND PATTERN
```

These are related but not interchangeable.

A package's mechanical dimensions shall not automatically be treated as
a PCB land pattern.

Manufacturer-recommended land patterns take precedence when available.

------------------------------------------------------------------------

# 63. Package Topology Specification

Every supported PDL package shall define expected topology:

-   Pin count
-   Side distribution
-   Pitch
-   Numbering direction
-   Corner behavior
-   Staggering
-   Exposed pads
-   Mechanical pin locations
-   Pin 1 location
-   Symmetry/mirroring rules

Example:

``` text
QFN-16

       1  2  3  4
    ┌─────────────┐
 16 │             │ 5
 15 │             │ 6
 14 │             │ 7
 13 │             │ 8
    └─────────────┘
      12 11 10  9
```

Topology validation shall occur before artifact generation.

------------------------------------------------------------------------

# 64. Coordinate-System Specification

B.F.T. shall explicitly model coordinate systems.

## 47.1 Required systems

``` text
Component coordinate system
Footprint coordinate system
3D model coordinate system
PCB coordinate system
KiCad display coordinates
```

## 47.2 Required conventions

The specification shall define:

-   Origin
-   X direction
-   Y direction
-   Z direction
-   Positive rotation direction
-   Units
-   Pin 1 orientation
-   Mirroring convention
-   Model-to-footprint transform

## 47.3 Reference geometry

The viewer and validation engine shall display, where useful:

``` text
PCB reference plane
Package center
Footprint origin
3D model origin
Pad centers
3D pin centers
Pin 1 marker
Body bounding box
```

------------------------------------------------------------------------

# 65. Independent Generator Interfaces

Generators consume the Component IR but do not consume each other's
generated artifacts as authoritative input.

## 48.1 Footprint generator

Input:

``` text
Component IR
Package PDL
Land Pattern Definition
Authoritative evidence
```

Output:

``` text
Native .kicad_mod
```

## 48.2 3D generator

Input:

``` text
Component IR
Package PDL
Mechanical Definition
Authoritative evidence
```

Output:

``` text
OpenSCAD source
STEP model
Placement metadata
```

## 48.3 Symbol generator

Input:

``` text
Component IR
Electrical pin model
Symbol conventions
```

Output:

``` text
Native .kicad_sym
```

------------------------------------------------------------------------

# 66. Deterministic Validation Specification

Validation shall be deterministic wherever a mathematical or syntactic
rule can be used.

## 49.1 Categories

``` text
Schema
Source/Evidence
Package topology
Symbol
Footprint
Pin mapping
3D geometry
Footprint/3D cross-validation
KiCad compatibility
PCB connectivity
Visual regression
```

## 49.2 Result states

``` text
PASS
FAIL
WARN
HUMAN_REVIEW
NOT_GENERATABLE
```

WARN shall never silently become PASS.

## 49.3 Package-aware tolerances

Tolerances shall be configurable in the PDL.

``` yaml
validation:
  xy_pin_pad_tolerance_mm: 0.01
  package_center_tolerance_mm: 0.01
  rotation_tolerance_deg: 0.1
  height_tolerance_mm: 0.02
```

These are placeholders until calibrated against known-good components.

------------------------------------------------------------------------

# 67. Footprint ↔ 3D Cross-Validation

This is a primary B.F.T. differentiator.

## 50.1 Checks

At minimum:

-   Pad 1 ↔ 3D pin 1
-   All pad centers ↔ corresponding 3D lead/pin reference features, when
    those features are represented by the model
-   Package center
-   Body dimensions
-   Body orientation
-   Pin 1 orientation
-   Model origin
-   Model scale
-   Z height
-   Thermal/exposed pad alignment, when represented by the model;
    otherwise validate from independent package/placement definitions
-   Mirroring
-   Rotation

The PDL shall declare which 3D reference features are expected for each
package family. A model is not considered incorrect merely because an
internal or bottom-side electrical feature is not visually modeled; in
that case the corresponding cross-check must use the PDL/IR coordinate
definition rather than an absent STEP surface.

## 50.2 Mathematical validation

``` text
Footprint Pad 1:
  X = 0.000 mm
  Y = -1.000 mm

3D Pin 1:
  X = 0.002 mm
  Y = -1.001 mm

ΔX = 0.002 mm
ΔY = 0.001 mm

Result:
  PASS
```

## 50.3 Fault injection

The functional suite shall deliberately introduce:

-   XY offset
-   Z offset
-   90° rotation
-   180° rotation
-   Mirror
-   Incorrect scale
-   Pin 1 mismatch

The validator must detect each.

## 50.4 No silent correction

When cross-validation fails, B.F.T. shall report the mismatch and likely
causes. It shall not automatically alter either artifact merely to force
alignment.

------------------------------------------------------------------------

# 68. 3D Viewer / Placement Validation Architecture

The 3D viewer is part of PartSmith.

The first implementation shall provide:

-   Rotate
-   Pan
-   Zoom
-   Isometric view
-   Top/front/side views
-   Footprint + model overlay
-   Pads visibility
-   Silkscreen visibility
-   Courtyard visibility
-   Fabrication geometry visibility
-   Pin 1 highlight
-   Origin/axis display
-   Measurement
-   X/Y/Z model offset controls
-   X/Y/Z rotation controls
-   Height inspection
-   Pad/pin highlighting
-   Bounding-box display
-   Cross-section or clipping where practical

Placement changes shall be stored as explicit placement metadata and
remain distinguishable from model geometry.

Initial scope is component + footprint + 3D model. Full-board context is
future scope.

------------------------------------------------------------------------

# 69. Build State Machine

``` text
SOURCE_RECEIVED
      ↓
SOURCE_ANALYZED
      ↓
EVIDENCE_COLLECTED
      ↓
IR_BUILT
      ↓
IR_VALIDATED
      ↓
PACKAGE_IDENTIFIED
      ↓
FOOTPRINT_GENERATED
      ↓
3D_GENERATED
      ↓
SYMBOL_GENERATED
      ↓
ARTIFACT_VALIDATION
      ↓
CROSS_VALIDATION
      ↓
HUMAN_REVIEW_REQUIRED
      ↓
APPROVED
      ↓
EXPORTED
```

Failure states:

``` text
EXTRACTION_FAILED
EVIDENCE_CONFLICT
IR_INVALID
PACKAGE_UNSUPPORTED
NOT_GENERATABLE
ARTIFACT_VALIDATION_FAILED
CROSS_VALIDATION_FAILED
HUMAN_REVIEW_REQUIRED
```

Regeneration shall return to the appropriate earlier state.

------------------------------------------------------------------------

# 70. NOT_GENERATABLE State

`NOT_GENERATABLE` is a deliberate engineering result, not an application
error.

Example:

``` text
NOT GENERATABLE

The available documentation contains:
- pin names
- pin numbers
- package name

but does not contain:
- package dimensions
- mechanical drawing
- recommended land pattern

B.F.T. cannot safely create a production footprint.
```

The system shall explain what additional evidence could resolve the
condition.

------------------------------------------------------------------------

# 71. Build Reproducibility

A build shall be reproducible from:

``` text
Source documents
+
Evidence selections
+
Component IR
+
PDL version
+
B.F.T. version
+
Generator version
+
Configuration
+
AI provider/model identifiers
+
User-approved overrides
```

------------------------------------------------------------------------

# 72. Content Hashing and Artifact Identity

B.F.T. should compute cryptographic hashes for:

``` text
Source PDF
Evidence package
Component IR
PDL definition
Generated symbol
Generated footprint
OpenSCAD source
STEP model
Manifest
```

Example:

``` yaml
hashes:
  source_sha256:
  evidence_sha256:
  component_ir_sha256:
  pdl_sha256:
  symbol_sha256:
  footprint_sha256:
  openscad_sha256:
  step_sha256:
  manifest_sha256:
```

------------------------------------------------------------------------

# 73. Revision and Change Tracking

When a component is regenerated, B.F.T. shall compare the new IR and
artifacts with the previous approved version.

Example:

``` text
TPS62130RGTR
Datasheet: Rev A → Rev B

Changes:
  Pin mapping:      UNCHANGED
  Body height:      0.80 → 0.85 mm
  Thermal pad:      1.60 → 1.70 mm
  Footprint:        CHANGED
  3D model:         CHANGED
  Symbol:           UNCHANGED
```

The system shall identify which engineering domains changed.

------------------------------------------------------------------------

# 74. AI Provider Boundary

AI providers are interchangeable interpretation services, not
engineering authorities.

``` text
OpenAI
Anthropic
Gemini
Copilot
Future/local model
       │
       ▼
Provider Adapter
       │
       ▼
Normalized AI Result
       │
       ▼
Evidence / IR Engine
```

AI may propose extracted values, interpretations, package
classifications, symbol intent, ambiguity explanations, and candidate
corrections.

B.F.T. shall decide schema validity, evidence consistency, topology
validity, geometry validity, KiCad compatibility, cross-validation
results, and production approval.

------------------------------------------------------------------------

# 75. Evidence Conflict Engine

B.F.T. shall classify evidence relationships:

``` text
CONSISTENT
DERIVABLE
CONFLICTING
AMBIGUOUS
INSUFFICIENT
```

A numerical difference is not automatically a conflict if the values
describe different engineering quantities.

Example:

``` text
Package drawing:
  Body = 3.00 mm

Land pattern:
  Pad span = 3.20 mm

Result:
  CONSISTENT
```

------------------------------------------------------------------------

# 76. Datasheet Difficulty Test Matrix

The test corpus shall include:

### Documents

-   Native digital PDF
-   Scanned PDF
-   Poor scan
-   Rotated pages
-   Low-resolution diagrams
-   Image-based tables
-   Multi-column layouts
-   Chinese
-   Japanese
-   German
-   French
-   Spanish
-   Mixed-language documents

### Information challenges

-   Symbol present
-   Symbol absent
-   Symbol inside block diagram
-   Multiple symbols
-   Pinout separated from descriptions
-   Package drawing separated from pinout
-   Multiple package variants
-   Conflicting revisions
-   Incomplete mechanical information

### Packages

-   Two-terminal passive
-   SOT-23
-   SOIC
-   TSSOP
-   QFN
-   DFN
-   Thermal-pad package
-   BGA
-   Irregular package
-   Connector

------------------------------------------------------------------------

# 77. Golden Components and Fault Injection

Each golden component shall include:

``` text
Source
Approved Component IR
Approved Symbol
Approved Footprint
Approved 3D Model
Expected Validation Results
```

The suite shall inject faults such as:

``` text
Wrong pin number
Wrong pin name
Wrong electrical type
Missing pad
Extra pad
Pad shifted
Pad mirrored
Wrong pitch
Wrong footprint origin
3D shifted
3D rotated
3D mirrored
3D scaled
Wrong height
Pin 1 mismatch
Thermal pad mismatch
```

------------------------------------------------------------------------

# 78. MVP Package Strategy

The initial release shall prioritize reliability over package breadth.

Proposed initial corpus:

``` text
0402
0603
0805

SOT-23

SOIC-8
TSSOP-16

QFN-16
QFN-24
```

Additional families shall be added only after their package definitions,
generators, viewer checks, and validation tests are mature.

------------------------------------------------------------------------

# 79. Architecture Diagrams

## 62.1 Evidence Architecture

``` text
                     DATASHEET
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
        Text           Tables       Images/Diagrams
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                    OCR / Vision
                         │
                         ▼
                      Evidence
                         │
                         ▼
                    Component IR
```

## 62.2 Independent Artifact Architecture

``` text
                     Component IR
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
            Footprint           3D Model
             Engine              Engine
                 │                 │
                 ▼                 ▼
             .kicad_mod      OpenSCAD / CadQuery → STEP
                 │                 │
                 └────────┬────────┘
                          ▼
                  Cross Validator
                          │
                    PASS / FAIL
```

## 62.3 Review Architecture

``` text
Source Evidence
      │
      ▼
Component IR
      │
      ▼
Generated Artifacts
      │
      ▼
Deterministic Validation
      │
 ┌────┴─────┐
 ▼          ▼
PASS      Review
 │          │
 │     ┌────┴────┐
 │     ▼         ▼
 │   Correct   Reject
 │     │
 └─────┘
      │
      ▼
Approved Component
```

------------------------------------------------------------------------

# 80. Implementation Roadmap

## Phase 1 --- Evidence → Component IR

Build PDF ingestion, page selection, OCR, table extraction,
image/diagram extraction, evidence objects, provenance, conflict
detection, and the Component IR schema.

**Exit criterion:** a validated IR can be produced from representative
datasheets without generating KiCad artifacts.

## Phase 2 --- IR → Symbol

Build the Symbol IR, deterministic `.kicad_sym` serializer, validation,
preview, and golden symbol tests.

## Phase 3 --- IR + PDL → Footprint

Build PDL package schema, land-pattern definitions, deterministic
footprint generation, `.pretty` libraries, footprint validation, and
topology tests.

## Phase 4 --- IR + PDL → 3D

Build mechanical package definitions, 3D backend templates/interfaces, deterministic
parameter generation, STEP generation, and model validation.

## Phase 5 --- 3D Viewer

Build model/footprint overlay, coordinate axes, Pin 1, measurements,
placement transforms, standard views, and human review.

## Phase 6 --- Cross-Validation

Build pad/pin correspondence, XY alignment, rotation, mirroring, Z
height, scale, thermal-pad checks, and fault-injection tests.

## Phase 7 --- KiCad Integration

Build native library packaging, KiCad opening/parsing tests,
symbol/footprint association, 3D model association, and installation/use
workflow.

## Phase 8 --- Production Test Corpus

Build golden components, difficult PDFs, multilingual corpus, visual
regression, ERC-oriented tests, PCB connectivity tests, and full
regression.

------------------------------------------------------------------------

# 81. v0.8 Acceptance Criteria

Before implementation begins, the architecture shall have:

-   [ ] Formal Component IR schema
-   [ ] Formal evidence/provenance model
-   [ ] Source precedence by engineering domain
-   [ ] Explicit package mechanical model
-   [ ] Explicit land-pattern model
-   [ ] Explicit package topology model
-   [ ] Explicit coordinate-system conventions
-   [ ] Independent footprint generator interface
-   [ ] Independent 3D generator interface
-   [ ] Deterministic validation model
-   [ ] Package-aware validation tolerances
-   [ ] Footprint/3D cross-validation
-   [ ] 3D viewer requirements
-   [ ] Human-review workflow
-   [ ] Build state machine
-   [ ] NOT_GENERATABLE state
-   [ ] Reproducible build definition
-   [ ] Content hashing model
-   [ ] Revision/change tracking
-   [ ] AI provider boundary
-   [ ] Evidence conflict engine
-   [ ] Golden component strategy
-   [ ] Fault-injection strategy
-   [ ] MVP package strategy
-   [ ] Implementation roadmap

------------------------------------------------------------------------

# 82. Recommended Next Specification: v0.8

v0.8 should define the MVP implementation specification rather than
adding more conceptual features.

It should contain:

1.  Exact Component IR schema.
2.  PDL schema for the first supported packages.
3.  Generator interfaces.
4.  Validation algorithms.
5.  Coordinate transforms.
6.  Data persistence format.
7.  Build-state persistence.
8.  UI/workflow screens.
9.  First AI-provider adapter.
10. First end-to-end golden components.
11. Automated test harness.
12. KiCad integration strategy.

The objective is to make the architecture sufficiently precise that
implementation can begin without major architectural decisions being
made during coding.

------------------------------------------------------------------------

# 83. Final B.F.T. Component Builder Principles

1.  **AI interprets; B.F.T. verifies.**
2.  **The Component IR is the central structured source of truth.**
3.  **Evidence provenance is preserved for important engineering
    values.**
4.  **Source authority is domain-specific.**
5.  **Package mechanical geometry and land pattern are distinct
    concepts.**
6.  **Package topology is explicitly modeled and validated.**
7.  **Footprint and 3D artifacts are independently generated.**
8.  **Independent artifact agreement is used as a cross-validation
    signal.**
9.  **B.F.T. never silently modifies an artifact merely to force
    agreement.**
10. **Deterministic validators, not AI confidence, decide PASS/FAIL.**
11. **Ambiguous or conflicting evidence requires human review.**
12. **Insufficient source data may result in NOT_GENERATABLE.**
13. **Validated package definitions are reused instead of reinvented.**
14. **OpenSCAD is an initial 3D backend, not the ultimate package source
    of truth.**
15. **Native KiCad artifacts remain the final deliverables.**
16. **Builds are reproducible and traceable.**
17. **Engineering changes are explicitly tracked.**
18. **A small, highly validated MVP is preferred over broad unreliable
    package coverage.**
19. **Functional end-to-end testing is mandatory; unit tests alone are
    insufficient.**
20. **Human review is a controlled part of the engineering workflow, not
    an exception hidden from the user.**

> **Don't ask AI to draw the same package a thousand times. Teach B.F.T.
> what the package is, let AI extract the component-specific parameters,
> let independent deterministic generators build the artifacts, and let
> B.F.T. prove that they agree.**

------------------------------------------------------------------------

# 245. v0.9 Boundary

v0.8.1 is the corrected architecture + direct build specification. It
defines the implementation contract but does not itself claim that the
repository implementation already exists.

v0.9 shall be the **Executable Specification / Repository Bootstrap**
and shall contain the first actual implementation artifacts:

1.  JSON Schema files committed to the repository.
2.  PDL YAML records with validated dimensions/evidence.
3.  Python domain models and package skeleton.
4.  Deterministic generator implementations.
5.  Validator implementations.
6.  SQLite migrations.
7.  CLI skeleton and command contracts.
8.  API request/response schemas and service skeleton.
9.  Golden and negative fixture files.
10. CI configuration.
11. At least one runnable deterministic end-to-end build without AI.

The distinction is normative:

-   **v0.8.1:** defines what must be built.
-   **v0.9:** begins shipping the code and machine-readable
    implementation artifacts that realize that specification.

------------------------------------------------------------------------

# Final v0.8.1 Build Specification Position

The architecture is now converted into an implementation contract with
explicit ownership, schemas, interfaces, deterministic generation,
validation, persistence, testing, and release behavior.

The critical implementation boundary remains:

``` text
                 Manufacturer Documents
                         │
                         ▼
                 Extraction / OCR
                         │
                         ▼
                   Evidence Graph
                         │
                         ▼
                    Component IR
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
             PDL               AI Interpretation
              │                     │
              └──────────┬──────────┘
                         ▼
                  Approved IR
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      Footprint Generator      3D Generator
             │                       │
             ▼                       ▼
        .kicad_mod                 STEP
             │                       │
             └───────────┬───────────┘
                         ▼
                Deterministic Validation
                         │
                         ▼
                  Cross-Validation
                         │
                         ▼
                    Human Review
                         │
                         ▼
                       Export
```

**The AI is deliberately downstream of the engineering model and
upstream of deterministic decision-making.**

That is the central design decision that prevents PartSmith from
becoming an AI system that merely produces plausible-looking KiCad
files.

------------------------------------------------------------------------

# v0.8 --- Direct Build Specification

v0.8 freezes the implementation contract sufficiently to begin coding.

This version adds the concrete artifacts required to turn the
specification into a working repository:

-   normative JSON Schemas
-   PDL record examples
-   Python model contracts
-   validator rule IDs
-   SQL schema
-   API request/response contracts
-   CLI behavior
-   exact build dependency rules
-   fixture layout
-   test-case identifiers
-   UI state model
-   first implementation backlog
-   acceptance gates

The examples in this document are normative unless explicitly marked
illustrative.

# 1. v0.8 Normative Conventions

The following keywords are normative:

``` text
MUST
MUST NOT
REQUIRED
SHALL
SHALL NOT
SHOULD
SHOULD NOT
MAY
```

A production implementation MUST follow all `MUST` and `SHALL`
requirements.

# 2. Frozen Version Matrix

  Artifact                Version
  ----------------------- --------------
  B.F.T. spec             0.8
  Component IR schema     1.0
  Evidence schema         1.0
  PDL schema              1.0
  Manifest schema         1.0
  Validation schema       1.0
  Build database schema   1.0
  KiCad target            10.x
  Internal units          mm / degrees
  Hash                    SHA-256

The initial KiCad target is KiCad 10.x. KiCad 10.0 documentation
identifies `.kicad_sym`, `.kicad_mod`, `.pretty`, and the current
CLI/API architecture; B.F.T. therefore treats KiCad compatibility as a
versioned adapter rather than assuming file-format stability.
citeturn0search1turn0search12turn0search9

# 3. Normative Component IR

The canonical IR is JSON-compatible.

``` json
{
  "schema_version": "1.0",
  "identity": {
    "manufacturer": "Example Manufacturer",
    "mpn": "EXAMPLE-123",
    "package_variant": "QFN-16-3x3-0.5P"
  },
  "pins": [],
  "package": {},
  "symbol": {},
  "footprint": {},
  "model_3d": {},
  "evidence": [],
  "standards": [],
  "overrides": [],
  "validation": {},
  "build": {},
  "revision": {}
}
```

Unknown fields MUST be rejected unless the schema explicitly permits an
extension namespace.

# 4. Component IR JSON Schema --- Core

The repository MUST contain:

``` text
schemas/component-ir-1.0.json
```

Core schema:

``` json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://board-forge-tools.dev/schema/component-ir/1.0",
  "title": "BFT Component IR",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "identity",
    "pins",
    "package",
    "evidence",
    "validation"
  ],
  "properties": {
    "schema_version": {
      "const": "1.0"
    },
    "identity": {
      "$ref": "#/$defs/identity"
    },
    "pins": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/pin"
      }
    },
    "package": {
      "$ref": "#/$defs/package"
    },
    "symbol": {
      "$ref": "#/$defs/symbol"
    },
    "footprint": {
      "$ref": "#/$defs/footprint"
    },
    "model_3d": {
      "$ref": "#/$defs/model3d"
    },
    "evidence": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/evidenceRef"
      }
    },
    "standards": {
      "type": "array"
    },
    "overrides": {
      "type": "array"
    },
    "validation": {
      "type": "object"
    },
    "build": {
      "type": "object"
    },
    "revision": {
      "type": "object"
    }
  }
}
```

The full schema MUST define every `$defs` object in the repository.

# 5. Value Status Schema

``` json
{
  "type": "string",
  "enum": [
    "DIRECT",
    "DERIVED",
    "STANDARD",
    "USER_OVERRIDE",
    "INFERRED",
    "UNKNOWN",
    "AMBIGUOUS",
    "CONFLICTING",
    "MISSING"
  ]
}
```

Release-critical values MUST NOT have status:

``` text
INFERRED
UNKNOWN
AMBIGUOUS
CONFLICTING
MISSING
```

unless a specific validator explicitly allows that state.

# 6. Identity Schema

``` json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "manufacturer",
    "mpn",
    "package_variant"
  ],
  "properties": {
    "manufacturer": {"type": "string", "minLength": 1},
    "manufacturer_normalized": {"type": "string"},
    "mpn": {"type": "string", "minLength": 1},
    "mpn_normalized": {"type": "string"},
    "package_variant": {"type": "string", "minLength": 1},
    "ordering_suffix": {"type": "string"},
    "temperature_grade": {"type": "string"},
    "qualification": {"type": "string"},
    "source_revision": {"type": "string"}
  }
}
```

# 7. Pin Schema

``` json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["number", "name", "electrical_type"],
  "properties": {
    "number": {"type": "string", "minLength": 1},
    "name": {"type": "string"},
    "electrical_type": {
      "enum": [
        "input",
        "output",
        "bidirectional",
        "tri_state",
        "open_collector",
        "open_emitter",
        "passive",
        "power_input",
        "power_output",
        "power_flag",
        "no_connect",
        "unspecified"
      ]
    },
    "function": {"type": "string"},
    "active_low": {"type": "boolean"},
    "alternate_functions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "topology": {
      "$ref": "#/$defs/pinTopology"
    },
    "flags": {
      "$ref": "#/$defs/pinFlags"
    },
    "evidence_ids": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

# 8. Package Schema

``` json
{
  "type": "object",
  "required": [
    "family",
    "variant",
    "mechanical",
    "topology",
    "land_pattern"
  ],
  "properties": {
    "family": {"type": "string"},
    "variant": {"type": "string"},
    "pdl_id": {"type": "string"},
    "pdl_revision": {"type": "integer", "minimum": 1},
    "mechanical": {"type": "object"},
    "topology": {"type": "object"},
    "land_pattern": {"type": "object"},
    "coordinate_system": {"type": "object"}
  }
}
```

# 9. Mechanical Dimension Object

All dimensions use:

``` json
{
  "nominal_mm": 3.0,
  "min_mm": 2.9,
  "max_mm": 3.1,
  "status": "DIRECT",
  "evidence_ids": ["E-001"]
}
```

A dimension with no tolerance MUST NOT be interpreted as a tolerance of
zero.

# 10. Evidence Schema --- Normative

File:

``` text
schemas/evidence-1.0.json
```

Required structure:

``` json
{
  "id": "E-000001",
  "type": "PACKAGE_DRAWING",
  "source": {
    "document_id": "DOC-000001",
    "document_sha256": "…",
    "page": 34,
    "region": {
      "x": 100,
      "y": 200,
      "width": 800,
      "height": 500
    }
  },
  "raw": {
    "text": "3.00 ± 0.10",
    "language": "en"
  },
  "interpretation": {
    "value": 3.0,
    "unit": "mm",
    "status": "DIRECT"
  },
  "extractor": {
    "type": "pdf_text",
    "version": "1.0"
  }
}
```

# 11. Evidence Type Enum

``` text
DATASHEET_TEXT
OCR_TEXT
TABLE
PACKAGE_DRAWING
BLOCK_DIAGRAM
PINOUT_DIAGRAM
LAND_PATTERN
MANUFACTURER_CAD
MANUFACTURER_WEB_DOCUMENT
JEDEC_STANDARD
IPC_STANDARD
USER_PROVIDED_VALUE
DERIVED_VALUE
```

# 12. PDL Schema --- Normative

File:

``` text
schemas/pdl-1.0.json
```

Example:

``` yaml
schema_version: "1.0"

id: "qfn-16-3x3-0p5"
revision: 1

identity:
  family: "QFN"
  variant: "QFN-16-3x3-0.5P"

mechanical:
  body:
    length_mm: 3.0
    width_mm: 3.0
    height_nominal_mm: 0.85

topology:
  pin_count: 16
  pitch_mm: 0.5
  numbering: counter_clockwise
  pin1:
    location: top_left

land_pattern:
  strategy: manufacturer_or_validated_family
  thermal_pad:
    supported: true

model_3d:
  body_strategy: qfn_body
  lead_strategy: gullwing_like
  marker_strategy: pin1_marker

coordinate_system:
  origin: package_center
  x_positive: right
  y_positive: up
  z_positive: away_from_pcb

validation:
  xy_pin_pad_tolerance_mm: 0.01
  center_tolerance_mm: 0.01
  rotation_tolerance_deg: 0.1
  height_tolerance_mm: 0.02
```

# 13. PDL Record Rules

Every PDL record MUST include:

``` text
id
revision
schema_version
family
variant
topology
coordinate_system
validation
source references
```

A PDL record without evidence is not approved for production generation.

# 14. Initial PDL Records

The repository shall initially contain:

``` text
pdl/variants/0402.yaml
pdl/variants/0603.yaml
pdl/variants/0805.yaml
pdl/variants/sot-23.yaml
pdl/variants/soic-8.yaml
pdl/variants/tssop-16.yaml
pdl/variants/qfn-16-3x3-0p5.yaml
pdl/variants/qfn-24-4x4-0p5.yaml
```

Exact dimensions must be populated from validated sources before the
records are marked approved.

# 15. Python Domain Models

Use typed immutable models for engineering data.

Representative:

``` python
@dataclass(frozen=True)
class Dimension:
    nominal_mm: float | None
    min_mm: float | None
    max_mm: float | None
    status: ValueStatus
    evidence_ids: tuple[str, ...]
```

``` python
@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    electrical_type: ElectricalType
    function: str | None
    active_low: bool | None
    evidence_ids: tuple[str, ...]
```

Mutable UI state MUST NOT be used as the engineering source of truth.

# 16. Exact Domain Interfaces

Required Python protocols:

``` python
class EvidenceStore(Protocol):
    def get(self, evidence_id: str) -> Evidence: ...
    def list_for_value(self, path: str) -> list[Evidence]: ...
```

``` python
class PDLStore(Protocol):
    def get(self, pdl_id: str, revision: int | None = None) -> PDL: ...
    def find_candidates(self, query: PackageQuery) -> list[PDLCandidate]: ...
```

``` python
class IRStore(Protocol):
    def save(self, ir: ComponentIR) -> None: ...
    def load(self, component_id: str) -> ComponentIR: ...
```

# 17. Generator Context

``` python
@dataclass(frozen=True)
class GeneratorContext:
    bft_version: str
    generator_version: str
    target_kicad: str
    output_root: Path
    reproducible: bool = True
```

Generators MUST NOT read global mutable configuration.

# 18. Artifact Contract

``` python
@dataclass(frozen=True)
class GeneratedArtifact:
    artifact_id: str
    artifact_type: ArtifactType
    path: Path
    sha256: str
    generator: str
    generator_version: str
    input_hash: str
```

# 19. Validation Rule Registry

Each validator rule receives a permanent ID.

Examples:

``` text
IR-001 Schema valid
IR-002 Required value present
PIN-001 Unique pin numbers
PIN-002 Pin count matches package
PIN-003 Electrical type supported
PKG-001 Package family recognized
PKG-002 Topology valid
PKG-003 Pin-1 orientation valid
FP-001 Pad count
FP-002 Pad numbering
FP-003 Pad geometry
FP-004 Courtyard
3D-001 STEP parse
3D-002 Scale
3D-003 Height
3D-004 Orientation
3D-005 Required STEP artifact
3D-006 Backend/runtime metadata
MAP-001 Symbol-to-pad mapping
MAP-002 Pad-to-model mapping
XVAL-001 Pin/pad alignment
XVAL-002 Center alignment
XVAL-003 Pin-1 alignment
XVAL-004 Height alignment
XVAL-005 Thermal-pad alignment
KICAD-001 Target version
KICAD-002 Parse/open
KICAD-003 Round-trip
REP-001 Reproducibility
REL-001 No blocking validation
```

Rule IDs MUST never be reused for different meanings.

# 20. Validator Implementation Contract

``` python
@dataclass(frozen=True)
class ValidationRule:
    rule_id: str
    category: str
    severity: Severity
    blocking: bool
```

``` python
class ValidationEngine:
    def run(
        self,
        build: BuildContext,
        rules: Sequence[ValidationRule]
    ) -> list[ValidationResult]:
        ...
```

# 21. Validation Severity

``` text
INFO
WARNING
ERROR
BLOCKING
```

`BLOCKING` always prevents approval.

# 22. Deterministic Rule Example

``` python
def validate_pad_count(ir, footprint):
    expected = len([p for p in ir.pins if not p.flags.no_connect])
    actual = len(footprint.signal_pads())
    if expected != actual:
        return fail(
            "FP-001",
            expected=expected,
            measured=actual
        )
    return pass_("FP-001")
```

The actual implementation must account for legitimate exposed/thermal
pads and package-specific exceptions.

# 23. Coordinate Transform Tests

Required test cases:

``` text
identity
translation
rotation X
rotation Y
rotation Z
mirror X
mirror Y
combined transform
inverse
round trip
```

Every transform test must use known analytical expected results.

# 24. SQL Schema

MVP migration:

``` sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE components (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    manufacturer TEXT NOT NULL,
    mpn TEXT NOT NULL,
    package_variant TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    component_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    media_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE evidence (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    page INTEGER,
    region_json TEXT,
    raw_json TEXT NOT NULL,
    interpretation_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE builds (
    id TEXT PRIMARY KEY,
    component_id TEXT NOT NULL,
    state TEXT NOT NULL,
    bft_version TEXT NOT NULL,
    ir_hash TEXT,
    inputs_hash TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    generator TEXT NOT NULL,
    generator_version TEXT NOT NULL
);

CREATE TABLE validation_results (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE TABLE overrides (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    path TEXT NOT NULL,
    old_value_json TEXT,
    new_value_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    reviewer TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    build_id TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE build_dependencies (
    build_id TEXT NOT NULL,
    upstream_id TEXT NOT NULL,
    downstream_id TEXT NOT NULL,
    dependency_type TEXT NOT NULL,
    PRIMARY KEY(build_id, upstream_id, downstream_id)
);
```

Foreign keys MUST be enabled.

# 25. Database Migration Rules

Migrations live in:

``` text
migrations/
001_initial.sql
002_...
```

Never modify an applied migration.

# 26. API Contract

Base path:

``` text
/api/v1
```

Create component:

``` http
POST /api/v1/components
Content-Type: application/json
```

Request:

``` json
{
  "manufacturer": "Example",
  "mpn": "EXAMPLE-123",
  "package_variant": "QFN-16-3x3-0.5P"
}
```

Response:

``` json
{
  "component_id": "COMP-…",
  "status": "CREATED"
}
```

# 27. Build API

``` http
POST /api/v1/builds
```

Request:

``` json
{
  "component_id": "COMP-…",
  "source_document_ids": ["DOC-…"],
  "target_kicad": "10",
  "mode": "review"
}
```

Response:

``` json
{
  "build_id": "BUILD-…",
  "state": "SOURCE_RECEIVED"
}
```

# 28. Build Status API

``` http
GET /api/v1/builds/{build_id}
```

Response shall contain:

``` text
state
current_stage
progress
blocking_issues
warnings
artifact_status
```

# 29. Evidence API

``` http
GET /api/v1/builds/{build_id}/evidence
```

Supports filtering:

``` text
type
page
status
pin
package
```

# 30. Review API

``` http
POST /api/v1/builds/{build_id}/review
```

Request:

``` json
{
  "decision": "APPROVE",
  "reviewer": "user",
  "comment": "Reviewed pin table and package drawing."
}
```

`APPROVE` MUST be rejected if blocking issues remain.

# 31. Override API

``` http
POST /api/v1/builds/{build_id}/overrides
```

Request:

``` json
{
  "path": "package.mechanical.body.height.nominal_mm",
  "value": 0.85,
  "reason": "Manufacturer mechanical drawing confirmed value."
}
```

The server MUST create an immutable override record and invalidate
dependent artifacts.

# 32. CLI Contract

``` bash
bft component create
bft component inspect
bft component build
bft component validate
bft component review
bft component approve
bft component reject
bft component export
bft component diff

bft build status
bft build resume
bft build invalidate

bft pdl list
bft pdl inspect
bft pdl validate

bft doctor
bft version
```

# 33. CLI Exit Codes

``` text
0   success
1   general failure
2   invalid arguments
3   source failure
4   validation failure
5   human review required
6   not generatable
7   compatibility failure
8   reproducibility failure
9   security/resource violation
```

# 34. CLI JSON Output

All commands support:

``` bash
--json
```

Example:

``` json
{
  "status": "HUMAN_REVIEW_REQUIRED",
  "build_id": "BUILD-123",
  "issues": [
    {
      "rule_id": "PIN-004",
      "severity": "BLOCKING",
      "message": "Conflicting pin evidence."
    }
  ]
}
```

# 35. Build Dependency Matrix

  Change              Symbol       Footprint     3D                    Cross-validation
  ------------------- ------------ ------------- --------------------- ------------------
  pin number          regenerate   regenerate    conditional           rerun
  pin name only       regenerate   retain        retain                rerun mapping
  electrical type     regenerate   retain        retain                rerun mapping
  body length         retain       regenerate    regenerate            rerun
  body width          retain       regenerate    regenerate            rerun
  body height         retain       conditional   regenerate            rerun
  pitch               retain       regenerate    regenerate            rerun
  pin-1 orientation   regenerate   regenerate    regenerate            rerun
  land pattern        retain       regenerate    retain                rerun
  symbol graphic      regenerate   retain        retain                no
  3D marker           retain       retain        regenerate            rerun
  3D placement        retain       retain        regenerate metadata   rerun

"Conditional" means the dependency engine consults the PDL rule graph.

# 36. Invalidation Algorithm

``` text
1. Identify changed IR paths.
2. Resolve dependency graph.
3. Mark affected artifacts stale.
4. Preserve unaffected artifacts.
5. Rebuild in topological order.
6. Rerun all dependent validators.
7. Recompute manifest.
```

# 37. Artifact Staleness

Artifact states:

``` text
CURRENT
STALE
FAILED
MISSING
```

A stale artifact cannot participate in approval.

# 38. Build Resume

A resumed build MUST verify:

``` text
source hashes
IR hash
PDL hash
generator versions
configuration hash
artifact hashes
```

If any immutable input changed, the appropriate dependency subtree is
invalidated.

# 39. Canonical Serialization

Canonical JSON MUST:

``` text
sort keys
use UTF-8
use LF
normalize Unicode
use deterministic number formatting
omit insignificant whitespace
```

Floating-point values shall use a defined decimal representation.

# 40. Hash Inputs

Build input hash includes:

``` text
source document hashes
evidence selection hashes
IR canonical hash
PDL canonical hash
generator versions
BFT version
configuration hash
override hashes
target KiCad version
```

# 41. Manifest Schema

File:

``` text
schemas/manifest-1.0.json
```

Required:

``` json
{
  "schema_version": "1.0",
  "build_id": "BUILD-…",
  "component_id": "COMP-…",
  "status": "APPROVED",
  "inputs_hash": "…",
  "artifacts": [],
  "validation": {},
  "compatibility": {},
  "overrides": [],
  "reproducibility": {}
}
```

# 42. PDL Validation Rules

Minimum PDL rules:

``` text
PDL-001 schema valid
PDL-002 unique ID
PDL-003 revision valid
PDL-004 pin count positive
PDL-005 pitch positive
PDL-006 topology internally consistent
PDL-007 coordinate system complete
PDL-008 tolerance values valid
PDL-009 evidence present
PDL-010 land-pattern strategy valid
```

# 43. PDL Topology Model

The topology object shall support:

``` yaml
sides:
  north:
    pins: [1, 2, 3, 4]
  east:
    pins: [5, 6, 7, 8]
  south:
    pins: [9, 10, 11, 12]
  west:
    pins: [13, 14, 15, 16]
```

The topology validator shall derive pad coordinates from topology only
when the PDL explicitly defines a derivable rule.

# 44. Package-Specific Geometry Strategy

Each PDL family shall declare a geometry strategy:

``` text
RECTANGULAR
ROUND
CYLINDRICAL
LEADED
ARRAY
CUSTOM
```

Custom geometry requires an explicit deterministic generator.

# 45. 0402/0603/0805 Strategy

For passive chip packages:

``` text
body rectangle
termination geometry
pad geometry
courtyard
silkscreen restrictions
```

The footprint and 3D model are still generated independently.

# 46. SOIC/TSSOP Strategy

The PDL shall define:

``` text
body
lead count
lead pitch
lead span
lead width
lead thickness
pin-1 marker
```

The footprint uses land-pattern evidence.

The 3D generator uses mechanical lead/body evidence.

# 47. QFN Strategy

QFN PDL shall explicitly support:

``` text
perimeter pads
exposed thermal pad
corner pin behavior
pin-1 marking
center thermal pad
```

Thermal pad dimensions are independent of body dimensions.

# 48. Symbol Unit Strategy

The symbol generator shall support:

``` text
single-unit
multi-unit
power-unit
alternate-body
```

The initial MVP may implement single-unit and power-unit components
first.

# 49. Symbol Pin Placement Strategy

Pin placement shall be deterministic.

Rules shall consider:

``` text
function group
pin direction
pin name length
pin number
package topology where useful
standard BFT symbol conventions
```

The symbol generator MUST NOT infer electrical grouping solely from pin
order.

# 50. Symbol Graphics Contract

Generated symbol graphics shall have deterministic:

``` text
line widths
pin lengths
text sizes
grid alignment
origin
body dimensions
```

All values shall be configurable through versioned symbol rules.

# 51. Footprint Text Contract

Default fields:

``` text
Reference: REF**
Value: component value
```

The generated footprint MUST preserve KiCad-required footprint structure
and use valid layer identifiers for the target KiCad version.

KiCad 10 documentation identifies `Reference` and `Value` as mandatory
footprint fields in the footprint editor and describes `.kicad_mod` as
the native footprint file format. citeturn0search6turn0search5

# 52. 3D Model Placement Contract

The footprint shall reference the 3D model using a
project/library-relative path.

Placement metadata:

``` yaml
placement:
  offset_mm:
    x: 0
    y: 0
    z: 0
  rotation_deg:
    x: 0
    y: 0
    z: 0
  mirror: none
```

# 53. 3D Model Geometry Contract

The model generator owns:

``` text
body
leads
terminals
marker
mechanical details
```

The footprint generator owns:

``` text
pads
courtyard
silkscreen
fabrication graphics
```

No geometry ownership is shared.

# 54. Cross-Validation Measurement Contract

Measurements are taken from independent artifacts.

For each check:

``` text
expected
measured
difference
tolerance
status
```

Example:

``` yaml
rule_id: XVAL-001
expected_mm:
  x: 0.75
  y: -1.25
measured_mm:
  x: 0.751
  y: -1.249
difference_mm:
  x: 0.001
  y: 0.001
tolerance_mm: 0.01
status: PASS
```

# 55. Fault Injection Contract

Faults shall be generated from immutable golden artifacts.

Each fault has:

``` yaml
fault:
  id: FI-3D-ROT-180
  target: model_3d
  operation:
    type: rotate
    z_deg: 180
  expected_rule: XVAL-003
  expected_status: FAIL
```

# 56. Test Fixture Manifest

Each fixture shall contain:

``` yaml
fixture_id:
source:
expected_ir:
expected_pdl:
expected_artifacts:
expected_results:
faults:
```

# 57. Golden Fixture IDs

Initial:

``` text
GOLD-0402-001
GOLD-0603-001
GOLD-0805-001
GOLD-SOT23-001
GOLD-SOIC8-001
GOLD-TSSOP16-001
GOLD-QFN16-001
GOLD-QFN24-001
```

# 58. Negative Fixture IDs

Initial:

``` text
NEG-PIN-001
NEG-PIN-002
NEG-PITCH-001
NEG-PAD-001
NEG-PIN1-001
NEG-PKG-001
NEG-3D-OFFSET-001
NEG-3D-ROT-001
NEG-3D-MIRROR-001
NEG-3D-SCALE-001
NEG-3D-HEIGHT-001
NEG-EVIDENCE-CONFLICT-001
NEG-LANDPATTERN-MISSING-001
```

# 59. Test Naming

Tests shall use:

``` text
test_<domain>_<rule>_<condition>
```

Example:

``` text
test_cross_validation_xval003_detects_180_degree_rotation
```

# 60. Unit Test Minimums

Minimum initial test counts:

``` text
schema: 20
units: 15
transforms: 25
PDL: 30
topology: 30
generators: 40
validators: 60
hashing: 15
dependency graph: 30
```

These are minimum test cases, not coverage percentages.

# 61. Integration Test Minimums

At least:

``` text
8 golden end-to-end builds
8 negative end-to-end builds
5 document-extraction cases
5 evidence-conflict cases
5 reproducibility cases
3 KiCad compatibility cases
```

# 62. CI Gate Definitions

``` text
GATE-01 schema
GATE-02 unit
GATE-03 PDL
GATE-04 generator
GATE-05 validator
GATE-06 golden
GATE-07 negative
GATE-08 deterministic
GATE-09 security
GATE-10 KiCad
```

All gates MUST pass for a release build.

# 63. Security Gate

The security gate MUST test:

``` text
path traversal
command injection
prompt injection
malformed PDFs
malformed STEP
oversized inputs
credential leakage
unsafe filenames
symlink attacks
temporary-directory escape
```

# 64. UI State Model

The review UI shall have:

``` text
IMPORT
ANALYZE
EVIDENCE
IR
PACKAGE
SYMBOL
FOOTPRINT
3D
VALIDATION
REVIEW
EXPORT
```

Each state displays:

``` text
status
blocking issues
warnings
source/evidence links
```

# 65. Evidence Viewer

The evidence viewer shall support:

``` text
page navigation
zoom
region highlight
OCR text
source text
translation
evidence status
linked IR value
```

# 66. IR Editor

The IR editor shall:

-   display provenance
-   distinguish source values from overrides
-   reject invalid values
-   show downstream impact before applying changes
-   require confirmation for blocking overrides

# 67. Package Review Panel

Show:

``` text
selected PDL
candidate PDLs
why selected
mechanical dimensions
topology
land pattern source
evidence
validation
```

# 68. 2D Footprint Preview

Show:

``` text
pads
numbers
silkscreen
courtyard
fabrication
origin
pin 1
dimensions
```

# 69. 3D Viewer Overlay

The viewer shall allow:

``` text
footprint-only
3D-only
overlay
crosshair
pad highlight
pin highlight
measurement
```

# 70. Review Issue Navigation

Selecting a validation failure shall navigate to:

``` text
artifact
geometry
evidence
IR path
```

where applicable.

# 71. Export UI

Export shall show:

``` text
approved?
validation status
KiCad target
artifact hashes
destination
existing-file conflicts
```

The final action is disabled if approval requirements are not met.

# 72. Project-Local Library Installation

Installation sequence:

``` text
validate
→ dry-run
→ backup
→ write temporary files
→ validate again
→ atomic commit
→ update library tables if requested
→ record audit
```

# 73. KiCad Adapter v10

The KiCad 10 adapter shall support:

``` text
detect version
launch kicad-cli
launch IPC API server
validate supported library/document operations
report unsupported operations
```

KiCad currently documents `kicad-cli` subcommands including
`api-server`, `fp`, `sch`, `sym`, and `version`, and the official Python
bindings expose the IPC API. citeturn0search9turn0search0

# 74. API Integration Boundary

B.F.T. shall prefer:

``` text
official IPC/Python API
```

for operations requiring live KiCad interaction.

Direct native file generation remains acceptable for deterministic
library artifacts where the format contract is explicitly implemented
and tested.

The older `pcbnew` scripting API shall be isolated as a compatibility
fallback rather than becoming the primary new integration architecture.
KiCad's documentation describes the `pcbnew` API as tightly coupled to
internals and subject to change. citeturn0search6

# 75. Current KiCad API Caution

B.F.T. MUST record the exact KiCad version used for API tests.

A passing test against KiCad 10.0.6 MUST NOT be represented as proof of
compatibility with every future KiCad 10.x release.

# 76. Build Performance Targets

Initial targets for a typical supported component:

``` text
document inspection: < 2 s
local text extraction: < 10 s
deterministic generation: < 10 s
deterministic validation: < 10 s
3D generation: < 60 s
```

AI/OCR network latency is excluded from deterministic performance
targets.

These are engineering targets, not release blockers until measured
against the MVP hardware baseline.

# 77. Memory Targets

MVP should remain usable within:

``` text
8 GB RAM
4 CPU cores
```

Large documents may be streamed/page-processed rather than loaded
entirely into memory.

# 78. Temporary File Rules

Temporary files shall live under a per-build directory:

``` text
<cache>/builds/<build_id>/tmp/
```

The build ID must be non-predictable enough to avoid collisions.

Temporary files are deleted after successful cleanup unless retained by
a failure/debug policy.

# 79. Cache Rules

Cache entries shall be immutable.

Cache key:

``` text
SHA256(
    operation
    + normalized input
    + tool version
    + configuration
)
```

# 80. AI Cache Rules

AI results shall only be reused when:

``` text
provider
model
task schema
prompt template version
input hash
relevant provider settings
```

all match.

# 81. Provider Failure Policy

If AI fails:

``` text
retry transiently
→ fall back to another configured provider if allowed
→ otherwise continue with deterministic extraction
→ enter HUMAN_REVIEW when required
```

The system shall never substitute fabricated values.

# 82. Local-Only Security Mode

When enabled:

``` text
no external AI calls
no external OCR calls
no external web retrieval
```

unless explicitly authorized for a specific operation.

# 83. Source Retention Policy

Build records shall retain:

``` text
source hash
source metadata
evidence references
```

Whether raw source files are retained is a project policy.

The system shall support:

``` text
retain
reference-only
delete-after-build
```

# 84. Provenance Integrity

If a source document is replaced:

``` text
document hash changes
→ evidence becomes stale
→ IR values become stale
→ dependent artifacts become stale
```

No old evidence may silently attach to a new document.

# 85. Evidence Staleness

Evidence states:

``` text
CURRENT
STALE
INVALID
SUPERSEDED
```

A stale evidence object cannot support approval until revalidated.

# 86. Revision Diff

Semantic diff output:

``` yaml
changes:
  - path: pins[7].name
    old: "EN"
    new: "ENABLE"
    category: electrical
  - path: package.mechanical.body.height
    old: 0.80
    new: 0.85
    category: mechanical
```

# 87. Review Decision Persistence

A review decision shall store:

``` text
build ID
reviewer
timestamp
decision
comment
issue IDs addressed
override IDs created
```

# 88. Approval Immutability

Once a build is approved:

``` text
approved build inputs are immutable
approved artifacts are immutable
approved manifest is immutable
```

Changes create a new build.

# 89. Release IDs

Approved builds receive:

``` text
release_id
```

Example:

``` text
BFTREL-2026-000123
```

The release ID is separate from the build ID.

# 90. Release Manifest

The release manifest shall include:

``` text
release_id
build_id
component identity
artifact hashes
PDL revision
BFT version
KiCad target
validation summary
reviewer
timestamp
```

# 91. Component Library Update Policy

A library update shall compare:

``` text
existing release
vs
new release
```

and show semantic changes before replacing anything.

# 92. Duplicate/Near-Duplicate Detection

Similarity features:

``` text
normalized MPN
package
pin count
pin map
body dimensions
pad geometry
symbol hash
footprint hash
```

The system may report:

``` text
EXACT_DUPLICATE
LIKELY_DUPLICATE
POSSIBLE_DUPLICATE
UNRELATED
```

This classification is informational and does not replace human review.

# 93. Documentation Extraction Acceptance

The extraction subsystem is considered acceptable when it can correctly
preserve:

``` text
page
bounding box
source text
table rows
diagram regions
language
document hash
```

for the initial test corpus.

# 94. AI Extraction Acceptance

AI is considered integrated when it can:

``` text
return typed candidates
cite evidence IDs
identify ambiguity
identify conflicts
avoid inventing missing values
```

A successful AI call alone does not constitute component acceptance.

# 95. PDL Acceptance

A PDL record is accepted only after:

``` text
schema PASS
topology PASS
mechanical evidence PASS
land-pattern evidence PASS
coordinate contract PASS
3D strategy PASS
```

# 96. Generator Acceptance

Each generator must pass:

``` text
golden output
negative input rejection
determinism
schema/format validation
```

# 97. Cross-Validation Acceptance

Cross-validation must detect every injected fault in the initial fault
corpus.

False negatives are release-blocking.

# 98. Reproducibility Acceptance

Run:

``` text
build A
build B
```

with identical inputs.

Required:

``` text
IR hash identical
artifact hashes identical
validation results identical
manifest inputs hash identical
```

# 99. CI Reproducibility

At least one golden build shall be reproduced in a clean CI environment.

# 100. First Implementation Backlog

Priority order:

``` text
BFT-001 repository bootstrap
BFT-002 schema package
BFT-003 core value/unit types
BFT-004 canonical JSON
BFT-005 hashing
BFT-006 SQLite migrations
BFT-007 evidence store
BFT-008 PDL store
BFT-009 PDL topology engine
BFT-010 Component IR model
BFT-011 IR validator
BFT-012 symbol generator
BFT-013 footprint generator
BFT-014 3D generator
BFT-015 geometry engine
BFT-016 coordinate transforms
BFT-017 validators
BFT-018 cross-validator
BFT-019 build orchestrator
BFT-020 dependency graph
BFT-021 golden fixtures
BFT-022 negative fixtures
BFT-023 PDF adapter
BFT-024 OCR adapter
BFT-025 AI provider adapter
BFT-026 review UI
BFT-027 3D viewer
BFT-028 KiCad adapter
BFT-029 export/install
BFT-030 CI/security hardening
```

# 101. BFT-001 --- Repository Bootstrap

Deliver:

``` text
pyproject.toml
src/partsmith/
tests/
schemas/
pdl/
migrations/
fixtures/
```

Acceptance:

``` text
pytest runs
package imports
CLI returns version
```

# 102. BFT-002 --- Schema Package

Deliver:

``` text
component-ir-1.0.json
evidence-1.0.json
pdl-1.0.json
manifest-1.0.json
validation-1.0.json
```

Acceptance:

``` text
valid fixtures PASS
invalid fixtures FAIL
```

# 103. BFT-003 --- Core Engineering Types

Implement:

``` text
Dimension
Angle
Point2
Point3
Vector2
Vector3
Transform
BoundingBox
Tolerance
ValueStatus
```

# 104. BFT-004 --- Canonicalization

Implement:

``` python
canonical_json(obj) -> bytes
sha256_bytes(data) -> str
sha256_file(path) -> str
```

Acceptance includes known hash vectors.

# 105. BFT-005 --- Persistence

Implement repositories:

``` text
ComponentRepository
DocumentRepository
EvidenceRepository
BuildRepository
ArtifactRepository
ValidationRepository
ReviewRepository
```

# 106. BFT-006 --- Evidence Store

Support:

``` text
create
get
list
link
supersede
invalidate
```

# 107. BFT-007 --- PDL Store

Support:

``` text
load
validate
list
resolve
compare
```

# 108. BFT-008 --- Topology Engine

Input:

``` text
PDL topology
```

Output:

``` text
expected physical pin coordinates
pin ordering
side membership
pin-1 reference
```

# 109. BFT-009 --- Component IR Builder

Input:

``` text
evidence
AI candidates
PDL candidate
overrides
```

Output:

``` text
canonical IR
issues
provenance graph
```

# 110. BFT-010 --- Symbol Generator

Initial scope:

``` text
single-unit symbols
power pins
standard pin types
reference/value fields
datasheet field
footprint association
```

# 111. BFT-011 --- Footprint Generator

Initial scope:

``` text
0402
0603
0805
SOT-23
SOIC-8
TSSOP-16
QFN-16
QFN-24
```

# 112. BFT-012 --- 3D Generator

Initial scope:

``` text
chip body
lead/body packages
QFN body
QFN leads
pin-1 marker
STEP export
```

# 113. BFT-013 --- Geometry Engine

Must support:

``` text
rectangle
circle
line
arc
extrusion
translation
rotation
mirror
bounding box
distance
intersection
```

# 114. BFT-014 --- Validator Engine

Implement initial rules:

``` text
IR-001 through IR-002
PIN-001 through PIN-003
PKG-001 through PKG-003
FP-001 through FP-004
3D-001 through 3D-004
MAP-001 through MAP-002
XVAL-001 through XVAL-005
```

# 115. BFT-015 --- Build Orchestrator

Implement the state machine and resume behavior.

# 116. BFT-016 --- Dependency Graph

Implement path-based dependency invalidation.

# 117. BFT-017 --- Golden Corpus

Create the eight initial golden fixture directories.

# 118. BFT-018 --- Fault Injection

Implement transformations:

``` text
offset
rotation
mirror
scale
height
pin-1 marker
pad shift
```

# 119. BFT-019 --- Document Extraction

Implement:

``` text
PDF inspection
text extraction
page rendering
image extraction
table extraction
OCR adapter
```

# 120. BFT-020 --- AI Adapter

Implement one provider first behind:

``` python
AIProvider
```

The provider implementation is replaceable.

# 121. BFT-021 --- Review UI

Initial screens:

``` text
build dashboard
evidence viewer
IR editor
package panel
validation panel
approval panel
```

# 122. BFT-022 --- 3D Viewer

Initial capabilities:

``` text
rotate
pan
zoom
standard views
overlay
measurement
transform display
pin-1 highlight
```

# 123. BFT-023 --- KiCad Adapter

Initial capabilities:

``` text
version detection
CLI invocation
IPC connection
library validation
project-local installation
```

# 124. BFT-024 --- Export

Implement:

``` text
atomic export
manifest
backup
rollback
library table update
audit record
```

# 125. BFT-025 --- CI Hardening

Implement all ten CI gates.

# 126. v0.8.1 Specification Exit Criteria

The specification baseline is implementation-ready when:

``` text
[ ] all normative schemas exist
[ ] all initial PDL records exist as placeholders
[ ] domain model contracts compile
[ ] database migration runs
[ ] validator rule registry exists
[ ] build dependency graph is defined
[ ] fixture IDs are assigned
[ ] first implementation backlog is accepted
[ ] KiCad 10 target is configured
[ ] no architectural boundary remains undefined
```

# 127. v0.9 Implementation Boundary

v0.9 shall be the **Executable Specification**.

It should contain the first actual implementation artifacts:

``` text
JSON Schema files
PDL YAML records
Python package skeleton
SQLite migrations
initial validators
initial generators
golden fixtures
CLI skeleton
CI configuration
```

The goal of v0.9 should be:

> **A runnable B.F.T. PartSmith skeleton that can build and validate at
> least one deterministic component end-to-end without AI.**

# 128. Final v0.8.5 Position

The project is now ready to move from specification into implementation.

The intended sequence is:

``` text
v0.5
Architecture/data model

v0.6
Architecture hardening

v0.7
Implementation contract

v0.8
Direct build specification

v0.8.1
Contradiction-corrected build specification

v0.8.2
Feature-set-refined build specification

v0.8.3
Component acquisition feature + full-spec review

v0.9
Executable repository specification / code skeleton
```

The first implementation milestone should deliberately **exclude AI**.

The first end-to-end success should be:

``` text
Known-good structured Component IR
        ↓
PDL
        ↓
Symbol
        ↓
Footprint
        ↓
Independent 3D model
        ↓
Deterministic validation
        ↓
Footprint/3D cross-validation
        ↓
KiCad validation
        ↓
Approved component
```

Once that deterministic path works, document intelligence and AI
interpretation can be inserted upstream without allowing AI behavior to
define engineering correctness.

> **The AI should make B.F.T. faster at understanding components. It
> should never become the mechanism by which B.F.T. decides whether a
> component is correct.**

------------------------------------------------------------------------

# v0.8.5 Final Consistency Statement

The specification is internally organized around the engineering build
layers plus a separate acquisition boundary:

``` text
SOURCE / EVIDENCE
        ↓
COMPONENT IR + PDL
        ↓
DETERMINISTIC GENERATORS
        ↓
INDEPENDENT ARTIFACTS
        ↓
DETERMINISTIC VALIDATION
        ↓
CROSS-VALIDATION
        ↓
HUMAN REVIEW / APPROVAL
        ↓
FINAL ASSOCIATION + EXPORT

                 ┌──────────────────────┐
                 │  B.F.T. Acquisition  │
                 │  AI Build | Purchase │
                 └──────────────────────┘
```

No later stage is permitted to become the hidden source of truth for an
earlier stage.

# Appendix --- Current KiCad References

The KiCad-specific portions of this specification were checked against
current KiCad documentation. KiCad 10 documentation identifies native
symbol and footprint library formats and current CLI behavior; the
official `kicad-python` project documents Python bindings for the KiCad
IPC API. The specification intentionally treats these interfaces as
versioned integration boundaries.
citeturn0search12turn0search9turn0search0

------------------------------------------------------------------------

# v0.8.5 Full-Spec Review and Baseline Cleanup

This release is a **specification consistency and
implementation-readiness review** of v0.8.4. It adds no product
features.

## REVIEW-011 --- Product identity is now normative

The current product identity is:

``` text
B.F.T. — Board Forge Tools
        │
        └── PartSmith
            AI-Driven Component Builder
            Repository: partsmith
```

B.F.T. is the parent suite. PartSmith is the named product/tool.
`partsmith` is the independent repository.

Historical references to "Tool 01" remain only where they describe the
version-history context of the specification. Current normative
references use **PartSmith**.

## REVIEW-012 --- Repository independence is normative

PartSmith shall be independently:

-   built
-   tested
-   versioned
-   released
-   packaged
-   documented

The PartSmith repository shall not require a monolithic B.F.T.
repository.

B.F.T.-wide conventions may be shared conceptually or through separately
defined reusable standards, but PartSmith's build must remain
independently executable.

## REVIEW-013 --- Acquisition boundary remains unchanged

The v0.8.3 acquisition feature remains exactly one product capability:

``` text
PartSmith
   │
   ├── Build with AI
   │
   └── Purchase from B.F.T.
```

No commerce infrastructure is added to the PartSmith engineering core by
this release.

## REVIEW-014 --- Deterministic engineering authority remains unchanged

The governing architecture remains:

``` text
AI interprets
      ↓
Component IR
      ↓
PDL + authoritative evidence
      ↓
Deterministic generators
      ↓
Deterministic validators
      ↓
Human review
      ↓
Released KiCad component
```

AI does not construct final KiCad artifacts directly, and purchase
status does not replace engineering validation/release authority.

## REVIEW-015 --- Feature set remains frozen

No additional user-facing product feature is introduced in v0.8.5.

The existing PartSmith feature set remains the approved scope:

-   document/evidence ingestion
-   component identification and extraction
-   Component IR
-   package/PDL handling
-   symbol generation
-   footprint generation
-   independent 3D generation
-   deterministic validation
-   footprint/3D cross-validation
-   2D/3D review
-   human approval
-   native KiCad export
-   AI-build vs. B.F.T.-purchase choice

## REVIEW-016 --- v0.9 boundary is unchanged

v0.9 remains the first executable repository specification.

It shall translate the current normative requirements into actual
repository artifacts including:

``` text
schemas
PDL records
Python package
database migrations
generators
validators
fixtures
CLI
CI
```

The first executable milestone remains deliberately AI-free so that
deterministic component construction and validation are proven before AI
interpretation is introduced.

## REVIEW-017 --- Historical numbering is retained for traceability

The v0.8.x history contains prior review sections and implementation
planning sections. Those historical sections are retained rather than
rewritten as though they were authored in v0.8.5.

Current implementation decisions are governed by the latest normative
sections and this review.

## REVIEW-018 --- No unresolved product-architecture contradiction identified

The review found no new contradiction requiring a change to:

-   Component IR
-   PDL
-   evidence hierarchy
-   provenance
-   independent artifact generation
-   coordinate transforms
-   validation
-   cross-validation
-   reproducibility
-   KiCad integration
-   acquisition boundary
-   repository independence

# v0.8.3 Release Position (Historical)

**Feature-set decision:** The feature set is now frozen with one
additional capability: **Component Acquisition Choice**.

``` text
                         TOOL 01
                            │
                 ┌──────────┴──────────┐
                 │                     │
             BUILD WITH AI         PURCHASE
                 │                  FROM B.F.T.
                 │                     │
                 ▼                     ▼
          Existing deterministic   Released B.F.T.
             build path             component
                 │                     │
                 └──────────┬──────────┘
                            ▼
                    Native KiCad Use
```

The commercial path is intentionally separated from the engineering
core.

The next implementation specification remains **v0.9**, with the
acquisition boundary represented in the executable architecture but
without making commerce infrastructure part of the deterministic
engineering bootstrap.

------------------------------------------------------------------------

# v0.8.4 Product Identity Correction (Historical)

This release explicitly establishes the product and repository
hierarchy.

## ID-001 --- B.F.T. is the parent suite

B.F.T. means **Board Forge Tools** and represents the complete family of
tools.

## ID-002 --- PartSmith is the named product

The current tool is:

> **PartSmith --- AI-Driven Component Builder**

## ID-003 --- PartSmith is independently hosted

The implementation repository is:

``` text
partsmith
```

PartSmith is independently buildable, testable, versioned, and released.
It does not require a monolithic B.F.T. repository.

## ID-004 --- No additional feature is introduced

This release changes product naming and repository organization only.
The acquisition feature remains the only product feature added in
v0.8.3.

------------------------------------------------------------------------

# v0.8.5 Current Release Position

**PartSmith** is the named B.F.T. product covered by this specification.

``` text
B.F.T.
Board Forge Tools
│
├── PartSmith
│   AI-Driven Component Builder
│   Independent repository: partsmith
│
└── Other B.F.T. tools
    Independent repositories
```

The PartSmith feature set is frozen at the current scope. The only
product capability added in the v0.8.x review sequence beyond the
original builder is the acquisition choice:

``` text
Build with AI
OR
Purchase from B.F.T.
```

No additional feature is introduced by v0.8.5.

**Next version:** v0.9 --- Executable PartSmith Repository
Specification.
# v0.9.2 Full-Spec Review and Resolution Log

## REVIEW-019 — CadQuery backend architecture selected

The specification previously contained stale sections that described an
OpenSCAD-based or backend-neutral 3D pipeline. The current architecture uses
CadQuery/OCP/OCCT as the sole 3D implementation runtime consuming Component
IR and PDL and exporting STEP directly.

## REVIEW-020 — STEP requirement unified

STEP is mandatory wherever a component includes 3D. The specification now
uses one normative rule: a required 3D component cannot pass release
acceptance without a valid STEP artifact.

## REVIEW-021 — Historical material explicitly subordinated

Historical v0.8/v0.8.x sections remain for traceability, but current v0.9.3
normative sections take precedence. Stale historical statements must not
be interpreted as current requirements.

## REVIEW-022 — Clean installation unified

CadQuery, OCP, OCCT, and Python are runtime dependencies managed by PartSmith
rather than separate customer installation requirements.
Development environments may still install them independently.

## REVIEW-023 — AI billing/authentication unified

External AI provider usage is user-account based: the user supplies the
provider credential and pays the provider directly. Credentials remain
secret and are excluded from engineering artifacts and reproducibility
hashes.

## REVIEW-024 — Implementation plan aligned with architecture

The small-step implementation plan now uses a pinned CadQuery/OCP/OCCT spike
with explicit STEP-equivalence measurements before committing production
packaging. The first complete deterministic component remains the principal
milestone before AI integration.

---

# v0.9.3 Cleanup Note

**Document purpose:** v0.9.3 implementation baseline, revised for a single,
release-capable CadQuery 3D path.

This revision resolves the previous 3D-backend ambiguity. It selects
CadQuery/OCP/OCCT as the only 3D-generation runtime, removes OpenSCAD from
the current normative implementation path, and adds requirements for pinned
runtime tuples, dependency hashes, and measurable Phase 6 STEP validation.
Historical v0.8/v0.8.x text remains non-normative and is retained solely for
traceability. The engineering decisions include:

- STEP is mandatory for every released 3D component.
- CadQuery/OCP/OCCT is the sole 3D-generation runtime.
- Footprint and 3D generation remain independent.
- AI interprets evidence and proposes IR content; deterministic generators and
  validators remain authoritative.
- Customer installation is a single PartSmith installation with required
  runtime dependencies provisioned by PartSmith.
- User-supplied AI credentials and direct provider billing remain the model.
- The first implementation path remains deterministic and AI-free.

**Status:** Implementation baseline — documentation cleanup complete.
