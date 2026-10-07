# Phase 13.4 — deterministic semantic staging

PASS, 2026-10-06, after actual native checks and affected-hash closeout.
No publication or installation approval is claimed at this checkpoint.

The stager freshly resolves every complete historical approval against the
authoritative release database. It builds an isolated complete project generation
and preserves unrelated files, empty directories and complete library-table
nodes. Mutable project files remain outside the installation identity. Original
source artifacts remain unchanged in the component store.

Adapter/serializer/comparator 1.0 supports the released single-entry symbol format.
The closed mechanical relocation rules change outer symbol names, derived unit
name prefixes, footprint entry names, the symbol Footprint property and model URI.
The Footprint property may be inserted when absent, using only the plan's declared
footprint identity. Other properties, pins, electrical types, geometry, layers,
model offset/scale/rotation and numeric spelling remain exact. STEP is copied
byte-for-byte. Unsupported versions or grammar fail.

Complete expected trees are derived from the original approved bytes and compared
against the exact staged files, including every unchanged retained component.
The comparator rejects extra/missing files and entries, changed table nodes,
pin/pad terminal discrepancies and every engineering-token change outside the
allowlist. Native KiCad 10.0.6 independently upgrades/parses and exports SVG for
every packed symbol unit and footprint. A disposable board exports the actual
project-relative models through native KiCad; CAD solid counts and volume must
match the unchanged source STEP models. Diagnostic boards and exports never
replace engineering artifacts.

Pre-manifest results bind fixed final files, sources, target and base. The external
canonical installation manifest hash identifies the generation. Post-manifest
results separately bind that exact manifest. Native paths/output transport hashes
are operational telemetry, excluded from deterministic identity. A revalidation
service reruns trusted source, semantic and native checks and reconstructs the
expected reports and manifest; imported PASS text cannot establish authority.

Two independent clean stages produce identical files, checks and manifests.
Updating one approved component preserves the other complete symbol tree,
footprint, STEP and source bindings. Fault tests cover pin number/name/type/position,
pad geometry/layers, model placement/reference, properties, extra/missing entries,
STEP/table tampering, edits after/during checks, target concurrency, disk/permission
failure and native refusal. Target and source database identities remain unchanged
on pure staging and failure. Explicit stage persistence leaves commit/rollback
under caller ownership.

Initial negative results are retained: the first output inventory assumed SVG
names without KiCad's unit suffix; the next model export incorrectly assumed the
diagnostic board body thickness. The final exporter excludes the board body and
compares only component solids/volume, with a 0.00001-mm3 CAD tolerance.

Validation: the combined staging/planner/store/parser/contract run records 162
passing checks in `phase-13.4-final-source-results.xml`. The final staging run
records 25 passing checks in `phase-13.4-revalidated-source-results.xml`; these
overlap the combined run and are not added to claim unique test counts. Ruff
passes. `scripts/verify_integration_staging.py` records two further real native
stages, exact contracts, files, transport receipts and the unchanged source
fixture database under `phase-13.4-native-staging/`. Each native model readback
contains six solids totaling approximately 0.39 mm3. Source database hashes are
identical before/after staging. A metadata encoding setup failure is archived
separately; canonical JSON retains exact decimal values in the final receipt.

`scripts/close_integration_gate.py --phase 13.4` refreshes and verifies every
active/CI manifest. Its closeout records affected previous/new hashes and disk
verification. Git-blob verification follows a user commit. The full Phase 13
gate remains pending through 13.5–13.8.
