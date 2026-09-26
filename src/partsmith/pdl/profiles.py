"""Pinned release-profile loading and content hashing."""

import re
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.pdl.errors import fail

_REQUIRED_FIELD_TYPES = {
    "schema_version": str,
    "id": str,
    "version": str,
    "bootstrap_variant": str,
    "production_variants": list,
    "required_model_accuracy": str,
    "required_artifacts": list,
    "kicad_target": str,
}
_SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def load_release_profile(
    profile_id: str,
    version: str,
    *,
    root: str | Path | None = None,
) -> dict:
    """Load one exact release profile without implicit version selection."""
    if not _SAFE_IDENTIFIER.fullmatch(profile_id):
        fail(
            "/release_profile/id",
            "PDL_PROFILE_ID",
            "Invalid release-profile identifier",
        )
    if not _SAFE_IDENTIFIER.fullmatch(version):
        fail(
            "/release_profile/version",
            "PDL_PROFILE_VERSION",
            "Invalid release-profile version",
        )
    name = f"{profile_id}@{version}.json"
    if root is None:
        resource = files(__package__).joinpath("release-profiles", name)
        if not resource.is_file():
            resource = (
                Path(__file__).resolve().parents[3]
                / "pdl"
                / "release-profiles"
                / name
            )
    else:
        resource = Path(root) / name
    if not resource.is_file():
        fail(
            "/release_profile",
            "PDL_PROFILE_NOT_FOUND",
            "Release profile was not found",
        )
    profile = parse_json(resource.read_bytes())
    if profile.get("id") != profile_id or profile.get("version") != version:
        fail(
            "/release_profile",
            "PDL_PROFILE",
            "Release profile identity does not match its filename",
        )
    for key, kind in _REQUIRED_FIELD_TYPES.items():
        if not isinstance(profile.get(key), kind):
            fail(
                "/release_profile",
                "PDL_PROFILE",
                f"Release profile is missing required field '{key}'",
            )
    return profile


def release_profile_hash(profile: dict) -> str:
    """Hash canonical release-profile content."""
    return sha256(canonical_json(profile)).hexdigest()
