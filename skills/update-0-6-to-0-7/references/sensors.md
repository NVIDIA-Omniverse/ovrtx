<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# Depth cameras and sensor scheduling

Use this reference with the [0.6-to-0.7 upgrade skill](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/SKILL.md).

## Depth-camera authoring and camera versions

Search USD generators and assets for the old depth RenderProduct API,
`omni:rtx:post:depthSensor:*`, and explicit camera model-version requests.

- Apply `OmniSensorGenericDepthSensorSingleViewAPI` to the `Camera` and author
  `omni:sensor:depthSensor:*` parameters there. Remove the old depth API and
  depth-specific parameters from the RenderProduct.
- Keep the RenderProduct's camera relationship and required input/output
  RenderVars. Moving parameters does not replace output configuration.
- Camera Core and the single-view depth model use schema/model selection.
  In 0.7.0 their supported pair is schema `1`, model `0`. Inspect the installed
  schema and versioning reference before choosing explicit revisions.
- An unsupported version request produces no output for that sensor. Do not
  assume the renderer silently substitutes a supported version.
- Versions are fixed once accepted. To change them, recreate the RenderProduct
  with the intended request instead of editing a live version selector.

Read [depth setup](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/visual/depth_camera/howto/set_up_depth_product.html)
and [camera versioning](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/versioning.html).

## Sensor frame limits and history reset

Search authored and generated `omni:sensor:frameLimit` attributes, raw attribute
writers, pause/resume logic, and `omni:rtx:viewTile:renderHistoryReset:*`.

- The new `frameLimit` type is `int`: `-1` means unlimited and `0` pauses output.
  When migrating legacy `uint` attributes, convert unlimited `0` to signed `-1`;
  preserve positive limits only if they fit `int32`. Retain larger legacy unsigned
  limits until an explicit scheduling decision is made; do not cast them to signed values.
- Legacy `uint` values retain their old interpretation with a deprecation warning.
  Do not change only the type of an old zero value: that changes unlimited to paused.
- The limit applies to scheduled frame numbers, not a fresh quota on each resume.
  Choose a new limit that allows the current scheduled frame to be produced.
- Clear history before resuming if objects moved while paused. Use
  `ovrtx_clear_history()` or Python `Renderer.clear_history()` /
  `clear_history_async()` when history should reset without resetting simulation time.
- Replace deprecated per-tile history-reset attributes with the clear-history API's tile list.

Read [clear-history semantics](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#ovrtx.Renderer.clear_history).
