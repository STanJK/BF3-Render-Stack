// Clean-room behavioral reference for the captured BF3 final photographic pass.
// This is NOT original DICE source, DXBC, disassembly, or decompiled shader text.
//
// Resource semantics observed in the captured pass:
//   main HDR texture
//   half-resolution bloom texture
//   32^3 color-grading LUT
//   film-grain texture
//
// The public Python implementation in bf3_post.py is the executable reference.

float3 BF3ToneCurve(float3 x)
{
    x = max(x, 0.0.xxx);

    float3 r1 = 0.985521 * x;
    float3 r2 = 0.985521 * x + 0.058662;
    float3 numerator = r1 * r2;

    float3 d1 = 0.774597 * x + 0.048281;
    float3 d2 = 0.774597 * x + 1.242710;
    float3 denominator = d1 * d2;

    float3 y = sqrt(max(numerator / denominator, 0.0.xxx));

    // Maps into voxel-center coordinates for a 32^3 LUT.
    return y * 0.96875 + 0.015625;
}

float BF3DirtSourceLuma(float3 c)
{
    return dot(c, float3(0.299, 0.587, 0.114));
}

// Conceptual final-pass ordering:
//
// float3 hdr = mainHDR + bloom * bloomScale;
// hdr *= colorScale;
// float3 lutCoord = BF3ToneCurve(hdr);
// float3 color = ColorLUT.SampleLevel(linearClamp, lutCoord, 0).rgb;
// color = ApplyRecoveredVignette(color, uv);
// color = ApplyRecoveredFilmGrain(color, uv);
// return color;
//
// See docs/shader1490.md and docs/pipeline.md for recovered constants.
