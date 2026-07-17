# Tiled Rendering

Renders a 3x3 grid of scene instances through a single RenderProduct with multiple cameras. Demonstrates tiled multi-camera rendering, ovstage population of USD reference composition, and ordinal-keyed material color writes.

Each grid cell references the same base scene but gets a unique logo color generated from evenly spaced HSV hues. A single 1024x1024 RenderProduct targets all nine cameras, and RTX tiles them into a grid in the output image.

> _“Create a Python example that composes multiple referenced scene instances into a grid, assigns per-instance visual variation at runtime, renders all cameras through one tiled output, warms up for image quality, and saves or displays the final tiled image.”_

![output](../../../img/example-tiled-rendering.avif)

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)

## Running

```bash
uv run main.py
```

Save the rendered image to `_output/tiled_render.png` instead of displaying it:

```bash
uv run main.py --png
```

The first time the example is run, driver shader compilation will be performed and cached. Subsequent runs will be much faster.
