# PartSmith Implementation Specification

**Specification version:** v0.9.3  
**Status:** Implementation baseline — CadQuery architecture selected  
**Document date:** 2026-09-19

## v0.9.3 Normative Baseline

This document has been cleaned so that current implementation requirements are
presented first and prior v0.8/v0.8.x material is retained only in the
**Historical Appendix** at the end.

The current normative sections, rules, interfaces, schemas, acceptance
criteria, and implementation plan are authoritative for PartSmith v0.9.3.
Historical material is non-normative and is retained solely for traceability.
It must not be used to resolve an implementation question when it conflicts
with the current baseline.

The cleanup specifically removes ambiguity caused by earlier optional-STEP
claims, obsolete alternate 3D output claims, old backend/install assumptions,
and earlier AI credential/billing wording.

# Implementation Strategy — Small, Testable Increments

PartSmith implementation shall proceed in small increments with a
working, testable result at every step. The project shall not begin with
the AI interpretation layer.

## Phase-gate policy

Every phase has a **blocking phase gate**. A phase gate passes only when
every numbered work item in that phase is complete, every listed gate
condition passes, and the commands, artifact hashes where applicable,
and test results are recorded in the repository or CI evidence.

Implementation work for phase *N+1* shall not begin until phase *N* has
a recorded PASS. A failing, skipped, unrecorded, or manually assumed
check is a gate failure. A waived gate requires an explicit specification
revision that identifies the risk owner, scope, rationale, and expiry;
a waiver is not a PASS.

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

1. Implement the normative Component IR schema.
2. Implement canonical serialization.
3. Implement schema validation.
4. Implement units and numeric normalization.
5. Implement IR hashing.

**Phase 2 gate (blocking):** A known-good IR fixture passes schema,
unit/number normalization, canonical serialization, and stable-hash
tests. Each invalid IR fixture fails the intended validator
deterministically.

## Phase 3 — PDL

1. Implement PDL schema.
2. Implement PDL loader/versioning.
3. Implement PDL validation.
4. Add the first PDL entry: 0402.
5. Add PDL inspection CLI support.

**Phase 3 gate (blocking):** `GOLD-0402-001` loads through the versioned
PDL loader; the PDL inspection CLI reports it; valid PDL tests pass; and
each invalid/topologically incorrect PDL fixture fails deterministically.

## Phase 4 — Deterministic symbol generation

1. Define symbol generator interface.
2. Implement deterministic KiCad symbol serialization.
3. Generate a known-good 0402 component symbol.
4. Validate pin numbering and symbol structure.

**Phase 4 gate (blocking):** The known-good 0402 IR/PDL input generates
a syntactically valid KiCad symbol with valid pin numbering and structure.
At least two independent runs produce byte-identical output.

## Phase 5 — Deterministic footprint generation

1. Define footprint generator interface.
2. Implement 0402 land-pattern generation.
3. Generate native `.kicad_mod`.
4. Validate pads, numbering, courtyard, and required graphics.

**Phase 5 gate (blocking):** The known-good 0402 input generates a native
`.kicad_mod`; all pad, numbering, courtyard, required-graphic, and
footprint-format validators pass.

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

**Phase 6 gate (blocking):** The CadQuery backend consumes the 0402 IR/PDL
and exports a parseable, dimensionally valid STEP artifact from the intended
packaged PartSmith environment. The recorded comparison includes body
length, width, height, terminal/pin-1 anchor positions, orientation,
expected-solid count, reference coordinate system, comparison algorithm, and
explicit tolerances. All CadQuery/OCP/OCCT runtime versions, dependency
hashes, and packaging-feasibility results are recorded.

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
offset, rotation, mirror, scale, height, and pin-1 fault fails with its
intended validation result.

## Phase 8 — First complete deterministic component

1. Connect IR → PDL → symbol.
2. Connect IR → PDL → footprint.
3. Connect IR → PDL → selected 3D backend → STEP.
4. Run all validators.
5. Run footprint/STEP cross-validation.
6. Run KiCad compatibility validation.
7. Generate the complete component package.
8. Generate the manifest.

**Phase 8 gate (blocking):** One known-good component completes the
IR-to-PDL-to-symbol/footprint/STEP pipeline without AI, passes all
validators, cross-validation, and KiCad compatibility validation, and
has an APPROVED package and manifest.

