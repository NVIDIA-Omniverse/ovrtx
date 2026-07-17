---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
name: spg-usd-lua-authoring
description: >
  Authoring, reviewing, and fixing RTX Sensor Processing Graphs (SPG) defined
  across CUDA kernels, Lua launch scripts, shader USDA files, and scene
  RenderProduct wiring. Use when the user asks to write or debug SPG source-asset
  shaders, info:spg:sourceAsset/subIdentifier binding, Lua cuda.kernel args,
  opaque AOV ports, typed value inputs, RenderVar/orderedVars connections,
  shader chaining, or built-in rtx.spg factory/stdlib nodes.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - spg
  - cuda
tools:
  - Read
  - Grep
  - Write
  - Edit
---

# SPG USD/Lua Authoring

## When to Use

Use this skill when the user asks to author, review, or fix RTX Sensor Processing Graphs (SPG) in USD, CUDA, or Lua: `info:spg:sourceAsset`, `info:id = "spg:..."`, `subIdentifier`, `opaque` AOV ports, `RenderProduct` / `RenderVar` / `orderedVars` wiring, typed value inputs, shader chaining, or `cuda.kernel` launch scripts.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target artifact: CUDA kernel, `.cu.lua` launch script, reusable shader `.usda`, scene wiring `.usda`, or built-in factory node.
- AOV/resource inputs and outputs, including shape, dtype, and whether each resource is an image or buffer.
- Value inputs and their USD types (`int`, `float`, `bool`, vectors, matrices, quaternions, `token`) plus defaults or scene overrides.
- RenderProduct path, camera, resolution, RenderVars, final output AOVs, and any shader-to-shader dependencies.
- Public docs and example snippets referenced below. Treat these as the source of truth.

## Prerequisites

- Use an ovrtx public checkout that contains the SPG docs and examples under `docs/spg` and `examples/python/spg-*`.
- Read the relevant public docs/example asset before writing or explaining SPG usage; do not rely on memory for port names or Lua wrapper behavior.
- Use the public Lua API annotations in `docs/spg/.luarc/cuda.lua` and `docs/spg/.luarc/globals.lua` for exact `cuda.*` wrappers, dtypes, resource descriptors, and sandbox globals.
- SPG custom source-asset nodes use a `.cu` CUDA source file, a matching Lua sidecar, and a reusable `.usda` shader definition. The `.lua` file must live next to the `.cu` file and be named by appending `.lua` (`GrayscaleKernel.cu` -> `GrayscaleKernel.cu.lua`).
- Built-in factory nodes use `info:implementationSource = "id"` and need no `.cu` or `.cu.lua`.
- End-to-end runtime validation requires an RTX-capable GPU. Docs-only validation does not exercise NVRTC or graph execution.

## Instructions

1. Identify whether a built-in factory node already covers the operation. Check the built-in nodes section of `docs/spg/index.rst` first, then the public built-in-node example `examples/python/spg-builtin-nodes/stdlib_scene.usda`. If a documented node covers the task, author only the USD Shader with `info:implementationSource = "id"` and `info:id = "spg:<node-id>"`. Do not invent unlisted node IDs.
2. Read the closest public example or docs section before editing. Prefer the grayscale, pipeline, and built-in-node examples for concrete patterns.
3. For custom CUDA nodes, keep the three-file contract intact: `.cu` CUDA source, matching `.cu.lua` launch script sidecar, and reusable `.usda` shader definition.
4. Make the name binding explicit. `info:spg:sourceAsset:subIdentifier` must match the `extern "C" __global__` kernel function and the Lua launch function.
5. In Lua, validate resource shape/dtype, allocate every output, and return `cuda.kernel({ args = ..., block = ..., grid = ... })`. Keep `args` in the exact order and type expected by the C signature. If a wrapper, dtype, descriptor field, or global is uncertain, check `docs/spg/.luarc/cuda.lua` and `docs/spg/.luarc/globals.lua`.
6. In USD scene wiring, trace from final RenderVars backward: output RenderVars connect to shader outputs, shader inputs connect to source AOVs or upstream shader outputs, and every produced or consumed RenderVar is listed in `orderedVars`.
7. Do not nest SPG Shader prims under a `Material` prim. Author them under a plain scope or under the RenderProduct/Post-processing scope used by the scene.
8. When changing code, run the narrow SPG test or example scene whenever practical. If runtime validation is not possible, state that runtime execution was not run.

