"""@package partsmith.pcm.installation
@brief Installs and upgrades verified PCM archives with transactional backups.
@details Requires closed KiCad applications and preserves unrelated packages.
Customer operations run using the isolated bundled executable.
"""

import argparse
import ctypes
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from .package import IDENTIFIER, verify_pcm
from .runtime import verify_inventory

DIRECTORY = IDENTIFIER.replace(".", "_")


def documents_directory() -> Path:
    """@brief Resolves the user's actual Windows Documents folder.
    @return Documents path including any configured folder redirection.
    @details Uses the Windows shell rather than assuming a profile subfolder.
    """
    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)
    if result != 0:
        raise OSError("Cannot locate the Windows Documents folder")
    return Path(buffer.value)


def installation_paths(settings=None, third_party=None):
    """@brief Resolves KiCad 10 configuration and third-party package paths.
    @param settings Optional explicit versioned KiCad settings directory.
    @param third_party Optional explicit third-party content root.
    @return Versioned settings path and third-party package root.
    @details Honors KiCad's configured or external KICAD10_3RD_PARTY value.
    """
    settings = settings or Path(os.environ["APPDATA"]) / "kicad/10.0"
    common = json.loads((settings / "kicad_common.json").read_bytes())
    variables = (common.get("environment") or {}).get("vars") or {}
    configured = variables.get("KICAD10_3RD_PARTY")
    if third_party is None:
        chosen = os.environ.get("KICAD10_3RD_PARTY") or configured
        third_party = (
            Path(os.path.expandvars(chosen))
            if chosen
            else documents_directory() / "KiCad/10.0/3rdparty"
        )
    return settings.resolve(), third_party.resolve()


def require_closed_kicad() -> None:
    """@brief Refuses installation while a KiCad application is running.
    @return None.
    @details Never force-closes editors or discards project changes.
    """
    from partsmith.integration.host import WindowsHostApi

    api = WindowsHostApi()
    names = {name for _, name in api.processes().values()}
    if (
        names & {"kicad.exe", "pcbnew.exe", "eeschema.exe", "fpedit.exe"}
        or api.partsmith_is_open()
    ):
        raise RuntimeError(
            "Close KiCad and PartSmith, then run the installer."
        )


def require_owned_path(path: Path, root: Path) -> None:
    """@brief Rejects package targets redirected outside their intended root.
    @param path Explicit installer-owned package path.
    @param root Intended package-root directory.
    @return None.
    @details Rejects symlinks, junctions and existing non-directory targets.
    """
    resolved = path.resolve()
    if (
        not resolved.is_relative_to(root.resolve())
        or resolved == root.resolve()
    ):
        raise ValueError("Installer target escapes the KiCad package root")
    for part in [path, *path.parents]:
        if part == root.parent:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError(
                "Installer targets cannot contain path redirection"
            )
    if path.exists() and not path.is_dir():
        raise ValueError("Package target must be a directory")


