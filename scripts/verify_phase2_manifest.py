"""

@package scripts.verify_phase2_manifest
@brief Verify the current Phase 2 manifest against exact repository
file bytes.
@details Provides the module implementation and public interfaces.
"""

import argparse
import json
from hashlib import sha256
from pathlib import Path


def verify(manifest_path: Path, root: Path) -> list[str]:
    """

    @brief Return missing/changed inputs; wheel output is separately
    recorded.
    @param manifest_path The manifest_path argument.
    @param root The root argument.
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
        elif not path.is_file():
            errors.append(f"Missing: {name}")
        elif sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f"Hash mismatch: {name}")
    return errors


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
    args = parser.parse_args()
    errors = verify(args.manifest, root)
    if errors:
        print("\n".join(errors))
        return 1
    print("PASS: all recorded repository input hashes match exact file bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
