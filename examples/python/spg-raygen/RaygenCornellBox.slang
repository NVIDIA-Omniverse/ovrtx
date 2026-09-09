// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// SPG raygen SHOWCASE: a ray-traced Cornell box rendered by a single SPG ray-generation node.
//
// Uses ONLY the standard ray-tracing intrinsics and the scene binding a node already receives from its
// RenderProduct -- no scene-geometry buffers, no renderer types, no includes, nothing required at link
// time:
//   * one PRIMARY ray per pixel through a perspective camera, placed by the auto-provided
//     camera-to-trace-space transform,
//   * the exact per-triangle GEOMETRIC NORMAL, recovered from the trace itself,
//   * a SHADOW ray toward the light -> hard ray-traced shadows,
//   * N.L diffuse shading tinted by the recovered normal.
//
// The scene's two blocks are ordinary solid 6-sided meshes rotated about Y, so their faces are not axis
// aligned; each face still resolves to its own correct normal.
//
// PER-PIXEL ALGORITHM
// 1. Camera ray. The launch index maps to [-1,1] screen coordinates (y flipped, so row 0 is the top of
//    the image) and from there to a direction in scene-unit camera space, where the camera sits at the
//    origin looking down -Z and tanHalfFov sets the fan angle. Origin and direction are then moved into
//    trace space by sceneTransform, so the shader never needs to know where the camera is in the world.
// 2. Primary trace. An inline RayQuery returns the hit distance and the surface's identity -- instance
//    and primitive index -- which the probes use to confirm they landed on the same triangle. A miss
//    writes black with alpha 0 and stops.
// 3. Normal. See RECOVERING THE NORMAL below.
// 4. Shadow ray. The hit point is lifted along the normal by a small epsilon so the ray cannot strike
//    its own surface, then traced toward the light with RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH: an
//    occlusion query only needs to know whether anything blocks the light, not what is closest, so
//    traversal stops at the first hit.
// 5. Shading. lighting = ambient + (1 - ambient) * N.L * visibility, where visibility is shadowFactor
//    when occluded and 1 otherwise. The ambient term keeps shadowed surfaces readable rather than black.
//
// RECOVERING THE NORMAL
// A triangle is flat, so three points on it define its plane exactly. The primary ray gives one point
// and the surface's identity (instance + primitive). Two probe rays parallel to it -- origin shifted
// sideways, direction unchanged -- give two more points on the same face, and the cross product of the
// two edge vectors is the geometric normal. The probe offset scales with hit distance so it stays
// roughly constant on screen.
//
// Probes are trusted only when they land on the same surface, checked over four attempts: both offset
// directions requiring the same triangle, then both again requiring only the same instance. The relaxed
// pass matters because a flat quad is two coplanar triangles -- a probe crossing that seam still lies in
// the same plane, so the fit stays exact; without it every quad diagonal becomes a line of fallback
// pixels. When all four fail (a true silhouette) the normal falls back to -direction, confining the
// error to a thin edge line.
//
// The result is exact in the triangle interior for any geometry, including tessellated and moving
// objects, since it is re-derived every frame. It costs three rays per shaded hit plus one shadow ray,
// and degrades on triangles smaller than the probe offset -- tune normalEpsilon: too small makes the
// cross product ill-conditioned, too large crosses more edges.
//
// OUTPUT ENCODING
// RGB = the recovered normal encoded to [0,1] (n*0.5+0.5), modulated by N.L and shadowing.
// A   = visibility: 1 lit, shadowFactor shadowed, 0 miss.
//
// Colour and visibility are kept in separate channels so shading and shadowing can be verified
// independently. main.py checks the render without a golden image: that every ray
// hits a surface; that each wall's dominant colour channel matches its normal (the channel ordering
// survives any lighting level, so the check is immune to brightness but fails on a wrong or flipped
// normal); that more than 1% of pixels carry a normal more than 15 degrees off every axis direction,
// which only genuine per-triangle recovery produces; and that both shadowed and lit pixel populations
// are present, the latter so a uniformly dark image cannot pass the colour checks.
//
// Direct lighting only -- no global illumination, so none of the colour bleeding a physically lit
// Cornell box shows. The colours are surface normals, not materials.

