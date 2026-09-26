# BF3 Render Stack

Research-oriented reconstruction of selected parts of the **Battlefield 3 / Frostbite 2 photographic render stack**, built from GPU-capture observations and independently written replay code.

The project currently focuses on:

- the five-layer lens-flare / optical-artifact stack;
- the final photographic pass: tone curve, 32³ LUT, vignette and grain;
- Blender compositor integration;
- validation against captured HDR buffers.

The public repository contains **our own code, equations, documentation, Blender integration, and research figures**. Extracted DICE/Frostbite assets, raw RenderDoc captures, shader bytecode/disassembly, LUTs, grain textures, flare textures, and game buffers are intentionally excluded.

> Unofficial research project. Not affiliated with Electronic Arts or DICE. Battlefield, Frostbite and related marks are property of their respective owners.

## Repository layout

```text
BF3-Render-Stack/
├─ src/
│  ├─ bf3_flare_replay.py
│  └─ bf3_post.py
├─ blender/
│  └─ build_bf3_flare_nodes.py
├─ examples/
│  └─ post.ps1
├─ docs/
│  ├─ pipeline.md
│  ├─ shader1490.md
│  ├─ private-assets.md
│  └─ images/
├─ assets/
│  └─ README.md
├─ requirements.txt
├─ THIRD_PARTY_NOTICE.md
└─ LICENSE
```

## Quick start

### Supply your own local reference assets

The code does **not** ship extracted Battlefield 3 assets. See `assets/README.md` and `docs/private-assets.md`.

Expected flare texture names:

```text
star.png
ring.png
dirty_source.png
lens_dirt.png
warm_ghost.png
blue_ghost.png
```

Expected final-post assets:

```text
colorGradingTexture.dds
filmGrainTexture.png
```

### Offline flare replay

```powershell
py -m pip install -r requirements.txt
$env:OPENCV_IO_ENABLE_OPENEXR="1"

py .\src\bf3_flare_replay.py `
  .\input.exr `
  -o .\flare.exr `
  --assets-dir .\private\flare `
  --sun-uv 0.70 0.28
```

### Final photographic pass

```powershell
py .\src\bf3_post.py `
  .\flare_plus_bloom.exr `
  --lut .\private\colorGradingTexture.dds `
  --grain .\private\filmGrainTexture.png `
  --exposure-ev -0.5 `
  -o .\final.png
```

### Blender compositor integration

Open `blender/build_bf3_flare_nodes.py` in Blender's Scripting workspace and run it. It projects an object named `SunCircle`, builds the flare stack as native compositor nodes, preserves the full-frame HDR domain, and inserts an A/B switch before the existing Bloom/Glare node.

## Validation

The offline five-layer flare replay was compared with captured HDR render-target snapshots and reached approximately:

```text
MAE  ≈ 0.00030
RMSE ≈ 0.00058
```

The Blender node version is creator-friendly rather than bit-identical to D3D11. The current Blender Bloom is also an approximation and remains a reconstruction target.

## Shader-code policy

The repo publishes **our own functional reimplementation and equations**. It does **not** publish verbatim DXBC bytecode, RenderDoc shader dumps, or decompiled/disassembled DICE shader text.

## Research status

- [x] Final-pass functional reconstruction
- [x] 32³ LUT trilinear sampling
- [x] vignette and grain reconstruction
- [x] five-layer lens-flare reconstruction
- [x] per-layer HDR validation
- [x] Blender compositor integration
- [ ] BF3 bloom reconstruction/calibration
- [ ] stronger sampler-level parity for BC1 textures
- [ ] generalized camera/occlusion logic
- [ ] HDR display-output path

## License

Original project code and documentation are MIT licensed. Third-party game imagery and marks in research figures are not covered by MIT; see `THIRD_PARTY_NOTICE.md`.
