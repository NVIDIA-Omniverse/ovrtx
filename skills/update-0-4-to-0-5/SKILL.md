---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
name: update-0-4-to-0-5
description: >
  Upgrade an existing Python or C/C++ application from ovrtx 0.4.x to 0.5.x.
  Use when porting application code, authored sensor USD, RenderVar output
  handling, DLPack interoperability, Windows renderer configuration, or an
  attached ovstage 0.1 workflow to the ovrtx 0.5 release train.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - "0.5"
  - ovstage
  - migration
tools:
  - Read
  - Grep
  - Edit
---

# Update OVRTX 0.4 to 0.5

Port an existing application with the minimum changes required by the 0.5
public contract. Do not adopt unrelated 0.5 features or rewrite working code.

## When to Use

Use this skill when upgrading an existing Python, C, or C++ application from
OVRTX 0.4.x to 0.5.x. It also covers authored sensor USD and attached-mode
applications that must upgrade from OVStage 0.1.x to the matching 0.2.x release.

Do not use it for applications starting on OVRTX 0.3.x or earlier; apply the
corresponding earlier-version migration skill first.

## Inputs

Resolve these before editing:

- The exact source and target OVRTX versions and package locations.
- Whether the application uses Python, C/C++, authored USD, or a combination.
- Whether it uses attached OVStage and directly consumes OVStage data.
- The source, build, deployment, and generated-asset files in migration scope.
- Whether 0.4-equivalent rendered output must be preserved.

## Prerequisites

- Access to the application's current source, package pins, build configuration,
  authored USD, and accepted output baselines when visual compatibility matters.
- Matching OVRTX 0.5.x and OVStage 0.2.x packages from the same release train for
  attached mode.
- Read the authoritative sources below before changing APIs or data contracts.
- Runtime validation requires the GPU, driver, network, and unsandboxed execution
  prerequisites documented in [`../../AGENTS.md`](../../AGENTS.md).

## Scope

- Source: OVRTX 0.4.x, including 0.4.1, with optional OVStage 0.1.x.
- Target: OVRTX 0.5.x and, when attached mode is used, the matching OVStage
  0.2.x package from the same release train.
- Languages: Python, C, C++, and authored USD used by those applications.
- Preserve application behavior unless the user explicitly wants the new 0.5
  defaults.

This skill includes only changes that can require user source, build, deployment,
or authored-USD changes. Renderer bug fixes, performance work, tests, CI,
packaging reductions, documentation-only work, and optional new features are not
migration steps.

## Authoritative Sources

Before editing, read:

1. The `[0.5.0]` migration bullets in
   [`../../CHANGELOG.md`](../../CHANGELOG.md).
2. The installed 0.5 headers and Python signatures. They override release-note
   drafts and internal inventories.
3. [`../../include/ovrtx/ovrtx_types.h`](../../include/ovrtx/ovrtx_types.h),
   [`../../include/ovrtx/ovrtx_config.h`](../../include/ovrtx/ovrtx_config.h),
   and [`../reading-render-output/SKILL.md`](../reading-render-output/SKILL.md)
   when output or tensor APIs are present.
4. [`../../../../ovstage/public/CHANGELOG.md`](../../../../ovstage/public/CHANGELOG.md)
   when the application uses attached OVStage, OVStage population, or direct
   OVStage reads/writes.

Do not infer a migration from a ticket title alone. Confirm that the change is
present in the target package and absent from 0.4.

## Migration-Relevant Inventory