## Output Format

- For explanations, cite the relevant SPG attributes, file roles, and source snippets.
- For code changes, summarize the changed `.cu` CUDA source, matching `.cu.lua` sidecar, shader `.usda`, and scene `.usda` files plus the cross-file invariants preserved.
- For validation, report the exact test, scene load, or static check run. If not run, explain the missing prerequisite.

## Scripts

This skill has no scripts.

## Limitations

- The referenced public docs and examples remain the source of truth; update tested assets or docs before documenting new SPG behavior.
- SPG standard library nodes operate on 2D textures only; integer texture formats and buffer-backed resources are not supported by those nodes.
- Public SPG examples are expected to run successfully. Static docs or USDA checks only validate syntax/composition; runtime execution on an RTX-capable GPU validates CUDA compilation, Lua launch execution, resource binding, and graph output.
- A shader node output can be bound to only one RenderVar at a time. Do not connect two RenderVars to the same `Shader.outputs:*` port.
- Cross-product reads can be one frame stale when a consumer product renders before the producer; affected outputs converge after the dependency has rendered.

## Source Map

Read these local sources before reusing patterns:

| Need | Source |
|------|--------|
| Conceptual overview | `docs/spg/index.rst` |
| Custom CUDA shader authoring | `docs/spg/index.rst`, `examples/python/spg-grayscale/GrayscaleKernel.*` |
| Scene RenderProduct/RenderVar wiring | `docs/spg/index.rst`, `examples/python/spg-grayscale/grayscale_scene.usda`, `examples/python/spg-pipeline/pipeline_scene.usda` |
| Value inputs and cached Lua setup | `docs/spg/index.rst`, `examples/python/spg-pipeline/InvertKernel.cu.lua`, `examples/python/spg-pipeline/InvertKernel.usda` |
| Exact Lua API annotations | `docs/spg/.luarc/cuda.lua`, `docs/spg/.luarc/globals.lua` |
| Built-in factory nodes | `docs/spg/index.rst`, `examples/python/spg-builtin-nodes/stdlib_scene.usda` |
| End-to-end Python usage | `examples/python/spg-grayscale/main.py`, `examples/python/spg-pipeline/main.py` |

## Overview

SPG runs custom GPU post-processing over RTX render outputs (AOVs). A custom node has three layers:

| File | Role |
|------|------|
| `.cu` | CUDA source compiled by NVRTC. |
| `.cu.lua` | Lua launch script sidecar that validates inputs, allocates outputs, and returns launch configuration. |
| `.usda` | Reusable Shader definition that declares ports and points at the source asset. |

The scene file instantiates or references the Shader under a RenderProduct, connects AOV resources to `inputs:*`, connects final `outputs:*` to RenderVars, and lists active RenderVars in `orderedVars`.

## Minimal Templates

These templates are derived from the public grayscale example. Preserve the cross-file names unless you intentionally rename all corresponding CUDA, Lua, USD, and scene references together.

### CUDA Kernel Template

> **Source:** `examples/python/spg-grayscale/GrayscaleKernel.cu` snippet `grayscale-kernel-template`

### Lua Launch Template

> **Source:** `examples/python/spg-grayscale/GrayscaleKernel.cu.lua` snippet `grayscale-launch-template`

### Shader Definition Template

> **Source:** `examples/python/spg-grayscale/GrayscaleKernel.usda` snippet `shader-definition-template`

### Scene Wiring Template

> **Source:** `examples/python/spg-grayscale/grayscale_scene.usda` snippet `render-graph`

## Cross-File Contract

For source-asset SPG nodes, validate the CUDA, Lua, shader `.usda`, and scene `.usda` together. Do not review any one file in isolation.

### Entry Point Name

