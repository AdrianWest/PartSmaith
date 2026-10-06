"""@package partsmith.kicad.runtime
@brief Discovers and executes the mandatory native KiCad 10 CLI.
@details Compatibility validation round-trips and renders exact generated
symbol and footprint bytes with a pinned target-major KiCad runtime.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from partsmith.process import run_process

_LOG = ContextVar("partsmith_native_log", default=None)


@contextmanager
def native_output(log):
    """@brief Connects native CLI output to the current progress sink.
    @param log Incremental redacting stdout/stderr progress callback.
    @return Context-manager iterator.
    @details Scope is process/thread-local and cannot affect other sessions.
    """
    token = _LOG.set(log)
    try:
        yield
    finally:
        _LOG.reset(token)


class KiCadCompatibilityError(RuntimeError):
    """@brief Reports missing or failed native KiCad compatibility.
    @details Phase 8 treats this exception as a blocking validation failure.
    """


@dataclass(frozen=True)
class KiCadRuntime:
    """@brief Identifies one verified native KiCad CLI runtime.
    @details The executable path is audit metadata; version affects validation.
    """

    executable: Path
    version: str
    major_version: int
    platform: str


@dataclass(frozen=True)
class NativeKiCadValidation:
    """@brief Records deterministic outputs from native KiCad validation.
    @details Output hashes prove native parse, round-trip, and render success.
    """

    runtime: KiCadRuntime
    output_hashes: tuple[str, ...]
    operations: tuple[str, ...]
    previews: tuple[tuple[str, bytes], ...] = ()


def _run(
    executable: Path,
    arguments: tuple[str, ...],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """@brief Runs one bounded native KiCad CLI operation.
    @param executable Verified KiCad CLI executable.
    @param arguments Command arguments excluding the executable.
    @param cwd Optional operation working directory.
    @return Completed native process result.
    @details Nonzero exits and timeouts become explicit compatibility errors.
    """
    try:
        if _LOG.get() is not None:
            result = run_process(
                [str(executable), *arguments],
                log=_LOG.get(),
                cwd=cwd,
                timeout=120,
            )
        else:
            result = subprocess.run(
                [str(executable), *arguments],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise KiCadCompatibilityError(
            f"KiCad CLI operation failed to execute: {arguments[0]}"
        ) from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise KiCadCompatibilityError(
            f"KiCad CLI operation failed ({result.returncode}): {detail}"
        )
    return result


def _candidate_paths() -> tuple[Path, ...]:
    """@brief Returns ordered native KiCad CLI discovery candidates.
    @return Candidate executable paths without existence guarantees.
    @details An explicit environment override precedes PATH and standard paths.
    """
    candidates: list[Path] = []
    override = os.environ.get("PARTSMITH_KICAD_CLI")
    if override:
        candidates.append(Path(override))
    discovered = shutil.which("kicad-cli")
    if discovered:
        candidates.append(Path(discovered))
    if os.name == "nt":
        program_files = Path(
            os.environ.get("ProgramFiles", r"C:\Program Files")
        )
        candidates.extend(
            (
                program_files / "KiCad" / "10.0" / "bin" / "kicad-cli.exe",
                program_files / "KiCad" / "10" / "bin" / "kicad-cli.exe",
            )
        )
    else:
        candidates.extend(
            (Path("/usr/bin/kicad-cli"), Path("/usr/local/bin/kicad-cli"))
        )
    return tuple(dict.fromkeys(candidates))


def discover_kicad(required_version: str = "10.0.6") -> KiCadRuntime:
    """@brief Discovers the pinned native KiCad CLI.
    @param required_version Required exact KiCad version.
    @return Verified runtime identity.
    @details Missing or wrong-version runtimes fail closed for Phase 8.
    """
    required_major = int(required_version.split(".", maxsplit=1)[0])
    for candidate in _candidate_paths():
        if not candidate.is_file():
            continue
        result = _run(candidate, ("version",))
        version = result.stdout.strip().splitlines()[0]
        match = re.match(r"^(\d+)\.", version)
        if match is None:
            continue
        major = int(match.group(1))
        if major != required_major or version != required_version:
            continue
        return KiCadRuntime(
            executable=candidate.resolve(),
            version=version,
            major_version=major,
            platform=platform.platform(),
        )
    raise KiCadCompatibilityError(
        f"KiCad CLI version {required_version} is required"
    )


def _write(path: Path, content: bytes) -> None:
    """@brief Writes exact validation input bytes.
    @param path Destination file path.
    @param content Exact generated artifact bytes.
    @return None.
    @details Parent directories are created without modifying content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _output_hashes(root: Path) -> tuple[str, ...]:
    """@brief Hashes every native validation output file.
    @param root Native output root directory.
    @return Sorted output content hashes.
    @details Paths are transport metadata; exact output bytes form evidence.
    """
    if root.is_file():
        return (sha256(root.read_bytes()).hexdigest(),)
    return tuple(
        sorted(
            sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def validate_native_artifacts(
    runtime: KiCadRuntime,
    *,
    target: str,
    symbol_filename: str,
    symbol_content: bytes,
    footprint_filename: str,
    footprint_content: bytes,
    model_path: str,
    model_content: bytes,
) -> NativeKiCadValidation:
    """@brief Validates released artifacts with native target KiCad.
    @param runtime Verified native KiCad runtime.
    @param target Declared KiCad target such as `10.x`.
    @param symbol_filename Portable generated symbol filename.
    @param symbol_content Exact released symbol bytes.
    @param footprint_filename Portable generated footprint filename.
    @param footprint_content Exact finalized footprint bytes.
    @param model_path Portable model association path.
    @param model_content Exact released STEP bytes.
    @return Native validation identity and output hashes.
    @details KiCad must parse, force-round-trip, and render both library types.
    """
    required_major = int(target.split(".", maxsplit=1)[0])
    if runtime.major_version != required_major:
        raise KiCadCompatibilityError(
            "Native KiCad runtime does not match the declared target"
        )
    with TemporaryDirectory(prefix="partsmith-kicad-") as temporary:
        root = Path(temporary)
        symbol_input = root / "input" / symbol_filename
        footprint_library = root / "input.pretty"
        footprint_input = footprint_library / footprint_filename
        _write(symbol_input, symbol_content)
        _write(footprint_input, footprint_content)
        _write(root / model_path, model_content)
        _write(footprint_library / model_path, model_content)
        symbol_upgrade = root / "symbol-upgrade"
        symbol_render = root / "symbol-render"
        footprint_upgrade = root / "footprint-upgrade.pretty"
        footprint_render = root / "footprint-render"
        symbol_render.mkdir()
        footprint_render.mkdir()
        _run(
            runtime.executable,
            (
                "sym",
                "upgrade",
                "--force",
                str(symbol_input),
                "--output",
                str(symbol_upgrade),
            ),
            cwd=root,
        )
        _run(
            runtime.executable,
            (
                "sym",
                "export",
                "svg",
                str(symbol_input),
                "--output",
                str(symbol_render),
                "--black-and-white",
            ),
            cwd=root,
        )
        _run(
            runtime.executable,
            (
                "fp",
                "upgrade",
                "--force",
                str(footprint_library),
                "--output",
                str(footprint_upgrade),
            ),
            cwd=root,
        )
        _run(
            runtime.executable,
            (
                "fp",
                "export",
                "svg",
                str(footprint_library),
                "--output",
                str(footprint_render),
                "--black-and-white",
            ),
            cwd=root,
        )
        hashes = _output_hashes(symbol_upgrade)
        hashes += _output_hashes(symbol_render)
        hashes += _output_hashes(footprint_upgrade)
        hashes += _output_hashes(footprint_render)
        if not hashes:
            raise KiCadCompatibilityError(
                "Native KiCad validation produced no outputs"
            )
        return NativeKiCadValidation(
            runtime=runtime,
            output_hashes=tuple(sorted(hashes)),
            operations=(
                "sym-upgrade",
                "sym-export-svg",
                "fp-upgrade",
                "fp-export-svg",
            ),
            previews=tuple(
                (kind, path.read_bytes())
                for kind, directory in (
                    ("SYMBOL", symbol_render),
                    ("FOOTPRINT", footprint_render),
                )
                for path in sorted(directory.rglob("*.svg"))
            ),
        )
