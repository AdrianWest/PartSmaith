"""@file record_phase13_acceptance.py
@brief Records complete source, PCM and supervised native Phase 13 evidence.
@details Required checks must pass before recording. Final affected hash
closeout remains mandatory; this script never creates publication authority.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import date
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def suite_counts(path: Path) -> dict:
    """@brief Requires a complete nonempty passing acceptance result.
    @param path Explicit retained JUnit XML.
    @return Tests, failures, errors and skipped counts.
    @details Failure, error, skip or incomplete XML blocks gate recording.
    """
    suites = list(ET.parse(path).getroot().iter("testsuite"))
    counts = {
        key: sum(int(s.get(key, 0)) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    assert counts["tests"] > 0
    assert all(counts[key] == 0 for key in ("failures", "errors", "skipped"))
    return counts


def main() -> None:
    """@brief Records final 13.8 and full Phase 13 maps from actual checks.
    @return None.
    @details Refuses existing receipts and requires all prior hash closeouts,
    exact final PCM identity, full tests, three PDF rounds and native evidence.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    for name in ("phase-13.8-artifacts.json", "phase-13-artifacts.json"):
        assert not (ROOT / "docs/gates" / name).exists()
    prerequisites = {}
    for number in range(1, 8):
        name = f"docs/gates/phase-13.{number}-artifacts.json"
        previous = json.loads((ROOT / name).read_bytes())
        assert previous["status"] == "PASS"
        assert (ROOT / previous["hash_closeout"]).is_file()
        prerequisites[f"13.{number}"] = "PASS"
    source = "docs/gates/phase-13.8-source-results.xml"
    desktop = "docs/gates/phase-13.8-source-desktop-results.xml"
    pcm = "docs/gates/phase-13.8-pcm-regression/results.xml"
    counts = {
        "source": suite_counts(ROOT / source),
        "source_desktop": suite_counts(ROOT / desktop),
        "pcm_with_desktop": suite_counts(ROOT / pcm),
    }
    pcm_root = ROOT / "docs/gates/phase-13.8-pcm-regression"
    acceptance = json.loads((pcm_root / "receipt.json").read_bytes())
    origins = json.loads((pcm_root / "origins.json").read_bytes())
    assert acceptance["exit_code"] == 0
    assert origins["isolated"] and not origins["repository_imports"]
    archive = args.archive.resolve()
    identity = sha256(archive.read_bytes()).hexdigest()
    assert acceptance["archive_sha256"] == identity
    pdf_root = ROOT / "docs/gates/phase-13.8-pdf-stability"
    pdf = json.loads((pdf_root / "manifest.json").read_bytes())
    assert pdf["status"] == "PASS" and pdf["rounds_requested"] == 3
    assert len(pdf["attempts"]) == 3
    assert pdf["archive_sha256"] == identity
    for attempt in pdf["attempts"]:
        assert attempt["status"] == "PASS" and attempt["exit_code"] == 0
        for name, expected in attempt["artifacts"].items():
            assert sha256((pdf_root / name).read_bytes()).hexdigest() == (
                expected
            )
        suite_counts(pdf_root / f"round-{attempt['round']}.xml")
    live = json.loads(
        (ROOT / "docs/gates/phase-13.7-live-relocated-019.json").read_bytes()
    )
    assert live["state"] == "READY" and live["package_version"] == "0.1.9"
    inspection = live["ipc_inspection"]["inspection"]
    assert inspection["capabilities"]["evidence_origin"] == (
        "official-live-binding"
    )
    assert len(inspection["footprints"]) == 2
    comparison = json.loads(
        (
            ROOT
            / "docs/gates/phase-13.7-instance-comparison-relocated-019.json"
        ).read_bytes()
    )
    assert comparison["passed"]
    prior_pcm = json.loads(
        (ROOT / "docs/gates/phase-13.7-artifacts.json").read_bytes()
    )["pcm_package"]
    assert prior_pcm["sha256"] == identity
    lifecycle_path = "docs/gates/phase-13.8-pcm-lifecycle.json"
    lifecycle = json.loads((ROOT / lifecycle_path).read_bytes())
    assert lifecycle["status"] == "PASS"
    assert lifecycle["package_version"] == prior_pcm["version"] == "0.1.9"
    assert lifecycle["archive_sha256"] == identity
    assert lifecycle["inventory_sha256"] == prior_pcm["inventory_sha256"]
    assert len(lifecycle["observations"]) == 7
    assert all(
        (ROOT / p).is_file() for p in lifecycle["observations"].values()
    )
    authority = {
        lifecycle[f"authority_{boundary}_sha256"]
        for boundary in (
            "before_removal",
            "after_removal",
            "after_reinstall",
            "after_upgrade",
        )
    }
    assert len(authority) == 1
    managed = json.loads((ROOT / lifecycle["installed_runtime"]).read_bytes())
    assert (
        managed["state"] == "READY" and managed["package_version"] == "0.1.9"
    )
    assert managed["inventory_sha256"] == prior_pcm["inventory_sha256"]
    assert managed["engineering"]["kicad"]["version"] == "10.0.6"
    assert len(managed["dependencies"]) == 67
    assert all(lifecycle["cleanup"].values())
    assert not lifecycle["partsmith_wheel_build_install_test"]
    assert not lifecycle["public_repository_or_clean_machine_claim"]
    inputs = {
        "README.md",
        "docs/pcm-installation.md",
        "resources/BFT_PartSmith_Implementation_Spec.md",
        "pyproject.toml",
        ".gitattributes",
        ".gitignore",
        ".github/workflows/ci.yml",
        ".github/instructions/gate-closeout.instructions.md",
        ".github/instructions/python-docstrings.instructions.md",
        "docs/gates/phase-13.8.md",
        "docs/gates/phase-13.md",
        source,
        desktop,
        pcm,
    }
    for directory in (
        "src",
        "tests",
        "scripts",
        "schemas",
        "migrations",
        "fixtures",
        "pdl",
        "integrations",
    ):
        inputs.update(
            p.relative_to(ROOT).as_posix()
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
    inputs.update(p.name for p in ROOT.glob("requirements*.txt"))
    for pattern in ("phase-13.7-*", "phase-13.8-*"):
        for path in (ROOT / "docs/gates").glob(pattern):
            if path.is_file():
                inputs.add(path.relative_to(ROOT).as_posix())
    evidence = set()
    for directory in (
        "docs/gates/phase-13.7-native-final",
        "docs/gates/phase-13.7-native-roundtrip-final",
        "docs/gates/phase-13.8-pcm-regression",
        "docs/gates/phase-13.8-pdf-stability",
    ):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                name = path.relative_to(ROOT).as_posix()
                inputs.add(name)
                evidence.add(name)
    document = {
        "phase": "13.8",
        "date": date.today().isoformat(),
        "status": "PASS",
        "scope": "Final Windows AMD64 KiCad 10.0.6 source/PCM acceptance",
        "full_phase13_status": "PASS",
        "prerequisite": prerequisites,
        "hash_closeout": "docs/gates/phase-13.8-hash-closeout.json",
        "hash_source": "disk",
        "git_blob_verification": "Due after current inputs are committed",
        "checks": counts,
        "pcm_package": prior_pcm,
        "pdf_rounds": [a["tests"] for a in pdf["attempts"]],
        "live_native_evidence": "docs/gates/phase-13.7-artifacts.json",
        "pcm_lifecycle": lifecycle_path,
        "partsmith_wheel_build_install_test": False,
        "evidence": sorted(evidence),
        "sha256": {
            name: sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(inputs)
            if not name.endswith("-artifacts.json")
        },
    }
    destination = ROOT / "docs/gates/phase-13.8-artifacts.json"
    destination.write_text(json.dumps(document, indent=2) + "\n", "utf-8")
    aggregate = {
        key: value
        for key, value in document.items()
        if key not in {"sha256", "phase", "prerequisite", "hash_closeout"}
    }
    aggregate.update(
        phase="13",
        prerequisite=prerequisites | {"13.8": "PASS"},
        hash_closeout="docs/gates/phase-13-hash-closeout.json",
        sha256={
            f"docs/gates/phase-13.{n}-artifacts.json": sha256(
                (ROOT / f"docs/gates/phase-13.{n}-artifacts.json").read_bytes()
            ).hexdigest()
            for n in range(1, 9)
        },
    )
    (ROOT / "docs/gates/phase-13-artifacts.json").write_text(
        json.dumps(aggregate, indent=2) + "\n", "utf-8"
    )
    print("Recorded full acceptance; affected hash closeout remains required")


if __name__ == "__main__":
    main()
