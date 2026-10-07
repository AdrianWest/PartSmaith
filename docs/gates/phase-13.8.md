# Phase 13.8 — final source and PCM acceptance

PASS, 2026-10-07, after complete final acceptance and affected-manifest hash
closeout. The final receipt and closeout identify the exact verified bytes.

The declared target is Windows AMD64, CPython 3.12.10 and KiCad 10.0.6. The
official PCB IPC binding is kicad-python 0.8.0; the prepared engineering runtime
uses CadQuery 2.8.0, OCP 7.9.3.1.1 and OCCT 7.9.3.1. Customer installation uses
KiCad PCM and customer launch uses the PCB Editor's PartSmith anvil action.
The package manager uses the unchanged owner-supplied PartSmith logo. No
PartSmith distribution wheel was built, installed or tested for Phase 13.

The frozen final archive is `dist/partsmith-0.1.9-pcm.zip`, 7,006,359 bytes,
SHA-256 `a52e0ce3ecbc12aec3a5a79c8c95327529a3b2903c5e6d118596d0e59749fca7`.
It contains 165 members and 162 inventoried owned payload files. The inventory
SHA-256 is `0c08eac8ac182e8ba3a5dfcf1329a22d2404796c252b2ab0a075e2d170f0b4ec`.
The inventory file itself is the 163rd installed plugin file. Every installed
plugin file matches the exact ZIP. Schema, migration, plugin, dependency,
engineering and artwork bytes retain their declared package identities.

| Final verification | Result |
| --- | --- |
| Complete source suite | 1,104 passed; no failures, errors or skips |
| Source desktop harness | 14 passed; no failures, errors or skips |
| Isolated exact PCM payload, including desktop harness | 1,118 passed; exact source-plus-desktop case-set parity; 123 payload module origins verified |
| Network-disabled isolated contract payload | 98 passed; deterministic/source-resource parity and no checkout fallback |
| Combined PCM PDF/native/desktop stability | Three rounds of 194 passed; no failures, errors or skips |
| Real PCM/native/official IPC acceptance | PASS; separate supervised evidence |
| Ruff lint and formatting | PASS under the recorded configuration |
| Tagged Python documentation | 106 changed/new modules and 879 named callables checked |
| Affected active/CI maps and outside-map identities | 33 active maps verified; current PCM/native/offline identities verified |

The full PCM harness copies declared test inputs into its own workspace and
extracts the final ZIP separately. Its supervising interpreter uses `-I -B`,
an unrelated working directory and explicit payload imports. Every loaded
PartSmith module must resolve inside the extracted payload. Test subprocesses
receive only the payload import path; package-builder tests also consume an
owned source copy. This is regression evidence, separate from actual KiCad
managed-environment preparation, native editors and live IPC acceptance.
The frozen IPC entry retains its native-accepted delayed import grouping via
one scoped Ruff I001 exception; every other lint rule applies. Captured runtime
harness directories are excluded from formatting to preserve evidence bytes.
Source CLI version/doctor checks pass; the core CLI version is 0.1.0 and the
independently versioned PCM package is 0.1.9. Fresh managed diagnostics after
the final upgrade report READY with the exact package inventory.

The initial isolated collection attempt omitted the PDF corpus and copied
helper namespace. A second attempt exposed a missing multiprocessing main
guard in the bootstrap and was stopped with its child processes. Both failed
harness attempts are retained under `history/phase-13.8-pcm-regression-*`;
neither is passing package evidence. The final harness supplies the complete
inputs, uses the main guard, and stops on the first failure.

`phase-13.8-pcm-lifecycle.json` records exact 0.1.9 removal through Pending/Apply,
immediate Install from File, a frozen 0.1.8 baseline and explicit update to
0.1.9. Native screenshots show each boundary. The durable authority database
SHA-256 remained `9da9e353e6ef69af23c38aaffe9ba0ba6b8951e1e7d78eaa55cecce81097dc20`
through removal, reinstallation and upgrade. The managed runtime reports READY
with 67 pinned third-party distributions and the exact final inventory.
Earlier 13.2 evidence separately records actual background preparation,
failure/retry, environment recreation, denied-index and missing-binary cases,
and the provisioned offline binary supply. Updating plugin code did not publish
or roll back project libraries. The owned local repository and loopback server
were removed; the official repository and original user project were restored.

