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
name: spg
description: >
  Sensor Processing Graphs: run your own GPU code as a pass over RTX render outputs.
  Covers the three-file node contract in CUDA and Slang, wiring a graph in USD, built-in
  nodes, cross-frame state, sensor composites, ray generation, scene queries and
  diagnosis. Use when the user asks to add SPG to a scene, write or debug an SPG node or
  launch script, work with `.cu.lua` or `.slang.lua`, author `info:spg:sourceAsset`,
  `omni:rtx:aov`, `orderedVars` or a `spg:` built-in node, post-process an AOV on the GPU,
  read a lidar or radar point cloud in a kernel, trace the scene from a node, or work out
  why an SPG output is empty or black.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - spg
  - cuda
  - slang
  - usd
tools:
  - Read
  - Grep
  - Shell
  - Edit
  - Write
---

# Sensor Processing Graphs

## When to Use

Any task where the user's own GPU code has to run inside the renderer, over the images or
sensor data the renderer produces. Trigger vocabulary: SPG, `.cu.lua`, `.slang.lua`,
`info:spg:sourceAsset`, `subIdentifier`, `omni:rtx:aov`, `orderedVars`, `cuda.kernel`,
`slang.dispatch`, `spg:rtx.spg.stdlib/...`, "post-process the AOV", "custom kernel on the
render output", "my SPG AOV is black".

Not this skill: reading a finished AOV back on the host. Use `reading-render-output`.

## Task → Sections

Read **The Model**, **Instructions** and **The Traps** for any task. Then only what the row names.

| The user asks for | Also read |
|---|---|
| A new node that transforms an AOV | The Three Files, Choosing a Backend, Values, Resources, Launch Geometry |
| Wiring an existing node into a scene | Wiring the Graph |
| A common operation with no code | Built-In Nodes |
| A node that remembers a previous frame | Cross-Frame State |
| Data built in Lua on the GPU | Uploading Data |
| Retuning a value without reloading | Runtime Changes |
| Lidar or radar point cloud input | Sensor Composites |
| A node that traces the scene | Ray Generation |
| Pre-compiled `.ptx` / `.slang-module` / `.spv` | Pre-Compiled Sources |
| An output that is empty, black or wrong | Troubleshooting |

## Prerequisites

- ovrtx 0.4 or later. SPG is enabled by default.
- The user can already render: a stage, a RenderProduct with a camera, and a step loop.
- Slang nodes need the renderer on Vulkan, which is the ovrtx default on Linux and Windows.
- Proficiency with CUDA kernels or Slang/HLSL compute shaders, and with USD authoring, is
  assumed. This skill maps those onto SPG rather than teaching them.

## Inputs

The user's scene file, their kernel if they have one, and which backend they want. If they
have not said, choose by what the node needs: **Choosing a Backend**.

**Every `examples/` and `docs/` path below is relative to the ovrtx public root**:
`rendering/ovrtx/public/` in the kit repository, the package root in an installed ovrtx.

Precedence when facts conflict: the code under `examples/python/spg-*` first, then the pages
under `docs/spg/`, then this skill. Every code reference below names a snippet marker in a
runnable example. Read the file between the markers rather than relying on memory; this skill
is not the source of truth for API shape. Markers are paired comments carrying the name:

    // [snippet:grayscale-kernel-template]   ... // [/snippet:grayscale-kernel-template]

`//` in `.cu` and `.slang`, `--` in `.lua`, `#` in `.py` and `.usda`. Conventions in
`skills/README.md`.

## The Model

SPG runs a directed graph of GPU nodes inside the renderer's frame, over its Arbitrary Output
Variables (AOVs). Everything stays on the GPU.

**A node is three files that share a name**: the GPU code, `Kernel.cu` or `Kernel.slang`; the
launch script beside it, `Kernel.cu.lua` or `Kernel.slang.lua`, which validates inputs,
describes outputs and returns the launch configuration; and the USD shader definition,
`Kernel.usda`, which declares the ports and points at the GPU source.

Three facts drive most mistakes:

1. **The launch script is found by appending `.lua` to the source asset path**, and cannot be
   redirected. `GrayscaleKernel.cu` pairs with `GrayscaleKernel.cu.lua`.
