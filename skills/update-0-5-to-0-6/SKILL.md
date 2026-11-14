---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: update-0-5-to-0-6
description: >
  Upgrade an existing Python or C/C++ application from ovrtx 0.5.x to 0.6.x,
  including attached ovstage 0.2 to 0.3 workflows. Use when migrating logging,
  animation clocks, population and raw attribute contracts, sensor revisions
  and outputs, or SPG Lua scripts. Does not cover renderer-setting migrations.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - "0.6"
  - ovstage
  - migration
tools:
  - Read
  - Grep
  - Edit
---

# Update OVRTX 0.5 to 0.6

Port the application's source and data contracts with the minimum necessary
changes. Apply each conditional migration only where the application uses the
affected interface; do not rewrite working code or adopt unrelated features.

## When to Use

Use for Python, C/C++, authored USD, and SPG Lua applications moving from
OVRTX 0.5.x to 0.6.x, including attached OVStage 0.2.x to 0.3.x applications.
For earlier versions, apply the corresponding earlier upgrade skill first.

## Inputs

- Exact source and target package versions and locations, including build IDs.
- Application source, native bindings, authored/generated USD, SPG scripts,
  dependency pins, and deployment configuration.
- Whether the application directly consumes OVStage buffers or sensor outputs.
- Accepted image/tensor baselines and animation/seek behavior to preserve.

## Prerequisites

- Use matching OVRTX 0.6.x and OVStage 0.3.x packages for attached applications.
  Rebuild native integrations against the target headers and runtime.
- Read target headers/signatures before editing. They override draft release
  notes; confirm applicability to the application's exact 0.5 patch release.
- Runtime validation requires the GPU, driver, network, and execution conditions
  in [the public agent guide](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/AGENTS.md). Static checks do not prove runtime
  compatibility.

## Scope

This skill covers the nine source/data migrations below. Renderer settings,
render-mode selection, section planes, spectral configuration, Gaussian tone
mapping, and denoiser-setting migrations are outside its scope. Completing this
skill is not a claim that those separate settings have been audited.

## Authoritative Sources

- [OVRTX changelog](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/CHANGELOG.md) and installed headers/Python signatures.
- [OVStage changelog](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/CHANGELOG.md) and
  [population contract](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/include/ovstage/ovstage_population.h).
- The area-specific public references linked below. Links target the published
  repositories on `main`; use the matching release tag or installed distribution
  when checking a version-specific contract.

The comparison starts at the released OVRTX 0.5.0 source, not a pre-release
approval candidate. In particular, the renderer animation-clock change is new
relative to that release even if a changelog groups it under 0.5.

## Instructions

1. Inventory uses of the nine interfaces below before editing. Record each as
   applicable, already migrated, or not used.
2. Apply only the matching source, binding, or data edits. Preserve unrelated
   settings and behavior.
3. Rebuild affected native consumers and regenerate application-owned bindings
   or assets when their layouts or types changed.
4. Validate the application's existing representative workflows: callback
   concurrency, playback/seek, population/replacement, raw buffer decoding,
   sensor outputs, SPG execution, and cleanup as applicable. Ask before adding
   new tests when the application's repository requires it.
5. Report completed migrations, checks actually run, and remaining blockers.

## Audit Searches and Required Actions

### 1. C logging callbacks

Search for `ovrtx_log_severity_t`, `ovrtx_log_callback_t`, `OVRTX_LOG_INFO`,
`OVRTX_LOG_WARNING`, `OVRTX_LOG_ERROR`, `OVRTX_LOG_FATAL`, and callback registration.

- Include `<ovrtx/ovrtx_logging.h>` explicitly; shared message types come from
  `<ovx/logging_types.h>`.
- Replace the severity/callback types with `ovx_log_severity_t` and
  `ovx_log_callback_t`, and the listed severity constants with `OVX_LOG_*`.
  The new severity set also includes verbose logging.
- Replace the old callback arguments (severity, floating-point timestamp,
  message, user data) with `const ovx_log_message_t*` and user data.
- Read severity and text from that structure. It also supplies library/channel,
  Unix and elapsed timestamps in nanoseconds, source location, process/thread
  IDs, and sequence number. Update timestamp conversions accordingly.
