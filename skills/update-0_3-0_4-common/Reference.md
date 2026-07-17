# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# ovrtx 0.3 to 0.4 Common Upgrade Reference

Read this reference before applying a language-specific 0.3 to 0.4 migration skill. It captures behavior changes that apply to both C/C++ and Python applications when scene ownership moves from ovrtx compatibility APIs to an attached ovstage instance.

## Ownership Model

In ovrtx 0.4 attached mode, ovstage owns scene data and ovrtx owns rendering.

| Responsibility | Owner after migration |
|---|---|
| Root USD open and inline population | ovstage population APIs |
| Add/remove/reset USD source content | ovstage population plus apply changes |
| USD time evaluation | ovstage population USD-time update |
| Clone runtime prims | ovstage clone APIs |
| Stage queries and reusable path lists | ovstage query and path dictionary APIs |
| Attribute read/write | ovstage read/write APIs |
| Persistent attribute binding | Reusable ovstage query handle |
| Attribute map/unmap | ovstage map iterator and unmap APIs |
| Rendering and sensor outputs | ovrtx renderer attached to a committed ovstage ordinal |

Do not move renderer-side behavior to ovstage just because the renderer is attached. Picking, selection outline, render products, render-var outputs, sensor outputs, renderer status/progress, and logging remain ovrtx responsibilities.

## Attachment Mode

Migrated user applications should use the default attached rendering behavior unless current product documentation explicitly calls for a different configuration.

## Path Dictionary Ownership

Use the dictionary owned by the API that produced or consumes the IDs.

- IDs produced by ovstage queries, path lists, or writes belong to the ovstage path dictionary.
- IDs produced by ovrtx outputs or renderer-side APIs belong to the ovrtx path dictionary.
- Do not decode ovrtx path IDs with the ovstage dictionary, or ovstage path IDs with the ovrtx dictionary, even when the renderer is attached to the stage.

## Transform Semantics

Do not assume ovrtx 0.3 transform convenience helpers map one-to-one into ovstage writes. Ovstage uses canonical scene attributes and tensor metadata, and older ovrtx helpers may have written packed layouts or renderer-specific semantics.

When migrating transform writes:

- Re-check the current ovstage transform documentation and examples for the language being edited.
- Convert old helper-specific layouts to the ovstage-supported transform representation.
- Preserve reset-xform-stack behavior explicitly when the 0.3 application depended on it.
- Treat transform changes as behavior-sensitive, not mechanical symbol replacement.

## Ordinals And Write Floor

Attached rendering consumes committed ovstage state at an application-owned ordinal. The application must publish completed population or data-plane mutations by advancing the ovstage write floor before asking ovrtx to render that ordinal.

Rules of thumb:

- Keep application ordinals monotonically increasing for frames that commit new scene state.
- Do not render an ordinal above the current ovstage write floor.
- Wait for population/write-floor work to complete before rendering the committed ordinal.
- For frame loops that mutate the stage every frame, fence the previous render step before publishing writes for the next ordinal if the language/API exposes asynchronous render operations.

## Async Boundaries

Ovstage population, ovstage data-plane work, and ovrtx rendering are separate operation domains. Do not use renderer progress/status APIs to wait for ovstage population or data-plane work, and do not use ovstage waits for renderer work.

Match the wait/status mechanism to the API that enqueued the work:

- USD population: wait with the ovstage population wait/status API for the language.
- Data-plane writes, reads, queries, maps, and write-floor advances: wait with the ovstage data-plane wait/status API for the language.
- Rendering, render results, renderer status, and renderer progress: wait with the ovrtx renderer wait/status API for the language.

## Camera Exposure Defaults

Camera exposure can change after migration. In ovrtx 0.3 standalone mode, cameras without authored exposure attributes could pick up RTX render-setting fallbacks. With ovrtx 0.4 plus ovstage, unauthored exposure attributes may resolve from OpenUSD camera defaults instead.

If image brightness changes after migration, check whether the source scene authored the expected exposure attributes. Author exposure explicitly on the relevant camera prims when the application depends on specific exposure behavior.

## Deprecated Compatibility Calls

Deprecated renderer-owned scene APIs should be replaced in production application code. Keep them only when intentionally testing standalone compatibility or deprecation behavior, and document why each remaining call is intentional.

## Related Topic Skills

- [`../picking-selection/SKILL.md`](../picking-selection/SKILL.md) for renderer-side picking and selection-outline APIs.
- [`../writing-attributes/SKILL.md`](../writing-attributes/SKILL.md) for historical ovrtx attribute-write context.
- [`../application-flow/SKILL.md`](../application-flow/SKILL.md) for ovrtx renderer lifecycle and render loop context.
- [`../../docs/core/ovstage_integration.rst`](../../docs/core/ovstage_integration.rst) for attachment modes, ordinals, and renderer update ordering.