`phase-13.7-native-final/` retains three actual two-component publication chains
and immutable source evidence. `phase-13.7-native-roundtrip-final/` retains real
saved and relocated native SVG/STEP exports. Native editor screenshots show
the usable schematic and PCB; official live IPC records and the independent
comparison confirm both installed instances against approved sources and the
final mapping. The native pin-name rewrite finding is blocked by exact native
pin comparison and a separately approved compatible revision; the failed
earlier candidate was never relabeled PASS. Session load, unsaved-work Cancel,
disconnect and wrong-board evidence preserve data and disable execution.

The source and PCM suites cover the earlier Phase 8 release, Phase 9 replay
and Phase 12 desktop services as well as all Phase 13 services. Mandatory
negative and failure-injection coverage is mapped below. Contract fixtures and
test doubles retain their own scope; they do not substitute for the actual
Windows NTFS publication, native editors or official PCB IPC session.

| Contract/failure category | Regression and native evidence |
| --- | --- |
| Closed contracts, canonical/golden identity and INVALID_CONTRACT | `test_integration_contracts.py`, `test_phase2_manifest.py`, `fixtures/integration/`, 13.1 |
| MISSING_SOURCE, UNAPPROVED_SOURCE and TAMPERED_SOURCE | `test_integration_sources.py`, release approval/bundle regressions, 13.1/13.3 |
| STALE_BASE, TARGET_CONFLICT, NAMESPACE_CONFLICT and PATH_CONFLICT | `test_integration_planner.py`, `test_integration_target.py`, `test_atomic_target.py`, real saved-edit replan in 13.7 |
| SEMANTIC_CHECK_FAILED and NATIVE_CHECK_FAILED | `test_integration_staging.py`, `test_instance_semantics.py`, project-reference cases, actual native pin rewrite negatives and 13.4/13.7 exports |
| IPC_UNAVAILABLE and WRONG_IPC_SESSION categories | `test_integration_ipc.py`, `test_ipc_inspection.py`, action tests in `test_pcm.py`, actual disconnect and IPC_WRONG_BOARD in 13.7 |
| AUTHENTICATION_FAILED and exact decision bindings | `test_integration_review.py`, `test_integration_publication.py`, real OS-authenticated decisions and durable retry in 13.5–13.7 |
| RESOURCE_LIMIT, redaction, cancellation and deadlines | Contract/source/store/target/staging/IPC/PCM tests, explicit worker termination, token exclusion and safe diagnostics |
| UNSUPPORTED_ATOMIC_INSTALL | `test_atomic_target.py`, actual fixed local NTFS feasibility and owned project publication in 13.2/13.6 |
| PUBLICATION_FAILED and RECOVERY_REQUIRED categories | `test_integration_publication.py`, real child-process crashes before/after switch, write/permission/lock/sharing faults, receipt gaps and COMMIT faults, 13.6 |
| Rollback, changed references and immutable source history | Publication and project-reference tests, fresh exact rollback authorization and complete native rollback receipt in 13.6 |
| Runtime/resource/preparation failures and lifecycle ownership | `test_pcm.py`, isolated payload inventory, managed READY record, actual 13.2 and final 13.8 PCM lifecycle |

Reproduction commands use the project's Python 3.12 environment:

```text
python -m pytest -q --junitxml=docs/gates/phase-13.8-source-results.xml
python -m pytest -q scripts/verify_gui.py --junitxml=docs/gates/phase-13.8-source-desktop-results.xml
python scripts/verify_pcm_acceptance.py dist/partsmith-0.1.9-pcm.zip --output docs/gates/phase-13.8-pcm-regression --desktop
python scripts/verify_pdf_stability.py --archive dist/partsmith-0.1.9-pcm.zip --rounds 3 --output docs/gates/phase-13.8-pdf-stability --desktop
python -m ruff check .
python -m ruff format --check .
python scripts/record_phase13_acceptance.py --archive dist/partsmith-0.1.9-pcm.zip
python scripts/close_integration_gate.py --phase 13.8 --reason "Final source, exact PCM, supervised native and PDF acceptance"
python scripts/close_integration_gate.py --phase 13 --reason "Complete ordered Phase 13 gate and affected input verification"
```

Evidence output directories must be absent for new runs. Existing receipts
retain their historical scope. Final closeout refreshes every affected active
map and verifies every CI map, the final PCM identities and retained native
receipts outside input maps. Disk hashes describe the uncommitted checkout;
Git-blob verification follows a user commit. CI includes source, native CLI,
offline PCM contracts, full isolated Windows PCM tests and both final maps.
Hosted publication, additional desktop platforms, clean-machine production
installation and power-loss guarantees are outside this gate. Phase 14 remains
the separate production packaging/clean installation gate.
