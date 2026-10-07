"""

@package tests.test_cli
@brief Tests for the Phase 0 command-line interface.
@details Provides the module implementation and public interfaces.
"""

import json

from partsmith import __version__
from partsmith.cli import collect_diagnostics, is_supported_python, main


def test_version_command_prints_package_version(capsys):
    """

    @brief Implements the test_version_command_prints_package_version
    operation.
    @param capsys The capsys argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert main(["version"]) == 0
    assert capsys.readouterr().out == f"{__version__}\n"


def test_doctor_reports_passing_foundation_checks(capsys):
    """

    @brief Implements the test_doctor_reports_passing_foundation_checks
    operation.
    @param capsys The capsys argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert main(["doctor", "--json"]) == 0
    diagnostics = json.loads(capsys.readouterr().out)
    assert {item["name"] for item in diagnostics} == {
        "cli",
        "kicad",
        "package",
        "python",
    }
    assert all(item["status"] == "PASS" for item in diagnostics)


def test_doctor_output_is_deterministic():
    """

    @brief Implements the test_doctor_output_is_deterministic operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert collect_diagnostics() == collect_diagnostics()


def test_supported_python_range_is_exactly_python_3_12():
    """

    @brief Implements the
    test_supported_python_range_is_exactly_python_3_12 operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert not is_supported_python((3, 11))
    assert is_supported_python((3, 12))
    assert not is_supported_python((3, 13))


def test_pdl_inspection_commands(capsys):
    """

    @brief Implements the test_pdl_inspection_commands operation.
    @param capsys The capsys argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert main(["pdl", "list"]) == 0
    catalog = capsys.readouterr().out.splitlines()
    assert catalog == sorted(catalog)
    assert "synthetic-0402@1.0" in catalog
    assert len(catalog) == 9

    assert main(["pdl", "inspect", "synthetic-0402"]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["identity"]["variant"] == "0402"

    assert main(["pdl", "validate", "synthetic-0402"]) == 0
    assert capsys.readouterr().out.startswith("PASS synthetic-0402@1.0 ")


def test_pdl_inspect_reports_missing_entry(capsys):
    """

    @brief Implements the test_pdl_inspect_reports_missing_entry
    operation.
    @param capsys The capsys argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert main(["pdl", "inspect", "missing"]) == 2
    assert "PDL_NOT_FOUND" in capsys.readouterr().err
