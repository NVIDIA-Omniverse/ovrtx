# SPG Pipeline Example

Two SPG shaders chained into a pipeline: `LdrColor` → **Grayscale** → **Invert** →
`LdrInverted`. Shaders are chained by connecting one shader's `outputs:` port directly to the
next shader's `inputs:` port — **no intermediate RenderVar is needed**, so the grayscale result
stays internal to the chain and only the final inverted image is published as an AOV.

> **ovrtx 0.4 compatibility:** This example uses the deprecated renderer scene-loading API so it can remain focused on SPG authoring. Use the 0.3-to-0.4 migration skill when moving scene management to ovstage.

| File | Role |
|------|------|
| `GrayscaleKernel.cu` / `.cu.lua` / `.usda` | First pass: color → grayscale. |
| `InvertKernel.cu` / `.cu.lua` / `.usda` | Second pass: invert the grayscale image (`inputs:Image`). |
| `pipeline_scene.usda` | Wires `Grayscale.outputs:LdrGrayscale` → `Invert.inputs:Image`. |

SPG runs the shaders in **topological order of the connection graph**, not the order of
`orderedVars`. Because the intermediate grayscale image is consumed by `InvertKernel` and never
published, it does not appear in `orderedVars`.

> _“Chain two SPG shaders so the renderer's color output is converted to grayscale and then inverted in a single RenderProduct, reading back only the final result.”_

![output](../../../img/example-spg-pipeline.png)

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py
```

The first step compiles both CUDA kernels with NVRTC and may block for up to a minute on a
fresh shader cache. A successful run writes `_output/input.png` and
`_output/inverted_grayscale.png`.

## Tip

To inspect the intermediate grayscale result, publish it as its own RenderVar (an *intermediate
AOV*) and add it to `orderedVars`. See the **Sensor Processing Graphs** docs for that pattern.
