---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
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
license: CC-BY-4.0 AND Apache-2.0
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
`slang.compute`, `slang.dispatch`, `spg:rtx.spg.stdlib/...`, "post-process the AOV", "custom
kernel on the render output", "my SPG AOV is black". Not this skill: reading a finished AOV back
on the host, which is `reading-render-output`.

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
| A node that reads its camera, a prim of the scene, or its product | Scene Queries |
| An output that is empty, black or wrong | Troubleshooting |

## Prerequisites

- ovrtx 0.4 or later. SPG is enabled by default.
- A working stage, camera RenderProduct and step loop; Slang requires Vulkan (the default).
- CUDA or Slang/HLSL compute and USD authoring are assumed; this skill maps them onto SPG.

## Inputs

The user's scene file, their kernel if they have one, and which backend they want. If they
have not said, choose by what the node needs: **Choosing a Backend**.

**Every `examples/` and `docs/` path below is relative to the ovrtx public root**:
`rendering/ovrtx/public/` in the kit repository, the package root in an installed ovrtx.

Precedence when facts conflict: the code under `examples/python/spg-*` first, then the pages
under `docs/spg/`, then this skill. Every code reference below names a snippet marker in a
runnable example, a pair of comments `// [snippet:name]` and `// [/snippet:name]` (`--` in
`.lua`, `#` in `.py` and `.usda`); read the file between the markers, not memory.

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
2. **The launch script's function runs once per rendered frame**, on the CPU, before the GPU
   work, and sees resource *descriptors* (shape, dtype, rank), never pixel or point *data*.
3. **Execution is driven backwards from what is asked for.** A node whose output nothing
   consumes and which publishes no RenderVar never runs at all.

## Instructions

1. **Decide built-in or custom.** If a stdlib node covers the operation, author only a USD
   Shader prim and write no code: **Built-In Nodes**. Do not invent node IDs.
2. **Write the GPU code**, one entry point, named the same in all three files and `extern "C"`
   on CUDA so the symbol survives.
3. **Write the launch script**, one global Lua function of that name taking
   `(inputs, outputs)`, assigning a descriptor to every declared output, which is otherwise never
   backed, and returning a launch configuration.
4. **Write the shader definition**: `info:implementationSource = "sourceAsset"`,
   `info:spg:sourceAsset` at the GPU file, `subIdentifier` naming the entry point, and one
   `opaque inputs:`/`outputs:` port per resource. Details in **The Three Files**.
5. **Wire it into the scene**: **Wiring the Graph**.
6. **Verify by content, not by exit code.** A node that never ran leaves an AOV of zeros, so a
   clean run proves nothing. Assert something only your node could have produced, such as
   `R == G == B` in every pixel of a grayscale output. If you cannot run anything, hand the user
   the command and the check rather than reporting the work as verified.

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
`cuda` or `slang` table: `cuda.uchar4` is four unsigned 8-bit numbers, so one
RGBA pixel. It compares, `inputs["Image"].dtype == cuda.uchar4`, and it is callable to wrap a
value, `cuda.int(42)`.

**Shapes are height-first.** `shape[1]` is height and `shape[2]` is width, while
`cuda.image(width, height, dtype)` takes width first. That reversal is the most common
cause of a transposed or wrongly proportioned result.

## Choosing a Backend

CUDA and Slang are the same shape: same three files, same ports, same launch-script contract.
They differ in how the GPU code receives things.

| | CUDA | Slang |
|---|---|---|
| Values arrive | as individual kernel arguments, matched by position | packed into one constant buffer, read through a `ParameterBlock` |
| Resources arrive | as `cudaTextureObject_t` / `cudaSurfaceObject_t` / raw pointers | bound by declared type: `Texture2D`, `RWTexture2D`, `StructuredBuffer` |
| Splitting across files | not possible: one translation unit against a single include directory (`CUDA_PATH`/`CUDA_HOME`, else the bundled headers), never the `.cu`'s own | `import MyModule;` resolves beside the shader |
| 64-bit integers | work | do not; the Vulkan `shaderInt64` feature is off |
| Ray generation | not available | available |

The same node in both, to compare directly:

> **Source (CUDA):** `examples/python/spg-pipeline/InvertKernel.cu.lua` snippet `invert-launch`
> **Source (Slang):** `examples/python/spg-pipeline/InvertKernel.slang.lua` snippet `invert-slang-launch`

## Values

Declare a typed attribute on the shader definition; a scene instance may override it.

