# Python: Carter camera monitor

Drive NVIDIA Carter in a circle and display its previous camera frame in greyscale
on a stationary monitor. Warp processes the camera output on CUDA; ovstage publishes
the result as a runtime texture sampled by an existing `UsdUVTexture` shader and
`UsdPreviewSurface` material.

`carter_monitor.usda` is a trimmed copy of the robot-lineup scene containing only
Carter and the warehouse, plus the monitor and cameras. Carter moves kinematically;
its child camera follows. The monitor starts black and then trails the robot camera
by one frame.

## Run

```bash
uv run main.py --rrd _output/carter-monitor.rrd
uv run main.py --png _output/carter-monitor.png
uv run main.py --frames 8 --fps 4 --period 2 --check --png _output/check.png
```

Requires matching ovrtx/ovstage builds with `OmniRuntimeTexture`, an RTX GPU, and
internet access for the scene's warehouse and Carter payloads. Both renderer and
Warp use CUDA device 0 through the Hydra path.

Default: 180 frames at 30 simulation fps, a six-second circle. `--frames`, `--fps`
and `--period` can be changed independently. With no output flags, Rerun opens and
streams the external view, current robot camera and monitor close-up. `--rrd` saves
those views as an animated recording. `--png` saves the final overview plus sibling
`_first.png`, `_robot.png` and `_monitor.png` images.

`--check` compares the kernel's output with an independent CPU reference and checks
that the rendered monitor samples the previous camera image. These checks add CPU
readbacks; the render-to-Warp-to-texture feedback itself stays on the GPU. Mapping
linear CUDA memory and publishing textures can still involve GPU copies.

## Luminance kernel

Decode sRGB, compute linear-light Rec. 709 luminance, then encode greyscale to sRGB.
The texture declares `sRGB` and preserves the camera image's row order.

```python
@wp.func
def srgb_to_linear(value: float):
    if value <= 0.04045:
        return value / 12.92
    return wp.pow((value + 0.055) / 1.055, 2.4)


@wp.kernel
def camera_luminance(source: wp.array3d(dtype=wp.uint8), texels: wp.array(dtype=wp.uint8)):
    y, x = wp.tid()
    r = srgb_to_linear(float(source[y, x, 0]) / 255.0)
    g = srgb_to_linear(float(source[y, x, 1]) / 255.0)
    b = srgb_to_linear(float(source[y, x, 2]) / 255.0)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    encoded = 12.92 * luminance
    if luminance > 0.0031308:
        encoded = 1.055 * wp.pow(luminance, 1.0 / 2.4) - 0.055
    gray = wp.uint8(wp.clamp(encoded * 255.0 + 0.5, 0.0, 255.0))
    index = (y * source.shape[1] + x) * 4
    texels[index] = gray
    texels[index + 1] = gray
    texels[index + 2] = gray
    texels[index + 3] = wp.uint8(255)
```

## Publish the previous frame

Keep the result and mapping alive until Warp completes, then publish the CUDA buffer.

```python
if products is not None:
    # Consume frame N-1 before rendering N. Keep the result and mapping alive
    # until Warp finishes reading; the texture update never goes through the CPU.
    output = products["/Render/Robot"].frames[-1].render_vars["/Render/Robot/LdrColor"]
    with output.map(device=ovrtx.Device.CUDA, sync_stream=0) as mapped:
        mapped.wait()
        source = wp.from_dlpack(mapped)
        wp.launch(camera_luminance, dim=(height, width), inputs=[source, texels], device="cuda:0")
        wp.synchronize_device("cuda:0")
        del source
    del mapped, output
    stage.write_attribute(texture_query, "texture:data", ordinal=ordinal,
                          is_array=True, tensors=texels).wait()
```

## Move Carter and render

Publish the pose and texture at one ordinal, seal, then render. The camera follows Carter.

```python
angle = math.tau * (frame / args.fps) / args.period
heading = angle + math.pi / 2  # Carter's +X axis follows the circle's tangent.
c, s = math.cos(heading), math.sin(heading)
pose = np.array([[
    [c, s, 0, 0], [-s, c, 0, 0], [0, 0, 1, 0],
    [-5 + 1.4 * math.cos(angle), 4 + 1.4 * math.sin(angle), 0.25, 1],
]], dtype=np.float64)
stage.write_attribute(robot_query, "omni:xform", ordinal=ordinal,
                      is_array=False, tensors=pose).wait()
# The child camera follows Carter. Seal texture and motion together.
stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
products = renderer.step(render_products, 1.0 / args.fps, ordinal=ordinal)
```