- Make callbacks fast and thread-safe: they may run concurrently on emitting
  threads, rather than being serialized.
- Copy length-delimited strings before retaining them beyond the callback.
  Keep callback state alive until successful replacement/disable has drained
  active calls, or shutdown has fully completed.
- Do not replace/register a callback from inside itself: it can deadlock.
  Flushing from a callback is rejected; explicit flush timeouts use nanoseconds.
- Rebuild even though callback registration retains its function name: the
  callback ABI has changed.

Read [the logging API](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/include/ovrtx/ovrtx_logging.h) and
[message types](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/include/ovx/logging_types.h).

> **Source (C):** [C logging example](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/tests/docs/c/test_logging.cpp) snippet `doc-log-callback-prefix-filter-c`.

### 2. Animation clocks

Search the update loop for population time updates, step delta time, reset/seek,
video textures, MDL `state::animation_time`, and animated NuRec/Gaussian content.

- Renderer-driven animation follows accumulated step time. Updating attached
  USD population time alone does not advance it.
- Continue sampling USD population at the desired absolute time in seconds,
  and supply the corresponding elapsed time when stepping OVRTX.
- A changed USD time with zero step delta leaves renderer-driven animation
  frozen. Preserve that behavior only when the application intends to pause it.
- For seeking, reset the renderer with the desired time where appropriate.
  Reset also discards temporal history; do not present it as a history-preserving
  seek operation.

Read [attached timing and update ordering](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/docs/core/ovstage_integration.rst).

### 3. OVStage Python API and ownership

Search for `time_code=`, `PathDictionary`, reused path lists/selections, `wait()`
return assumptions, clone results, configuration dictionaries, version parsing,
and attachment/query teardown.

| Old usage or assumption | Required action |
|---|---|
| Population keyword `time_code` | Rename to `time`, including descriptor/async forms; values are seconds. |
| Implicit `PathDictionary()` or `None` stage | Pass the owning stage explicitly. |
| Path lists shared between stages | Recreate them for each owner; release them before destroying that owner. |
| Data-plane `wait()` returns `None` | It returns the operation/handle itself; adjust return-value assertions. Population waits retain their own payload contract. |
| A timed-out wait consumes the operation | Keep the pending operation and its inputs alive; retry or complete cleanup. |
| `Stage.clone()` returns `None` | It returns a clone result; update assertions or consume that result. |
| Mutating a returned config dictionary configures the object | Config access returns a fresh snapshot/copy, not mutable live configuration. |
| Unknown configuration keys are ignored | Remove obsolete or misspelled keys. |
| Every package version has exactly three numeric components | Allow distribution/build identity; `Renderer.version` remains the semantic tuple. |

- Destroying the caller's stage handle releases that reference; an attached
  renderer retains its own reference. Unrelated stages/path lists do not keep
  the owner alive.
- Attachment/detachment waits for actual completion. A timeout does not cancel
  the operation; a failed teardown can require cleanup-only retry.
- A failed query refresh can invalidate prepared query handles. Recreate them
  rather than assuming earlier handles remain usable.
- `DEFAULT_TIME` is a NaN sentinel: use the supplied predicate, not equality.
- Creating paths from zero components yields the absolute root `/`.

Read [OVStage changes](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/CHANGELOG.md) and
[path ownership](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/docs/scene/path_dictionary.rst).

### 4. Population merges instead of implicit scene replacement

Search for repeated USD opens into one stage, scene replacement, time resampling,
`reset_usd`, query predicates, and direct writes to derived transform fields.

- Opening into an already populated stage merges: selected attributes are
  overwritten, but unrelated/absent content is not removed automatically.
- If open previously meant replace, either create and attach a fresh stage or
  explicitly clear the intended content before opening the replacement.
- To clear USD-populated source content, finish `reset_usd`, then finish
  `apply_usd_changes` to drain it, and open the replacement at a later ordinal.
  Reset alone changes the USD source, not the populated stage.
- To clear everything, including application-created content, complete an
  unfiltered prim query and whole-prim deletion, release the query resources,
  then populate at a later ordinal.
- Reapplying the same time rewrites time-sampled attributes; do not assume a
  no-op. Give potentially overlapping time updates and USD-change application
  distinct ordinals.
