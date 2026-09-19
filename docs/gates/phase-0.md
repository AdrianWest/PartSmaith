# Phase 0 prerequisite: PASS

Verified on 2026-09-19, Windows, Python 3.12.10, PartSmith 0.1.0,
before implementing Phase 1. Used the virtual environment selected by
`.env`, with pinned dependencies from `requirements-ci.txt`.

Commands (all exited 0 after normalizing Python files to LF):

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-ci.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/partsmith.exe version
.venv/Scripts/partsmith.exe doctor --json
```

Results: 6 tests passed; lint and formatting passed; version `0.1.0`;
doctor reported PASS for Python, package, and CLI. `.gitattributes`
preserves LF for Python and SQL on future Windows checkouts. Existing CI
runs installation and these checks on Windows and Ubuntu with Python 3.12.
This is local verification; no new remote CI run is claimed.
