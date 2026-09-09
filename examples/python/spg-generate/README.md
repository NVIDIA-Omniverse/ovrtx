# SPG Generating Node Example

An SPG node with **no input AOV at all**. Every value it needs is a typed USD attribute, and it
draws a checkerboard into its own output, which the scene publishes as the `Checker` AOV.

This is the answer to "does my node need an input?". It does not. A resource-input is optional,
and a node can generate its output from authored values alone.

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

The first step compiles the kernel and may block for up to a minute on a fresh shader cache. A
successful run writes `_output/checker.png` and prints:

```
pixels differing from the host-computed pattern: 0
```

The pattern is exact, so any difference at all means a value did not reach the GPU or the launch
did not cover the output. A failing run exits non-zero.

## How it works

- The shader definition declares typed attributes and one `opaque outputs:` port. There is no
  `opaque inputs:` port, so nothing connects an AOV to this node.
- Nothing hands the node a shape, so the launch script takes `width` and `height` from
  attributes and states the output size itself.
- The node runs only because its output is published as a RenderVar listed in `orderedVars`.
  Execution is driven backward from what a product is asked to produce, so a generating node
  that nothing asks for never runs.
- The colours are exact at 8 bits, which lets `main.py` predict the output byte for byte
  regardless of how a float is rounded into a texture.

See the **Generate an Output Without an Input** page in the SPG documentation for the same
material in prose.
