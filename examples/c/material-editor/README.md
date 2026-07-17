# Material Editor

An interactive desktop application that demonstrates how to use the ovrtx C API to build a material editing workflow. The application loads a USD scene, renders it with ovrtx, and provides a GUI for browsing materials, inspecting shader graphs, and editing shader parameters with live-rendered feedback.

> **ovrtx 0.4 compatibility:** This example uses deprecated standalone renderer population and attribute-write APIs for its live material-editing workflow. Use the 0.3-to-0.4 migration skill when moving scene management and edits to ovstage.

> _“Create a C++ Qt desktop application that combines live ovrtx rendering with read-only USD material introspection, showing materials, a rendered viewport, a shader graph, and editable shader properties, while keeping runtime material edits and rendering resets separate from introspection.”_

![Material Editor window](../../../img/example-material-editor.avif)

This example supports **MaterialX materials only**. The OpenUSD installation used to build the example must be built with **MaterialX support enabled** so MaterialX shader definitions are available through Sdr.

The four-panel layout gives you:

- **Material list** (left) -- select which material is bound to the scene geometry
- **Viewport** (center top) -- live path-traced render from ovrtx, progressively refined
- **Node graph** (center bottom) -- read-only visualization of the selected material's UsdShade shader graph
- **Property panel** (right) -- all shader inputs from the USD Sdr registry, grouped into collapsible sections. Properties authored in the USD are highlighted in blue; the rest show the shader's defaults and are editable.

## Prerequisites

### Linux

```bash
sudo apt install build-essential cmake qt6-base-dev
```

You also need **OpenUSD 25.11** headers and shared libraries, built with **MaterialX support enabled**. Pass both Qt6 and OpenUSD to CMake via `CMAKE_PREFIX_PATH`:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="/path/to/Qt/6.x/gcc_64;/path/to/OpenUSD-25.11"
```

An NVIDIA GPU with driver 535+ is required for ovrtx rendering.

### Windows

- [Visual Studio 2022](https://visualstudio.microsoft.com/downloads/) (or 2019) with the C++ desktop workload
- [Qt6](https://www.qt.io/download) -- install the MSVC 2019 64-bit component
- [OpenUSD 25.11](https://github.com/PixarAnimationStudios/OpenUSD) -- built with the matching MSVC toolchain and MaterialX support enabled

Pass both to CMake via `CMAKE_PREFIX_PATH`:

```cmd
cmake -B build -DCMAKE_PREFIX_PATH="C:/Qt/6.5.1/msvc2019_64;C:/path/to/OpenUSD-25.11"
```

### Automatically fetched

These are downloaded by CMake at configure time -- no manual install needed:

- **ovrtx** -- GPU rendering engine (via `cmake/ovrtx.cmake`)
- **QtNodes v3** -- node graph widget (via FetchContent from GitHub)

## Building

**Note:** OpenUSD is used for read-only material introspection and must include MaterialX support. The app opens the USD file supplied at runtime through both OpenUSD and ovrtx.

### Linux

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="/path/to/Qt/6.x/gcc_64;/path/to/OpenUSD-25.11"
cmake --build build
```

### Windows

```cmd
cmake -B build -DCMAKE_PREFIX_PATH="C:/Qt/6.5.1/msvc2019_64;C:/path/to/OpenUSD-25.11"
cmake --build build --config Release
```

## Running

### Linux

```bash
./build/material-editor path/to/materialx-scene.usd
```

### Windows

CMake generates a `run-material-editor.bat` launcher in the build directory that prepends Qt6 and OpenUSD to `PATH` before running the executable:

```cmd
build\run-material-editor.bat path\to\materialx-scene.usd
```

The launcher automatically finds the executable in multi-config (Release/Debug) and single-config build layouts.

If no path is provided, the app loads the included `data/material-editor-ball.usda` test scene.

## USD Scene Requirements

The scene should contain:

- At least one `Mesh` prim with a `MaterialBindingAPI` schema applied
- One or more MaterialX `Material` prims under a `Looks` scope, each containing `Shader` child prims
- A `Camera` and `RenderProduct` (e.g. at `/Render/Camera`) defining the render output
- The target mesh prim path is currently hardcoded to `/World/Sphere` in `main_window.hpp`

## Limitations

- **MaterialX only** -- this example is intended for MaterialX materials. The OpenUSD used at build time must be built with MaterialX support enabled.

## Architecture

The application has two main subsystems: **ovrtx** for GPU rendering and scene manipulation, and **OpenUSD C++ API** for read-only material introspection. They operate on the same USD stage but through different interfaces.

