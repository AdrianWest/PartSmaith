"""@file verify_pcm_acceptance.py
@brief Runs full source regressions against isolated final PCM payload modules.
@details Reconstructs declared test inputs in an owned harness. PartSmith
imports must originate from the exact ZIP without a distribution installation.
"""

import argparse
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''"""@file pcm_acceptance_bootstrap.py
@brief Runs copied acceptance tests using isolated installed modules.
@details Original checkout paths are absent from imports and working directory.
"""
import json
import sys
from pathlib import Path


def main():
    """@brief Runs exact PCM tests once in the supervising interpreter.
    @return Pytest exit status after checking every loaded PartSmith origin.
    @details A main guard prevents multiprocessing children restarting pytest.
    """
    payload = Path(sys.argv[1]).resolve()
    workspace = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(workspace))
    sys.path.insert(0, str(workspace / "tests"))
    sys.path.insert(0, str(payload))
    import partsmith
    assert sys.flags.isolated
    assert Path(partsmith.__file__).resolve().is_relative_to(payload)
    from partsmith.pcm.runtime import verify_inventory
    inventory = verify_inventory(payload)
    import pytest
    arguments = ["-c", str(workspace / "pytest.ini"), "-q", "--maxfail=1",
                 "-p", "no:cacheprovider", "--junitxml=" + sys.argv[3],
                 str(workspace / "tests")]
    if sys.argv[4] == "desktop":
        arguments.append(str(workspace / "scripts/verify_gui.py"))
    code = pytest.main(arguments)
    origins = {}
    for name, module in sorted(sys.modules.items()):
        if name == "partsmith" or name.startswith("partsmith."):
            origin = getattr(module, "__file__", None)
            if origin is not None:
                assert Path(origin).resolve().is_relative_to(payload), name
                origins[name] = str(
                    Path(origin).resolve().relative_to(payload)
                )
    (workspace.parent / "origins.json").write_text(json.dumps({
        "version": inventory["version"], "origins": origins,
        "repository_imports": False, "isolated": True,
    }, indent=2) + "\\n", encoding="utf-8", newline="\\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
'''


def main():
    """@brief Creates a fresh exact-payload full regression harness.
    @return Zero only when all copied acceptance tests pass.
    @details Retains failures, command output and verified module identities.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir()
    workspace = output / "workspace"
    workspace.mkdir()
    copied = {}
    for directory in (
        "tests",
        "test_data_sheets",
        "fixtures",
        "resources",
        "schemas",
        "migrations",
        "pdl",
        "integrations",
        "scripts",
        "src/partsmith",
        ".github",
    ):
        for source in (ROOT / directory).rglob("*"):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            relative = source.relative_to(ROOT)
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            destination.write_bytes(data)
            copied[relative.as_posix()] = sha256(data).hexdigest()
    root_inputs = (
        "pyproject.toml",
        "requirements-ci.txt",
        "requirements-extraction.txt",
        "requirements-pcm.txt",
        "LICENSE",
        "docs/gates/phase-2-artifacts.json",
    )
    for name in root_inputs:
        data = (ROOT / name).read_bytes()
        destination = workspace / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        copied[name] = sha256(data).hexdigest()
    (workspace / "pytest.ini").write_text("[pytest]\n", "utf-8")
    with ZipFile(args.archive) as archive:
        archive.extractall(output / "payload")
    bootstrap = output / "bootstrap.py"
    bootstrap.write_text(BOOTSTRAP, "utf-8")
    unrelated = output / "unrelated"
    unrelated.mkdir()
    environment = os.environ.copy()
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "KICAD_API_SOCKET",
        "KICAD_API_TOKEN",
    ):
        environment.pop(name, None)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTHONPATH"] = str(output / "payload/plugins")
    command = [
        sys.executable,
        "-I",
        "-B",
        str(bootstrap),
        str(output / "payload/plugins"),
        str(workspace),
        str(output / "results.xml"),
        "desktop" if args.desktop else "headless",
    ]
    with (output / "stdout.txt").open("wb") as stdout:
        with (output / "stderr.txt").open("wb") as stderr:
            completed = subprocess.run(
                command,
                cwd=unrelated,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                timeout=7200,
                check=False,
            )
    report = {
        "schema_version": "partsmith-pcm-acceptance-evidence-1.0",
        "archive_sha256": sha256(args.archive.read_bytes()).hexdigest(),
        "command": command,
        "exit_code": completed.returncode,
        "copied_input_hashes": copied,
        "scope": "Exact PCM modules, owned copied regression inputs",
        "live_desktop_claim": False,
    }
    (output / "receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", "utf-8"
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