| Area | Inventory evidence | Applies when |
|---|---|---|
| Full RenderVar path identity | OMPE-94127 | The app fetches, indexes, logs, or compares render outputs. |
| Python DLPack surface | OMPE-102110, OMPE-104349, OMPE-105119, OMPE-105460 | The app imports `ManagedDLTensor`, uses `.tensor`, passes raw `DLTensor`, or inspects mapping metadata/lifetimes. |
| Vulkan-only Windows package | OMPE-103728 | The app selects DX12/Vulkan, has DX12 interop, or ships a pre-0.5 C binary. |
| Sensor schema/model versioning | OMPE-74104, OMPE-94528 through OMPE-94535 | The app authors acoustic, IDS, lidar, or radar sensors. |
| GenericModelOutput removal | OMPE-107766 | USD requests `sourceName = "GenericModelOutput"` or code imports the bundled GMO decoder. |
| Schema registration order | OMPE-94125, OMPE-103596 | OVRTX and OVStage or another OpenUSD runtime share a process. |
| One renderer per attached stage | OMPE-105429 | The app attaches one OVStage instance to more than one live OVRTX renderer. |
| Reset-stack Boolean dtype | OMPE-103960 | Low-level code reads/writes `omni:resetXformStack` and assumes `kDLUInt`. |
| OVStage population layouts | OMPE-102552 | Attached applications directly consume assets, path expressions, extents, or affected semantics. |
| OVStage loader packaging | OMPE-106739 | A C/C++ app manually links or deploys OVStage rather than using its package CMake config. |
| Other OVStage 0.2 public breaks | Paired-package changelog; not fully represented in the OVRTX Jira inventory | Attached applications use OVStage metadata, raw reads/maps, Python resource objects, physics schema fallbacks, or permissive 0.1 argument coercions. |
| Changed image defaults | OMPE-102343, OMPE-103674, OMPE-105838 | The app requires output equivalent to 0.4 and relied on an omitted setting. |

## Instructions

1. **Establish the real baseline.** Locate OVRTX and OVStage version pins,
   package roots, copied headers/libraries, lock files, and generated USD. Record
   whether the source is 0.4.0 or 0.4.1 and whether the application is Python,
   C/C++, or mixed.
2. **Update packages together.** Pin OVRTX to the requested 0.5 build. If the
   app uses attached mode, pin the matching OVStage 0.2 build from the same
   release train. Do not mix their bundled OpenUSD runtimes.
3. **Run the audit searches below before editing.** Apply a migration only when
   its search matches application code, build/deployment logic, or authored
   USD. Do not turn every conditional item into a source change.
4. **Migrate RenderVar identity first.** It affects nearly every output-reading
   application and makes later tensor tests address the correct output.
5. **Migrate Python tensor handling.** Remove `ManagedDLTensor` dependencies,
   consume mappings through DLPack, replace raw `DLTensor` inputs, and fix
   device/lifetime assumptions.
6. **Migrate removed configuration and outputs.** Remove Windows backend
   selection and replace `GenericModelOutput` where used.
7. **Migrate sensor assets.** Resolve each applied sensor schema version and
   update `omni:sensor:modelVersion`; do not use the deprecation escape hatch as
   the permanent migration.
8. **Fix initialization order.** Register OVRTX schema paths before OpenUSD is
   loaded and before OVStage performs its first population.
9. **Apply OVStage 0.2 data-contract migrations** only to code that directly
   reads or writes the affected representations. Ordinary OVRTX render-output
   consumers do not need these edits.
10. **Decide whether to preserve 0.4 rendering defaults.** Author explicit old
    values only when image compatibility is required; otherwise accept and test
    the new 0.5 defaults.
11. **Rebuild C/C++ applications.** Do not reuse a 0.4 binary with 0.5 headers or
    runtime libraries. Rebuild all translation units that include OVRTX or OVX
    public headers.
12. **Validate representative workflows.** Test renderer creation, scene
    population, one step, every consumed RenderVar, sensor output parsing,
    teardown, and Windows Vulkan/CUDA interop when applicable. Compare images or
    tensors against the application's accepted 0.4 baseline when behavior must
    remain stable.

## Audit Searches and Required Actions

### 1. RenderVar path identity

Search Python for `frame.render_vars`, `RenderVarOutput.name`,
`MappedRenderVar.name`, and dictionaries keyed by AOV/source names such as
`LdrColor`, `HdrColor`, `DepthSD`, or `PointCloud`.

- Index `frame.render_vars` by the full authored RenderVar prim path, not the
  prim name and not `sourceName`. A unique prim name is insufficient.
- Replace `RenderVarOutput.name` and `MappedRenderVar.name` with
  `render_var_path`.
- Use `source_name` only when code needs the AOV kind; do not use it as output
  identity.

Search C/C++ for `render_var_name` and `ovrtx_render_var_output_t`.

- Replace `ovrtx_render_var_output_t.render_var_name` with `render_var_path`.
- Use the new `source_name` and `source_type` fields only for classification.
- Treat `ovrtx_render_var_t.name` as a full RenderVar prim path.
- Recompile because the public result structure layout changed.

