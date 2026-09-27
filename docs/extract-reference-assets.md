# Extracting the Battlefield 3 reference inputs

BF3 Render Stack is runnable with a small set of reference resources that you
can export from your own Battlefield 3 GPU capture. You do **not** need the
original RenderDoc capture used during development.

This guide walks through the exact resources the current tools expect, how to
identify them in RenderDoc, how to export them, and where to place them in the
repository.

> Use a copy of Battlefield 3 you are authorized to run. This guide covers GPU
> capture/export for interoperability and research; it does not cover bypassing
> DRM or redistributing extracted game assets.

## What you need

Required for the lens-flare reconstruction:

```text
local_assets/
└─ flare/
   ├─ star.png
   ├─ ring.png
   ├─ dirty_source.png
   ├─ lens_dirt.png
   ├─ warm_ghost.png
   └─ blue_ghost.png
```

Required for the final photographic pass:

```text
local_assets/
├─ colorGradingTexture.dds
└─ filmGrainTexture.png
```

The expected resource characteristics are:

| File | Captured resource | Expected size / format |
|---|---|---|
| `star.png` | star / diffraction flare texture | 512×512, BC1 sRGB source |
| `ring.png` | rainbow/ring flare texture | 512×512, BC1 sRGB source |
| `dirty_source.png` | local flare-source mask | 256×256, BC1 sRGB source |
| `lens_dirt.png` | fixed screen-space dirt texture | 1024×512, RGBA8 sRGB source |
| `warm_ghost.png` | warm optical ghost | 256×256, BC1 sRGB source |
| `blue_ghost.png` | blue optical ghost | 128×128, BC1 sRGB source |
| `colorGradingTexture.dds` | final-pass 3D LUT | 32×32×32, RGBA8 |
| `filmGrainTexture.png` | final-pass film grain | 512×512, R8 source |

The Python/Blender code is written against these filenames.

---

## 1. Capture a useful BF3 frame

Install RenderDoc and capture Battlefield 3 through a compatible D3D11 capture
path.

For the easiest extraction, use a scene with:

- a visible bright sun or strong flare source;
- the normal BF3 post-processing path enabled;
- enough contrast to make the flare layers obvious in the Texture Viewer.

A frame with a visible sun makes the five flare draws much easier to identify,
but the LUT and grain texture can be extracted from almost any normal gameplay
frame.

### Practical capture note

Battlefield 3 is a 32-bit title. RenderDoc capture overhead can push it close to
its virtual-address-space limit at high resolutions. If capture is unstable,
temporarily capture at a lower resolution such as 1280×720. Resource dimensions
for the authored flare textures, LUT, and grain do not depend on the display
resolution.

---

## 2. Find the final photographic pass

Open the capture in RenderDoc and work near the end of the frame.

You are looking for a late fullscreen pixel pass whose shader-resource set has
the following shape:

```text
full-resolution FP16 HDR texture
half-resolution FP16 bloom texture
32×32×32 RGBA8 3D texture
512×512 single-channel grain texture
```

In the reference capture these semantic roles were:

```text
main HDR texture
tonemap/bloom texture
color-grading 3D LUT
film-grain texture
```

A good way to identify the pass:

1. Select late fullscreen draws in the Event Browser.
2. In **Pipeline State → Pixel Shader → Resources**, inspect the bound SRVs.
3. Look for a 3D texture with dimensions **32×32×32**.
4. Confirm that the same draw also binds a **512×512** grain-like texture.
5. In the Texture Viewer, inspect the full-resolution HDR input and the final
   output to confirm you are on the photographic final pass.

The exact RenderDoc resource IDs/event IDs will differ between captures, so use
resource shape and visual content rather than hard-coded IDs.

---

## 3. Export the 32³ color-grading LUT

With the final photographic pass selected:

1. Open the **32×32×32 RGBA8 3D texture** in Texture Viewer.
2. Use **Save Texture**.
3. Export it as DDS while preserving the 3D texture and mip 0.
4. Name it:

