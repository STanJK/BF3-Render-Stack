# Final-pass functional reconstruction (Shader 1490)

This note records the **behavioral reconstruction** of the captured final
photographic pixel pass. It is intentionally not a verbatim shader dump or
DXBC disassembly.

## Inputs

Observed resource roles:

```text
t0  full-resolution scene-linear HDR main texture
t1  half-resolution bloom texture
t2  32^3 color-grading texture
t3  512^2 R8 film-grain texture
```

## Pipeline

Conceptually:

```text
main = sample(mainTexture)
bloom = sample(tonemapBloomTexture)

hdr = main + bloom * bloomScale
hdr *= colorScale

coord = ToneCurve(hdr)
color = Sample3DLUT(coord)
color = ApplyVignette(color)
color = ApplyGrain(color)

alpha = dot(color, (0.299, 0.587, 0.114))
```

The public Python implementation currently expects Bloom to have been produced
upstream, so `src/bf3_post.py` starts from the HDR image at the tone-curve stage.

## Captured constants used by the public implementation

```text
colorScale ~= (1.0000066, 1.0000066, 1.0000066)

vignetteParams = (1.5, 1.5, 2.0)
vignetteColor  = (0.000, 0.007, 0.013)
vignetteAlpha  = 0.5

filmGrainScale = (0.005, 0.005, 0.005)
```

## Why no original shader code is checked in

The objective is to publish an interoperable reconstruction, not to redistribute
DICE shader artifacts. Therefore original DXBC bytecode and verbatim RenderDoc
shader dumps remain private while resource semantics, equations, constants and
independently written implementations are public.