struct Params
{
    // Camera-to-trace-space transform of the render product's camera, auto-provided from the implicit
    // scene binding. Rays are authored in scene-unit CAMERA space and placed by this matrix, so the
    // shader needs no world-space knowledge. Row 3 is the camera position in trace space.
    row_major float4x4 sceneTransform;
    float3 lightPosCamera;   // point light, in scene-unit camera space
    float renderScaleFactor; // scene units -> render units, auto-provided
    float tanHalfFov;        // tan(vertical FOV / 2); drives the perspective ray fan
    float maxRange;          // primary-ray far distance (scene units)
    float shadowFactor;      // brightness multiplier where the light is occluded
    float ambient;           // ambient term so shadowed surfaces stay readable
    float normalEpsilon;     // sideways probe offset, as a fraction of the hit distance
};

// [snippet:raygen-bindings]
[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] RaytracingAccelerationStructure g_Scene; // scene TLAS, implicit from the RenderProduct
[[vk::binding(2, 1)]] RWTexture2D<float4> g_Image;             // NxN output: the rendered Cornell box
// [/snippet:raygen-bindings]

/// One inline trace. Returns false on a miss; otherwise reports the hit distance and the surface the
/// ray landed on (instance + primitive), which is what lets the probes below confirm they share a
/// triangle with the primary hit.
bool traceHit(float3 origin, float3 direction, float tMax, out float t, out uint instanceId, out uint primIndex)
{
    RayDesc r;
    r.Origin = origin;
    r.Direction = direction;
    r.TMin = 0.0f;
    r.TMax = tMax;

    RayQuery<RAY_FLAG_NONE> q;
    q.TraceRayInline(g_Scene, RAY_FLAG_NONE, 0xFF, r);
    while (q.Proceed()) {}

    t = 0.0f;
    instanceId = 0;
    primIndex = 0;
    if (q.CommittedStatus() != COMMITTED_TRIANGLE_HIT)
        return false;
    t = q.CommittedRayT();
    instanceId = q.CommittedInstanceID();
    primIndex = q.CommittedPrimitiveIndex();
    return true;
}

/// Recover the EXACT geometric normal of the hit triangle using only ray queries.
///
/// Two extra rays are fired parallel to the primary one, offset sideways by a small distance. When all
/// three land on the SAME triangle (same instance and primitive), their three hit points lie on that
/// triangle's plane, so the cross product of the two edge vectors is the triangle's exact geometric
/// normal -- no vertex data, no scene-geometry buffer, no renderer types.
///
/// Near a triangle boundary a probe can land on a neighbouring triangle; that is detected (the
/// instance/primitive differs) and retried with the probes mirrored to the other side. If both attempts
/// straddle an edge the function reports failure and the caller falls back, which confines any error to
/// a thin line of pixels along silhouettes.
bool estimateGeometricNormal(float3 origin, float3 direction, float tMax, float t0, uint id0, uint prim0, out float3 normal)
{
    normal = -direction;

    // Orthonormal basis perpendicular to the ray, to offset the probes in.
    const float3 helper = (abs(direction.x) < 0.9f) ? float3(1.0f, 0.0f, 0.0f) : float3(0.0f, 1.0f, 0.0f);
    const float3 tangentU = normalize(cross(direction, helper));
    const float3 tangentV = cross(direction, tangentU);

    // Scale the offset with distance so the probes stay a roughly constant size on screen.
    const float offset = max(g_Params.normalEpsilon * t0, 1e-4f);
    const float3 hit0 = origin + direction * t0;

    // Attempts 0-1 probe each side requiring the exact same triangle. Attempts 2-3 repeat requiring only
    // the same instance: a probe that merely crossed the seam between two coplanar triangles of the same
    // flat face still lies on the same plane, so the fit stays exact -- without this, every quad's
    // diagonal would show as a line of fallback pixels.
    for (int attempt = 0; attempt < 4; ++attempt)
    {
        const float sign = ((attempt & 1) == 0) ? 1.0f : -1.0f;
        const bool samePrimitiveRequired = (attempt < 2);

        float t1, t2;
        uint id1, id2, prim1, prim2;
        const bool ok1 = traceHit(origin + tangentU * (sign * offset), direction, tMax, t1, id1, prim1);
        const bool ok2 = traceHit(origin + tangentV * (sign * offset), direction, tMax, t2, id2, prim2);
        if (!ok1 || !ok2 || id1 != id0 || id2 != id0)
            continue; // a probe left the surface entirely; try the opposite side
        if (samePrimitiveRequired && (prim1 != prim0 || prim2 != prim0))
            continue; // crossed a triangle boundary; retry, then relax to same-instance

        const float3 hit1 = origin + tangentU * (sign * offset) + direction * t1;
        const float3 hit2 = origin + tangentV * (sign * offset) + direction * t2;

        float3 n = cross(hit1 - hit0, hit2 - hit0);
        const float len = length(n);
        if (len < 1e-12f)
            continue; // degenerate probe triangle

        n /= len;
        normal = (dot(n, direction) > 0.0f) ? -n : n; // orient toward the viewer
        return true;
    }
    return false;
}

