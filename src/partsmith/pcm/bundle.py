"""@package partsmith.pcm.bundle
@brief Validates the self-contained Windows production runtime.
@details Uses streaming hashes and separate packaging bounds; importing this
module needs only the bundled Python standard library.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class PackagingPolicy:
    """@brief Bounds the pinned executable PCM runtime independently of IPC.
    @details The dependency closure exceeds the integration payload limit.
    """

    max_file_bytes: int = 256 * 1024 * 1024
    max_total_bytes: int = 3 * 1024 * 1024 * 1024
    max_files: int = 50000

    def require_sizes(self, sizes: list[int]) -> None:
        """@brief Rejects oversized or malformed packaging inventories.
        @param sizes Uncompressed regular-file sizes.
        @return None.
        @details Booleans, negative sizes and excessive totals fail closed.
        """
        if (
            len(sizes) > self.max_files
            or any(type(n) is not int or n < 0 for n in sizes)
            or any(n > self.max_file_bytes for n in sizes)
            or sum(sizes) > self.max_total_bytes
        ):
            raise ValueError("BUNDLE_RESOURCE_LIMIT")


def file_identity(path: Path) -> dict:
    """@brief Hashes a file without loading a native library into memory.
    @param path Regular file to inspect.
    @return SHA-256 and byte size mapping.
    @details Raises OSError for unavailable inputs.
    """
    with path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    return {"sha256": digest, "size": path.stat().st_size}


def confined_file(root: Path, name: str) -> Path:
    """@brief Resolves a portable owned path without traversing links.
    @param root Exact installed plugin directory.
    @param name Forward-slash relative inventory name.
    @return Confined regular file.
    @details Rejects devices, alternate streams, junctions and symlinks.
    """
    relative = PurePosixPath(name)
    devices = {"CON", "PRN", "AUX", "NUL"}
    devices |= {f"{kind}{n}" for kind in ("COM", "LPT") for n in range(1, 10)}
    if (
        not name
        or relative.is_absolute()
        or str(relative) != name
        or ".." in relative.parts
        or "\\" in name
        or any(
            part.endswith((" ", "."))
            or part.split(".")[0].upper() in devices
            or re.search(r'[<>:"|?*\x00-\x1f]', part)
            for part in relative.parts
        )
    ):
        raise ValueError("BUNDLE_UNSAFE_PATH")
    path = root
    for part in relative.parts:
        path /= part
        if path.is_symlink() or path.is_junction():
            raise ValueError("BUNDLE_LINK_FORBIDDEN")
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("BUNDLED_RUNTIME_RESOURCE_MISSING")
    return path


def validate_descriptor(descriptor: dict) -> None:
    """@brief Checks the closed supported production-runtime descriptor.
    @param descriptor Parsed bundle identity document.
    @return None.
    @details Rejects unknown fields and malformed pinned content identities.
    """
    if (
        set(descriptor)
        != {
            "schema_version",
            "platform",
            "architecture",
            "python_version",
            "dependency_manifest_sha256",
            "runtime_lock_sha256",
        }
        or descriptor["schema_version"] != "partsmith-runtime-bundle-1.0"
        or descriptor["python_version"] != "3.12.10"
        or (descriptor["platform"], descriptor["architecture"])
        != ("Windows", "AMD64")
        or any(
            not isinstance(descriptor[k], str)
            or not re.fullmatch(r"[0-9a-f]{64}", descriptor[k])
            for k in ("dependency_manifest_sha256", "runtime_lock_sha256")
        )
    ):
        raise ValueError("BUNDLE_DESCRIPTOR_INVALID")


def validate_dependencies(manifest: dict, records: dict) -> None:
    """@brief Checks complete dependency ownership and retained notices.
    @param manifest Parsed closed dependency manifest.
    @param records Verified installed-file size and SHA-256 inventory.
    @return None.
    @details Requires unique dependency identities, exact notice identities,
    portable declared files and coverage of every runtime and OCR byte.
    """
    if (
        set(manifest) != {"schema_version", "components"}
        or manifest["schema_version"] != "partsmith-dependencies-1.0"
        or not isinstance(manifest["components"], list)
        or not manifest["components"]
    ):
        raise ValueError("BUNDLE_DEPENDENCY_MANIFEST_INVALID")
    covered, identities = set(), set()
    for component in manifest["components"]:
        if set(component) != {
            "name",
            "version",
            "source",
            "sha256",
            "license",
            "platform",
            "architecture",
            "files",
            "license_files",
        } or any(
            not isinstance(component[k], str) or not component[k].strip()
            for k in ("name", "version", "source", "sha256", "license")
        ):
            raise ValueError("BUNDLE_DEPENDENCY_IDENTITY_INVALID")
        identity = (component["name"].casefold(), component["version"])
        if identity in identities:
            raise ValueError("BUNDLE_DEPENDENCY_IDENTITY_INVALID")
        identities.add(identity)
        files = component["files"]
        licenses = component["license_files"]
        if (
            not component["source"].startswith("https://")
            or not re.fullmatch(r"[0-9a-f]{64}", component["sha256"])
            or component["platform"] != "Windows"
            or component["architecture"] != "AMD64"
            or not isinstance(files, list)
            or not files
            or any(not isinstance(n, str) for n in files)
            or len(files) != len(set(files))
            or not isinstance(licenses, dict)
            or not licenses
        ):
            raise ValueError("BUNDLE_DEPENDENCY_LICENSE_MISSING")
        for name, expected in licenses.items():
            if name not in files or records.get(name) != expected:
                raise ValueError("BUNDLE_DEPENDENCY_LICENSE_CHANGED")
        for name in files:
            if name not in records:
                raise ValueError("BUNDLE_DEPENDENCY_FILE_MISSING")
            covered.add(name)
    required = {
        name
        for name in records
        if name.startswith(("runtime/", "ocr/", "licenses/"))
    }
    if not required <= covered:
        raise ValueError("BUNDLE_DEPENDENCY_FILE_UNDECLARED")


def verify_bundle(root: Path, *, interpreter: bool = True) -> dict:
    """@brief Verifies byte ownership, isolation and dependency licenses.
    @param root Exact installed executable PCM root.
    @param interpreter Whether the running interpreter must belong to root.
    @return Verified bundle descriptor including dependency manifest hash.
    @details No repository, user-site or externally installed runtime fallback
    is accepted. Validation uses no third-party imports or subprocesses.
    """
    descriptor = json.loads(confined_file(root, "bundle.json").read_bytes())
    validate_descriptor(descriptor)
    if interpreter and (
        not sys.flags.isolated
        or not Path(sys.executable)
        .resolve()
        .is_relative_to((root / "runtime").resolve())
        or ".".join(map(str, sys.version_info[:3]))
        != descriptor["python_version"]
    ):
        raise ValueError("BUNDLED_PYTHON_REQUIRED")
    inventory = json.loads(confined_file(root, "inventory.json").read_bytes())
    if set(inventory) != {"schema_version", "identifier", "version", "files"}:
        raise ValueError("BUNDLE_INVENTORY_INVALID")
    if (
        inventory["schema_version"] != "partsmith-pcm-inventory-1.0"
        or inventory["identifier"] != "com.boardforgetools.partsmith"
    ):
        raise ValueError("BUNDLE_INVENTORY_INVALID")
    records = inventory["files"]
    PackagingPolicy().require_sizes(
        [item["size"] for item in records.values()]
    )
    if len({name.casefold() for name in records}) != len(records):
        raise ValueError("BUNDLE_CASE_ALIAS")
    for name, expected in records.items():
        if file_identity(confined_file(root, name)) != expected:
            raise ValueError("BUNDLED_RUNTIME_RESOURCE_CHANGED")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink() or path.is_junction():
            raise ValueError("BUNDLE_LINK_FORBIDDEN")
        if path.suffix.lower() in {".pyc", ".pyo"}:
            raise ValueError("BUNDLE_BYTECODE_FORBIDDEN")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(records) | {"inventory.json"}:
        raise ValueError("BUNDLED_RUNTIME_RESOURCE_UNDECLARED")
    manifest_bytes = confined_file(root, "dependencies.json").read_bytes()
    if (
        sha256(manifest_bytes).hexdigest()
        != (descriptor["dependency_manifest_sha256"])
    ):
        raise ValueError("BUNDLE_DEPENDENCY_MANIFEST_CHANGED")
    validate_dependencies(json.loads(manifest_bytes), records)
    return descriptor
