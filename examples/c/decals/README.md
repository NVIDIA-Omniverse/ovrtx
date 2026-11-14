# Decals

Projects three red RTX wordmarks and three silver metallic NVIDIA logos onto the curved green logo using Path Tracing, with the same local scene as the Python example.

The decals retain their enlarged projected width and height, with unchanged projection depth. The upper silver logo overlaps the red RTX wordmark, and the new lower-right RTX overlaps the right-hand NVIDIA logo. Silver uses `omni:decal:priority = 10` and red uses 0; raising red to 20 reverses their ordering. Cutouts reveal the lower decal or the green receiver. See the Python example documentation for the illustrated ordering comparison and equivalent USDA/usd-core authoring snippets.

> _“Create a minimal C API example that loads USD-authored decals through a runtime stage, renders them, and saves the color output.”_

The example loads the shared scene, advances the runtime stage, and renders enough frames for image quality:

```cpp
constexpr ovstage_ordinal_t ordinal = 1;
std::filesystem::path executable_dir =
    std::filesystem::absolute(argc > 0 ? argv[0] : "decals").parent_path();
std::string scene_path = (executable_dir / "ovrtx-test-decals.usda").string();
auto populate = ovstage_population_open_usd_from_file(
    stage,
    {scene_path.c_str(), scene_path.size()},
    ordinal,
    0.0,
    OVSTAGE_POPULATION_DOMAIN_RENDERING);
ovstage_write_floor_desc_t floor {ordinal, OVSTAGE_SCOPE_ALL};
if (wait_population(stage, populate) ||
    wait_stage(stage, ovstage_advance_write_floor(stage, &floor))) {
    std::cerr << "Could not populate the decal scene." << std::endl;
    return cleanup(1);
}

ovx_string_t product_path = {"/Render/Camera", strlen("/Render/Camera")};
ovrtx_render_product_set_t render_products {&product_path, 1};
ovrtx_step_result_handle_t final_handle = OVRTX_INVALID_STEP_RESULT_HANDLE;
for (int frame = 0; frame <= 40; ++frame) {
    ovrtx_step_result_handle_t step_handle = OVRTX_INVALID_STEP_RESULT_HANDLE;
    auto enqueue = ovrtx_step_with_stage(
        renderer, render_products, 1.0 / 60.0, ordinal, &step_handle);
    ovrtx_op_wait_result_t wait_result {};
    if (failed(enqueue, "step") ||
        failed(ovrtx_wait_op(renderer,
                             enqueue.op_index,
                             ovrtx_timeout_infinite,
                             &wait_result),
               "wait_op") ||
        report_wait_errors(wait_result)) {
        return cleanup(1);
    }
    if (frame < 40) {
        ovrtx_destroy_results(renderer, step_handle);
    } else {
        final_handle = step_handle;
    }
}
```

It maps `LdrColor` to CPU memory and writes a PNG:

```cpp
ovrtx_render_product_set_outputs_t outputs {};
if (failed(ovrtx_fetch_results(
               renderer, final_handle, ovrtx_timeout_infinite, &outputs),
           "fetch_results")) {
    return cleanup(1);
}
auto output_handle = find_ldr_color(outputs);
ovrtx_map_output_description_t map_desc {};
map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
ovrtx_render_var_output_t output {};
if (output_handle == OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE ||
    failed(ovrtx_map_render_var_output(renderer,
                                       output_handle,
                                       &map_desc,
                                       ovrtx_timeout_infinite,
                                       &output),
           "map_render_var_output") ||
    output.num_tensors != 1) {
    return cleanup(1);
}
DLTensor const& pixels = *output.tensors[0].dl;
int width = static_cast<int>(pixels.shape[1]);
int height = static_cast<int>(pixels.shape[0]);
std::filesystem::path output_path = executable_dir / "decals.png";
bool wrote_output =
    stbi_write_png(output_path.string().c_str(), width, height, 4, pixels.data, 4 * width) != 0;
ovrtx_cuda_sync_t no_sync {};
ovrtx_unmap_render_var_output(renderer, output.map_handle, no_sync);
ovrtx_destroy_results(renderer, final_handle);
if (!wrote_output) {
    std::cerr << "Could not write " << output_path << std::endl;
    return cleanup(1);
}
std::cout << "Saved " << output_path << std::endl;
```

## Prerequisites

- CMake 3.16 or newer
- C++17 compiler
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver

## Build and run

On Linux with the default single-configuration generator:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
./build/shared/decals-dynamic
```

On Windows or with another multi-configuration generator:

```powershell
cmake -B build
cmake --build build --config Release
.\build\shared\Release\decals-dynamic.exe
```

A successful run writes `decals.png` beside the executable.
