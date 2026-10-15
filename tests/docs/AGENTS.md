# AGENTS.md - Documentation Tests

This directory ensures every code example in the ovrtx docs is tested. **Test snippets are the single source of truth** -- docs and skills reference them, never the other way around.

## Why This Exists

Hand-written code blocks in docs go stale. They use wrong API signatures, miss imports, and teach patterns that don't actually work. By requiring all doc code to live in tested files with snippet markers, the docs break when the API changes -- which is the point.

## Architecture

### Three independent subprojects

The split is primarily about separation of concerns: `usd/` tests demonstrate USD data layout and can run anywhere without a GPU, while `python/` tests exercise the ovrtx runtime and require a GPU. Keeping them separate also means simpler dependencies and faster feedback -- you can validate all USDA and USD Python API examples without touching ovrtx.

| Directory | Dependencies | GPU? | Purpose |
|-----------|-------------|------|---------|
| `python/` | `ovrtx`, `pytest`, `numpy`, `Pillow` | Yes | Test ovrtx API snippets (step, map, render) |
| `usd/`    | `usd-core`, `pytest` | No  | Validate USDA files + test USD Python API snippets |
| `c/`      | CMake, GoogleTest, ovrtx C API | Yes | Test C API snippets (step, map, render) |

Python and USD suites each have their own `pyproject.toml` and run via `uv run pytest`. The C suite uses CMake + GoogleTest and runs via `ctest`.

### ovrtx 0.4 port status

- New tests and snippets in `python/` always use attached ovstage. The `@pytest.mark.allow_deprecated_ovrtx_api` marker is reserved for retained tests whose subject is the deprecated renderer-owned API contract; other deprecated use remains in the ovstage migration summary.
- `c/` has not been ported to attached ovstage and remains compatibility coverage for deprecated standalone renderer stage APIs.
- `usd/` validates USD content directly and does not exercise either stage-ownership model.

### Data flow: test -> snippet -> skill -> doc

```
test file (tests/docs/python/*.py, tests/docs/usd/*.py)
    contains snippet markers: # [snippet:name] ... # [/snippet:name]
        |
        v
skills (root ../../skills/*/SKILL.md and local skills/*/SKILL.md)
    reference snippets via > **Source:** directives
        |
        v
RST doc (docs/*.rst)
    uses literalinclude with :start-after: / :end-before:
        |
        v
rendered HTML
```

Skills are the primary consumer of snippets -- they're what agents read to learn how to use the API. Keeping skills up to date is at least as important as keeping the human-facing docs up to date. When you add or change a snippet, update every skill that references it, and check if the skills are really appropriate for the snippets or if new ones need to be created (ask your human before creating new ones).

USDA data files under `data/` and `usd/data/` follow the same pattern -- snippet markers inside `.usda` files, referenced by `literalinclude` in RST and by skills.

## Directory Layout

```
tests/docs/
├── AGENTS.md                                    # This file
├── CLAUDE.md                                    # Redirects to AGENTS.md
├── pyproject.toml                               # Meta-project root
├── skills/                                      # Task-oriented skills for this subtree
│   ├── adding-doc-snippets/SKILL.md
│   └── sublayer-test-scenes/SKILL.md
├── python/
│   ├── pyproject.toml                           # ovrtx + pytest
│   ├── conftest.py                              # Pytest configuration
│   ├── check_gaussian_splats_c_example.py        # Validate packaged C renders against hidden splats
│   ├── check_usd_plugin_paths_c_example.py       # Validate packaged C registration examples
│   ├── test_all_attributes.py                   # Authored USD attribute read/write snippets and coverage
│   ├── test_camera_aovs.py                      # Smoke tests for all camera AOVs (SDG snippet + full RTPT catalog, 82 AOVs)
│   ├── test_camera_sensors.py                   # Snippets for camera_sensors.rst
│   ├── test_camera_feature_examples.py           # End-to-end public Camera example smoke tests
│   ├── test_gaussian_splats.py                  # Visible/hidden splats in each mode, first and 32nd frame
│   ├── test_render_modes.py                     # Tests for camera render modes
│   ├── test_sensor_configuration.py             # Snippets for sensor_configuration.rst
│   └── test_usd_plugin_paths.py                 # External-USD registration integration test
├── usd/
│   ├── pyproject.toml                           # usd-core + pytest
│   ├── conftest.py                              # validate_usda() helper
│   ├── data/
│   │   ├── camera_sensor_render_product.usda    # USDA with snippet markers
│   │   ├── gaussian_splat.usda                     # One ParticleField Gaussian splat
│   │   ├── minimal_render_product.usda
│   │   ├── multi_render_product_shared_vars.usda
│   │   └── plugin_physical_light.usda           # Existing ovrtx schema application
│   ├── test_camera_sensors_usda.py              # Validates USDA structure
│   ├── test_gaussian_splats_usda.py             # Validates the public Gaussian scene arrays
│   ├── test_sensor_config_usda.py               # Validates USDA structure
│   └── test_usd_python_examples.py              # USD Python API equivalents, including physical lighting
└── c/
    ├── CMakeLists.txt                           # CMake project (GoogleTest + ovrtx C API)
    ├── helpers.h                                # Shared test helpers
    ├── test_all_attributes.cpp                  # Authored USD attribute read/write snippets and coverage (C)
    ├── test_camera_aovs.cpp                     # Smoke tests for all camera AOVs (C)
    ├── test_camera_sensors.cpp                  # C snippets for camera_sensors.rst
    ├── test_sensor_configuration.cpp            # C snippets for sensor_configuration.rst
    └── test_usd_plugin_paths.cpp                # Path count, truncation, and borrowed lifetime
```