def install_archive(
    archive: Path, settings: Path, third_party: Path, *, before_publish=None
) -> dict:
    """@brief Installs only PartSmith's verified payload and PCM registration.
    @param archive Fully built and schema-verified PCM ZIP.
    @param settings Closed KiCad's versioned settings directory.
    @param third_party Explicit third-party content root.
    @param before_publish Optional final closed-host preflight callback.
    @return Installed version, payload identities and retained backup path.
    @details Stages outside plugin discovery; rollback restores prior bytes.
    """
    metadata = verify_pcm(archive)
    registry = settings / "installed_packages.json"
    before = registry.read_bytes() if registry.exists() else None
    document = json.loads(before) if before is not None else {"packages": []}
    if not isinstance(document.get("packages"), list):
        raise ValueError("Invalid KiCad package registry")
    plugin = third_party / "plugins" / DIRECTORY
    resources = third_party / "resources" / DIRECTORY
    require_owned_path(plugin, third_party)
    require_owned_path(resources, third_party)
    if plugin.exists():
        registration = json.loads((plugin / "plugin.json").read_bytes())
        if registration.get("identifier") != IDENTIFIER:
            raise ValueError("Existing directory is not the PartSmith plugin")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex
    backup = third_party.parent / "PartSmith-install-backups" / stamp
    backup.mkdir(parents=True)
    if before is not None:
        (backup / "installed_packages.before.json").write_bytes(before)
    staged_plugin = backup / "new-plugin"
    staged_resources = backup / "new-resources"
    staged_plugin.mkdir()
    staged_resources.mkdir()
    with ZipFile(archive) as package:
        for name in package.namelist():
            if name.startswith("plugins/"):
                target = staged_plugin / name.removeprefix("plugins/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(package.read(name))
        (staged_resources / "icon.png").write_bytes(
            package.read("resources/icon.png")
        )
    inventory = verify_inventory(staged_plugin)
    version = inventory["version"]
    existing = [
        item
        for item in document["packages"]
        if item.get("package", {}).get("identifier") == IDENTIFIER
    ]
    if len(existing) > 1:
        raise ValueError("Duplicate PartSmith PCM registrations")
    replacement = {
        "current_version": version,
        "install_timestamp": int(time.time()),
        "package": {
            key: value for key, value in metadata.items() if key != "$schema"
        },
        "pinned": existing[0].get("pinned", False) if existing else False,
        "repository_id": "",
        "repository_name": "Local file",
    }
    document["packages"] = [
        replacement if item in existing else item
        for item in document["packages"]
    ]
    if not existing:
        document["packages"].append(replacement)
    after = (json.dumps(document, indent=4) + "\n").encode("utf-8")
    pending = settings / (".partsmith-packages-" + uuid4().hex + ".tmp")
    pending.write_bytes(after)
    installed = []
    retained = []
    try:
        if before_publish is not None:
            before_publish()
        if (registry.read_bytes() if registry.exists() else None) != before:
            raise RuntimeError("KiCad package registry changed during staging")
        for target, staged, old_name in (
            (plugin, staged_plugin, "previous-plugin"),
            (resources, staged_resources, "previous-resources"),
        ):
            require_owned_path(target, third_party)
            target.parent.mkdir(parents=True, exist_ok=True)
            old = backup / old_name
            if target.exists():
                target.replace(old)
                retained.append((target, old))
            staged.replace(target)
            installed.append(target)
        verify_inventory(plugin)
        pending.replace(registry)
    except Exception:
        for target in reversed(installed):
            require_owned_path(target, third_party)
            target.replace(backup / ("failed-" + target.parent.name))
        for target, old in reversed(retained):
            old.replace(target)
        if pending.exists():
            pending.replace(backup / "uncommitted-packages.json")
        raise
    report = {
        "status": "INSTALLED",
        "version": version,
        "plugin_root": str(plugin),
        "backup": str(backup),
        "verified_files": len(inventory["files"]),
        "runtime_preparation": (
            "Bundled and verified"
            if (plugin / "bundle.json").is_file()
            else "Owned by KiCad on next startup"
        ),
    }
    try:
        (backup / "installation.json").write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        report["receipt_warning"] = (
            "Installation committed; receipt unavailable"
        )
    return report


def uninstall(settings: Path, third_party: Path) -> dict:
    """@brief Removes the verified owned package by retaining rollback bytes.
    @param settings Closed KiCad's versioned settings directory.
    @param third_party Explicit third-party content root.
    @return Removal receipt with retained payload and registry backup.
    @details Unrelated registrations and user application state survive;
    moved paths remain confined outside recursive KiCad plugin discovery.
    """
    registry = settings / "installed_packages.json"
    before = registry.read_bytes()
    document = json.loads(before)
    matches = [
        p
        for p in document["packages"]
        if p.get("package", {}).get("identifier") == IDENTIFIER
    ]
    if len(matches) != 1:
        raise ValueError("Expected exactly one PartSmith registration")
    plugin = third_party / "plugins" / DIRECTORY
    resources = third_party / "resources" / DIRECTORY
    require_owned_path(plugin, third_party)
    require_owned_path(resources, third_party)
    verify_inventory(plugin)
    if (
        json.loads((plugin / "plugin.json").read_bytes()).get("identifier")
        != IDENTIFIER
    ):
        raise ValueError("Uninstall target is not the PartSmith plugin")
    backup = third_party.parent / "PartSmith-install-backups"
    backup /= datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex
    backup.mkdir(parents=True)
    (backup / "installed_packages.before.json").write_bytes(before)
    document["packages"] = [
        p for p in document["packages"] if p not in matches
    ]
    pending = settings / (".partsmith-packages-" + uuid4().hex + ".tmp")
    pending.write_text(json.dumps(document, indent=4) + "\n", "utf-8")
    moved = []
    try:
        require_closed_kicad()
        if registry.read_bytes() != before:
            raise RuntimeError("KiCad package registry changed during staging")
        for target, name in ((plugin, "plugin"), (resources, "resources")):
            retained = backup / name
            require_owned_path(target, third_party)
            target.replace(retained)
            moved.append((target, retained))
        pending.replace(registry)
    except Exception:
        for target, retained in reversed(moved):
            retained.replace(target)
        if pending.exists():
            pending.replace(backup / "uncommitted-packages.json")
        raise
    return {"status": "UNINSTALLED", "backup": str(backup)}


def main(argv: list[str]) -> int:
    """@brief Runs an explicit install, upgrade or uninstall operation.
    @param argv Closed installer options excluding the native launcher.
    @return Zero after a verified commit, two on a rejected operation.
    @details Requires no customer Python preparation; callable from a spare
    extracted bundle, so the installed runtime is never its own updater.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install-archive", type=Path)
    action.add_argument("--uninstall", action="store_true")
    parser.add_argument("--settings-dir", type=Path)
    parser.add_argument("--third-party-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        require_closed_kicad()
        settings, third_party = installation_paths(
            args.settings_dir, args.third_party_dir
        )
        running = Path(__file__).resolve()
        if running.is_relative_to(third_party):
            raise ValueError("Run installation from an extracted spare bundle")
        if args.uninstall:
            report = uninstall(settings, third_party)
        else:
            report = install_archive(
                args.install_archive.resolve(),
                settings,
                third_party,
                before_publish=require_closed_kicad,
            )
    except Exception as error:
        code = (
            str(error) if isinstance(error, ValueError) else "INSTALL_FAILED"
        )
        report = {"status": "FAILED", "code": code}
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report["status"] != "FAILED" else 2
