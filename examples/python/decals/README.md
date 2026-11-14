# Decals

Projects three red RTX wordmarks and three silver metallic NVIDIA logos onto the curved green logo using Path Tracing. The example reuses the documentation test scene, lighting, and geometry.

The example loads the shared scene, advances the runtime stage, and renders enough frames for image quality:

```python
# ovstage owns the scene; ovrtx renders the attached runtime stage.
renderer = ovrtx.Renderer()
stage = ovstage.Stage("ovrtx.example.decals")
renderer.attach_ovstage(stage)

ordinal = 1
ovstage.population.open_usd(stage, SCENE_PATH, ordinal=ordinal)
stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

# Warm up material loading and temporal accumulation before saving.
for _ in range(40):
    renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)

products = renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)
```

It copies the color output to CPU memory before releasing the mapped buffer:

```python
product = products["/Render/Camera"]
frame = product.frames[-1]
mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
view = np.from_dlpack(mapped)
pixels = view.copy()  # Keep pixels valid after the mapped output is released.
del view
mapped.unmap()
del mapped
if args.png:
    args.png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(args.png)
    print(f"Saved {args.png}", file=sys.stderr)
```

## Prerequisites

- Python 3.10–3.13 and [uv](https://docs.astral.sh/uv/)
- An NVIDIA RTX-capable GPU and supported driver
- Unsandboxed runtime execution

## Running

```bash
uv run main.py
uv run main.py --png
uv run main.py --png _output/stickers.png --rrd _output/stickers.rrd
```

With no output options, the example opens Rerun. `--png` saves a PNG without opening a viewer; its default path is `_output/decals.png`. `--rrd PATH` saves a Rerun recording, and can be combined with `--png`.

The first run may take up to 5 minutes while shaders are compiled and cached.

## Scene and masks

`../../../tests/docs/data/ovrtx-test-decals.usda` layers decals over the existing base scene. Only the logo mesh receives them; the ground remains unchanged. The enlarged decals use local X/Y scales of 16 for the upper RTX, 13 for the left and lower-right RTX wordmarks, and 10.6 for each NVIDIA logo. Local Z stays at 12, preserving projection depth. Decals are clipped by the receiver's surface boundaries.

The upper silver NVIDIA logo overlaps the red RTX wordmark, and the lower-right RTX overlaps the right-hand NVIDIA logo. Silver's `omni:decal:priority = 10` places it above red's priority 0. Raising red to 20 reverses the order without moving any decals. The companion scene `../../../tests/docs/data/ovrtx-test-decals-red-on-top.usda` authors this override on `RedRTXA`; `RedRTXB` and `RedRTXC` inherit it. Use distinct priorities when ordering matters, not binding relationship order.

The two grayscale PNG masks are runtime texture assets. White applies the decal and black reveals the lower decal or receiver. The OmniSurface materials explicitly read the red channel with `geometry_opacity_image_alpha_mode = 1`. The silver material uses `metalness = 1`; lighting and reflections come from the renderer.

The committed masks can be regenerated from the original artwork in `artwork/`:

```bash
uv run --no-project --with pillow generate_masks.py
```

Regeneration is optional and requires no downloaded artwork.
