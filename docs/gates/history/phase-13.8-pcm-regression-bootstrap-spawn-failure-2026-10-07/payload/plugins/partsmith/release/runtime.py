"""Verified runtime identities for complete Phase 8 input snapshots."""

import platform
import sys
from hashlib import sha256
from importlib.metadata import distribution, version
from importlib.resources import files
from pathlib import Path

import OCP

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.kicad import KiCadRuntime


def runtime_configuration(kicad: KiCadRuntime) -> dict:
    """Verify the installed CAD tuple against reviewed wheel identities.

    Paths belong to audit metadata. Actual Python patch/build, OS, machine,
    archive hashes, installed content, and native KiCad bytes affect replay.
    """
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("PartSmith requires Python 3.12.x")
    lock_bytes = (
        files(__package__).joinpath("runtime-lock-1.0.json").read_bytes()
    )
    lock = parse_json(lock_bytes)
    tag = f"{platform.system()}-{platform.machine()}"
    archives = lock["platforms"].get(tag)
    if archives is None:
        raise RuntimeError(f"Unreviewed CAD runtime platform: {tag}")
    if kicad.version != lock["kicad_version"]:
        raise RuntimeError("KiCad runtime differs from the reviewed lock")
    if OCP.__version__ != lock["occt_version"]:
        raise RuntimeError("OCCT runtime differs from the reviewed lock")
    identities = []
    for archive in archives:
        installed = distribution(archive["distribution"])
        if installed.version != archive["version"]:
            raise RuntimeError("CAD distribution differs from reviewed lock")
        for name, expected in (archive["files"] | archive["licenses"]).items():
            path = Path(installed.locate_file(name))
            if not path.is_file() or sha256(path.read_bytes()).hexdigest() != (
                expected
            ):
                raise RuntimeError(f"CAD runtime content mismatch: {name}")
        identities.append(
            {key: value for key, value in archive.items() if key != "files"}
            | {
                "installed_content_sha256": sha256(
                    canonical_json(archive["files"])
                ).hexdigest()
            }
        )
    constraints = files(__package__).joinpath("runtime-constraints.txt")
    if not constraints.is_file():
        constraints = (
            Path(__file__).resolve().parents[3] / "requirements-ci.txt"
        )
    constraints_bytes = constraints.read_bytes()
    # Record the complete installed pinned environment. Missing or drifted
    # dependencies fail before generating release files.
    dependencies = {}
    for line in constraints_bytes.decode("utf-8").splitlines():
        if "==" not in line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        if name in {"pytest", "ruff", "iniconfig", "pluggy", "pygments"}:
            continue
        actual = version(name)
        if actual != expected:
            raise RuntimeError(f"Pinned dependency version mismatch: {name}")
        dependencies[name] = actual
    return {
        "python": platform.python_version(),
        "python_baseline": lock["python_baseline"],
        "python_implementation": platform.python_implementation(),
        "python_build": list(platform.python_build()),
        "python_executable_sha256": sha256(
            Path(sys._base_executable).read_bytes()
        ).hexdigest(),
        "platform": tag,
        "cadquery": version("cadquery"),
        "ocp": version("cadquery-ocp"),
        "occt": OCP.__version__,
        "generator": "1.1",
        "validator": "1.0",
        "kicad": {
            "version": kicad.version,
            "executable_sha256": sha256(
                kicad.executable.read_bytes()
            ).hexdigest(),
        },
        "lock_sha256": sha256(lock_bytes).hexdigest(),
        "constraints_sha256": sha256(constraints_bytes).hexdigest(),
        "dependencies": dependencies,
        "archives": identities,
    }
