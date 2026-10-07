# Phase 13.4 staging design preparation

Design only, recorded 2026-10-06. Implementation must wait for recorded 13.3
PASS. This document supplies no stage, validation, authorization or publication
result. The current specification's 13.4 requirements and section 174.1 govern
the eventual service; the existing required rules are `MAPPING`, `NATIVE_PARSE`,
`PATH_RESOLUTION` and `SEMANTIC_PRESERVATION`.

The staging service should receive an immutable hash-verified 13.3 plan, its
exact approved release closure and the complete verified target/base inventory.
It must resolve final symbol, finalized footprint and STEP bytes from their
existing release identities. It should not rerun component generators or
reconstruct final releases from IR, previews or imported approval labels.

Use an owned isolated stage for the complete generation. The plan controls
logical paths and names: the packed `BFT_Symbols.kicad_sym`, the declared
`.pretty` library, STEP layout, both project-local library tables and all other
files required by the proven complete-project publication boundary. Preserve
unrelated entries and project bytes only under the plan's explicit verified
policy. No staging path, run ID, local absolute root or future manifest digest
may enter deterministic file bytes or validation content. The active junction
is operational root resolution, recorded separately in audit.

Use a bounded token-preserving S-expression parser for supported released
formats. It must handle quoted strings and escaping, parse finite decimal
tokens without floats, reject malformed/trailing content and resource excess,
and preserve entry ordering and every engineering token. The current symbol
and footprint validation regexes check selected generated fields; they are
insufficient for whole-entry semantic preservation.

Pack symbols by deterministic plan order under one versioned library header.
Use source entry bytes or equivalent complete tokens rather than re-emitting
geometry from component IR. A versioned closed relocation allowlist should
identify exact structural locations and old/new values: outer symbol name,
derived unit-symbol name prefixes when explicitly required, footprint root name,
symbol-to-footprint library identifier and STEP reference path. No pin name,
number/type, graphic, pad field, layer, model offset/scale/rotation, mirror or
electrical property may change through a broad text replacement. Unknown grammar
or an undeclared change fails until supported by an explicit comparator version.

There is a concrete mapping decision to settle in the 13.3/13.4 contract: the
current released symbol serializer emits Reference and Value but no Footprint
property. Do not silently add this property under a rename-only rule. Either
keep the plan's externally bound mapping and test explicit native footprint
assignment, or define a narrowly versioned source-bound mapping-property
insertion rule and bind it in the frozen plan/comparator. In either case, the
approved source symbol and component release bytes stay unchanged. Inserting
an arbitrary property without a reviewed rule is a semantic failure.

For every added and retained component, produce a structural comparison of
source versus its exact staged symbol/footprint entry after reversing only the
declared relocations. Compare the complete AST/token content, not just pin/pad
counts. Independently compare source symbol pin identity/type/mapping to the
associated footprint terminal inventory; duplicate physical pad groups require
the source PDL's explicit mapping rather than an assumed one-pad-per-pin rule.
Require all packed entries to have exactly one declared source component and
reject missing/extra entries, duplicate names, conflicting nicknames and aliases.

STEP is copied byte-for-byte and verified by its approved hash and length.
Every staged model reference must resolve inside the complete generation from
the declared native project context, with Windows case/Unicode/device aliases,
escaping reparses and unmanaged collisions rejected. If `${KIPRJMOD}` is used,
its native resolution must be checked against the owned project-generation root.
Offset, rotation, scale and mirror values remain those of the finalized release;
the PCB inspection point adapter is not a blanket 3D placement conversion.

Native validation should use the pinned 10.0.6 CLI against the exact staged
packed symbol and complete footprint library. Existing `sym upgrade --force`,
`sym export svg`, `fp upgrade --force` and `fp export svg` calls provide real
parse/round-trip/render boundaries. Preserve their output as separate evidence;
never replace staged artifacts with upgraded or rendered output. Check successful
outputs for every expected component, with no missing or extra entry. Native
validation and reference resolution require the whole stage and project-local
tables, since validating individual detached files alone can miss broken paths.
All native workers obey resource policy 1.0 and its 120-second native deadline;
IPC inspection keeps its separate 15-second limit.

Freeze staged file identities and deterministic check results first. Results
bind the exact plan, target, expected base, source set, staged bytes and versions,
with an outcome for every required rule. Separate run telemetry and diagnostic
renders from deterministic rule content. Build the installation manifest only
after those bytes/checks are fixed, then perform post-manifest verification in a
separate report. The external canonical manifest hash identifies the generation.
Any staged-byte or mapping edit invalidates its bound checks and authorization.

Acceptance needs two independent clean stages with identical bytes, check hashes
and manifest identity; two components with a one-component update preserving
the other's complete engineering tokens and source bindings; allowed exact
relocations; and deliberate pin/type/mapping, pad geometry/layer, model placement,
path, extra/missing entry and STEP tampering faults. Include Windows aliases,
resource exhaustion, native parser failure, disk failure, mutation after checks
and source-store byte preservation. This service performs no target publication
and cannot grant integration approval.

Native editor quiescence and mutable project-file preservation must use the
publication mechanism's declared checks, not only absent `.lck` files. The
[pinned lock implementation](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/include/lockfile.h)
creates a same-directory advisory marker and closes its handle; its absence is
not an exclusion lock. Marker spelling derives from the
[pinned prefix/extension constants](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/wildcards_and_files_ext.cpp):
`foo.kicad_pcb` maps to `~foo.kicad_pcb.lck`. No dirty-state or close/reopen IPC
capability has been validated by the current read-only adapter. Those workflow
checks must remain explicit before later publication and rollback.
