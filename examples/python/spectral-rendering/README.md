# Python: Spectral Rendering

Render the rect-light scene with `white`, `blackbody3200`, `daylight`, `sodium`, or `mercury` illumination and `rgb` or `spectral` transport.
A dispersive diamond rests on a pavilion facet in front of the two spheres,
with its crown facing 65 degrees camera-left. Rendering uses 32 maximum bounces,
denoising, and glossy/diffuse/emissive firefly thresholds of 10,000.
The scene, camera, and 6400-lumen light power remain fixed. Run each transport
in a separate process because the material backend is initialized at startup.

![Spectral PathTracing under white, sodium, and mercury illumination](../../../docs/img/spectral-banner.avif)

*Spectral PathTracing under white (left), sodium (center), and mercury (right).*

```bash
# Enter the spectral rendering example directory.
cd examples/python/spectral-rendering
# Render low-pressure sodium with RGB transport and save a PNG.
uv run main.py --illuminant sodium --transport rgb --png _output/sodium-rgb.png
# Render low-pressure sodium with spectral PathTracing and save a PNG.
uv run main.py --illuminant sodium --transport spectral --png _output/sodium-spectral.png
# Render mercury light with RGB transport and save a PNG.
uv run main.py --illuminant mercury --transport rgb --png _output/mercury-rgb.png
# Render mercury light with spectral PathTracing and save a PNG. Also save a Rerun recording.
uv run main.py --illuminant mercury --transport spectral --png _output/mercury-spectral.png --rrd _output/mercury.rrd
```

Transport defaults to RGB; pass `--transport spectral` to enable spectral PathTracing.

Use `--spp` to change the default 4096 samples per pixel, and `--size` to
change the default 512-pixel square output. `--png PATH` saves a headless image;
`--rrd PATH` saves a Rerun recording. With neither option, Rerun opens a viewer.
`--hdr PATH.npy` also saves linear `HdrColor` for
numerical comparisons. Renderer diagnostics go to `_output/spectral.log`;
use `--log PATH` for a separate log per render.

The following snippet sets the startup configuration.

```python
# Select the process-wide material backend before creating any renderer.
config = ovrtx.RendererConfig(
    enable_spectral_rendering=args.transport == "spectral",
    log_file_path=str(args.log),
)
renderer = ovrtx.Renderer(config=config)
```

The following snippet selects the shared scene variants and renders one converged PathTracing frame.

{% raw %}
```python
# Camera prims share geometry/exposure; only their spectral response differs.
camera_path = {"cie1931": "/World/Camera", "canon5d": "/World/Canon5D", "sony_a7iv": "/World/SonyA7IV"}[args.camera]
# Apply the API only when requested; its default curves provide CIE 1931 responsivity.
white_point_layer = ""
if args.white_point is not None:
    camera_name = camera_path.rsplit("/", 1)[1]
    white_point_layer = f'''over "{camera_name}" (prepend apiSchemas = ["PhysicalCameraResponsivityAPI"]) {{
        float physical:responsivity:colorTemperature = {args.white_point}
    }}'''
scene_path = Path(__file__).with_name("spectral.usda").resolve()
layer = f"""#usda 1.0
(
    subLayers = [@{scene_path.as_posix()}@]
)
over "World" {{
    {white_point_layer}
    over "RectLight" (variants = {{ string illuminant = "{args.illuminant}" }}) {{}}
}}
over "Render" {{
    over "Camera" (variants = {{ string transport = "{args.transport}" }}) {{
        rel camera = <{camera_path}>
        uint omni:rtx:pt:samplesPerPixel = {args.spp}
        int2 resolution = ({args.size}, {args.size})
    }}
}}
"""
ordinal = 1
ovstage.population.open_usd_from_string(stage, layer, ordinal=ordinal)
stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
# PathTracing accumulates the requested samples within one step.
products = renderer.step(render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=ordinal)
frame = products["/Render/Camera"].frames[-1]
mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
pixels = np.from_dlpack(mapped).copy()
mapped.unmap()
del mapped
```
{% endraw %}


## Camera responsivity example

Compare the original Canon EOS 5D and Sony α7 IV responses from rawtoaces with
the default CIE 1931 observer. Render both D65 daylight and sodium with a fixed
D65 calibration for each camera:

```bash
# Repeat the comparison under D65 daylight and sodium illumination.
for light in daylight sodium; do
  # Compare the CIE 1931 observer, Canon EOS 5D, and Sony α7 IV.
  for camera in cie1931 canon5d sony_a7iv; do
    # Render this illuminant and camera response with spectral PathTracing; save the named outputs.
    uv run main.py --transport spectral --illuminant "$light" --camera "$camera" --png "_output/${light}-${camera}.png" --hdr "_output/${light}-${camera}.npy"
  done # Finish this camera comparison.
done # Finish both illuminants.
```

Camera selection defaults to `cie1931`. Custom camera responses require spectral
transport. Geometry, exposure, and light power stay fixed.

## White-point adaptation

Select the camera white point independently of the light. These commands render
eight images with CIE 1931 responsivity, 4096 samples, 32 bounces, denoising,
and firefly thresholds of 10,000. The camera responsivity API is applied when
a white point is supplied; its default channel curves retain the CIE observer.

```bash
# Compare tungsten-like blackbody illumination with D65 daylight.
for light in blackbody3200 daylight; do
  # Select the camera white point explicitly; no scene estimation is performed.
  for white in 3200 5000 5600 6504; do
    # Save a spectral image using CIE 1931 responsivity and sensor-channel white balance.
    uv run main.py --transport spectral --illuminant "$light" --white-point "$white" --png "_output/${light}-wb${white}.png"
  done # Finish the four white points.
done # Finish both illuminants.
```

![Blackbody 3200 K and D65 at four camera white points](../../../docs/img/spectral-white-balance.avif)

*Top: blackbody 3200 K. Bottom: D65. Columns: 3200, 5000, 5600, and 6504 K.*
