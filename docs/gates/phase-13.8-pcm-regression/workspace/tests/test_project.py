"""

@package tests.test_project
@brief Tests that protect the Phase 0 repository contract.
@details Provides the module implementation and public interfaces.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_zero_directories_exist():
    """

    @brief Implements the test_phase_zero_directories_exist operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    for directory in (
        "fixtures",
        "migrations",
        "pdl",
        "schemas",
        "src",
        "tests",
    ):
        assert (ROOT / directory).is_dir()


def test_build_configuration_exists():
    """

    @brief Implements the test_build_configuration_exists operation.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()
    assert (ROOT / "requirements-ci.txt").is_file()