## Rules

### Snippets are the source of truth

1. **Never write inline code blocks in RST for API usage.** All substantial code examples must live in a test file with snippet markers, then be pulled into RST via `literalinclude`.
2. **Small fragments are OK inline.** Single-line USDA like `rel camera = </World/Camera>` can stay as `code-block` in RST -- don't over-engineer.

### Naming conventions

- Snippet names are kebab-case, prefixed with `doc-`: e.g., `doc-step-and-map-camera-outputs`.
- USD Python API snippets append `-python`: e.g., `doc-camera-sensor-render-product-python`.
- Names must be unique across the entire `tests/docs/` tree.

### USDA examples get two tabs

Every substantial USDA block in the docs should be a `tab-set` with:
- **USDA tab** -- `literalinclude` from a `.usda` data file in `usd/data/`
- **Python tab** -- `literalinclude` from `usd/test_usd_python_examples.py`

### RST directive format

For USDA (`.usda` files, `#` comment markers):
```rst
.. literalinclude:: ../tests/docs/usd/data/some_file.usda
   :language: usda
   :start-after: # [snippet:doc-snippet-name]
   :end-before: # [/snippet:doc-snippet-name]
```

For Python (`.py` files, need `:dedent:`):
```rst
.. literalinclude:: ../tests/docs/python/test_something.py
   :language: python
   :start-after: # [snippet:doc-snippet-name]
   :end-before: # [/snippet:doc-snippet-name]
   :dedent:
```

### Where things go

| Content type | Test location | Notes |
|-------------|--------------|-------|
| ovrtx Python API (step, map, render) | `python/test_*.py` | Needs GPU to run |
| USDA validation | `usd/test_*_usda.py` | Parses `.usda` data files, checks prim structure |
| USD Python API (`from pxr import ...`) | `usd/test_usd_python_examples.py` | No GPU needed |
| USDA data files | `usd/data/*.usda` | Must have snippet markers |
| C API examples | `c/test_*.cpp` | CMake + GoogleTest; snippet markers use `// [snippet:...]` |

### Debug artifacts

Runtime tests that create an ovrtx renderer should write renderer logs under
their suite's `_output/` directory. Tests that generate images for debugging or
visual assertions should also write them under `_output/` with stable,
descriptive names that include the test area and visual state, for example
`picking_selection.selection_outline.selected.png` or
`PickingSelection.SelectionOutline.delta_selected_vs_baseline.png`.

### The sublayer pattern

ovrtx only supports one root layer. When a test needs a base scene plus additional prims (like RenderProducts), it must use a single `open_usd_from_string()` / `ovrtx_open_usd_from_string()` call with a USD `subLayers` composition arc. See `skills/sublayer-test-scenes/SKILL.md` for the pattern.

## Running Tests

```bash
# USDA validation + USD Python API (no GPU)
cd tests/docs/usd && uv run pytest -v

# ovrtx Python API (GPU required)
cd tests/docs/python && uv run pytest -v

# C API tests (GPU required, must build first)
cd tests/docs/c
cmake -B build -DCMAKE_PREFIX_PATH=/path/to/ovrtx
cmake --build build
cd build && ctest --output-on-failure

# All suites at once (Linux)
./tests/docs/run_tests.sh -v
```

## Adding New Doc Pages

See `skills/adding-doc-snippets/SKILL.md` for the step-by-step workflow.

## Current Snippet Inventory

**Agents MUST keep this table up to date.** When you add, rename, move, or remove a snippet, update this table in the same change.