2. **The launch script runs once per rendered frame**, on the CPU, before the GPU work, and
   sees resource *descriptors* — shape, dtype, rank — never pixel or point *data*.
3. **Execution is driven backwards from what is asked for.** A node whose output nothing
   consumes and which publishes no RenderVar never runs at all.

## Instructions

1. **Decide built-in or custom.** If a stdlib node covers the operation, author only a USD
   Shader prim and write no code: **Built-In Nodes**. Do not invent node IDs.
2. **Write the GPU code**, one entry point, named the same in all three files and `extern "C"`
   on CUDA so the symbol survives.
3. **Write the launch script**, one global Lua function of that name taking
   `(inputs, outputs)`, assigning a descriptor to every declared output and returning a launch
   configuration.
4. **Write the shader definition**: `info:implementationSource = "sourceAsset"`,
   `info:spg:sourceAsset` at the GPU file, `subIdentifier` naming the entry point, and one
   `opaque inputs:`/`outputs:` port per resource. Details in **The Three Files**.
5. **Wire it into the scene**: **Wiring the Graph**.
6. **Verify by content, not by exit code.** A node that never ran leaves an AOV of zeros, so a
   clean run proves nothing. Assert something only your node could have produced, as every
   `spg-*` example's `README.md` does. If you cannot run anything, hand the user the command
   and the check rather than reporting the work as verified.

The smallest complete node, in all three files:

> **Source (kernel):** `examples/python/spg-grayscale/GrayscaleKernel.cu` snippet `grayscale-kernel-template`
> **Source (launch script):** `examples/python/spg-grayscale/GrayscaleKernel.cu.lua` snippet `grayscale-launch-template`
> **Source (shader definition):** `examples/python/spg-grayscale/GrayscaleKernel.usda` snippet `shader-definition-template`
> **Source (scene):** `examples/python/spg-grayscale/grayscale_scene.usda` snippet `render-graph`

## The Three Files

**The entry-point name appears three times and must match exactly**: the GPU source's function,
the launch script's global function, and `subIdentifier` in USD, which falls back to the Shader
prim's own name when absent.

**Ports are declared in USD and keyed by name in Lua**, with the `inputs:` scope stripped, so
`inputs:LdrColor` arrives as `inputs["LdrColor"]`. A **resource port** is `opaque inputs:X` or
`opaque outputs:Y` and carries an AOV or a buffer another node produced. A **value input** is a
typed attribute, `float inputs:strength`, carrying a number, vector, matrix, token or asset.

**A resource is described by `shape`, `rank` and `dtype`.** A dtype is a value taken from the
`cuda` or `slang` table, not a type name: `cuda.uchar4` is four unsigned 8-bit numbers, so one
RGBA pixel. It compares, `inputs["Image"].dtype == cuda.uchar4`, and it is callable to wrap a
value, `cuda.int(42)`.

**Shapes are height-first.** `shape[1]` is height and `shape[2]` is width, while
`cuda.image(width, height, dtype)` takes width first. That reversal is the most common
cause of a transposed or wrongly proportioned result.

**Every declared output must be assigned a descriptor** before the launch script returns, or
it is never backed and the node has nothing to write into.

## Choosing a Backend

CUDA and Slang are the same shape: same three files, same ports, same launch-script contract.
They differ in how the GPU code receives things.

| | CUDA | Slang |
|---|---|---|
| Values arrive | as individual kernel arguments, matched by position | packed into one constant buffer, read through a `ParameterBlock` |
| Resources arrive | as `cudaTextureObject_t` / `cudaSurfaceObject_t` / raw pointers | bound by declared type: `Texture2D`, `RWTexture2D`, `StructuredBuffer` |
| Splitting across files | not possible — one translation unit against a single include directory (`CUDA_PATH`/`CUDA_HOME`, else the bundled headers), never the `.cu`'s own | `import MyModule;` resolves beside the shader |
| 64-bit integers | work | do not; the Vulkan `shaderInt64` feature is off |
| Ray generation | not available | available |

The same node in both, to compare directly:

