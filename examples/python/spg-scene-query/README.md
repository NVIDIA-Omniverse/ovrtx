# SPG Scene Query Example

An SPG node that reads the scene it runs in. The launch script asks for the render product it
sits under, takes the camera that product is bound to, reads the camera's lens values and world
transform, and looks up the world position of every marker a prim of the scene lists. The kernel
projects each marker into the camera image and draws a crosshair on it, over the renderer's
`LdrColor`.

Nothing in the node names a camera or a marker. Point the product at another camera, move the
rig, or list other prims on `/World/Overlay`, and the overlay follows.

| File | Role |
|------|------|
| `MarkerOverlayKernel.cu` / `.cu.lua` | The kernel and its launch script, in CUDA. The script does every scene read. |
| `MarkerOverlayKernel.slang` / `.slang.lua` | The same node in Slang. The scene reads are identical; only the dispatch differs. |
| `MarkerOverlayKernel.usda` / `.slang.usda` | The shader definitions: one image in, one image out, a token naming the settings prim. |
| `overlay_scene.usda` / `overlay_scene_slang.usda` | A camera on a rig, three coloured marker spheres, the settings prim, and the RenderProduct. |

> _“Write an SPG node that draws a crosshair on chosen scene prims, working out where they land from the camera's transform and lens values read inside the launch script.”_

![output](../../../img/example-spg-scene-query.png)

## What the launch script reads

| Call | What it gives the node |
|------|------------------------|
| `rtx.product` | The product the node sits under: `.path`, `.cameras`, `.render_vars`, and its authored `resolution`. |
| `rtx.product.cameras[1]` | The bound camera as a prim table: `.path`, `.local_matrix`, `.world_matrix`, `["focalLength"]`. |
| `rtx.stage.prim(path)` | The settings prim by path; its relationship reads as a list of path strings. |
| `rtx.stage.query_attributes(paths, { WORLD_MATRIX })` | One attribute of many prims in one call: the markers' world transforms. |

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py                                    # CUDA
uv run main.py --scene overlay_scene_slang.usda   # Slang
```

The first step compiles the kernel and may block for up to a minute on a fresh shader cache. A
successful run writes `_output/color.png`, the rendered image, and `_output/overlay.png`, the same
image with a white crosshair on each marker.

## How it works

- The settings prim `/World/Overlay` holds custom attributes the renderer has no use for, so
  `main.py` opens the scene with a description that publishes them alongside the renderer's own
  content. Without it the prim is found, but `markers` and `crosshairSize` read `nil`.
- The camera's world transform arrives flat and row-major: the first three rows are the
  camera's axes in world space and the fourth row its position. The kernel projects a marker by
  expressing it in those axes and dividing by depth; the lens values set the field of view.

See the `spg` skill and the **Sensor Processing Graphs** section of the docs for the full
authoring reference.
