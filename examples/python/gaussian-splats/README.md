# gaussian-splats

Render the supplied 73-splat scene in RTPT, PT, or Minimal.
The default is one frame without warmup. Use `--steps` to request later frames.

`uv run main.py --mode rtpt --png _output/render.png`

`uv run main.py --rrd _output/render.rrd`

## Feature code

The following code loads the scene, selects a render mode, renders the requested frames,
and copies the rendered image before releasing its CPU mapping.

```python
renderer = ovrtx.Renderer()
stage = ovstage.Stage("ovrtx.example.gaussian-splats")
try:
    renderer.attach_ovstage(stage)
    # Layer a mode override over the same scene; render one mode per run.
    layer = ('#usda 1.0\n(subLayers = [@' + args.scene.resolve().as_posix() + '@])\n'
             'over "Render" {\n over "Camera" {\n token omni:rtx:rendermode = "' + mode + '"\n }\n }\n')
    ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    # Render one frame by default; --steps can request later frames.
    for _ in range(args.steps):
        products = renderer.step(render_products={"/Render/Camera"}, delta_time=1/60, ordinal=1)
    output = products["/Render/Camera"].frames[0].render_vars["/Render/Camera/LdrColor"]
    mapped = output.map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    pixels = view.copy()
    del view
    mapped.unmap()
    del mapped, output, products
finally:
    renderer.detach_ovstage()
    renderer.destroy()
    stage.destroy()
```