> **Source (CUDA):** `examples/python/spg-pipeline/InvertKernel.cu.lua` snippet `invert-launch`
> **Source (Slang):** `examples/python/spg-pipeline/InvertKernel.slang.lua` snippet `invert-slang-launch`

## Values

Declare a typed attribute on the shader definition; a scene instance may override it.

> **Source (USD):** `examples/python/spg-pipeline/InvertKernel.usda` snippet `invert-shader-definition`

**A value input is a wrapper, not a number.** Arithmetic on `inputs["strength"]` raises. Pass
it through a dtype constructor to hand it to the GPU, or read `.value` to compute with it in
Lua.

**A vector is not a scalar on CUDA.** Scalars pass by value, but a `float3`, a matrix or a
quaternion is bound with `cuda.array` and arrives as a pointer to its components; passing one
by value gives a correct first component and garbage after it. On Slang every value goes into
the parameter block.

**Two traps in the type mapping.** A quaternion is written `(w, x, y, z)` in USDA and arrives
as `(x, y, z, w)`. A `token` arrives as a null-terminated `char` array and an `asset` as the
file's raw bytes, so both are bound with `array`, not a scalar constructor.

Depth, including every USD type SPG reads: `docs/spg/ref/usd.rst` and `docs/spg/do/values.rst`.

## Resources

**Backing is fixed when a resource is created.** `image` asks for a texture, `empty` for a
buffer, and the binder used later has to agree. A texture has one, two or three dimensions;
anything else is buffer-backed.

**On Slang the binder must match how the shader declares the parameter.** The binders check
rank, direction, backing and buffer kind in Lua before anything reaches the GPU, naming the
port.

**A `uchar4` texture is normalised**, alone among the 8-bit element types, so Slang writes
`float4` in 0..1 with hardware rounding while CUDA writes raw bytes. The same colour can land
one least-significant bit apart on the two backends; where a test must match byte for byte,
pick colours exact in 8 bits.

Texture in and texture out, then buffers and textures mixed in one bind list:

> **Source (CUDA):** `examples/python/spg-grayscale/GrayscaleKernel.cu.lua` snippet `grayscale-launch-template`
> **Source (Slang):** `examples/python/spg-grayscale/GrayscaleKernel.slang.lua` snippet `grayscale-slang-launch-template`
> **Source (mixed):** `examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua` snippet `histogram-binding`

Depth: `docs/spg/do/textures_buffers.rst`.

## Launch Geometry

**Both keys are optional and SPG derives them.** Left out, the geometry comes from the first
output's shape: one thread per element. On CUDA the derived block is 16 x 16 x 1, or
256 x 1 x 1 for a rank-1 resource.

**On Slang, `numthreads` states the group size the shader was compiled with**, so SPG can divide
the output's shape into groups. It is for a `.spv`, which carries no reflection; nothing compares
it against the byte code, so a value that differs mis-covers the output. A shader that declares
`[numthreads]` supersedes it, logged at INFO level and so invisible by default.

**State the geometry when the iteration domain is not the output.** A kernel whose threads
walk a buffer, or take one thread per column rather than per pixel, must say so. Round up
when dividing, or the last partial group never launches and the far edge is never written.
Both cases, one pass stating nothing and one stating the domain:

> **Source (derived):** `examples/python/spg-blur/BlurKernel.cu.lua` snippet `blur-horizontal-launch`
> **Source (stated):** `examples/python/spg-blur/BlurKernel.cu.lua` snippet `blur-vertical-launch`

Depth: `docs/spg/do/launch_geometry.rst`.

## Wiring the Graph

A graph is authored under a RenderProduct: a RenderVar names an AOV, `orderedVars` lists what
the product produces, and a shader-to-shader connection chains two nodes without publishing
what passes between them.

> **Source (publishing):** `examples/python/spg-grayscale/grayscale_scene.usda` snippet `render-graph`
> **Source (chaining):** `examples/python/spg-pipeline/pipeline_scene.usda` snippet `render-graph`
> **Source (no input):** `examples/python/spg-generate/CheckerKernel.cu.lua` snippet `checker-launch`

**Order comes from connections, not from `orderedVars`.** SPG runs nodes in topological order
over the edges the connections create, so an unpublished intermediate stays inside the graph
and is unreadable from the host. That is the default; publishing is the deliberate act.

