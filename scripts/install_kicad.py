"""@file install_kicad.py
@brief Installs the managed-Python PCM package with KiCad closed.
@details Preserves other packages, runtime environments and rollback backups.
"""

import argparse
import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Explicit repository source takes precedence over any installed project copy.
from partsmith.pcm.package import (  # noqa: E402
    IDENTIFIER,
    VERSION,
    build_pcm,
)

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


def bundled_python() -> Path:
    """@brief Verifies Python beside the supported native KiCad executable.
    @return Absolute KiCad-bundled Python 3.11 interpreter path.
    @details Uses KiCad discovery, including PARTSMITH_KICAD_CLI for custom
    installations. Probes use disposable KiCad settings, so even CLI startup
    bookkeeping cannot change user preferences. Base Python is never modified.
    """
    from partsmith.kicad import discover_kicad

    previous_config = os.environ.get("KICAD_CONFIG_HOME")
    try:
        with TemporaryDirectory(prefix="partsmith-kicad-probe-") as temporary:
            os.environ["KICAD_CONFIG_HOME"] = temporary
            runtime = discover_kicad()
    finally:
        if previous_config is None:
            os.environ.pop("KICAD_CONFIG_HOME", None)
        else:
            os.environ["KICAD_CONFIG_HOME"] = previous_config
    if runtime.version != "10.0.6":
        raise RuntimeError("KiCad 10.0.6 is required")
    interpreter = runtime.executable.with_name("python.exe").resolve()
    result = subprocess.run(
        [
            str(interpreter),
            "-I",
            "-c",
            "import platform, sys; "
            "raise SystemExit(0 if sys.version_info[:2] == (3,11) "
            "and platform.machine() == 'AMD64' else 1)",
        ],
        check=False,
        capture_output=True,
        timeout=15,
    )
    if result.returncode:
        raise RuntimeError("KiCad must supply Windows AMD64 Python 3.11")
    return interpreter


from partsmith.pcm.installation import (  # noqa: E402,F401
    install_archive,
    require_owned_path,
    uninstall,
)


def main() -> int:
    """@brief Installs or removes the current managed-Python package locally.
    @return Zero on installation or dry-run success; one on a rejected install.
    @details The producer uses Python 3.11 or 3.12. Installation selects
    KiCad's bundled 3.11 for IPC with a transactional preference backup.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--archive", type=Path)
    action.add_argument("--uninstall", action="store_true")
    parser.add_argument("--settings-dir", type=Path)
    parser.add_argument("--third-party-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-pause", action="store_true")
    args = parser.parse_args()
    try:
        if os.name != "nt" or sys.version_info[:2] not in {(3, 11), (3, 12)}:
            raise RuntimeError(
                "Use the Windows Python 3.11 or 3.12 project environment"
            )
        settings, third_party = installation_paths(
            args.settings_dir, args.third_party_dir
        )
        require_closed_kicad()
        if args.uninstall:
            if args.dry_run:
                print("Dry run: no installation files changed.")
                return 0
            report = uninstall(settings, third_party)
            print("Removed PartSmith; backup: " + str(report.get("backup")))
            return 0
        interpreter = bundled_python()
        print("KiCad IPC interpreter: " + str(interpreter))
        print("Installation selects this interpreter for KiCad Python IPC.")
        if args.dry_run:
            print("KiCad settings: " + str(settings))
            print(
                "Plugin destination: "
                + str(third_party / "plugins" / DIRECTORY)
            )
            print("Dry run: no installation files changed.")
            return 0
        archive = args.archive or ROOT / f"dist/partsmith-{VERSION}-pcm.zip"
        if args.archive is None:
            build_pcm(ROOT, archive, VERSION)
        with ZipFile(archive) as package:
            plugin = json.loads(package.read("plugins/plugin.json"))
        if plugin.get("runtime", {}).get("type") != "python":
            raise ValueError(
                "Only KiCad-managed Python packages are supported"
            )
        report = install_archive(
            archive.resolve(),
            settings,
            third_party,
            before_publish=require_closed_kicad,
            python_interpreter=interpreter,
        )
        print("Installed PartSmith " + report["version"])
        print("Backup: " + report["backup"])
        print("Open KiCad and wait for its plugin runtime preparation.")
        print(
            "For an existing Python 3.12 cache, use Recreate Plugin "
            "Environment in PCB Editor plugin preferences."
        )
        return 0
    except Exception as error:
        print("PartSmith installation failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
