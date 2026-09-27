# Methodology

BF3 Render Stack is a behavioral reconstruction project built from GPU-capture
observation and independent reimplementation.

## Observation sources

The reconstruction process uses RenderDoc capture data from Battlefield 3,
including:

- shader resource bindings and constants;
- render-target snapshots;
- screen-space vertex data;
- blend/sampler state;
- locally exported reference textures.

Anyone with their own compatible capture can reproduce the required input set.
See [extract-reference-assets.md](extract-reference-assets.md).

## Reconstruction process

1. **Isolate a pass or draw.**
   Capture the render target immediately before and after the target draw.

2. **Recover resource semantics.**
   Identify texture roles, dimensions, formats, constant buffers, vertex data,
   sampler behavior, blend state, and render-target format.

3. **Write an independent implementation.**
   Re-express the observed behavior in Python, HLSL reference code, or Blender
   compositor nodes.

4. **Validate against GPU output.**
   Compare the reconstructed HDR result to captured render-target snapshots.

5. **Generalize into a creator-facing workflow.**
   Keep the offline replay path for numerical validation and a separate
   Blender-native implementation for interactive scene work.

## Reproducibility

The repository does not depend on one specific RenderDoc resource ID or event
number. Those identifiers are capture-specific.

Instead, the extraction guide identifies the required resources by:

- dimensions and format;
- shader-resource role;
- draw ordering;
- additive HDR behavior;
- visible optical contribution.

This allows the workflow to be repeated on a new capture rather than relying on
a single archived frame.
