# Phase 13 PCM installation correction

Specification v0.9.7 addendum, 2026-10-05, requested by the project owner.
The [updated specification](../resources/BFT_PartSmith_Implementation_Spec.md#phase-13--kicad-integration)
requires a KiCad Plugin and Content Manager (PCM) ZIP as the customer plugin
artifact. The subsequent [PCM-only update](spec-phase-13-pcm-only-update-2026-10-05.md)
removes the former internal PartSmith wheel build/test requirement from Phase 13.
No plugin
implementation, published package or Phase 13 milestone PASS is claimed.

The [prior specification](../resources/history/BFT_PartSmith_Implementation_Spec_v0.9.7_before_PCM_2026-10-05.md)
is retained byte-for-byte. R13-01 remains REASSIGNED_OPEN to 13.1; the eight
ordered milestones and existing Phase 12 runtime evidence retain their scope.

## Documentation and pinned-build review

KiCad's [addon guide](https://dev-docs.kicad.org/en/addons/index.html) defines the
PCM ZIP layout and package metadata. The [version 10 manual](https://docs.kicad.org/10.0/en/kicad/kicad.html#_installing_packages)
describes local-file/repository installation and PCM lifecycle controls.
The [IPC guide](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
describes action registration and managed Python/executable runtimes.

The [10.0.6 loader source](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp)
reads requirements.txt for environment preparation and passes binary-only flags
to pip. The [10.0.6 action schema](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/api/schemas/api.v1.schema.json)
describes min_version as not yet used. The installed 10.0.6 schemas were also
read; their exact identities are retained in the correction receipt. These
sources guide requirements; actual target behavior still needs milestone proof.

## Changes and acceptance ownership

| Location | Required change |
| --- | --- |
| 13.2 | Schema-tested deterministic PCM ZIP, archive/repository metadata separation, package layout, runtime selection and real lifecycle checks |
| 13.2 Python runtime | Verify Python 3.12, pinned dependency closure and available binary packages; show background preparation/errors/recreation; declare network and offline behavior |
| 13.2 executable runtime | Permit an owned bundled runtime/application with inventory/license/runtime and real PCM launch proof |
| 13.7 | Exercise the PCM-installed action without a checkout or manually installed PartSmith wheel; retain project/component data through lifecycle operations |
| 13.8 | Validate source regressions, the exact final ZIP/runtime and PCM lifecycle; mocks/manual copies cannot substitute; no PartSmith wheel builds/tests |
| 174.1.5 | Distinguish PCM metadata, IPC registration and optional local PartSmith launcher data; allow a verified KiCad-managed environment and preserve legacy migration |
| Phase 14 | Use the verified PCM mechanism for clean-machine/offline production proof; do not require a separate customer OS installer |

Package files/environment caches are disposable. Component databases, history,
secrets, journals and generated project libraries remain application/project
data outside those paths. Installing/updating plugin software cannot authorize
or perform a component-library publication. PCM lifecycle success does not
replace 13.3–13.6 integration approval, transaction and rollback requirements.

## Validation scope

This correction changes specification/docs and current input maps only. Runtime
code, dependencies, schemas and installed plugin data remain unchanged; no new
PCM ZIP is built or installed. Prior source/wheel test runs keep their exact
identities and historical scope. Structural/link/ownership checks, unchanged
runtime-resource byte checks, final active/CI input maps and current-gate
artifact references are verified against final disk bytes under the repository
closeout instructions. Git-blob verification remains due after committing.

See the [correction receipt](gates/phase-13-pcm-spec-update-2026-10-05.json)
for commands/results, prior-document/manifests and final identities.
