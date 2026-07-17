# Radar Sensor Composite Tensor Example

This example populates an ovstage instance from `radar_example.usda`, attaches
it to the renderer, renders a radar `PointCloud` output through
`ovrtx_step_with_stage`, maps the composite render variable to CPU memory, and
reads the named tensor channels. ovstage owns scene ingest and stepping; sensor
output fetch/map stays a renderer-side concern on the ovrtx APIs. The moving
target approaches the radar, so its `RadialVelocityMs` values are expected to be
negative.

> _“Create a C/C++ radar sensor example that applies required runtime settings before renderer creation, loads an animated radar scene, advances scene time across several simulation steps, reads valid detection data including signal strength and signed radial velocity, prints per-step summaries, reports moving-target observations, and cleans up all resources.”_

## Scene

The scene is Z-up and contains:

- a radar at `(0, 0, 1)` rotated to look along world +X
- an asphalt ground plane spanning `X=-200..200` and `Y=-200..200`
- a steel cube moving from `(30, 4, 0.75)` to `(20, 4, 0.75)`
- a concrete cube fixed at `(30, -4, 0.75)`

The moving cube advances 1 m toward the radar on each of 10 simulation steps.
Approaching radar detections use the radar sign convention and report negative
`RadialVelocityMs`.

## Render Output

The USD requests the radar `PointCloud` render variable with these channels:

- `Coordinates`
- `Counts`
- `RCS`
- `RadialVelocityMs`

The executable maps the output to CPU, uses `Counts` as the number of valid
point entries, and prints min/max `RCS` and `RadialVelocityMs` values for each
step.

## API Flow

The example demonstrates this ovrtx + ovstage attach flow:

1. Create a renderer with motion BVH set to `OVRTX_MOTION_BVH_ENABLE`.
2. Initialize ovstage, create an instance, and attach it with
   `ovrtx_attach_ovstage`.
3. Populate the stage from `radar_example.usda` with
   `ovstage_population_open_usd_from_file` at time 0, then commit the write
   floor with `ovstage_advance_write_floor`.
4. Warm up the sensor pipeline with `ovrtx_step_with_stage` on the committed
   ordinal.
5. For each simulation step, advance USD time with
   `ovstage_population_apply_usd_time` on a fresh ordinal, commit the write
   floor, refresh the renderer with `ovrtx_update_from_stage`, and render with
   `ovrtx_step_with_stage`.
6. Fetch step results and locate the `PointCloud` render variable output.
7. Map the composite render variable to CPU memory.
8. Read the named DLTensor channels and unmap the output.

## Renderer Config

Motion BVH is required for moving-object radial velocity. The example enables
it via the renderer config at creation time (alongside the static-loader package
root):

```c
ovrtx_config_entry_t config_entries[] = {
    ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
    ovrtx_config_entry_motion_bvh(OVRTX_MOTION_BVH_ENABLE),
};
ovrtx_config_t config = { config_entries, 2 };
ovrtx_create_renderer(&config, &renderer);
```

Because ovstage takes over scene ingest, the example renders each committed
ordinal with `ovrtx_step_with_stage` instead of `ovrtx_step`, and advances the
animation with `ovstage_population_apply_usd_time` instead of
`ovrtx_update_stage_from_usd_time`.

The radar orientation is authored in `radar_example.usda`.

## Building

From this directory:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

## Running

```bash
./build/radar-composite-tensor
```

You can also pass an explicit scene path:

```bash
./build/radar-composite-tensor path/to/radar_example.usda
```

Expected output values vary, but a successful run prints 10 steps and a final
observation line:

```text
Stepping moving cube toward radar...
  step 1: valid points=..., RCS min/max=[..., ...], radial velocity min/max=[-..., ...] m/s
  ...
Observed ... detections with |radial velocity| > 0.1 m/s; max |radial velocity| = ... m/s
```