**Publishing needs both parts**: a `sourceName`, which registers the name, and the connection.
A RenderVar with only one produces nothing. Under a name the renderer already produces it
overwrites in place, which downstream consumers pick up unknowingly.

**Fan-out and fan-in are ordinary connections**, but a node output binds to one RenderVar at a
time, and a node cannot read an AOV and republish under that same name in one product.

**A node needs no input at all.** With no resource port it generates its output from authored
values, and must state its own size because nothing hands it a shape.

Depth: `docs/spg/do/chaining.rst`, `split_join.rst`, `aovs.rst`, `products.rst`, `generate.rst`.

## Built-In Nodes

Named rather than sourced: no GPU file and no launch script, just
`info:implementationSource = "id"` and `info:id = "spg:<node-id>"`.

> **Source:** `examples/python/spg-builtin-nodes/stdlib_scene.usda` snippet `render-graph`

The four that exist:

| `info:id` | Ports | Operation |
|---|---|---|
| `spg:rtx.spg.stdlib/Add` | `A`, `B` → `Result` | Element-wise add; uint8 saturates |
| `spg:rtx.spg.stdlib/Multiply` | `A`, `B` → `Result` | Element-wise multiply; uint8 normalised |
| `spg:rtx.spg.stdlib/Scale` | `Input`, `scaleX`, `scaleY` (0.5) → `Output` | Nearest-neighbour resize |
| `spg:rtx.spg.stdlib/Swizzle` | `Input`, `swizzle` (`"xyzw"`) → `Output` | Per-channel routing |

That is the complete standard library and the whole of the published surface. Other renderer
components register nodes into the same registry under their own prefix, so an `info:id`
outside this table may still resolve; treat anything else as internal and unsupported. These
four take 2D textures only and refuse integer formats. A built-in is the whole node: the moment
you need something it does not do, you are writing a node.

Depth: `docs/spg/ref/builtin_catalogue.rst`.

## Cross-Frame State

Two mechanisms, differing in who owns the data.

**A stateful output is the node's own resource**, handed back to it next frame instead of a
fresh one. Mark it with a trailing `cuda.stateful` / `slang.stateful` on the allocation. It is
zero-initialised on first use and needs no RenderVar.

**A previous-frame read is an AOV**, so any node connected to it sees the same history. Suffix
a RenderVar's `sourceName` with `:-N`, for N from 1 to 8. Nothing on the node says anything
about time; that follows from what the scene connects it to.

> **Source (stateful, CUDA):** `examples/python/spg-stateful/TrailKernel.cu.lua` snippet `trail-alloc`
> **Source (stateful, Slang):** `examples/python/spg-stateful/TrailKernel.slang.lua` snippet `trail-slang-alloc`
> **Source (previous frame):** `examples/python/spg-previous-frame/motion_scene.usda` snippet `render-graph`

An unrecognised suffix is not an error: it leaves the name unchanged and reads the live AOV
under that literal name, which looks like the feature silently not working.

Depth: `docs/spg/do/state.rst`, `previous_frame.rst`.

## Uploading Data

`array` takes a Lua table and a dtype and creates a device buffer, or uploads an `asset` value
input's raw bytes; `zeros`, `ones` and `full` fill one without Lua data.

**An `asset` file is resolved exactly as the GPU source is**, so it may sit beside the scene,
inside a `.usdz` package, or behind a URI the Omniverse client can reach.

**Wrap the construction in `static`** so it is built once rather than on every frame, since
the launch script runs per frame under an instruction budget.

> **Source (CUDA):** `examples/python/spg-blur/BlurKernel.cu.lua` snippet `blur-weights`
> **Source (Slang):** `examples/python/spg-blur/BlurKernel.slang.lua` snippet `blur-slang-weights`

`static` caches the Lua work, not the GPU upload: the bytes are copied again each frame. For a
filter kernel that costs nothing measurable, so size a design around the Lua saving rather than
the transfer.

Depth: `docs/spg/do/upload_data.rst`, `caching.rst`.

## Runtime Changes

A value input is addressable on the Shader prim by its USD name. Write it, publish the edit
by advancing the write floor, then step.

