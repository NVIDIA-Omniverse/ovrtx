# SPG Separable Blur Example

Two SPG nodes chained into a separable Gaussian blur: `LdrColor` -> **horizontal** -> **vertical**
-> `LdrBlurred`. The launch script, rather than the GPU, builds the tap weights, because they
depend only on the radius, and caches them, so each pass builds its table only when the radius
changes.

The radius is a USD attribute this example rewrites between renders: at radius 0 the weight table
is `{1.0}` and the blur is the identity.

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

The first step compiles the kernel and may block for up to 5 minutes on a fresh shader cache. A
successful run writes five PNGs to `_output/`: `input.png`, the rendered `LdrColor`;
`blurred-one-pass.png`, after the horizontal pass only; `blurred.png`, after both passes at radius
8; and, once the radius is set to 0, `radius-0-input.png` and `radius-0.png`, that frame's
`LdrColor` and the published AOV, which match pixel for pixel.

## How it works

- **One source, two nodes.** Both passes are entry points in one file, and the launch script
  carries one function per entry point. Two Shader prims point at that source and name a
  different `subIdentifier`.

- **The weights are built in Lua and cached.** `gaussianWeights` is wrapped in `cuda.static` /
  `slang.static`, which calls it once and caches the result against its arguments. Over the whole run
  each pass builds its table **twice**, for the first radius and again when the radius changes,
  not once per frame.

- **The two passes launch differently.** The horizontal pass runs one thread per
  output pixel, which is SPG's default launch geometry. The vertical pass
  runs one thread per output *column*, each walking its column top to bottom, so the iteration
  domain is the width alone and the launch script has to say so.

- **The first pass feeds two things at once.** Its output goes on to the second pass and to a
  RenderVar of its own, so the half-finished blur can be read back as `blurred-one-pass.png`.

- **The radius is written at runtime.** `inputs:radius` is connected to nothing, so writing it on
  the Shader prim takes effect on the next step with no reset.

- **Slang splits the tap loop into a module.** `BlurKernel.slang` does `import BlurTaps;`, which
  resolves to the file beside it. CUDA has no equivalent: one include directory is searched and
  it is never the `.cu`'s own, so both CUDA passes share the loop through a `__device__` function
  in the same file.

See the **Upload Your Own Data**, **Cache Work Across Frames**, **Control the Launch Geometry** and
**Change Values and Rewire** pages in the SPG documentation for the same material in prose.
