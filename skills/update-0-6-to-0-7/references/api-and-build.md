<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# API types and native builds

Use this reference with the [0.6-to-0.7 upgrade skill](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/SKILL.md).

## Typed handles and token/string arguments

Search for integer handles, numeric sentinel comparisons, `int(handle)`, custom
ctypes/FFI declarations, `ovx_string_or_token_t`, and `OVX_INVALID_TOKEN`.

- Keep resource handles, operation IDs, tokens, prim paths, and path lists in
  their declared types. Do not pass one handle kind where another is expected.
- In Python, use the corresponding public handle type at explicit raw-ID input
  boundaries, and `.raw_id` when storing or passing a numeric ID outside the API.
  `int(handle)` is unsupported. Compare against the matching named invalid handle.
- In C/C++, follow the target typed declarations and supplied helpers instead of
  relying on implicit integer conversions. Update callback signatures, containers,
  and application-owned bindings as well as direct calls.
- Rename `ovx_string_or_token_t` to `ovx_token_or_string_t`. The token/string field
  order and binary layout are unchanged.
- Token ID `0` is a valid empty string; `OVX_INVALID_TOKEN` is `UINT64_MAX`.
  Remove assumptions that a zero token is invalid. Empty prim paths remain invalid.
- For token-only arguments, leave `string.ptr` null. A non-null pointer takes
  precedence over the token even when the string length is zero.
- Do not use shared Python invalid-sentinel objects as writable native output
  buffers; allocate a fresh handle instance.

Read [Python handle types](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#python-handle-types)
and the installed `ovx/types.h`, `ovx/string_types.h`, and `ovrtx/ovrtx_types.h`.

## Native ovstage dependency

Search native builds and packaging for assumptions that ovrtx supplies ovstage headers.

- Install the matching ovstage package separately. Make it discoverable through
  `CMAKE_PREFIX_PATH` or the sibling-package layout supported by the target package.
- Manual include-path configurations must add ovstage's headers explicitly.
- Preserve matching static/shared loader choices and include both packages in
  application deployment as required by the integration.

Read [C project setup](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/project-setup-c/SKILL.md).
