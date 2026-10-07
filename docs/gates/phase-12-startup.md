# Phase 12 startup checkpoint

Verified 2026-10-04 on Windows AMD64 with the project Python 3.12.10.
Scope: startup and milestone 12.1 only; the full Phase 12 gate remains open.

The preceding [Phase 11 PASS](phase-11.md), its
[review corrections](phase-11-finding-fixes-2026-10-04.md), and the subsequent
[Phase 10 parser correction](phase-10-parser-fix-2026-10-04.md) were inspected
before implementation. The corrections retain historical evidence; the original
Phase 10 failure is not waived. A fresh source/native run of the Phase 11
adapter, HTTPS, GUI, CLI, extraction isolation, KiCad, and original review probes
passed **122 tests**, without failures or skips, in 15.11 seconds.
Evidence: [startup results](phase-12-startup-results.xml).

The working specification includes the user's expanded milestone and worker
contracts. Preserve those edits. Implement 12.1 before starting 12.2; do not
expose unfinished Save/Load or review actions as available features.

Initial inspection found stale active Phase 11/correction hashes after the
committed parser, packaging, cross-platform, and specification changes. The
closeout will archive affected manifests, record every old/new hash, and verify
all active manifests plus the Phase 5/6/8 manifests checked by CI. Historical
test counts, live outputs, and wheel identities retain their original scope.

Rendering experiment: import/tessellate STEP in an isolated native worker;
project and rasterize the resulting display mesh in another isolated worker;
display a bounded RGB frame in wxPython. Use the independently generated 0402
footprint and explicit convention-1.1 placement. Camera changes cannot write
engineering artifacts, revisions, approval states, or source bytes.
