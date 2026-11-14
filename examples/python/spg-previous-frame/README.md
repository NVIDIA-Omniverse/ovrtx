# SPG Previous Frame Example

An SPG node that reads the **same AOV twice**: once as the renderer produced it this frame, and
once as it was one frame ago. It publishes the difference, so whatever moved lights up and whatever
held still goes dark.

One suffix on a RenderVar selects the previous frame:

```usda
def RenderVar "PreviousColor"
{
    uniform string sourceName = "LdrColor:-1"
    opaque omni:rtx:aov
}
```

The node declares two `opaque inputs:` ports, and
which of them is a past frame follows from what the scene connects them to.

| File | Role |
|------|------|
| `MotionKernel.cu` / `.cu.lua` / `.usda` | The node, in CUDA. |
| `MotionKernel.slang` / `.slang.lua` / `.slang.usda` | The same node, in Slang. |
| `motion_scene.usda` / `motion_scene_slang.usda` | A ball on a backdrop, and the graph. |

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py                                  # CUDA
uv run main.py --scene motion_scene_slang.usda  # Slang
```

The first step compiles the kernel and may block for up to 5 minutes on a fresh shader cache. A
successful run writes three PNGs to `_output/`: `colour.png`, the last frame the renderer drew;
`motion-moving.png`, the difference while the ball moves; and `motion-still.png`, the difference
once the ball has held still.

## How it works

The run has two halves.

- **Moving.** The ball is driven a step around a circle before each render, so this frame and the
  last one disagree wherever it went. The difference image shows the ball and the hole it left.

- **Still.** The ball is written to the same position before each render. This frame and the last
  one now agree, and the difference collapses to the sampling noise of a converged render.

The still image is not completely black: a path-traced render
keeps refining, so consecutive frames of a static scene differ slightly.

See the **Read a Previous Frame** page in the SPG documentation for the same material in prose,
including how far back `:-N` can read and how it differs from a stateful output.
