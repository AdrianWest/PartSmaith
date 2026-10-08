"""@package partsmith.external_dependencies
@brief Checks manually installed OCR prerequisites before desktop startup.
@details Checks only Tesseract and its language data. Python dependencies
remain owned by KiCad's requirements installer; KiCad itself is not probed.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

TESSERACT_URL = "https://github.com/UB-Mannheim/tesseract/wiki"
LANGUAGES = {
    "eng": "English",
    "deu": "German",
    "chi_sim": "Simplified Chinese",
}


@dataclass(frozen=True)
class ExternalDependencyIssue:
    """@brief Describes one actionable manual prerequisite problem.
    @details Text and URLs are application-owned, never native error output.
    """

    code: str
    name: str
    reason: str
    instructions: str
    url: str


def find_tesseract(executable: str | Path | None = None) -> str | None:
    """@brief Resolves the OCR executable using the extraction adapter policy.
    @param executable Optional explicit executable selected by a caller.
    @return Selected executable string, or None when it cannot be found.
    @details Explicit selection and PARTSMITH_TESSERACT precede PATH and the
    standard Windows location. A broken override is never silently replaced.
    """
    selected = (
        executable
        or os.environ.get("PARTSMITH_TESSERACT")
        or shutil.which("tesseract")
    )
    if selected:
        return str(selected)
    candidate = (
        Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        / "Tesseract-OCR/tesseract.exe"
    )
    return str(candidate) if candidate.is_file() else None


def _probe(executable: str, argument: str) -> str:
    """@brief Runs a bounded noninteractive OCR installation probe.
    @param executable Selected Tesseract executable or command name.
    @param argument Version or installed-language listing option.
    @return Standard output decoded as UTF-8.
    @details Inherits TESSDATA_PREFIX exactly as extraction does. No shell,
    browser, download, image recognition or package installer is started.
    """
    result = subprocess.run(
        [executable, argument],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.stdout


def _engine_issue(code: str, reason: str) -> ExternalDependencyIssue:
    """@brief Builds a fixed, actionable Tesseract installation error.
    @param code Stable diagnostic reason code.
    @param reason Application-owned explanation without exception content.
    @return Manual-install issue linked to the Windows installer provider.
    @details All required languages are named when the engine is unavailable.
    """
    return ExternalDependencyIssue(
        code,
        "Tesseract OCR 5",
        reason,
        "Install Tesseract 5 for Windows (64-bit), including English, German "
        "and Simplified Chinese language data. If it is already installed, "
        "correct PARTSMITH_TESSERACT or PATH, then restart PartSmith.",
        TESSERACT_URL,
    )


def check_external_dependencies() -> tuple[ExternalDependencyIssue, ...]:
    """@brief Checks only prerequisites requiring installation outside Python.
    @return Missing or unusable OCR engine/language issues; empty when ready.
    @details Does not check KiCad, Python packages, CAD DLLs or credentials.
    Failures and timeouts produce safe errors rather than native output.
    """
    executable = find_tesseract()
    if executable is None:
        return (_engine_issue("TESSERACT_MISSING", "Not installed."),)
    try:
        version = _probe(executable, "--version")
        if not re.match(r"^tesseract\s+v?5(?:\.|\s|$)", version.strip()):
            return (
                _engine_issue(
                    "TESSERACT_VERSION_UNSUPPORTED",
                    "The installed OCR engine is not Tesseract 5.",
                ),
            )
        available = {
            line.strip()
            for line in _probe(executable, "--list-langs").splitlines()[1:]
        }
    except (OSError, subprocess.SubprocessError):
        return (
            _engine_issue(
                "TESSERACT_UNAVAILABLE",
                "The OCR installation failed its check or did not respond.",
            ),
        )
    return tuple(
        ExternalDependencyIssue(
            "OCR_LANGUAGE_MISSING_" + code.upper(),
            label + " OCR language data (" + code + ")",
            "Not available in Tesseract's active language-data folder.",
            "Add this language using the Tesseract installer, or download "
            + code
            + ".traineddata into Tesseract's tessdata folder. If you use "
            "TESSDATA_PREFIX, check that folder instead. Restart PartSmith "
            "after installing the data.",
            "https://github.com/tesseract-ocr/tessdata_fast/blob/4.1.0/"
            + code
            + ".traineddata",
        )
        for code, label in LANGUAGES.items()
        if code not in available
    )
