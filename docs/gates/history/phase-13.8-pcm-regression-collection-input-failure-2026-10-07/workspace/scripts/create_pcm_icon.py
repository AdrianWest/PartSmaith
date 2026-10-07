"""@file create_pcm_icon.py
@brief Copies the project owner's unchanged anvil artwork into the PCM plugin.
@details Uses supplied PNG bytes and removes only owned placeholder assets.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """@brief Packages the exact 24x24 and 64x64 PartSmith anvil PNGs.
    @return Zero after copying both assets and retiring the placeholders.
    @details Performs no image conversion, scaling or generated artwork.
    """
    directory = ROOT / "integrations/kicad/partsmith_ipc/icons"
    directory.mkdir(parents=True, exist_ok=True)
    for size in (24, 64):
        name = f"PartSmith_Anvil_Icon_{size}x{size}.png"
        (directory / name).write_bytes(
            (ROOT / "resources" / name).read_bytes()
        )
    for name in ("partsmith.svg", "partsmith-24.png", "partsmith-48.png"):
        (directory / name).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
