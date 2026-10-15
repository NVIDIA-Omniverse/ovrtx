# Semantic Segmentation

Populates an attached ovstage from the bundled `ovrtx-robot-lineup.usda` scene, renders semantic segmentation through `/World/Camera`, and streams the labeled results to Rerun.

The example uses an inline USDA root layer with a relative `subLayers` arc to the source scene. The inline layer authors semantic-label overrides for each top-level robot payload, `/Render/Camera`, and one `RenderVar` for each requested AOV, so the original USD file is left untouched. Rerun is initialized with an active blueprint that arranges the AOV display images in a grid, and each logged frame is timestamped on the `sim_time` timeline from the same `delta_time` passed to `renderer.step()`.

> _“Create a Python example that composes an existing scene with semantic label overrides and camera annotation outputs, renders several camera AOVs including semantic segmentation and its ID map, decodes metadata into human-readable labels, logs a useful visual layout to a viewer, and supports headless image export.”_

![semantic segmentation example](../../../img/example-semantic-segmentation.avif)

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote payloads referenced by `ovrtx-robot-lineup.usda`
- Unsandboxed runtime execution

## Running

```bash
uv run main.py
```

Useful options:

```bash
uv run main.py --resolution 1280 720
uv run main.py --warmup-frames 10
uv run main.py --step-dt 0.0166666667 --grid-columns 5
uv run main.py --usd /path/to/scene.usda
uv run main.py --no-spawn
```

Logged AOVs:

- `LdrColor`
- `HdrColor`
- `NormalSD`
- `DepthSD`
- `DistanceToCameraSD`
- `DistanceToImagePlaneSD`
- `DiffuseAlbedoSD`
- `Camera3dPositionSD`
- `SemanticSegmentation`
- `SemanticIdMap`
- `TargetMotionSD` (captured after the robots move)

Image AOVs are logged as raw Rerun tensors under `render/aovs/<name>/raw` when supported by the installed
`rerun-sdk`, and they also get a viewable image under `render/aovs/<name>/display`.

`SemanticIdMap` is decoded before the semantic segmentation image is logged. The example builds 16-bit Rerun class IDs
from that map, remaps scalar semantic IDs into the new class-ID space, then logs `rr.SegmentationImage` data under
`render/aovs/SemanticSegmentation/class_ids` with an `rr.AnnotationContext` containing the corresponding labels. The
grid blueprint displays that class-id segmentation image rather than the debug RGB label visualization.

The `class_ids` image contains compact Rerun IDs, not the original renderer IDs. The original `uint32`
`SemanticSegmentation` image is still logged under its `raw` entity.

When `--no-spawn` is used, the example also writes display PNGs for each image AOV to `_output/`.

The example captures the static AOVs after 50 warmup frames by default. It then moves all seven robots between their rest pose and small offsets for ten frames with the camera and warehouse fixed, and captures only `TargetMotionSD`. Motion direction is shown as hue and displacement as brightness, with 20 pixels at full brightness. In headless mode, static PNGs are saved before animation and are not overwritten. The raw motion output is also saved as `_output/TargetMotionSD.npy`.

The example also captures instance segmentation, bounding boxes, visibility, ID maps and camera parameters. Raw additional outputs are saved as `_output/<sourceName>.npy`, display images as PNGs, and shape/content diagnostics in `_output/capture.json`. First-frame ID-map deltas are saved in `_output/initial/`; after warmup the unchanged scene has no new IDs. Empty outputs and mapping failures are recorded without preventing other outputs from being captured.


## Visualizing buffer outputs

Raw bounding-box overlays show individual robot parts; semantic overlays show the seven top-level robot bounds. Runtime IDs are joined through `InstanceMap` and `StableIdSemanticIdMap` to stable IDs and prim paths. `OcclusionSD` colors loose robot-part boxes from green to red, omitting invalid ratios. This is a per-instance diagnostic, not a pixel mask.

The code below projects a decoded 3D box with the view and projection matrices from `CameraParams`. It uses row vectors and clips edges against the near plane; box and camera coordinates already share scene units.

```python
def draw_projected_box(draw, row, color) -> int:
    """Transform eight local corners and clip each edge against the camera near plane before projection."""
    corners = np.array([[row["max"][axis] if index & (1 << axis) else row["min"][axis]
                         for axis in range(3)] + [1] for index in range(8)], dtype=np.float64)
    clip = corners @ row["transform"] @ view @ projection
    edges_drawn = 0
    for first in range(8):
        for axis in range(3):
            second = first ^ (1 << axis)
            if second < first:
                continue
            a, b = clip[first].copy(), clip[second].copy()
            if not np.all(np.isfinite([a, b])) or max(a[3], b[3]) < near:
                continue
            if a[3] < near:
                a += (b - a) * (near - a[3]) / (b[3] - a[3])
            if b[3] < near:
                b += (a - b) * (near - b[3]) / (a[3] - b[3])
            ndc = np.array([a[:2] / a[3], b[:2] / b[3]])
            pixels = (ndc * [0.5, -0.5] + 0.5) * [width, height]
            draw.line([tuple(point) for point in pixels], fill=color, width=max(1, width // 750))
            edges_drawn += 1
    return edges_drawn
```

ID maps are presented beside an annotated camera image, with complete records saved in `_output/decoded.json`. Delta-map illustrations use first-frame entries; unchanged frames contain no new entries. `_output/visualization.json` records selection and drawing counts.

## Minimal capture

Run `main.py --render-mode MinimalRendering --resolution 960 540 --no-spawn`
to save previews under `_output/minimal/`. The capture uses 50 warmup frames,
then moves the robots for a separate motion image. Minimal requests `LdrColor`
and the supported Synthetic Data outputs; it omits `HdrColor`.
A small ambient fill keeps every robot visible; Minimal ignores dome lights.

