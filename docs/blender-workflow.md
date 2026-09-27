# Blender workflow

The current Blender integration builds the recovered lens-flare stack as native
compositor nodes.

## Scene requirements

- an active Camera;
- a visible sun-disc / anchor object named `SunCircle`;
- the six local-only flare textures under `//private/flare/`;
- a compositor Bloom/Glare node downstream of the reconstructed flare stack.

## Intended graph

```text
Render Layers ---------------------------> A/B Switch OFF
     |
     +--> Raw_HDR File Output
     |
     +--> + Star A
          + Star B
          + Ring A
          + Ring B
          + Lens Dirt
          + Warm Ghost
          + Blue Ghost ------------------> A/B Switch ON
                                               |
                                               v
                                             Bloom
                                               |
                                      Composite / Viewer
```

The script projects `SunCircle` through the active camera and derives the
screen-space center and radial distance used by the recovered flare equations.

## Important compositor-domain rule

Do not first add all finite flare sprites into a separate "flare-only" image and
then add that result to the scene. In Blender this can inherit a finite image
domain and create a visible square seam.

Instead, each recovered flare layer is added directly into the full render-sized
HDR chain.

## Current limitation

The Bloom node is a visual approximation, not yet a recovered Frostbite bloom
generator. The final photographic pass is handled separately by
`src/bf3_post.py`.
