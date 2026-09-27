#!/usr/bin/env python3
"""Validate the locally extracted BF3 reference inputs."""

from pathlib import Path
import struct
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "local_assets"
FLARE_ROOT = ASSET_ROOT / "flare"

EXPECTED_IMAGES = {
    FLARE_ROOT / "star.png": (512, 512),
    FLARE_ROOT / "ring.png": (512, 512),
    FLARE_ROOT / "dirty_source.png": (256, 256),
    FLARE_ROOT / "lens_dirt.png": (1024, 512),
    FLARE_ROOT / "warm_ghost.png": (256, 256),
    FLARE_ROOT / "blue_ghost.png": (128, 128),
    ASSET_ROOT / "filmGrainTexture.png": (512, 512),
}


def check_image(path: Path, expected):
    if not path.exists():
        print(f"[MISSING] {path.relative_to(ROOT)}")
        return False

    try:
        with Image.open(path) as im:
            size = im.size
    except Exception as exc:
        print(f"[ERROR]   {path.relative_to(ROOT)}: {exc}")
        return False

    if size != expected:
        print(
            f"[BAD]     {path.relative_to(ROOT)} "
            f"{size[0]}x{size[1]} (expected {expected[0]}x{expected[1]})"
        )
        return False

    print(f"[OK]      {path.relative_to(ROOT)} {size[0]}x{size[1]}")
    return True


def check_lut(path: Path):
    if not path.exists():
        print(f"[MISSING] {path.relative_to(ROOT)}")
        return False

    data = path.read_bytes()

    if len(data) < 128 or data[:4] != b"DDS ":
        print(f"[BAD]     {path.relative_to(ROOT)}: not a legacy DDS")
        return False

    # The public loader expects 32^3 RGBA8 after the standard 128-byte header.
    payload = len(data) - 128
    expected_payload = 32 * 32 * 32 * 4

    if payload != expected_payload:
        print(
            f"[BAD]     {path.relative_to(ROOT)}: "
            f"payload={payload} bytes, expected={expected_payload}. "
            "Check dimensions/format/header."
        )
        return False

    print(
        f"[OK]      {path.relative_to(ROOT)} "
        f"32x32x32 RGBA8 payload ({len(data)} bytes total)"
    )
    return True


def main():
    print(f"BF3 Render Stack asset check\nroot: {ROOT}\n")

    ok = True

    for path, expected in EXPECTED_IMAGES.items():
        ok = check_image(path, expected) and ok

    ok = check_lut(ASSET_ROOT / "colorGradingTexture.dds") and ok

    if ok:
        print("\nAll required reference inputs look valid.")
        return 0

    print("\nOne or more reference inputs are missing or incompatible.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
