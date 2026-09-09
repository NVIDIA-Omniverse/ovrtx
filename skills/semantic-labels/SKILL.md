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
name: semantic-labels
description: >
  Assigning USD SemanticsAPI class and label metadata for semantic segmentation and
  ground-truth annotation outputs. Use when user asks to label objects, assign semantic
  class/label metadata, configure semantic segmentation labels, or author SemanticsAPI
  overrides.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - semantics
  - labels
tools:
  - Read
  - Grep
---

# Semantic Labels

## When to Use

Use this skill when the user asks to label objects, assign semantic class/label metadata, configure semantic segmentation labels, or author SemanticsAPI overrides.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Prims to label, desired semantic class and label values, and whether labels should be authored directly or as override layers.
- Requested ground-truth outputs such as `SemanticSegmentation` or `SemanticIdMap` when the workflow includes rendering.
- Existing composition context: source asset path, inline USDA, sublayer, or runtime-loaded stage.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `camera-outputs-rt2` when the request is about which segmentation outputs to add to a RenderProduct.
- Use `reading-render-output` when the request is about mapping the segmentation image or ID map after rendering.

## Instructions

1. Identify the prims to label, class/label values, and whether the label should be authored directly or as a composed override.
2. Read the matching USD or Python source snippet before writing semantic metadata.
3. Preserve USD `SemanticsAPI` instance names, inheritance behavior, and any source-layer composition pattern.
4. Keep label authoring, RenderProduct output selection, and output readback separate unless the user asks for the full segmentation workflow.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Use USD `SemanticsAPI` metadata to assign semantic class and label values to scene prims that should appear in semantic segmentation or ground-truth annotation outputs. `SemanticsAPI` is a multi-apply schema: apply the `class` and `label` instances to an ancestor prim, and child prims inherit those semantics unless they author more specific semantics.

For runtime-composed scenes, keep the source asset untouched. Build one inline root layer that sublayers the source scene, then author `over` prims for the objects you want to label.

## USDA

### Label existing composed prims

> **Source:** `tests/docs/usd/data/semantic_label_overrides.usda` snippet `doc-semantic-label-overrides`
>
> **Source:** `tests/docs/data/ovrtx-test-base-semantic-labels.usda` snippet `doc-test-base-semantic-class-layer`

## Python

Use the same inline-root sublayer pattern as the loading skill: build the USDA string with `subLayers`, add `SemanticsAPI` `over` prims for the labeled objects, add `SemanticSegmentation` and `SemanticIdMap` outputs to a RenderProduct, then pass that string to `renderer.open_usd_from_string()`.

> **Source:** `tests/docs/python/test_semantic_labels.py` snippet `doc-semantic-class-overrides-python`

### Interpret rendered semantic outputs

`SemanticIdMap` maps renderer semantic IDs to semantic strings such as `class: logo;`. `SemanticSegmentation` is an image whose pixel values are those renderer semantic IDs.

> **Source:** `tests/docs/python/test_semantic_labels.py` snippet `doc-interpret-semantic-segmentation-python`

## C

### Label existing composed prims

> **Source:** `tests/docs/c/test_semantic_labels.cpp` snippet `doc-semantic-class-overrides-c`

### Interpret rendered semantic outputs

> **Source:** `tests/docs/c/test_semantic_labels.cpp` snippet `doc-interpret-semantic-segmentation-c`

## Key USD Fields

| Field | Purpose |
|---|---|
| `prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]` | Applies the `label` and `class` SemanticsAPI instances to a prim. |
| `semantic:class:params:semanticType` | Set to `class`. |
| `semantic:class:params:semanticData` | The class value, such as `robot`, `vehicle`, or `person`. |
| `semantic:label:params:semanticType` | Set to `label`. |
| `semantic:label:params:semanticData` | The object-specific label value, such as the asset or instance name. |

## Troubleshooting

- Label the object root, not the RenderProduct or RenderVar. Semantics are scene metadata consumed by annotation outputs.
- Use `over` prims when labeling objects from a sublayered source scene. This avoids modifying the original asset.
- Keep semantic label attributes constant. Sensor RTX semantic label attributes are not time-sampled.
- Apply labels at the right granularity. A top-level asset label is inherited by children; part-level labels should be added only when you need finer segmentation classes.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
