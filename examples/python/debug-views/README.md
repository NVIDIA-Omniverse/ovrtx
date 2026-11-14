# Debug Views

Renders RT2 G-buffer and heat map debug views from the robot-lineup scene, then logs all
captured images together to Rerun. Each debug view is rendered through a separate
RenderProduct that requests only `LdrColor` and `HdrColor`.

![RT2 G-buffer debug views](../../../docs/img/example-debug-views.avif)

```bash
uv run main.py
uv run main.py --rrd _output/debug-views.rrd
uv run main.py --no-rr --png _output/debug-views.png
```

The example reads each debug view from `HdrColor`. The renderer writes debug views
there when both color RenderVars are requested. Debug views are display-encoded
and clamp directly to 8-bit without HDR tonemapping.

Static views are captured first. The robots then move in alternating directions
for ten frames, and only the two motion views are replaced with moving captures.
The key rendering loop renders every debug view before logging any of them:

```python
    images = {}
    for label, selector in DEBUG_VIEWS:
        render_product_path = f"/Render/{selector}"
        print(f"Rendering {label} ({selector})...")

        products = None
        # Each RenderProduct has independent temporal state, so warm it up before capture.
        for _ in range(max(args.warmup_frames, 0) + 1):
            products = renderer.step(
                render_products={render_product_path},
                delta_time=args.step_dt,
                ordinal=ordinal,
            )

        if not products[render_product_path].frames:
            raise RuntimeError(f"{render_product_path} did not produce an image")

        frame = products[render_product_path].frames[0]
        # Debug views already contain display colors; copy them without HDR tonemapping.
        pixels = _map_hdr_debug_view(frame, render_product_path)
        images[selector] = _to_uint8(pixels)
        del frame, products

    # Capture motion views after all static views so movement cannot change their images.
    motion_selectors = ("targetMotion", "targetMotionArrows")
    robot_paths = [
        "/World/GR1T2_fourier_hand_6dof", "/World/spot", "/World/forklift_c", "/World/forklift_b",
        "/World/carter_v1", "/World/jetbot", "/World/kaya",
    ]
    velocities = np.array(
        [(3, 0, 0), (-3, 0, 0), (2, 0, 1), (-2, 0, 1), (3, 0, 1), (-3, 0, 1), (2, 0, 1)],
        dtype=np.float64,
    )
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(robot_paths)
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:xform")
            transforms = np.full((len(robot_paths), 4, 4), np.nan, dtype=np.float64)
            # Preserve orientation and scale, including the centimetre-scaled forklift payload.
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                while (group := read.fetch_next()) is not None:
                    column = group.columns[0]
                    values = np.from_dlpack(column.dlpack(0)).reshape(-1, 4, 4)
                    for index in range(group.prim_count):
                        transforms[group.prim_index(index)] = values[column.data_row_index(index)]
                    del values
                    stage.release_group(group)
            if not np.all(np.isfinite(transforms)):
                raise RuntimeError("Motion views require transforms for all seven lineup robots")

            matrix_dtype = ovstage.numpy_to_dldatatype(transforms.dtype, lanes=16)
            for selector in motion_selectors:
                render_product_path = f"/Render/{selector}"
                # Refresh previous-frame transforms after the other views' independent warmups.
                for _ in range(2):
                    products = renderer.step(
                        render_products={render_product_path}, delta_time=args.step_dt, ordinal=ordinal
                    )
                    del products

                for motion_step in range(10):
                    # Alternate small offsets to keep robots in view while providing motion every frame.
                    direction = 1.0 if motion_step % 2 == 0 else -1.0
                    transforms[:, 3, :3] += direction * velocities * args.step_dt
                    ordinal += 1
                    tensor = ovstage.make_dltensor(transforms, dtype=matrix_dtype, shape=[len(robot_paths)], ndim=1)
                    stage.write_attribute(query, attribute, ordinal=ordinal, tensors=tensor, is_array=False).wait()
                    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                    products = renderer.step(
                        render_products={render_product_path}, delta_time=args.step_dt, ordinal=ordinal
                    )
                    if motion_step < 9:
                        del products

                if not products[render_product_path].frames:
                    raise RuntimeError(f"{render_product_path} did not produce a moving frame")
                frame = products[render_product_path].frames[0]
                pixels = _map_hdr_debug_view(frame, render_product_path)
                display = _to_uint8(pixels)
                changed_pixels = np.count_nonzero(np.any(display != images[selector], axis=-1))
                print(f"Moving {selector}: {changed_pixels} pixels differ from static capture", flush=True)
                images[selector] = display
                del frame, products
        paths.destroy_path_list(path_list)
```
