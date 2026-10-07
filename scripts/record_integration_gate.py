"""@file record_integration_gate.py
@brief Records ordered source checkpoint inputs before final hash closeout.
@details Passing XML is necessary but does not replace native acceptance.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import date
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """@brief Creates a scoped checkpoint receipt from verified evidence.
    @return None.
    @details Refuses failed/skipped suites and existing receipts; the gate
    closeout helper must run afterward before reporting checkpoint PASS.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        required=True,
        choices=[f"13.{number}" for number in range(3, 9)],
    )
    parser.add_argument("--scope", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args()
    phase = args.phase
    previous = f"13.{int(phase[-1]) - 1}"
    prerequisite = ROOT / f"docs/gates/phase-{previous}-artifacts.json"
    prior = json.loads(prerequisite.read_bytes())
    assert prior["status"] == "PASS"
    assert (ROOT / prior["hash_closeout"]).is_file()
    suites = list(ET.parse(ROOT / args.results).getroot().iter("testsuite"))
    assert suites and sum(int(s.attrib["tests"]) for s in suites) > 0
    assert all(
        int(s.attrib.get(field, 0)) == 0
        for s in suites
        for field in ("failures", "errors", "skipped")
    )
    output = ROOT / f"docs/gates/phase-{phase}-artifacts.json"
    assert not output.exists()
    inputs = {
        "README.md",
        "resources/BFT_PartSmith_Implementation_Spec.md",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        ".gitattributes",
        ".gitignore",
        "scripts/close_integration_gate.py",
        "scripts/record_integration_gate.py",
        "src/partsmith/persistence/database.py",
        "tests/test_persistence.py",
        "tests/phase13_support.py",
        args.results,
        f"docs/gates/phase-{phase}.md",
        *args.evidence,
    }
    for pattern in (
        "src/partsmith/integration/**/*.py",
        "tests/test_integration*.py",
        "migrations/*.sql",
        "schemas/integration*.json",
    ):
        inputs.update(
            p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern)
        )
    document = {
        "phase": phase,
        "date": date.today().isoformat(),
        "status": "PASS",
        "scope": args.scope,
        "full_phase13_status": "PENDING",
        "prerequisite": {previous: "PASS"},
        "hash_closeout": f"docs/gates/phase-{phase}-hash-closeout.json",
        "hash_source": "disk",
        "git_blob_verification": "Due after current inputs are committed",
        "source_checks": {
            "path": args.results,
            "tests": sum(int(s.attrib["tests"]) for s in suites),
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        },
        "evidence": args.evidence,
        "sha256": {
            name: sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(inputs)
        },
    }
    output.write_text(
        json.dumps(document, indent=2) + "\n", "utf-8", newline="\n"
    )
    print(f"Recorded {phase}; final hash closeout is still required")


if __name__ == "__main__":
    main()
