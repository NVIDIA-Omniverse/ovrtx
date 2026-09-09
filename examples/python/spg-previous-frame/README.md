# SPG Previous Frame Example

An SPG node that reads the **same AOV twice**: once as the renderer produced it this frame, and
once as it was one frame ago. It publishes the difference, so whatever moved lights up and whatever
held still goes dark.

The whole mechanism is one suffix on a RenderVar:

```usda
def RenderVar "PreviousColor"
{
    uniform string sourceName = "LdrColor:-1"
    opaque omni:rtx:aov
}
```

Nothing on the node says anything about time. It declares two ordinary `opaque inputs:` ports, and
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

The first step compiles the kernel and may block for up to a minute on a fresh shader cache. A
successful run writes three PNGs to `_output/` and prints:

```
pixels changed while moving: 3281
pixels changed while still:  50
```

Neither count repeats exactly between runs. The check is the gap between them, and a run that
fails it exits non-zero.

## How it works

The run has two halves, and the contrast between them is the whole check.

- **Moving.** The ball is driven a step around a circle before each render, so this frame and the
  last one disagree wherever it went. The difference image shows the ball and the hole it left.

- **Still.** The ball is written to the same position before each render. This frame and the last
  one now agree, and the difference collapses to the sampling noise of a converged render.

A node wired to the live AOV twice would print a near-zero count in **both** halves, so the moving
half is what proves the `:-1` binding resolved to a past frame rather than to the current one.

The count while still is not exactly zero, and should not be expected to be: a path-traced render
keeps refining, so consecutive frames of a static scene differ slightly. What matters is the ratio.

See the **Read a Previous Frame** page in the SPG documentation for the same material in prose,
including how `:-N` behaves for N up to 8 and how it differs from a stateful output.
