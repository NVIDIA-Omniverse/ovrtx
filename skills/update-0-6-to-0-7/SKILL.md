---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: update-0-6-to-0-7
description: >
  Upgrade an existing Python or C/C++ application from ovrtx 0.6.x to 0.7.x.
  Use when migrating typed handles and tokens, native dependencies, RenderVar
  results and SDG decoding, depth cameras, compression, SPG scripts, or sensor
  frame limits. Covers application-facing compatibility changes, not a complete
  audit of the separately versioned ovstage library.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - "0.7"
  - migration
tools:
  - Read
  - Grep
  - Edit
---

# Update ovrtx 0.6 to 0.7

## When to Use

Migrate Python, C/C++, authored USD, output decoders, and SPG scripts from
ovrtx 0.6.x to 0.7.x. Apply only changes relevant to the application; new
features need not be adopted. For older applications, follow the
[earlier upgrade skills](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-5-to-0-6/SKILL.md) first.

## Inputs

Identify the exact source and target packages, build IDs, matching ovstage
package, application source, dependency pins, generated assets, and existing
image/tensor baselines. Preserve the application's intended timing and lifecycle.

## Prerequisites

Read the [changelog](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/CHANGELOG.md) and installed target headers, Python
signatures, and schemas. Installed contracts take precedence over summaries or
stale prose. Reference links target 0.7.0; check the matching contracts for later
patches. Do not infer an ovstage version from ovrtx's version number.

## Choose the relevant references

Inventory each area as applicable, already migrated, or not used. Read the
matching reference before editing; there is no need to load unrelated sections.

| Application uses | Read | Main migration |
|---|---|---|
| Handles, tokens, native bindings, or C/C++ builds | [API and build](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/references/api-and-build.md) | Typed identities, invalid-token semantics, and separate ovstage headers |
| RenderVar results, SDG decoders, compression, or multiple RenderProducts | [Render outputs](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/references/render-outputs.md) | Per-output errors, named tensors, compression authoring, and unique view identity |
| Depth cameras, explicit camera versions, frame limits, or history resets | [Sensors](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/references/sensors.md) | Camera-authored depth parameters, signed limits, and history-reset APIs |
| SPG Lua or precompiled shaders | [SPG](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/references/spg.md) | Array/layout bindings, wrapper userdata, and the eight-frame history limit |
| Startup or deployment configuration | [Telemetry](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/references/telemetry.md) | Review the new default against the application's policy |

## Instructions

1. Search application code and generated data using each selected reference's
   audit terms. Record affected callers, assets, and bindings before changing them.
2. Apply the reference's conditional actions. Preserve unrelated behavior;
   do not globally cast handles, rename arbitrary attributes, or change policies.
3. Rebuild affected native consumers and regenerate application-owned bindings
   or assets whose layouts or types changed. Keep target headers and runtime matched.
4. Validate representative existing workflows: successful, failed, and empty
   outputs; affected sensor schedules; pause/resume; multiple products; and cleanup.
   Compare existing image/tensor baselines where rendering behavior changed.
5. If results differ, inspect the relevant reference and target contract before
   changing expected data. Report unresolved behavior rather than guessing a migration.

Runtime checks require the GPU, driver, network, and execution conditions in the
[public agent guide](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/AGENTS.md). Static checks do not establish runtime
compatibility. Rendering changes can require baseline review even without source edits.

## Output Format

State source/target versions, applicable migrations, edits made, and areas not
used. Separate static/build checks from runtime checks and baseline comparisons.
List unresolved contracts, environment blockers, and any remaining ovstage work.

## Scripts

None.

## Limitations

This is not a complete renderer-settings or independent ovstage audit.

## Troubleshooting

For migration failures, consult the relevant reference and inspect the installed
contract before changing expected behavior.

## References

- Topic references are linked in the table above.
- Consult ovstage's matching upgrade instructions for direct uses of that library.
