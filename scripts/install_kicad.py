"""@file install_kicad.py
@brief Builds and installs the development PCM package with KiCad closed.
@details Preserves other packages, runtime environments and rollback backups.
"""

import argparse
import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

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


from partsmith.pcm.installation import (  # noqa: E402,F401
    install_archive,
    require_owned_path,
)


def main() -> int:
    """@brief Builds the current development package and installs it locally.
    @return Zero on installation or dry-run success; one on a rejected install.
    @details Requires Windows Python 3.12 and preserves existing preferences.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--settings-dir", type=Path)
    parser.add_argument("--third-party-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-pause", action="store_true")
    args = parser.parse_args()
    try:
        if os.name != "nt" or sys.version_info[:2] != (3, 12):
            raise RuntimeError(
                "Use the Windows Python 3.12 project environment"
            )
        settings, third_party = installation_paths(
            args.settings_dir, args.third_party_dir
        )
        require_closed_kicad()
        common = json.loads((settings / "kicad_common.json").read_bytes())
        interpreter = (common.get("api") or {}).get("interpreter_path")
        if not interpreter or not Path(interpreter).is_file():
            raise RuntimeError("Configure KiCad's external Python 3.12 first")
        result = subprocess.run(
            [
                interpreter,
                "-I",
                "-c",
                "import sys; "
                "raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)",
            ],
            check=False,
            capture_output=True,
            timeout=15,
        )
        if result.returncode:
            raise RuntimeError("KiCad's selected Python must be version 3.12")
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
        report = install_archive(
            archive.resolve(),
            settings,
            third_party,
            before_publish=require_closed_kicad,
        )
        print("Installed PartSmith " + report["version"])
        print("Backup: " + report["backup"])
        print("Open KiCad and wait for its plugin runtime preparation.")
        return 0
    except Exception as error:
        print("PartSmith installation failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
