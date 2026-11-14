# SPG Stateful Node Example

An SPG node that reads back its own previous output, which is the effect known as
**framebuffer feedback**, so a moving object drags a fading comet tail behind it.

The feedback is one line:

```
history[n] = current[n] + decay * history[n-1]
```

Fade what you kept last time, add what you were handed this time.

## What you are looking at

The run writes two images:

- `_output/live.png` is the frame the node was handed. **One glowing ball**, on a flat grey
  backdrop.
- `_output/trail.png` is what the node published from that same frame. The **same ball in
  the same place**, now with a comet tail sweeping about half a revolution behind it,
  brightest at the ball and fading to nothing further back.

Both images come out of the same render step, the same node and the same tone map, so
everything you can see that differs between them came from the previous frame.

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

The run writes `_output/live.png` and `_output/trail.png`.

## How the state is declared

The node has **two outputs and one memory**:

- `History` is the feedback framebuffer, and it is memory of the node: the launch script
  states it as `self.memory["History"]`, so SPG hands back the same resource on every run
  instead of a fresh one.
- `Live` and `Trail` are ordinary outputs, handed out fresh each frame and published as
  AOVs.

Memory is stated with the allocator outputs use and passed to the kernel with the wrapper
outputs use, on both backends:

```
self.memory["History"] = cuda.image(width, height, cuda.float4)
cuda.SurfaceObject(self.memory["History"])

self.memory["History"] = slang.image(image.shape, slang.float4)
slang.RWTexture2D(self.memory["History"])
```

**The history is `float4` while the published AOVs are `uchar4`.** Memory may use whatever
format the algorithm needs. Here the feedback runs on linear radiance, which would not survive
being rounded into 8 bits and re-scaled every frame.

**Memory starts zeroed.** SPG clears it when it creates it, so the first frame reads zeros
rather than whatever was in GPU memory, and `history[0] = current[0]` comes out correct
without the node having to initialise anything.


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

## Why the input is HdrColor

The node reads `HdrColor`, which is linear radiance, rather than the tone-mapped `LdrColor`.
Multiplying by `decay` is only a fade in linear light; applied to display-encoded values it
darkens by the wrong amount and the tail comes out with the wrong falloff. The emissive ball
also carries far more range in `HdrColor` than 8 bits can hold, which is what keeps the tail
visible for many frames as it decays.

The node tone-maps once itself, at the end, identically for both published images.
