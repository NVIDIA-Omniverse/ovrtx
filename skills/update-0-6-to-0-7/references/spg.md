<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# SPG scripts and shader layouts

Use this reference with the [0.6-to-0.7 upgrade skill](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/SKILL.md).

## SPG scripts and shader layouts

Search for bare Slang array arguments, precompiled shader layouts, `order`,
`stride`, `slang.dispatch`, `type`, `next`, and previous-frame resource reads.

- Pass Slang arrays through `slang.array(...)` with the appropriate type/layout.
  For precompiled shaders without reflection, supply array/matrix byte offsets
  and strides that match the compiled shader's layout; do not guess them.
- Replace deprecated matrix layouts `{ offset, order, stride }` with
  `{ offset, strides }` and migrate `slang.dispatch()` to `slang.compute()`.
- CUDA/Slang argument wrappers and launch objects are now userdata. For those
  objects, replace table-type checks, `next()`, and table-library operations with
  field access, `pairs`, or `#` as appropriate. Ordinary Lua tables are unaffected.
- Previous-frame reads more than eight frames back fail. Audit history offsets;
  redesign algorithms needing longer history.

Read [Slang bindings](https://nvidia-omniverse.github.io/ovrtx/0.7.0/spg/ref/lua_slang.html),
[the Lua contract](https://nvidia-omniverse.github.io/ovrtx/0.7.0/spg/ref/lua_contract.html),
and [state and history](https://nvidia-omniverse.github.io/ovrtx/0.7.0/spg/do/state.html).
