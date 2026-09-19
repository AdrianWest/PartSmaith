"""Tests for the Phase 0 command-line interface."""

import json

from partsmith import __version__
from partsmith.cli import collect_diagnostics, main


def test_version_command_prints_package_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out == f"{__version__}\n"


def test_doctor_reports_passing_foundation_checks(capsys):
    assert main(["doctor", "--json"]) == 0
    diagnostics = json.loads(capsys.readouterr().out)
    assert {item["name"] for item in diagnostics} == {
        "cli",
        "package",
        "python",
    }
    assert all(item["status"] == "PASS" for item in diagnostics)


def test_doctor_output_is_deterministic():
    assert collect_diagnostics() == collect_diagnostics()
