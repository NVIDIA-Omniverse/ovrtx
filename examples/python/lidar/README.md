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

The scene explicitly sets `includeInvalidPoints = false`, so invalid returns are
dropped before the point cloud is delivered.

## Alternative Scene

`lidar_example_panels.usda`, beside the default scene, puts the same lidar
1.5 m above the origin, looking along world +X, among panels of different
materials: a glass pane 3 m ahead with a concrete wall 6 m ahead behind it, a
silver panel 3 m to the right, a wide concrete wall 4 m to the left, and a
concrete panel 3 m behind, on the asphalt ground plane of the default scene.
Its labels are `asphalt`, `concrete`, `clear_glass`, and `silver`; every
`Material` prim carries both the `omni:simready:nonvisual` label the lidar
reads and a visual shader, so one prim serves the sensor and a camera. The
scene also carries a `PreviewCamera` with its own `CameraProduct`, which this
example does not step; it exists so the scene can be looked at. The
`PointCloud` request is the same as the default scene's.

Select it with `--scene`:

```bash
uv run main.py --scene lidar_example_panels.usda
```

With that scene, `uv run main.py --scene lidar_example_panels.usda --no-rr`
printed:

```text
valid points=441505, mean intensity=0.3046911656856537, max time offset=99996722 ns
```

## Render Output

The USD requests the lidar `PointCloud` render variable with these channels:

- `Coordinates`
- `Intensity`
- `Counts`
- `TimeOffsetNs`

The executable maps the output to CPU and uses `Counts` to bound the delivered
point entries. Because the scene drops invalid returns, that range is also the
valid-point range. It colors `Coordinates` by `Intensity` and prints mean
intensity and max `TimeOffsetNs` over those points.

## Renderer Config

Motion BVH is required for motion effects in the lidar output. Without it the
lidar still delivers points, but every ray is traced from the sensor's pose at
the end of its frame against a scene that does not move, and the generic lidar
model this example uses logs a warning, once, that its point cloud will have no
motion effects. The example enables motion BVH via `RendererConfig` at renderer
creation time:

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
