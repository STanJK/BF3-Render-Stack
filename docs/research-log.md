# Research log

This is a compact milestone log rather than a complete conversation transcript.

## 2026-09 — Final photographic pass

A late final pixel pass was isolated in RenderDoc and reconstructed behaviorally.

Observed resource roles:

- full-resolution FP16 scene-linear HDR input;
- half-resolution FP16 bloom input;
- 32³ RGBA8 3D color-grading LUT;
- 512² R8 grain texture.

Recovered public components:

- rational/square-root tone curve;
- LUT voxel-center mapping and trilinear sampling;
- blue-black vignette;
- low-amplitude film grain.

The reconstructed final pass was then transferred onto an original Blender scene.

## 2026-09 — Lens flare stack

Five additive HDR flare draws were isolated and mapped to:

1. star flare;
2. rainbow ring;
3. screen-space lens dirt;
4. warm optical ghost;
5. blue mirrored ghost.

The capture exposed screen-space quad geometry, per-layer gains, color multipliers, radial rotation relationships, and additive blending behavior.

Offline replay reached approximately:

```text
HDR MAE  ≈ 0.00030
HDR RMSE ≈ 0.00058
```

## 2026-09 — Blender transfer

A Blender-native compositor implementation was created for interactive scene work.

An important implementation bug was found during transfer: composing finite flare sprites into a finite intermediate image caused visible square seams because of compositor domain propagation.

The fix was architectural: every recovered flare layer is added directly to the full-frame HDR chain before the A/B switch and Bloom node.

## Current gap

The largest remaining gap is the **upstream bloom-generation pass**. The current Blender Bloom/Glare node is only an approximation; the captured final shader merely consumes a precomputed half-resolution bloom texture.

## Public-release boundary

Raw capture data, extracted assets, original bytecode, and verbatim disassembly remain local-only. The public repo records the independently written reconstruction, constants, methodology, and reduced research figures.
