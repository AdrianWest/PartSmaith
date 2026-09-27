"""

@package scripts.verify_phase2_manifest
@brief Verify the current Phase 2 manifest against exact repository
file bytes.
@details Provides the module implementation and public interfaces.
"""

import argparse
import json
import subprocess
from hashlib import sha256
from pathlib import Path


def _git_blob_bytes(root: Path, name: str) -> bytes:
    """

    @brief Read a tracked file's committed HEAD content, bypassing any
    local working-tree line-ending conversion.
    @param root The root argument.
    @param name The name argument.
    @return The bytes result.
    @details Runs `git show HEAD:<name>` and returns raw stdout bytes;
    raises subprocess.CalledProcessError if the path is not tracked at
    HEAD.

    """
    result = subprocess.run(
        ["git", "show", f"HEAD:{name}"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return result.stdout


def _read_bytes(root: Path, name: str, source: str) -> bytes:
    """

    @brief Read the bytes to hash for a manifest entry from the
    requested source.
    @param root The root argument.
    @param name The name argument.
    @param source Either "disk" (working-tree file) or "git" (committed
    HEAD blob).
    @return The bytes result.
    @details "disk" bytes can differ from "git" bytes when a local git
    configuration (e.g. core.autocrlf=true) rewrites line endings on
    checkout; use "git" when authoring or refreshing a manifest so the
    recorded hash matches what any clone/CI checkout will produce.

    """
    if source == "git":
        return _git_blob_bytes(root, name)
    return (root / name).read_bytes()


def verify(manifest_path: Path, root: Path, source: str = "disk") -> list[str]:
    """

    @brief Return missing/changed inputs; wheel output is separately
    recorded.
    @param manifest_path The manifest_path argument.
    @param root The root argument.
    @param source Either "disk" or "git"; see `_read_bytes`.
    @return The list[str] result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for name, expected in manifest["sha256"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append(f"Outside repository: {name}")
            continue
        if not path.is_file():
            errors.append(f"Missing: {name}")
            continue
        try:
            actual = sha256(_read_bytes(root, name, source)).hexdigest()
        except subprocess.CalledProcessError:
            errors.append(f"Not tracked at HEAD: {name}")
            continue
        if actual != expected:
            errors.append(f"Hash mismatch: {name}")
    return errors


def update(manifest_path: Path, root: Path, source: str) -> None:
    """

    @brief Recompute and rewrite every hash in a manifest's sha256 map.
    @param manifest_path The manifest_path argument.
    @param root The root argument.
    @param source Either "disk" or "git"; see `_read_bytes`.
    @return None.
    @details Preserves key order and all other manifest fields; only
    the sha256 map values are replaced.

    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in manifest["sha256"]:
        manifest["sha256"][name] = sha256(
            _read_bytes(root, name, source)
        ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    """

    @brief Implements the main operation.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "docs/gates/phase-2-v0.9.6-artifacts.json",
    )
    parser.add_argument(
        "--source",
        choices=["disk", "git"],
        default="disk",
        help=(
            "'disk' reads working-tree bytes (what CI checks); 'git' "
            "reads the committed HEAD blob, immune to local line-ending "
            "conversion. Use --source git with --update when authoring "
            "a manifest."
        ),
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rewrite the manifest's sha256 map from --source instead of "
        "verifying.",
    )
    args = parser.parse_args()
    if args.update:
        update(args.manifest, root, args.source)
        print(f"Updated {args.manifest} from source={args.source}")
        return 0
    errors = verify(args.manifest, root, args.source)
    if errors:
        print("\n".join(errors))
        return 1
    print("PASS: all recorded repository input hashes match exact file bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
