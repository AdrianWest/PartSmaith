"""@package partsmith.pcm.production
@brief Builds and verifies a self-contained executable PCM archive.
@details Preserves the frozen Phase 13 Python-package contract. Production
archives use independently bounded streaming I/O and a pinned portable loader.
"""

from __future__ import annotations

import json
import shutil
import stat
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from jsonschema import Draft7Validator

from .bundle import (
    PackagingPolicy,
    confined_file,
    file_identity,
    validate_dependencies,
    validate_descriptor,
)
from .package import (
    IDENTIFIER,
    INVENTORY,
    PCM_ICON,
    PCM_ICON_SHA256,
    SCHEMA_HASHES,
    _metadata,
    _unique_names,
    collect_payload,
    json_bytes,
)

PRODUCTION_VERSION = "0.2.0"


def registration() -> dict:
    """@brief Returns the closed KiCad executable-action contract.
    @return Exact supported production registration document.
    @details Keeps action scope, entry point and real icon names explicit.
    """
    icons = [
        "icons/PartSmith_Anvil_Icon_24x24.png",
        "icons/PartSmith_Anvil_Icon_64x64.png",
    ]
    return {
        "identifier": IDENTIFIER,
        "name": "PartSmith",
        "description": "Deterministic component preparation and inspection",
        "runtime": {"type": "exec"},
        "actions": [
            {
                "identifier": "open",
                "name": "Open PartSmith",
                "description": (
                    "Open PartSmith after engineering runtime checks"
                ),
                "show-button": True,
                "scopes": ["pcb"],
                "entrypoint": "PartSmith.exe",
                "icons-light": icons,
                "icons-dark": icons.copy(),
            }
        ],
    }


def metadata(version: str, size: int) -> dict:
    """@brief Declares the Windows executable PCM distribution.
    @param version Explicit build version.
    @param size Exact uncompressed archive size.
    @return Closed KiCad metadata document.
    @details Development status remains until all Phase 14 evidence passes.
    """
    result = _metadata(version, size)
    result["description_full"] = (
        "PartSmith for Windows AMD64 and KiCad 10.0.6. Includes isolated "
        "Python 3.12, the pinned CAD runtime, OCR and application "
        "dependencies. "
        "Install the PCM ZIP and launch the action; no separate Python, pip "
        "or Conda installation is required. Phase 14 acceptance candidate."
    )
    return result