> **Source:** `examples/python/spg-blur/main.py` snippet `blur-write-radius`

**An unconnected input takes effect on the next step**, with no reset. **A connected input
ignores a direct write**: the connection is the source, so the write succeeds and changes
nothing; write the source attribute instead and reset the renderer. Each node carries its own
copy, so retuning two nodes means writing both.

Depth: `docs/spg/do/runtime_changes.rst`.

## Sensor Composites

A lidar or radar publishes a **composite**: several named channels under one render var rather
than the single image a camera AOV gives. The node's port is declared like any other, and
nothing on the shader side says "composite".

> **Source (launch script):** `examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua` snippet `histogram-launch`
> **Source (scene):** `examples/python/spg-composite-aov/lidar_scene.usda` snippet `lidar-render-graph`

Test `inputs["X"].isComposite` first — it is the only way to tell the two shapes apart, and a
node written for one will not work on the other. Then take channels from `.tensors[name]` and
scalars from `.params[name]`, with `.channelNames` saying what this render var carries. A
render var with no `channels` authored is not a composite: it binds as a one-dimensional
`uchar` buffer of raw bytes.

**Bound the work by the count channel.** Point channels are allocated for the worst case and
only the first `Counts[0]` entries hold a return. The launch script sees descriptors, not data,
so pass `Counts` to the GPU and apply the bound there. `Coordinates` is `[3, Nmax]` — all x,
then all y, then all z — so the stride between runs is the capacity, not the count.

Do not branch on `.status`: it reports what the render output said when the launch script ran,
and reads `"empty"` on every frame of the working example while the channels carry a full sweep.

Depth: `docs/spg/do/composites.rst`.

## Ray Generation

Slang only. The entry point is `[shader("raygeneration")]` and the launch script returns
`slang.rayQuery` or `slang.traceRays` in place of `slang.dispatch`. Either way the ray grid is
the output's shape, one invocation per element, so there is no `numthreads`.

`slang.rayQuery` traverses and shades inline in the ray-generation shader and needs nothing
else. `slang.traceRays` drives a pipeline with a shader binding table, so shading moves into
one `miss` and one hit group in the same file, named by the extra launch fields `miss`, `hit`,
`payloadSize` and `attributeSize`.

> **Source (inline):** `examples/python/spg-raygen/RaygenCornellBox.slang.lua` snippet `raygen-launch`
> **Source (pipeline):** `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang.lua` snippet `pipeline-launch`

A shader under a RenderProduct is given the scene acceleration structure and its camera with
**no authored input and no connection**: bind it with `slang.binding("scene", inputs["scene"])`
and place rays with the `sceneTransform` value input rather than assuming world coordinates.
Exactly one hit group is supported, `payloadSize` and `attributeSize` are byte counts you work
out yourself, and a `.spv` cannot be used on a ray-tracing stage.

**No geometry is exposed.** A hit yields distance and the surface's instance and primitive
index, and nothing else, so the example recovers geometric normals from two extra probe rays.

Depth: `docs/spg/do/raygen.rst`.

## Pre-Compiled Sources

The extension on `info:spg:sourceAsset` decides what happens: CUDA takes `.cu`, `.ptx`,
`.cubin` and `.fatbin`, Slang takes `.slang`, `.slang-module` and `.spv`. The launch script is
still required and still found by appending `.lua`, and a CUDA entry point must be `extern "C"`
so the symbol is findable in the artifact.

A `.spv` carries no reflection at all: the descriptor space, the binding slots, the
parameter-block offsets and the thread group size all have to be stated in the launch script,
and it cannot be used on a ray-tracing stage. A `.slang-module` keeps its reflection and binds
like source.

Sources and `asset` value inputs may live beside the scene, inside a `.usdz` package, or
behind a URI the Omniverse client can reach, and the launch script always follows its source;
inside a package the `.lua` goes within the brackets.

Depth: `docs/spg/do/precompiled.rst`, `descriptor_sets.rst`, `docs/spg/ref/usd.rst`.

## The Traps

These bite across every task, and each produces a plausible result rather than an error.

