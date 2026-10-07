# PCM 0.1.4 independent packaging acceptance

Recorded 2026-10-06. The [identity and coverage record](phase-13.2-pcm014-readiness-coverage.json)
verifies scoped final-package evidence and reserves milestone completion for
the root gate's live evidence and affected-manifest hash closeout. Earlier
0.1.3 records retain their original identities and scope.

The exact frozen archive is `dist/partsmith-0.1.4-pcm.zip`, SHA-256
`862cff04151d22c87529f63102fa000f0afc8a8d0b2fff4bb39cd3d2f8aa4cf9`.
It has 152 ZIP members and 150 owned inventory entries. Its engineering source,
schemas, four SQL migrations, PDL data, viewer assets, runtime constraints,
CAD lock, IPC entry/registration and icon bytes match their declared source
inputs. The identity map checks the archive before and after acceptance.

The [isolated result](phase-13.2-pcm014-isolated-acceptance.json) records
**208 passed in 11.18 seconds**: 98 contract, 58 IPC adapter, 24 inspector and
28 PCM cases. No failures, errors or skips occurred. Python ran with `-I -B`
from an unrelated directory; connection and DNS audit operations were blocked.
All 44 imported PartSmith modules originated in the extracted frozen ZIP.
Tests and contract fixtures were copied explicitly into an owned harness.
PCM builder cases used a separate source-shaped reconstruction from exact ZIP
bytes and the declared build configuration, while importing the builder from
the installed layout. No checkout import fallback or PartSmith wheel build
occurred. Injected IPC tests do not establish live PCB acceptance.

```text
.venv/Scripts/python.exe .tools/phase13-discovery/verify_pcm014_acceptance.py
.venv/Scripts/python.exe .tools/phase13-discovery/build_pcm014_coverage.py
```

The acceptance helper requires a new owned harness path for another run so
prior output stays intact. Both helpers pass Ruff and formatting checks.
JUnit, stdout and empty stderr are retained beside the isolated JSON record.

The coverage builder independently verifies all 67 locked dependency versions
in the actual root-owned managed readiness record and both isolated Python
3.12 readiness cases. Each record identifies package 0.1.4, its exact inventory,
Python 3.12.10, Windows AMD64, CadQuery 2.8.0, OCP 7.9.3.1.1, OCCT 7.9.3.1 and
KiCad 10.0.6. Their engineering lock and constraints hashes match both source
and frozen package bytes. The recorded embedded Python 3.11 case fails with
`PYTHON_312_REQUIRED`. These runtime operations belong to their original
packaging/root evidence owners; this review validates their exact bindings.

The final package's PDF stability manifest records three passing rounds with
180 cases each and no failures, errors or skips. All referenced result/output
hashes were rechecked, and its archive identity matches 0.1.4. The manifest is
currently `.tools/phase13-live/pdf-stability-014/manifest.json`; the root closeout
must preserve and bind that exact final evidence rather than infer it from
the earlier 0.1.3 rounds.

The root-owned 0.1.4 live records already show deliberate Refresh at READY
sequence 2 and wrong selected board at `IPC_WRONG_BOARD`. This agent did not
independently witness those desktop operations. The root must finish recording
active-session loss/restart/context rejection, the exact PCM lifecycle and
durable-data ownership checks, native complete-generation feasibility limits
and the final hash refresh of every affected active/CI manifest. This report
does not change a gate status or advertise another platform or KiCad build.
