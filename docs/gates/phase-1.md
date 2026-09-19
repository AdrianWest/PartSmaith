# Phase 1 persistence foundation: PASS

Recorded 2026-09-19 against implementation specification v0.9.3.
Prerequisite: [Phase 0 local verification](phase-0.md).
Runtime: Windows, Python 3.12.10, SQLite 3.49.1, PartSmith 0.1.0,
pytest 8.4.2, Ruff 0.16.8. Tests use temporary databases, never user data.

## Work items and gate coverage

| Requirement | Implementation / evidence |
| --- | --- |
| SQLite connections | `connect` and `database`; explicit close, commit, rollback tests |
| Foreign keys | Enabled and checked on each connection; invalid component/build references and parent deletion fail |
| Migration 001 | Atomic SQL plus version/checksum ledger; repeated and concurrent application records exactly one migration |
| Project/component/build records | Typed creation and ID/relationship queries; all normative build fields and UTC creation/update timestamps |
| Migration tests | Empty file database, reopen, durable record round trips, unchanged ledger, failure rollback/retry, altered/unknown migration rejection |

`test_phase_one_gate` creates an empty database, verifies foreign keys,
applies 001, verifies a second application is a no-op, closes/reopens,
creates all three record types, closes/reopens again, and compares every
stored field. Invalid foreign keys fail after reopening.

## Commands and results

Loaded `PYTHONUTF8` and `VIRTUAL_ENV` from the user's ignored `.env`.
The configured `.venv` interpreter required execution outside the sandbox
because its base Python was inaccessible inside the sandbox. `.env` was
not modified. No runtime dependency was added to PartSmith.

```powershell
.venv/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-1-tests.xml
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m pip wheel . --no-deps --wheel-dir dist
.venv/Scripts/python.exe -m venv .tools/gate-env
.tools/gate-env/Scripts/python.exe -m pip install -r requirements-ci.txt
.tools/gate-env/Scripts/python.exe -m pip install --no-deps dist/partsmith-0.1.0-py3-none-any.whl
.tools/gate-env/Scripts/python.exe -c "from importlib.resources import files; import partsmith; print(partsmith.__file__); assert files('partsmith.persistence').joinpath('001_initial.sql').is_file()"
.tools/gate-env/Scripts/python.exe -m pytest --junitxml=docs/gates/phase-1-wheel-tests.xml
.tools/gate-env/Scripts/partsmith.exe version
.tools/gate-env/Scripts/partsmith.exe doctor --json
Get-FileHash migrations/001_initial.sql,dist/partsmith-0.1.0-py3-none-any.whl -Algorithm SHA256
```

All commands exited 0. Editable installation: **18 passed**, including 12
persistence tests. Fresh wheel installation: **18 passed**. Lint passed;
format check passed (11 files). Wheel imports resolved to the fresh
environment's `site-packages`, and the installed SQL resource exists.
Version: `0.1.0`. Doctor: all three diagnostics PASS.

Machine-readable results:
[editable tests](phase-1-tests.xml), [wheel tests](phase-1-wheel-tests.xml).

SHA-256 of migration 001 (UTF-8, LF):
`840216cf721f9b76be6575a4dccc07ff70b3fd32637f4c1f39d33892f5c3eba9`

SHA-256 of tested `partsmith-0.1.0-py3-none-any.whl`:
`ea54e39b071510b3382636406d9febb613fb8b26e17ad59cb0d825c89b94b8df`

CI now repeats the editable checks and installed-wheel persistence tests on
Windows and Ubuntu, preserving JUnit reports and wheels as run artifacts.
No new remote CI run is claimed. This PASS records the completed local gate;
Phase 2 implementation has not started.
