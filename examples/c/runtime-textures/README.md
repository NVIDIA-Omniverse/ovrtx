# C/C++: Runtime textures

Update an attached runtime texture from red to green using CUDA texels.
The material continues referencing `dynamic://runtimeTextureExample`.
Both states are rendered and checked for the expected primary color.

Use matching ovrtx and ovstage packages containing `OmniRuntimeTexture`;
older releases do not support this example. The shared scene reuses the
documentation test plane, camera, and studio environment.

## Run

```bash
cd examples/c/runtime-textures
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
./build/static/runtime-textures
./build/shared/runtime-textures-dynamic
```

Requires CMake 3.18+, a C++17 compiler, and an RTX-capable GPU with a supported driver.
The code uses the C APIs; C++ provides file handling and containers.
On Windows use `build/static/Release/runtime-textures.exe` and
`build/shared/Release/runtime-textures-dynamic.exe`.
CUDA production requires a CUDA development toolkit at configure time;
set `-DCUDAToolkit_ROOT=/path/to/cuda` if needed.
Both producer and renderer use CUDA device 0.
Each executable writes `runtime-textures_before.png` (red) and
`runtime-textures.png` (green) beside itself. Both loader models use attached ovstage.

## Publish a texture update

The following sequence produces packed RGBA8 bytes, waits for writes, and seals
the ordinal before rendering. Keep source buffers alive until the writes complete.

```cpp
const ovstage_ordinal_t ordinal = channel + 1;
// RGBA8 on little-endian supported platforms: red, then green, opaque alpha.
const uint32_t color = channel == 0 ? 0xff0000ffu : 0xff00ff00u;
if (!cuda_ok(cuCtxSetCurrent(context)) ||
    !cuda_ok(cuMemsetD32(gpu_pixels, color, 256 * 256)) ||
    !cuda_ok(cuCtxSynchronize())) return cleanup(1);
int32_t extent[] = {256, 256, 1};
int64_t extent_shape[] = {1};
int64_t byte_shape[] = {256 * 256 * 4};
DLTensor extent_tensor {extent, {kDLCPU, 0}, 1, {kDLInt, 32, 3}, extent_shape, nullptr, 0};
DLTensor byte_tensor {reinterpret_cast<void*>(gpu_pixels), {kDLCUDA, 0}, 1,
                      {kDLUInt, 8, 1}, byte_shape, nullptr, 0};
ovstage_write_data_t extent_write {};
extent_write.tensors = &extent_tensor;
extent_write.tensor_count = 1;
ovstage_write_data_t data_write {};
data_write.tensors = &byte_tensor;
data_write.tensor_count = 1;
data_write.is_array = true;
// Keep all source storage alive until the writes complete successfully.
if (wait_stage(stage, ovstage_write_attribute(stage, query,
        {OVX_INVALID_TOKEN, {"texture:extent", strlen("texture:extent")}}, ordinal,
        extent_write, OVSTAGE_PRIM_MODE_UPSERT)) ||
    wait_stage(stage, ovstage_write_attribute(stage, query,
        {OVX_INVALID_TOKEN, {"texture:data", strlen("texture:data")}}, ordinal,
        data_write, OVSTAGE_PRIM_MODE_UPSERT))) return cleanup(1);
// Seal only after the related metadata and data writes both succeed.
ovstage_write_floor_desc_t floor {ordinal, OVSTAGE_SCOPE_ALL};
if (wait_stage(stage, ovstage_advance_write_floor(stage, &floor))) return cleanup(1);
```
