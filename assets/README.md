# Local-only assets

No extracted Battlefield 3 assets are committed here.

For local experiments, point the tools at assets you extract from your own
legally obtained copy/capture.

Expected flare assets:

```text
star.png
ring.png
dirty_source.png
lens_dirt.png
warm_ghost.png
blue_ghost.png
```

Expected final-pass assets:

```text
colorGradingTexture.dds
filmGrainTexture.png
```

Recommended local layout:

```text
private/
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

`private/` is gitignored.
