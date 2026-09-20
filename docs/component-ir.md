# Component IR — contract and implementation status

The IR contract is now part of the normative
[PartSmith Implementation Specification, section 121](../resources/BFT_PartSmith_Implementation_Spec.md#121-component-ir-json-schema-and-contract).
That section is the authoritative text; this page remains as a navigation
entry for existing links.

Specification **v0.9.6** retains IR 1.2 and canonical JSON profile 1.0. The
[IR 1.2 gate report](gates/phase-2-ir-1.2.md) records verification against v0.9.5;
its unchanged Phase 2 scope remains the prerequisite for Phase 3. New v0.9.6
downstream services and snapshot profile 1.2 remain later-phase requirements.
The [fresh Phase 2 verification against v0.9.6](gates/phase-2-v0.9.6.md)
records 280 passing tests in both the source and isolated-wheel installations.
IR 1.1 has a recorded
[Phase 2 PASS against v0.9.4](gates/phase-2-ir-1.1.md). IR 1.0 remains supported;
older schemas, fixtures, and gate evidence retain their original versions.
The IR 1.2 API additions are below; the later IR 1.1 examples remain valid for
that version.

- [Target schema and record structure](../resources/BFT_PartSmith_Implementation_Spec.md#1211-normative-component-ir-12-contract)
- [API and validation behavior](../resources/BFT_PartSmith_Implementation_Spec.md#1212-component-ir-api-and-validation-behavior)
- [Canonical JSON, numeric limits, units, paths, and hashing](../resources/BFT_PartSmith_Implementation_Spec.md#1213-canonical-profile-10)
- [Fixtures, packaging, and Phase 2 scope](../resources/BFT_PartSmith_Implementation_Spec.md#1214-fixtures-packaging-and-phase-2-scope)
- [Structured provenance](../resources/BFT_PartSmith_Implementation_Spec.md#1215-structured-provenance-records)
- [Target typed overrides](../resources/BFT_PartSmith_Implementation_Spec.md#1216-typed-overrides-and-target-bindings)
- [Target candidate relevance and transitions](../resources/BFT_PartSmith_Implementation_Spec.md#1217-candidate-relevance-and-revision-transitions)
- [Target resolution history](../resources/BFT_PartSmith_Implementation_Spec.md#1218-resolution-history-and-active-selections)
- [Snapshot profiles and scoped dependencies](../resources/BFT_PartSmith_Implementation_Spec.md#166-reproducible-build-algorithm)
- [Persisted revisions and transaction boundaries](../resources/BFT_PartSmith_Implementation_Spec.md#163-persistence-model)
- [Input and release review services](../resources/BFT_PartSmith_Implementation_Spec.md#172-review-decision-api)
- [Installation aggregates and authorization](../resources/BFT_PartSmith_Implementation_Spec.md#1741-installation-aggregates-and-approval-boundaries)
- [Portable history and offline rebuild bundles](../resources/BFT_PartSmith_Implementation_Spec.md#175-project-packaging)
- [Existing IR 1.0 JSON Schema](../schemas/component-ir-1.0.schema.json)
- [IR 1.1 JSON Schema](../schemas/component-ir-1.1.schema.json)
- [IR 1.2 JSON Schema](../schemas/component-ir-1.2.schema.json)
- [Recorded IR 1.0 Phase 2 gate evidence](gates/phase-2.md)

## IR 1.2 generation prechecks and history

```python
import json
from pathlib import Path
from partsmith.ir import (
    ComponentIR,
    MemoryRevisionStore,
    RequirementsContext,
    validate_ir,
)

ir = ComponentIR.from_file("fixtures/ir/v1.2/valid/0402.json")
inventory = json.loads(
    Path("fixtures/ir/v1.2/history/inventory.json").read_text()
)
store = MemoryRevisionStore([ir], [inventory])
paths = (
    "/identity",
    "/electrical",
    "/pins",
    "/package",
    "/footprint",
    "/model_3d",
)
context = RequirementsContext(
    "synthetic", "test-1", "test-1", "test-1", paths, paths
)
assert (
    validate_ir(
        ir.data, for_generation=True, requirements=context, revisions=store
    )
    == ()
)
```

`RevisionStore` exposes `get_revision(id)` and `get_inventory(sha256)`. The memory
implementation copies canonical bytes and returns detached data. Missing parents,
changed stored IDs, edited historical records, incomplete inventories, unreviewed
candidates, and invalid active selections block generation. Structural loading
alone does not verify external revision history or grant build approval.

`validate_revision_transition(previous, current)` returns sorted Issue records.
It enforces parent/component identity, retained evidence/decisions/documents,
append-only review history, explicit replacement/removal, and terminal rebindings.
Pending proposals become new approved decision records; old proposals and old
approvals remain immutable. Phase 8 supplies persisted revisions and typed input
review services; Phase 12 connects the UI. Those services will review inputs
before generation and approve final releases separately. Their stale-base checks,
atomic decision commits, and supported pin-edit sequencing are specified future
service behavior, not additional operations exposed by today's IR helpers.

The trusted editable-path registry is implemented in `partsmith.ir.targets`.
It supports typed value/quantity records, pin records/arrays and listed pin leaves,
placement records/vectors/scalars/mirrors, and the land-pattern source enum.
It excludes record IDs, source history, status fields, output reports, and selectors.

## IR 1.2 migration

`migrate_v1_1_to_v1_2(ir, supplied_evidence)` returns `MigrationResult`, preserving
the original bytes/hash. Supply:

- `reason` and a new `revision` with explicit active selectors, inventory review,
  exclusions and rebindings; legacy ancestry is retained separately in migration
  history, while imported 1.2 roots reference retained 1.2 snapshots.
- `accuracy_class`, supported by retained evidence.
- `evidence`, keyed by every retained ID, containing acquisition_revision_id,
  candidate_targets and a complete source record with converted region metadata.
- Complete revised `overrides`, `resolutions`, and `validation_results` when the
  source contains them. Original content cannot be silently rewritten or dropped.

Absent relevance, coordinates, decision bindings, or result classifications produce
migration issues. IR 1.0 migrates through the existing 1.0→1.1 function first.
Successful migration creates a structurally valid candidate; generation still
requires a valid revision/inventory store and trusted requirements.

## Dependency projections — implemented profile 1.1

`dependency_projection(ir, requirements=..., revisions=..., configuration=...)`
returns snapshot-profile 1.1 canonicalizable content; `dependency_hash` hashes it.
Configuration contains nonempty `pdl`, `release_profile`, `runtime`, and `exporter`
objects. Runtime requires python/cadquery/ocp/occt/generator/validator versions;
the release profile requires id/version/accuracy_class. The trusted caller supplies
all engineering configuration and excludes secrets; these helpers never read `.env`.

Record IDs become referenced content hashes. Active override bindings hash once;
previous values, superseded decisions, reviewer identities/times and output reports
remain audit data. Source revisions, selected evidence, decisions/reasons, and
required engineering inputs remain significant. Canonical profile 1.0 is unchanged.
Frozen projection fixtures are in `fixtures/ir/v1.2/expected`.

These helpers implement the Phase 2 projection contract. They do not implement
the Phase 8 build orchestrator, full release manifests, final artifact checks,
or a production PDL/CAD backend. Applicability declarations and CLASS_A geometry
are verified against production fixtures/PDL in their later gates.

Specification v0.9.6 defines **snapshot profile 1.2**, which is not implemented
by these helpers. It retains the provenance edge rules while giving each
generator, finalizer, and validator a trusted declaration of the configuration
it consumes. Complete build snapshots retain the full runtime configuration;
symbol and footprint geometry dependencies exclude unused CAD settings.
Phases 4–6 implement and test the generator declarations, and Phases 8–9 add
complete snapshots, invalidation, and reproducibility verification. Profile 1.1
APIs and golden hashes keep their original scope.

The later bundle/import service must retain the revisions and inventories
needed to validate history, distinguish locally verified OFFLINE_COMPLETE
bundles from RETRIEVAL_REQUIRED distributions, and reject missing or tampered
history. The current migration helpers create candidates; they do not perform
that bundle import or transfer release approval. Shared-library installation
will validate and authorize new aggregate files separately from immutable
approved component bundles. These contracts are linked above.

## IR 1.1 generation precheck API

IR 1.1 generation validation requires `RequirementsContext`. Trusted adapter
code supplies its pinned versions, mandatory paths, requested paths (a superset
of mandatory paths), and PDL-declared optional features permitting zero. IR and
user configuration must not supply or weaken the adapter's mandatory declaration.
Phase 2 fixtures use synthetic contexts; production contexts arrive with PDL
and generators. The precheck does not assign build state or grant approval.

```python
from partsmith.ir import ComponentIR, RequirementsContext, validate_ir

ir = ComponentIR.from_file("fixtures/ir/v1.1/valid/0402.json")
paths = ("/identity", "/pins", "/package", "/footprint", "/model_3d")
context = RequirementsContext(
    artifact="synthetic-test",
    generator_version="test-1",
    pdl_version="test-1",
    rule_version="test-1",
    mandatory_paths=paths,
    required_paths=paths,
)
assert validate_ir(ir.data, for_generation=True, requirements=context) == ()
```

## Migration API

`migrate_v1_0_to_v1_1(ir, supplied_evidence)` accepts a dictionary or `ComponentIR`
and returns `MigrationResult(ir, history, issues)`. `ir` is a new immutable
`ComponentIR` on success, otherwise `None`; `issues` contains sorted diagnostics.
`history` is canonical JSON bytes recording source/target hashes, the supplied
evidence hash, reason, migration version, and success/failure. Persist the history
alongside the original record and supplied evidence; original records are unchanged.

Supplied evidence fields:

- `reason`: required explanation of the evidence supporting the migration.
- `placement`: required complete convention-1.1 placement with evidence links;
  the legacy coordinate convention cannot be inferred automatically.
- `source_document_id`: required when the authoritative document is ambiguous.
- `document_revisions`: revision and optional `revision_basis`, keyed by source
  ID, when the legacy document lacks revision information.
- `land_pattern_source`: required to disambiguate STANDARD or USER_OVERRIDE;
  MANUFACTURER maps directly to MANUFACTURER_RECOMMENDED.
- `standards`: complete structured records keyed by ID when legacy standards
  exist; existing revision/reference information cannot be silently changed.

`load_schema()` retains its IR 1.0 default for compatibility; use
`load_schema("1.1")` or `load_schema("1.2")` explicitly for those versions.
Record loading dispatches
on `schema_version` and rejects unsupported versions. Whole-record hashing
includes history. The implemented IR 1.2 profile 1.1 dependency helpers are
described above; complete build caching and profile 1.2 remain later-phase work.
