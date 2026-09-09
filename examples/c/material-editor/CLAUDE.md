# material-editor -- Claude Code Context

## What This Is

A Qt Widgets desktop application that integrates ovrtx rendering with OpenUSD material introspection. It loads a USD scene, lets the user browse/bind materials, view shader graphs, and edit shader parameters with live-rendered feedback.

## Directory Layout

```
material-editor/
├── CMakeLists.txt                    # Build config: Qt6, QtNodes (FetchContent), ovrtx, OpenUSD
├── README.md                         # User-facing docs, prerequisites, build/run instructions
├── CLAUDE.md                         # This file
├── data/
│   ├── material-editor-ball.usda     # Default test scene: sphere, 2 materials, camera, dome light
│   └── studio_kontrast_04.exr        # HDRI environment map used by the dome light
├── render-test/                      # Python sanity-check app (renders same scene via ovrtx Python API)
│   ├── main.py
│   └── pyproject.toml
└── src/
    ├── main.cpp                      # Entry point: ovrtx_initialize/shutdown lifecycle, QApplication
    ├── main_window.hpp/cpp           # QMainWindow: dock layout, signal/slot wiring between widgets
    ├── ovrtx_engine.hpp/cpp          # ovrtx renderer: async step loop, material binding, attribute writes
    ├── viewport_widget.hpp/cpp       # QWidget that paints QImage from CPU-mapped render output
    ├── material_list_widget.hpp/cpp  # QListWidget sidebar for material selection
    ├── node_graph_widget.hpp/cpp     # QtNodes v3 AbstractGraphModel for read-only UsdShade graph
    ├── property_panel_widget.hpp/cpp # Grouped property editors with Sdr metadata, accordions, type dispatch
    └── usd_material_graph.hpp/cpp    # OpenUSD/Sdr: enumerate materials, shaders, inputs, connections
```

## Build & Run

Qt6 and OpenUSD 25.11 must be findable by CMake. OpenUSD must be built with MaterialX support enabled. Pass both via `CMAKE_PREFIX_PATH`.

```bash
# Build (Linux)
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="/path/to/Qt/6.x/gcc_64;/path/to/OpenUSD-25.11"
cmake --build build

# Build (Windows)
cmake -B build -DCMAKE_PREFIX_PATH="C:\Qt\6.5.1\msvc2019_64;C:\path\to\OpenUSD-25.11"
cmake --build build --config Release

# Run (Linux)
./build/material-editor [path/to/materialx-scene.usd]

# Run (Windows) — use the generated launcher that sets PATH for Qt6/OpenUSD DLLs
build\run-material-editor.bat [path\to\materialx-scene.usd]
```

Default scene is `data/material-editor-ball.usda` if no argument is given.

On Windows, CMake generates `run-material-editor.bat` in the build directory at configure time. It prepends the resolved Qt6 and OpenUSD DLL directories to `PATH` before launching the executable, so the DLLs are found without any manual environment setup. The launcher handles both multi-config (Release/Debug) and single-config build layouts.

On Linux, the executable runs directly — rpath is set by CMake so shared libraries are found automatically.

## Important Patterns

### Initialization Order

1. `ovrtx_initialize()` in `main.cpp` -- must happen before any OpenUSD API calls. Bootstraps the USD plugin registry including Sdr parsers. The build-time OpenUSD must include MaterialX support.
2. `engine_->initialize(usda_path)` in `MainWindow` -- creates ovrtx renderer, opens the USD root layer in ovrtx. Must happen before `loadMaterialGraphs()`.
3. `loadMaterialGraphs(usda_path)` -- opens the same stage via OpenUSD C++ API for introspection (Sdr queries, material/shader enumeration).

### Async Render Loop

`OvrtxEngine::startRender(iterations)` does 1 immediate synchronous step for fast visual feedback, then uses a `QTimer(0ms)` to drive chunks of `kChunkSize=4` frames. Each chunk maps the last frame and emits `frameReady(QImage)`. Calling `startRender()` again cancels any in-progress render and restarts. The UI stays responsive because Qt processes events between timer callbacks.