> **Source (USD):** `examples/python/spg-pipeline/InvertKernel.usda` snippet `invert-shader-definition`

**A value input is a wrapper, not a number.** Arithmetic on `inputs["strength"]` raises. Pass it
through a dtype constructor to hand it to the GPU, or read `.value` to compute with it in Lua.

**Slang integer fields require matching element widths.** Narrower integers are rejected with
an error naming the value and widths. Use `slang.int` or `slang.uint` for a 32-bit field.

**A numeric vector can pass by value on CUDA.** A dtype constructor passes every component
to a kernel parameter of the matching type and component count. `cuda.array` passes a pointer
to the components instead; use it for matrices or when the kernel expects a pointer. A quaternion
can use a matching four-component dtype constructor or `cuda.array`. On Slang every value goes
into the parameter block.

**An array may hold no elements.** Its `sourceShape[1]` is 0, `cuda.array` gives a null pointer
and a Slang buffer a placeholder, so pass the count to the GPU code and read no element past it.

**Traps in the type mapping.** A quaternion is written `(w, x, y, z)` in USDA and arrives
as `(x, y, z, w)`. A `token` arrives as a null-terminated `char` array and an `asset` as the
file's raw bytes. CUDA passes a token with `array`. A Slang `uint4` field needs token bytes packed
explicitly into four 32-bit words; see `docs/spg/do/values.rst`. Assets use `array` with the dtype
the shader reads. A `token[]` input is
not taken: it keeps the node's graph from being built, with an error naming the node and the input.

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

**`block` and `grid` are optional; SPG derives them.** Left out, the geometry comes from the first
output's shape: one thread per element. On CUDA the derived block is 16 x 16 x 1, or
256 x 1 x 1 for a rank-1 or rank-0 resource.

Without a `block` override, any `blockDimX`, `blockDimY` or `blockDimZ` value input makes the
missing axes default to 1. An explicit launch `block` takes precedence over those inputs.

**On Slang, `numthreads` states the group size a `.spv` was compiled with**, which it does not
reflect; nothing checks it against the byte code, so a wrong value mis-covers the output. A
shader that declares `[numthreads]` supersedes it, logged only at INFO level.

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
over the edges the connections create. An unpublished intermediate stays inside the graph
and is unreadable from the host.

**Publishing needs both parts**: a `sourceName`, which registers the name, and the connection.
A RenderVar with only one produces nothing. Under a name the renderer already produces it
overwrites in place, which downstream consumers pick up unknowingly.

**Fan-out and fan-in are allowed**, but a node output binds to one RenderVar at a
time, and a node cannot read an AOV and republish under that same name in one product.

**A node may have no input at all.** With no resource port it generates its output from authored
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

Other renderer
components register nodes into the same registry under their own prefix, so an `info:id`
outside this table may still resolve; treat anything else as internal and unsupported.

Depth: `docs/spg/ref/builtin_catalogue.rst`.

## Cross-Frame State

**Memory is the node's own resource**, handed back on every run and to nobody else. State it on
`self.memory` with an output's allocator, `self.memory["History"] = cuda.image(...)`, and pass it
with an output's wrapper. SPG zeroes it when it creates it, creates it again zeroed when a launch
describes it otherwise, and leaves it alone when a launch does not state it. It is not a port.

**A stateful output is the node's resource that the scene also reads**: a trailing `cuda.stateful`
/ `slang.stateful` on the allocation, or `self.stateful = true` for every output of the node. Zeroed
and kept as memory is, it stays a port a RenderVar can publish and another node can connect to.

**A previous-frame read is an AOV**, so any node connected to it sees the same history: suffix a
RenderVar's `sourceName` with `:-N`, N from 1 to `/rtx/spg/state/maxPreviousFrameOffset` (8 by
default); further back stops the node's graph. A `:-N` read of a sensor composite gives that frame
as the sensor filled it, and zeros where its history holds none. A suffix that is not a number,
`:-x`, is part of the name and reads the live AOV under it; `:-0` reads the current frame.

> **Source (memory, CUDA):** `examples/python/spg-stateful/TrailKernel.cu.lua` snippet `trail-alloc`
> **Source (memory, Slang):** `examples/python/spg-stateful/TrailKernel.slang.lua` snippet `trail-slang-alloc`
> **Source (previous frame):** `examples/python/spg-previous-frame/motion_scene.usda` snippet `render-graph`

