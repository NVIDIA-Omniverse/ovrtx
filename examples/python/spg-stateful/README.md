# SPG Stateful Node Example

An SPG node that reads back its own previous output, which is the effect known as
**framebuffer feedback**, so a moving object drags a fading comet tail behind it.

The whole node is one line:

```
history[n] = current[n] + decay * history[n-1]
```

Fade what you published last time, add what you were handed this time.

## What you are looking at

The run writes two images, and the point is the pair:

- `_output/live.png` is the frame the node was handed. **One glowing ball**, on a flat grey
  backdrop, and nothing else.
- `_output/trail.png` is what the node published from that same frame. The **same ball in
  the same place**, now with a comet tail sweeping about half a revolution behind it,
  brightest at the ball and fading to nothing further back.

Both images come out of the same render step, the same node and the same tone map, so
everything you can see that differs between them came from the previous frame. The backdrop
deliberately reads at the same brightness in both, so the tail is the only difference.

The scene is a single ball on a plain backdrop: no floor, no reflections, nothing else that
could be mistaken for the effect. The ball is driven around a **circle** rather than in a
straight line on purpose, because a tail curving through half a revolution cannot be
mistaken for blur within one frame.

The tail is faintly beaded rather than perfectly smooth. Each bead is one render step, so
what you are seeing is the frame rate: the node only ever knows the positions it was
actually shown.

| File | Role |
|------|------|
| `TrailKernel.cu` / `.cu.lua` / `.usda` | The CUDA node: read back, fade, add, publish. |
| `TrailKernel.slang` / `.slang.lua` / `.slang.usda` | The same node as a Slang compute shader. |
| `trail_scene.usda` | Backdrop, one glowing ball, the CUDA graph on `/Render/TrailDemo`. |
| `trail_scene_slang.usda` | The same scene against the Slang shader definition. |

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py                                # CUDA
uv run main.py --scene trail_scene_slang.usda   # Slang
```

```
lit area:         3448 px live,  40308 px with the tail (11.7x)
backdrop level:     91    live,     91    with the tail
```

The pixel counts move from run to run, because the image is still converging. The ratio is what the run checks, along with the backdrop level matching.

The tail lights about twelve times the area the ball covers, over a backdrop sitting at the
same level in both images. Both backends produce the same picture to within one 8-bit level,
which is the rounding difference between CUDA's explicit conversion and the Vulkan UNORM
write.

## Why the node cannot be written without state

`history[n-1]` **is** the previous execution's output. SPG hands a node one frame per
execution and nothing else: there is no multi-frame input, and no way to see what you
published last time except to write it into an allocation that survives.

This is not a technique that has a stateless alternative formulation. Feedback is defined by
the recursion. Remove the previous term and there is no effect left, only the input passing
through.

A *host* program could of course produce a similar picture by stepping the renderer, copying
each frame back to the CPU and blending in numpy. That is true of every temporal algorithm
and is not the claim here. What a host loop cannot do is put the result back **inside the
graph**, as an AOV that downstream SPG nodes and render-product consumers see, at graph
rate, without the frame ever leaving the GPU.

## How the state is declared

The node allocates **three** outputs:

- `History` carries the feedback framebuffer. It is allocated with the `cuda.stateful` /
  `slang.stateful` marker, so SPG hands back the same resource next frame instead of a fresh
  one. It is never published and has no RenderVar, which is worth noting: a stateful output
  is scratch space for the node, not something the scene has to know about.
- `Live` and `Trail` are ordinary outputs, handed out fresh each frame and published as
  AOVs.

The marker is the **trailing argument** of the allocator, in the same position on both
backends:

```
cuda.image(width, height, cuda.float4, cuda.stateful)
slang.empty(shape, slang.float4, slang.stateful)
```

Nothing else about a stateful output is special. It binds like any other resource, and the
shader reads and writes it with the ordinary read/write binder for its backend.

**The history is `float4` while the published AOVs are `uchar4`.** A stateful output may use
whatever format the algorithm needs. Here the feedback runs on linear radiance, which would
not survive being rounded into 8 bits and re-scaled every frame.

**A stateful allocation starts zeroed.** SPG clears it on first use, so the first frame
reads zeros rather than whatever was in memory, and `history[0] = current[0]` comes out
correct without the node having to initialise anything.

## What `decay` does

`inputs:decay` sets how much of the previous frame is kept. A pixel the ball passed over `k`
frames ago still holds `decay^k` of the light it deposited, so one number sets the whole
length of the tail: `0.7` gives roughly half a revolution, and `0.0` keeps nothing and makes
`Trail` identical to `Live`.

## Why the published image is scaled by (1 - decay)

Feedback amplifies whatever holds still. A pixel showing the same radiance every frame
settles at `current / (1 - decay)`, so without correction the backdrop would come out
brighter in `Trail` than in `Live` and the two images would no longer be comparable.

Scaling the published image by `(1 - decay)` puts the static scene back at its true
brightness. The backdrop then reads identically in both images and only what actually moved
leaves a tail. The recursion itself is untouched: this is an exposure applied on the way
out, not a change to the filter.

## Losing the state leaves the input passing through

Drop `cuda.stateful` / `slang.stateful` from the allocator and `history[n-1]` reads back
empty every frame:

```
lit area:         3448 px live,  40308 px with the tail (11.7x)   # working
backdrop level:     91    live,     91    with the tail

lit area:         3448 px live,   3440 px with the tail (1.0x)    # state lost
backdrop level:     91    live,     36    with the tail
```

The lit area falls back to exactly the ball, and the backdrop darkens by the `(1 - decay)`
exposure because there is no longer any accumulated gain for it to undo. What gets published
is a dimmed copy of the frame that came in. `main.py` measures both and flags the failure.

## Why the input is HdrColor

The node reads `HdrColor`, which is linear radiance, rather than the tone-mapped `LdrColor`.
Multiplying by `decay` is only a fade in linear light; applied to display-encoded values it
darkens by the wrong amount and the tail comes out with the wrong falloff. The emissive ball
also carries far more range in `HdrColor` than 8 bits can hold, which is what keeps the tail
visible for many frames as it decays.

The node tone-maps once itself, at the end, identically for both published images.
