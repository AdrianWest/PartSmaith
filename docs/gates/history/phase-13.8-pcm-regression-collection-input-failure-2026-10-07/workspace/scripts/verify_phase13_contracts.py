"""@file verify_phase13_contracts.py
@brief Builds and tests an isolated PCM-layout contract-only payload fixture.
@details This fixture proves offline source/resource parity for milestone 13.1.
It is not a customer plugin or evidence of PCM lifecycle/runtime readiness.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''
import sys
from pathlib import Path
root = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(root))
def offline(event, args):
    """@brief Blocks network access during isolated contract validation.
    @param event Python audit event name.
    @param args Event-specific arguments.
    @return None.
    @details Raises RuntimeError before connection or DNS operations.
    """
    if event in ('socket.connect', 'socket.getaddrinfo'):
        raise RuntimeError('Network disabled for contract payload validation')
sys.addaudithook(offline)
import partsmith.integration
from partsmith.integration.schema import load_schema
assert Path(partsmith.integration.__file__).resolve().is_relative_to(root)
schema_path = root / 'partsmith/integration'
schema_path /= 'integration-contracts-1.0.schema.json'
assert schema_path.is_file()
schema = load_schema()
assert schema['$defs']['integration_plan']['additionalProperties'] is False
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
'''


def payload_inventory() -> dict[str, bytes]:
    """@brief Collects exact owned source and schema/resource dependencies.
    @return PCM-layout archive paths mapped to exact bytes.
    @details Existing packaging mappings supply resource coverage, without
    invoking a build backend or generating/installing a PartSmith wheel.
    """
    inventory = {}
    for source in sorted((ROOT / "src/partsmith").rglob("*")):
        if source.is_file() and source.suffix in {".py", ".json"}:
            path = "plugins/" + source.relative_to(ROOT / "src").as_posix()
            inventory[path] = source.read_bytes()
    config = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
    resources = config["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    for name, target in resources.items():
        source = ROOT / name
        entries = sorted(source.rglob("*")) if source.is_dir() else [source]
        for entry in entries:
            if not entry.is_file() or "__pycache__" in entry.parts:
                continue
            suffix = "/" + entry.relative_to(source).as_posix()
            path = target + suffix if source.is_dir() else target
            inventory["plugins/" + path] = entry.read_bytes()
    for entry in sorted((ROOT / "fixtures/integration").rglob("*.json")):
        path = "plugins/" + entry.relative_to(ROOT).as_posix()
        inventory[path] = entry.read_bytes()
    test = "tests/test_integration_contracts.py"
    inventory["plugins/" + test] = (ROOT / test).read_bytes()
    return dict(sorted(inventory.items()))


def build_payload(path: Path, inventory: dict[str, bytes]) -> None:
    """@brief Writes a deterministic contract-fixture ZIP.
    @param path Owned output archive path.
    @param inventory Exact bytes in sorted archive order.
    @return None.
    @details Fixed timestamps, modes and stored encoding remove host variance.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, blob in inventory.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, blob)


def main() -> int:
    """@brief Builds, byte-checks and tests a checkout-independent payload.
    @return Zero for exact parity and passing isolated contract checks.
    @details Preserves stdout, stderr, XML and resource/hash evidence.
    Does not invoke or mutate the customer's PCM installation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use the project Python 3.12 runtime")
    archive = args.archive.resolve()
    evidence = args.evidence.resolve()
    junit = args.junit.resolve()
    inventory = payload_inventory()
    build_payload(archive, inventory)
    with tempfile.TemporaryDirectory(prefix="partsmith-contract-pcm-") as name:
        root = Path(name)
        repeated = root / "repeated.zip"
        build_payload(repeated, inventory)
        if repeated.read_bytes() != archive.read_bytes():
            raise RuntimeError("Payload construction is nondeterministic")
        with zipfile.ZipFile(archive) as package:
            if package.namelist() != list(inventory):
                raise RuntimeError("Payload inventory differs")
            for path, blob in inventory.items():
                if package.read(path) != blob:
                    raise RuntimeError("Payload resource bytes differ")
            package.extractall(root / "extracted")
        payload_root = root / "extracted/plugins"
        environment = os.environ.copy()
        for key in ("PYTHONPATH", "PYTHONHOME"):
            environment.pop(key, None)
        command = [
            sys.executable,
            "-I",
            "-c",
            BOOTSTRAP,
            str(payload_root),
            "tests/test_integration_contracts.py",
            "-q",
            "--import-mode=importlib",
            f"--junitxml={junit}",
        ]
        result = subprocess.run(
            command,
            cwd=payload_root,
            env=environment,
            capture_output=True,
            timeout=120,
            check=False,
        )
    suites = list(ET.parse(junit).getroot().iter("testsuite"))
    counts = {
        field: sum(int(suite.get(field, 0)) for suite in suites)
        for field in ("tests", "failures", "errors", "skipped")
    }
    passed = (
        result.returncode == 0
        and counts["tests"] > 0
        and not any(
            counts[field] for field in ("failures", "errors", "skipped")
        )
    )
    evidence.parent.mkdir(parents=True, exist_ok=True)
    stdout = evidence.with_suffix(".stdout.txt")
    stderr = evidence.with_suffix(".stderr.txt")
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    report = {
        "scope": "13.1 contract-only PCM-layout fixture; no plugin lifecycle",
        "status": "PASS" if passed else "FAIL",
        "runtime": {"python": sys.version.split()[0]},
        "archive": {
            "path": archive.relative_to(ROOT).as_posix(),
            "sha256": sha256(archive.read_bytes()).hexdigest(),
            "byte_length": archive.stat().st_size,
        },
        "deterministic_repeat": True,
        "offline": True,
        "repository_fallback": False,
        "exit_code": result.returncode,
        "tests": counts,
        "inventory": {
            path: {
                "sha256": sha256(blob).hexdigest(),
                "byte_length": len(blob),
            }
            for path, blob in inventory.items()
        },
        "evidence": {
            path.relative_to(ROOT).as_posix(): sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (stdout, stderr, junit)
            if path.exists()
        },
    }
    evidence.write_text(
        json.dumps(report, indent=2) + "\n", "utf-8", newline="\n"
    )
    print(result.stdout.decode("utf-8", errors="replace"))
    if result.returncode:
        print(result.stderr.decode("utf-8", errors="replace"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
