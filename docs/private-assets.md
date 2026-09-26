# Private-reference boundary

The research process used a local reference bundle containing material extracted
from a GPU capture of a legally obtained Battlefield 3 installation. That bundle
is intentionally **not** part of the public repository.

## Local-only reference categories

### Capture data

- RenderDoc `.rdc` capture
- XML + binary capture export
- per-draw HDR render-target snapshots
- main HDR and bloom buffer exports

### Extracted textures

- star flare texture
- rainbow/ring texture
- local dirt-source texture
- screen-space lens-dirt texture
- warm optical-ghost texture
- blue optical-ghost texture
- 32³ color-grading LUT
- 512² film-grain texture

### Shader artifacts

- original DXBC bytecode
- verbatim RenderDoc shader disassembly/decompilation
- unrelated captured game shaders used only for research cross-checks

## What the public repo contains instead

- independently written Python/Blender implementations;
- numerical constants and resource dimensions needed for interoperability;
- mathematical descriptions of observed behavior;
- validation results;
- reduced research figures / frame excerpts for commentary.

## Suggested local folder

```text
private/
├─ capture/
├─ flare/
│  ├─ star.png
│  ├─ ring.png
│  ├─ dirty_source.png
│  ├─ lens_dirt.png
│  ├─ warm_ghost.png
│  └─ blue_ghost.png
├─ shaders/
├─ colorGradingTexture.dds
└─ filmGrainTexture.png
```

The top-level `.gitignore` blocks the known private filenames and capture
extensions to reduce the chance of accidental publication.
