# Phase 14 readiness review — 2026-10-07

The current checkout is ready to begin Phase 14 on the declared Windows AMD64,
Python 3.12.10 and KiCad 10.0.6 target. The recorded Phase 13 gate permits this
handoff. The fresh source/desktop checks, exact package/evidence verification
and repository-required final hash closeout pass. No outstanding Phase 13
implementation blocker was found.

The review originally covered uncommitted Phase 13 source and evidence over
HEAD `6a90e6b` (`Phase 12 is done`). The reviewed baseline is now committed as
`742387b22b27c14b5cd24a12fe08df01468fc90d`. All 33 active input maps, including
all 12 CI maps, match both that commit's exact Git blobs and the checkout bytes.
The [committed-input verification receipt](gates/phase-13-committed-input-verification-2026-10-07.json)
records fulfillment of the prior closeout's deferred Git verification.

| Readiness evidence | Review result |
| --- | --- |
| Ordered 13.1–13.8 receipts | All eight record PASS and have retained closeouts |
| Full Phase 13 gate | Recorded PASS for the declared target |
| Active input maps | All 33 match exact committed Git blobs and checkout bytes |
| CI input maps | All 12 are included and match exact committed Git blobs and checkout bytes |
| Final PCM package | Inventory, metadata, SHA-256 and source/resource parity verified |
| Fresh deterministic PCM builds | Two builds match frozen 0.1.9 archive bytes exactly |
| Native publication, relocation and isolated PCM receipts | Retained identities and referenced artifacts verified |
| PCM lifecycle and offline contract evidence | Package identities, installed payload and authority preservation verified |
| Complete source suite | Fresh run: 1,104 passed in 1,066 seconds; no failures or skips |
| Desktop harness | Fresh run: 14 passed |
| Ruff lint and formatting | Fresh runs pass; 281 files formatted |
| Source CLI diagnostics | Python, package, CLI and KiCad checks pass |
| Final hash refresh and verification | PASS: 33 active maps, all 12 CI maps and current outside-map identities; zero input hashes changed |

The final archive is `dist/partsmith-0.1.9-pcm.zip`, SHA-256
`a52e0ce3ecbc12aec3a5a79c8c95327529a3b2903c5e6d118596d0e59749fca7`.
Its 163 owned payload/resource files match the current package inputs.
The retained isolated PCM suite has 1,118 passing cases and exactly matches
the source-plus-desktop case set. Retained offline contract evidence has 98
passing cases; the final PDF stability receipt records three passing rounds.
Supervised PCM/native-editor/IPC acceptance retains its recorded execution
scope. This review verifies that evidence against the unchanged package bytes.

Phase 14 has substantial production work remaining:

1. **Single-installation runtime.** The current package contains PartSmith
   source/resources and pinned requirements. Its documented installation needs
   an external Python 3.12 interpreter; offline dependency preparation needs an
   administrator-provisioned binary supply and site policy outside the ZIP.
   Deliver and prove the production PCM runtime/dependency layout without
   customer installation of Python or CAD dependencies. The current package
   validator accepts the Python IPC registration only; an executable layout
   needs corresponding registration, validator and diagnostic changes.
2. **Complete dependency and license inventory.** Existing CAD runtime locks
   and license hashes provide part of the foundation. Produce the complete
   INSTALL-004/005 manifest, preserved notices/texts and packaged-file checks
   for the production dependency closure. Include required external tools:
   OCR currently discovers system Tesseract and requires `eng`, `deu` and
   `chi_sim` language data from the pinned extraction profile.
3. **All eight production variants.** The sole shipped PDL entry is synthetic
   0402; its golden explicitly declares `production_evidence: false`.
   The 3D generator accepts only `CHIP_BODY`, `END_TERMINATIONS` and `NONE`.
   Add manufacturer-backed PDL/golden coverage and the necessary geometry and
   CLASS A validation for 0402, 0603, 0805, SOT-23, SOIC-8, TSSOP-16,
   QFN-16-3x3-0.5P and QFN-24-4x4-0.5P. Per-variant negative, reproducibility
   and native KiCad results are mandatory.
4. **Clean-machine acceptance.** Prove automated install, launch, diagnostics,
   upgrade and uninstall on a clean supported machine, including the production
   offline path. Existing developer-machine and provisioned-runtime evidence
   has a narrower scope.

These are assigned Phase 14 obligations. They do not reopen Phase 13's scoped
implementation gate. The Phase 14 specification is sufficient to begin work;
the first implementation checkpoint should prove the production runtime layout,
followed by dependency/license closure, variant expansion and clean-machine
acceptance. Phase 14 PASS requires all nine numbered items and its full gate.

One nonblocking documentation inconsistency remains: the status paragraph near
the end of specification section 245 still describes Phase 0–12 evidence and
says installation contracts/execution remain due at 13.1–13.8. The current
header, numbered gate policy and final receipts correctly record Phase 13 PASS.
Update that older paragraph in the next specification edit; the explicit
numbered gate policy remains the implementation-order authority.

Review commands include:

```text
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pytest -q scripts/verify_gui.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m partsmith doctor --json
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest <active-manifest> --source disk
.venv/Scripts/python.exe scripts/verify_phase2_manifest.py --manifest <active-manifest> --source git
.venv/Scripts/python.exe scripts/close_integration_gate.py --phase 13 --reason "Phase 14 readiness review: fresh source and desktop checks; retained exact PCM, native and offline evidence verified"
```

All Python checks use the project's Python 3.12.10 environment. Package and
receipt inspection additionally resolves outside-map artifact identities,
compares source/package bytes, verifies retained JUnit case parity and builds
two deterministic PCM archives in a disposable directory. CLI diagnostics use
the declared `src` import path. Post-test inspection found no unexpected input
changes. The final closeout verified all 33 active maps and outside-map identities,
recorded zero hash changes and preserved its previous receipt under
`docs/gates/history/`. Original test, package and native acceptance artifacts
retain their exact original bytes and scope. Committed verification additionally
tracks the three historical wheel inputs previously hidden by `.tools/` and
preserves the recorded bytes of three historical XML captures in Git. Gate
execution records retain their original disk-validation scope; the separate
committed-input receipt records the subsequent Git verification.

References: [phase policy and Phase 14 requirements](../resources/BFT_PartSmith_Implementation_Spec.md),
[full Phase 13 gate](gates/phase-13.md),
[final acceptance](gates/phase-13.8.md),
[review hash closeout](gates/phase-13-hash-closeout.json),
[PCM installation](pcm-installation.md),
[package construction and validation](../src/partsmith/pcm/package.py),
[3D strategy validation](../src/partsmith/threed/model.py),
[synthetic golden scope](../fixtures/pdl/golden/GOLD-0402-001.json),
[OCR dependency discovery](../src/partsmith/extraction/ocr.py).