- Repopulation preserves USD source/layer references but overwrites selected
  runtime values and does not delete omitted content.
- USD-authored derived transform fields no longer override computed transforms.
- Typeless prims no longer carry `__ovstage_population_untyped__`; test absence
  of a prim type instead.
- Generic population can contain an empty `usd-schemas` set. Use membership
  (`CONTAINS`), not presence (`HAS`), to test for an applied API schema.
- Multiple-apply schemas include the bare schema name alongside the
  instance-qualified names; allow for both in consumers.
- Non-rendering queries no longer expose two internal bookkeeping prims; remove
  assumptions about their presence or contribution to prim counts.

Read [population behavior](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/include/ovstage/ovstage_population.h).

### 5. OVStage raw attribute representations

Search raw reads/writes for universal token-ID decoding, fixed string dtypes,
schema-mismatched numeric values, `focusTint`, DLPack stride assumptions, and
connection broadcasting.

- Decode using dtype, array shape, and semantic metadata. Selected scalar
  strings now use UTF-8 byte arrays with STRING semantic, rather than token IDs:
  rendering settings/product/variable properties covered by the rendering
  mapping; relevant sensor-model/camera configuration strings; scalar string
  primvars; and selected Material/NodeGraph/Shader properties including shader
  source code and material configuration.
- Other strings/string arrays may remain interned IDs. Legacy semantic-label
  type/data fields remain token IDs. Consult the property-specific population
  mapping instead of globally replacing token decoding.
- Schema-mismatched numeric values convert to the declared type where
  compatible. Float-to-integer conversion truncates toward zero and checks
  range; NaN/infinity cannot convert to integers. Floating-point narrowing can
  round, overflow to infinity, or underflow to zero.
- Conversion preserves scalar/array/vector shape and requires every component
  to convert. Unsupported mismatches retain authored types and can fail with a
  type conflict; custom attributes keep their authored types.
- Export uses converted populated values, not original authored representations.
- `focusTint` has VECTOR semantic for the supported shaped light types, rather
  than universally COLOR. Use `ReadGroup.semantic` to interpret values.
- DLPack outputs provide explicit strides; do not depend on a null strides
  pointer to recognize a valid layout.
- CPU connection values are path/attribute-token pairs. Supply exactly one pair
  per target on writes; broadcasting is unsupported. GPU connection access is
  still unsupported.

Read [the population type mapping](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/include/ovstage/ovstage_population.h)
and [population guide](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/docs/scene/population.rst).

### 6. Sensor revision selectors and CFA type

Search authored/generated USD and sensor setup for `omni:sensor:modelVersion`,
schema revisions, deprecation allowances, and
`omni:sensor:core:colorFilterArrayMaximalValue`.

- The affected lidar, radar, acoustic, and IDS implementations use schema `1`,
  model `0`. Replace an explicit old model `"1"` with the target-supported `"0"`
  or deliberately choose `"latest"` after checking the installed model.
- `"latest"` was already supported/default in 0.5; do not treat it as a new
  feature. Do not switch the model revision of an instantiated sensor dynamically.
- Revisit exact-version deprecation allowances when upgrading. Do not blindly
  extend an escape hatch instead of migrating the sensor.
- CFA maximal value changes from integer to float with the same numeric default,
  `16777215.0`. Update custom bindings/raw writers and author it as float.
  Fractional scales are now representable.

Read [sensor configuration](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/docs/sensors/common/sensor_configuration.rst).

### 7. Lidar channel IDs

Search `ChannelId` consumers for zero-based indexing, channel-ID offsets, dense
array indexing, and recorded expected point clouds.

- Output preserves authored unsigned 32-bit channel IDs. Authored IDs `1..N`
  previously could emerge as `0..N-1`; do not retain that implicit remapping.
- Use an authored-ID-to-channel lookup instead of indexing by the output ID.
- Update downstream decoders and reference data. Do not apply unconditional
  `+1` or `-1` conversion to arbitrary IDs.
- Sparse IDs, zero, and large unsigned IDs are valid subject to the model's
  channel-count constraints.

Read [lidar point-cloud interpretation](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/interpreting-lidar-pointclouds/SKILL.md).

