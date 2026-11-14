# SPG Generating Node Example

An SPG node with **no input AOV at all**. Every value it needs is a typed USD attribute, and it
draws a checkerboard into its own output, which the scene publishes as the `Checker` AOV.

| File | Role |
|------|------|
| `CheckerKernel.cu` / `.cu.lua` / `.usda` | The node, in CUDA. |
| `CheckerKernel.slang` / `.slang.lua` / `.slang.usda` | The same node, in Slang. |
| `checker_scene.usda` / `checker_scene_slang.usda` | A RenderProduct that publishes `Checker`. |

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py                                   # CUDA
uv run main.py --scene checker_scene_slang.usda  # Slang
```

The first step compiles the kernel and may block for up to 5 minutes on a fresh shader cache. A
successful run writes `_output/checker.png`: 64-pixel squares in white and dark blue, the size
and colours the scene authors.

## How it works

- The shader definition declares typed attributes and one `opaque outputs:` port. There is no
  `opaque inputs:` port.
- The launch script takes `width` and `height` from
  attributes and states the output size itself.
- The node runs only because its output is published as a RenderVar listed in `orderedVars`.
  Execution is driven backward from what a product is asked to produce, so a generating node
  that nothing asks for never runs.

See the **Write a Node With No Input** page in the SPG documentation for the same
material in prose.