> **Source (Python):** [`../../examples/python/minimal/main.py`](../../examples/python/minimal/main.py) snippet `read-render-output`.
> **Source (C lookup):** [`../../examples/c/minimal/main.cpp`](../../examples/c/minimal/main.cpp) snippet `find-output-helper`.

### 2. Python DLPack and mapping objects

Search for `ManagedDLTensor`, `MappedRenderVar.tensor`, `.numpy()`,
`.to_bytes()`, `.raw_dltensor`, `isinstance` checks against the old wrapper,
direct `DLTensor(...)` inputs, and comparisons of `.device` with
`ovrtx.Device`.

- Remove public imports and direct construction of `ManagedDLTensor`.
- For a single-tensor RenderVar, pass the `MappedRenderVar` directly to a
  DLPack consumer. For composite outputs, select a named `RenderVarTensor`; use
  `params` for named parameters.
- Replace `.tensor.numpy()` or `.numpy()` with the consuming library's
  `from_dlpack`. Take a copy through that library when independent storage is
  required.
- A CPU-only consumer cannot read a CUDA pointer. Map to CPU or use a
  CUDA-capable DLPack consumer such as Warp, PyTorch, or CuPy.
- `device` is now a `DLDevice`. Update comparisons to inspect its DLPack device
  type and device id rather than comparing it with OVRTX's mapping-request
  `Device` enum.
- Do not inspect mapping properties after `unmap()` or context exit. Capture
  metadata first, or retain a tensor/param view created while mapped.
- Renderer tensor inputs must implement `__dlpack__`; raw ctypes `DLTensor`
  structures are no longer accepted by Python write, bind, map, or read-
  destination paths.
- Deprecated attribute reads with `dest=` now return the exact destination
  object. Remove assumptions that the result is a separate wrapper.
- A supplied read destination must have zero byte offset and C-contiguous
  layout.

> **Source:** [`../reading-render-output/SKILL.md`](../reading-render-output/SKILL.md).

### 3. Windows backend selection

Search for `use_vulkan`, `OVRTX_CONFIG_USE_VULKAN`,
`ovrtx_config_entry_use_vulkan`, DX12 interop, and backend-dependent deployment
branches.

- Remove the retired configuration field/key/helper.
- Treat Windows OVRTX 0.5 as Vulkan-only.
- Port DX12-specific graphics interop to Vulkan or disable that integration.
- Recompile C/C++; passing the retired numeric key returns `OVRTX_API_ERROR`.

### 4. Sensor versioning and GenericModelOutput

Search USD generators and assets for `OmniSensorGeneric`,
`omni:sensor:modelVersion`, dotted versions such as `0.0.0`,
`GenericModelOutput`, and imports from the bundled GMO Python extension.

- The applied `OmniSensorGeneric*API_N` suffix selects schema version `N`;
  unsuffixed schemas select version 1.
- Set `omni:sensor:modelVersion` to `latest` or a supported positive integer
  string for that schema. Dotted semantic versions are invalid.
- Replace `sourceName = "GenericModelOutput"` with the composite `PointCloud`
  RenderVar and author the channels the application consumes. Update parsing to
  read named tensors and params rather than a packed GMO buffer.
- If a separate consumer still needs packed GMO decoding, depend explicitly on
  the standalone `generic-model-output` package; OVRTX no longer bundles it.
- Prefer a supported sensor version. `sensors_allowed_deprecation_base` is a
  temporary compatibility gate and must exactly match the running OVRTX version,
  so using it creates another required edit at the next upgrade.

> **Source (lidar):** [`../configuring-lidar-sensors/SKILL.md`](../configuring-lidar-sensors/SKILL.md).
> **Source (radar):** [`../configuring-radar-sensors/SKILL.md`](../configuring-radar-sensors/SKILL.md).

### 5. Schema registration and reset-stack dtype

Search initialization code for `ovrtx_register_schema_paths`, creation of an
OVStage instance, the first population call, and any earlier import/load of an
OpenUSD runtime. Also find every `attach_ovstage` call and map attached stage
instances to live renderers.

- In C/C++, call `ovrtx_register_schema_paths()` before OpenUSD loads and before
  OVStage's first population. Registration now also makes the OVRTX schema
  families visible to attached OVStage population.
