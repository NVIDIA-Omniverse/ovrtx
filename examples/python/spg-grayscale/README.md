# SPG Grayscale Example

The "hello world" of Sensor Processing Graphs (SPG). It runs a custom CUDA kernel as a
post-processing pass over the renderer's `LdrColor` AOV, converting it to grayscale entirely
on the GPU, and publishes the result as a new `LdrGrayscale` AOV.

> **ovrtx 0.4 compatibility:** This example uses the deprecated renderer scene-loading API so it can remain focused on SPG authoring. Use the 0.3-to-0.4 migration skill when moving scene management to ovstage.

This is the minimal **three-file** SPG shader:

| File | Role |
|------|------|
| `GrayscaleKernel.cu` | The CUDA kernel — reads `LdrColor`, writes grayscale. |
| `GrayscaleKernel.cu.lua` | The Lua launch script — validates the input, allocates the output, returns the launch config. |
| `GrayscaleKernel.usda` | The shader definition — declares the ports and points at the `.cu`. |

`grayscale_scene.usda` wires the shader into a `RenderProduct`: the built-in `LdrColor`
RenderVar feeds `GrayscaleKernel`, whose output is published as the `LdrGrayscale` RenderVar.
The names line up across all three files — the `extern "C"` kernel name, the
`info:spg:sourceAsset:subIdentifier`, and the Lua function name are all `grayscale`.

> _“Create the smallest useful SPG example: a CUDA kernel that converts the LdrColor render output to grayscale, wired into a RenderProduct and read back from Python as a new AOV.”_

![output](../../../img/example-spg-grayscale.png)

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

The first step compiles the CUDA kernel with NVRTC and may block for up to a minute on a
fresh shader cache. A successful run writes `_output/input.png` (the rendered `LdrColor`) and
`_output/grayscale.png` (the SPG output).

## How it works

- The kernel reads its input AOV through a `cudaTextureObject_t` (read-only, hardware-cached)
  and writes its output through a `cudaSurfaceObject_t` (random-access writes).
- The launch script's `args` list maps Lua-wrapped values to the kernel's C parameters in
  order — the binding is positional, not by name.
- An SPG output AOV is read back exactly like a built-in render var:
  `frame.render_vars["LdrGrayscale"].map(device=ovrtx.Device.CPU)`.

See the `spg-usd-lua-authoring` skill and the **Sensor Processing Graphs** section of the docs
for the full authoring reference.
