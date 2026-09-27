# Validation notes

## Lens flare

The five captured additive flare draws were replayed over the HDR target and
compared with the corresponding captured output.

Current offline replay result:

```text
HDR MAE  ≈ 0.00030
HDR RMSE ≈ 0.00058
max absolute error observed in the test frame ≈ 0.01953
```

The remaining error is concentrated in a small number of bright pixels and is
consistent with differences between native GPU BC1 sampling / half-float stores
and the PNG-decoded offline path.

## Blender compositor

The Blender node graph is not intended to be bit-identical to D3D11. It is a
creator-facing implementation of the recovered structure.

A significant implementation issue discovered during transfer was compositor
**domain preservation**: pre-composing finite flare sprites into another finite
sprite domain produced visible square seams. The final Blender graph adds each
flare layer directly into the full-frame HDR image so every intermediate stage
retains the render-sized domain.

## Final post

The final-pass implementation reconstructs:
- exposure/color scale;
- the recovered rational/square-root tone curve;
- normalized trilinear sampling of the 32³ LUT;
- vignette;
- film grain.

The current Blender workflow still uses an approximate compositor Bloom/Glare
stage. Reconstructing BF3's upstream bloom-generation path is the largest
remaining gap in the camera stack.
