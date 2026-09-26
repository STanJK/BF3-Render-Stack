#!/usr/bin/env python3
"""
BF3 lens-flare replay reconstructed from observed GPU behavior.

Reference capture:
  1280x720 FP16 HDR target
  Sun center ~= (843.22, 266.72) px
  Five draws:
    1. star flare
    2. rainbow ring
    3. lens-dirt modulation
    4. warm optical ghost
    5. blue mirrored ghost

This is an independently written behavioral reimplementation. It expects the
six locally extracted flare textures to be supplied at runtime.

Dependencies:
    py -m pip install numpy pillow opencv-python
"""

import os
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import argparse
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

STAR_INTENSITY  = 0.06178417
RING_INTENSITY  = 0.01170392
DIRTY_INTENSITY = 0.24746911
WARM_INTENSITY  = 0.17841211
BLUE_INTENSITY  = 0.07087997

STAR_SIZE_720  = 765.17
RING_SIZE_720  = 1102.66
DIRTY_SIZE_720 = 746.21
WARM_SIZE_720  = 15360.0
BLUE_SIZE_720  = 921.60

CAPTURE_SUN_UV = (843.22 / 1280.0, 266.72 / 720.0)
BC1_PNG_GPU_GAIN = 1.0112


def srgb_to_linear(x):
    x = np.asarray(x, dtype=np.float32)
    return np.where(
        x <= 0.04045,
        x / 12.92,
        ((x + 0.055) / 1.055) ** 2.4,
    )


def load_rgb_srgb(path):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return srgb_to_linear(im)


def load_exr(path):
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise RuntimeError(f"Could not read EXR: {path}")
    if im.ndim != 3 or im.shape[2] < 3:
        raise RuntimeError(f"Expected RGB/RGBA EXR, got {im.shape}")

    if im.shape[2] == 3:
        rgb = im[..., ::-1].astype(np.float32)
        alpha = np.ones((*rgb.shape[:2], 1), dtype=np.float32)
    else:
        rgb = im[..., [2, 1, 0]].astype(np.float32)
        alpha = im[..., 3:4].astype(np.float32)

    return rgb, alpha


def save_exr(path, rgb, alpha):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.concatenate([rgb, alpha], axis=2).astype(np.float32)
    bgra = rgba[..., [2, 1, 0, 3]]
    if not cv2.imwrite(str(path), bgra):
        raise RuntimeError(f"Could not write EXR: {path}")


def sample_linear(img, u, v, address="clamp"):
    """D3D-style normalized bilinear sampling."""
    h, w = img.shape[:2]
    tx = u * w - 0.5
    ty = v * h - 0.5

    x0 = np.floor(tx).astype(np.int32)
    y0 = np.floor(ty).astype(np.int32)
    fx = tx - x0
    fy = ty - y0
    x1 = x0 + 1
    y1 = y0 + 1

    def fetch(x, y):
        if address == "wrap":
            return img[y % h, x % w]

        if address == "clamp":
            return img[np.clip(y, 0, h - 1), np.clip(x, 0, w - 1)]

        if address == "border":
            valid = (x >= 0) & (x < w) & (y >= 0) & (y < h)
            out = img[np.clip(y, 0, h - 1), np.clip(x, 0, w - 1)].copy()
            out[~valid] = 0.0
            return out

        raise ValueError(address)

    c00 = fetch(x0, y0)
    c10 = fetch(x1, y0)
    c01 = fetch(x0, y1)
    c11 = fetch(x1, y1)

    c0 = c00 * (1.0 - fx)[..., None] + c10 * fx[..., None]
    c1 = c01 * (1.0 - fx)[..., None] + c11 * fx[..., None]
    return c0 * (1.0 - fy)[..., None] + c1 * fy[..., None]


def rotate_uv(u, v, angle):
    uc = u - 0.5
    vc = v - 0.5
    s = np.sin(angle)
    c = np.cos(angle)
    return (
        uc * c - vc * s + 0.5,
        vc * c + uc * s + 0.5,
    )


def sprite_uv(width, height, center_uv, size_px):
    yy, xx = np.mgrid[0:height, 0:width]
    cx = center_uv[0] * width
    cy = center_uv[1] * height

    left = cx - size_px * 0.5
    top = cy - size_px * 0.5

    u = ((xx + 0.5) - left) / size_px
    v = ((yy + 0.5) - top) / size_px

    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
    return u, v, inside


def quantize_fp16(x, enabled):
    if not enabled:
        return x
    return x.astype(np.float16).astype(np.float32)


