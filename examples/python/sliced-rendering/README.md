# Sliced Rendering ovrtx Example

Demonstrates rendering a full image as four successive crops using OpenUSD's `dataWindowNDC` RenderProduct attribute.

The example renders the top-left, top-right, bottom-left, and bottom-right 512x512 regions of a 1024x1024 RenderProduct. Each region receives 10 warmup frames before its captured frame. The example then stitches the four captured outputs into one 1024x1024 RGBA image.

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
