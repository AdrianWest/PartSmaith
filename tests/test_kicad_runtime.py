"""@package tests.test_kicad_runtime
@brief Tests mandatory native KiCad 10 discovery and artifact validation.
@details Exercises the installed target runtime against committed artifacts.
"""

from pathlib import Path

import pytest

from partsmith.kicad import (
    KiCadCompatibilityError,
    discover_kicad,
    validate_native_artifacts,
)
from partsmith.kicad import runtime as runtime_module

ROOT = Path(__file__).resolve().parents[1]


def test_discovers_required_native_kicad_10():
    """@brief Verifies the mandatory native KiCad runtime is available.
    @return None.
    @details Phase 8 cannot pass when the target-major runtime is absent.
    """
    runtime = discover_kicad()
    assert runtime.major_version == 10
    assert runtime.version == "10.0.6"
    assert runtime.executable.is_file()


def test_native_kicad_round_trips_and_renders_artifacts():
    """@brief Verifies native KiCad parses and renders exact artifacts.
    @return None.
    @details Both symbol and footprint libraries must produce native outputs.
    """
    validation = validate_native_artifacts(
        discover_kicad(),
        target="10.x",
        symbol_filename="0402.kicad_sym",
        symbol_content=(
            ROOT / "fixtures" / "symbol" / "expected" / "0402.kicad_sym"
        ).read_bytes(),
        footprint_filename="0402.kicad_mod",
        footprint_content=(
            ROOT / "fixtures" / "footprint" / "expected" / "0402.kicad_mod"
        ).read_bytes(),
        model_path="3d/0402.step",
        model_content=(
            ROOT / "fixtures" / "threed" / "expected" / "0402.step"
        ).read_bytes(),
    )
    assert validation.runtime.major_version == 10
    assert validation.output_hashes
    assert validation.operations == (
        "sym-upgrade",
        "sym-export-svg",
        "fp-upgrade",
        "fp-export-svg",
    )


def test_native_kicad_rejects_wrong_target_major():
    """@brief Verifies target/runtime mismatches fail closed.
    @return None.
    @details A different requested target cannot reuse KiCad 10 evidence.
    """
    with pytest.raises(KiCadCompatibilityError, match="does not match"):
        validate_native_artifacts(
            discover_kicad(),
            target="9.x",
            symbol_filename="unused.kicad_sym",
            symbol_content=b"",
            footprint_filename="unused.kicad_mod",
            footprint_content=b"",
            model_path="3d/unused.step",
            model_content=b"",
        )


def test_native_kicad_discovery_fails_when_target_is_unavailable(
    monkeypatch,
):
    """@brief Verifies unavailable native KiCad fails explicitly.
    @param monkeypatch Pytest patch fixture.
    @return None.
    @details Internal parsers cannot replace a missing target runtime.
    """
    monkeypatch.setattr(runtime_module, "_candidate_paths", lambda: ())
    with pytest.raises(KiCadCompatibilityError, match="is required"):
        discover_kicad()