def build_layers(width, height, sun_uv, decode_gain, asset_dir):
    asset_dir = Path(asset_dir)

    star = load_rgb_srgb(asset_dir / "star.png")
    ring = load_rgb_srgb(asset_dir / "ring.png")
    dirty_source = load_rgb_srgb(asset_dir / "dirty_source.png")
    lens_dirt = load_rgb_srgb(asset_dir / "lens_dirt.png")
    warm = load_rgb_srgb(asset_dir / "warm_ghost.png")
    blue = load_rgb_srgb(asset_dir / "blue_ghost.png")

    scale = height / 720.0

    ndc_x = 2.0 * sun_uv[0] - 1.0
    ndc_y = 1.0 - 2.0 * sun_uv[1]
    center_dist = float(np.sqrt(ndc_x * ndc_x + ndc_y * ndc_y))

    # Star
    u, v, inside = sprite_uv(width, height, sun_uv, STAR_SIZE_720 * scale)
    u1, v1 = rotate_uv(u, v, 0.4 * center_dist)
    u2, v2 = rotate_uv(u, v, 1.2 * center_dist)

    s1 = sample_linear(star, u1, v1, "clamp")
    s2 = sample_linear(star, u2, v2, "clamp")

    star_layer = (
        s1 * np.array([12.000, 3.442, 0.079], dtype=np.float32)
        + s2 * np.array([11.299, 12.000, 7.828], dtype=np.float32)
    )
    star_layer *= STAR_INTENSITY * decode_gain
    star_layer *= inside[..., None]

    # Rainbow ring
    u, v, inside = sprite_uv(width, height, sun_uv, RING_SIZE_720 * scale)
    u1, v1 = rotate_uv(u, v, -2.0 * center_dist)
    u2, v2 = rotate_uv(u, v, +2.0 * center_dist)

    r1 = sample_linear(ring, u1, v1, "clamp")
    r2 = sample_linear(ring, u2, v2, "border")

    ring_layer = r1 + r2
    ring_layer *= np.array([3.000, 2.550, 1.977], dtype=np.float32)
    ring_layer *= RING_INTENSITY * decode_gain
    ring_layer *= inside[..., None]

    # Screen-space lens dirt
    u, v, inside = sprite_uv(width, height, sun_uv, DIRTY_SIZE_720 * scale)
    source = sample_linear(dirty_source, u, v, "clamp")
    lum = (
        source[..., 0] * 0.299
        + source[..., 1] * 0.587
        + source[..., 2] * 0.114
    )

    yy, xx = np.mgrid[0:height, 0:width]
    su = (xx + 0.5) / width
    sv = (yy + 0.5) / height
    dirt = sample_linear(lens_dirt, su, sv, "wrap")

    dirty_layer = dirt * (
        lum * 30.0 * DIRTY_INTENSITY * decode_gain
    )[..., None]
    dirty_layer *= inside[..., None]

    # Warm optical ghost
    u, v, inside = sprite_uv(width, height, sun_uv, WARM_SIZE_720 * scale)
    warm_sample = sample_linear(warm, u, v, "wrap")
    warm_layer = (
        warm_sample
        * np.array([1.000, 0.922, 0.554], dtype=np.float32)
        * WARM_INTENSITY
        * decode_gain
    )
    warm_layer *= inside[..., None]

    # Blue optical ghost mirrored through the screen center
    blue_uv = (1.0 - sun_uv[0], 1.0 - sun_uv[1])
    u, v, inside = sprite_uv(width, height, blue_uv, BLUE_SIZE_720 * scale)
    blue_sample = sample_linear(blue, u, v, "wrap")
    blue_layer = (
        blue_sample
        * np.array([0.131, 0.350, 1.174], dtype=np.float32)
        * BLUE_INTENSITY
        * decode_gain
    )
    blue_layer *= inside[..., None]

    return {
        "star": star_layer.astype(np.float32),
        "ring": ring_layer.astype(np.float32),
        "dirty": dirty_layer.astype(np.float32),
        "warm": warm_layer.astype(np.float32),
        "blue": blue_layer.astype(np.float32),
        "center_dist": center_dist,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path, help="Scene-linear HDR EXR before flare")
    p.add_argument(
        "--assets-dir",
        type=Path,
        required=True,
        help="Directory containing the six locally extracted flare PNGs",
    )
    p.add_argument("-o", "--output", type=Path, default=Path("bf3_flare.exr"))
    p.add_argument(
        "--sun-uv",
        nargs=2,
        type=float,
        metavar=("X", "Y"),
        default=CAPTURE_SUN_UV,
        help="Sun position in top-left-origin normalized image coordinates",
    )
    p.add_argument(
        "--strength",
        type=float,
        default=1.0,
        help="Overall flare multiplier",
    )
    p.add_argument(
        "--decode-gain",
        type=float,
        default=BC1_PNG_GPU_GAIN,
        help="Offline BC1-PNG sampling compensation",
    )
    p.add_argument(
        "--no-half-quantize",
        action="store_true",
        help="Do not emulate FP16 target store after each draw",
    )
    p.add_argument(
        "--layers-dir",
        type=Path,
        help="Optional directory to write each HDR flare layer as EXR",
    )

    args = p.parse_args()

    rgb, alpha = load_exr(args.input)
    h, w = rgb.shape[:2]

    layers = build_layers(
        w,
        h,
        tuple(args.sun_uv),
        args.decode_gain,
        args.assets_dir,
    )

    half = not args.no_half_quantize
    out = rgb.copy()

    for name in ("star", "ring", "dirty", "warm", "blue"):
        out = quantize_fp16(out + layers[name] * args.strength, half)

    save_exr(args.output, out, alpha)

    if args.layers_dir:
        args.layers_dir.mkdir(parents=True, exist_ok=True)
        zero_alpha = np.zeros((h, w, 1), dtype=np.float32)
        for name in ("star", "ring", "dirty", "warm", "blue"):
            save_exr(
                args.layers_dir / f"{name}.exr",
                layers[name],
                zero_alpha,
            )

    print(f"Sun UV: {tuple(args.sun_uv)}")
    print(
        "external_lensFlareCenterDist ~= "
        f"{layers['center_dist']:.9f}"
    )
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