```text
colorGradingTexture.dds
```

5. Place it at:

```text
BF3-Render-Stack/local_assets/colorGradingTexture.dds
```

### Important DDS requirement

The current `bf3_post.py` loader expects the same simple layout used by the
reference export: a legacy DDS header followed by the 32³ RGBA8 payload.

A matching file is normally:

```text
128-byte DDS header
+ 32 × 32 × 32 × 4 bytes
= 131200 bytes total
```

If your RenderDoc version emits a DX10-extended DDS instead, the validation tool
will flag it. In that case export/convert to an uncompressed legacy RGBA8 DDS
without resizing or color processing.

---

## 4. Export the grain texture

Still on the final photographic pass:

1. Open the **512×512 single-channel grain resource**.
2. Save mip 0 as PNG.
3. Do not resize, denoise, sharpen, or color-correct it.
4. Name it:

```text
filmGrainTexture.png
```

5. Place it at:

```text
BF3-Render-Stack/local_assets/filmGrainTexture.png
```

The current implementation reads the first channel of the PNG.

---

## 5. Find the five flare draws

Move earlier in the frame, immediately before the bloom/final-post region.

The reference frame contained five additive screen-space flare draws in this
order:

```text
1. star flare
2. rainbow/ring flare
3. lens-dirt modulation
4. warm optical ghost
5. blue mirrored ghost
```

A useful identification strategy is to step one draw at a time while watching
the FP16 HDR render target in Texture Viewer. Each target draw adds a visible
optical element without replacing the existing HDR scene.

The captured blend behavior is effectively additive RGB.

### 5.1 Star texture

Look for a draw that:

- uses a 512×512 BC1/sRGB texture;
- places a square sprite around the sun;
- produces two differently rotated/tinted star patterns from the same texture.

Export that texture as:

```text
local_assets/flare/star.png
```

Expected authored texture size:

```text
512×512
```

### 5.2 Rainbow/ring texture

The next flare layer uses a 512×512 BC1/sRGB ring/rainbow texture and samples it
twice with opposite rotations.

Export as:

```text
local_assets/flare/ring.png
```

Expected size:

```text
512×512
```

### 5.3 Dirt source texture

The dirt modulation draw uses two textures:

- a local flare-source image centered on the flare;
- a screen-fixed lens-dirt texture.

The local source is the **256×256 BC1/sRGB** texture. Export it as:

```text
local_assets/flare/dirty_source.png
```

Expected size:

```text
256×256
```

### 5.4 Screen-space lens dirt

The second texture in the dirt draw is fixed in screen space.

Export the **1024×512 RGBA8/sRGB** texture as:

```text
local_assets/flare/lens_dirt.png
```

Expected size:

```text
1024×512
```

### 5.5 Warm optical ghost

Find the warm ghost draw after the dirt pass.

Its authored resource is a **256×256 BC1/sRGB** texture. The captured draw maps
it onto an extremely large screen-space quad, so only a small interior region
may be visible on screen.

Export as:

```text
local_assets/flare/warm_ghost.png
```

Expected size:

```text
256×256
```

### 5.6 Blue mirrored ghost

The final isolated flare draw uses the small blue optical-ghost texture. In the
captured frame its screen-space center was the exact reflection of the sun
around the screen center.

Export the **128×128 BC1/sRGB** texture as:

```text
local_assets/flare/blue_ghost.png
```

Expected size:

```text
128×128
```

---

## 6. Export settings for the flare PNGs

For all six flare images:

- export mip 0;
- preserve the original dimensions;
- export to PNG;
- do not apply tonemapping;
- do not normalize brightness;
- do not crop;
- do not resize;
- do not denoise or sharpen.

The source SRVs are sRGB resources. The public replay code therefore loads the
PNG as sRGB and converts it back to linear before performing the recovered
shader math.

---

## 7. Final directory layout

