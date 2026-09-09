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
name: render-product-device-pinning
description: >
  Restricting RenderProducts to specific CUDA-visible device indices with the USD
  deviceIds attribute. Use when a scene, test, or example must constrain a
  RenderProduct to CUDA-visible GPU 0 or another explicit set of CUDA-visible GPUs,
  especially for multi-GPU CI or viewport picking.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - gpu
tools:
  - Read
  - Grep
---

# RenderProduct Device Selection

## When to Use

Use this skill when a scene, test, or example must constrain a RenderProduct to CUDA-visible GPU 0 or another explicit set of CUDA-visible GPUs, especially for multi-GPU CI or viewport picking.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- RenderProduct prim path or scene file that needs a `deviceIds` restriction.
- CUDA-visible device index allow-list, usually `[0]` for picking or deterministic multi-GPU CI.
- Whether the pinning is authored in static USDA, inline USD, or an existing example/test scene.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm device indices are CUDA-visible indices after `CUDA_VISIBLE_DEVICES` filtering, not physical GPU IDs.
- Pin the RenderProduct only; Camera and RenderVar prims do not own `deviceIds`.

## Instructions

1. Identify the RenderProduct path and the CUDA-visible device indices it should be allowed to use.
2. Author or update the RenderProduct `deviceIds` attribute in USD; do not pin Camera or RenderVar prims.
3. Interpret device IDs after `CUDA_VISIBLE_DEVICES` remapping, not as physical PCI bus or global GPU IDs.
4. For picking workflows, pin the relevant RenderProduct to CUDA-visible GPU 0 until the picking limitation is removed.
5. When changing code, run the picking or render-product docs test that owns the GPU-pinning snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- For picking, pin RenderProducts to CUDA-visible GPU 0 until the current picking limitation is removed.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

ovrtx can select active CUDA devices at renderer creation and can also restrict
an individual RenderProduct to a specific device list. Author
`uint[] deviceIds` on the RenderProduct prim before the stage is loaded.

`deviceIds` is an allow-list of indices into the CUDA-visible device set, after
`CUDA_VISIBLE_DEVICES` filtering and remapping. ovrtx is free to choose any
CUDA-visible GPU from the list. A one-element list such as `[0]` restricts the
RenderProduct to CUDA-visible GPU 0.

Use this when a workflow is device-sensitive, needs to constrain eligible GPUs,
or must run on CUDA-visible GPU 0. In the current ovrtx version, viewport
picking only works for RenderProducts running on CUDA-visible GPU 0, so picking
tests and examples should restrict their picking RenderProduct to
`deviceIds = [0]`.

## USDA

### Restrict a RenderProduct to CUDA-visible GPU 0

> **Source:** `tests/docs/data/ovrtx-test-picking-selection.usda` snippet `doc-pin-render-product-to-gpu-0-usda`

## Workflow

1. Choose the CUDA-visible device indices that may render the product.
2. Author `uint[] deviceIds` directly on the RenderProduct prim in USD.
3. If using renderer-level `active_cuda_gpus`, ensure the RenderProduct allow-list is compatible with that active device set.
4. Load the scene normally from Python or C.
5. Step the constrained RenderProduct path as usual.

For picking, use CUDA-visible GPU 0 until the current picking limitation is
removed.

## Key Attribute

| Attribute | Type | Use |
|-----------|------|-----|
| `deviceIds` | `uint[]` | Allow-list of indices into `CUDA_VISIBLE_DEVICES` that may render this RenderProduct. ovrtx may choose any listed CUDA-visible GPU. Use `[0]` to restrict picking RenderProducts to CUDA-visible GPU 0. |

## Troubleshooting

- `deviceIds` is authored on the RenderProduct prim, not on the renderer config
  object, camera, or RenderVar.
- `deviceIds` indexes CUDA-visible devices, not non-CUDA devices, Vulkan device
  indices, display adapters, or physical GPU ids masked out by
  `CUDA_VISIBLE_DEVICES`.
- `deviceIds` is an allow-list, not a load-balancing or exact-placement policy.
  Exact device selection requires a singleton list such as `[0]`; `[0, 1]`
  permits ovrtx to choose either listed CUDA-visible GPU.
- Renderer-level CUDA selection and per-RenderProduct `deviceIds` must agree.
  For picking, leave `active_cuda_gpus` unset or ensure it includes
  CUDA-visible index `0`.
- Author the attribute before loading the scene. Do not rely on runtime mutation
  for tests that need deterministic device assignment during renderer setup.
- Picking currently requires the picked RenderProduct to run on CUDA-visible
  GPU 0. In multi-GPU CI, omit the CUDA-visible GPU 0 restriction only if the
  test does not depend on pick results.

## Related Skills

- `picking-selection` for viewport picking, marquee selection, and selection
  outline drawing.
- `renderer-creation` for renderer-level CUDA device selection.
- `cuda-interop` for mapping a selected CUDA-visible ordinal to the exact Vulkan
  physical device, including sibling MIG instances.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