### Sdr Property Discovery

`buildShaderNode()` in `usd_material_graph.cpp`:
1. Calls `findSdrNode()` which tries `GetShaderNodeForSourceType()` with mdl, glslfx, OSL, then all registered types.
2. Enumerates ALL Sdr inputs (not just USD-authored ones) with metadata: `label`, `page`, `type`, `default`.
3. For each input, checks if USD has an authored value -- if so uses that and sets `is_authored=true`, otherwise uses Sdr default.
4. Falls back to authored-only inputs if Sdr lookup fails.

Currently also prints all Sdr property info to stderr for debugging.

### Attribute Writes

- All writes use `OVRTX_BINDING_PRIM_MODE_CREATE_NEW` so non-authored properties can be created in the runtime stage on first edit.
- Material binding uses `ovrtx_set_path_attributes()` with `"material:binding"`.
- Material binding and shader parameter changes wait for the enqueued mutation and call `ovrtx_reset()` to clear path tracer accumulated samples.
- Float/color3f/int/bool/token writes use `ovrtx_write_attribute()` with `ovrtx_make_binding_desc()` and CPU DLPack tensors.
- Multi-component values use shape-based tensor payloads, but the binding descriptor still advertises the component count in `DLDataType::lanes` (for example, `color3f` uses a `[1, 3]` tensor with scalar dtype and a `{kDLFloat, 32, 3}` binding dtype).

### Node Graph

QtNodes v3 `AbstractGraphModel` subclass (`ShaderGraphModel`). Key details:
- Must return `StyleCollection::nodeStyle().toJson().toVariantMap()` for `NodeRole::Style` (nodes won't paint without it).
- Must handle `setNodeData(NodeRole::Size)` -- QtNodes computes node sizes and stores them via this callback.
- `DeviceCoordinateCache` is disabled on node graphics objects after graph creation to prevent clipping on large nodes (many ports exceed max pixmap size).
- Visual input ports are derived from actual graph connections plus all discovered shader inputs, including Sdr-defined defaults that are not authored in USD.
- USD `ui:nodegraph:node:pos` and `ui:nodegraph:node:expansionState` metadata is honored for initial layout and NodeGraph expansion.
- Graph is read-only: `connectionPossible()` returns false, `addNode()`/`deleteNode()`/`deleteConnection()` are no-ops.

## Limitations

- **MaterialX only** -- this example is intended for MaterialX materials. The OpenUSD used at build time must be built with MaterialX support enabled.

## render-test (Python)

`render-test/` contains a standalone Python script that loads the same scene via ovrtx's Python API, binds a material, sets diffuse color, and renders a PNG. Useful for:
- Verifying the scene renders correctly independent of the C++ app
- Comparing C++ attribute edits against the Python API path when investigating renderer-side material behavior

Run with: `cd render-test && uv run main.py`

## Dependencies on ovrtx C API

| Function | Usage |
|----------|-------|
| `ovrtx_initialize()` / `ovrtx_shutdown()` | Process lifecycle, must wrap all USD usage |
| `ovrtx_create_renderer()` / `ovrtx_destroy_renderer()` | Renderer instance management |
| `ovrtx_open_usd_from_file()` | Open USD root layer (async, poll with `ovrtx_wait_op`) |
| `ovrtx_step()` | Render one frame (async) |
| `ovrtx_fetch_results()` / `ovrtx_map_render_var_output()` | Get rendered pixels (CPU map) |
| `ovrtx_set_path_attributes()` | Material binding writes |
| `ovrtx_write_attribute()` | Shader parameter writes |
| `ovrtx_reset()` | Clear path tracer history |
| `ovrtx_make_binding_desc()` / `ovrtx_make_write_cpu_tensor()` | Helpers for constructing write descriptors |