## Phase 9 — Reproducible builds

1. Hash all required inputs.
2. Canonicalize structured inputs.
3. Record generator/backend/runtime versions.
4. Implement dependency invalidation.
5. Rebuild identical fixtures.
6. Compare hashes.

**Phase 9 gate (blocking):** Two clean builds with identical canonical
inputs and pinned runtime have identical IR, artifact, validation-result,
and manifest-input hashes, or each approved deterministic-equivalence
difference is documented and validated.

## Phase 10 — Document extraction

Only after the deterministic component path works:

1. Add PDF ingestion.
2. Add page selection.
3. Add OCR.
4. Add table extraction.
5. Add diagram/image extraction.
6. Convert extraction results into Evidence objects.
7. Add evidence tests using the document corpus.

**Phase 10 gate (blocking):** The document corpus tests demonstrate PDF
ingestion, selected-page extraction, OCR, tables, and diagram/image
extraction into structured Evidence records with provenance. The tests
verify that extraction creates no engineering artifact directly.

## Phase 11 — AI provider adapter

1. Implement normalized provider interface.
2. Implement user API-key configuration.
3. Implement provider/model metadata.
4. Implement extraction/interpretation tasks.
5. Attach AI results only to Evidence/IR workflows.
6. Add prompt-injection/security tests.
7. Add conflict and ambiguity handling.

**Phase 11 gate (blocking):** The configured provider produces typed,
provenance-linked Evidence/IR candidates with provider/model metadata;
credential-handling and prompt-injection tests pass; conflicts and
ambiguities are surfaced; and tests prove AI cannot bypass deterministic
validation or human review.

## Phase 12 — Human review and application UI

1. Display evidence.
2. Display conflicts.
3. Display IR.
4. Display generated symbol/footprint.
5. Display 3D placement.
6. Support explicit overrides.
7. Implement review/approval states.

**Phase 12 gate (blocking):** End-to-end UI tests demonstrate that a user
can inspect evidence, conflicts, IR, symbol, footprint, 3D placement,
overrides, and validation results, then explicitly approve the
deterministic build.

## Phase 13 — KiCad integration

1. Implement versioned KiCad adapter.
2. Add CLI validation.
3. Add supported IPC operations.
4. Add round-trip tests.
5. Add installation/export workflow.

**Phase 13 gate (blocking):** The versioned KiCad adapter, CLI validation,
and supported IPC operations pass integration and round-trip tests. An
approved component is installed/exported and usable in the supported
KiCad 10.x environment.

## Phase 14 — Packaging and clean installation

1. Build the production application.
2. Bundle the selected CAD runtime.
3. Bundle required runtime dependencies.
4. Generate dependency/license manifest.
5. Test clean-machine installation.
6. Test upgrade/uninstall.
7. Test runtime diagnostics.

**Phase 14 gate (blocking):** A clean supported machine passes automated
install, launch, runtime-diagnostic, upgrade, and uninstall tests. The
production package includes the selected CAD runtime, required
dependencies, and validated dependency/license manifest, without a user
manually installing Python, CadQuery, OCP, OCCT, Conda, or
another CAD runtime.

# B.F.T. --- PartSmith

## Proposed Product Specification --- PartSmith

**Project:** Board Forge Tools (B.F.T.)\
**Product:** PartSmith\
**Tool:** AI-Driven Component Builder\
**Repository:** `partsmith` (independent repository)\
**Status:** Proposed / Feature-Set-Refined Engineering Specification
with Component Acquisition\
**Version:** 0.9.3\
**Target EDA:** KiCad\
**Primary output:** Native KiCad symbol + footprint + 3D model, packaged
as a usable component library; users may build with PartSmith AI or
purchase a released component from B.F.T.\
**Document date:** 2026-09-18

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

# PartSmith Runtime, Dependencies, Licensing, and Installation

## INSTALL-001 — Single-product installation

The customer installation experience shall be a **single PartSmith
installation**. Users shall not be required to manually install
CadQuery, OCP, OCCT, Python, Conda, or another CAD runtime
merely to use the supported PartSmith 3D-generation workflow.

The installer shall provision the exact runtime dependencies required by
the selected production backend.

## INSTALL-002 — Development versus customer runtime

