# Generic WPM C consumer

Read dense contributions from a Generic WPM sensor through the ovrtx C API.
The C++17 program uses attached ovstage, reuses the Python example's steel
enclosure and configuration layers, and writes valid contributions to CSV.

## Build and run

Use matching ovrtx and ovstage SDKs containing the flattened Generic WPM
schemas. The shared package-fetch helpers follow neighbouring examples; their
default versions are not a confirmed minimum version for this feature.
Point `CMAKE_PREFIX_PATH` at SDKs containing Generic WPM until released-package
availability is verified.

From this directory, with an RTX GPU and a supported driver:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/path/to/ovrtx;/path/to/ovstage"
cmake --build build --config Release
./build/generic-wpm ../../.. depth _output/depth.csv
./build/generic-wpm ../../.. gaussian_bloom _output/bloom.csv
./build/generic-wpm ../../.. mixed _output/mixed.csv --live-edits
```

On Windows, use `build\Release\generic-wpm.exe` for a multi-configuration
generator. The first argument is the ovrtx public source root, containing
`tests/docs/usd/data/` and `examples/python/generic-wpm/scene.usda`.
The output path defaults to `_output/contributions.csv`; a renderer log is
written beside it. The first run may spend several minutes compiling shaders.


## Read contributions

The program finds `/Render/GenericWpm/Contributions` by its complete RenderVar
path, maps it to CPU, and resolves channels and parameters by name.
`copy_tensor()` checks the DLPack type and contiguous shape, respects
`byte_offset`, and copies payloads before the mapping is released.

The following excerpt from `doc-generic-wpm-valid-slots-c` in
[`main.cpp`](main.cpp) writes only valid slots, preserving their dense indices.
`captured` already owns its channel and CPU-parameter copies; it has no borrowed
renderer pointers.

```cpp
for (size_t slot = 0; slot < captured.valid.size(); ++slot) {
    if (!captured.valid[slot]) {
        continue; // Dense holes are not returns.
    }
    size_t index = slot;
    std::array<size_t, 5> coordinates{};
    for (int axis = 4; axis >= 0; --axis) {
        coordinates[axis] = index % captured.shape[axis];
        index /= captured.shape[axis];
    }
    // Coordinates are tile, transmitter, ray, bounce, receiver slot
    // (fastest).
    csv << ordinal << ',' << slot;
    for (auto coordinate : coordinates) {
        csv << ',' << coordinate;
    }
    csv << ',' << captured.distance[slot];
    for (int axis = 0; axis < 3; ++axis) {
        csv << ',' << captured.hit_world[3 * slot + axis];
    }
    csv << ',';
    // Only the colocated, one-bounce depth recipe has range = round-trip
    // / 2.
    if (depth) {
        csv << captured.distance[slot] / 2;
    }
    csv << '\n';
}
```

The five dimensions are `(numTiles, numTx, raysPerTx, maxBounces, groupSize)`.
`rx_slot` is a slot within the selected mapping group, not a receiver index.
The depth recipe produces 15 valid rows and has an 11 m centre range.
The blooming recipe has 1,215 dense slots but writes only 819 valid rows.
`range_m` is deliberately blank outside the colocated, one-bounce depth recipe.

## Live selection and checks

`--live-edits` writes all three `uint32` selectors at one application-owned
ordinal, waits for those writes, advances the stage write floor, and renders
that ordinal. The printed accepted triplet comes from output CPU parameters,
not from the requested values.

The mixed sequence requests `0/0/0`, `1/1/1`, `2/1/1`, invalid `0/1/0`, then
`0/0/0`. Its dense slot counts are 2, 6, 18, 18, and 2. The rejected edit retains
the previous accepted selectors and geometry. The program checks those values,
the depth range, and the blooming valid count and exits nonzero on failure.
The three CTest cases exercise these paths.

This is an output consumer, not a detector or general acoustic/radar simulator.
See the
[Generic WPM guide](../../../docs/sensors/nonvisual/generic_wpm/index.rst) for limits and the
[Python example](../../python/generic-wpm/README.md) for all modality recipes.
