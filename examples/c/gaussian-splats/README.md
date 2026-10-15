# gaussian-splats (C/C++)

Build this project with `cmake -B build` and `cmake --build build --config Release`.
The static-loader executable is in `build/static/Release/` on Windows and
`build/static/` on Linux. The shared-loader target adds `-dynamic` to the name.

Pass `../../python/gaussian-splats/gaussian_splats.usda` and an optional output PNG path.
Both loaders save the first frame without preceding warmup frames.

For PT or Minimal, change `omni:rtx:rendermode` on `/Render/Camera` in that scene
to `PathTracing` or `MinimalRendering`. For Minimal, keep the supplied
`omni:rtx:minimal:mode = 3` and `omni:rtx:minimal:dlss:mode = 2` settings.

The following excerpt shows the core workflow from `main.cpp`.

```cpp
// We render a frame by stepping the renderer.
//
// Any sensors whose exposures end during this step will generate a frame
// that will be available in the step result. Since the camera in the loaded
// USD layer is instantaneous (does not specify motion blur or rolling
// shutter), it will generate a frame every time the render is stepped.
//
// To step the renderer we need to tell ovrtx which RenderProducts we're
// interested in, which in this case is the RenderProduct we defined in the
// loading layer.
ovrtx_render_product_set_t render_products = {};
ovx_string_t render_product_str = {"/Render/Camera", strlen("/Render/Camera")};
render_products.render_products = &render_product_str;
render_products.num_render_products = 1;

std::cerr << "Stepping renderer..." << std::endl;
ovrtx_step_result_handle_t step_result_handle = 0;
ovrtx_enqueue_result_t enqueue_result =
    ovrtx_step_with_stage(renderer, render_products, 1.0 / 60.0, stage_ordinal, &step_result_handle);
if (check_and_print_error(enqueue_result, "step")) {
    return cleanup(1);
}

// Wait for the render to complete. Here we'll just block until it's done.
ovrtx_op_wait_result_t wait_result;
result = ovrtx_wait_op(renderer,
                       enqueue_result.op_index,
                       ovrtx_timeout_infinite,
                       &wait_result);
if (check_and_print_error(result, "wait_op")) {
    ovrtx_destroy_results(renderer, step_result_handle);
    return cleanup(1);
}
std::cerr << "Stepped renderer." << std::endl;
```