- In Python, call `ovrtx.register_schema_paths()` before creating/populating an
  OVStage or importing another OpenUSD runtime. Merely importing `ovrtx` does
  not register paths unless `OVRTX_PXR_SCHEMA_AUTO_REGISTER=1` was set before
  import.
- For a separate host OpenUSD runtime, enumerate/filter OVRTX plugin paths as
  described by `ovrtx_get_usd_plugin_paths()` and publish them before that
  runtime opens its first stage.
- Do not attach one OVStage instance to multiple live OVRTX renderers. Give each
  renderer its own stage, or detach the first renderer before attaching that
  stage to another; 0.5 rejects simultaneous attachment.

Search low-level attribute code for `omni:resetXformStack` with `kDLUInt`.
Change its declared dtype to `{kDLBool, 8, 1}`. Calls through
`ovrtx_set_reset_xform_stack()` keep the same `bool*` signature and need no
source edit.

### 6. Attached OVStage 0.2 data contracts

Search direct OVStage readers/writers and population consumers for
`ASSET_STRING`, `ASSET_PATH_ID`, `PATH_EXPRESSION_STRING`, `extent`, and switches
over attribute semantics.

- Assets are `(authored, resolved)` token-id pairs with
  `ASSET_PATH_ID`, `{kDLUInt, 64, 2}`. This applies to scalar and array assets;
  empty values are zero pairs.
- Path expressions are interned `{kDLUInt, 64, 1}` token ids, not UTF-8 byte
  rows. Resolve them through the path dictionary; scalar versus array is
  selected by `is_array`.
- `extent` on `UsdGeomImageable` is one non-array `{kDLFloat, 64, 6}` value in
  `(min xyz, max xyz)` order, not a two-element `float3[]`.
- Update semantic switches: Curves/Points `normals` report `POINT`; light and
  shadow colors report `VECTOR`; finite-dome, NeRF, and NuRec size/crop/offset
  attributes report `VECTOR`. Inspect the USD type when the original USD role
  matters.
- If C/C++ deployment manually names OVStage libraries, ship and link the new
  forwarding loader plus its runtime. Applications using the package CMake
  targets and setup helper retain the stable target and need no source change.

Also audit the rest of the OVStage 0.2 public changelog. These changes are
outside the original OVRTX Jira inventory but can still break an attached OVRTX
0.4 application when its OVStage dependency moves from 0.1 to 0.2:

- Stage metadata moved from `/__ovstage_population_stage_info__` to `/`, and
  its columns use the `usd-metadata:` prefix.
  `ovstage_population_stage_info_path()` was removed. Update stored paths,
  query filters, and metadata column names.
- Fixed-size reads/maps now expose one data-row dimension and put tuple width
  in `dtype.lanes`. Update code that expects shapes such as `(N, 3)` or
  `(N, 4, 4)`. Fixed-size writes without an index map must supply exactly one
  leading row per logical element rather than a flattened one-lane buffer.
- Populated USD bools now report `kDLBool`, not `kDLUInt`. Update dtype switches
  and assertions for every populated bool, not only `omni:resetXformStack`.
- `TIME_CODE` and `FRAME` semantics are now reported for the corresponding
  columns. Add those cases to exhaustive semantic switches and do not write a
  conflicting role such as `MATRIX` to a `frame4d` column.
- OVStage no longer bundles PhysX, deformable, or Newton schema definitions.
  Applications that depend on unauthored schema fallback properties must ship
  their own definitions and register them with
  `ovstage_population_register_usd_schemas()` before the first schema read.
- Python `PathDictionary.path_to_string(root_handle)` now returns `/`, not an
  empty string. Update root/sentinel tests that treated `""` as the root.
- Keep each Python `ReadGroup` alive while using arrays or DLPack views borrowed
  from it; use its context manager and copy data that must outlive the group.
  Do not construct a view from an unbound temporary group.
- `ReadGroup.array()` is read-only. Replace attempts to mutate committed read
  storage with a map or write operation.
- Caller-created Python path lists are now owned `PathList` objects. Reuse or
  explicitly release them; do not add a second manual release for the reference
  the object already owns.
- Replace float/string spellings of integer fields with real integers; this
  includes ordinals such as `5.0`, indices, handles, tokens, masks, and enum
  arguments. Use declared enum members, avoid negative population-domain masks,
  and pass attribute names as `str` or tokens as `int` explicitly.