The same entry point name must appear in all three shader files:

| Layer | Required form |
|-------|---------------|
| CUDA | `extern "C" __global__ void grayscale(...)` |
| Lua | `function grayscale(inputs, outputs)` |
| Shader `.usda` | `uniform token info:spg:sourceAsset:subIdentifier = "grayscale"` |

If any one of these names differs, SPG cannot bind the launch script and compiled kernel correctly.

### Signature and Lua Args

The Lua `cuda.kernel({ args = { ... } })` list must match the CUDA entry point parameters exactly. Binding is positional, not by C parameter name.

For each CUDA parameter, verify:

- The Lua `args` entry appears in the same order.
- The wrapper maps to the expected C type: `cuda.int(...)` for `int`, `cuda.float(...)` for `float`, `cuda.TextureObject(...)` for `cudaTextureObject_t`, `cuda.SurfaceObject(...)` for `cudaSurfaceObject_t`, and `cuda.array(...)` for raw device pointers. Check `docs/spg/.luarc/cuda.lua` for the complete public wrapper and dtype list.
- Any resource passed to `cuda.TextureObject(...)`, `cuda.SurfaceObject(...)`, or `cuda.array(...)` has been declared as a shader `opaque` port and connected in the scene if it is an input.
- Any output resource passed to the kernel is allocated in `outputs[...]` before the return.

### Shader Ports and Lua Keys

Shader `.usda` port names are the Lua table keys with the `inputs:` / `outputs:` prefix removed:

| Shader definition | Lua key |
|-------------------|---------|
| `opaque inputs:LdrColor` | `inputs["LdrColor"]` |
| `opaque outputs:LdrGrayscale` | `outputs["LdrGrayscale"]` |
| `float inputs:strength` | `inputs["strength"]` |

Use `opaque inputs:*` and `opaque outputs:*` only for AOV/resource ports. Use typed `inputs:*` for scalar, vector, matrix, quaternion, and token value inputs.

### Source Asset and Sidecar

- `info:spg:sourceAsset` is relative to the shader definition file.
- SPG locates the launch script by appending `.lua` to the `info:spg:sourceAsset` path.
- The `.lua` sidecar must live next to the `.cu` file named by `info:spg:sourceAsset`.
- Example: `GrayscaleKernel.cu` expects `GrayscaleKernel.cu.lua`.

## Scene Wiring Contract

A scene instance wires the reusable shader into a RenderProduct. Validate from the final output backward.

SPG evaluates only the shader subgraphs needed to produce RenderVars listed in `orderedVars`. Authoring a Shader prim is not enough to make it run; its output must feed a RenderVar requested by `orderedVars`, or feed another shader that eventually does.

### Final Output RenderVar

The final output RenderVar must:

- Set `uniform string sourceName = "<OutputAovName>"`.
- Connect `opaque omni:rtx:aov.connect = <../Shader.outputs:PortName>` to an existing shader output port.
- Appear in `rel orderedVars`.

### Source RenderVar

Each renderer-produced source AOV consumed by a shader must:

- Set `uniform string sourceName = "<InputAovName>"`.
- Expose `opaque omni:rtx:aov`.
- Appear in `rel orderedVars`.

### Shader Instance

Each shader instance must:

- Reference or define the shader with the expected ports.
- Connect each resource input with `opaque inputs:PortName.connect = <../RenderVar.omni:rtx:aov>` or to an upstream shader output.
- Override typed value inputs only with matching USD types.

### Chaining and Intermediate AOVs

- Shader-to-shader chaining should connect output to input directly: `opaque inputs:Image.connect = <../PreviousShader.outputs:Result>`.
- Do not add an intermediate RenderVar unless the intermediate AOV must be read, displayed, or published.
- If an intermediate RenderVar is added, give it `sourceName`, connect it to the upstream shader output, and add it to `orderedVars`.
- Do not connect multiple RenderVars to the same shader output. If two published AOVs are needed, author distinct shader outputs or distinct node instances.
- Shader execution order comes from the connection graph, not the order of `orderedVars`.

## Static Validation Checklist

