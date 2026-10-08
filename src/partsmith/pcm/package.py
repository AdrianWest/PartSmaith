"""@package partsmith.pcm.package
@brief Builds deterministic PCM archives and offline repository fixtures.
@details Packages source directly without invoking a PartSmith build backend.
"""

from __future__ import annotations

import json
import stat
import tomllib
from hashlib import file_digest, sha256
from pathlib import Path, PurePosixPath
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from jsonschema import Draft7Validator

from partsmith.integration.policy import ResourcePolicy
from partsmith.path_support import is_junction

IDENTIFIER = "com.boardforgetools.partsmith"
VERSION = "0.3.1"
INVENTORY = "plugins/inventory.json"
PCM_ICON = "resources/icon.png"
PCM_ICON_SHA256 = (
    "dc06e6c7275a24553b16667cf2fa7c2afe08efcd8a2cfd8a4e02d97864f1fdae"
)
SCHEMA_HASHES = {
    "api.v1.schema.json": (
        "a51ecc9cc4166fc857a0378b6361909c66a7957451146bd50123d52313fdea96"
    ),
    "pcm.v2.schema.json": (
        "74bfb8fca2abdcf619afd152f57bcc768c855541587e21b81e2c6e8fd3b8abb2"
    ),
}


def json_bytes(value: dict) -> bytes:
    """@brief Serializes package data deterministically.
    @param value JSON-compatible mapping.
    @return UTF-8 bytes with sorted keys and a terminal newline.
    @details Rejects non-finite numbers and does not embed local paths.
    """
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _safe_name(name: str) -> None:
    """@brief Rejects nonportable or escaping archive member names.
    @param name Forward-slash relative archive name.
    @return None.
    @details Rejects Windows devices, invalid characters and trailing dots.
    """
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or ":" in name
        or "\\" in name
        or str(path) != name
    ):
        raise ValueError("PCM member path is not portable")
    devices = {"CON", "PRN", "AUX", "NUL"}
    devices |= {f"COM{number}" for number in range(1, 10)}
    devices |= {f"LPT{number}" for number in range(1, 10)}
    for component in path.parts:
        if (
            component.endswith((" ", "."))
            or component.split(".")[0].upper() in devices
            or any(char in '<>:"|?*' or ord(char) < 32 for char in component)
        ):
            raise ValueError("PCM member is not a portable Windows name")


def _unique_names(names: list[str]) -> None:
    """@brief Rejects case aliases and file/directory collisions before reads.
    @param names Relative forward-slash member names.
    @return None.
    @details Uses casefolded Windows identities and checks all ancestor paths.
    """
    seen = set()
    for name in names:
        _safe_name(name)
        alias = name.casefold()
        if alias in seen:
            raise ValueError("Duplicate or case-aliased PCM member")
        seen.add(alias)
    for name in seen:
        if any(str(parent) in seen for parent in PurePosixPath(name).parents):
            raise ValueError("PCM file/directory path collision")


