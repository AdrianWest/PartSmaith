"""@package partsmith.pcm.runtime
@brief Gates installed PCM actions on engineering runtime and resource checks.
@details Uses safe diagnostic codes and never records IPC tokens or secrets.
"""

from __future__ import annotations

import json
import platform
import sys
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path


def verify_inventory(root: Path) -> dict:
    """@brief Checks every owned installed plugin byte against its inventory.
    @param root PCM-installed plugin root with inventory.json.
    @return Verified inventory document.
    @details Ignores bytecode and rejects symlinks and escaping paths.
    """
    inventory = json.loads((root / "inventory.json").read_bytes())
    from partsmith.integration.policy import ResourcePolicy

    from .package import IDENTIFIER, _unique_names

    if set(inventory) != {"schema_version", "identifier", "version", "files"}:
        raise ValueError("PCM_INVENTORY_FIELDS")
    if inventory["schema_version"] != "partsmith-pcm-inventory-1.0":
        raise ValueError("PCM_INVENTORY_VERSION")
    if inventory["identifier"] != IDENTIFIER:
        raise ValueError("PCM_INVENTORY_IDENTITY")
    _unique_names(list(inventory["files"]))
    ResourcePolicy().require_sizes(
        [item["size"] for item in inventory["files"].values()]
    )
    for name, item in inventory["files"].items():
        path = root / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file()
        ):
            raise ValueError("PCM_RESOURCE_MISSING")
        blob = path.read_bytes()
        if item != {"sha256": sha256(blob).hexdigest(), "size": len(blob)}:
            raise ValueError("PCM_RESOURCE_CHANGED")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    if actual != set(inventory["files"]) | {"inventory.json"}:
        raise ValueError("PCM_RESOURCE_UNDECLARED")
    return inventory


def readiness(root: Path) -> dict:
    """@brief Verifies Python, locked binary/CAD dependencies and resources.
    @param root Exact installed plugin root, never a repository fallback.
    @return Safe diagnostic document with READY or FAILED and stable code.
    @details Failures do not serialize exception text or import legacy pcbnew.
    """
    result = {
        "schema_version": "partsmith-pcm-readiness-1.0",
        "state": "FAILED",
        "python": platform.python_version(),
        "code": "PYTHON_312_REQUIRED",
    }
    if sys.version_info[:2] != (3, 12):
        return result
    result["code"] = "WINDOWS_AMD64_REQUIRED"
    if (platform.system(), platform.machine()) != ("Windows", "AMD64"):
        return result
    try:
        result["code"] = "PCM_RESOURCE_CHECK_FAILED"
        inventory = verify_inventory(root)
        result["code"] = "PINNED_DEPENDENCY_MISSING_OR_CHANGED"
        pins = {}
        for line in (
            (root / "requirements.txt").read_text("utf-8").splitlines()
        ):
            if not line or line.startswith("#"):
                continue
            name, expected = line.split("==")
            actual = version(name)
            if actual != expected:
                return result
            pins[name] = actual
        result["code"] = "IPC_BINDING_API_BUILD_CHANGED"
        from kipy.kicad_api_version import KICAD_API_VERSION

        if KICAD_API_VERSION != "10.0.6-0-gcaf7377e9c":
            return result
        result["code"] = "PCM_SCHEMA_CHECK_FAILED"
        from jsonschema import Draft7Validator

        from .package import SCHEMA_HASHES

        schemas = {}
        for name, expected in SCHEMA_HASHES.items():
            blob = (root / "partsmith/pcm/schemas" / name).read_bytes()
            if sha256(blob).hexdigest() != expected:
                return result
            schemas[name] = json.loads(blob)
        plugin = json.loads((root / "plugin.json").read_bytes())
        Draft7Validator(schemas["api.v1.schema.json"]).validate(plugin)
        result["code"] = "ENGINEERING_RUNTIME_CHECK_FAILED"
        from partsmith.kicad import discover_kicad
        from partsmith.release.runtime import runtime_configuration

        engineering = runtime_configuration(discover_kicad())
        result.update(
            state="READY",
            code="READY",
            package_version=inventory["version"],
            inventory_sha256=sha256(
                (root / "inventory.json").read_bytes()
            ).hexdigest(),
            dependencies=pins,
            engineering=engineering,
        )
    except Exception:
        # Third-party messages can contain endpoints or credentials; retain
        # only the boundary code and let an explicit diagnostic retry recover.
        return result
    return result
