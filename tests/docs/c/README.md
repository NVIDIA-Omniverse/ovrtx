# C documentation tests

The `ovrtx_docs_tests` CMake target builds the C API documentation examples into
one GoogleTest executable. CTest discovers the individual cases after the
executable has linked. Runtime tests require an RTX GPU and a
[supported NVIDIA driver](../../../docs/driver_requirements.rst).

## SDK selection

The default SDK packages are pinned in
[`ovrtx.cmake`](../../../examples/c/cmake/ovrtx.cmake) and
[`ovstage.cmake`](../../../examples/c/cmake/ovstage.cmake), shared with the C
examples. Use those files as the source of truth for package versions.

## Run the standard target

Use matching headers, loaders, and runtimes from an SDK pair that provides the
APIs used by this checkout, including `ovrtx_get_config()`. From this directory:

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH="/path/to/ovrtx;/path/to/ovstage"
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

After the full target builds, select the multi-rate case with:

```bash
ctest --test-dir build -C Release --output-on-failure \
    -R '^MultiRateSensorConfigurationTest\.MultiRateSensorsKeepEveryProductActive$'
```

