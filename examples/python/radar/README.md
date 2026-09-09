# Radar Sensor Composite Tensor Example

This example loads `radar_example.usda`, renders a radar `PointCloud`, maps the
composite render variable to CPU memory, and visualizes detections in
[rerun.io](https://rerun.io/). Point color is derived from signed
`RadialVelocityMs`: blue is approaching the sensor, green is near zero, and red
is receding.

> _“Create a Python sensor example that loads a scene containing a configured radar and moving target, advances scene time over multiple steps, reads valid detections and signed radial velocity, prints per-step summaries, and optionally visualizes detections with velocity-based colors.”_

## Scene

The scene is Z-up and contains:

- a radar at `(0, 0, 1)` rotated to look along world +X
- an asphalt ground plane spanning `X=-200..200` and `Y=-200..200`
- a steel cube moving from `(30, 4, 0.75)` to `(20, 4, 0.75)`
- a concrete cube fixed at `(30, -4, 0.75)`

The moving cube advances 1 m toward the radar on each of 10 simulation steps.
Approaching radar detections report negative `RadialVelocityMs`.

## Render Output

The USD requests the radar `PointCloud` render variable with these channels:

- `Coordinates`
- `Counts`
- `RadialVelocityMs`

The radar model also auto-enables `Flags`, which the example uses for validity
filtering.

The executable maps the output to CPU, uses `Counts` to bound the delivered
detection entries, and filters that range with the `Flags` `VALID` bit. It
colors the remaining `Coordinates` by `RadialVelocityMs`.

## Renderer Config

Motion BVH is required for moving-object radial velocity. The example enables
it via `RendererConfig` at renderer creation time:

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
uv run main.py --rrd radar_points.rrd
```

Disable rerun and print only the per-step summary:

```bash
uv run main.py --no-rr
```

Write a carb log file:

```bash
uv run main.py --no-rr --log
```

By default, `--log` writes to `_output/radar_example.log` from `OUTPUT_DIR`.
You can also pass a custom path:

```bash
uv run main.py --no-rr --log /tmp/radar_example.log
```

Expected console output values vary, but a successful run prints 10 steps:

```text
Loading radar scene from .../radar_example.usda...
step 1: valid points=..., radial velocity min/max=[-..., ...] m/s
...
```