Development environments may use package managers, Conda/Miniforge,
system Python, KiCad development installations, or other
developer tooling. Those development requirements shall not become
customer installation requirements unless explicitly approved.

## INSTALL-003 — Backend packaging

Production PartSmith shall package the selected CAD runtime and its
native dependencies. The runtime shall be version-pinned, isolated from
the user's unrelated Python environment, and invoked through the
PartSmith backend adapter.

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

The manifest shall cover direct and redistributable runtime dependencies.

## INSTALL-005 — License compliance

PartSmith shall preserve required license notices, attribution, and
license texts for redistributed open-source dependencies. Production
release checks shall compare the dependency manifest against packaged
files.

## INSTALL-006 — Runtime reproducibility

The selected 3D backend and all runtime components capable of affecting
generated STEP geometry shall be recorded in the build manifest and
included in reproducibility metadata.

# v0.9.3 Standards Lock and Implementation Baseline

## v0.9.3 External Reference Baseline

The standards-lock review used the following current public documentation:

- KiCad 10 documentation — native KiCad component/library concepts and
  KiCad 10 CLI behavior.
- KiCad official Python bindings documentation — IPC API integration.
- IPC-7351 — Generic Requirements for Surface Mount Design and Land
  Pattern Standard.
- Applicable JEDEC package-outline documentation for the supported PDL
  package variants.

These references establish the implementation boundary; they do not
replace the authoritative manufacturer documentation for an exact part.

This release records the final standards/documentation review performed
before repository implementation begins. It does not add a new product
feature. It locks the external engineering references that the v0.9
repository bootstrap shall implement against.

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

For every component whose release includes a 3D model, the final
component package **MUST contain a valid STEP (`.step`) artifact**.

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
customer runtime shall package the required CadQuery/OCP/OCCT components
so that users do not need separate CAD-runtime installation.

The adapter shall expose deterministic geometry construction and STEP export
through a controlled interface. Runtime versions, exact dependency archive
hashes, exporter settings, and the Python version shall be recorded for
reproducibility. The CadQuery, OCP, and OCCT versions shall be pinned as one
tested compatibility tuple in a reviewed lockfile or constraints file.
The tuple shall also record the supported operating system, architecture,
Python 3.12 build, dependency source, archive SHA-256, and redistributable
license files. A different tuple is a reproducibility-relevant build input
and requires fresh Phase 6 validation.

#### Generator independence

No generator or validator may modify generated geometry in order to force
agreement with another artifact.

Authoritative inputs remain:

```text
Component IR
PDL
Authoritative evidence
Approved user overrides
```

Generated STEP, footprint, and other artifacts are outputs and
may not become authoritative inputs for another engineering generator.

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

Headless `kicad-cli api-server` operation may be used by automated tests
where supported.

The IPC adapter is an integration mechanism; it is not the authoritative
source of engineering geometry.

## STD-004 — KiCad CLI validation

The repository shall use `kicad-cli` where it provides deterministic
validation, conversion, export, rendering, or compatibility checks that
are appropriate to the PartSmith acceptance pipeline.

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

The standards/documentation review is considered complete for repository
bootstrap when:

1. KiCad 10 native artifact contracts are captured.
2. KiCad IPC integration boundary is captured.
3. KiCad CLI validation boundary is captured.
4. IPC land-pattern methodology is captured.
5. Each supported PDL variant identifies its applicable package-standard
   basis or manufacturer-specific evidence basis.
6. The evidence hierarchy is represented in the PDL schema.
7. Standards revisions participate in reproducible build hashes and
   dependency invalidation.

This is a **bootstrap completion criterion**, not a requirement to
implement every standards document before writing the first code.

## CODE-001 â€” Python code quality standards

