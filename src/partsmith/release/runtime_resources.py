"""@package partsmith.release.runtime_resources
@brief Selects reviewed runtime resources for the running Python baseline.
@details Preserves the frozen 3.12 lock for historical release verification.
The customer PCM baseline is 3.11 on Windows AMD64.
"""

import sys
from importlib.resources import files
from pathlib import Path


def runtime_resources() -> tuple[bytes, bytes]:
    """@brief Loads matching CAD lock and complete dependency constraints.
    @return Exact lock and constraints bytes for the running interpreter.
    @details Installed resources take precedence; checkout fallbacks only
    supply constraints. Unsupported Python baselines fail before generation.
    """
    minor = sys.version_info[:2]
    if minor not in {(3, 11), (3, 12)}:
        raise RuntimeError("PartSmith requires Python 3.11.x or 3.12.x")
    release = files("partsmith.release")
    lock_name = (
        "runtime-lock-1.1.json"
        if minor == (3, 11)
        else "runtime-lock-1.0.json"
    )
    constraints_name = (
        "runtime-constraints-311.txt"
        if minor == (3, 11)
        else "runtime-constraints.txt"
    )
    constraints = release.joinpath(constraints_name)
    if not constraints.is_file():
        constraints = Path(__file__).resolve().parents[3] / (
            "requirements-pcm.txt"
            if minor == (3, 11)
            else "requirements-ci.txt"
        )
    return release.joinpath(lock_name).read_bytes(), constraints.read_bytes()