```
┌─────────────────────────────────────────────────────────────────────┐
│  main.cpp                                                           │
│  ovrtx_initialize() / ovrtx_shutdown()                              │
│  Sets up the ovrtx runtime (must happen before any USD API calls)   │
├─────────────────────────────────────────────────────────────────────┤
│  MainWindow  ─── Qt signals/slots wiring between all panels         │
├────────┬──────────┬──────────────┬──────────────┬───────────────────┤
│Material│ Viewport │  Node Graph  │  Property    │  OvrtxEngine      │
│List    │ Widget   │  Widget      │  Panel       │  (ovrtx C API)    │
│        │          │              │              │                   │
│ QList  │ QPainter │ QtNodes v3   │ QFormLayout  │ create_renderer() │
│ Widget │ of       │ graph model  │ with type-   │ open_usd()        │
│        │ QImage   │ (read-only)  │ dispatched   │ step() / fetch()  │
│        │          │              │ editors      │ write_attribute() │
└────────┴──────────┴──────────────┴──────────────┴───────────────────┘
      UI (Qt Widgets)                                 ovrtx C API
      OpenUSD C++ API (read-only introspection)
```

### How ovrtx is used

This example demonstrates the core ovrtx workflow for integrating path-traced rendering into a desktop application:

**1. Lifecycle (`main.cpp`)**

`ovrtx_initialize()` bootstraps the ovrtx runtime, which includes the USD plugin registry and Sdr shader parsers. This must be called before any OpenUSD API calls. `ovrtx_shutdown()` tears it down at exit.

**2. Renderer and scene loading (`OvrtxEngine::initialize`)**

`ovrtx_create_renderer()` creates a renderer instance, then `ovrtx_open_usd_from_file()` opens a `.usda` file as the root layer. Scene loading is asynchronous -- the engine polls `ovrtx_wait_op()` until the operation completes and checks `ovrtx_op_wait_result_t` for operation errors.

**3. Rendering frames (`OvrtxEngine::startRender`)**

Each frame follows a three-step pattern:

1. **`ovrtx_step()`** -- enqueue a render pass targeting a `RenderProduct` prim path. Returns a step handle.
2. **`ovrtx_fetch_results()`** -- retrieve the rendered outputs from the step handle.
3. **`ovrtx_map_render_var_output()`** -- CPU-map the `LdrColor` render variable to get raw RGBA pixel data.

The pixel data is copied from the first `LdrColor` tensor into a `QImage` and the mapping is released with `ovrtx_unmap_render_var_output()`. The engine performs one synchronous step for immediate feedback, then continues rendering in timer-driven chunks of 4 frames so the Qt event loop stays responsive.

**4. Material binding (`OvrtxEngine::bindMaterial`)**

`ovrtx_set_path_attributes()` writes the `material:binding` relationship on a prim, pointing it at a different material path. After rebinding, `ovrtx_reset()` clears the path tracer's accumulated samples to prevent ghosting.

**5. Attribute editing (`OvrtxEngine::writeFloatAttribute`, etc.)**

`ovrtx_write_attribute()` writes individual shader parameters (float, color3f/float3, int, bool, token) directly to ovrtx's internal scene representation (Fabric). Each write uses:

- `ovrtx_make_binding_desc()` to describe which prim and attribute to target
- a CPU DLPack tensor to wrap the value data (`color3f` uses a shape `[1, 3]` payload with scalar tensor dtype, while the binding descriptor advertises a 3-component float attribute)
- `OVRTX_BINDING_PRIM_MODE_CREATE_NEW` so attributes that aren't yet in Fabric are created on first edit
- `ovrtx_wait_op()` to surface async mutation errors immediately
- `ovrtx_reset()` after successful mutations so the path tracer does not blend old accumulated samples with the edited material

### OpenUSD introspection (read-only)

The OpenUSD C++ API (`usd_material_graph.cpp`) opens the same stage independently for read-only introspection:

- **Material enumeration** -- walks the stage for `UsdShadeMaterial` prims
- **Shader graph extraction** -- follows `UsdShadeConnectableAPI` connections to build the node graph topology, including context-specific outputs such as `outputs:mdl:surface` and `outputs:mtlx:surface`
- **Sdr metadata** -- queries the Shader Definition Registry for every input's label, type, page grouping, default value, enum options, and valid ranges. This metadata drives the property panel's UI (accordion groups, sliders, dropdowns)

The introspection layer never writes to the stage -- all mutations go through the ovrtx C API.
