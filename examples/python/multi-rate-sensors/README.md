# Multi-rate Sensors

Learn how to run sensors with different capture rates in one simulation: keep
every sensor active and process its outputs as they arrive. This example steps
at 40 Hz with two lidars (40 and 20 Hz) and two cameras (10 and 20 Hz).
The 20 Hz camera uses a rolling shutter.

## Run

Use an RTX GPU and a supported NVIDIA driver. From this directory:

```bash
uv run main.py
uv run main.py --rrd _output/multi-rate-sensors.rrd
uv run main.py --no-rr --filmstrip _output/full-timeline.png --report _output/full.json
uv run main.py --no-rr --partial-outputs --filmstrip _output/partial-timeline.png --report _output/partial.json
```

The default emits completed captures only. `--partial-outputs` also delivers
intermediate scans and camera exposures. Each run records 40 steps (one simulated
second), starting at simulation time zero without warmup. The first result is
`step=01 t=0.025s`, the end of the first 25 ms step. Use `--steps N` to change the
recorded interval. Animation covers the first two seconds and holds its last pose afterward.

With the default completed-output policy, the schedule repeats every four steps:

| Sensor | Rate | Steps with completed output |
| --- | --- | --- |
| Lidar40 | 40 Hz | 1, 2, 3, 4, ... |
| Lidar20 | 20 Hz | 2, 4, 6, 8, ... |
| Camera10 (global shutter) | 10 Hz | 4, 8, 12, 16, ... |
| Camera20 (rolling shutter) | 20 Hz | 2, 4, 6, 8, ... |

The rolling-shutter exposure spans exactly 50 ms (two steps). Enabling partial
outputs also delivers intermediate Lidar20 and Camera20 outputs on odd steps.

Rerun shows each camera and lidar in a separate view. `--filmstrip` saves a PNG
timeline of the first eight steps: the 10 Hz and 20 Hz cameras on top, followed
by the 40 Hz and 20 Hz lidar point clouds projected from the rolling-shutter
camera's viewpoint. Blank cells mark steps with no output. Each lidar cell
shows only that step's delivered points, with total and in-view return counts.
The lidars output world-space coordinates in metres; their different positions
and fields of view mean the point clouds cover only part of the camera's view.
With partial outputs enabled, the 20 Hz lidar delivers successive 25 ms scan
slices rather than an accumulated scan on even steps. `--png PATH` saves the last
delivered images side by side. The JSON report records delivery steps, capture
times, point counts, and available frame metadata. It skips lidar payloads with
zero delivered points.

The first eight steps of the default run print:

```text
step=01 t=0.025s: Lidar40
step=02 t=0.050s: Camera20, Lidar20, Lidar40
step=03 t=0.075s: Lidar40
step=04 t=0.100s: Camera10, Camera20, Lidar20, Lidar40
step=05 t=0.125s: Lidar40
step=06 t=0.150s: Camera20, Lidar20, Lidar40
step=07 t=0.175s: Lidar40
step=08 t=0.200s: Camera10, Camera20, Lidar20, Lidar40
```

## Choose the output policy

After loading the scene, set `partialOutputs` through ovstage before the first
render step. `false` returns completed captures only; `true` also allows
intermediate outputs. The sensors' capture rates stay the same:

```python
# Set the delivery policy on all four sensors before the first step.
# False returns completed captures only; True also allows intermediate outputs.
ordinal += 1
with ovstage.PathDictionary(stage) as paths:
    path_list = paths.create_path_list_from_strings(
        [
            "/World/Lidar40",
            "/World/Lidar20",
            "/World/Camera10",
            "/World/Camera20",
        ]
    )
    with stage.query_from_path_list(path_list) as query:
        stage.write_attribute(
            query,
            "omni:sensor:Core:partialOutputs",
            ordinal=ordinal,
            tensors=np.full(4, args.partial_outputs, dtype=np.bool_),
            is_array=False,
        ).wait()
    paths.destroy_path_list(path_list)
stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
```

## Keep all sensors active

Advance USD animation separately from the sensor clock, and pass the same product
set every time. This is the essential step-loop fragment from `main.py`:

```python
# USD animation and sensor simulation have separate clocks. Advance both.
ordinal += 1
simulation_time = (step_index + 1) / 40
ovstage.population.update_from_usd_time(stage, ordinal, simulation_time)
stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
products = renderer.step(
    render_products={
        "/Render/Lidar40",
        "/Render/Lidar20",
        "/Render/Camera10",
        "/Render/Camera20",
    },
    delta_time=1 / 40,
    ordinal=ordinal,
)
```

Omitting a product discards its accumulated rendering history and requires
expensive initialization when it is requested again. Keep a slow sensor active
between completed outputs.

## Consume available outputs

Walk the returned products and frames. For lidar, `Counts[0]` is the number of
delivered points; read only that many entries from the point-data arrays.
This scene sets `includeInvalidPoints=false`, so invalid returns have already
been removed:

```python
# Iterate what was returned. A product can be absent or have no frames.
for product_path, product in products.items():
    for frame in product.frames:
        for render_var in frame.render_vars.values():
            with render_var.map(device=ovrtx.Device.CPU) as mapped:
                if render_var.source_name == "PointCloud":
                    count = int(np.from_dlpack(mapped["Counts"])[0])
                    if count == 0:
                        # No points this step; keep the lidar active.
                        continue
                    points = np.from_dlpack(mapped["Coordinates"])[:, :count].T
                    if rr is not None:
                        rr.log(product_path, rr.Points3D(points, radii=0.02))
                    del points
                else:
                    pixels = np.from_dlpack(mapped)
                    if rr is not None:
                        rr.log(product_path, rr.Image(pixels))
```

`partialOutputs=false` suppresses intermediate delivery, while the sensor still
performs the work required to advance and accumulate its capture. With partial
camera output enabled, `LdrColor` returns the last completed image during an
unfinished exposure. It does not provide a partially rendered image. Ignore
these repeated images; use `partialOutputs=false` to receive only newly completed
images.

See [Multi-rate Sensor Simulation](../../../docs/sensors/common/multi_rate.rst) for the
shared timing model, and [the example page](../../../docs/examples/python_multi_rate_sensors.rst)
for the complete walkthrough.
