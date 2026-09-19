"""Tests that protect the Phase 0 repository contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_zero_directories_exist():
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
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()
    assert (ROOT / "requirements-ci.txt").is_file()
