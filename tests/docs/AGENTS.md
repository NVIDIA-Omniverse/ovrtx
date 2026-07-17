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

- Stage-owning tests in `python/` request the attached ovstage fixture. Focused compatibility tests still exercise deprecated renderer wrappers in `test_all_attributes.py`, `test_attribute_bindings.py`, `test_attribute_read.py`, `test_base.py`, `test_picking_selection.py`, and `test_stage_query.py`.
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
│   ├── test_all_attributes.py                   # Authored USD attribute read/write snippets and coverage
│   ├── test_camera_aovs.py                      # Smoke tests for all camera AOVs
│   ├── test_camera_sensors.py                   # Snippets for camera_sensors.rst
│   ├── test_render_modes.py                     # Tests for camera render modes
│   └── test_sensor_configuration.py             # Snippets for sensor_configuration.rst
├── usd/
│   ├── pyproject.toml                           # usd-core + pytest
│   ├── conftest.py                              # validate_usda() helper
│   ├── data/
│   │   ├── camera_sensor_render_product.usda    # USDA with snippet markers
│   │   ├── minimal_render_product.usda
│   │   └── multi_render_product_shared_vars.usda
│   ├── test_camera_sensors_usda.py              # Validates USDA structure
│   ├── test_sensor_config_usda.py               # Validates USDA structure
│   └── test_usd_python_examples.py              # USD Python API equivalents
└── c/
    ├── CMakeLists.txt                           # CMake project (GoogleTest + ovrtx C API)
    ├── helpers.h                                # Shared test helpers
    ├── test_all_attributes.cpp                  # Authored USD attribute read/write snippets and coverage (C)
    ├── test_camera_aovs.cpp                     # Smoke tests for all camera AOVs (C)
    ├── test_camera_sensors.cpp                  # C snippets for camera_sensors.rst
    └── test_sensor_configuration.cpp            # C snippets for sensor_configuration.rst
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
| `doc-camera-sensor-render-product` | `usd/data/camera_sensor_render_product.usda` | `camera_sensors.rst` |
| `doc-camera-sensor-render-product-python` | `usd/test_usd_python_examples.py` | `camera_sensors.rst` |
| `doc-step-and-map-camera-outputs` | `python/test_camera_sensors.py` | `camera_sensors.rst` |
| `doc-camera-aov-smoke-test` | `python/test_camera_aovs.py` | _(test only)_ |
| `doc-camera-aov-smoke-test-c` | `c/test_camera_aovs.cpp` | _(test only)_ |
| `doc-minimal-render-product` | `usd/data/minimal_render_product.usda` | `sensor_configuration.rst` |
| `doc-minimal-render-product-python` | `usd/test_usd_python_examples.py` | `sensor_configuration.rst` |
| `doc-multi-render-product-shared-vars` | `usd/data/multi_render_product_shared_vars.usda` | `sensor_configuration.rst` |
| `doc-multi-render-product-shared-vars-python` | `usd/test_usd_python_examples.py` | `sensor_configuration.rst` |
| `doc-step-multiple-render-products` | `python/test_sensor_configuration.py` | `sensor_configuration.rst` |
| `doc-add-render-config-layer` | `python/test_sensor_configuration.py` | `sensor_configuration.rst` |
| `doc-step-and-map-camera-outputs-c` | `c/test_camera_sensors.cpp` | `camera_sensors.rst` |
| `doc-step-multiple-render-products-c` | `c/test_sensor_configuration.cpp` | `sensor_configuration.rst` |
| `doc-add-render-config-layer-c` | `c/test_sensor_configuration.cpp` | `sensor_configuration.rst` |
| `doc-path-tracing-render-product` | `python/test_render_modes.py` | `sensors/cameras/render_modes.rst` |
| `doc-bind-material` | `python/test_base.py` | `scene/material_binding.rst` |
| `doc-bind-material-c` | `c/test_base.cpp` | `scene/material_binding.rst` |
| `doc-set-render-setting` | `python/test_base.py` | `sensors/configuration.rst` |
| `doc-set-render-setting-c` | `c/test_base.cpp` | `sensors/configuration.rst` |
| `doc-warmup` | `python/test_base.py` | _(skill only)_ |
| `doc-warmup-c` | `c/test_base.cpp` | _(skill only)_ |
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
| `doc-get-last-error-c` | `c/test_support_api.cpp` | _(skill only)_ |
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