All production Python source code, test code, and executable maintenance
scripts in the PartSmith repository shall conform to both the
[PEP 8 Style Guide for Python Code](https://peps.python.org/pep-0008/)
and the
[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

Where the two guides differ, the stricter applicable rule shall be used.
In particular, Python lines shall not exceed 79 characters, excluding
explicitly exempted generated files and third-party source material.

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
4. Generate
5. Validate
6. Review
7. Export
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
    pins: 16
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
    type: power_input

footprint:
  pad_count: 16
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
-   No duplicate pin numbers unless explicitly valid for the device
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
-   Duplicate pad
-   Incorrect numbering
-   Incorrect exposed-pad mapping
-   Pin/pad count mismatch
-   Pin-name/pad-number inconsistency

A component cannot receive a **PASS** result if this relationship has
unresolved errors.

------------------------------------------------------------------------

# 10. 3D Model Generation

B.F.T. shall generate a 3D representation of the physical component when
the supplied mechanical information is sufficient.

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
other. Final KiCad association is permitted only after both artifacts
have been independently generated and validated.

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
7.  Place the 3D model against the footprint in the B.F.T. 3D Viewer.
8.  Perform automated cross-validation.
9.  If discrepancies remain, report them rather than silently correcting
    them.
10. Only after successful validation, create/finalize the KiCad 3D model
    association.

------------------------------------------------------------------------

# 12A. Independent Artifact Principle --- Mandatory Rule

The footprint and 3D model are independent engineering artifacts.

B.F.T. SHALL:

1.  Generate the footprint from the Component IR, package definition,
    land-pattern requirements, and authoritative evidence.
2.  Generate the 3D model independently from the Component IR, package
    definition, mechanical requirements, and authoritative evidence.
3.  Never use the generated 3D model as authoritative input to determine
    pad locations or footprint geometry.
4.  Never use the generated footprint as authoritative input to
    determine 3D package geometry.
5.  Use shared authoritative package definitions where appropriate while
    preserving independent generator paths.
6.  Cross-validate the resulting artifacts after generation.
7.  Never silently move, scale, rotate, or mirror either artifact merely
    to make the two artifacts appear aligned.

Agreement between independently generated artifacts is a deliberate
cross-validation signal. Disagreement shall be treated as evidence of a
possible extraction, package-definition, coordinate-system, generator,
or source-data problem.

# 12. 3D Viewer / Placement Validator

The first B.F.T. tool shall include a **3D Viewer / Placement
Validator**. Its purpose is not merely to display a model; it is an
engineering validation interface for determining whether the
independently generated 3D model correctly belongs on the independently
generated footprint.

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
*.wrl
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
generator = bft_component_builder
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

## Initial provider targets

### OpenAI

Support user-supplied OpenAI API credentials.

OpenAI's current API uses API keys and supports multimodal input,
including image input, structured responses, tools, and file/search
workflows.

### Anthropic

Support user-supplied Anthropic API credentials.

Anthropic currently supports API-key authentication as well as other
production authentication methods.

### Google Gemini

Support user-supplied Gemini API credentials.

Gemini provides an API-key-based API and current documentation describes
multimodal and structured-output capabilities.

### GitHub Copilot

B.F.T. should treat **GitHub Copilot separately from GitHub Models**.

GitHub Models was retired on July 30, 2026, including its inference API
and BYOK capability. GitHub states that Copilot remains the GitHub
product for AI-powered workflows.

Therefore:

**Do not design B.F.T. around the retired GitHub Models API.**

For Copilot, the implementation should depend on the currently supported
GitHub Copilot extension/integration mechanism rather than assuming that
a normal Copilot subscription provides a general-purpose API key.

GitHub documents Copilot Extensions as an integration mechanism with
authorization and API access.

------------------------------------------------------------------------

# 15. Provider Interface

Conceptually:

``` python
class AIProvider:

    def analyze_document(self, document):
        ...

    def extract_component_data(self, pages):
        ...

    def generate_symbol_data(self, component_ir):
        ...

    def generate_footprint_data(self, component_ir):
        ...

    def generate_3d_model_spec(self, component_ir):
        ...

    def validate_component(self, component_ir, generated_data):
        ...
```

The provider must return structured data.

It must NOT be trusted to directly write arbitrary KiCad files.

------------------------------------------------------------------------

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
  16 pins
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

The B.F.T. component model should be designed so that package standards
can be incorporated.

Potential standards/data sources to investigate include:

-   JEDEC package standards
-   IPC footprint/land-pattern standards
-   Manufacturer package drawings
-   Manufacturer recommended land patterns

The user will separately investigate relevant JEDEC standards.

### Design requirement

Standards must be represented as **authoritative sources with
version/revision metadata**, not merely hard-coded assumptions.

Example:

``` yaml
standard:
  organization: JEDEC
  document: <standard identifier>
  revision: <revision>
  source: <reference>
```

The B.F.T. system should eventually be able to distinguish:

``` text
Manufacturer datasheet
        +
JEDEC package standard
        +
IPC land-pattern guidance
        ↓
Component definition
```

------------------------------------------------------------------------

# 31. Component Package Types

Initial MVP should support common packages first.

Suggested initial test families:

### Through-hole

-   Axial
-   Radial
-   DIP
-   TO packages
-   Connectors

### SMT

-   0402
-   0603
-   0805
-   SOT-23
-   SOT-223
-   SOIC
-   TSSOP
-   QFP
-   QFN
-   DFN
-   LGA
-   BGA

The package list should expand based on real test coverage rather than
being treated as a marketing checklist.

------------------------------------------------------------------------

# 32. Output Package

A successful component build should produce something similar to:

``` text
BFT_Component/
│
├── symbol/
│   └── BFT_Component.kicad_sym
│
├── footprint/
│   └── BFT_Component.pretty/
│       └── BFT_Component.kicad_mod
│
├── 3d/
│   └── BFT_Component.step
│
├── documentation/
│   └── source.pdf
│
├── bft/
│   ├── component.json
│   ├── provenance.json
│   ├── validation.json
│   └── build-report.html
│
└── README.md
```

------------------------------------------------------------------------

# 33. Component Manifest

Every generated component should have a machine-readable manifest.

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
POWER_INPUT
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
-   [ ] Output is reproducible from the same source and configuration.

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

A documented source-priority policy may be added later, but conflicting
authoritative information must remain visible.

------------------------------------------------------------------------

# 50. Non-English Datasheets

B.F.T. must support datasheets that are not written in English.

Initial design should support at least:

-   English
-   Simplified Chinese
-   Traditional Chinese
-   Japanese
-   Korean
-   German
-   French
-   Spanish

The architecture must allow additional languages to be added later.

------------------------------------------------------------------------

# 51. Language-Aware Extraction

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
    pin_count: 16

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
    thermal_pad_supported: true

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
  path: package.mechanical.body_height_mm
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
3.  An override is included in the build hash.
4.  Removing an override restores the prior derived/source value.
5.  Overrides require explicit user action.
6.  An override that creates a validation failure cannot produce `PASS`.
7.  Overrides affecting package topology, pin mapping, or
    safety-critical geometry require human review.

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

# 90. Independent Artifact Contract

The independent-generation rule is elevated to a release-gating
requirement.

``` text
                   Component IR
                  /             \
                 /               \
                ▼                 ▼
       Footprint Generator   3D Generator
                │                 │
                ▼                 ▼
          .kicad_mod             STEP
                │                 │
                └───────┬─────────┘
                        ▼
                Cross-Validation
```

Agreement is evidence that the package definition, coordinate
conventions, and generation processes are mutually consistent.

Agreement does **not** prove that both artifacts are correct; source
evidence and independent validation remain required.

# 91. Coordinate and Unit Contract

All internal B.F.T. geometry shall use:

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

Every 3D placement shall be representable as:

``` text
T = Translation × Rotation × Scale × Mirror
```

The implementation shall define a single canonical transform order and
use it everywhere.

The transform record shall include:

-   Source coordinate system
-   Destination coordinate system
-   Translation
-   Rotation
-   Scale
-   Mirror state
-   Units
-   Convention version

The implementation shall provide round-trip transform tests.

A transform that cannot be inverted or reproduced within tolerance shall
fail validation.

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

Electrical pin types shall be determined from manufacturer evidence and
explicit B.F.T. rules.

The system shall support at least:

``` text
input
output
bidirectional
tri_state
open_collector
open_emitter
passive
power_input
power_output
power_flag
no_connect
unspecified
```

`unspecified` is a legitimate intermediate state.

It is not acceptable for the AI to select an electrical type solely
because it is common for that pin name.

For example:

``` text
RESET
ENABLE
FAULT
SENSE
```

shall not be assigned an electrical type by name alone.

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
answer with the highest confidence.

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

The MVP should target Class A for supported package families.

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
tested rather than assumed. citeturn0search3turn0search20

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

# 102. Canonical Serialization and Hashing

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

Generated text artifacts shall be hashed after canonicalization unless
the exact byte representation is itself the release artifact.

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
    → invalidate cross-validation if footprint geometry changes
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

The manifest shall identify:

``` yaml
manifest:
  schema_version:
  component_id:
  build_id:
  build_status:

  source:
    documents:
    hashes:

  evidence:
    package:
    hashes:

  component_ir:
    schema_version:
    hash:

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
    count:
    ids:

  reproducibility:
    build_inputs_hash:
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

v0.8 build architecture acceptance means:

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

# 115. Recommended v0.8

The next specification should be implementation-level.

It should define:

1.  Exact JSON Schema for Component IR.
2.  Exact JSON Schema for PDL.
3.  Exact Evidence schema.
4.  Exact manifest schema.
5.  Generator API signatures.
6.  Deterministic geometry algorithms.
7.  Coordinate-transform implementation.
8.  First package-family PDL records.
9.  First supported KiCad version matrix.
10. PDF/OCR adapter interface.
11. AI provider adapter interface.
12. Persistent build database schema.
13. UI wireframes and state transitions.
14. CLI/API behavior.
15. Golden component fixture format.
16. Fault-injection harness.
17. CI/CD test gates.
18. Packaging and installation behavior.

------------------------------------------------------------------------

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

The compatibility architecture in this specification is intentionally
versioned because KiCad major releases can change file formats and are
not guaranteed to be forward-compatible. KiCad documentation identifies
native `.kicad_sym` symbol libraries, `.pretty` footprint libraries
containing `.kicad_mod` files, and separate 3D model files referenced by
footprints. These facts are used here only to define validation
boundaries; the implementation must validate against the specific KiCad
major version it claims to support.
citeturn0search3turn0search21turn0search24

------------------------------------------------------------------------

# Implementation Specification — Current Normative Baseline

## Purpose

v0.8 converts the architecture into an implementation contract.

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

Primary outputs:

``` text
component/
├── symbol/
│   └── *.kicad_sym
├── footprint/
│   └── *.kicad_mod
├── 3d/
│   └── *.step
├── evidence/
├── manifest/
└── report/
```

The implementation must support a headless build path so CI can generate
and validate components without opening the GUI.

# 117. Technology Baseline

The MVP reference implementation shall use:

``` text
Language: Python 3.12
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
change file formats and are not forward-compatible with older major
versions after saving.
citeturn0search0turn0search2turn0search6turn0search1

The implementation shall isolate KiCad-version-specific behavior behind
adapters.

# 118. Repository Structure

Recommended repository:

``` text
board-forge-tools/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── bft/
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

# 121. Component IR JSON Schema

The implementation shall maintain a machine-readable JSON Schema.

Representative structure:

``` json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "bft://schemas/component-ir/1",
  "type": "object",
  "required": [
    "schema_version",
    "identity",
    "pins",
    "package",
    "evidence",
    "validation"
  ],
  "properties": {
    "schema_version": {"type": "string"},
    "identity": {"$ref": "#/$defs/identity"},
    "pins": {
      "type": "array",
      "items": {"$ref": "#/$defs/pin"}
    },
    "package": {"$ref": "#/$defs/package"},
    "evidence": {"type": "array"},
    "overrides": {"type": "array"},
    "validation": {"type": "object"}
  }
}
```

The repository shall contain the complete schema, not merely an example.

# 122. Component Identity Schema

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

Validation occurs before generation.

Checks:

-   schema validity
-   required fields
-   duplicate pin numbers
-   impossible topology
-   contradictory dimensions
-   unresolved critical evidence
-   unsupported package
-   invalid units
-   invalid transforms

Only `IR_VALIDATED` can enter generation.

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

The final 3D reference path is attached only in a post-validation
association/finalization step. A pre-validation footprint artifact may
contain no 3D reference, or only a non-authoritative placeholder token.
In all cases, 3D geometry must never drive pad generation.

# 142. Land Pattern Algorithm

For a package with a manufacturer land pattern:

``` text
Use manufacturer coordinates
→ normalize units
→ validate pad count
→ validate numbering
→ validate pin-1
→ generate footprint
```

For a manufacturer land pattern:

``` text
Manufacturer coordinates
→ normalize units
→ validate against package/topology constraints
→ generate
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

Cross-validation shall compare independently generated artifacts.

Required checks:

``` text
pad count ↔ physical pin count
pad positions ↔ lead/pin positions
package center ↔ model center
pin 1 ↔ pin-1 marker
body extents ↔ model extents
model height ↔ package height
orientation ↔ coordinate contract
mirror state ↔ expected state
thermal pad ↔ exposed pad
```

No validator may "fix" either artifact.

# 149. Fault Injection for Cross-Validation

CI shall intentionally modify test 3D models:

``` text
+0.10 mm X offset
-0.10 mm Y offset
90° rotation
180° rotation
mirror X
mirror Y
2× scale
0.5× scale
wrong height
wrong pin-1 marker
```

Every injected fault must be detected.

# 150. Coordinate Transform Library

Provide:

``` python
@dataclass(frozen=True)
class Transform:
    translation_mm: Vec3
    rotation_deg: Vec3
    scale: Vec3
    mirror: MirrorState
```

Required functions:

``` python
compose()
invert()
apply_point()
apply_vector()
apply_bbox()
equivalent_within_tolerance()
```

All functions shall be deterministic.

# 151. Tolerance Engine

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

``` yaml
validation_result:
  id:
  category:
  rule_id:
  status:
  severity:
  message:
  evidence_ids:
  artifact_ids:
  measured:
  expected:
  tolerance:
```

Status:

``` text
PASS
FAIL
WARN
HUMAN_REVIEW
NOT_GENERATABLE
```

# 153. Blocking Rules

The following are release-blocking:

``` text
FAIL
HUMAN_REVIEW
NOT_GENERATABLE
```

unless an explicitly approved rule allows the specific warning.

Warnings must never be silently converted to PASS.

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

# 157. KiCad Integration Strategy

The implementation shall prefer supported KiCad interfaces over private
file manipulation when the required operation is available.

For KiCad 10, the implementation shall evaluate the IPC API and official
Python bindings for runtime integration. KiCad documents a headless IPC
API server and officially maintained Python bindings.
citeturn0search8turn0search1

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

# 159. Build State Machine

Implementation states:

``` text
SOURCE_RECEIVED
SOURCE_ANALYZED
EVIDENCE_COLLECTED
IR_BUILT
IR_VALIDATED
PACKAGE_IDENTIFIED
FOOTPRINT_GENERATED
3D_GENERATED
SYMBOL_GENERATED
ARTIFACT_VALIDATION
CROSS_VALIDATION
HUMAN_REVIEW
APPROVED
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

A reproducible build shall be determined by:

``` text
source hashes
+
evidence selections
+
IR
+
PDL revision
+
generator versions
+
B.F.T. version
+
configuration
+
approved overrides
```

Canonicalize all structured inputs first.

Then:

``` text
build_inputs_hash = SHA256(canonical_build_inputs)
```

# 167. Manifest Generation

The manifest shall be generated last from the completed build graph.

It shall include all artifact hashes and validation results.

The manifest itself receives a SHA-256 hash.

# 168. CLI

MVP commands:

``` bash
bft component inspect <source>
bft component extract <source>
bft component build <source>
bft component validate <build-id>
bft component review <build-id>
bft component export <build-id>
bft component diff <build-a> <build-b>

bft pdl list
bft pdl inspect <pdl-id>
bft pdl validate <pdl-id>

bft doctor
bft version
```

# 169. Build Command

Example:

``` bash
bft component build TPS62130.pdf \
  --kicad 10 \
  --output ./generated \
  --review
```

The command shall never auto-export a blocked build.

# 170. Non-Interactive CI Mode

``` bash
bft component build source.pdf \
  --ci \
  --fail-on-review \
  --fail-on-warning
```

CI mode shall produce machine-readable JSON results.

# 171. Review Command

``` bash
bft component review BUILD-ID
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
class ReviewService:
    def approve(self, build_id: UUID, reviewer: str) -> ReviewResult: ...
    def reject(self, build_id: UUID, reviewer: str, reason: str) -> ReviewResult: ...
    def override(
        self,
        build_id: UUID,
        path: str,
        value: object,
        reason: str
    ) -> Override: ...
```

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

Export shall create:

``` text
library/
├── symbols/
├── footprints/
├── 3d/
└── manifest/
```

# 175. Project Packaging

A generated component package shall be self-contained enough to
reproduce the component.

Recommended:

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

Placement edits shall update placement metadata, not rewrite the
underlying STEP geometry.

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

Initial package coverage:

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

At least one component shall be selected for each package family with
high-quality manufacturer documentation.

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

Run the same build twice.

Expected:

``` text
same IR hash
same artifact hashes
same validation results
same manifest content
```

If nondeterminism is unavoidable in a backend, it must be isolated and
normalized before release.

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

The effective configuration shall be stored in the build manifest.

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
POST /builds
GET  /builds/{id}
POST /builds/{id}/validate
POST /builds/{id}/review
POST /builds/{id}/approve
POST /builds/{id}/export
GET  /builds/{id}/manifest
GET  /builds/{id}/evidence
GET  /builds/{id}/artifacts
```

The API is optional for the first desktop MVP but the internal service
boundaries shall support it.

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

# 205. Plugin/Extension Model

The following shall be replaceable:

``` text
AI provider
OCR engine
PDF parser
3D backend
KiCad adapter
storage backend
```

Core schemas and validation rules remain B.F.T.-owned.

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
older schema.

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
citeturn0search0

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

KiCad 10 documentation supports both packed `.kicad_sym` libraries and
unpacked symbol-library directories. citeturn0search0

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

Export shall use:

``` text
temporary directory
→ validate
→ hash
→ atomic rename
```

A partially generated library shall never be presented as a successful
export.

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

The mapping engine shall compare:

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

# 228. Mapping Failure Rules

Failures include:

``` text
missing mapping
duplicate mapping
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
no duplicate pin numbers
no duplicate pin names unless explicitly permitted
pin orientation valid
pin lengths valid
reference/value fields present
footprint field valid
```

# 231. Footprint Quality Rules

MVP footprint checks:

``` text
all pads have unique numbers
pad count correct
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

## Milestone 1 --- Foundation

Implement:

-   repository
-   schemas
-   IDs
-   evidence objects
-   SQLite
-   configuration
-   hashing
-   basic CLI

## Milestone 2 --- PDL

Implement:

-   PDL schema
-   first 8 package variants
-   topology engine
-   package resolver

## Milestone 3 --- Deterministic Generators

Implement:

-   symbol generator
-   footprint generator
-   3D generator
-   CadQuery/OCP/OCCT adapter

## Milestone 4 --- Validators

Implement:

-   schema
-   topology
-   mapping
-   footprint
-   3D
-   cross-validation

## Milestone 5 --- Document Intelligence

Implement:

-   PDF parser
-   OCR
-   page classifier
-   evidence extraction
-   AI adapter

## Milestone 6 --- Review UI

Implement:

-   evidence viewer
-   IR editor
-   package review
-   2D/3D viewer
-   validation panel
-   override system

## Milestone 7 --- KiCad Integration

Implement:

-   KiCad adapter
-   CLI discovery
-   headless validation
-   project-local library installation
-   library-table handling

## Milestone 8 --- Release Hardening

Implement:

-   reproducibility
-   golden corpus
-   negative corpus
-   security tests
-   CI
-   packaging

# 236. MVP Definition of Done

PartSmith MVP is complete when a supported golden component can:

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

and the complete process is reproducible from recorded inputs.

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

The first code should not start with the AI. This is the **engineering
bootstrap milestone**, not a claim that the full PartSmith MVP is
complete.

The recommended implementation order is:

``` text
Schemas
↓
PDL
↓
Component IR
↓
Deterministic generators
↓
Deterministic validators
↓
Golden tests
↓
Document extraction
↓
AI interpretation
↓
Review UI
↓
KiCad integration
```

This ordering ensures that AI is plugged into a known engineering
framework rather than becoming the framework.

# 239. First Package Definition Set

Create and validate PDL records for:

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

All must fail at deterministic validation.

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

Before declaring v0.8.2 specification-ready:

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

# 245. Implementation Boundary and Repository Bootstrap
# Appendix --- Current KiCad Reference Basis

The implementation targets KiCad 10 initially. KiCad's current
documentation describes native `.kicad_sym` symbol libraries, `.pretty`
footprint libraries containing `.kicad_mod` files, project/global
symbol-library tables, and the KiCad 10 IPC/Python integration path.
KiCad also states that major releases commonly change file formats and
that files saved by a newer major release are not generally readable by
older major releases. These facts are why B.F.T. uses a versioned KiCad
adapter and compatibility matrix rather than assuming universal
compatibility.
citeturn0search0turn0search2turn0search6turn0search1turn0search8

------------------------------------------------------------------------

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