### 8. Acoustic SignalWays output

Search acoustic RenderVars, granular byte-blob AOV decoders, result lookups,
array reshaping, and validity masks.

- Replace the previous granular outputs with RenderVar source `SignalWays`,
  and use full RenderVar paths for result lookup.
- Decode the composite tensors using their declared types:

| Tensor | Type |
|---|---|
| `TransmitterIds`, `ReceiverIds`, `ChannelIds` | float32 |
| `Amplitudes` | float32 |
| `TimeOffsetNs` | int32 |
| `Flags` | uint8 |

- Read runtime parameters for frame/cycle, signal-way count, samples per way,
  total elements, center frequency, and sample duration.
- Amplitude storage has `numSignalWays * numSamplesPerSignalWay` elements.
- For per-way metadata tensors, only the first `numSignalWays` entries are
  meaningful; remaining entries are zero-filled.
- Interpret the `0x40` validity flag per signal way, not per amplitude sample.

### 9. SPG Lua product access and sandbox

Search SPG scripts for the old product/camera accesses, protected calls, pattern
functions, cached stage values, and ambiguous RenderVar source names.

| Old usage or assumption | Required action |
|---|---|
| `rtx.product.prim_path` | Use `rtx.product.path`. |
| `rtx.product.resolution.width` / `.height` | Use authored dimensions `resolution[1]` / `[2]`. |
| Resolution is the actual tile size | Use `rtx.product.tiling.width` / `.height`, or actual resource descriptors. |
| `rtx.product.cameras[i]` is a string | It is a prim table; read `.path`. |
| `pcall` / `xpcall` are available | Remove reliance on protected calls; they are removed. |
| Lua pattern functions are available | Replace `string.find`, `match`, `gmatch`, and `gsub`; they are removed. |

- Stage/prim tables expose current-frame scene data, transforms, cameras, and
  RenderVars. Missing prim lookup returns `nil`; unsupported attribute access
  errors. Retained values are snapshots, not automatically refreshed references.
- Byte-array inputs are supported.
- Respect fixed limits: 10 MB memory, one million Lua instructions per load/call,
  and 64 KB log output. Native queries and array work consume budget too.
- A limit failure stops the node until setup changes or the graph is reopened.
  Syntax errors are isolated to the affected node.
- Disambiguate repeated RenderVar source names by channels/full-path identity.
- Do not remove the legacy third launch argument merely because it disappeared
  from documentation: the implementation still passes it. Verify the exact
  target implementation before changing a consumer that relies on it.

Read [Lua RTX access](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/docs/spg/ref/lua_rtx.rst) and
[the execution contract](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/docs/spg/ref/lua_contract.rst).

## Output Format

- State exact source/target versions and which of the nine migrations applied.
- Summarize source, authored-data, and binding changes separately where useful.
- Report checks actually run, runtime prerequisites/blockers, and unresolved
  compatibility differences. Do not claim GPU validation from static checks.
- State that renderer-setting migration is outside this skill's coverage.

## Scripts

This skill has no scripts.

## Limitations

- Covers source/data contracts, not renderer-setting migration or the complete
  feature/fix inventory for 0.6.
- Target patch releases can differ; installed public contracts take precedence.
- Callback ABI and sensor/SPG runtime behavior require application validation;
  documentation checks alone cannot establish their correctness.

## Troubleshooting

- No audit matches: verify the source version and used interfaces; do not invent
  edits for a conditional migration the application does not need.
- Frozen animation after USD time changes: check renderer step delta/reset time.
- Old prims after opening a replacement: explicitly clear/drain or use a fresh stage.
- Broken raw strings or sensor decoding: inspect target dtype/semantic/channel
  identity before changing numeric values or applying offsets.
- SPG size errors: distinguish authored full resolution from actual tile/resource
  dimensions, and check execution limits and node failure state.

## References

- [Earlier 0.4 to 0.5 migration](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-4-to-0-5/SKILL.md).
- [OVRTX changelog](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/CHANGELOG.md).
- [OVStage changelog](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/CHANGELOG.md).
- [Reading render output](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/reading-render-output/SKILL.md).
- [SPG workflow](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/spg/SKILL.md).