/// Is the light blocked? ACCEPT_FIRST_HIT stops at the first blocker -- an occlusion query needs no
/// closest hit.
bool isOccluded(float3 origin, float3 direction, float tMax)
{
    RayDesc shadowRay;
    shadowRay.Origin = origin;
    shadowRay.Direction = direction;
    shadowRay.TMin = 0.0f;
    shadowRay.TMax = tMax;

    RayQuery<RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH> sq;
    sq.TraceRayInline(g_Scene, RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH, 0xFF, shadowRay);
    while (sq.Proceed()) {}
    return sq.CommittedStatus() == COMMITTED_TRIANGLE_HIT;
}

// [snippet:raygen-entry]
[shader("raygeneration")]
void rayGenCornellBox()
{
    const uint2 idx = DispatchRaysIndex().xy;
    const uint2 dim = DispatchRaysDimensions().xy;

    // Perspective ray fan in scene-unit camera space: the camera looks down -Z, +Y is up. Pixel centres
    // map to [-1, 1] with y flipped (row 0 = top of the image).
    const float u = (2.0f * (float(idx.x) + 0.5f) / float(dim.x)) - 1.0f;
    const float v = 1.0f - (2.0f * (float(idx.y) + 0.5f) / float(dim.y));
    const float aspect = float(dim.x) / float(dim.y);
    const float3 dirCamera = normalize(float3(u * g_Params.tanHalfFov * aspect, v * g_Params.tanHalfFov, -1.0f));

    const float3 origin = mul(float4(0.0f, 0.0f, 0.0f, 1.0f), g_Params.sceneTransform).xyz; // the camera
    const float3 direction = normalize(mul(float4(dirCamera, 0.0f), g_Params.sceneTransform).xyz);
    const float tMax = g_Params.maxRange * g_Params.renderScaleFactor;

    float t0;
    uint id0, prim0;
    if (!traceHit(origin, direction, tMax, t0, id0, prim0))
    {
        g_Image[idx] = float4(0.0f, 0.0f, 0.0f, 0.0f); // miss -> black, alpha 0
        return;
    }

    float3 n;
    estimateGeometricNormal(origin, direction, tMax, t0, id0, prim0, n); // falls back to -direction

    // Offset along the normal so the shadow ray cannot self-hit.
    const float epsilon = 2.0f * g_Params.renderScaleFactor; // 2 scene units
    const float3 hitP = origin + direction * t0;
    const float3 shadowOrigin = hitP + n * epsilon;

    const float3 lightP = mul(float4(g_Params.lightPosCamera, 1.0f), g_Params.sceneTransform).xyz;
    const float3 toLight = lightP - shadowOrigin;
    const float lightDist = length(toLight);
    const float3 lightDir = toLight / max(lightDist, 1e-6f);

    const float diffuse = max(dot(n, lightDir), 0.0f);
    const bool occluded = isOccluded(shadowOrigin, lightDir, max(lightDist - epsilon, 0.0f));
    const float visibility = occluded ? g_Params.shadowFactor : 1.0f;

    // Colour = the recovered normal (encoded to [0,1]) modulated by the lighting, so each surface's hue
    // identifies its orientation while the image still reads as a lit 3-D room.
    const float3 normalColor = n * 0.5f + 0.5f;
    const float lighting = g_Params.ambient + (1.0f - g_Params.ambient) * diffuse * visibility;
    g_Image[idx] = float4(normalColor * lighting, occluded ? g_Params.shadowFactor : 1.0f);
}
// [/snippet:raygen-entry]
