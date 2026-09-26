#!/usr/bin/env python3
"""
bf3_post.py
Reconstructs the Battlefield 3 Shader 1490 final photographic pass
on a scene-linear HDR OpenEXR input.

Expected pipeline:
    scene-linear HDR input
      -> optional exposure compensation
      -> BF3 tone curve
      -> BF3 32^3 color-grading LUT
      -> BF3 vignette
      -> BF3 film-grain/dither
      -> PNG output

For a Blender workflow, feed the compositor's pre-final-post HDR EXR here.
That EXR already contains the upstream bloom approximation, so this script
does not re-add the captured BF3 tonemapBloomTexture.

Dependencies:
    pip install numpy opencv-python pillow
"""

import os
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import argparse
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

COLOR_SCALE = np.array([1.0000065565109253] * 3, dtype=np.float64)

VIGNETTE_PARAMS = np.array([1.5, 1.5, 2.0], dtype=np.float64)
VIGNETTE_COLOR = np.array([0.000, 0.007, 0.013], dtype=np.float64)
VIGNETTE_ALPHA = 0.5

FILM_GRAIN_SCALE = np.array([0.005, 0.005, 0.005], dtype=np.float64)


def load_exr_rgb(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(
            f"Could not read EXR: {path}\n"
            "If OpenCV reports OpenEXR disabled, make sure "
            "OPENCV_IO_ENABLE_OPENEXR=1 is set before importing cv2."
        )
    if img.ndim != 3 or img.shape[2] < 3:
        raise RuntimeError(f"Expected RGB/RGBA EXR, got shape {img.shape}")
    return img[..., :3][..., ::-1].astype(np.float64)


def bf3_tone_curve(x: np.ndarray) -> np.ndarray:
    x = np.maximum(x, 0.0)

    r1 = 0.985521 * x
    r2 = 0.985521 * x + 0.058662
    numerator = r1 * r2

    d1 = 0.774597 * x + 0.048281
    d2 = 0.774597 * x + 1.242710
    denominator = d1 * d2

    y = np.sqrt(np.maximum(numerator / denominator, 0.0))
    y = y * 0.96875 + 0.015625
    return y


def load_bf3_lut_dds(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if len(data) < 128 or data[:4] != b"DDS ":
        raise RuntimeError(f"{path} is not a legacy DDS file")

    payload = np.frombuffer(data[128:], dtype=np.uint8)
    expected = 32 * 32 * 32 * 4
    if payload.size < expected:
        raise RuntimeError(
            f"DDS payload too small ({payload.size} bytes, "
            f"expected at least {expected})"
        )

    lut = payload[:expected].reshape(32, 32, 32, 4)[..., :3]
    return lut.astype(np.float64) / 255.0


def sample_lut_trilinear(lut: np.ndarray, coord: np.ndarray) -> np.ndarray:
    idx = np.clip(coord * 32.0 - 0.5, 0.0, 31.0)

    x0 = np.floor(idx[..., 0]).astype(np.int16)
    y0 = np.floor(idx[..., 1]).astype(np.int16)
    z0 = np.floor(idx[..., 2]).astype(np.int16)

    x1 = np.minimum(x0 + 1, 31)
    y1 = np.minimum(y0 + 1, 31)
    z1 = np.minimum(z0 + 1, 31)

    fx = idx[..., 0] - x0
    fy = idx[..., 1] - y0
    fz = idx[..., 2] - z0

    c000 = lut[z0, y0, x0]
    c100 = lut[z0, y0, x1]
    c010 = lut[z0, y1, x0]
    c110 = lut[z0, y1, x1]
    c001 = lut[z1, y0, x0]
    c101 = lut[z1, y0, x1]
    c011 = lut[z1, y1, x0]
    c111 = lut[z1, y1, x1]

    c00 = c000 * (1 - fx)[..., None] + c100 * fx[..., None]
    c10 = c010 * (1 - fx)[..., None] + c110 * fx[..., None]
    c01 = c001 * (1 - fx)[..., None] + c101 * fx[..., None]
    c11 = c011 * (1 - fx)[..., None] + c111 * fx[..., None]

    c0 = c00 * (1 - fy)[..., None] + c10 * fy[..., None]
    c1 = c01 * (1 - fy)[..., None] + c11 * fy[..., None]

    return c0 * (1 - fz)[..., None] + c1 * fz[..., None]


def apply_vignette(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]

    u = (xx + 0.5) / w
    v = (yy + 0.5) / h

    dx = (u - 0.5) * VIGNETTE_PARAMS[0]
    dy = (v - 0.5) * VIGNETTE_PARAMS[1]

    radius2 = dx * dx + dy * dy
    q = radius2 ** VIGNETTE_PARAMS[2]
    amount = q * VIGNETTE_ALPHA

    multiplier = 1.0 + amount[..., None] * (VIGNETTE_COLOR - 1.0)
    return rgb * multiplier


def load_grain(path: Path) -> np.ndarray:
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    return rgba[..., 0].astype(np.float64) / 255.0


def apply_grain(rgb: np.ndarray, grain_tex: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    gh, gw = grain_tex.shape[:2]

    grain = grain_tex[
        np.arange(h)[:, None] % gh,
        np.arange(w)[None, :] % gw,
    ]
    grain = grain - 0.5

    return rgb + grain[..., None] * FILM_GRAIN_SCALE


def neutral_preview(scene_linear: np.ndarray) -> np.ndarray:
    x = np.maximum(scene_linear, 0.0)
    x = x / (1.0 + x)

    return np.where(
        x <= 0.0031308,
        12.92 * x,
        1.055 * np.power(x, 1 / 2.4) - 0.055,
    )


def save_png(path: Path, rgb: np.ndarray):
    arr = np.clip(
        np.rint(np.clip(rgb, 0.0, 1.0) * 255.0),
        0,
        255,
    ).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)


def process(args):
    inp = load_exr_rgb(args.input)

    x = inp * (2.0 ** args.exposure_ev) * COLOR_SCALE
    tone_lut_coord = bf3_tone_curve(x)

    if args.no_lut:
        graded = np.clip(tone_lut_coord, 0.0, 1.0)
    else:
        lut = load_bf3_lut_dds(args.lut)
        graded = sample_lut_trilinear(lut, tone_lut_coord)

    if not args.no_vignette:
        graded = apply_vignette(graded)

    if not args.no_grain:
        if args.grain is None:
            raise RuntimeError("--grain is required unless --no-grain is used")
        graded = apply_grain(graded, load_grain(args.grain))

    save_png(args.output, graded)

    if args.stages is not None:
        args.stages.mkdir(parents=True, exist_ok=True)
        save_png(
            args.stages / "00_input_neutral_preview.png",
            neutral_preview(inp),
        )
        save_png(
            args.stages / "01_bf3_tone_curve.png",
            np.clip(tone_lut_coord, 0, 1),
        )

        if not args.no_lut:
            lut = load_bf3_lut_dds(args.lut)
            stage_lut = sample_lut_trilinear(lut, tone_lut_coord)
            save_png(args.stages / "02_bf3_3d_lut.png", stage_lut)

            stage = stage_lut
            if not args.no_vignette:
                stage = apply_vignette(stage)
                save_png(args.stages / "03_bf3_vignette.png", stage)

            if not args.no_grain:
                stage = apply_grain(stage, load_grain(args.grain))
                save_png(args.stages / "04_bf3_grain_final.png", stage)

    lum = (
        0.2126 * inp[..., 0]
        + 0.7152 * inp[..., 1]
        + 0.0722 * inp[..., 2]
    )
    q = np.quantile(lum[np.isfinite(lum)], [0.5, 0.9, 0.99, 0.999, 1.0])

    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Exposure compensation: {args.exposure_ev:+.2f} EV")
    print(
        "Input luminance percentiles "
        f"(50/90/99/99.9/max): {q[0]:.4f}, {q[1]:.4f}, "
        f"{q[2]:.4f}, {q[3]:.4f}, {q[4]:.4f}"
    )


def main():
    p = argparse.ArgumentParser(
        description=(
            "Apply the reconstructed BF3 Shader 1490 photographic pass "
            "to scene-linear HDR."
        )
    )
    p.add_argument("input", type=Path, help="Scene-linear HDR OpenEXR input")
    p.add_argument(
        "--lut",
        type=Path,
        required=True,
        help="Local colorGradingTexture.dds (32x32x32 RGBA8)",
    )
    p.add_argument("--grain", type=Path, help="Local filmGrainTexture.png")
    p.add_argument("-o", "--output", type=Path, default=Path("bf3_post.png"))
    p.add_argument(
        "--exposure-ev",
        type=float,
        default=0.0,
        help="Multiply HDR input by 2^EV before BF3 tone mapping",
    )
    p.add_argument("--no-lut", action="store_true")
    p.add_argument("--no-vignette", action="store_true")
    p.add_argument("--no-grain", action="store_true")
    p.add_argument(
        "--stages",
        type=Path,
        help="Optional directory for diagnostic stage PNGs",
    )

    args = p.parse_args()

    if not args.input.exists():
        p.error(f"Input does not exist: {args.input}")
    if not args.no_lut and not args.lut.exists():
        p.error(f"LUT does not exist: {args.lut}")
    if not args.no_grain and args.grain is None:
        p.error("--grain is required unless --no-grain is specified")
    if args.grain is not None and not args.grain.exists():
        p.error(f"Grain texture does not exist: {args.grain}")

    process(args)


if __name__ == "__main__":
    main()