1. **Shapes are height-first**, while the `image` constructors take width first.
2. **Argument order is unchecked.** CUDA `args` is matched against the C signature by
   position and a mismatch is not diagnosed: the kernel reads whatever occupies that slot.
3. **A value input is a wrapper**, so arithmetic on it raises. Use `.value`.
4. **The launch script has a fixed VM instruction budget**, about a thousand, renewed each
   frame and not adjustable. Loops over attributes or large tables exceed it and fail the node
   with an execution-limit error. Build assert messages as plain literals, since a concatenated
   message costs its instructions whether or not it fires.
5. **The sandbox scans the script's text before running it**, as a plain substring match
   over the whole file including comments. A comment mentioning a forbidden construct is
   enough to reject the script, which surfaces as an output that is never written.
6. **`info()` and `print()` are invisible at the default log level.** Use `warning()` when
   you need to see something.
7. **A rejected or never-scheduled node leaves zeros and exits 0.** Never take a clean run
   as evidence.

## Output Format

State which of the three files you changed and why. Show the entry-point name and confirm it
matches in all three. If you added a port, say whether it is a resource port or a value
input. Name the check that proves it worked, and what its failing value would look like.

## Scripts

This skill has no scripts. Every `spg-*` example runs itself with `uv run main.py`, as its
`README.md` states.

## Limitations

- No geometry, materials or vertex data reach a node, including a ray-generation node.
- No node reaches the CPU mid-frame, and no launch script reads pixel or point data.
- A launch script cannot read the scene: no prim attributes, no camera transform, no product
  layout. A node gets what its ports carry and its authored value inputs.
- A shader output binds to one RenderVar at a time; a node cannot read an AOV and republish
  under that same name in one product.
- Previous-frame reads reach 8 frames back.
- A cross-product read can be one frame stale when the consuming product renders first.
- SPG Shader prims must not sit under a `Material` prim, and shaders under an instance
  prototype are ignored.
- Slang has no 64-bit integers, CUDA cannot ray-generate or split across files, and the
  built-in nodes take 2D textures only and refuse integer formats.

## Troubleshooting

Start from what was observed. Full index: `docs/spg/diagnose/symptoms.rst`.

| Symptom | Most likely cause |
|---|---|
| Output empty or black | The node never ran: its output is consumed by nothing and publishes no RenderVar |
| Output empty, scene looks right | The RenderVar has a connection but no `sourceName`, or the name collides with a built-in AOV that shadows it |
| Output empty, node looks right | The launch script was rejected by the sandbox scan, an output was never assigned a descriptor, or the shader sits under a `Material` or instanceable prim and is ignored |
| Wrong pixels rather than none | Argument or bind order does not match the GPU code, or the shape order is reversed |
| First component right, rest garbage | A vector was passed by value on CUDA instead of with `cuda.array` |
| A band or corner unwritten | The grid is too small; round up when dividing the domain by the block |
| Node fails, log names `numthreads` | A `.spv` with no thread group size from either the shader or the script |
| Values right on frame one only | A cache key is changing every frame, often a value input passed as its wrapper |
| Lidar output empty | The sweep returned nothing; check `Counts`, and that motion BVH is enabled |

The renderer writes its log to standard output. Launch-script `warning()` lines appear there
prefixed `Lua:`.

## References

Docs are the depth behind every section here, under `docs/spg/`: `overview.rst` for what SPG
is, `first_node.rst` for one node built from nothing, `do/index.rst` for one page per task,
`ref/index.rst` for every Lua function and USD attribute, and `diagnose/index.rst` for the
symptom index and the limitations.

Runnable examples, each self-checking: `spg-grayscale` (smallest node), `spg-pipeline`
(chaining, value inputs), `spg-builtin-nodes`, `spg-generate` (no input), `spg-blur` (uploads,
caching, launch geometry, runtime changes, fan-out), `spg-stateful`, `spg-previous-frame`,
`spg-composite-aov`, `spg-raygen`.

Related skills: `reading-render-output` for getting an AOV back on the host, `loading-usd` and
`stepping-and-rendering` for the surrounding loop, `cuda-interop` for sharing GPU memory.
Editor support: type stubs in `docs/spg/.luarc/`, wired up as `docs/spg/ref/lua_contract.rst`
describes.
