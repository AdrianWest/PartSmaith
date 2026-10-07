# Phase 12.5 working increment

Generate / Validate Reviewed Component routes through the existing deterministic
pipeline and BuildOrchestrator. The desktop adapter verifies the current reviewed
head and exact PDL before creating and publishing an attempt. The isolated worker
owns SQLite connections. Consistent symbol, footprint, STEP and final-artifact
stages commit and checkpoint their exact content references before continuing.
Operational failure/cancellation remains separate from persisted BuildState.

The Symbol / Footprint tab shows exact bound artifact bytes/hashes and actual
native KiCad SVG previews. The main wx timer remains responsive. Progress binds
action, operational instance, revision and build attempt. Superseded action
notifications are ignored. Atomic review commits retain their actual outcome.

Native scripts stream stdout and stderr through bounded pipe readers, with
origin labels, pre-failure output, final partial lines and actual exit status.
Redaction precedes displayed/persisted logs. Windows kill-on-close job objects
contain worker descendants; POSIX uses owned process groups. Timeout and
cancellation reap pipes and readers. A failed model stage retains completed
symbol/footprint objects for inspection and session save/load.

Recorded check before Phase 12.6: `phase-12.5-source-results.xml`, **11 passed**
on Python 3.12.10, including actual isolated generation, exact final artifacts,
native previews, hard model-worker crash, cooperative cancellation, output/time
budgets, redacted stdout/stderr, existing pipeline approval/export, and the real
wx generation button and main-window responsiveness.

Worker progress exposed contention caused by re-running write-locking migration
verification on every read connection. Each operational process now validates
migrations on attachment/load, then uses short-lived normal transactions. Archive
loads still validate migration identities after staging the imported database.

Later viewer/release milestones and final installed-wheel/hash closeout remain
open. The previous combined native regression finding remains unresolved.
