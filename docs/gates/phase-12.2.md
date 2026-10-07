# Phase 12.2 working increment

The unfinished desktop session now has an isolated working SQLite database,
immutable content-addressed objects, a closed versioned transport index,
atomic Save/Load and recovery checkpoints. Every load stages a fresh operational
instance; the archive retains its historical acquisition identities. Source
PDF bytes are snapshotted before extraction or the first setup save. The
complete local extraction is retained before provider work.

The real wx window exposes Save Session, Load Session and New / Clear
Component. Save/Load are disabled while busy. Save, Discard and Cancel are
explicit unsaved-work choices, and replacement only follows a successful save.
Startup offers recovery without executing processing or review decisions.

Recorded check: Python 3.12.10, source imports explicitly selected with
`sys.path[:0] = ['src', '.']`, pytest over `tests/test_desktop_session.py`,
`tests/test_gui.py`, and `scripts/verify_phase12.py`.
`phase-12.2-source-results.xml`: **26 passed**. Checks cover real wx controls,
background save/load, setup recovery after deletion of the original PDF,
independent repeated loads, immutable source bytes, tampered object/database,
unknown versions, unresolved references, unexpected archive members, failed
atomic replacement, known-secret redaction, busy exclusion and late cancellation
after commit. Ruff passes for the implemented session modules.

This records the working increment before Phase 12.3. Full Phase 12 closeout,
installed-wheel evidence and final shared-input hash verification remain due
at milestone 12.10. The earlier combined native regression failure remains open.
