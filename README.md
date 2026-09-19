# PartSmith

PartSmith is the Board Forge Tools deterministic component builder for native KiCad
libraries. This repository currently implements Phase 0 of the implementation
specification: the Python package, command-line entry point, quality tooling, and CI
foundation.

## Development

PartSmith requires Python 3.12 or newer. Create an environment and install the project
with its development tools:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --requirement requirements-ci.txt
python -m pip install -e . --no-deps
```

Run the deterministic local checks:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
partsmith version
partsmith doctor
```

`doctor` deliberately checks only the Phase 0 runtime foundation. KiCad and CAD backend
diagnostics will be added when those integrations are implemented.

CI uses the exact tool versions in `requirements-ci.txt`. Update that file deliberately
and retain the successful CI run as Phase 0 gate evidence.
