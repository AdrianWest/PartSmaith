"""

@package src.partsmith.pdl.loader
@brief Versioned PDL entry discovery and loading.
@details Provides the module implementation and public interfaces.
"""

import re
from importlib.resources import files
from pathlib import Path

from partsmith.pdl.errors import fail
from partsmith.pdl.model import PDL


def _entry_root(root: str | Path | None = None):
    """

    @brief Implements the _entry_root operation.
    @param root The root argument.
    @return The callable result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    if root is not None:
        return Path(root)
    packaged = files(__package__).joinpath("entries")
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[3] / "pdl" / "entries"


def load_pdl(
    pdl_id: str,
    revision: str | None = None,
    *,
    root: str | Path | None = None,
) -> PDL:
    """

    @brief Load an exact PDL revision, or the sole available revision.
    @param pdl_id The pdl_id argument.
    @param revision The revision argument.
    @param root The root argument.
    @return The PDL result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", pdl_id):
        fail("/id", "PDL_ID", "Invalid PDL identifier")
    entry_root = _entry_root(root)
    candidates = sorted(entry_root.glob(f"{pdl_id}@*.json"))
    if revision is not None:
        candidates = [
            path for path in candidates if path.stem == f"{pdl_id}@{revision}"
        ]
    if not candidates:
        fail("/id", "PDL_NOT_FOUND", "PDL entry was not found")
    if len(candidates) != 1:
        fail(
            "/revision",
            "PDL_REVISION_REQUIRED",
            "Multiple revisions exist; select one explicitly",
        )
    result = PDL.from_file(candidates[0])
    if result.data["id"] != pdl_id:
        fail("/id", "PDL_ID", "PDL filename and content disagree")
    filename_revision = candidates[0].stem.removeprefix(f"{pdl_id}@")
    if result.data["revision"] != filename_revision:
        fail(
            "/revision",
            "PDL_REVISION",
            "PDL filename and revision disagree",
        )
    return result


def list_pdls(
    *, root: str | Path | None = None
) -> tuple[tuple[str, str], ...]:
    """

    @brief List validated PDL identity/revision pairs deterministically.
    @param root The root argument.
    @return The tuple[tuple[str, str], ...] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    entries = []
    for path in sorted(_entry_root(root).glob("*.json")):
        pdl = PDL.from_file(path)
        pdl_id = pdl.data["id"]
        revision = pdl.data["revision"]
        if path.stem != f"{pdl_id}@{revision}":
            fail(
                "/id",
                "PDL_ID",
                "PDL filename and content disagree",
            )
        entries.append((pdl_id, revision))
    return tuple(entries)


def resolve_pdl(
    family: str,
    variant: str,
    terminal_numbers: set[str] | frozenset[str],
    *,
    root: str | Path | None = None,
) -> PDL:
    """

    @brief Resolve one exact validated package; never use similarity
    scoring.
    @param family The family argument.
    @param variant The variant argument.
    @param terminal_numbers The terminal_numbers argument.
    @param root The root argument.
    @return The PDL result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    matches = []
    for pdl_id, revision in list_pdls(root=root):
        candidate = load_pdl(pdl_id, revision, root=root)
        data = candidate.data
        numbers = {item["number"] for item in data["topology"]["terminals"]}
        if (
            data["identity"]["family"] == family
            and data["identity"]["variant"] == variant
            and numbers == set(terminal_numbers)
        ):
            matches.append(candidate)
    if not matches:
        fail("/package", "PDL_NOT_FOUND", "No exact PDL candidate matched")
    if len(matches) != 1:
        fail(
            "/package",
            "PDL_AMBIGUOUS",
            "Multiple exact PDL candidates matched",
        )
    return matches[0]