Depth: `docs/spg/do/state.rst`, `previous_frame.rst`.

## Uploading Data

`array` takes a Lua table and a dtype and creates a device buffer, or uploads an `asset` value
input's raw bytes; `zeros`, `ones` and `full` fill one without Lua data.

**An `asset` file resolves as the GPU source does**: beside the scene, in a `.usdz` or at a URI.

**Wrap the construction in `static`** so it is built once rather than on every frame, since
the launch script runs per frame under an instruction budget.

> **Source (CUDA):** `examples/python/spg-blur/BlurKernel.cu.lua` snippet `blur-weights`
> **Source (Slang):** `examples/python/spg-blur/BlurKernel.slang.lua` snippet `blur-slang-weights`

`static` caches the Lua work, for each node that calls it on its own. The GPU upload is
separate: an array whose bytes stay the same from frame to frame stays on the GPU and is not
copied again, whether or not it came from `static`; an array whose bytes change is copied again.
Size a design around the Lua saving rather than the transfer.

An error inside `cuda.static` or `slang.static` fails the launch like any script error.
The failed call stores no result; a later successful call can be cached normally.

Depth: `docs/spg/do/upload_data.rst`, `caching.rst`.

## Runtime Changes

A value input is addressable on the Shader prim by its USD name. Write it, publish the edit
by advancing the write floor, then step.

> **Source:** `examples/python/spg-blur/main.py` snippet `blur-write-radius`

**An unconnected input takes effect on the next step**, with no reset. **A connected input
ignores a direct write**: the connection is the source, so the write succeeds and changes
nothing; write the source attribute instead, which also takes effect on the next step. Each node
carries its own copy, so retuning two nodes means writing both.

Connecting a RenderVar to an existing node's output while the scene runs publishes that
output on the next step. Adding or removing a binding or shader input rebuilds the affected
connected component; writing an existing input's value does not.

Depth: `docs/spg/do/runtime_changes.rst`.

## Sensor Composites

A lidar or radar publishes a **composite**: several named channels under one render var rather
than the single image a camera AOV gives. The node's port is an `opaque` input.

> **Source (launch script):** `examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua` snippet `histogram-launch`
> **Source (scene):** `examples/python/spg-composite-aov/lidar_scene.usda` snippet `lidar-render-graph`

Test `inputs["X"].isComposite` first: it is the only way to tell the two shapes apart, and a
node written for one will not work on the other. Then take channels from `.tensors[name]` and
scalars from `.params[name]`, with `.channelNames` saying what this render var carries. A
lidar or radar `PointCloud` is a composite whether or not `channels` is authored.

**Bound the work by the count channel.** Point channels are allocated for the worst case and
only the first `Counts[0]` entries hold a return. The launch script sees descriptors, not data,
so pass `Counts` to the GPU and apply the bound there. `Coordinates` is `[3, Nmax]`: all x,
then all y, then all z, so the stride between runs is the capacity, not the count.

Do not branch on `.status`: it reports what the render output said when the launch script ran,
and reads `"empty"` on every frame of the working example while the channels carry a full sweep.

Depth: `docs/spg/do/composites.rst`.

## Ray Generation

