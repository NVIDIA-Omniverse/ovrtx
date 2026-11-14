# Sliced Rendering ovrtx Example

Demonstrates rendering a full image as four successive crops using OpenUSD's `dataWindowNDC` RenderProduct attribute.

The example renders the top-left, top-right, bottom-left, and bottom-right 512x512 regions of a 1024x1024 RenderProduct. Each region uses PathTracing at 64 samples per pixel, with zero client warmup frames. The example waits for each crop to converge, then stitches the four captured outputs into one 1024x1024 RGBA image.

No quality attribute is authored; streaming wait uses the renderer defaults.

## Prerequisites

- Python 3.10–3.13
- [uv](https://docs.astral.sh/uv/)

## Running

```bash
uv run main.py
```

Save the stitched image to PNG instead of displaying it:

```bash
uv run main.py --png
```
