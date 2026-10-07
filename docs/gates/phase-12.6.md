# Phase 12.6 — active-session viewer

Current layout: Banner3 belongs to the Phase 9.5 main GUI; the viewer has no
banner. See the [banner amendment](phase-12-banner-update.md). The checkpoint
evidence below records the original implementation and acceptance scope.

The production action requires the retained actual footprint, STEP and exact
placement from the same attempt/revision. Preliminary, failed and stale
bindings remain labeled and inspectable. The owned modeless window is a
singleton and retains its display camera after bounded native cleanup.

Banner3 is the exact `resources/PartSmith-Banner3.png` resource, included in
wheel and sdist. It starts at client `(0, 0)`, spans the client width, derives
its aspect ratio from the loaded image and sits outside scrollable controls.
Missing resources are logged without substituting the earlier banner.

Source verification: `scripts/verify_phase12.py`, 4 passed, including actual
generation, viewer readiness, singleton/reopen and resize from 540×420 to
1000×800. Results: `phase-12.6-desktop-results.xml`. Packaging, launch paths,
display scale and final hash closeout are rechecked under milestone 12.10.
Overall Phase 12 remains open.
