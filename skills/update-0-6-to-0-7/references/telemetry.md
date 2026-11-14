<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# Startup telemetry

Use this reference with the [0.6-to-0.7 upgrade skill](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/SKILL.md).

## Startup telemetry

Check application startup and deployment policy. Anonymous library-startup
telemetry is enabled by default, at most once per process for ovrtx. If the
application needs to opt out, do so before initialization with
`ovrtx_library_telemetry_opt_out()` / `ovrtx.library_telemetry_opt_out()`, or set
`NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1` before process startup.
Do not silently change the application's telemetry policy as part of migration.

Read [telemetry contents and controls](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/TELEMETRY.md).
