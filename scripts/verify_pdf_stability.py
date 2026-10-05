"""@file verify_pdf_stability.py
@brief Repeat the combined installed-wheel PDF gate.
@details Retain each attempt's raw output and fail without automatic retries.
"""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = [
    "tests/test_extraction.py",
    "tests/test_extraction_isolation.py",
    "tests/test_ai.py",
    "tests/test_ai_transport.py",
    "tests/test_cli.py",
    "tests/test_gui.py",
    "tests/test_kicad_runtime.py",
]
BOOTSTRAP = """
import json, os, sys
from pathlib import Path
if os.name == 'nt':
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
sys.path.insert(0, str(Path.cwd()))
import partsmith.extraction, pdfplumber, pdfminer, pypdfium2 as pdfium
installed = Path(partsmith.extraction.__file__).resolve().parents[1]
assert 'site-packages' in installed.parts, installed
assert not any(n == 'pymupdf' or n.startswith('pymupdf.') for n in sys.modules)
assert pdfium.PYPDFIUM_INFO.api_tag == (5, 14, 0)
assert pdfplumber.__version__ == '0.11.10', pdfplumber.__version__
assert pdfminer.__version__ == '20260107', pdfminer.__version__
for source in Path('src/partsmith').rglob('*'):
    if source.is_file() and source.suffix in ('.py', '.json'):
        target = installed / source.relative_to('src/partsmith')
        assert source.read_bytes() == target.read_bytes(), source
print(json.dumps({'package': str(installed),
                  'pdfium': str(pdfium.PDFIUM_INFO),
                  'pdfplumber': pdfplumber.__version__,
                  'pdfminer': pdfminer.__version__}), flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
"""


def main():
    """@brief Run the requested installed-wheel verification rounds.
    @return Zero if all rounds pass, one on a failed round.
    @details Require matching installed code and retain native-crash output.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--desktop", action="store_true")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    suite = [*SUITE, "scripts/verify_gui.py"] if args.desktop else SUITE
    manifest = {
        "status": "RUNNING",
        "rounds_requested": args.rounds,
        "suite": suite,
        "attempts": [],
    }
    manifest_path = output / "manifest.json"

    def save():
        """@brief Persist progress and every completed attempt.
        @return None.
        @details Keep failures visible even if a later invocation passes.
        """
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    save()
    for number in range(1, args.rounds + 1):
        prefix = output / f"round-{number}"
        junit = prefix.with_suffix(".xml")
        stdout = prefix.with_suffix(".stdout.txt")
        stderr = prefix.with_suffix(".stderr.txt")
        command = [
            sys.executable,
            "-c",
            BOOTSTRAP,
            *suite,
            "-v",
            "--tb=short",
            f"--basetemp={output / f'tmp-{number}'}",
            "-o",
            f"cache_dir={output / 'cache'}",
            f"--junitxml={junit}",
        ]
        print(f"Installed-wheel combined gate, round {number}.", flush=True)
        with stdout.open("wb") as out, stderr.open("wb") as err:
            try:
                process = subprocess.run(
                    command,
                    cwd=ROOT,
                    stdout=out,
                    stderr=err,
                    check=False,
                    timeout=1200,
                )
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                exit_code = -1
        attempt = {
            "round": number,
            "exit_code": exit_code,
            "timed_out": exit_code == -1,
            "complete_junit": False,
            "artifacts": {
                path.name: sha256(path.read_bytes()).hexdigest()
                for path in (stdout, stderr, junit)
                if path.exists()
            },
        }
        if junit.exists():
            try:
                suites = list(ET.parse(junit).getroot().iter("testsuite"))
                attempt["tests"] = {
                    key: sum(int(suite.get(key, 0)) for suite in suites)
                    for key in ("tests", "failures", "errors", "skipped")
                }
                attempt["complete_junit"] = True
            except ET.ParseError as error:
                attempt["junit_error"] = str(error)
        counts = attempt.get("tests", {})
        passed = (
            exit_code == 0
            and counts.get("tests", 0) > 0
            and not any(
                counts.get(key, 0) for key in ("failures", "errors", "skipped")
            )
        )
        attempt["status"] = "PASS" if passed else "FAIL"
        manifest["attempts"].append(attempt)
        manifest["status"] = "RUNNING" if passed else "FAIL"
        save()
        print(f"Round {number}: {attempt['status']} {counts}", flush=True)
        if not passed:
            print(f"All attempt output is retained in {output}.", flush=True)
            return 1
    manifest["status"] = "PASS"
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
