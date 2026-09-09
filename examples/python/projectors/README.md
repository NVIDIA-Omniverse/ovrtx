# Projectors

Loads the projectors USD test scene, warms up the real-time path tracer, renders its authored camera, and saves the
result to `_output/projectors.png`.

The scene demonstrates cubic, planar, normalized spherical, and tri-planar projector mappings across several
primitive types.

> _“Create a Python rendering example that loads the projectors scene without modifying it, warms up the renderer,
> renders one frame, and saves the result as a PNG.”_

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

The first run may take several minutes while shaders are compiled and cached.