def _tree(root: Path) -> list[Path]:
    """@brief Lists owned source files without generated caches.
    @param root Source directory.
    @return Sorted regular file paths.
    @details Symlinks fail; Python bytecode and caches are never distributed.
    """
    paths = []
    for path in sorted(root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink() or is_junction(path):
            raise ValueError("PCM source cannot contain symlinks")
        if path.is_file():
            paths.append(path)
    return paths


def collect_payload(root: Path) -> dict[str, bytes]:
    """@brief Collects source and every declared engineering resource.
    @param root Repository root containing the declared source tree.
    @return Archive member names mapped to their exact source bytes.
    @details The historical force-include map is resource declaration only.
    """
    payload = {}
    source = root / "src/partsmith"
    for path in _tree(source):
        name = "plugins/partsmith/" + path.relative_to(source).as_posix()
        payload[name] = path.read_bytes()
    config = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))
    resources = config["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    for origin, target in resources.items():
        path = root / origin
        if path.is_dir():
            for child in _tree(path):
                name = "plugins/" + target + "/"
                name += child.relative_to(path).as_posix()
                payload[name] = child.read_bytes()
        else:
            payload["plugins/" + target] = path.read_bytes()
    plugin = root / "integrations/kicad/partsmith_ipc"
    for path in _tree(plugin):
        name = "plugins/" + path.relative_to(plugin).as_posix()
        if name in payload:
            raise ValueError("Duplicate PCM plugin member")
        payload[name] = path.read_bytes()
    payload["plugins/requirements.txt"] = (
        root / "requirements-pcm.txt"
    ).read_bytes()
    payload["plugins/LICENSE"] = (root / "LICENSE").read_bytes()
    payload[PCM_ICON] = (
        root / "resources/PartSmith_Logo_64x64.png"
    ).read_bytes()
    for name in payload:
        _safe_name(name)
    return payload


def _metadata(version: str, install_size: int) -> dict:
    """@brief Constructs archive metadata without self-referential downloads.
    @param version Explicit package release version.
    @param install_size Total extracted archive bytes.
    @return Schema-compatible PCM package metadata.
    @details Advertises only the pinned Windows AMD64 and KiCad 10.0.6 target.
    """
    return {
        "$schema": "https://go.kicad.org/pcm/schemas/v2",
        "name": "PartSmith",
        "description": "Deterministic component preparation and inspection",
        "description_full": (
            "PartSmith IPC action for Windows AMD64, KiCad 10.0.6 and "
            "KiCad's bundled Python 3.11. KiCad prepares pinned binary "
            "dependencies in the background; first preparation requires "
            "internet access. Offline installation is unsupported. "
            "Engineering readiness is checked again by the action."
        ),
        "identifier": IDENTIFIER,
        "type": "plugin",
        "author": {"name": "Board Forge Tools", "contact": {}},
        "license": "GPL-3.0-only",
        "resources": {},
        "versions": [
            {
                "version": version,
                "status": "development",
                "kicad_version": "10.0.6",
                "kicad_version_max": "10.0.6",
                "platforms": ["windows"],
                "runtime": "ipc",
                "install_size": install_size,
            }
        ],
    }


def build_pcm(root: Path, output: Path, version: str = VERSION) -> dict:
    """@brief Writes the deterministic customer PCM ZIP and receipt.
    @param root Repository root supplying owned source and resources.
    @param output Destination archive path.
    @param version Explicit release version for lifecycle fixtures.
    @return Archive identity, inventory identity and extracted size.
    @details Fixed ordering, stored bytes, timestamps and permissions are used.
    """
    payload = collect_payload(root)
    ResourcePolicy().require_sizes(list(map(len, payload.values())))
    inventory = {
        "schema_version": "partsmith-pcm-inventory-1.0",
        "identifier": IDENTIFIER,
        "version": version,
        "files": {
            name.removeprefix("plugins/"): {
                "sha256": sha256(data).hexdigest(),
                "size": len(data),
            }
            for name, data in sorted(payload.items())
            if name.startswith("plugins/")
        },
    }
    payload[INVENTORY] = json_bytes(inventory)
    size = sum(map(len, payload.values()))
    for _ in range(10):
        metadata = json_bytes(_metadata(version, size))
        actual = sum(map(len, payload.values())) + len(metadata)
        if actual == size:
            break
        size = actual
    else:
        raise ValueError("PCM extracted size did not converge")
    payload["metadata.json"] = metadata
    validate_payload(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    blob = output.read_bytes()
    return {
        "identifier": IDENTIFIER,
        "version": version,
        "sha256": sha256(blob).hexdigest(),
        "download_size": len(blob),
        "install_size": size,
        "inventory_sha256": sha256(payload[INVENTORY]).hexdigest(),
        "members": len(payload),
        "package_icon": {
            "path": PCM_ICON,
            "sha256": sha256(payload[PCM_ICON]).hexdigest(),
            "size": len(payload[PCM_ICON]),
        },
    }


def validate_payload(payload: dict[str, bytes]) -> dict:
    """@brief Checks inventory, installed schemas and runtime declaration.
    @param payload Archive member bytes, including root metadata.
    @return Validated archive metadata.
    @details Plugin inventory and the separate PCM listing icon are verified;
    only bundled schemas are resolved and extra/missing members fail.
    """
    _unique_names(list(payload))
    ResourcePolicy().require_sizes(list(map(len, payload.values())))
    for name in payload:
        _safe_name(name)
        if name not in {"metadata.json", PCM_ICON} and not name.startswith(
            "plugins/"
        ):
            raise ValueError("Unexpected PCM top-level member")
    inventory = json.loads(payload[INVENTORY])
    if set(inventory) != {"schema_version", "identifier", "version", "files"}:
        raise ValueError("Unknown PCM inventory field")
    if inventory["schema_version"] != "partsmith-pcm-inventory-1.0":
        raise ValueError("Unknown PCM inventory version")
    expected = {"plugins/" + name for name in inventory["files"]}
    iconless_packages = {f"0.1.{number}" for number in range(6)}
    if inventory["version"] not in iconless_packages:
        expected.add(PCM_ICON)
        icon = payload.get(PCM_ICON, b"")
        if sha256(icon).hexdigest() != PCM_ICON_SHA256:
            raise ValueError("PCM package listing icon is missing or changed")
    if set(payload) != expected | {INVENTORY, "metadata.json"}:
        raise ValueError("PCM inventory contains extra or missing files")
    for name, item in inventory["files"].items():
        _safe_name(name)
        data = payload["plugins/" + name]
        if item != {"sha256": sha256(data).hexdigest(), "size": len(data)}:
            raise ValueError("PCM payload identity differs from inventory")
    schemas = {}
    for name, expected_hash in SCHEMA_HASHES.items():
        blob = payload["plugins/partsmith/pcm/schemas/" + name]
        if sha256(blob).hexdigest() != expected_hash:
            raise ValueError("PCM schema differs from pinned KiCad 10.0.6")
        schemas[name] = json.loads(blob)
    metadata = json.loads(payload["metadata.json"])
    Draft7Validator(schemas["pcm.v2.schema.json"]).validate(metadata)
    if len(metadata["versions"]) != 1:
        raise ValueError("Archive metadata requires exactly one version")
    entry = metadata["versions"][0]
    if metadata != _metadata(entry["version"], entry["install_size"]):
        raise ValueError("PCM archive metadata differs from closed contract")
    if entry["install_size"] != sum(map(len, payload.values())):
        raise ValueError("PCM extracted size differs from metadata")
    if inventory["identifier"] != IDENTIFIER or (
        inventory["version"] != entry["version"]
    ):
        raise ValueError("PCM inventory and metadata identities differ")
    plugin = json.loads(payload["plugins/plugin.json"])
    Draft7Validator(schemas["api.v1.schema.json"]).validate(plugin)
    if set(plugin) != {
        "identifier",
        "name",
        "description",
        "runtime",
        "actions",
    }:
        raise ValueError("Unknown IPC plugin registration field")
    if plugin["identifier"] != IDENTIFIER or plugin["runtime"] != {
        "type": "python",
        "min_version": "3.11",
    }:
        raise ValueError("IPC plugin identity/runtime differs")
    if len(plugin["actions"]) != 1:
        raise ValueError("Unexpected IPC action count")
    action = plugin["actions"][0]
    expected_action = {
        "identifier": "open",
        "name": "Open PartSmith",
        "description": "Open PartSmith after engineering runtime checks",
        "show-button": True,
        "scopes": ["pcb"],
        "entrypoint": "entry.py",
        "icons-light": [
            "icons/PartSmith_Anvil_Icon_24x24.png",
            "icons/PartSmith_Anvil_Icon_64x64.png",
        ],
        "icons-dark": [
            "icons/PartSmith_Anvil_Icon_24x24.png",
            "icons/PartSmith_Anvil_Icon_64x64.png",
        ],
    }
    legacy_iconless_versions = {"0.1.0", "0.1.1", "0.1.2", "0.1.3"}
    if entry["version"] in legacy_iconless_versions:
        del expected_action["icons-light"]
        del expected_action["icons-dark"]
    elif entry["version"] == "0.1.4":
        # Preserve verification of the frozen placeholder-icon fixture.
        for theme in ("icons-light", "icons-dark"):
            expected_action[theme] = [
                "icons/partsmith-24.png",
                "icons/partsmith-48.png",
            ]
    if action != expected_action:
        raise ValueError("IPC action differs from closed registration")
    if "plugins/entry.py" not in payload:
        raise ValueError("IPC action entrypoint is missing")
    for name in action.get("icons-light", []) + action.get("icons-dark", []):
        if "plugins/" + name not in payload:
            raise ValueError("IPC action icon is missing")
    if entry["version"] == "0.1.4" and (
        "plugins/icons/partsmith.svg" not in payload
    ):
        raise ValueError("Owned IPC vector icon source is missing")
    return metadata


def verify_pcm(path: Path) -> dict:
    """@brief Verifies an archive before extraction or publication.
    @param path PCM ZIP path.
    @return Validated root metadata.
    @details Duplicate, encrypted and nonregular members fail closed.
    """
    with ZipFile(path) as archive:
        try:
            registration = archive.getinfo("plugins/plugin.json")
        except KeyError:
            registration = None
        if registration is not None:
            if registration.file_size > 4096:
                raise ValueError("PCM registration is oversized")
            plugin = json.loads(archive.read(registration))
            if plugin.get("runtime") == {"type": "exec"}:
                from .production import verify_production_pcm

                return verify_production_pcm(path)
        names = archive.namelist()
        _unique_names(names)
        ResourcePolicy().require_sizes(
            [item.file_size for item in archive.infolist()]
        )
        for item in archive.infolist():
            mode = item.external_attr >> 16
            if (
                item.flag_bits & 1
                or not stat.S_ISREG(mode)
                or item.compress_type != ZIP_STORED
            ):
                raise ValueError(
                    "PCM members must be regular unencrypted files"
                )
        return validate_payload({name: archive.read(name) for name in names})


def repository_package(archive: Path, url: str) -> dict:
    """@brief Adds repository download data only after archive finalization.
    @param archive Final validated PCM archive.
    @param url Explicit local fixture or hosted archive URL.
    @return Package metadata with exact download size and SHA-256.
    @details Does not modify the archive or claim a hosted release exists.
    """
    metadata = verify_pcm(archive)
    with archive.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    metadata["versions"][0].update(
        download_url=url,
        download_size=archive.stat().st_size,
        download_sha256=digest,
    )
    with ZipFile(archive) as source:
        schema = json.loads(
            source.read("plugins/partsmith/pcm/schemas/pcm.v2.schema.json")
        )
    Draft7Validator(schema).validate(metadata)
    return metadata