Before runtime validation:

1. Find the CUDA entry point and record its name and parameter list.
2. Confirm `info:spg:sourceAsset:subIdentifier` uses the same name.
3. Confirm the Lua launch function uses the same name.
4. Compare CUDA parameters against Lua `args` line by line for count, order, and wrapper type.
5. Confirm every Lua `inputs["X"]` and `outputs["Y"]` resource key has a matching shader `.usda` port.
6. Confirm every scene connection targets an existing shader port.
7. Confirm every active source or final output RenderVar appears in `orderedVars`.
8. Confirm each shader chain reaches at least one RenderVar listed in `orderedVars`; otherwise that subgraph is not requested for execution.
9. Confirm output resources are allocated in Lua before they are wrapped as kernel arguments.

## Built-in Factory Nodes

Built-in SPG nodes are authored entirely in USD:

> **Source:** `examples/python/spg-builtin-nodes/stdlib_scene.usda` snippet `render-graph`

Common IDs are:

| `info:id` | Inputs | Output | Notes |
|-----------|--------|--------|-------|
| `spg:rtx.spg.core/NoOp` | `Input` | `Output` | Passthrough. |
| `spg:rtx.spg.stdlib/Add` | `A`, `B` | `Result` | Same dimensions and format; uint8 saturates. |
| `spg:rtx.spg.stdlib/Multiply` | `A`, `B` | `Result` | Same dimensions and format; uint8 is normalized by 255. |
| `spg:rtx.spg.stdlib/Scale` | `Input`, `scaleX`, `scaleY` | `Output` | Nearest-neighbor resize; dimensions may change. |
| `spg:rtx.spg.stdlib/Swizzle` | `Input`, `swizzle` | `Output` | Channel routing with selectors `x`, `y`, `z`, `w`, `0`, `1`. |

Use the `spg:` prefix for new scenes. Older scenes may use bare IDs, but new authoring should keep SPG IDs scoped.

## Lua Sandbox

SPG launch scripts run in a restricted Lua 5.4 sandbox with bounded memory and instruction count. Only small validation, output allocation, and launch-table construction belong in Lua; heavy work belongs in CUDA.

- File-system, package-loading, debug, coroutine, protected-call, metatable, raw table, and environment APIs are unavailable or rejected.
- Forbidden-token checks apply to the full source text, including comments and strings. Keep comments and identifiers clear of blocked API names.
- The default sandbox limits are documented in `docs/spg/index.rst`; the available sandbox globals are annotated in `docs/spg/.luarc/globals.lua`.

## Troubleshooting

- **Kernel not found:** check that `subIdentifier`, the CUDA entry point, and the Lua function name are identical.
- **Launch fails or output is corrupt:** compare Lua `args` order and wrappers against the C signature.
- **AOV does not appear:** ensure the RenderVar has `sourceName`, is in `orderedVars`, and either exposes `omni:rtx:aov` or connects `omni:rtx:aov` to a shader output.
- **Lua shape bugs:** remember `shape[1] = height`, `shape[2] = width`; `cuda.image` takes `width, height`.
- **Port binding bugs:** use `opaque` for resource ports and typed attributes for value inputs.
- **Factory node does not resolve:** confirm `info:implementationSource = "id"` and an `info:id` such as `spg:rtx.spg.stdlib/Add`.
- **Sandbox rejection:** check comments and string literals as well as code for blocked Lua APIs.
- **Material interaction issues:** move SPG Shader prims out from under `Material`.

## Related Skills

- `reading-render-output` for mapping an SPG output AOV after rendering.
- `cuda-interop` for CUDA memory and synchronization patterns outside SPG launch scripts.
- `loading-usd` for composing and loading scenes that host RenderProducts.
- `camera-outputs-rt2` for built-in camera AOVs such as `LdrColor` and `HdrColor`.

## References

- `docs/spg/index.rst`
- `docs/spg/.luarc/cuda.lua`
- `docs/spg/.luarc/globals.lua`
- `examples/python/spg-*`
- Keep related skills, SPG docs, and public examples synchronized when changing the workflow.