| Snippet | Source file | Used in RST |
|---------|-----------|-------------|
| `doc-dlss-nr-render-product` | `usd/data/dlss_nr.usda` | `sensors/cameras/render_modes/dlss_nr.rst` |
| `doc-dlss-nr-render-product-python` | `usd/test_dlss_nr.py` | `sensors/cameras/render_modes/dlss_nr.rst` |
| `doc-spectral-config-python` | `examples/python/spectral-rendering/main.py` | `sensors/cameras/render_modes/spectral_rendering.rst`, `examples/python_spectral_rendering.rst` |
| `doc-spectral-config-c` | `examples/c/spectral-rendering/main.cpp` | `sensors/cameras/render_modes/spectral_rendering.rst`, `examples/c_spectral_rendering.rst` |
| `doc-spectral-authoring` | `usd/data/spectral_rendering.usda` | `sensors/cameras/render_modes/spectral_rendering.rst` |
| `doc-spectral-authoring-python` | `usd/test_spectral_rendering.py` | `sensors/cameras/render_modes/spectral_rendering.rst` |
| `doc-spectral-illuminant` | `examples/python/spectral-rendering/spectral.usda` | Example source only |
| `doc-spectral-render-product` | `examples/python/spectral-rendering/spectral.usda` | Example source only |
| `doc-spectral-select-python` | `examples/python/spectral-rendering/main.py` | `examples/python_spectral_rendering.rst` |
| `doc-spectral-select-c` | `examples/c/spectral-rendering/main.cpp` | `examples/c_spectral_rendering.rst` |
| `doc-spectral-save-c` | `examples/c/spectral-rendering/main.cpp` | `examples/c_spectral_rendering.rst` |
| `doc-light-shaping` | `usd/data/light_shaping.usda` | `lights/shaping_and_ies.rst` |
| `doc-light-shaping-python` | `usd/test_usd_python_examples.py` | `lights/shaping_and_ies.rst` |
| `doc-light-shaping-ies` | `usd/data/light_shaping.usda` | `lights/shaping_and_ies.rst` |
| `doc-light-shaping-ies-python` | `usd/test_usd_python_examples.py` | `lights/shaping_and_ies.rst` |
| `doc-light-linking` | `usd/data/light_linking.usda` | `lights/light_linking.rst` |
| `doc-light-linking-python` | `usd/test_usd_python_examples.py` | `lights/light_linking.rst` |
| `doc-ghost-lights` | `usd/data/ghost_lights.usda` | `lights/ghost_lights.rst` |
| `doc-ghost-lights-python` | `usd/test_usd_python_examples.py` | `lights/ghost_lights.rst` |
| `doc-common-light-attributes` | `usd/data/light_types.usda` | `lights/common_attributes.rst` |
| `doc-common-light-attributes-python` | `usd/test_usd_python_examples.py` | `lights/common_attributes.rst` |
| `doc-physical-lighting` | `usd/data/physical_lighting.usda` | `lights/physical_lighting.rst` |
| `doc-physical-lighting-python` | `usd/test_usd_python_examples.py` | `lights/physical_lighting.rst` |
| `doc-distant-light` | `usd/data/light_types.usda` | `lights/distant_light.rst` |
| `doc-distant-light-python` | `usd/test_usd_python_examples.py` | `lights/distant_light.rst` |
| `doc-sphere-light` | `usd/data/light_types.usda` | `lights/sphere_light.rst` |
| `doc-sphere-light-python` | `usd/test_usd_python_examples.py` | `lights/sphere_light.rst` |
| `doc-rect-light` | `usd/data/light_types.usda` | `lights/rect_light.rst` |
| `doc-rect-light-python` | `usd/test_usd_python_examples.py` | `lights/rect_light.rst` |
| `doc-projector-light` | `usd/data/projector_lights.usda` | `lights/rect_light.rst` |
| `doc-projector-light-python` | `usd/test_usd_python_examples.py` | `lights/rect_light.rst` |
| `doc-projector-opencv-calibration` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `lights/rect_light.rst`, `examples/python_projector_light_calibration.rst`, and the example README |
| `doc-projector-octahedral-directions` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `lights/rect_light.rst`, `examples/python_projector_light_calibration.rst`, and the example README |
| `doc-projector-opencv-project` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `lights/rect_light.rst`, `examples/python_projector_light_calibration.rst`, and the example README |
| `doc-projector-write-direction-texture` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `lights/rect_light.rst`, `examples/python_projector_light_calibration.rst`, and the example README |
| `doc-projector-generate-and-render` | `examples/python/projector-light-calibration/main.py` | `examples/python_projector_light_calibration.rst` and the example README |
| `doc-disk-light` | `usd/data/light_types.usda` | `lights/disk_light.rst` |
| `doc-disk-light-python` | `usd/test_usd_python_examples.py` | `lights/disk_light.rst` |
| `doc-cylinder-light` | `usd/data/light_types.usda` | `lights/cylinder_light.rst` |
| `doc-cylinder-light-python` | `usd/test_usd_python_examples.py` | `lights/cylinder_light.rst` |
| `doc-dome-light` | `usd/data/light_types.usda` | `lights/dome_light.rst` |
| `doc-dome-light-python` | `usd/test_usd_python_examples.py` | `lights/dome_light.rst` |
| `doc-finite-dome-light` | `usd/data/finite_dome_lights.usda` | `lights/dome_light.rst` |
| `doc-finite-dome-light-python` | `usd/test_usd_python_examples.py` | `lights/dome_light.rst` |
| `doc-mesh-light` | `usd/data/mesh_lights.usda` | `lights/mesh_lights.rst` |
| `doc-mesh-light-python` | `usd/test_usd_python_examples.py` | `lights/mesh_lights.rst` |
| `doc-enable-mesh-light-sampling` | `usd/data/mesh_lights.usda` | `lights/mesh_lights.rst` |
| `doc-enable-mesh-light-sampling-python` | `usd/test_usd_python_examples.py` | `lights/mesh_lights.rst` |
| `doc-camera-sensor-render-product` | `usd/data/camera_sensor_render_product.usda` | `camera_sensors.rst` |
| `doc-camera-sensor-render-product-python` | `usd/test_usd_python_examples.py` | `camera_sensors.rst` |
| `doc-camera-attributes` | `usd/data/camera_attributes.usda` | `sensors/cameras/usd_camera_attributes.rst` |
| `doc-camera-attributes-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/usd_camera_attributes.rst` |
| `doc-camera-lens-calibration` | `usd/data/camera_lens_calibration.usda` | `sensors/cameras/lens_calibration.rst` |
| `doc-camera-lens-calibration-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/lens_calibration.rst` |
| `doc-camera-rolling-shutter` | `usd/data/camera_rolling_shutter.usda` | `sensors/cameras/rolling_shutter.rst` |
| `doc-camera-rolling-shutter-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/rolling_shutter.rst` |
| `doc-create-rolling-shutter-renderer` | `python/test_support_api.py` | `sensors/cameras/rolling_shutter.rst` |
| `doc-create-rolling-shutter-renderer-c` | `c/test_support_api.cpp` | `sensors/cameras/rolling_shutter.rst` |
| `doc-camera-scene-partitions` | `usd/data/camera_scene_partitions.usda` | _(authoring test)_ |
| `doc-camera-scene-partitions-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/scene_partitions.rst` |
| `doc-render-calibrated-cameras` | `examples/python/camera-lens-calibration/main.py` | _(example only)_ |
| `doc-render-rolling-shutter` | `examples/python/camera-rolling-shutter/main.py` | _(example only)_ |
| `doc-example-camera-scene-partitions` | `examples/python/camera-scene-partitions/scene_partitions.usda` | `sensors/cameras/scene_partitions.rst` |
| `doc-render-camera-scene-partitions` | `examples/python/camera-scene-partitions/main.py` | `sensors/cameras/scene_partitions.rst`, `examples/python_camera_scene_partitions.rst`, and the example README |
| `doc-author-gbuffer-debug-views` | `examples/python/debug-views/main.py` | _(example only)_ |
| `doc-render-gbuffer-debug-views` | `examples/python/debug-views/main.py` | `examples/python_debug_views.rst` and the example README |
| `doc-step-and-map-camera-outputs` | `python/test_camera_sensors.py` | `camera_sensors.rst` |
| `doc-camera-aov-smoke-test` | `python/test_camera_aovs.py` | _(test only — SDG AOVs; see also `test_all_rtpt_aovs` in same file for full RTPT catalog)_ |
| `doc-camera-aov-smoke-test-c` | `c/test_camera_aovs.cpp` | _(test only)_ |
| `doc-lpe-render-vars` | `usd/data/light_path_expressions.usda` | `sensors/cameras/light_path_expressions.rst` |
| `doc-lpe-render-vars-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/light_path_expressions.rst` |
| `doc-example-lpe-render-vars` | `examples/python/lpes/lpe-layer.usda` | `examples/python_lpes.rst` |
| `doc-example-lpe-render-vars-python` | `usd/test_usd_python_examples.py` | `examples/python_lpes.rst` |
| `doc-read-lpe-outputs` | `examples/python/lpes/main.py` | `examples/python_lpes.rst` and the example README |
| `doc-lpe-initialize-rerun` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-create-renderer` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-load-scene` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-step` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-minimal-render-product` | `usd/data/minimal_render_product.usda` | `sensor_configuration.rst` |
| `doc-minimal-render-product-python` | `usd/test_usd_python_examples.py` | `sensor_configuration.rst` |
| `doc-multi-render-product-shared-vars` | `usd/data/multi_render_product_shared_vars.usda` | `sensor_configuration.rst` |
| `doc-multi-render-product-shared-vars-python` | `usd/test_usd_python_examples.py` | `sensor_configuration.rst` |
| `doc-step-multiple-render-products` | `python/test_sensor_configuration.py` | `sensor_configuration.rst` |
| `doc-add-render-config-layer` | `python/test_sensor_configuration.py` | `sensor_configuration.rst` |
| `doc-step-and-map-camera-outputs-c` | `c/test_camera_sensors.cpp` | `camera_sensors.rst` |
| `doc-step-multiple-render-products-c` | `c/test_sensor_configuration.cpp` | `sensor_configuration.rst` |
| `doc-multi-rate-lidar-usda`, `doc-multi-rate-camera-usda` | `examples/python/multi-rate-sensors/multi_rate.usda` | `sensors/multi_rate.rst` |
| `doc-multi-rate-lidar-python`, `doc-multi-rate-camera-python` | `usd/test_usd_python_examples.py` | `sensors/multi_rate.rst` |
| `doc-multi-rate-step`, `doc-multi-rate-partial-outputs` | `examples/python/multi-rate-sensors/main.py` | `sensors/multi_rate.rst`, `examples/python_multi_rate_sensors.rst`, and the example README |
| `doc-multi-rate-read-outputs` | `examples/python/multi-rate-sensors/main.py` | `examples/python_multi_rate_sensors.rst` and the example README |
| `doc-multi-rate-step-c`, `doc-multi-rate-partial-outputs-c` | `c/test_sensor_configuration.cpp` | `sensors/multi_rate.rst` |
| `doc-observer-cameras-usda` | `examples/c/sensor-observer/conveyor.usda` | `examples/c_sensor_observer.rst` |
| `doc-observer-cameras-python` | `usd/test_sensor_observer_usda.py` | `examples/c_sensor_observer.rst` |
| `doc-observer-output-policy-c`, `doc-observer-step-c`, `doc-observer-copy-outputs-c` | `examples/c/sensor-observer/main.cpp` | `examples/c_sensor_observer.rst` and the example README |
| `doc-observer-output-policy-python`, `doc-observer-simulation-step-python`, `doc-observer-view-step-python` | `python/test_sensor_observer.py` | `examples/c_sensor_observer.rst` and `stepping-and-rendering` skill |
| `doc-add-render-config-layer-c` | `c/test_sensor_configuration.cpp` | `sensor_configuration.rst` |
| `doc-path-tracing-render-product` | `python/test_render_modes.py` | `sensors/cameras/render_modes.rst` |
| `doc-bind-material` | `python/test_base.py` | `materials/material_binding.rst` |
| `doc-bind-material-c` | `c/test_base.cpp` | `materials/material_binding.rst` |
| `doc-uv-projector-api` | `examples/python/projectors/projectors.usda` | `materials/projectors.rst` |
| `doc-uv-projector-binding` | `examples/python/projectors/projectors.usda` | `materials/projectors.rst` |
| `doc-create-decal` | `usd/data/decal.usda` | `materials/decals.rst` |
| `doc-create-decal-python` | `usd/test_usd_python_examples.py` | `materials/decals.rst` |
| `doc-bind-decal` | `usd/data/decal_binding.usda` | `materials/decals.rst` |
| `doc-bind-decal-python` | `usd/test_usd_python_examples.py` | `materials/decals.rst` |
| `doc-decals-python-render` | `examples/python/decals/main.py` | `examples/python_decals.rst` |
| `doc-decals-python-save` | `examples/python/decals/main.py` | `examples/python_decals.rst` |
| `doc-decals-c-render` | `examples/c/decals/main.cpp` | `examples/c_decals.rst` |
| `doc-decals-c-save` | `examples/c/decals/main.cpp` | `examples/c_decals.rst` |
| `doc-decal-silver-mask-usda` | `data/ovrtx-test-decals.usda` | `examples/python_decals.rst` |
| `doc-decal-silver-mask-python` | `usd/test_decals_usda.py` | `examples/python_decals.rst` |
| `doc-decal-ordering-usda` | `data/ovrtx-test-decals-red-on-top.usda` | `examples/python_decals.rst` |
| `doc-decal-ordering-python` | `usd/test_decals_usda.py` | `examples/python_decals.rst` |
| `doc-set-render-setting` | `python/test_base.py` | `sensors/configuration.rst` |
| `doc-set-render-setting-c` | `c/test_base.cpp` | `sensors/configuration.rst` |
| `doc-set-view-lighting` | `python/test_base.py` | _(skill only)_ |
| `doc-warmup` | `python/test_base.py` | _(skill only)_ |
| `doc-warmup-c` | `c/test_base.cpp` | _(skill only)_ |
| `doc-sliced-rendering` | `python/test_base.py` | `examples/python_sliced_rendering.rst` |
| `doc-query-prims-basic` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-prims-by-type` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-prims-with-attributes` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-prims-async` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-prims-basic-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-query-prims-by-type-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-path-dictionary-resolve-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-read-attribute-scalar` | `python/test_attribute_read.py` | _(skill only)_ |
| `doc-read-attribute-dest-tensor` | `python/test_attribute_read.py` | _(skill only)_ |
| `doc-read-array-attribute` | `python/test_attribute_read.py` | _(skill only)_ |
| `doc-read-attribute-async` | `python/test_attribute_read.py` | _(skill only)_ |
| `doc-read-attribute-cuda-dest` | `python/test_attribute_read.py` | _(skill only)_ |
| `doc-read-attribute-scalar-c` | `c/test_attribute_read.cpp` | _(skill only)_ |
| `doc-read-array-attribute-c` | `c/test_attribute_read.cpp` | _(skill only)_ |
| `doc-update-from-usd-time-async` | `python/test_base.py` | `scene/loading_usd.rst` |
| `doc-update-from-usd-time-async-c` | `c/test_base.cpp` | `scene/loading_usd.rst` |
| `doc-operation-status` | `python/test_base.py` | _(skill only)_ |
| `doc-python-sync-runtime-error` | `python/test_error_handling.py` | _(skill only)_ |
| `doc-python-async-operation-error` | `python/test_error_handling.py` | _(skill only)_ |
| `doc-wait-op-error-retrieval-c` | `c/test_error_handling.cpp` | _(skill only)_ |
| `doc-wait-op-no-release-errors-c` | `c/test_error_handling.cpp` | _(skill only)_ |
| `doc-log-callback-prefix-filter-c` | `c/test_logging.cpp` | _(skill only)_ |
| `doc-step-async` | `python/test_camera_sensors.py` | _(skill only)_ |
| `doc-reset-simulation-clock` | `python/test_camera_sensors.py` | _(skill only)_ |
| `doc-shape-scalar-int32` | `python/test_attribute_shapes.py` | _(skill only)_ |
| `doc-shape-float3-array` | `python/test_attribute_shapes.py` | _(skill only)_ |
| `doc-shape-mat4-array` | `python/test_attribute_shapes.py` | _(skill only)_ |
| `doc-shape-scalar-int32-c` | `c/test_attribute_shapes.cpp` | _(skill only)_ |
| `doc-shape-float3-array-c` | `c/test_attribute_shapes.cpp` | _(skill only)_ |
| `doc-shape-mat4-array-c` | `c/test_attribute_shapes.cpp` | _(skill only)_ |
| `doc-add-remove-usd-reference` | `python/test_stage_mutation.py` | _(skill only)_ |
| `doc-add-remove-usd-reference-c` | `c/test_stage_mutation.cpp` | _(skill only)_ |
| `doc-add-usd-reference-from-string` | `python/test_stage_mutation.py` | _(skill only)_ |
| `doc-add-usd-reference-from-string-c` | `c/test_stage_mutation.cpp` | _(skill only)_ |
| `doc-clone-usd` | `python/test_stage_mutation.py` | _(skill only)_ |
| `doc-clone-usd-async` | `python/test_stage_mutation.py` | _(skill only)_ |
| `doc-clone-usd-c` | `c/test_stage_mutation.cpp` | _(skill only)_ |
| `doc-clone-usd-async-c` | `c/test_stage_mutation.cpp` | _(skill only)_ |
| `doc-bind-attribute-write` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-bind-attribute-async` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-binding-write-async` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-bind-array-attribute` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-map-attribute-cpu` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-map-attribute-cpu-c` | `c/test_attribute_bindings.cpp` | _(skill only)_ |
| `doc-map-bound-attribute` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-map-attribute-cuda` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-unmap-attribute-async` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-write-attribute-async-data-access` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-write-token-array` | `python/test_attribute_bindings.py` | _(skill only)_ |
| `doc-create-attribute-binding-c` | `c/test_attribute_bindings.cpp` | _(skill only)_ |
| `doc-write-bound-attribute-c` | `c/test_attribute_bindings.cpp` | _(skill only)_ |
| `doc-destroy-attribute-binding-c` | `c/test_attribute_bindings.cpp` | _(skill only)_ |
| `doc-set-token-attributes-c` | `c/test_attribute_helpers.cpp` | _(skill only)_ |
| `doc-dldata-type-from-str` | `python/test_support_api.py` | _(skill only)_ |
| `doc-managed-dltensor-helpers` | `python/test_support_api.py` | _(skill only)_ |
| `doc-renderer-config` | `python/test_support_api.py` | _(skill only)_ |
| `doc-open-usd-async` | `python/test_support_api.py` | _(skill only)_ |
| `doc-open-usd-from-string-async` | `python/test_support_api.py` | _(skill only)_ |
| `doc-reset-async` | `python/test_support_api.py` | _(skill only)_ |
| `doc-reset-stage-async` | `python/test_support_api.py` | _(skill only)_ |
| `doc-version-and-config-c` | `c/test_support_api.cpp` | _(skill only)_ |
| `doc-query-op-status-c` | `c/test_support_api.cpp` | _(skill only)_ |
| `doc-get-last-error-c` | `c/test_support_api.cpp` | `c_api/practical_patterns.rst` |
| `doc-query-require-any-exclude` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-specific-empty-attributes` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-inline-sublayer-composition` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-test-base-semantic-class-layer` | `data/ovrtx-test-base-semantic-labels.usda` | _(skill only)_ |
| `doc-semantic-class-overrides-python` | `python/test_semantic_labels.py` | _(skill only)_ |
| `doc-interpret-semantic-segmentation-python` | `python/test_semantic_labels.py` | _(skill only)_ |
| `doc-semantic-class-overrides-c` | `c/test_semantic_labels.cpp` | _(skill only)_ |
| `doc-interpret-semantic-segmentation-c` | `c/test_semantic_labels.cpp` | _(skill only)_ |
| `doc-semantic-label-overrides` | `usd/data/semantic_label_overrides.usda` | _(skill only)_ |
| `doc-query-has-attribute-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-query-require-any-exclude-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-query-specific-empty-attributes-c` | `c/test_stage_query.cpp` | _(skill only)_ |
| `doc-map-render-output-cuda` | `python/test_camera_sensors.py` | _(skill only)_ |
| `doc-map-render-output-cuda-array` | `python/test_camera_sensors.py` | _(skill only)_ |
| `doc-map-render-output-cuda-c` | `c/test_camera_sensors.cpp` | _(skill only)_ |
| `doc-map-render-output-cuda-array-c` | `c/test_camera_sensors.cpp` | _(skill only)_ |
| `doc-set-xform-mat-c` | `c/test_transform_helpers.cpp` | _(skill only)_ |
| `doc-set-xform-pos-rot-scale-c` | `c/test_transform_helpers.cpp` | _(skill only)_ |
| `doc-set-xform-pos-rot3x3-c` | `c/test_transform_helpers.cpp` | _(skill only)_ |
| `doc-set-reset-xform-stack-c` | `c/test_transform_helpers.cpp` | _(skill only)_ |
| `doc-usda-inline-sublayers-camera-renderproduct` | `usd/data/inline_sublayers_camera_renderproduct.usda` | `sensors/configuration.rst` |
| `doc-read-usd-bool` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-bool` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-int` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-int` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-float` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-float` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-point3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-point3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-point3f-array` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-point3f-array` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-normal3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-normal3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-vector3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-vector3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-color3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-color3f` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-matrix4d` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-matrix4d` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-quatf` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-quatf` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-string` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-string` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-token` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-write-usd-token-array` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-read-usd-float-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-float-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-point3f-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-point3f-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-point3f-array-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-point3f-array-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-matrix4d-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-matrix4d-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-quatf-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-quatf-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-token-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-token-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-token-array-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-token-array-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-string-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-string-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-read-usd-asset-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-write-usd-asset-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-extent-world-extent` | `python/test_all_attributes.py` | _(skill only)_ |
| `doc-extent-world-extent-c` | `c/test_all_attributes.cpp` | _(skill only)_ |
| `doc-create-selection-outline-renderer-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-enqueue-pick-query-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-read-pick-hit-buffer-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-resolve-picked-prim-paths-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-set-pickable-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-set-selection-outline-group-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-clear-selection-outline-group-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-create-styled-selection-renderer-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-set-selection-group-styles-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-assign-selection-style-groups-python` | `python/test_picking_selection.py` | `scene/picking.rst` |
| `doc-pin-render-product-to-gpu-0-usda` | `data/ovrtx-test-picking-selection.usda` | _(skill only)_ |
| `doc-create-selection-outline-renderer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-enqueue-pick-query-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-read-pick-hit-buffer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-resolve-picked-prim-paths-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-resolve-primpath-helper-c` | `c/helpers.h` | `scene/picking.rst` |
| `doc-set-pickable-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-set-selection-outline-group-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-clear-selection-outline-group-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-create-styled-selection-renderer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-set-selection-group-styles-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-assign-selection-style-groups-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` |
| `doc-minimal-dlss-render-product` | `examples/python/minimal-dlss/minimal_dlss.usda` | `sensors/cameras/render_modes/minimal.rst` |
| `doc-minimal-dlss-render-product-python` | `usd/test_minimal_dlss.py` | `sensors/cameras/render_modes/minimal.rst` |
| `doc-render-minimal-dlss-python` | `examples/python/minimal-dlss/main.py` | `examples/python_minimal_dlss.rst` and the example README |
| `doc-minimal-dlss-c-populate` | `examples/c/minimal-dlss/main.cpp` | `examples/c_minimal_dlss.rst` and the example README |
| `doc-minimal-dlss-c-step-renderer` | `examples/c/minimal-dlss/main.cpp` | `examples/c_minimal_dlss.rst` and the example README |
| `doc-lineup-project-box` | `examples/python/semantic-segmentation/main.py` | `examples/python_semantic_segmentation.rst` and the example README |
| `doc-create-minimal-only-renderer` | `python/test_renderer_configuration.py` | `core/renderer_configuration.rst` |
| `doc-create-minimal-only-renderer-c` | `c/test_renderer_configuration.cpp` | `core/renderer_configuration.rst` |
| `doc-reset-render-mode-availability` | `python/test_renderer_configuration.py` | `core/renderer_configuration.rst` |
| `doc-reset-render-mode-availability-c` | `c/test_renderer_configuration.cpp` | `core/renderer_configuration.rst` |
| `doc-sd-map-image-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-map-image-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-records-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-records-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-boxes-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-boxes-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-occlusion-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-occlusion-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-tokens-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-tokens-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-instance-map-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-instance-map-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-identifiers-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-identifiers-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-id-pairs-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-id-pairs-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-camera-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-camera-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-project-python` | `python/test_camera_aovs.py` | _(test only)_ |
| `doc-sd-project-c` | `c/test_camera_aovs.cpp` | _(test only)_ |

| `doc-pt-pixels-python` | `examples/python/semantic-segmentation/main.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-pt-pixels-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-pt-view-data-python` | `examples/python/semantic-segmentation/main.py` | _(test only)_ |
| `doc-pt-view-data-c` | `c/test_camera_aovs.cpp` | _(test only)_ |
| `doc-pt-lineup-render-product` | `examples/python/semantic-segmentation/main.py` | `examples/python_semantic_segmentation.rst` and the example README |


### Gaussian splats

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `gaussian-render-product` | `examples/python/gaussian-splats/gaussian_splats.usda` | _(example only)_ |
| `gaussian-render-python` | `examples/python/gaussian-splats/main.py` | `examples/python_gaussian_splats.rst` |
| `gaussian-c-project-setup` | `examples/c/gaussian-splats/CMakeLists.txt` | _(example only)_ |
| `gaussian-c-linking-models` | `examples/c/gaussian-splats/CMakeLists.txt` | _(example only)_ |
| `gaussian-c-check-error-helper` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-create-renderer` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-load-usd-and-wait` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-step-renderer` | `examples/c/gaussian-splats/main.cpp` | `examples/c_gaussian_splats.rst` |
| `gaussian-c-fetch-results` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-map-rendered-output-cpu` | `examples/c/gaussian-splats/main.cpp` | `examples/c_gaussian_splats.rst` |
| `gaussian-c-unmap-and-cleanup` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-find-output-helper` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `doc-gaussian-splat-prim-python` | `usd/test_usd_python_examples.py` | `geometry/gaussian_splats.rst`, `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst` |
| `doc-gaussian-splat-prim` | `usd/data/gaussian_splat.usda` | `geometry/gaussian_splats.rst`, `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst` |

### usd-plugin-paths example snippets

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `plugin-paths-external-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst`, `examples/python_usd_plugin_paths.rst` |
| `plugin-paths-verify-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst`, `examples/python_usd_plugin_paths.rst` |
| `plugin-paths-enumerate-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` |
| `plugin-paths-register-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` |
| `plugin-c-project-setup` | `examples/c/usd-plugin-paths/CMakeLists.txt` | _(example only)_ |
| `plugin-c-linking-models` | `examples/c/usd-plugin-paths/CMakeLists.txt` | _(example only)_ |
| `doc-plugin-physical-light` | `usd/data/plugin_physical_light.usda` | `core/usd_plugin_paths.rst` |
| `doc-plugin-physical-light-python` | `usd/test_usd_python_examples.py` | `core/usd_plugin_paths.rst` |
| `plugin-paths-register-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst` |
| `plugin-paths-first-root-wins-python` | `examples/python/usd-plugin-paths/test_example.py` | `core/usd_plugin_paths.rst` |
| `plugin-paths-validate-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` |
