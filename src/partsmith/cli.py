"""The Phase 0 PartSmith command-line interface."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from partsmith import __version__


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic runtime diagnostic result."""

    name: str
    status: str
    detail: str


def collect_diagnostics() -> list[Diagnostic]:
    """Collect Phase 0 diagnostics without external dependencies."""
    checks = [
        ("python", sys.version_info >= (3, 11), platform.python_version()),
        ("package", bool(__version__), f"partsmith {__version__}"),
        ("cli", True, "command interface available"),
    ]
    return [
        Diagnostic(name, "PASS" if passed else "FAIL", detail)
        for name, passed, detail in checks
    ]


def _command_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _command_doctor(args: argparse.Namespace) -> int:
    diagnostics = collect_diagnostics()
    if args.json:
        payload = [asdict(item) for item in diagnostics]
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    else:
        print(f"PartSmith {__version__} diagnostics")
        for item in diagnostics:
            print(f"{item.status:4} {item.name}: {item.detail}")
    return 0 if all(item.status == "PASS" for item in diagnostics) else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="partsmith", description="PartSmith component builder"
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    version_parser = commands.add_parser(
        "version", help="print the application version"
    )
    version_parser.set_defaults(handler=_command_version)

    doctor_parser = commands.add_parser(
        "doctor", help="check the Phase 0 runtime foundation"
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="emit diagnostics as canonical JSON",
    )
    doctor_parser.set_defaults(handler=_command_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PartSmith CLI and return its process status."""
    args = build_parser().parse_args(argv)
    return args.handler(args)