## Path Tracing capture

Run `main.py --render-mode PathTracing --resolution 960 540 --samples-per-pixel 128 --no-spawn`
to write PT tensors, PNG previews, and `capture.json` under `_output/pt/`.
The capture renders one static frame at 128 samples per pixel, without warmup frames.
It then moves the seven robots for one separate motion frame.
Empty outputs remain visible in the report. LPE requests use expression source names.
`MultiMatte.png` combines corresponding vertical slices from `PtMultiMatte0`–`3`.
Geometry IDs 1–7 select the robots. The source scene assigns 8/9/10 to warehouse
walls/shelves/pallets, which fill the first output’s RGB channels. Material IDs 101/102
select the C forklift body/painted panels, and 103/104 select the B forklift body/glass.
Selectors are grouped by camera position so each vertical slice contains visible masks.
The labels list the RGBA selectors, with G for geometry IDs and M for material IDs.
Configure `omni:rtx:pt:multimatte:rId/gId/bId/aId` and the corresponding
`rIsMat/gIsMat/bIsMat/aIsMat` attributes on each RenderVar.
An ID of -1 or an omitted ID disables that component. Each flag selects geometry
`primvars:multimatte_id` (false) or material `multimatte_id` (true).
The requested RenderVars determine allocation: no `channelCount` is needed.
Eight outputs provide up to 32 masks; sparse requests and separate RenderVars
sharing a source name are supported. Alpha is independent coverage, not image opacity.
Warehouse floor ID 11 fills the first alpha mask; Jetbot/Kaya fill the next two;
the fourth alpha component is disabled. The grey strip shows full-frame alpha masks.

The render layer requests the PT and Synthetic Data outputs on the same scene:

```python
def build_pt_render_layer_usda(scene_path: Path, resolution: tuple[int, int], samples_per_pixel: int = 128) -> str:
    """Request PT outputs on the same labeled lineup without changing its source scene."""
    base = build_render_layer_usda(scene_path, resolution)
    # Tag existing objects and bound materials; mask IDs do not change their appearance.
    robot_names = ["GR1T2_fourier_hand_6dof", "spot", "forklift_c", "forklift_b",
                   "carter_v1", "jetbot", "kaya"]
    material_overrides = {
        "forklift_c": '''over "Looks" {
            over "M_Forklift_C01" {
                int multimatte_id = 101
            }
            over "M_Forklift_C01_Blue" {
                int multimatte_id = 102
            }
        }''',
        "forklift_b": '''over "Looks" {
            over "M_Forklift_B1_Body" {
                int multimatte_id = 103
            }
            over "M_Forklift_B1_Glass" {
                int multimatte_id = 104
            }
        }''',
    }
    for identifier, name in enumerate(robot_names, 1):
        base = re.sub(r'(over "' + name + r'"\s*\([^)]*\)\s*\{)',
                      lambda match: match[0] + f'\n        int primvars:multimatte_id = {identifier}\n'
                      + material_overrides.get(name, "") + "\n", base)
    # The source scene assigns IDs 8/9/10 to warehouse walls, shelves and pallets.
    # The source scene also tags warehouse floors with ID 11 for an independent alpha mask.
    # Request only the four configured Multi-Matte RenderVars; each carries its own selectors.
    names = list(dict.fromkeys(PT_AOV_NAMES + re.findall(r'string sourceName = "(\w+)"', base)))
    names = [name for name in names if not name.startswith("PtMultiMatte") or int(name[-1]) < 4]
    definitions = []
    for name in names:
        expression = PT_LPE_EXPRESSIONS[int(name[-1])] if name.startswith("PtLpe") else name
        source_type = 'token sourceType = "lpe"' if name.startswith("PtLpe") else ''
        matte_selectors = ""
        if name.startswith("PtMultiMatte"):
            index = int(name[-1])
            selectors = PT_MULTIMATTE_CHANNELS[index * 4:index * 4 + 4]
            for component, (identifier, is_material) in zip("rgba", selectors):
                matte_selectors += f"int omni:rtx:pt:multimatte:{component}Id = {identifier}\n"
                matte_selectors += f"bool omni:rtx:pt:multimatte:{component}IsMat = {str(is_material).lower()}\n"
        definitions.append(f'def RenderVar "{name}" {{\nstring sourceName = "{expression}"\n{source_type}\n{matte_selectors}}}')
    variables = "\n".join(definitions)
    ordered = ", ".join(f"<{name}>" for name in names)
    width, height = resolution
    # Allow two setup passes after scene edits; samplesPerPixel still caps the render at the requested SPP.
    return base.split('def "Render"', 1)[0] + f'''def "Render" {{
    def RenderProduct "Camera" {{
        rel camera = </World/Camera>
        int2 resolution = ({width}, {height})
        token omni:rtx:rendermode = "PathTracing"
        uint omni:rtx:pt:samplesPerPixel = {samples_per_pixel}
        int omni:rtx:pt:samplesPerIteration = {min(samples_per_pixel, 32)}
        int omni:rtx:quality = 100
        int omni:rtx:quality:minSpp = {samples_per_pixel + 2 * min(samples_per_pixel, 32)}
        bool omni:rtx:pt:adaptiveSampling:enabled = false
        bool omni:rtx:pt:radianceCache:enabled = false
        uint omni:rtx:rt:groundTruth:resolution:width = {width}
        uint omni:rtx:rt:groundTruth:resolution:height = {height}
        rel orderedVars = [{ordered}]
        {variables}
    }}
}}
'''
```
