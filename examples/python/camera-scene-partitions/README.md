# Camera Scene Partitions

Renders an orange cube on the left, a blue torus on the right, and both objects
through three cameras at the same viewpoint. All views share the ground and
studio environment from the documentation assets in `tests/docs/data/`.

```bash
uv run main.py
uv run main.py --rrd _output/camera-scene-partitions.rrd
uv run main.py --no-rr --png _output/camera-scene-partitions.png
```

The snippet below shows how the example loads the authored scene, renders the
left-only, right-only, and combined RenderProducts together, and maps each
`LdrColor` output to CPU memory. It is the `doc-render-camera-scene-partitions`
snippet from `main.py`.

```python
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.camera-scene-partitions")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd(
        stage,
        str(Path(__file__).with_name("scene_partitions.usda")),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    render_product_paths = ("/Render/Left", "/Render/Right", "/Render/Both")
    products = None
    for _ in range(40):
        products = renderer.step(
            render_products=set(render_product_paths),
            delta_time=1.0 / 60.0,
            ordinal=ordinal,
        )

    # Verify every partition camera produced output before accessing its first frame.
    if not all(products[path].frames for path in render_product_paths):
        raise RuntimeError("Not all scene-partition cameras produced an image")

    images = {}
    for render_product_path in render_product_paths:
        frame = products[render_product_path].frames[0]
        mapped = frame.render_vars["/Render/LdrColor"].map(device=ovrtx.Device.CPU)
        images[render_product_path] = np.from_dlpack(mapped).copy()
        del mapped, frame
```
