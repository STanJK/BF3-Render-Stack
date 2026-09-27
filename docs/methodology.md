# Methodology

BF3 Render Stack is a behavioral reconstruction project. The public repository
separates **observed behavior** from **third-party artifacts**.

## Observation sources

The reconstruction work used GPU-capture data from a locally owned Battlefield 3
installation, including:

- RenderDoc frame captures;
- shader resource bindings and constants;
- render-target snapshots;
- screen-space vertex data;
- blend/sampler state;
- extracted local reference textures.

Those raw materials are not redistributed by this repository.

## Reconstruction process

1. **Isolate a pass or draw.**
   Capture the render target immediately before and after the target draw.

2. **Recover resource semantics.**
   Identify texture roles, dimensions, formats, constant buffers, vertex data,
   sampler behavior, blend state and render-target format.

3. **Write an independent implementation.**
   Re-express the observed behavior in Python or Blender compositor nodes.

4. **Validate against GPU output.**
   Compare the reconstructed HDR result to captured render-target snapshots.

5. **Generalize into a creator-facing workflow.**
   Keep the exact offline replay for validation and a separate Blender-native
   implementation for interactive scene work.

## Public/private boundary

Public:
- independently written source code;
- equations and constants;
- resource dimensions and semantic descriptions;
- validation metrics;
- research figures and reduced frame excerpts used for commentary.

Private/local-only:
- raw RenderDoc captures;
- extracted game textures/LUT/grain;
- original shader bytecode;
- verbatim shader disassembly/decompilation;
- raw game framebuffer exports.

See `private-assets.md` and `THIRD_PARTY_NOTICE.md`.
