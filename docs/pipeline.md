# Reconstructed pipeline

This document records the current public reconstruction of the BF3 photographic
render stack used in the captured frame. It deliberately describes behavior,
resource roles and independently written equations rather than reproducing
proprietary shader dumps.

## High-level order

```text
scene-linear HDR
  -> lens flare stack
       -> star
       -> rainbow ring
       -> lens dirt
       -> warm ghost
       -> blue ghost
  -> bloom
  -> final photographic pass
       -> exposure / color scale
       -> tone curve
       -> 32^3 3D LUT
       -> vignette
       -> film grain
  -> SDR output
```

The original captured final pass sampled a full-resolution HDR main texture,
a half-resolution bloom texture, a 32³ color-grading texture and a 512² grain
texture.

## Lens-flare observations

Five additive screen-space draws were isolated and replayed independently.
All five wrote into the same FP16 HDR render target.

| Stage | Captured behavior | Reference size at 720p | Scalar gain |
|---|---|---:|---:|
| Star | same texture sampled twice, rotated by `0.4d` and `1.2d` | ~765.17 px square | 0.06178417 |
| Ring | ring sampled twice, rotated by `-2d` and `+2d` | ~1102.66 px square | 0.01170392 |
| Dirt | local flare-source luminance × 30 × full-screen dirt texture | ~746.21 px source quad | 0.24746911 |
| Warm ghost | enormous optical ghost quad centered on sun | ~15360 px square | 0.17841211 |
| Blue ghost | optical ghost mirrored across screen center | ~921.60 px square | 0.07087997 |

`d` is the radial distance between the flare center and screen center in NDC:

```text
ndc_x = 2*u - 1
ndc_y = 1 - 2*v
d = sqrt(ndc_x^2 + ndc_y^2)
```

The captured blue ghost center is the exact screen-center reflection of the
sun center.

### Color multipliers

```text
Star A:     (12.000,  3.442, 0.079)
Star B:     (11.299, 12.000, 7.828)
Ring:       ( 3.000,  2.550, 1.977)
Warm ghost: ( 1.000,  0.922, 0.554)
Blue ghost: ( 0.131,  0.350, 1.174)
```

The captured blend state was effectively additive because source alpha was zero
while RGB used `ONE` against `INV_SRC_ALPHA`.

## Dirt pass

```text
L = 0.299 R + 0.587 G + 0.114 B
DirtContribution = ScreenDirt * (L * 30) * intensity
```

The screen dirt is sampled in screen space; it is not attached to the sun
sprite itself.

## Final photographic pass

The public implementation is in `src/bf3_post.py`.

### Tone curve

For each channel `x >= 0`:

```text
r1  = 0.985521*x
r2  = 0.985521*x + 0.058662
num = r1*r2

d1  = 0.774597*x + 0.048281
d2  = 0.774597*x + 1.242710
den = d1*d2

y = sqrt(num/den)
y = y*0.96875 + 0.015625
```

The final scale/bias maps the result into voxel-center coordinates for a 32³
LUT.

### 3D LUT

The captured color-grading resource is a 32 × 32 × 32 RGBA8 texture. The
reimplementation performs normalized trilinear sampling with edge clamp.

### Vignette

```text
vignetteParams = (1.5, 1.5, 2.0)
vignetteColor  = (0.000, 0.007, 0.013)
vignetteAlpha  = 0.5
```

The vignette is multiplicative and subtly blue-black rather than neutral black.

### Grain

```text
filmGrainScale = (0.005, 0.005, 0.005)
```

The reference implementation uses the captured 512² R8 texture supplied by the
user at runtime. That texture is not committed.

## Validation

The offline flare replay was compared against exported HDR render-target
snapshots after each flare draw. The final five-layer replay achieved roughly:

```text
HDR MAE  ≈ 0.00030
HDR RMSE ≈ 0.00058
```

Remaining error is concentrated in small bright regions and is consistent with
differences between native GPU BC1 sampling / FP16 stores and the offline
PNG-based reference path.

## Known approximation: Bloom

The current Blender project uses a compositor Bloom/Glare approximation. The
captured final shader uses a dedicated half-resolution bloom texture and a
small color scale. Reconstructing that upstream bloom-generation path remains
future work.
