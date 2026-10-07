"""@file verify_phase14_packages.py
@brief Validates the complete frozen manufacturer-backed package corpus.
@details Golden creation is an explicit maintainer operation; normal runs
compare exact released bytes and never refresh expected artifacts.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.acceptance import run_corpus  # noqa: E402


def main() -> int:
    """@brief Verifies all eight packages and persists per-variant outcomes.
    @return Zero only when the full release corpus passes.
    @details --freeze creates reviewed reference candidates, never a gate PASS.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_corpus(ROOT / "fixtures/production", freeze=args.freeze)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Validated all", len(report["variants"]), "production variants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
