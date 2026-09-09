# SPG Separable Blur Example

Two SPG nodes chained into a separable Gaussian blur: `LdrColor` -> **horizontal** -> **vertical**
-> `LdrBlurred`. The tap weights are not computed on the GPU. They depend on nothing but the
radius, so the launch script builds them once, uploads them once, and hands both passes the same
buffer.

The radius is a USD attribute this example rewrites between renders, which is what makes its
checks exact: at radius 0 the weight table is `{1.0}`, the blur is the identity, and the published
AOV has to equal `LdrColor` byte for byte.

| File | Role |
|------|------|
| `BlurKernel.cu` / `.cu.lua` | Both passes, in CUDA. One source and one launch script, two entry points. |
| `BlurKernel.slang` / `.slang.lua` | The same two passes, in Slang. |
| `BlurTaps.slang` | The tap loop both Slang passes `import`, in its own module beside the shader. |
| `BlurHorizontal.usda` / `BlurVertical.usda` | The two shader definitions, naming one entry point each. |
| `BlurHorizontal.slang.usda` / `BlurVertical.slang.usda` | The same, for the Slang source. |
| `blur_scene.usda` / `blur_scene_slang.usda` | A RenderProduct that publishes `LdrBlurH` and `LdrBlurred`. |

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py                                # CUDA
uv run main.py --scene blur_scene_slang.usda  # Slang
```

The first step compiles the kernel and may block for up to a minute on a fresh shader cache. A
successful run writes `_output/input.png` and `_output/blurred.png` and prints:

```
radius 0, pixels differing from the input: 0
radius 8, sharpest edge: 122 -> 24
radius 8, sharpest edge after one pass: 55
radius 8, mean brightness drift: 0.003
weight tables built: 2 (radii 8, 0)
```

The zero and the table count are exact. The edge figures move a little from run to run, because the
image is still converging; what the run checks is that they fall in order, and a check that fails
exits non-zero.

## How it works

- **One source, two nodes.** Both passes are entry points in one file, and the launch script
  carries one function per entry point. Two Shader prims point at that source and name a
  different `subIdentifier`.

- **The weights are built in Lua and cached.** `gaussianWeights` is wrapped in `cuda.static` /
  `slang.static`, which calls it once and caches the result against its arguments. It announces
  itself in the renderer log, so the count is visible: over a run of some fifty rendered frames
  the table is built **twice**, once per radius, not once per frame.

- **The two passes launch differently, on purpose.** The horizontal pass runs one thread per
  output pixel, which is what SPG derives when the launch script states nothing. The vertical pass
  runs one thread per output *column*, each walking its column top to bottom, so the iteration
  domain is the width alone and the launch script has to say so.

- **The first pass feeds two things at once.** Its output goes on to the second pass and to a
  RenderVar of its own, so the half-finished blur can be read back. That is why the run reports
  three sharpest-edge figures rather than two, and why they have to come out in order.

- **The radius is written at runtime.** `inputs:radius` is connected to nothing, so writing it on
  the Shader prim takes effect on the next step with no reset. Changing it also changes the cache
  key, which is why the weight table is built a second time.

- **Slang splits the tap loop into a module.** `BlurKernel.slang` does `import BlurTaps;`, which
  resolves to the file beside it. CUDA has no equivalent: one include directory is searched and
  it is never the `.cu`'s own, so both CUDA passes share the loop through a `__device__` function
  in the same file.

## A warning you will see

Every frame, each pass logs:

```
allocateOrReuseStaticTensorResource: tensor '...' is not dense/row-major (size=68, dense=68); not caching
```

`static` still does its job, and the run reports it: the weight table is built twice, not once per
frame. The message is about the GPU-side upload of that table, which is a separate thing. SPG keeps
an uploaded buffer resident only for a tensor whose strides it reads as implicit row-major, and
every array a launch script hands over carries explicit ones, so the upload is redone each frame.
For a table of a few dozen floats that costs nothing measurable; for a large one it is worth
knowing before you plan around it.

See the **Upload Your Own Data**, **Cache Work Across Frames**, **Control the Launch Geometry** and
**Change Values and Rewire** pages in the SPG documentation for the same material in prose.