def portable_launcher(binary: bytes, *, gui: bool) -> bytes:
    """@brief Appends deterministic isolated bootstrap code to distlib.
    @param binary Reviewed Windows AMD64 distlib launcher bytes.
    @param gui Whether to select the windowed embedded interpreter.
    @return Portable native executable bytes.
    @details The launcher-relative interpreter survives moves and spaces;
    the embedded path file excludes user site, PYTHONPATH and current cwd.
    """
    bootstrap = (
        b'"""@file __main__.py\n'
        b"@brief Boots the isolated PCM runtime.\n"
        b'@details Validates bundled bytes before application imports.\n"""\n'
        b"import json, os, runpy, sys\n"
        b"from pathlib import Path\n"
        b"root = Path(sys.argv[0]).resolve().parent\n"
        b"sys.dont_write_bytecode = True\n"
        b"try:\n"
        b"    count = 0\n"
        b"    for folder, dirs, files in os.walk(root, followlinks=False):\n"
        b"        count += len(dirs) + len(files)\n"
        b"        if count > 100000:\n"
        b"            raise ValueError('BUNDLE_RESOURCE_LIMIT')\n"
        b"        for name in dirs + files:\n"
        b"            path = Path(folder)/name\n"
        b"            if path.is_symlink() or path.is_junction():\n"
        b"                raise ValueError('BUNDLE_LINK_FORBIDDEN')\n"
        b"            if path.suffix.lower() in ('.pyc', '.pyo'):\n"
        b"                raise ValueError('BUNDLE_BYTECODE_FORBIDDEN')\n"
        b"    from partsmith.pcm.bundle import verify_bundle\n"
        b"    verify_bundle(root)\n"
        b"except Exception as error:\n"
        b"    code = str(error) if isinstance(error, ValueError) "
        b"else 'BUNDLED_RUNTIME_CHECK_FAILED'\n"
        b"    report = {'state':'FAILED','code':code}\n"
        b"    if sys.stdout: print(json.dumps(report), flush=True)\n"
        b"    if not any(a in sys.argv for a in "
        b"('--diagnostics', '--self-test')):\n"
        b"        import ctypes\n"
        b"        ctypes.windll.user32.MessageBoxW(None, "
        b"'PartSmith runtime is not ready: '+code, 'PartSmith runtime', 16)\n"
        b"    raise SystemExit(2)\n"
        b"os.environ['PARTSMITH_TESSERACT'] = "
        b"str(root/'ocr/bin/tesseract.exe')\n"
        b"os.environ['TESSDATA_PREFIX'] = str(root/'ocr/tessdata')\n"
        b"dll_search = os.add_dll_directory(str(root/'ocr/bin'))\n"
        b"runpy.run_path(str(root/'entry.py'), run_name='__main__')\n"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        info = ZipInfo("__main__.py", (1980, 1, 1, 0, 0, 0))
        archive.writestr(info, bootstrap)
    interpreter = b"pythonw.exe" if gui else b"python.exe"
    return (
        binary
        + b"#!<launcher_dir>\\runtime\\"
        + interpreter
        + b" -I\n"
        + buffer.getvalue()
    )


def build_production_pcm(
    root: Path, runtime: Path, output: Path, version: str = PRODUCTION_VERSION
) -> dict:
    """@brief Packages exact locked runtime bytes and application resources.
    @param root Repository source root.
    @param runtime Prepared producer directory from the committed lock.
    @param output Destination PCM ZIP, replaced only after verification.
    @param version Explicit acceptance-candidate version.
    @return Artifact receipt with archive and dependency manifest identities.
    @details No dependency resolution, downloads or installation happen here.
    Hashing and ZIP writes are streamed so large CAD libraries stay bounded.
    """
    lock_bytes = (root / "resources/runtime/production-lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    payload = collect_payload(root)
    payload["plugins/plugin.json"] = json_bytes(registration())
    paths = {}
    for name, record in lock["files"].items():
        path = confined_file(runtime, name)
        if file_identity(path) != {k: record[k] for k in ("sha256", "size")}:
            raise ValueError("BUNDLE_PREPARED_INPUT_CHANGED: " + name)
        if not name.startswith("launchers/"):
            paths["plugins/" + name] = path
    payload["plugins/runtime/python312._pth"] = (
        b"python312.zip\n.\nLib/site-packages\n..\n"
    )
    paths.pop("plugins/runtime/python312._pth")
    for filename, launcher, gui in (
        ("PartSmith.exe", "w64.exe", True),
        ("PartSmith-diagnostics.exe", "t64.exe", False),
    ):
        payload["plugins/" + filename] = portable_launcher(
            (runtime / "launchers" / launcher).read_bytes(), gui=gui
        )
    components = json.loads(json.dumps(lock["components"]))
    for item in components:
        item["files"] = [
            n for n in item["files"] if not n.startswith("launchers/")
        ]
        if item["name"] == "distlib-launcher":
            item["files"] += ["PartSmith.exe", "PartSmith-diagnostics.exe"]
    dependencies = json_bytes(
        {
            "schema_version": "partsmith-dependencies-1.0",
            "components": components,
        }
    )
    payload["plugins/dependencies.json"] = dependencies
    payload["plugins/bundle.json"] = json_bytes(
        {
            "schema_version": "partsmith-runtime-bundle-1.0",
            "platform": "Windows",
            "architecture": "AMD64",
            "python_version": lock["python_version"],
            "dependency_manifest_sha256": sha256(dependencies).hexdigest(),
            "runtime_lock_sha256": sha256(lock_bytes).hexdigest(),
        }
    )
    _unique_names(list(payload) + list(paths))
    records = {
        name.removeprefix("plugins/"): file_identity(path)
        for name, path in sorted(paths.items())
    }
    records.update(
        {
            name.removeprefix("plugins/"): {
                "sha256": sha256(blob).hexdigest(),
                "size": len(blob),
            }
            for name, blob in payload.items()
            if name.startswith("plugins/")
        }
    )
    payload[INVENTORY] = json_bytes(
        {
            "schema_version": "partsmith-pcm-inventory-1.0",
            "identifier": IDENTIFIER,
            "version": version,
            "files": dict(sorted(records.items())),
        }
    )
    size = sum(item["size"] for item in records.values())
    size += len(payload[INVENTORY]) + len(payload[PCM_ICON])
    for _ in range(10):
        document = json_bytes(metadata(version, size))
        actual = sum(p.stat().st_size for p in paths.values())
        actual += sum(map(len, payload.values())) + len(document)
        if size == actual:
            break
        size = actual
    else:
        raise ValueError("BUNDLE_SIZE_DID_NOT_CONVERGE")
    payload["metadata.json"] = document
    PackagingPolicy().require_sizes(
        [len(blob) for blob in payload.values()]
        + [path.stat().st_size for path in paths.values()]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    with ZipFile(temporary, "w", compression=ZIP_STORED) as archive:
        for name in sorted(set(payload) | set(paths)):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            if name in payload:
                archive.writestr(info, payload[name])
            else:
                info.file_size = paths[name].stat().st_size
                with paths[name].open("rb") as source:
                    with archive.open(info, "w") as destination:
                        shutil.copyfileobj(source, destination, 1024 * 1024)
    verify_production_pcm(temporary)
    temporary.replace(output)
    return file_identity(output) | {
        "identifier": IDENTIFIER,
        "version": version,
        "install_size": size,
        "members": len(payload) + len(paths),
        "inventory_sha256": sha256(payload[INVENTORY]).hexdigest(),
        "dependency_manifest_sha256": sha256(dependencies).hexdigest(),
        "runtime_lock_sha256": sha256(lock_bytes).hexdigest(),
    }


def verify_production_pcm(path: Path) -> dict:
    """@brief Verifies the complete executable PCM before extraction.
    @param path Final or temporary production archive.
    @return Closed validated metadata document.
    @details Rejects unsafe paths, types, compression, inventory drift and
    altered license bytes; hashes native libraries with bounded memory.
    """
    with ZipFile(path) as archive:
        _unique_names(archive.namelist())
        if any(
            Path(name).suffix.lower() in {".pyc", ".pyo"}
            for name in archive.namelist()
        ):
            raise ValueError("BUNDLE_BYTECODE_FORBIDDEN")
        PackagingPolicy().require_sizes(
            [i.file_size for i in archive.infolist()]
        )
        for item in archive.infolist():
            if (
                item.flag_bits & 1
                or not stat.S_ISREG(item.external_attr >> 16)
                or item.compress_type != ZIP_STORED
            ):
                raise ValueError("BUNDLE_INVALID_ZIP_MEMBER")
        for name in (
            INVENTORY,
            "metadata.json",
            "plugins/dependencies.json",
            "plugins/bundle.json",
            "plugins/plugin.json",
        ):
            if archive.getinfo(name).file_size > 16 * 1024 * 1024:
                raise ValueError("BUNDLE_MANIFEST_LIMIT")
        inventory = json.loads(archive.read(INVENTORY))
        if set(inventory) != {
            "schema_version",
            "identifier",
            "version",
            "files",
        }:
            raise ValueError("BUNDLE_INVENTORY_INVALID")
        if inventory["schema_version"] != "partsmith-pcm-inventory-1.0":
            raise ValueError("BUNDLE_INVENTORY_VERSION")
        expected = {"plugins/" + n for n in inventory["files"]}
        if set(archive.namelist()) != expected | {
            INVENTORY,
            "metadata.json",
            PCM_ICON,
        }:
            raise ValueError("BUNDLE_INVENTORY_MEMBERS")
        for name, record in inventory["files"].items():
            with archive.open("plugins/" + name) as source:
                digest = sha256()
                while block := source.read(1024 * 1024):
                    digest.update(block)
            if record != {
                "sha256": digest.hexdigest(),
                "size": archive.getinfo("plugins/" + name).file_size,
            }:
                raise ValueError("BUNDLE_PAYLOAD_CHANGED")
        if sha256(archive.read(PCM_ICON)).hexdigest() != PCM_ICON_SHA256:
            raise ValueError("BUNDLE_ICON_CHANGED")
        schemas = {}
        for name, expected_hash in SCHEMA_HASHES.items():
            blob = archive.read("plugins/partsmith/pcm/schemas/" + name)
            if sha256(blob).hexdigest() != expected_hash:
                raise ValueError("BUNDLE_SCHEMA_CHANGED")
            schemas[name] = json.loads(blob)
        document = json.loads(archive.read("metadata.json"))
        Draft7Validator(schemas["pcm.v2.schema.json"]).validate(document)
        size = sum(i.file_size for i in archive.infolist())
        if document != metadata(inventory["version"], size):
            raise ValueError("BUNDLE_METADATA_CHANGED")
        if inventory["identifier"] != IDENTIFIER:
            raise ValueError("BUNDLE_IDENTITY_CHANGED")
        plugin = json.loads(archive.read("plugins/plugin.json"))
        Draft7Validator(schemas["api.v1.schema.json"]).validate(plugin)
        if plugin != registration():
            raise ValueError("BUNDLE_REGISTRATION_CHANGED")
        manifest_bytes = archive.read("plugins/dependencies.json")
        bundle = json.loads(archive.read("plugins/bundle.json"))
        validate_descriptor(bundle)
        if (
            bundle["dependency_manifest_sha256"]
            != sha256(manifest_bytes).hexdigest()
        ):
            raise ValueError("BUNDLE_DEPENDENCY_MANIFEST_CHANGED")
        validate_dependencies(json.loads(manifest_bytes), inventory["files"])
        return document
