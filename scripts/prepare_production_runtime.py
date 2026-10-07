"""@file prepare_production_runtime.py
@brief Assembles the locked self-contained Windows runtime for PCM builds.
@details Producer Python and zstandard are build tools, not customer steps.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.supply import prepare_supply  # noqa: E402


def main() -> int:
    """@brief Fetches pinned source artifacts into a new runtime directory.
    @return Zero after all member hashes match the committed lock.
    @details Failed preparation exits nonzero and is never accepted by build.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".tools/runtime")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = prepare_supply(
        ROOT / "resources/runtime/production-lock.json",
        args.cache,
        args.output,
    )
    print(f"Verified {len(lock['files'])} runtime input files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
