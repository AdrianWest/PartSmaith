# Phase 13 preparatory pinned-target discovery — 2026-10-06

Status: **READ_ONLY_PREPARATORY_DISCOVERY**. This is neither milestone 13.2
implementation nor PASS evidence. No plugin/dependency was installed, no native
UI was opened, and no project/library target or existing gate file was changed.
New helper/evidence files are the only writes. Installation-dependent work
remains gated on recorded 13.1 PASS and its required hash closeout.

Machine-readable discovery is in
[phase-13-discovery-2026-10-06.json](phase-13-discovery-2026-10-06.json).
The probe is `.tools/phase13-discovery/discover.py`, executed with the existing
project Python 3.12 interpreter. Public package metadata and the released IPC
binding archive were fetched for inspection; third-party code was not installed
or executed.

## Observed installed target and external runtime

| Surface | Observed value |
| --- | --- |
| Native CLI | KiCad 10.0.6; subcommands `fp`, `jobset`, `pcb`, `sch`, `sym`, `version` |
| Windows | AMD64; version 10.0.26200 |
| Workspace volume | C: NTFS; `Get-Volume` reports Healthy |
| Existing external interpreter | CPython 3.12.10 AMD64 |
| Existing CAD | CadQuery 2.8.0; cadquery-ocp/proxy 7.9.3.1.1; OCP reports OCCT 7.9.3.1 |
| Existing viewer/schema | wxPython 4.3.1; VTK 9.6.2; jsonschema 4.26.0 |
| Embedded legacy KiCad Python | 3.11; unsuitable for the required PartSmith Python 3.12 generation boundary |
| Installed schemas | `api.v1.schema.json`, `pcm.v1.schema.json`, `pcm.v2.schema.json`; exact hashes in JSON |

Version/import observation does not replace the repository's engineering
`runtime_configuration` checks of reviewed native bytes, licenses and the full
dependency lock. The configured KiCad IPC external interpreter and its managed
environment have not been inspected or changed.

## PCM registration and runtime boundary

The installed PCM v2 schema permits a version's `runtime: "ipc"`,
`platforms: ["windows"]`, and KiCad minimum/maximum both `10.0.6`. The portable
archive must contain root `metadata.json`, direct `plugins/plugin.json`,
`plugins/requirements.txt`, and owned entry/source/resources under `plugins/`.
PCM provides the installed package namespace. Archive metadata has one version
and omits all `download_*` values; repository metadata is constructed after ZIP
hash/size calculation. Package identity, license and a complete inventory are
required. Installed schema acceptance alone is insufficient because its
properties are not universally closed.

Installed API registration permits runtime type `python` or `exec`;
`min_version` explicitly does not enforce the interpreter. Use PCB scope only
for this build. The package registration, IPC action registration and optional
local PartSmith launcher are three separate contracts. Stable IDs and fixed
relative entrypoint/resource paths fit the installed schema.