Slang supports ray generation; CUDA kernels and C++ callbacks reject provider bindings.
Read [Ray generation](references/shader-sources.md#ray-generation) before writing a ray launch or binding the scene.

> **Source (inline):** `examples/python/spg-raygen/RaygenCornellBox.slang.lua` snippet `raygen-launch`
> **Source (pipeline):** `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang.lua` snippet `pipeline-launch`

## Scene Queries

Read the scene through `rtx.product`, `rtx.stage.prim` and `rtx.stage.query_attributes`. Wrong
values without an error: a custom attribute is absent unless the load names its prim, a custom
`string` reads as a number (author a `token`), a world position is at 13 to 15 of a matrix.

> **Source (launch script):** `examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua` snippets `scene-query-camera`, `scene-query-prim`, `scene-query-batch`
> **Source (publish your own prim):** `examples/python/spg-scene-query/main.py` snippet `scene-query-populate`

Depth: `docs/spg/do/scene_queries.rst`, `docs/spg/ref/lua_rtx.rst`.

## Pre-Compiled Sources

Read [Pre-compiled sources](references/shader-sources.md#pre-compiled-sources) when using CUDA binaries,
Slang modules or SPIR-V: the source format determines entry-point, reflection and binding requirements.

## The Traps

These bite across every task.

1. **Shapes are height-first**, while the `image` constructors take width first.
2. **Argument order is unchecked.** CUDA `args` is matched against the C signature by
   position and a mismatch is not diagnosed: the kernel reads whatever occupies that slot.
3. **A value input is a wrapper**, so arithmetic on it raises. Use `.value`.
4. **The launch script has fixed limits**: one million VM instructions and 64 KB of log output
   per call, and 10 MB of memory, not adjustable. Reaching one logs an execution-limit error naming
   the node and stops the node's whole graph. The stopped node retries when one of its own value
   inputs changes or its graph is rebuilt; equal values and another node's edits keep it stopped.
   Heavy work belongs in the GPU code.
5. **The sandbox scans the script's text before running it**, as a plain substring match
   over the whole file including comments. A comment mentioning a forbidden construct is
   enough to reject the script, which surfaces as an output that is never written.
6. **`info()` and `print()` are invisible at the default log level.** Use `warning()` when
   you need to see something.

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
- A launch script reads the scene and cannot write it. Custom attributes arrive only when the
  load names their prim.
- A shader output binds to one RenderVar at a time; a node cannot read an AOV and republish
  under that same name in one product.
- Previous-frame reads reach as far back as `/rtx/spg/state/maxPreviousFrameOffset` allows, 8 by default. An earlier frame of a sensor composite is kept
  only when all its channels are GPU buffers of an element type SPG binds, stored compactly, with no `/` in their names, and a 64-bit composite param, such
  as a lidar's `timestamp`, cannot be read in the launch script.
- A cross-product read can be one frame stale when the consuming product renders first.
- SPG Shader prims must not sit under a `Material` prim, and shaders under an instance
  prototype are ignored.
- Slang has no 64-bit integers, CUDA cannot ray-generate or split across files, and the
  built-in nodes take 2D textures only and refuse integer formats.

## Troubleshooting

Start from what was observed; the full index is `docs/spg/diagnose/symptoms.rst`. The renderer
writes its log to standard output, where launch-script `warning()` lines appear prefixed `Lua:`.

| Symptom | Most likely cause |
|---|---|
| Output empty or black | The node never ran: its output is consumed by nothing and publishes no RenderVar |
| Output empty, scene looks right | The RenderVar has a connection but no `sourceName` |
| Output empty, node looks right | The launch script was rejected by the sandbox scan, an output was never assigned a descriptor, or the shader sits under a `Material` or instanceable prim and is ignored |
| Wrong pixels rather than none | Argument or bind order does not match the GPU code, or the shape order is reversed |
| Vector components wrong on CUDA | The dtype constructor does not match the kernel parameter's type or component count, or a pointer parameter needs `cuda.array` |
| A band or corner unwritten | The grid is too small; round up when dividing the domain by the block |
| Graph stops, log names `numthreads` | A `.spv` with no thread group size from either the shader or the script |
| Values right on frame one only | A `static` function reads a value that is not one of its arguments, such as a variable declared at the top level of the script, or a field of a table argument whose contents change |
| Lidar output empty | The sweep returned nothing; check `Counts`, and that motion BVH is enabled |

## References

Docs under `docs/spg/`: `overview.rst` explains the model; `first_node.rst` builds one node;
`do/index.rst` routes tasks; `ref/index.rst` covers Lua functions and USD attributes;
`diagnose/index.rst` indexes symptoms and limitations.
Runnable examples: `spg-grayscale` (smallest node), `spg-pipeline` (chaining/value inputs),
`spg-builtin-nodes`, `spg-generate` (no input), `spg-blur` (uploads/caching/launch/runtime/fan-out),
`spg-stateful`, `spg-previous-frame`, `spg-composite-aov`, `spg-raygen`, `spg-scene-query`.
Related skills: `reading-render-output`, `loading-usd`, `stepping-and-rendering`, `cuda-interop`.
Editor support: `docs/spg/.luarc/` type stubs; setup in `docs/spg/ref/lua_contract.rst`.

## Custom selection overlay reference

Read [Custom selection overlays](references/selection-overlay.md) for the SelectionState format and styling contract.
> **Source (kernel):** `examples/c/selection-spg/SelectionOutline.slang` snippet `selection-spg-outline-kernel`
> **Source (launch):** `examples/c/selection-spg/SelectionOutline.slang.lua` snippet `selection-spg-launch`
> **Source (graph):** `examples/c/selection-spg/selection_scene.usda` snippet `selection-spg-render-graph`
