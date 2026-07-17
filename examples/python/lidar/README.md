# Lidar Sensor Composite Tensor Example

This example populates an attached ovstage from `lidar_example.usda`, renders a lidar `PointCloud`, maps the
composite render variable to CPU memory, and visualizes detections in
[rerun.io](https://rerun.io/). Point color is derived from the `Intensity`
channel.

> _“Create a Python sensor example that loads a scene containing a configured lidar, warms up the sensor pipeline, renders one point-cloud frame, reads valid point data using the count channel, prints summary statistics, and optionally visualizes the points with intensity-based colors.”_

## Scene

The scene is Z-up and contains:

- a lidar at `(0, 0, 1)` rotated to look along world +X
- an asphalt ground plane spanning `X=-200..200` and `Y=-200..200`
- a concrete cube fixed at `(10, 0, 0.75)`

## Render Output

The USD requests the lidar `PointCloud` render variable with these channels:

- `Coordinates`
- `Intensity`
- `Counts`
- `TimeOffsetNs`

The executable maps the output to CPU, uses `Counts` as the number of valid
point entries, colors `Coordinates` by `Intensity`, and prints mean intensity
and max `TimeOffsetNs` over valid points.

## Renderer Config

Motion BVH is required by the lidar sensor pipeline. The example enables it via
`RendererConfig` at renderer creation time:

```python
renderer = ovrtx.Renderer(ovrtx.RendererConfig(motion_bvh=ovrtx.MotionBvh.ENABLE))
```

## Running

From this directory:

```bash
uv run main.py
```

Write a rerun recording instead of spawning a viewer:

```bash
uv run main.py --rrd lidar_points.rrd
```

Disable rerun and print only the frame summary:

```bash
uv run main.py --no-rr
```

Write a carb log file:

```bash
uv run main.py --no-rr --log
```

By default, `--log` writes to `_output/lidar_example.log` from `OUTPUT_DIR`.
You can also pass a custom path:

```bash
uv run main.py --no-rr --log /tmp/lidar_example.log
```

Expected console output values vary, but a successful run prints one summary:

```text
Loading lidar scene from .../lidar_example.usda...
valid points=..., mean intensity=..., max time offset=... ns
```
