"""Install launch-only plugin into an explicitly selected KiCad plugin path."""

import argparse
import json
import shutil
import sys
from importlib.resources import as_file, files
from pathlib import Path


def install(plugin_directory, python):
    """Copy plugin and non-secret runtime configuration, never credentials."""
    target = Path(plugin_directory).resolve() / "partsmith_setup"
    python = Path(python).resolve()
    if not python.is_file():
        raise ValueError("Python executable does not exist")
    source = files("partsmith.gui").joinpath("kicad_plugin")
    if not source.is_dir():
        source = (
            Path(__file__).resolve().parents[3]
            / "integrations"
            / "kicad"
            / "partsmith_setup"
        )
        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    else:
        with as_file(source) as path:
            shutil.copytree(
                path,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    (target / "launcher.json").write_text(
        json.dumps({"python": str(python)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-dir", required=True, type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use the PartSmith Python 3.12 runtime")
    import wx  # noqa: F401

    from partsmith.gui.app import banner_bytes

    banner_bytes()
    print(install(args.plugin_dir, sys.executable))


if __name__ == "__main__":
    main()
