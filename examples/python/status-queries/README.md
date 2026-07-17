# Status Queries ovrtx Example

This example is based on the minimal Python example and adds operation status
queries for the async operations in that flow:

> **ovrtx 0.4 compatibility:** This example retains deprecated ovrtx population operations because ovstage population operations do not expose equivalent progress counters.

1. Create a Renderer
2. Load a USD layer from a remote S3 scene URL with `open_usd_async()` and query status while waiting
3. Run one shader-cache warm-up step and print shader compilation progress
4. Step the renderer with `step_async()` and query status while waiting
5. Map the rendered output and display it or save it to disk

Renderer logs are written to `_output/status-queries-ovrtx.log`.

> _“Create a Python rendering example that demonstrates progress reporting for long-running ovrtx operations, including asynchronous scene loading, status polling while waiting, shader warmup feedback, final frame rendering, and save-or-display output.”_

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
uv run main.py
```

To save the render instead of displaying it:

```bash
uv run main.py --png
```
