"""@file build_production_pcm.py
@brief Builds the online PCM candidate with KiCad-managed dependencies.
@details Ships source and requirements; KiCad downloads binary wheels.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.package import VERSION, build_pcm  # noqa: E402


def main() -> int:
    """@brief Builds a deterministic archive and writes its exact receipt.
    @return Zero after complete archive verification.
    @details The receipt is written only after the final ZIP is accepted.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default=VERSION)
    args = parser.parse_args()
    receipt = build_pcm(ROOT, args.output, args.version)
    receipt_path = args.output.with_suffix(".json")
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