- If the app relied on OVStage's incidental console diagnostics, install a log
  callback; the standalone runtime is silent by default.

### 7. Preserve 0.4 rendering defaults only when required

These are not compile failures. Add explicit settings only if the application
requires 0.4-equivalent images:

- Selection outlines changed from disabled to enabled by default. Set
  `selection_outline_enabled=false` when the app uses selection groups but must
  retain the old image.
- Multiple DomeLights changed from forced-single to enabled. Author
  `omni:rtx:scene:forceSingleDomeLight = true` on each relevant RenderProduct to
  retain the 0.4 single-DomeLight behavior.
- RTPT CFGPU camera jitter changed from disabled to enabled. Author
  `omni:rtx:rtpt:cfgpuCameraJitter = false` when deterministic 0.4 sampling is
  required.

If the application already authors any of these values explicitly, preserve its
authored choice; the default change requires no edit.

## Limitations

- New optional features such as SPG stateful/raygen nodes, UV projectors,
  decals, spectral rendering, Aftermath control, or DomeLight baking controls.
- Performance improvements, crash fixes, rendering correctness fixes, package
  size reductions, tests, CI, or documentation-only tickets.
- `DepthSD`: it is deprecated but not removed in 0.5. Record follow-up work if
  desired; do not block this port on replacing it.
- Auto-applied Camera and RenderProduct RTX schemas: existing explicit schema
  application remains valid and does not need removal.
- Strict validation of malformed times, config values, DLPack layouts, and null
  RenderProduct paths. Fix matches found in application code, but do not add
  compatibility workarounds for invalid 0.4 inputs.
- Any API that appeared and disappeared only during 0.5 development. Confirm
  the 0.4 and final 0.5 shipped surfaces before adding a migration step.

## Validation

- Python: import OVRTX 0.5 with no removed-symbol imports; run the narrowest
  tests that create the renderer, populate the stage, step, and consume every
  requested output on its real device.
- C/C++: cleanly rebuild and relink against the 0.5 package; run once with the
  packaged runtime layout rather than relying only on header compilation.
- Sensors: instantiate every authored sensor, confirm no version or skipped-
  output diagnostic, and validate PointCloud channel names, shapes, counts, and
  units.
- Attached mode: populate through OVStage 0.2, advance the write floor, render a
  committed ordinal, and exercise every directly consumed changed attribute.
- Behavior preservation: compare representative images/tensors with accepted
  0.4 baselines after explicitly pinning only the defaults the app depends on.

## Output Format

- List files changed, grouped by the migration areas above.
- State which audit areas did not apply and why.
- Call out authored-USD and deployment changes separately from source changes.
- Report exact build/test commands and runtime coverage.
- List any remaining deprecated-but-still-functional APIs as follow-up work,
  not as completed migration.

## Scripts

This skill has no scripts.

## Troubleshooting

- If an audit search finds no match, verify the source is really OVRTX 0.4.x;
  do not manufacture a migration edit.
- If attached mode fails during initialization or population, first confirm the
  OVRTX and OVStage packages are from the same release train and schema paths
  were registered before either OpenUSD runtime loaded.
- If a RenderVar lookup or mapping fails, verify the full authored RenderVar
  path, target device, DLPack layout, and mapping lifetime.
- If sensor output is absent or rejected, verify the applied sensor schema
  version, `omni:sensor:modelVersion`, and replacement of removed
  `GenericModelOutput` usage.
- If C/C++ works at compile time but fails at startup, cleanly rebuild and check
  the packaged runtime layout; a 0.4 binary is not compatible with the 0.5
  public result structures.

## References

- [`../reading-render-output/SKILL.md`](../reading-render-output/SKILL.md)
- [`../renderer-creation/SKILL.md`](../renderer-creation/SKILL.md)
- [`../configuring-lidar-sensors/SKILL.md`](../configuring-lidar-sensors/SKILL.md)
- [`../configuring-radar-sensors/SKILL.md`](../configuring-radar-sensors/SKILL.md)
- [`../../CHANGELOG.md`](../../CHANGELOG.md)
- [`../../../../ovstage/public/CHANGELOG.md`](../../../../ovstage/public/CHANGELOG.md)
