# Crop Window ovrtx Example

Demonstrates using OpenUSD's `dataWindowNDC` attribute on a RenderProduct to render a cropped sub-region of the full frame.

The scene defines a 1024x1024 RenderProduct with `dataWindowNDC = (0.25, 0.25, 0.75, 0.75)`, which crops to the center 512x512 pixels. The example verifies the output dimensions match the expected crop.

## Prerequisites

- Python 3.10–3.13
- [uv](https://docs.astral.sh/uv/)

## Running

```bash
uv run main.py
```

Save to PNG instead of displaying:

```bash
uv run main.py --png
```
