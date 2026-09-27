# Reference asset setup

BF3 Render Stack expects eight small reference inputs extracted from your own
Battlefield 3 GPU capture.

Follow the complete guide:

**[docs/extract-reference-assets.md](../docs/extract-reference-assets.md)**

Expected local layout:

```text
local_assets/
├─ flare/
│  ├─ star.png
│  ├─ ring.png
│  ├─ dirty_source.png
│  ├─ lens_dirt.png
│  ├─ warm_ghost.png
│  └─ blue_ghost.png
├─ colorGradingTexture.dds
└─ filmGrainTexture.png
```

Validate the setup with:

```powershell
py .\tools\check_reference_assets.py
```
