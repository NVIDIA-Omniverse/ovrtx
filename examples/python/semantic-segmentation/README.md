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

Image AOVs are logged as raw Rerun tensors under `render/aovs/<name>/raw` when supported by the installed
`rerun-sdk`, and they also get a viewable image under `render/aovs/<name>/display`.

`SemanticIdMap` is decoded before the semantic segmentation image is logged. The example builds 16-bit Rerun class IDs
from that map, remaps scalar semantic IDs into the new class-ID space, then logs `rr.SegmentationImage` data under
`render/aovs/SemanticSegmentation/class_ids` with an `rr.AnnotationContext` containing the corresponding labels. The
grid blueprint displays that class-id segmentation image rather than the debug RGB label visualization.

The `class_ids` image contains compact Rerun IDs, not the original renderer IDs. The original `uint32`
`SemanticSegmentation` image is still logged under its `raw` entity.

When `--no-spawn` is used, the example also writes display PNGs for each image AOV to `_output/`.