After extraction, your repository should look like:

```text
BF3-Render-Stack/
├─ local_assets/
│  ├─ flare/
│  │  ├─ star.png
│  │  ├─ ring.png
│  │  ├─ dirty_source.png
│  │  ├─ lens_dirt.png
│  │  ├─ warm_ghost.png
│  │  └─ blue_ghost.png
│  ├─ colorGradingTexture.dds
│  └─ filmGrainTexture.png
├─ src/
├─ blender/
└─ ...
```

`local_assets/` is ignored by Git because these are local inputs produced from
your own capture.

---

## 8. Validate the extracted files

Run:

```powershell
py .\tools\check_reference_assets.py
```

A valid setup should report:

```text
[OK] star.png                512x512
[OK] ring.png                512x512
[OK] dirty_source.png        256x256
[OK] lens_dirt.png           1024x512
[OK] warm_ghost.png          256x256
[OK] blue_ghost.png          128x128
[OK] filmGrainTexture.png    512x512
[OK] colorGradingTexture.dds 32^3 RGBA8 payload
```

---

## 9. Run the flare replay

```powershell
py -m pip install -r requirements.txt
$env:OPENCV_IO_ENABLE_OPENEXR="1"

py .\src\bf3_flare_replay.py `
  .\input.exr `
  --assets-dir .\local_assets\flare `
  --sun-uv 0.70 0.28 `
  -o .\flare.exr
```

`--sun-uv` uses a top-left image origin:

```text
(0,0) ---------------- (1,0)
  |                      |
  |                      |
(0,1) ---------------- (1,1)
```

For the original validation frame, the reconstructed capture sun position was
approximately:

```text
(0.658765625, 0.370444444)
```

For your own scene, use the actual screen-space flare-source position.

---

## 10. Run the final photographic pass

Once you have an HDR image containing the scene + flare + bloom:

```powershell
py .\src\bf3_post.py `
  .\flare_plus_bloom.exr `
  --lut .\local_assets\colorGradingTexture.dds `
  --grain .\local_assets\filmGrainTexture.png `
  --exposure-ev 0.0 `
  -o .\final.png
```

The exposure value is **scene calibration**, not a universal Battlefield 3
constant. Start at `0.0` EV and adjust only if your input renderer uses a
different scene-linear exposure scale.

Use `--stages <directory>` to export diagnostic images after each major
final-post stage.

---

## 11. Blender setup

The Blender integration expects:

```text
//local_assets/flare/
```

relative to the saved `.blend` file.

The scene also needs:

- an active Camera;
- an object named `SunCircle` at the visible flare-source position;
- an existing Bloom/Glare node downstream of the generated flare stack.

Run:

```text
blender/build_bf3_flare_nodes.py
```

from Blender's Scripting workspace.

See [blender-workflow.md](blender-workflow.md) for the compositor topology.

---

## Troubleshooting

### The LUT loader says the DDS is invalid

Check that:

- the file starts with `DDS `;
- the texture is 32×32×32;
- it is uncompressed RGBA8;
- the export does not use a DX10 extended header;
- the file has not been converted through an image editor.

### Flare colors look too dark or too bright

Make sure the six PNGs were exported without tonemapping and are being treated
as sRGB images. Do not manually linearize the files before giving them to the
tools.

### The warm ghost forms a square seam in Blender

Use the current repository version of `build_bf3_flare_nodes.py`. Each flare
layer must be accumulated directly into a full-frame HDR image. Pre-composing
finite flare sprites into a finite-domain image can produce a visible compositor
boundary.

### Capture crashes at high resolution

BF3 is a 32-bit process. Try a lower capture resolution. The required authored
textures/LUT/grain keep their native dimensions.

### I cannot find the exact same RenderDoc event IDs

That is expected. Resource IDs and event numbers are capture-specific. Identify
the passes by resource dimensions, binding pattern, additive HDR behavior, and
visual output rather than by fixed IDs.
