<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# SPG shader sources

Read the relevant section when authoring ray-generation nodes or using pre-compiled sources.
All `examples/` and `docs/` paths are relative to the ovrtx public root, as in the parent skill.
The parent skill links the tested ray-generation launch snippets.

## Ray Generation

Slang only. The entry point is `[shader("raygeneration")]` and the launch script returns
`slang.rayQuery` or `slang.traceRays` in place of `slang.compute`. Either way the ray grid is
the output's shape, one invocation per element, so there is no `numthreads`.

`slang.rayQuery` traverses and shades inline in the ray-generation shader and needs nothing
else. `slang.traceRays` drives a pipeline with a shader binding table, so shading moves into
one `miss` and one hit group in the same file, named by the extra launch fields `miss`, `hit`,
`payloadSize` and `attributeSize`.

A shader under a RenderProduct is given the scene acceleration structure and its camera with
**no authored input and no connection**: bind it with `slang.binding("scene", inputs["scene"])`
and place rays with the `sceneTransform` value input rather than assuming world coordinates.
Only one hit group is supported; calculate `payloadSize` and `attributeSize` in bytes.
A `.spv` cannot be used on a ray-tracing stage.

**No geometry is exposed.** A hit yields distance and the surface's instance and primitive
index, and nothing else, so the example recovers geometric normals from two extra probe rays.

Depth: `docs/spg/do/raygen.rst`.

## Pre-Compiled Sources

The extension on `info:spg:sourceAsset` decides what happens: CUDA takes `.cu`, `.ptx`,
`.cubin` and `.fatbin`, Slang takes `.slang`, `.slang-module` and `.spv`. The launch script and
the `extern "C"` entry point are needed as for source.

A `.spv` carries no reflection at all: the descriptor space, the binding slots, the
parameter-block offsets and the thread group size all have to be stated in the launch script,
and it cannot be used on a ray-tracing stage. It runs its compute entry point `main`, whatever
`subIdentifier` names, so compile the function to run so that it is exported as `main`
(`slangc -entry <function> -stage compute`). A `.slang-module` keeps its reflection and binds
like source, running the function `subIdentifier` names. With reflection, every space and slot
the launch script states must match the shader's, or the node's graph stops with an error naming
both; an offset or strides that differ are logged as a warning, and the shader's are used.

Sources and `asset` value inputs may live beside the scene, inside a `.usdz` package, or
behind a URI the Omniverse client can reach, and the launch script always follows its source;
inside a package the `.lua` goes within the brackets.

Depth: `docs/spg/do/precompiled.rst`, `descriptor_sets.rst`, `docs/spg/ref/usd.rst`.