The [10.0.6 loader](https://gitlab.com/kicad/code/kicad/-/raw/10.0.6/common/api/api_plugin_manager.cpp)
creates a per-plugin environment from the configured external interpreter using
`venv --system-site-packages`, upgrades pip, then installs requirements with
`--isolated --only-binary :all: --require-virtualenv`. Actions enter its ready set
after successful requirement installation. Application diagnostics must then
gate engineering readiness on the actual Python/CAD/resource lock, since pip
success alone cannot establish that. The loader supplies transient IPC endpoint
and token values when invoking an action. Environment recreation is a loader
operation, not registry editing.

Python IPC is feasible with a verified external Python 3.12 selection and full
pinned binary supply, but the default embedded interpreter cannot satisfy the
current engineering requirement. A bundled executable is the alternative if
its complete runtime/resources/licenses and PCM launch are proven. Neither
mechanism is selected or validated by this discovery. Python offline readiness
must also account for the loader's pip-upgrade stage; a ZIP alone is insufficient.

## Exact official binding and candidate dependency closure

The [official released `kicad-python` 0.8.0 metadata](https://pypi.org/pypi/kicad-python/0.8.0/json)
and its released wheel identify `KICAD_API_VERSION =
"10.0.6-0-gcaf7377e9c"`, an exact match for the target. The binding archive is
`kicad_python-0.8.0-py3-none-any.whl`, SHA-256
`3d43af4aa2515e88829a9d30e408b8ce89537431a802104ee2a50392f0deaa16`.
The [tagged source](https://gitlab.com/kicad/code/kicad-python/-/tree/0.8.0)
must govern calls and units rather than latest-development examples.

Candidate pins satisfy the release's declared ranges and each has a published
CPython 3.12 Windows AMD64 or compatible universal/ABI3 wheel:

```text
kicad-python==0.8.0
protobuf==5.29.6
pynng==0.9.0
cffi==2.0.0
pycparser==2.23
sniffio==1.3.1
typing-extensions==4.16.0
jsonschema==4.26.0
attrs==26.1.0
jsonschema-specifications==2025.9.1
referencing==0.37.0
rpds-py==2026.6.3
```

The JSON records exact wheel hashes and dependency metadata. These are
discovery candidates, not an executed resolver/preparation or installed lock.
The GUI, PDF and CAD dependency closure must be added without changing reviewed
engineering identities merely to accommodate IPC.
The CFFI/parser pins deliberately retain `requirements-extraction.txt` versions.

The [official add-on guide](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
limits KiCad 9/10 IPC to a running PCB Editor; schematic IPC and headless API
are later capabilities. Windows transport uses a named pipe. Clients must pass
the explicit launching/selected endpoint and token, then verify version and exact
board/project context. The released binding's default constructor may choose a
default pipe and `get_board()` picks the first document, so neither default is
appropriate for exact session binding. Enumerate open PCB documents, require
the expected board, and perform read/inspection against that explicit document.
Record no token values or hashes. Native CLI/editor evidence provides schematic
coverage separately.

The tagged binding's
[geometry wrappers](https://gitlab.com/kicad/code/kicad-python/-/blob/0.8.0/kipy/geometry.py)
store `Vector2` coordinates as integer nanometers and `Angle` values as float
degrees. Its positive 90-degree planar rotation sends native positive X toward
negative Y. PartSmith section 92 defines a top-view right-handed frame with
positive X right and positive Y up. An exact-decimal adapter should scale mm by
1,000,000 for nanometers, explicitly map the native Y axis, validate range and
precision, and verify cardinal angles/mirrors and round trips. Binding float
convenience helpers must not become the exact-decimal conversion authority.
These are source observations; real API and native geometry fixtures remain due.

## Complete-generation publication feasibility

Ordinary Windows replacement cannot be treated as multi-file atomic
publication. [MoveFileEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa)
rejects an existing directory destination and requires a directory move to stay
on the same drive. Two renames that move the old directory aside and then move
the new directory into place expose a gap. `os.replace` of independent symbol,
footprint, model and table files exposes mixed generations.

[FILE_RENAME_INFORMATION](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information)
documents POSIX replacement behavior for existing **file** handles, while its
general rules still reject directory destinations. It is not evidence that a
directory junction replacement through NtSetInformationFile is supported.

A narrower, testable candidate is an **owned stable project-root junction**
pointing to an immutable complete generation. Each generation contains the
project files, `sym-lib-table`, `fp-lib-table`, packed symbols, `.pretty`
footprints, models and installation manifest. References use native
`${KIPRJMOD}/...` within the complete root. A single in-place reparse-data update
retargets the owned junction; no table/file is separately published.

[Reparse Point Operations](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations)
permits modifying an existing reparse point through `DeviceIoControl` on a
handle opened with `FILE_FLAG_OPEN_REPARSE_POINT`.
[FSCTL_SET_REPARSE_POINT](https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-set-reparse-point)
requires the existing tag to match. Microsoft's
[WinFile junction implementation](https://github.com/microsoft/winfile/blob/master/src/lfn.c)
opens an existing junction without following it and sets its replacement target
in one control call. This establishes a concrete prototype path; the sources
do not, by themselves, prove the required crash/publication guarantee on this
machine.

The adapter must acquire its exclusive installation lock, open the actual owned
junction without following it, compare its complete expected target/manifest
and reparse data, persist the journal, recheck staged/base bytes, set the new
same-tag target in one operation, then verify the resolved complete generation.
Tag validation is not a compare-and-swap on the previous target; ownership,
locking and exact read-back remain mandatory. No unknown reparse target or
symlink escape may be accepted. Native editors must be closed/quiescent before
publication and reopened against the stable path afterward; a loaded board or
cached library must not be presented as refreshed without executable evidence.

Initial support can cover only a new owned stable junction target on local
NTFS, followed by updates and rollback through that same junction. Converting
an arbitrary existing ordinary project root, changing loose global tables,
cross-volume staging, shares, unsupported filesystems and open/dirty editors
remain unsupported unless separately proven. Atomic retarget of a root does
not establish a consistent multi-file read for a reader that continues across
the switch; editor quiescence and fresh cache resolution are necessary.

[Transactional NTFS guidance](https://learn.microsoft.com/en-us/windows/win32/fileio/deprecation-of-txf)
strongly discourages a new TxF dependency because future Windows versions may
remove it. The reparse control documentation also reports
`STATUS_EAS_NOT_SUPPORTED` for setting a reparse point in a transaction. TxF is
therefore not the proposed junction mechanism.

After 13.1 PASS, the isolated prototype must prove same-tag retarget permissions
without elevation, no missing root or mixed complete generation during bounded
concurrent opening, unchanged old handles, crash-before/after-switch recovery,
idempotent rollback, sharing/permission failures, malformed/foreign-link
rejection and actual KiCad resolution/cache reload. If these fail, this candidate
cannot be declared supported; publication must remain blocked until another
complete mechanism passes.

## Native UI tool availability

The installed computer-use skill specifies `mcp__node_repl__js` and
`import("@oai/sky")`. That deferred tool is listed in this session, so the
browser-only CUA interface does not establish native automation unavailability.
The skill, guidance and confirmation rules were read; no import, app enumeration
or UI control was performed. Tool/helper operation and real PCM lifecycle
remain unproven.

## Outstanding milestone evidence

Real PCM installation, repository Pending/Apply, background dependency
preparation, launch/reload, failed/interrupted preparation, environment
recreation, update, active-action uninstall/reinstall and durable-data ownership
remain due. Live IPC must cover version, intended PCB reads, changed/wrong
session, restart, timeout/disconnection, unavailable operations and central token
redaction. Native/API unit and angle fixtures, full source/payload/runtime byte
parity, wheel-automation retirement, the tested publication boundary and final
affected-manifest hash closeout are all still required for 13.2 PASS.
