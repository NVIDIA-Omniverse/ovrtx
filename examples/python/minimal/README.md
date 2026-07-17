# Minimal ovrtx Example

This is the minimal Python example from the ovrtx README. It demonstrates the basic workflow:

1. Create a Renderer and attach an ovstage Stage
2. Populate the Stage from a remote S3 scene URL and publish its ordinal
3. Step the renderer at that ordinal to produce a frame
4. Map the rendered output and display it

> _“Create the smallest useful Python example that loads an existing USD scene, renders one camera frame, maps the color output to CPU memory, and either displays it or saves it as an image through a command-line flag.”_

![output](../../../img/example-minimal.jpg)

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

## Running

```bash
uv run main.py --png
```

The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached. A successful run writes `_output/render.png`; the output should match the reference image above.
