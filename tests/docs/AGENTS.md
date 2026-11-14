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

The tree below is a partial map of the test files. The snippet inventory below
records data paths recursively, including `usd/data/nonvisual/`.

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
│   ├── test_camera_aovs.py                      # Smoke tests for all camera AOVs (SDG snippet + RTPT output catalog)
│   ├── test_camera_sensors.py                   # Camera output snippets (sensors/cameras pages)
│   ├── test_camera_feature_examples.py           # End-to-end public Camera example smoke tests
│   ├── test_gaussian_splats.py                  # Visible/hidden splats in each mode, first and 32nd frame
│   ├── test_frame_generation.py                 # DLSS-G output frame contract (hardware-gated)
│   ├── test_render_modes.py                     # Tests for camera render modes
│   ├── test_sensor_configuration.py             # RenderProduct and multi-product snippets (sensors/common pages)
│   └── test_usd_plugin_paths.py                 # External-USD registration integration test
├── usd/
│   ├── pyproject.toml                           # usd-core + pytest
│   ├── conftest.py                              # validate_usda() helper
│   ├── data/
│   │   ├── generic_wpm_acoustic.usda
│   │   ├── generic_wpm_base.usda
│   │   ├── generic_wpm_cylindrical.usda
│   │   ├── generic_wpm_depth.usda
│   │   ├── generic_wpm_gaussian.usda
│   │   ├── generic_wpm_gaussian_bloom.usda
│   │   ├── generic_wpm_lidar.usda
│   │   ├── generic_wpm_minimal.usda
│   │   ├── generic_wpm_mixed.usda
│   │   ├── generic_wpm_multistatic.usda
│   │   ├── generic_wpm_multistatic_map.usda
│   │   ├── generic_wpm_planar.usda
│   │   ├── camera_attributes.usda
│   │   ├── camera_core_request.usda
│   │   ├── camera_lens_calibration.usda
│   │   ├── camera_rolling_shutter.usda
│   │   ├── camera_scene_partitions.usda
│   │   ├── camera_core_versioning.usda          # Camera generic core model version request
│   │   ├── camera_sensor_render_product.usda    # USDA with snippet markers
│   │   ├── decal.usda
│   │   ├── decal_binding.usda
│   │   ├── depth_sensor_render_product.usda
│   │   ├── depth_sensor_versioning.usda         # Camera single-view stereo depth model version request
│   │   ├── dlss_nr.usda                         # DLSS-NR RenderProduct
│   │   ├── finite_dome_lights.usda
│   │   ├── gaussian_splat.usda                     # One ParticleField Gaussian splat
│   │   ├── ghost_lights.usda
│   │   ├── inline_sublayers_camera_renderproduct.usda
│   │   ├── lidar_wpm_output_request.usda
│   │   ├── lidar_wpm_firing_pattern_rotary.usda
│   │   ├── lidar_wpm_firing_pattern_solid_state.usda
│   │   ├── light_linking.usda
│   │   ├── light_path_expressions.usda
│   │   ├── light_shaping.usda
│   │   ├── light_types.usda
│   │   ├── mesh_lights.usda
│   │   ├── frame_generation_render_product.usda # DLSS Frame Generation RenderProduct
│   │   ├── minimal_render_product.usda
│   │   ├── multi_render_product_shared_vars.usda
│   │   ├── physical_lighting.usda
│   │   ├── plugin_physical_light.usda           # Existing ovrtx schema application
│   │   ├── projector_lights.usda
│   │   ├── radar_scan_configurations.usda
│   │   ├── sensor_configuration_minimal.usda
│   │   ├── sensor_configuration_orientation.usda
│   │   ├── sensor_configuration_override.usda
│   │   ├── semantic_label_base.usda
│   │   ├── semantic_label_overrides.usda
│   │   └── spectral_rendering.usda
│   ├── test_camera_calibration_example.py         # Runs calibration and checks authored camera data
│   ├── test_nonvisual_authoring.py                # USD Python twins for nonvisual sensor snippets
│   ├── test_camera_sensors_usda.py              # Validates USDA structure
│   ├── test_gaussian_splats_usda.py             # Validates the public Gaussian scene arrays
│   ├── test_frame_generation_usda.py            # Validates frame-generation USDA
│   ├── test_sensor_config_usda.py               # Validates USDA structure
│   └── test_usd_python_examples.py              # USD Python API equivalents, including physical lighting
└── c/
    ├── CMakeLists.txt                           # CMake project (GoogleTest + ovrtx C API)
    ├── helpers.h                                # Shared test helpers
    ├── test_all_attributes.cpp                  # Authored USD attribute read/write snippets and coverage (C)
    ├── test_camera_aovs.cpp                     # Smoke tests for all camera AOVs (C)
    ├── test_camera_sensors.cpp                  # C camera output snippets (sensors/cameras pages)
    ├── test_sensor_configuration.cpp            # C RenderProduct and multi-product snippets (sensors/common pages)
    ├── test_usd_plugin_paths.cpp                # Path count, truncation, and borrowed lifetime
    └── test_video_textures.cpp                  # C runtime snippet for python_video_textures.rst
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
- **USD Python tab** -- `literalinclude` from `usd/test_usd_python_examples.py` or `usd/test_nonvisual_authoring.py`

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
| USD Python API (`from pxr import ...`) | `usd/test_usd_python_examples.py`, `usd/test_nonvisual_authoring.py` | No GPU needed |
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
| `doc-profiling-render-loop-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-render-loop-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-profiling-replay-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-replay-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-profiling-file-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-json-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-json-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-profiling-file-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-profiling-read-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-read-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-profiling-stop-python` | `python/test_profiling.py` | `core/profiling.rst` |
| `doc-profiling-stop-c` | `c/test_profiling.cpp` | `core/profiling.rst` |
| `doc-generic-wpm-acoustic` | `usd/data/generic_wpm_acoustic.usda` | `sensors/nonvisual/generic_wpm/howto/mechanical_propagation.rst` |
| `doc-generic-wpm-acoustic-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/mechanical_propagation.rst` |
| `doc-generic-wpm-base` | `usd/data/generic_wpm_base.usda` | `sensors/nonvisual/generic_wpm/attributes.rst`, `sensors/nonvisual/generic_wpm/howto/setup.rst`, `sensors/nonvisual/generic_wpm/outputs.rst` |
| `doc-generic-wpm-imports-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/attributes.rst`, `sensors/nonvisual/generic_wpm/howto/setup.rst`, `sensors/nonvisual/generic_wpm/index.rst`, `sensors/nonvisual/generic_wpm/outputs.rst` |
| `doc-generic-wpm-base-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/attributes.rst`, `sensors/nonvisual/generic_wpm/howto/setup.rst`, `sensors/nonvisual/generic_wpm/outputs.rst` |
| `doc-generic-wpm-copy-contributions` | `examples/python/generic-wpm/main.py` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-cylindrical` | `usd/data/generic_wpm_cylindrical.usda` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-cylindrical-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-depth` | `usd/data/generic_wpm_depth.usda` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-depth-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-gaussian` | `usd/data/generic_wpm_gaussian.usda` | `sensors/nonvisual/generic_wpm/howto/beam_sampling.rst` |
| `doc-generic-wpm-gaussian-bloom` | `usd/data/generic_wpm_gaussian_bloom.usda` | `examples/python_generic_wpm.rst`, `sensors/nonvisual/generic_wpm/howto/beam_sampling.rst` and the example README |
| `doc-generic-wpm-gaussian-bloom-python` | `usd/test_generic_wpm_usda.py` | `examples/python_generic_wpm.rst`, `sensors/nonvisual/generic_wpm/howto/beam_sampling.rst` |
| `doc-generic-wpm-gaussian-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/beam_sampling.rst` |
| `doc-generic-wpm-lidar` | `usd/data/generic_wpm_lidar.usda` | `sensors/nonvisual/generic_wpm/howto/scan.rst` |
| `doc-generic-wpm-lidar-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/scan.rst` |
| `doc-generic-wpm-load-recipe` | `examples/python/generic-wpm/main.py` | _(example only)_ |
| `doc-generic-wpm-minimal` | `usd/data/generic_wpm_minimal.usda` | `sensors/nonvisual/generic_wpm/index.rst` |
| `doc-generic-wpm-minimal-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/index.rst` |
| `doc-generic-wpm-mixed` | `usd/data/generic_wpm_mixed.usda` | `sensors/nonvisual/generic_wpm/howto/runtime_updates.rst` |
| `doc-generic-wpm-mixed-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/runtime_updates.rst` |
| `doc-generic-wpm-multistatic` | `usd/data/generic_wpm_multistatic.usda` | `sensors/nonvisual/generic_wpm/howto/receiver_layouts.rst` |
| `doc-generic-wpm-multistatic-map` | `usd/data/generic_wpm_multistatic_map.usda` | `sensors/nonvisual/generic_wpm/howto/receiver_layouts.rst` |
| `doc-generic-wpm-multistatic-map-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/receiver_layouts.rst` |
| `doc-generic-wpm-multistatic-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/receiver_layouts.rst` |
| `doc-generic-wpm-planar` | `usd/data/generic_wpm_planar.usda` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-planar-python` | `usd/test_generic_wpm_usda.py` | `sensors/nonvisual/generic_wpm/howto/depth_sampling.rst` |
| `doc-generic-wpm-read-output` | `examples/python/generic-wpm/main.py` | `examples/c_generic_wpm.rst`, `examples/python_generic_wpm.rst`, `sensors/nonvisual/generic_wpm/outputs.rst` and the example README |
| `doc-generic-wpm-read-output-c` | `examples/c/generic-wpm/main.cpp` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-select-patterns` | `examples/python/generic-wpm/main.py` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-select-patterns-c` | `examples/c/generic-wpm/main.cpp` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-step` | `examples/python/generic-wpm/main.py` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-step-c` | `examples/c/generic-wpm/main.cpp` | `examples/python_generic_wpm.rst` |
| `doc-generic-wpm-valid-slots-c` | `examples/c/generic-wpm/main.cpp` | `examples/c_generic_wpm.rst`, `examples/python_generic_wpm.rst`, `sensors/nonvisual/generic_wpm/outputs.rst` and the example README |
| `doc-dlss-nr-render-product` | `usd/data/dlss_nr.usda` | `sensors/cameras/render_modes/dlss_nr.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-dlss-nr-render-product-python` | `usd/test_dlss_nr.py` | `sensors/cameras/render_modes/dlss_nr.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-aov-compositing-render` | `examples/python/aov-compositing/render-aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-aov-compositing-inputs` | `examples/python/aov-compositing/composite-aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-aov-compositing-sum` | `examples/python/aov-compositing/composite-aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-aov-compositing-display` | `examples/python/aov-compositing/composite-aovs.py` | `examples/python_aov_compositing.rst` ; _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-aov-compositing-compare` | `examples/python/aov-compositing/composite-aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-spectral-config-python` | `examples/python/spectral-rendering/main.py` | `examples/python_spectral_rendering.rst`, `sensors/cameras/render_modes/spectral_rendering.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-spectral-config-c` | `examples/c/spectral-rendering/main.cpp` | `examples/c_spectral_rendering.rst`, `sensors/cameras/render_modes/spectral_rendering.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-spectral-authoring` | `usd/data/spectral_rendering.usda` | `sensors/cameras/render_modes/spectral_rendering.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-spectral-authoring-python` | `usd/test_spectral_rendering.py` | `sensors/cameras/render_modes/spectral_rendering.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-spectral-illuminant` | `examples/python/spectral-rendering/spectral.usda` | _(example only)_ |
| `doc-spectral-render-product` | `examples/python/spectral-rendering/spectral.usda` | _(example only)_ |
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
| `doc-projector-opencv-calibration` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `examples/python_projector_light_calibration.rst`, `lights/rect_light.rst` |
| `doc-projector-octahedral-directions` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `examples/python_projector_light_calibration.rst`, `lights/rect_light.rst` |
| `doc-projector-opencv-project` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `examples/python_projector_light_calibration.rst`, `lights/rect_light.rst` |
| `doc-projector-write-direction-texture` | `examples/python/projector-light-calibration/generate_direction_texture.py` | `examples/python_projector_light_calibration.rst`, `lights/rect_light.rst` |
| `doc-projector-generate-and-render` | `examples/python/projector-light-calibration/main.py` | `examples/python_projector_light_calibration.rst` |
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
| `doc-camera-sensor-render-product` | `usd/data/camera_sensor_render_product.usda` | `sensors/cameras/decoding_outputs.rst` |
| `doc-camera-sensor-render-product-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-camera-attributes` | `usd/data/camera_attributes.usda` | `sensors/cameras/usd_camera_attributes.rst` |
| `doc-camera-attributes-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/usd_camera_attributes.rst` |
| `doc-camera-lens-calibration` | `usd/data/camera_lens_calibration.usda` | `sensors/cameras/lens_calibration.rst` |
| `doc-camera-lens-calibration-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/lens_calibration.rst` |
| `doc-camera-rolling-shutter` | `usd/data/camera_rolling_shutter.usda` | `sensors/cameras/rolling_shutter.rst` |
| `doc-camera-rolling-shutter-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/rolling_shutter.rst` |
| `doc-create-rolling-shutter-renderer` | `python/test_support_api.py` | `sensors/cameras/rolling_shutter.rst`, `sensors/common/output_configuration.rst` ; _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `doc-create-rolling-shutter-renderer-c` | `c/test_support_api.cpp` | `sensors/cameras/rolling_shutter.rst`, `sensors/common/output_configuration.rst` ; _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `doc-camera-core-request` | `usd/data/camera_core_request.usda` | `sensors/visual/camera_core/index.rst`, `sensors/visual/camera_core/outputs.rst` |
| `doc-camera-core-request-python` | `usd/test_usd_python_examples.py` | `sensors/visual/camera_core/index.rst`, `sensors/visual/camera_core/outputs.rst` |
| `doc-depth-sensor-render-product` | `usd/data/depth_sensor_render_product.usda` | `sensors/visual/depth_camera/howto/set_up_depth_product.rst`, `sensors/visual/depth_camera/index.rst` |
| `doc-depth-sensor-render-product-python` | `usd/test_usd_python_examples.py` | `sensors/visual/depth_camera/howto/set_up_depth_product.rst`, `sensors/visual/depth_camera/index.rst` |
| `doc-camera-scene-partitions` | `usd/data/camera_scene_partitions.usda` | _(test only)_ |
| `doc-camera-scene-partitions-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/scene_partitions.rst` |
| `doc-calibration-reference-usda` | `examples/python/camera-calibration/doc_snippets/reference_camera.usda` | `examples/python_camera_calibration.rst` |
| `doc-calibration-write-camera-usda` | `examples/python/camera-calibration/doc_snippets/camera_attributes.usda` | `examples/python_camera_calibration.rst` |
| `doc-calibration-reference-python` | `examples/python/camera-calibration/doc_snippets/reference_camera.py` | `examples/python_camera_calibration.rst` |
| `doc-calibration-detect-corners` | `examples/python/camera-calibration/main.py` | `examples/python_camera_calibration.rst` |
| `doc-calibration-solve` | `examples/python/camera-calibration/main.py` | `examples/python_camera_calibration.rst` |
| `doc-calibration-write-camera` | `examples/python/camera-calibration/main.py` | `examples/python_camera_calibration.rst` |
| `doc-render-calibrated-cameras` | `examples/python/camera-lens-calibration/main.py` | _(example only)_ |
| `doc-render-rolling-shutter` | `examples/python/camera-rolling-shutter/main.py` | _(example only)_ |
| `doc-example-camera-scene-partitions` | `examples/python/camera-scene-partitions/scene_partitions.usda` | `sensors/cameras/scene_partitions.rst` |
| `doc-render-camera-scene-partitions` | `examples/python/camera-scene-partitions/main.py` | `examples/python_camera_scene_partitions.rst` |
| `doc-author-gbuffer-debug-views` | `examples/python/debug-views/main.py` | _(example only)_ |
| `doc-render-gbuffer-debug-views` | `examples/python/debug-views/main.py` | `examples/python_debug_views.rst` |
| `doc-camera-core-versioning` | `usd/data/camera_core_versioning.usda` | `sensors/cameras/versioning.rst` |
| `doc-camera-core-versioning-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/versioning.rst` |
| `doc-depth-sensor-versioning` | `usd/data/depth_sensor_versioning.usda` | `sensors/cameras/versioning.rst` |
| `doc-depth-sensor-versioning-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/versioning.rst` |
| `doc-step-and-map-camera-outputs` | `python/test_camera_sensors.py` | `sensors/cameras/decoding_outputs.rst` ; _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-camera-aov-smoke-test` | `python/test_camera_aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-camera-aov-smoke-test-c` | `c/test_camera_aovs.cpp` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-lpe-render-vars` | `usd/data/light_path_expressions.usda` | `sensors/cameras/light_path_expressions.rst` |
| `doc-lpe-render-vars-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/light_path_expressions.rst` |
| `doc-example-lpe-render-vars` | `examples/python/lpes/lpe-layer.usda` | `examples/python_lpes.rst` |
| `doc-example-lpe-render-vars-python` | `usd/test_usd_python_examples.py` | `examples/python_lpes.rst` |
| `doc-read-lpe-outputs` | `examples/python/lpes/main.py` | `examples/python_lpes.rst` ; _(skill: `skills/reading-render-output/SKILL.md`)_ |
| `doc-lpe-initialize-rerun` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-create-renderer` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-load-scene` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-lpe-step` | `examples/python/lpes/main.py` | _(example only)_ |
| `doc-minimal-render-product` | `usd/data/minimal_render_product.usda` | `sensors/common/output_configuration.rst` |
| `doc-minimal-render-product-python` | `usd/test_usd_python_examples.py` | `sensors/common/output_configuration.rst` |
| `doc-multi-render-product-shared-vars` | `usd/data/multi_render_product_shared_vars.usda` | `sensors/common/output_configuration.rst` |
| `doc-multi-render-product-shared-vars-python` | `usd/test_usd_python_examples.py` | `sensors/common/output_configuration.rst` |
| `doc-step-multiple-render-products` | `python/test_sensor_configuration.py` | `sensors/common/output_configuration.rst` |
| `doc-add-render-config-layer` | `python/test_sensor_configuration.py` | `scene/loading_usd.rst`, `sensors/common/output_configuration.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-step-and-map-camera-outputs-c` | `c/test_camera_sensors.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-step-multiple-render-products-c` | `c/test_sensor_configuration.cpp` | `sensors/common/output_configuration.rst` |
| `doc-multi-rate-lidar-usda`, `doc-multi-rate-camera-usda` | `examples/python/multi-rate-sensors/multi_rate.usda` | `sensors/common/multi_rate.rst`, `sensors/common/sensor_configuration.rst` |
| `doc-multi-rate-lidar-python`, `doc-multi-rate-camera-python` | `usd/test_usd_python_examples.py` | `sensors/common/multi_rate.rst` |
| `doc-multi-rate-step`, `doc-multi-rate-partial-outputs` | `examples/python/multi-rate-sensors/main.py` | `sensors/common/multi_rate.rst`, `examples/python_multi_rate_sensors.rst`, and the example README |
| `doc-multi-rate-read-outputs` | `examples/python/multi-rate-sensors/main.py` | `examples/python_multi_rate_sensors.rst` |
| `doc-multi-rate-step-c`, `doc-multi-rate-partial-outputs-c` | `c/test_sensor_configuration.cpp` | `sensors/common/multi_rate.rst` |
| `doc-lidar-motion-compensation-python` | `usd/test_usd_python_examples.py` | _(test only)_ |
| `doc-lidar-wpm-output-request` | `usd/data/lidar_wpm_output_request.usda` | `sensors/nonvisual/lidar_wpm/outputs.rst` |
| `doc-lidar-wpm-output-request-python` | `usd/test_usd_python_examples.py` | `sensors/nonvisual/lidar_wpm/outputs.rst` |
| `doc-lidar-wpm-firing-pattern-rotary`, `doc-lidar-wpm-firing-pattern-solid-state` | `usd/data/lidar_wpm_firing_pattern_rotary.usda`, `usd/data/lidar_wpm_firing_pattern_solid_state.usda` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst` |
| `doc-lidar-wpm-firing-pattern-rotary-python`, `doc-lidar-wpm-firing-pattern-solid-state-python` | `usd/test_usd_python_examples.py` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst` |
| `doc-radar-second-scan-python` | `usd/test_usd_python_examples.py` | `sensors/common/sensor_configuration.rst` |
| `doc-observer-cameras-usda` | `examples/c/sensor-observer/conveyor.usda` | `examples/c_sensor_observer.rst` |
| `doc-observer-cameras-python` | `usd/test_sensor_observer_usda.py` | _(test only)_ |
| `doc-observer-output-policy-c`, `doc-observer-step-c`, `doc-observer-copy-outputs-c` | `examples/c/sensor-observer/main.cpp` | `examples/c_sensor_observer.rst` and the example README |
| `doc-add-render-config-layer-c` | `c/test_sensor_configuration.cpp` | `scene/loading_usd.rst`, `sensors/common/output_configuration.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `doc-path-tracing-render-product` | `python/test_render_modes.py` | `sensors/cameras/render_modes.rst` |
| `doc-path-tracing-render-product-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/render_modes.rst` |
| `doc-bind-material` | `python/test_base.py` | `materials/material_binding.rst` ; _(skill: `skills/binding-materials/SKILL.md`)_, _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-bind-material-c` | `c/test_base.cpp` | `materials/material_binding.rst` ; _(skill: `skills/binding-materials/SKILL.md`)_ |
| `doc-frame-generation-render-product` | `usd/data/frame_generation_render_product.usda` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst`, `examples/c_frame_generation.rst` |
| `doc-frame-generation-detect` | `python/test_frame_generation.py` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst` |
| `doc-frame-generation-read-times` | `python/test_frame_generation.py` | _(test only)_ |
| `doc-frame-generation-read-frames` | `python/test_frame_generation.py` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst` |
| `doc-frame-generation-render-product-python` | `usd/test_usd_python_examples.py` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst` |
| `enable-frame-generation` | `examples/c/frame-generation/main.cpp` | _(skill: `skills/dlss-frame-generation/SKILL.md`)_ |
| `find-render-product-output` | `examples/c/frame-generation/main.cpp` | _(skill: `skills/dlss-frame-generation/SKILL.md`)_ |
| `step-and-inspect-frames` | `examples/c/frame-generation/main.cpp` | _(skill: `skills/dlss-frame-generation/SKILL.md`)_ |
| `classify-output-frames` | `examples/c/frame-generation/main.cpp` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst`, `examples/c_frame_generation.rst` ; _(skill: `skills/dlss-frame-generation/SKILL.md`)_ |
| `doc-frame-pacing-promote` | `examples/c/vulkan-interop/src/main.cpp` | `sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst` ; _(skill: `skills/dlss-frame-generation/SKILL.md`)_ |
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
| `doc-video-texture-material` | `examples/python/video-textures/video_textures.usda` | `examples/python_video_textures.rst`, `materials/video_textures.rst` |
| `doc-video-texture-material-python` | `usd/test_usd_python_examples.py` | `examples/python_video_textures.rst`, `materials/video_textures.rst` |
| `doc-video-texture-binding` | `examples/python/video-textures/video_textures.usda` | `examples/python_video_textures.rst` |
| `doc-video-texture-binding-python` | `usd/test_usd_python_examples.py` | `examples/python_video_textures.rst` |
| `doc-video-texture-blocking` | `examples/python/video-textures/video_textures.usda` | `materials/video_textures.rst` |
| `doc-video-texture-blocking-python` | `usd/test_usd_python_examples.py` | `materials/video_textures.rst` |
| `doc-render-video-texture-source-times` | `examples/python/video-textures/main.py` | `examples/python_video_textures.rst` |
| `doc-render-video-texture-source-times-c` | `c/test_video_textures.cpp` | `examples/python_video_textures.rst` |
| `doc-set-render-setting` | `python/test_base.py` | `sensors/common/output_configuration.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-set-render-setting-c` | `c/test_base.cpp` | `sensors/common/output_configuration.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-set-view-lighting` | `python/test_base.py` | _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-warmup` | `python/test_base.py` | `sensors/common/output_configuration.rst` ; _(skill: `skills/warmup/SKILL.md`)_ |
| `doc-warmup-c` | `c/test_base.cpp` | `sensors/common/output_configuration.rst` ; _(skill: `skills/warmup/SKILL.md`)_ |
| `doc-sliced-rendering` | `python/test_base.py` | `examples/python_sliced_rendering.rst` ; _(skill: `skills/sliced-rendering/SKILL.md`)_ |
| `doc-query-prims-basic` | `python/test_stage_query.py` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-prims-by-type` | `python/test_stage_query.py` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-prims-with-attributes` | `python/test_stage_query.py` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-prims-async` | `python/test_stage_query.py` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-prims-basic-c` | `c/test_stage_query.cpp` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-prims-by-type-c` | `c/test_stage_query.cpp` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-path-dictionary-resolve-c` | `c/test_stage_query.cpp` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-read-attribute-scalar` | `python/test_attribute_read.py` | `scene/attributes.rst` ; _(skill: `skills/README.md`)_, _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-attribute-dest-tensor` | `python/test_attribute_read.py` | `scene/attributes.rst` ; _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-array-attribute` | `python/test_attribute_read.py` | `scene/attributes.rst` ; _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-attribute-async` | `python/test_attribute_read.py` | _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-attribute-cuda-dest` | `python/test_attribute_read.py` | `scene/attributes.rst` ; _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-attribute-scalar-c` | `c/test_attribute_read.cpp` | `scene/attributes.rst` ; _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-read-array-attribute-c` | `c/test_attribute_read.cpp` | `scene/attributes.rst` ; _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-update-from-usd-time-async` | `python/test_base.py` | `scene/loading_usd.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `doc-update-from-usd-time-async-c` | `c/test_base.cpp` | `scene/loading_usd.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `doc-operation-status` | `python/test_base.py` | _(skill: `skills/async-operations/SKILL.md`)_ |
| `doc-python-sync-runtime-error` | `python/test_error_handling.py` | _(skill: `skills/error-handling/SKILL.md`)_ |
| `doc-python-async-operation-error` | `python/test_error_handling.py` | _(skill: `skills/error-handling/SKILL.md`)_ |
| `doc-wait-op-error-retrieval-c` | `c/test_error_handling.cpp` | `c_api/practical_patterns.rst` ; _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-wait-op-no-release-errors-c` | `c/test_error_handling.cpp` | `c_api/practical_patterns.rst` ; _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-log-callback-prefix-filter-c` | `c/test_logging.cpp` | `c_api/practical_patterns.rst`, `core/async_status_errors.rst` ; _(skill: `skills/error-handling/SKILL.md`)_, _(skill: `skills/update-0-5-to-0-6/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-step-async` | `python/test_camera_sensors.py` | `core/async_status_errors.rst` ; _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-reset-simulation-clock` | `python/test_camera_sensors.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `doc-shape-scalar-int32` | `python/test_attribute_shapes.py` | _(skill only)_ |
| `doc-shape-float3-array` | `python/test_attribute_shapes.py` | `scene/attributes.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-shape-mat4-array` | `python/test_attribute_shapes.py` | `scene/transforms.rst` ; _(skill: `skills/writing-transforms/SKILL.md`)_ |
| `doc-shape-scalar-int32-c` | `c/test_attribute_shapes.cpp` | _(skill only)_ |
| `doc-shape-float3-array-c` | `c/test_attribute_shapes.cpp` | _(skill only)_ |
| `doc-shape-mat4-array-c` | `c/test_attribute_shapes.cpp` | _(skill: `skills/writing-transforms/SKILL.md`)_ |
| `doc-add-remove-usd-reference` | `python/test_stage_mutation.py` | `scene/loading_usd.rst` |
| `doc-add-remove-usd-reference-c` | `c/test_stage_mutation.cpp` | `scene/loading_usd.rst` |
| `doc-add-usd-reference-from-string` | `python/test_stage_mutation.py` | _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-add-usd-reference-from-string-c` | `c/test_stage_mutation.cpp` | _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-clone-usd` | `python/test_stage_mutation.py` | `scene/cloning.rst` ; _(skill: `skills/cloning-prims/SKILL.md`)_ |
| `doc-clone-usd-async` | `python/test_stage_mutation.py` | `scene/cloning.rst` ; _(skill: `skills/cloning-prims/SKILL.md`)_ |
| `doc-clone-usd-c` | `c/test_stage_mutation.cpp` | `scene/cloning.rst` ; _(skill: `skills/cloning-prims/SKILL.md`)_ |
| `doc-clone-usd-async-c` | `c/test_stage_mutation.cpp` | _(skill: `skills/cloning-prims/SKILL.md`)_ |
| `doc-bind-attribute-write` | `python/test_attribute_bindings.py` | `scene/attribute_bindings.rst` ; _(skill: `skills/attribute-bindings/SKILL.md`)_, _(skill: `skills/writing-attributes/SKILL.md`)_, _(skill: `skills/writing-transforms/SKILL.md`)_ |
| `doc-bind-attribute-async` | `python/test_attribute_bindings.py` | `scene/attribute_bindings.rst` |
| `doc-binding-write-async` | `python/test_attribute_bindings.py` | `scene/attribute_bindings.rst` ; _(skill: `skills/attribute-bindings/SKILL.md`)_ |
| `doc-bind-array-attribute` | `python/test_attribute_bindings.py` | `scene/attribute_bindings.rst` ; _(skill: `skills/attribute-bindings/SKILL.md`)_ |
| `doc-map-attribute-cpu` | `python/test_attribute_bindings.py` | `scene/attribute_mapping.rst` ; _(skill: `skills/mapping-attributes/SKILL.md`)_ |
| `doc-map-attribute-cpu-c` | `c/test_attribute_bindings.cpp` | `scene/attribute_mapping.rst` ; _(skill: `skills/mapping-attributes/SKILL.md`)_ |
| `doc-map-bound-attribute` | `python/test_attribute_bindings.py` | `scene/attribute_bindings.rst` ; _(skill: `skills/attribute-bindings/SKILL.md`)_, _(skill: `skills/mapping-attributes/SKILL.md`)_ |
| `doc-map-attribute-cuda` | `python/test_attribute_bindings.py` | `scene/attribute_mapping.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_, _(skill: `skills/mapping-attributes/SKILL.md`)_ |
| `doc-unmap-attribute-async` | `python/test_attribute_bindings.py` | `scene/attribute_mapping.rst` |
| `doc-write-attribute-async-data-access` | `python/test_attribute_bindings.py` | _(skill: `skills/attribute-bindings/SKILL.md`)_ |
| `doc-write-token-array` | `python/test_attribute_bindings.py` | `scene/attributes.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-create-attribute-binding-c` | `c/test_attribute_bindings.cpp` | `scene/attribute_bindings.rst` |
| `doc-write-bound-attribute-c` | `c/test_attribute_bindings.cpp` | `scene/attribute_bindings.rst`, `scene/attributes.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-destroy-attribute-binding-c` | `c/test_attribute_bindings.cpp` | `scene/attribute_bindings.rst` |
| `doc-set-token-attributes-c` | `c/test_attribute_helpers.cpp` | `scene/attributes.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-dldata-type-from-str` | `python/test_support_api.py` | _(test only)_ |
| `doc-managed-dltensor-helpers` | `python/test_support_api.py` | _(test only)_ |
| `doc-renderer-config` | `python/test_support_api.py` | `core/renderer_configuration.rst` ; _(skill: `skills/renderer-creation/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-open-usd-async` | `python/test_support_api.py` | `core/async_status_errors.rst` ; _(skill: `skills/async-operations/SKILL.md`)_ |
| `doc-open-usd-from-string-async` | `python/test_support_api.py` | _(test only)_ |
| `doc-reset-async` | `python/test_support_api.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `doc-reset-stage-async` | `python/test_support_api.py` | _(test only)_ |
| `doc-version-and-config-c` | `c/test_support_api.cpp` | `c_api/practical_patterns.rst`, `core/renderer_configuration.rst` ; _(skill: `skills/project-setup-c/SKILL.md`)_, _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `doc-query-op-status-c` | `c/test_support_api.cpp` | `c_api/practical_patterns.rst` |
| `doc-get-last-error-c` | `c/test_support_api.cpp` | `c_api/practical_patterns.rst` |
| `doc-query-require-any-exclude` | `python/test_stage_query.py` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-specific-empty-attributes` | `python/test_stage_query.py` | _(skill only)_ |
| `doc-query-inline-sublayer-composition` | `python/test_stage_query.py` | _(skill: `skills/loading-usd/SKILL.md`)_ |
| `doc-test-base-semantic-class-layer` | `data/ovrtx-test-base-semantic-labels.usda` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-semantic-class-overrides-python` | `python/test_semantic_labels.py` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-interpret-semantic-segmentation-python` | `python/test_semantic_labels.py` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-semantic-class-overrides-c` | `c/test_semantic_labels.cpp` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-interpret-semantic-segmentation-c` | `c/test_semantic_labels.cpp` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-semantic-label-overrides` | `usd/data/semantic_label_overrides.usda` | `scene/semantic_labels.rst` ; _(skill: `skills/semantic-labels/SKILL.md`)_ |
| `doc-query-has-attribute-c` | `c/test_stage_query.cpp` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-require-any-exclude-c` | `c/test_stage_query.cpp` | `scene/stage_queries.rst` ; _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-query-specific-empty-attributes-c` | `c/test_stage_query.cpp` | _(skill: `skills/stage-queries/SKILL.md`)_ |
| `doc-map-render-output-cuda` | `python/test_camera_sensors.py` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_, _(skill: `skills/reading-render-output/SKILL.md`)_ |
| `doc-map-render-output-cuda-array` | `python/test_camera_sensors.py` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_ |
| `doc-map-render-output-cuda-c` | `c/test_camera_sensors.cpp` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_, _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-map-render-output-cuda-array-c` | `c/test_camera_sensors.cpp` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_, _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `doc-set-xform-mat-c` | `c/test_transform_helpers.cpp` | `scene/transforms.rst` |
| `doc-set-xform-pos-rot-scale-c` | `c/test_transform_helpers.cpp` | `scene/transforms.rst` |
| `doc-set-xform-pos-rot3x3-c` | `c/test_transform_helpers.cpp` | `scene/transforms.rst` |
| `doc-set-reset-xform-stack-c` | `c/test_transform_helpers.cpp` | `scene/transforms.rst` |
| `doc-usda-inline-sublayers-camera-renderproduct` | `usd/data/inline_sublayers_camera_renderproduct.usda` | `scene/loading_usd.rst`, `sensors/common/output_configuration.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
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
| `doc-extent-world-extent` | `python/test_all_attributes.py` | _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-extent-world-extent-c` | `c/test_all_attributes.cpp` | _(skill: `skills/reading-attributes/SKILL.md`)_ |
| `doc-create-selection-outline-renderer-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-enqueue-pick-query-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-read-pick-hit-buffer-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-resolve-picked-prim-paths-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-pickable-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-selection-outline-group-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-clear-selection-outline-group-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-create-styled-selection-renderer-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-selection-group-styles-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-assign-selection-style-groups-python` | `python/test_picking_selection.py` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-pin-render-product-to-gpu-0-usda` | `data/ovrtx-test-picking-selection.usda` | `sensors/common/output_configuration.rst` ; _(skill: `skills/render-product-device-pinning/SKILL.md`)_ |
| `doc-create-selection-outline-renderer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-enqueue-pick-query-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-read-pick-hit-buffer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-resolve-picked-prim-paths-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-resolve-primpath-helper-c` | `c/helpers.h` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-pickable-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-selection-outline-group-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-clear-selection-outline-group-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-create-styled-selection-renderer-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-set-selection-group-styles-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-assign-selection-style-groups-c` | `c/test_picking_selection.cpp` | `scene/picking.rst` ; _(skill: `skills/picking-selection/SKILL.md`)_ |
| `doc-minimal-dlss-render-product` | `examples/python/minimal-dlss/minimal_dlss.usda` | `sensors/cameras/render_modes/minimal.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-minimal-dlss-render-product-python` | `usd/test_minimal_dlss.py` | `sensors/cameras/render_modes/minimal.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-render-minimal-dlss-python` | `examples/python/minimal-dlss/main.py` | `examples/python_minimal_dlss.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-minimal-dlss-c-populate` | `examples/c/minimal-dlss/main.cpp` | `examples/c_minimal_dlss.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-minimal-dlss-c-step-renderer` | `examples/c/minimal-dlss/main.cpp` | `examples/c_minimal_dlss.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-lineup-project-box` | `examples/python/semantic-segmentation/main.py` | `examples/python_semantic_segmentation.rst` |
| `doc-create-minimal-only-renderer` | `python/test_renderer_configuration.py` | `core/renderer_configuration.rst` |
| `doc-create-minimal-only-renderer-c` | `c/test_renderer_configuration.cpp` | `core/renderer_configuration.rst` |
| `doc-reset-render-mode-availability` | `python/test_renderer_configuration.py` | `core/renderer_configuration.rst` |
| `doc-reset-render-mode-availability-c` | `c/test_renderer_configuration.cpp` | `core/renderer_configuration.rst` |
| `doc-sd-map-image-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-map-structured-python` | `python/test_camera_aovs.py` | _(skill only)_ |
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
| `doc-sd-project-python` | `python/test_camera_aovs.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-sd-project-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-pt-pixels-python` | `examples/python/semantic-segmentation/main.py` | `sensors/cameras/decoding_outputs.rst` |
| `doc-pt-pixels-c` | `c/test_camera_aovs.cpp` | `sensors/cameras/decoding_outputs.rst` |
| `doc-pt-lineup-render-product` | `examples/python/semantic-segmentation/main.py` | `examples/python_semantic_segmentation.rst` |


### Gaussian splats

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `gaussian-render-product` | `examples/python/gaussian-splats/gaussian_splats.usda` | _(example only)_ |
| `gaussian-render-python` | `examples/python/gaussian-splats/main.py` | _(skill: `skills/loading-usd/SKILL.md`)_, _(skill: `skills/render-settings/SKILL.md`)_, _(skill: `skills/warmup/SKILL.md`)_ |
| `gaussian-c-project-setup` | `examples/c/gaussian-splats/CMakeLists.txt` | _(example only)_ |
| `gaussian-c-linking-models` | `examples/c/gaussian-splats/CMakeLists.txt` | _(example only)_ |
| `gaussian-c-check-error-helper` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-create-renderer` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-load-usd-and-wait` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-step-renderer` | `examples/c/gaussian-splats/main.cpp` | _(skill: `skills/warmup/SKILL.md`)_ |
| `gaussian-c-fetch-results` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-map-rendered-output-cpu` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-unmap-and-cleanup` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `gaussian-c-find-output-helper` | `examples/c/gaussian-splats/main.cpp` | _(example only)_ |
| `doc-gaussian-splat-prim-python` | `usd/test_usd_python_examples.py` | `geometry/gaussian_splats.rst` |
| `doc-gaussian-splat-prim` | `usd/data/gaussian_splat.usda` | `geometry/gaussian_splats.rst` |

### usd-plugin-paths example snippets

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `plugin-paths-external-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst`, `examples/python_usd_plugin_paths.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `plugin-paths-verify-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst`, `examples/python_usd_plugin_paths.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `plugin-paths-enumerate-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` |
| `plugin-paths-register-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` |
| `plugin-c-project-setup` | `examples/c/usd-plugin-paths/CMakeLists.txt` | _(example only)_ |
| `plugin-c-linking-models` | `examples/c/usd-plugin-paths/CMakeLists.txt` | _(example only)_ |
| `doc-plugin-physical-light` | `usd/data/plugin_physical_light.usda` | `core/usd_plugin_paths.rst` |
| `doc-plugin-physical-light-python` | `usd/test_usd_python_examples.py` | `core/usd_plugin_paths.rst` |
| `plugin-paths-register-python` | `examples/python/usd-plugin-paths/main.py` | `core/usd_plugin_paths.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `plugin-paths-first-root-wins-python` | `examples/python/usd-plugin-paths/test_example.py` | `core/usd_plugin_paths.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `plugin-paths-validate-c` | `examples/c/usd-plugin-paths/main.cpp` | `core/usd_plugin_paths.rst`, `examples/c_usd_plugin_paths.rst` ; _(skill: `skills/loading-usd/SKILL.md`)_ |
| `doc-selection-state-preview` | `examples/python/semantic-segmentation/main.py` | `examples/python_semantic_segmentation.rst` |

### Snippets added to the inventory on 2026-10-12

Rows generated from the markers in the sources; the "Used in RST" column lists every page that literalincludes the marker.

#### `examples/python/acoustic`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `acoustic-sample-index-to-range` | `examples/python/acoustic/main.py` | `sensors/nonvisual/acoustic_wpm/outputs.rst` |
| `configure-acoustic-output` | `examples/python/acoustic/acoustic_example.usda` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst`, `sensors/nonvisual/acoustic_wpm/outputs.rst` |
| `configure-acoustic-sensor` | `examples/python/acoustic/acoustic_example.usda` | `sensors/nonvisual/acoustic_wpm/attributes.rst`, `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst`, `sensors/nonvisual/acoustic_wpm/index.rst` |
| `initialize-rerun` | `examples/python/acoustic/main.py` | _(example only)_ |
| `load-acoustic-scene` | `examples/python/acoustic/main.py` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst` |
| `log-acoustic-signal-ways` | `examples/python/acoustic/main.py` | _(example only)_ |
| `parse-acoustic-cli-args` | `examples/python/acoustic/main.py` | _(example only)_ |
| `read-acoustic-signal-ways` | `examples/python/acoustic/main.py` | `sensors/nonvisual/acoustic_wpm/outputs.rst` |
| `step-and-visualize-acoustic` | `examples/python/acoustic/main.py` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst` |
| `warm-up-acoustic` | `examples/python/acoustic/main.py` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst` |

#### `examples/python/minimal`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `add-usd` | `examples/python/minimal/main.py` | `scene/loading_usd.rst` ; _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/loading-usd/SKILL.md`)_, _(skill: `skills/project-setup-python/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `read-render-output` | `examples/python/minimal/main.py` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/project-setup-python/SKILL.md`)_, _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_, _(skill: `skills/update-0-4-to-0-5/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `step` | `examples/python/minimal/main.py` | _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/error-handling/SKILL.md`)_, _(skill: `skills/project-setup-python/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |

#### `examples/python/spg-blur`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `blur-horizontal-kernel` | `examples/python/spg-blur/BlurKernel.cu` | _(example only)_ |
| `blur-module` | `examples/python/spg-blur/BlurTaps.slang` | `examples/python_spg_blur.rst`, `spg/do/precompiled.rst` |
| `blur-runtime-radius` | `examples/python/spg-blur/main.py` | `spg/do/runtime_changes.rst` |
| `blur-tap` | `examples/python/spg-blur/BlurKernel.cu` | _(example only)_ |
| `blur-vertical-kernel` | `examples/python/spg-blur/BlurKernel.cu` | _(example only)_ |
| `blur-vertical-slang-kernel` | `examples/python/spg-blur/BlurKernel.slang` | _(example only)_ |
| `blur-write-radius` | `examples/python/spg-blur/main.py` | `examples/python_spg_blur.rst`, `spg/do/runtime_changes.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `render-graph` | `examples/python/spg-blur/blur_scene.usda` | `examples/python_spg_previous_frame.rst`, `spg/do/aovs.rst`, `spg/do/builtin.rst`, `spg/do/chaining.rst`, `spg/do/previous_frame.rst`, `spg/do/split_join.rst`, `spg/do/values.rst`, `spg/first_node.rst` ; _(skill: `skills/spg/SKILL.md`)_ |

#### `examples/c/lidar`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `check-error-helper` | `examples/c/lidar/main.cpp` | `c_api/practical_patterns.rst`, `core/async_status_errors.rst` ; _(skill: `skills/error-handling/SKILL.md`)_, _(skill: `skills/project-setup-c/SKILL.md`)_, _(skill: `skills/string-handling/SKILL.md`)_ |
| `configure-lidar-pointcloud-output` | `examples/c/lidar/lidar_example.usda` | `sensors/common/output_configuration.rst`, `sensors/first_sensor.rst`, `sensors/nonvisual/lidar_core/outputs.rst` ; _(skill: `skills/configuring-lidar-sensors/SKILL.md`)_ |
| `configure-lidar-sensor` | `examples/c/lidar/lidar_example.usda` | `sensors/first_sensor.rst`, `sensors/nonvisual/lidar_core/attributes.rst`, `sensors/nonvisual/lidar_core/index.rst` ; _(skill: `skills/configuring-lidar-sensors/SKILL.md`)_ |
| `configure-render-product` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `cpu-tensor-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `create-renderer` | `examples/c/lidar/main.cpp` | `core/renderer_configuration.rst`, `sensors/first_sensor.rst`, `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst`, `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` ; _(skill: `skills/README.md`)_, _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/error-handling/SKILL.md`)_, _(skill: `skills/project-setup-c/SKILL.md`)_, _(skill: `skills/project-setup-python/SKILL.md`)_, _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `destroy-results-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `find-render-var-output-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `find-tensor-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `load-lidar-scene` | `examples/c/lidar/main.cpp` | `sensors/first_sensor.rst` |
| `ovx-string-view-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `read-lidar-pointcloud` | `examples/c/lidar/main.cpp` | `sensors/common/sensor_outputs.rst`, `sensors/first_sensor.rst`, `sensors/nonvisual/lidar_core/outputs.rst` ; _(skill: `skills/interpreting-lidar-pointclouds/SKILL.md`)_, _(skill: `skills/reading-sensor-pointclouds/SKILL.md`)_ |
| `resolve-default-scene-path` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `resolve-executable-dir` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `step-lidar-pointcloud` | `examples/c/lidar/main.cpp` | `sensors/first_sensor.rst` ; _(skill: `skills/reading-sensor-pointclouds/SKILL.md`)_ |
| `string-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `wait-op-helper` | `examples/c/lidar/main.cpp` | _(example only)_ |
| `warm-up-lidar` | `examples/c/lidar/main.cpp` | `sensors/first_sensor.rst` |

#### `examples/python/spg-generate`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `checker-kernel` | `examples/python/spg-generate/CheckerKernel.cu` | _(example only)_ |
| `checker-render-graph` | `examples/python/spg-generate/checker_scene.usda` | _(example only)_ |
| `checker-shader-definition` | `examples/python/spg-generate/CheckerKernel.usda` | `spg/do/generate.rst` |
| `checker-slang-kernel` | `examples/python/spg-generate/CheckerKernel.slang` | _(example only)_ |
| `checker-slang-render-graph` | `examples/python/spg-generate/checker_scene_slang.usda` | _(example only)_ |
| `checker-slang-shader-definition` | `examples/python/spg-generate/CheckerKernel.slang.usda` | _(example only)_ |
| `generate-run` | `examples/python/spg-generate/main.py` | _(example only)_ |

#### `examples/python/status-queries`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `compile-shader-cache-with-status` | `examples/python/status-queries/main.py` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `format-operation-status` | `examples/python/status-queries/main.py` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `load-usd-with-status` | `examples/python/status-queries/main.py` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `step-with-status` | `examples/python/status-queries/main.py` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `wait-operation-with-status` | `examples/python/status-queries/main.py` | `core/async_status_errors.rst` ; _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/status-queries/SKILL.md`)_ |

#### `examples/c/status-queries`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `compile-shader-cache-with-status-c` | `examples/c/status-queries/main.cpp` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `format-operation-status-c` | `examples/c/status-queries/main.cpp` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `load-usd-with-status-c` | `examples/c/status-queries/main.cpp` | _(example only)_ |
| `step-with-status-c` | `examples/c/status-queries/main.cpp` | _(skill: `skills/status-queries/SKILL.md`)_ |
| `wait-operation-with-status-c` | `examples/c/status-queries/main.cpp` | `core/async_status_errors.rst` ; _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/status-queries/SKILL.md`)_ |

#### `examples/python/semantic-segmentation`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `compose-sublayer-render-product` | `examples/python/semantic-segmentation/main.py` | _(example only)_ |
| `doc-pt-multimatte-channels` | `examples/python/semantic-segmentation/main.py` | _(example only)_ |
| `log-aovs-to-rerun` | `examples/python/semantic-segmentation/main.py` | _(example only)_ |
| `open-sublayered-usd` | `examples/python/semantic-segmentation/main.py` | _(example only)_ |
| `step-all-aovs` | `examples/python/semantic-segmentation/main.py` | _(example only)_ |

#### `examples/python/spg-composite-aov`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `composite-create-renderer` | `examples/python/spg-composite-aov/main.py` | _(example only)_ |
| `composite-read-channels` | `examples/python/spg-composite-aov/main.py` | _(example only)_ |
| `composite-step-both-products` | `examples/python/spg-composite-aov/main.py` | _(example only)_ |
| `histogram-kernel` | `examples/python/spg-composite-aov/RangeHistogramKernel.cu` | _(example only)_ |
| `histogram-shader-definition` | `examples/python/spg-composite-aov/RangeHistogramKernel.usda` | _(example only)_ |
| `histogram-slang-kernel` | `examples/python/spg-composite-aov/RangeHistogramKernel.slang` | _(example only)_ |
| `histogram-slang-shader-definition` | `examples/python/spg-composite-aov/RangeHistogramKernel.slang.usda` | _(example only)_ |
| `lidar-render-graph` | `examples/python/spg-composite-aov/lidar_scene.usda` | `spg/do/composites.rst` ; _(skill: `skills/spg/SKILL.md`)_ |

#### `examples/c/radar`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `configure-nonvisual-materials` | `examples/c/radar/radar_example.usda` | `materials/nonvisual_sensor_materials.rst`, `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst` ; _(skill: `skills/nonvisual-materials/SKILL.md`)_ |
| `doc-nonvisual-materials-python` | `usd/test_usd_python_examples.py` | `materials/nonvisual_sensor_materials.rst` |
| `configure-radar-pointcloud-output` | `examples/c/radar/radar_example.usda` | `sensors/nonvisual/radar_wpm_dmat/outputs.rst` ; _(skill: `skills/configuring-radar-sensors/SKILL.md`)_ |
| `configure-radar-sensor` | `examples/c/radar/radar_example.usda` | `sensors/nonvisual/radar_wpm_dmat/attributes.rst`, `sensors/nonvisual/radar_wpm_dmat/index.rst` ; _(skill: `skills/configuring-radar-sensors/SKILL.md`)_ |
| `load-radar-scene` | `examples/c/radar/main.cpp` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |
| `read-radar-pointcloud` | `examples/c/radar/main.cpp` | `sensors/nonvisual/radar_wpm_dmat/outputs.rst` ; _(skill: `skills/interpreting-radar-pointclouds/SKILL.md`)_, _(skill: `skills/reading-sensor-pointclouds/SKILL.md`)_ |
| `report-radar-observation` | `examples/c/radar/main.cpp` | _(example only)_ |
| `step-radar-pointcloud` | `examples/c/radar/main.cpp` | _(skill: `skills/reading-sensor-pointclouds/SKILL.md`)_ |
| `update-stage-time-helper` | `examples/c/radar/main.cpp` | _(example only)_ |
| `warm-up-radar` | `examples/c/radar/main.cpp` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |

#### `examples/python/crop-window`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `crop-window-setup` | `examples/python/crop-window/main.py` | _(example only)_ |
| `crop-window-step-and-verify` | `examples/python/crop-window/main.py` | _(example only)_ |

#### `examples/c/vulkan-interop`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `cuda-device-max-connections` | `examples/c/selection-spg/src/cuda/cuda_kernel.cpp` | _(skill: `skills/cuda-interop/SKILL.md`)_ |
| `initialize-and-create-renderer` | `examples/c/selection-spg/src/main.cpp` | `core/renderer_configuration.rst` ; _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `map-rendered-output-cuda-array` | `examples/c/selection-spg/src/main.cpp` | _(skill: `skills/cuda-interop/SKILL.md`)_, _(skill: `skills/mapping-attributes/SKILL.md`)_ |
| `resolve-cuda-device-uuid` | `examples/c/selection-spg/src/cuda/cuda_kernel.cpp` | `examples/c_vulkan_interop.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_ |
| `select-vulkan-device-by-cuda-uuid` | `examples/c/selection-spg/src/vk/vulkan_context.cpp` | `examples/c_vulkan_interop.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_ |
| `validate-render-output-cuda-device` | `examples/c/selection-spg/src/main.cpp` | `examples/c_vulkan_interop.rst` ; _(skill: `skills/cuda-interop/SKILL.md`)_ |
| `write-camera-transform` | `examples/c/selection-spg/src/main.cpp` | _(skill: `skills/writing-transforms/SKILL.md`)_ |

#### `c`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-attached-update-loop-c` | `c/test_stage_mutation.cpp` | `core/ovstage_integration.rst` |
| `doc-multi-rate-partial-outputs-c` | `c/test_sensor_configuration.cpp` | `sensors/common/multi_rate.rst` |
| `doc-multi-rate-step-c` | `c/test_sensor_configuration.cpp` | `sensors/common/multi_rate.rst` |

#### `python`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-attached-update-loop-python` | `python/test_stage_mutation.py` | `core/ovstage_integration.rst` |
| `doc-camera-aov-usda` | `python/test_camera_aovs.py` | _(skill: `skills/camera-outputs-rt2/SKILL.md`)_ |
| `doc-observer-output-policy-python` | `python/test_sensor_observer.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `doc-observer-simulation-step-python` | `python/test_sensor_observer.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `doc-observer-view-step-python` | `python/test_sensor_observer.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `python-lidar-example-reports-valid-pointcloud` | `python/test_sensor_examples.py` | _(test only)_ |
| `python-radar-example-reports-moving-detections` | `python/test_sensor_examples.py` | _(test only)_ |

#### `usd`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-lidar-wpm-firing-pattern-rotary` | `usd/data/lidar_wpm_firing_pattern_rotary.usda` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst`, `sensors/nonvisual/lidar_wpm/index.rst` |
| `doc-lidar-wpm-firing-pattern-rotary-python` | `usd/test_usd_python_examples.py` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst`, `sensors/nonvisual/lidar_wpm/index.rst` |
| `doc-lidar-wpm-firing-pattern-solid-state` | `usd/data/lidar_wpm_firing_pattern_solid_state.usda` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst` |
| `doc-lidar-wpm-firing-pattern-solid-state-python` | `usd/test_usd_python_examples.py` | `sensors/nonvisual/lidar_wpm/howto/firing_pattern.rst` |
| `doc-multi-rate-camera-python` | `usd/test_usd_python_examples.py` | `sensors/common/multi_rate.rst` |
| `doc-multi-rate-lidar-python` | `usd/test_usd_python_examples.py` | `sensors/common/multi_rate.rst`, `sensors/common/sensor_configuration.rst`, `sensors/nonvisual/lidar_core/howto/output_shaping.rst` |
| `doc-radar-second-scan` | `usd/data/radar_scan_configurations.usda` | `sensors/common/sensor_configuration.rst` |
| `test-spg-scene-composes` | `usd/test_spg_usda.py` | _(test only)_ |
| `test-spg-usda-parses` | `usd/test_spg_usda.py` | _(test only)_ |

#### `examples/python/multi-rate-sensors`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-multi-rate-camera-usda` | `examples/python/multi-rate-sensors/multi_rate.usda` | `sensors/common/multi_rate.rst` |
| `doc-multi-rate-lidar-usda` | `examples/python/multi-rate-sensors/multi_rate.usda` | `sensors/common/multi_rate.rst`, `sensors/common/sensor_configuration.rst`, `sensors/nonvisual/lidar_core/howto/output_shaping.rst` |
| `doc-multi-rate-partial-outputs` | `examples/python/multi-rate-sensors/main.py` | `examples/python_multi_rate_sensors.rst`, `sensors/common/multi_rate.rst` |
| `doc-multi-rate-step` | `examples/python/multi-rate-sensors/main.py` | `examples/python_multi_rate_sensors.rst`, `sensors/common/multi_rate.rst` |

#### `examples/c/sensor-observer`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-observer-copy-outputs-c` | `examples/c/sensor-observer/main.cpp` | `examples/c_sensor_observer.rst` |
| `doc-observer-output-policy-c` | `examples/c/sensor-observer/main.cpp` | _(example only)_ |
| `doc-observer-step-c` | `examples/c/sensor-observer/main.cpp` | `examples/c_sensor_observer.rst` |

#### `examples/c/minimal`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `fetch-results` | `examples/c/minimal/main.cpp` | _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `find-output-helper` | `examples/c/minimal/main.cpp` | _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_, _(skill: `skills/update-0-4-to-0-5/SKILL.md`)_ |
| `linking-models` | `examples/c/minimal/CMakeLists.txt` | `c_api/getting_started.rst` ; _(skill: `skills/project-setup-c/SKILL.md`)_ |
| `load-usd-and-wait` | `examples/c/minimal/main.cpp` | `core/async_status_errors.rst`, `scene/loading_usd.rst` ; _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/error-handling/SKILL.md`)_, _(skill: `skills/loading-usd/SKILL.md`)_, _(skill: `skills/project-setup-c/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `map-rendered-output-cpu` | `examples/c/minimal/main.cpp` | `sensors/common/sensor_outputs.rst` ; _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/reading-render-output/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |
| `project-setup` | `examples/c/minimal/CMakeLists.txt` | _(skill: `skills/project-setup-c/SKILL.md`)_ |
| `step-renderer` | `examples/c/minimal/main.cpp` | _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/async-operations/SKILL.md`)_, _(skill: `skills/loading-usd/SKILL.md`)_, _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `unmap-and-cleanup` | `examples/c/minimal/main.cpp` | `core/renderer_configuration.rst` ; _(skill: `skills/application-flow/SKILL.md`)_, _(skill: `skills/renderer-creation/SKILL.md`)_, _(skill: `skills/update-0_2-0_3/SKILL.md`)_ |

#### `examples/python/spg-grayscale`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `grayscale-kernel-template` | `examples/python/spg-grayscale/GrayscaleKernel.cu` | `spg/first_node.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `grayscale-slang-kernel-template` | `examples/python/spg-grayscale/GrayscaleKernel.slang` | _(example only)_ |
| `shader-definition-template` | `examples/python/spg-grayscale/GrayscaleKernel.usda` | `spg/first_node.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `slang-shader-definition-template` | `examples/python/spg-grayscale/GrayscaleKernel.slang.usda` | _(example only)_ |
| `spg-create-renderer` | `examples/python/spg-grayscale/main.py` | `spg/first_node.rst` |
| `spg-open-scene` | `examples/python/spg-grayscale/main.py` | `spg/first_node.rst` |
| `spg-read-output-aov` | `examples/python/spg-grayscale/main.py` | `spg/do/aovs.rst`, `spg/first_node.rst` |
| `spg-warmup-and-step` | `examples/python/spg-grayscale/main.py` | `spg/first_node.rst` |

#### `examples/python/lidar`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `intensity-colors` | `examples/python/lidar/main.py` | _(skill: `skills/interpreting-lidar-pointclouds/SKILL.md`)_ |
| `log-lidar-points` | `examples/python/lidar/main.py` | _(skill: `skills/interpreting-lidar-pointclouds/SKILL.md`)_ |
| `parse-lidar-cli-args` | `examples/python/lidar/main.py` | _(example only)_ |
| `step-and-visualize-lidar` | `examples/python/lidar/main.py` | `sensors/first_sensor.rst` |
| `configure-lidar-panels-materials` | `examples/c/lidar/lidar_example_panels.usda` | _(example only)_ |
| `configure-lidar-panels-output` | `examples/c/lidar/lidar_example_panels.usda` | _(example only)_ |
| `configure-lidar-panels-sensor` | `examples/c/lidar/lidar_example_panels.usda` | _(example only)_ |
| `configure-lidar-panels-targets` | `examples/c/lidar/lidar_example_panels.usda` | _(example only)_ |

#### `examples/python/spg-pipeline`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `invert-kernel` | `examples/python/spg-pipeline/InvertKernel.cu` | `spg/do/values.rst` |
| `invert-shader-definition` | `examples/python/spg-pipeline/InvertKernel.usda` | `spg/do/values.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `invert-slang-kernel` | `examples/python/spg-pipeline/InvertKernel.slang` | `spg/do/descriptor_sets.rst`, `spg/do/values.rst` |
| `invert-slang-shader-definition` | `examples/python/spg-pipeline/InvertKernel.slang.usda` | _(example only)_ |
| `run-spg-pipeline` | `examples/python/spg-pipeline/main.py` | _(example only)_ |

#### `examples/python/radar`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `log-radar-points` | `examples/python/radar/main.py` | _(skill: `skills/interpreting-radar-pointclouds/SKILL.md`)_ |
| `parse-radar-cli-args` | `examples/python/radar/main.py` | _(example only)_ |
| `radial-velocity-colors` | `examples/python/radar/main.py` | `sensors/nonvisual/radar_wpm_dmat/outputs.rst` ; _(skill: `skills/interpreting-radar-pointclouds/SKILL.md`)_ |
| `step-and-visualize-radar` | `examples/python/radar/main.py` | _(example only)_ |
| `configure-radar-field-materials` | `examples/c/radar/radar_example_field.usda` | _(example only)_ |
| `configure-radar-field-output` | `examples/c/radar/radar_example_field.usda` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |
| `configure-radar-field-sensor` | `examples/c/radar/radar_example_field.usda` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |
| `configure-radar-field-targets` | `examples/c/radar/radar_example_field.usda` | _(example only)_ |

#### `examples/python/spg-scene-query`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `marker-overlay-kernel` | `examples/python/spg-scene-query/MarkerOverlayKernel.cu` | _(example only)_ |
| `marker-overlay-shader-definition` | `examples/python/spg-scene-query/MarkerOverlayKernel.usda` | _(example only)_ |
| `marker-overlay-slang-kernel` | `examples/python/spg-scene-query/MarkerOverlayKernel.slang` | _(example only)_ |
| `overlay-render-graph` | `examples/python/spg-scene-query/overlay_scene.usda` | _(example only)_ |
| `overlay-rig` | `examples/python/spg-scene-query/overlay_scene.usda` | _(example only)_ |
| `overlay-settings` | `examples/python/spg-scene-query/overlay_scene.usda` | _(example only)_ |
| `scene-query-populate` | `examples/python/spg-scene-query/main.py` | `examples/python_spg_scene_query.rst`, `spg/do/scene_queries.rst` ; _(skill: `skills/spg/SKILL.md`)_ |

#### `examples/python/spg-previous-frame`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `motion-kernel` | `examples/python/spg-previous-frame/MotionKernel.cu` | _(example only)_ |
| `motion-shader-definition` | `examples/python/spg-previous-frame/MotionKernel.slang.usda` | `examples/python_spg_previous_frame.rst` |
| `previous-frame-moving-and-still` | `examples/python/spg-previous-frame/main.py` | _(example only)_ |

#### `examples/python/spg-raygen`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `pipeline-bindings` | `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang` | _(example only)_ |
| `pipeline-entry` | `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang` | _(example only)_ |
| `pipeline-entrypoints` | `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang` | `spg/do/raygen.rst` |
| `pipeline-render-graph` | `examples/python/spg-raygen/cornell_box_pipeline_scene.usda` | _(example only)_ |
| `pipeline-shader-definition` | `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang.usda` | _(example only)_ |
| `raygen-bindings` | `examples/python/spg-raygen/RaygenCornellBox.slang` | `spg/do/raygen.rst` |
| `raygen-entry` | `examples/python/spg-raygen/RaygenCornellBox.slang` | _(example only)_ |
| `raygen-render-graph` | `examples/python/spg-raygen/cornell_box_scene.usda` | _(example only)_ |
| `raygen-shader-definition` | `examples/python/spg-raygen/RaygenCornellBox.slang.usda` | _(example only)_ |

#### `examples/python/projectors`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `projectors-create-renderer` | `examples/python/projectors/main.py` | _(skill: `skills/renderer-creation/SKILL.md`)_ |
| `projectors-load-usd` | `examples/python/projectors/main.py` | _(skill: `skills/loading-usd/SKILL.md`)_ |
| `projectors-render` | `examples/python/projectors/main.py` | _(skill: `skills/stepping-and-rendering/SKILL.md`)_ |
| `projectors-save-png` | `examples/python/projectors/main.py` | _(skill: `skills/reading-render-output/SKILL.md`)_ |
| `projectors-warmup` | `examples/python/projectors/main.py` | _(skill: `skills/warmup/SKILL.md`)_ |

#### `examples/python/spg-builtin-nodes`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `run-spg-builtin-nodes` | `examples/python/spg-builtin-nodes/main.py` | _(example only)_ |
| `save-render-var` | `examples/python/spg-builtin-nodes/main.py` | _(example only)_ |

#### `examples/python/sliced-rendering`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `sliced-rendering-render-and-stitch` | `examples/python/sliced-rendering/main.py` | _(skill: `skills/sliced-rendering/SKILL.md`)_ |
| `sliced-rendering-setup` | `examples/python/sliced-rendering/main.py` | _(skill: `skills/sliced-rendering/SKILL.md`)_ |

#### `examples/python/spg-stateful`

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `trail-kernel` | `examples/python/spg-stateful/TrailKernel.cu` | _(example only)_ |
| `trail-move-and-step` | `examples/python/spg-stateful/main.py` | _(example only)_ |
| `trail-shader-definition` | `examples/python/spg-stateful/TrailKernel.usda` | _(example only)_ |
| `trail-slang-kernel` | `examples/python/spg-stateful/TrailKernel.slang` | _(example only)_ |
| `trail-slang-shader-definition` | `examples/python/spg-stateful/TrailKernel.slang.usda` | _(example only)_ |


### Runtime textures

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-runtime-texture-usda` | `data/ovrtx-test-runtime-textures.usda` | `materials/runtime_textures.rst` |
| `doc-runtime-texture-usd-python` | `usd/test_runtime_textures.py` | `materials/runtime_textures.rst` |
| `doc-runtime-texture-ovstage-python` | `python/test_runtime_textures.py` | `materials/runtime_textures.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-runtime-texture-python-producer` | `python/test_runtime_textures.py` | `materials/runtime_textures.rst` |
| `doc-runtime-texture-python-update` | `python/test_runtime_textures.py` | `materials/runtime_textures.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-runtime-texture-c-update` | `examples/c/runtime-textures/main.cpp` | `examples/c_runtime_textures.rst`, `materials/runtime_textures.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-runtime-texture-luminance` | `examples/python/runtime-textures/main.py` | `examples/python_runtime_textures.rst` |
| `doc-runtime-texture-camera-feedback` | `examples/python/runtime-textures/main.py` | `examples/python_runtime_textures.rst` ; _(skill: `skills/writing-attributes/SKILL.md`)_ |
| `doc-runtime-texture-carter-motion` | `examples/python/runtime-textures/main.py` | `examples/python_runtime_textures.rst` |

### Test-only snippets that arrived with main

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-matrix-compatibility-round-trip` | `python/test_attribute_shapes.py` | _(test only)_ |
| `doc-pt-independent-first-bounce-outputs` | `python/test_camera_aovs.py` | _(test only)_ |

### Gaussian rendering variants

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-gaussian-non-stochastic` | `examples/python/gaussian-splats/non_stochastic.usda` | `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst`, `geometry/gaussian_splats.rst` |
| `doc-gaussian-stochastic` | `examples/python/gaussian-splats/stochastic.usda` | _(example only)_ |
| `doc-gaussian-non-stochastic-python` | `usd/test_gaussian_splats_usda.py` | `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst`, `geometry/gaussian_splats.rst` ; _(skill: `skills/render-settings/SKILL.md`)_ |
| `doc-gaussian-sh-diffuse` | `examples/python/gaussian-splats/sh_diffuse.usda` | `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst`, `geometry/gaussian_splats.rst` |
| `doc-gaussian-sh-diffuse-python` | `usd/test_gaussian_splats_usda.py` | `examples/c_gaussian_splats.rst`, `examples/python_gaussian_splats.rst`, `geometry/gaussian_splats.rst` ; _(skill: `skills/binding-materials/SKILL.md`)_ |

### Selection and frame-generation examples

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `enable-dlssg` | `examples/c/vulkan-interop/src/main.cpp` | _(skill: `skills/render-settings/SKILL.md`)_ |
| `selection-spg-geometry-gpu` | `examples/c/selection-spg/data/selection_geometry.usda` | _(example only)_ |
| `selection-spg-initial-selection` | `examples/c/selection-spg/src/main.cpp` | `examples/c_selection_spg.rst` |
| `selection-spg-outline-kernel` | `examples/c/selection-spg/SelectionOutline.slang` | `examples/c_selection_spg.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `selection-spg-present-output` | `examples/c/selection-spg/src/main.cpp` | _(example only)_ |
| `selection-spg-render-graph` | `examples/c/selection-spg/selection_scene.usda` | `examples/c_selection_spg.rst` ; _(skill: `skills/spg/SKILL.md`)_ |

### Sensor configuration authoring

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-sensor-config-minimal` | `usd/data/sensor_configuration_minimal.usda` | `sensors/common/sensor_configuration.rst` |
| `doc-sensor-config-minimal-python` | `usd/test_usd_python_examples.py` | `sensors/common/sensor_configuration.rst` |
| `doc-sensor-config-override` | `usd/data/sensor_configuration_override.usda` | `sensors/common/sensor_configuration.rst` |
| `doc-sensor-config-override-python` | `usd/test_usd_python_examples.py` | `sensors/common/sensor_configuration.rst` |
| `doc-sensor-config-orientation` | `usd/data/sensor_configuration_orientation.usda` | `sensors/common/sensor_configuration.rst` |
| `doc-sensor-config-orientation-python` | `usd/test_usd_python_examples.py` | `sensors/common/sensor_configuration.rst` |

### Output configuration authoring

| Snippet | Source file | Used in RST |
|---------|-------------|-------------|
| `doc-output-lidar-channels-python` | `usd/test_usd_python_examples.py` | `sensors/common/output_configuration.rst` |
| `doc-output-inline-camera-python` | `usd/test_usd_python_examples.py` | `sensors/common/output_configuration.rst` |
| `doc-output-device-pinning-python` | `usd/test_usd_python_examples.py` | `sensors/common/output_configuration.rst` |


### Non-visual sensor authoring examples

The following USDA/Python pairs are checked for equivalent authored opinions by
`usd/test_nonvisual_authoring.py`. Tutorial reference examples also check composed
sensor data. These checks do not execute sensor models.

| Snippet | Source | Used in |
|---|---|---|
| `doc-nonvisual-acoustic-wpm-howto-array-topology-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/acoustic_wpm/howto/array_topology.rst` |
| `doc-nonvisual-lidar-core-howto-field-of-view-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/howto/field_of_view.rst` |
| `doc-nonvisual-lidar-core-howto-firing-pattern-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/howto/firing_pattern.rst` |
| `doc-nonvisual-lidar-core-howto-firing-pattern-2-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/howto/firing_pattern.rst` |
| `doc-nonvisual-lidar-core-howto-intensity-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/howto/intensity.rst` |
| `doc-nonvisual-lidar-core-howto-motion-artifacts-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/howto/motion_artifacts.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-2-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-3-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-4-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-5-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-2-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-3-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-4-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-5-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-6-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-7-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-8-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-wpm-howto-tile-lidars-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_wpm/howto/tile_lidars.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/howto/choose_parameters.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/howto/choose_parameters.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-scan-configurations-1-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/howto/scan_configurations.rst` |
| `doc-nonvisual-example-configure-acoustic-sensor-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/acoustic_wpm/attributes.rst`, `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst`, `sensors/nonvisual/acoustic_wpm/index.rst` |
| `doc-nonvisual-example-configure-acoustic-output-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst`, `sensors/nonvisual/acoustic_wpm/outputs.rst` |
| `doc-nonvisual-example-configure-nonvisual-materials-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/acoustic_wpm/howto/set_up_sensor.rst` |
| `doc-nonvisual-example-configure-lidar-sensor-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/attributes.rst`, `sensors/nonvisual/lidar_core/index.rst` |
| `doc-nonvisual-example-configure-lidar-pointcloud-output-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/lidar_core/outputs.rst` |
| `doc-nonvisual-example-configure-radar-sensor-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/attributes.rst`, `sensors/nonvisual/radar_wpm_dmat/index.rst` |
| `doc-nonvisual-example-configure-radar-field-sensor-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |
| `doc-nonvisual-example-configure-radar-field-output-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/howto/set_up_sensor.rst` |
| `doc-nonvisual-example-radar-pointcloud-python` | `usd/test_nonvisual_authoring.py` | `sensors/nonvisual/radar_wpm_dmat/outputs.rst` |
| `doc-nonvisual-acoustic-wpm-howto-array-topology-1` | `usd/data/nonvisual/acoustic_wpm_howto_array_topology_1.usda` | `sensors/nonvisual/acoustic_wpm/howto/array_topology.rst` |
| `doc-nonvisual-lidar-core-howto-field-of-view-1` | `usd/data/nonvisual/lidar_core_howto_field_of_view_1.usda` | `sensors/nonvisual/lidar_core/howto/field_of_view.rst` |
| `doc-nonvisual-lidar-core-howto-firing-pattern-1` | `usd/data/nonvisual/lidar_core_howto_firing_pattern_1.usda` | `sensors/nonvisual/lidar_core/howto/firing_pattern.rst` |
| `doc-nonvisual-lidar-core-howto-firing-pattern-2` | `usd/data/nonvisual/lidar_core_howto_firing_pattern_2.usda` | `sensors/nonvisual/lidar_core/howto/firing_pattern.rst` |
| `doc-nonvisual-lidar-core-howto-intensity-1` | `usd/data/nonvisual/lidar_core_howto_intensity_1.usda` | `sensors/nonvisual/lidar_core/howto/intensity.rst` |
| `doc-nonvisual-lidar-core-howto-motion-artifacts-1` | `usd/data/nonvisual/lidar_core_howto_motion_artifacts_1.usda` | `sensors/nonvisual/lidar_core/howto/motion_artifacts.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-1` | `usd/data/nonvisual/lidar_core_tutorials_blickfeld_cube1_1.usda` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-2` | `usd/data/nonvisual/lidar_core_tutorials_blickfeld_cube1_2.usda` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-3` | `usd/data/nonvisual/lidar_core_tutorials_blickfeld_cube1_3.usda` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-4` | `usd/data/nonvisual/lidar_core_tutorials_blickfeld_cube1_4.usda` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-5` | `usd/data/nonvisual/lidar_core_tutorials_blickfeld_cube1_5.usda` | `sensors/nonvisual/lidar_core/tutorials/blickfeld_cube1.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-1` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_1.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-2` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_2.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-3` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_3.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-4` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_4.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-5` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_5.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-6` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_6.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-7` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_7.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-sick-tim781-8` | `usd/data/nonvisual/lidar_core_tutorials_sick_tim781_8.usda` | `sensors/nonvisual/lidar_core/tutorials/sick_tim781.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_1.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_2.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_3.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_4.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_5.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6` | `usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_6.usda` | `sensors/nonvisual/lidar_core/tutorials/velodyne_alpha_prime.rst` |
| `doc-nonvisual-lidar-wpm-howto-tile-lidars-1` | `usd/data/nonvisual/lidar_wpm_howto_tile_lidars_1.usda` | `sensors/nonvisual/lidar_wpm/howto/tile_lidars.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1` | `usd/data/nonvisual/radar_wpm_dmat_howto_choose_parameters_1.usda` | `sensors/nonvisual/radar_wpm_dmat/howto/choose_parameters.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2` | `usd/data/nonvisual/radar_wpm_dmat_howto_choose_parameters_2.usda` | `sensors/nonvisual/radar_wpm_dmat/howto/choose_parameters.rst` |
| `doc-nonvisual-radar-wpm-dmat-howto-scan-configurations-1` | `usd/data/nonvisual/radar_wpm_dmat_howto_scan_configurations_1.usda` | `sensors/nonvisual/radar_wpm_dmat/howto/scan_configurations.rst` |

`python/test_acoustic_range_mapping.py` checks the acoustic example's basic-mode
range-bin conversion on the CPU, including the first/last bins and edited sample durations.

### Additional validated snippets

| Snippet | Source | Used in |
|---|---|---|
| `blur-horizontal-launch` | `examples/python/spg-blur/BlurKernel.cu.lua` | `examples/python_spg_blur.rst`, `spg/do/launch_geometry.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `blur-slang-horizontal-launch` | `examples/python/spg-blur/BlurKernel.slang.lua` | _(example only)_ |
| `blur-slang-vertical-launch` | `examples/python/spg-blur/BlurKernel.slang.lua` | `spg/do/launch_geometry.rst` |
| `blur-slang-weights` | `examples/python/spg-blur/BlurKernel.slang.lua` | `spg/do/caching.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `blur-vertical-launch` | `examples/python/spg-blur/BlurKernel.cu.lua` | `examples/python_spg_blur.rst`, `spg/do/launch_geometry.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `blur-weights` | `examples/python/spg-blur/BlurKernel.cu.lua` | `examples/python_spg_blur.rst`, `spg/do/caching.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `checker-launch` | `examples/python/spg-generate/CheckerKernel.cu.lua` | `examples/python_spg_generate.rst`, `spg/do/generate.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `checker-slang-launch` | `examples/python/spg-generate/CheckerKernel.slang.lua` | `spg/do/generate.rst` |
| `grayscale-launch-template` | `examples/python/spg-grayscale/GrayscaleKernel.cu.lua` | `spg/do/textures_buffers.rst`, `spg/first_node.rst`, `spg/ref/lua_contract.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `grayscale-slang-launch-template` | `examples/python/spg-grayscale/GrayscaleKernel.slang.lua` | `spg/do/textures_buffers.rst`, `spg/ref/lua_contract.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `histogram-binding` | `examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua` | `examples/python_spg_composite_aov.rst`, `spg/do/textures_buffers.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `histogram-launch` | `examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua` | `spg/do/composites.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `histogram-slang-binding` | `examples/python/spg-composite-aov/RangeHistogramKernel.slang.lua` | `spg/do/textures_buffers.rst` |
| `histogram-slang-launch` | `examples/python/spg-composite-aov/RangeHistogramKernel.slang.lua` | `spg/do/composites.rst` |
| `invert-launch` | `examples/python/spg-pipeline/InvertKernel.cu.lua` | `spg/do/values.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `invert-slang-launch` | `examples/python/spg-pipeline/InvertKernel.slang.lua` | `spg/do/descriptor_sets.rst`, `spg/do/values.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `motion-launch` | `examples/python/spg-previous-frame/MotionKernel.cu.lua` | `examples/python_spg_previous_frame.rst` |
| `motion-slang-launch` | `examples/python/spg-previous-frame/MotionKernel.slang.lua` | _(example only)_ |
| `pipeline-launch` | `examples/python/spg-raygen/RaygenCornellBoxPipeline.slang.lua` | `spg/do/raygen.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `raygen-launch` | `examples/python/spg-raygen/RaygenCornellBox.slang.lua` | `spg/do/raygen.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `scene-query-batch` | `examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua` | `spg/do/scene_queries.rst` |
| `scene-query-camera` | `examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua` | `examples/python_spg_scene_query.rst`, `spg/do/scene_queries.rst` |
| `scene-query-launch` | `examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua` | `spg/do/scene_queries.rst` |
| `scene-query-prim` | `examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua` | `spg/do/scene_queries.rst` |
| `scene-query-slang-launch` | `examples/python/spg-scene-query/MarkerOverlayKernel.slang.lua` | `spg/do/scene_queries.rst` |
| `selection-spg-launch` | `examples/c/selection-spg/SelectionOutline.slang.lua` | `examples/c_selection_spg.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `trail-alloc` | `examples/python/spg-stateful/TrailKernel.cu.lua` | `spg/do/state.rst`, `spg/ref/lua_cuda.rst` ; _(skill: `skills/spg/SKILL.md`)_ |
| `trail-slang-alloc` | `examples/python/spg-stateful/TrailKernel.slang.lua` | `spg/do/state.rst`, `spg/ref/lua_slang.rst` ; _(skill: `skills/spg/SKILL.md`)_ |

### Recursive USD fixture inventory

Paths relative to `usd/data/`; checked recursively, including model subdirectories.

```text
── camera_attributes.usda
── camera_core_request.usda
── camera_core_versioning.usda
── camera_lens_calibration.usda
── camera_rolling_shutter.usda
── camera_scene_partitions.usda
── camera_sensor_render_product.usda
── decal.usda
── decal_binding.usda
── depth_sensor_render_product.usda
── depth_sensor_versioning.usda
── dlss_nr.usda
── finite_dome_lights.usda
── gaussian_splat.usda
── ghost_lights.usda
── inline_sublayers_camera_renderproduct.usda
── lidar_wpm_firing_pattern_rotary.usda
── lidar_wpm_firing_pattern_solid_state.usda
── lidar_wpm_output_request.usda
── light_linking.usda
── light_path_expressions.usda
── light_shaping.usda
── light_types.usda
── mesh_lights.usda
── minimal_render_product.usda
── multi_render_product_shared_vars.usda
── nonvisual/acoustic_wpm_howto_array_topology_1.usda
── nonvisual/lidar_core_howto_field_of_view_1.usda
── nonvisual/lidar_core_howto_firing_pattern_1.usda
── nonvisual/lidar_core_howto_firing_pattern_2.usda
── nonvisual/lidar_core_howto_intensity_1.usda
── nonvisual/lidar_core_howto_motion_artifacts_1.usda
── nonvisual/lidar_core_tutorials_blickfeld_cube1_1.usda
── nonvisual/lidar_core_tutorials_blickfeld_cube1_2.usda
── nonvisual/lidar_core_tutorials_blickfeld_cube1_3.usda
── nonvisual/lidar_core_tutorials_blickfeld_cube1_4.usda
── nonvisual/lidar_core_tutorials_blickfeld_cube1_5.usda
── nonvisual/lidar_core_tutorials_sick_tim781_1.usda
── nonvisual/lidar_core_tutorials_sick_tim781_2.usda
── nonvisual/lidar_core_tutorials_sick_tim781_3.usda
── nonvisual/lidar_core_tutorials_sick_tim781_4.usda
── nonvisual/lidar_core_tutorials_sick_tim781_5.usda
── nonvisual/lidar_core_tutorials_sick_tim781_6.usda
── nonvisual/lidar_core_tutorials_sick_tim781_7.usda
── nonvisual/lidar_core_tutorials_sick_tim781_8.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_1.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_2.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_3.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_4.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_5.usda
── nonvisual/lidar_core_tutorials_velodyne_alpha_prime_6.usda
── nonvisual/lidar_wpm_howto_tile_lidars_1.usda
── nonvisual/radar_wpm_dmat_howto_choose_parameters_1.usda
── nonvisual/radar_wpm_dmat_howto_choose_parameters_2.usda
── nonvisual/radar_wpm_dmat_howto_scan_configurations_1.usda
── physical_lighting.usda
── plugin_physical_light.usda
── projector_lights.usda
── radar_scan_configurations.usda
── semantic_label_base.usda
── semantic_label_overrides.usda
── sensor_configuration_minimal.usda
── sensor_configuration_orientation.usda
── sensor_configuration_override.usda
── spectral_rendering.usda
```
