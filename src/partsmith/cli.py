"""

@package src.partsmith.cli
@brief The Phase 0 PartSmith command-line interface.
@details Provides the module implementation and public interfaces.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from partsmith import __version__
from partsmith.kicad import KiCadCompatibilityError, discover_kicad
from partsmith.pdl import PDLValidationError, list_pdls, load_pdl


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic runtime diagnostic result."""

    name: str
    status: str
    detail: str


def is_supported_python(version: tuple[int, int]) -> bool:
    """

    @brief Return whether a Python major/minor version is supported.
    @param version The version argument.
    @return The bool result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    return (3, 12) <= version < (3, 13)


def collect_diagnostics() -> list[Diagnostic]:
    """

    @brief Collect Phase 0 diagnostics without external dependencies.
    @return The list[Diagnostic] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    checks = [
        (
            "python",
            is_supported_python(sys.version_info[:2]),
            platform.python_version(),
        ),
        ("package", bool(__version__), f"partsmith {__version__}"),
        ("cli", True, "command interface available"),
    ]
    try:
        runtime = discover_kicad()
    except KiCadCompatibilityError as error:
        checks.append(("kicad", False, str(error)))
    else:
        checks.append(
            (
                "kicad",
                True,
                f"{runtime.version} at {runtime.executable}",
            )
        )
    return [
        Diagnostic(name, "PASS" if passed else "FAIL", detail)
        for name, passed, detail in checks
    ]


def _command_version(_: argparse.Namespace) -> int:
    """

    @brief Implements the _command_version operation.
    @param _ The _ argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    print(__version__)
    return 0


def _command_doctor(args: argparse.Namespace) -> int:
    """

    @brief Implements the _command_doctor operation.
    @param args The args argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    diagnostics = collect_diagnostics()
    if args.json:
        payload = [asdict(item) for item in diagnostics]
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    else:
        print(f"PartSmith {__version__} diagnostics")
        for item in diagnostics:
            print(f"{item.status:4} {item.name}: {item.detail}")
    return 0 if all(item.status == "PASS" for item in diagnostics) else 1


def _command_pdl_list(_: argparse.Namespace) -> int:
    """

    @brief Implements the _command_pdl_list operation.
    @param _ The _ argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    for pdl_id, revision in list_pdls():
        print(f"{pdl_id}@{revision}")
    return 0


def _load_cli_pdl(args: argparse.Namespace):
    """

    @brief Implements the _load_cli_pdl operation.
    @param args The args argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    try:
        return load_pdl(args.pdl_id, args.revision)
    except PDLValidationError as error:
        print(str(error), file=sys.stderr)
        return None


def _command_pdl_inspect(args: argparse.Namespace) -> int:
    """

    @brief Implements the _command_pdl_inspect operation.
    @param args The args argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    pdl = _load_cli_pdl(args)
    if pdl is None:
        return 2
    print(pdl.canonical_bytes.decode("utf-8"))
    return 0


def _command_pdl_validate(args: argparse.Namespace) -> int:
    """

    @brief Implements the _command_pdl_validate operation.
    @param args The args argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    pdl = _load_cli_pdl(args)
    if pdl is None:
        return 2
    data = pdl.data
    print(f"PASS {data['id']}@{data['revision']} {pdl.sha256}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """

    @brief Build the command-line parser.
    @return The argparse.ArgumentParser result.
    @details Implements the documented behavior without changing the
    public contract.

    """
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

    pdl_parser = commands.add_parser("pdl", help="inspect package definitions")
    pdl_commands = pdl_parser.add_subparsers(dest="pdl_command", required=True)
    pdl_commands.add_parser(
        "list", help="list installed PDL entries"
    ).set_defaults(handler=_command_pdl_list)
    for name, handler in (
        ("inspect", _command_pdl_inspect),
        ("validate", _command_pdl_validate),
    ):
        command = pdl_commands.add_parser(name, help=f"{name} one PDL entry")
        command.add_argument("pdl_id")
        command.add_argument("--revision")
        command.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """

    @brief Run the PartSmith CLI and return its process status.
    @param argv The argv argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    args = build_parser().parse_args(argv)
    return args.handler(args)
