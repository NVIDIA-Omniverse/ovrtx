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
name: string-handling
description: >
  Working with ovx_string_t in C and C++. Use when user asks about printing, comparing,
  or converting ovx strings.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - c
  - strings
tools:
  - Read
  - Grep
---

# String Handling

## When to Use

Use this skill when the user asks about printing, comparing, or converting ovx strings.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: C, C++, or Python interop with C strings.
- Source of the `ovx_string_t`: error text, returned path, dictionary lookup, status message, or user-provided string wrapper.
- Required operation: print, compare, convert to `std::string_view`, copy to owning storage, or preserve lifetime.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Know whether the string is API-owned borrowed storage or caller-owned storage before recommending a borrowed view or copy.

## Instructions

1. Identify whether the task is printing, comparing, converting, or preserving an `ovx_string_t`.
2. Use both `ptr` and `length`; do not assume the string can be handled safely by APIs that only look for a null terminator.
3. In C, print with a precision-limited string format and compare by checking `length` before using `strncmp`.
4. In C++, prefer `std::string_view` when the caller only needs borrowed access, and copy immediately if the value must outlive the API-owned storage.
5. When changing code, run the C example or helper test that owns the referenced string-handling pattern whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

All strings returned by the ovrtx API use `ovx_string_t` — a `(ptr, length)` pair. The strings are null-terminated, but prefer using the `length` field over relying on the null terminator.

## C

Print with the `%.*s` precision pattern so the explicit length controls how many
characters are read from `ptr`.

Compare by checking `length` first, then using `strncmp` for the exact byte count.

## C++

Wrap `ptr` and `length` in `std::string_view` for zero-copy access to the
standard string API.

The error-handling helper in the minimal C example demonstrates this pattern:

> **Source:** `examples/c/minimal/main.cpp` snippet `check-error-helper`

## Key Types / Functions

| Type | Header |
|------|--------|
| `ovx_string_t` | `include/ovx/types.h` |
| `literal_to_ovx_string(str)` | `include/ovx/types.h` — creates `ovx_string_t` from a string literal |
| `is_ovx_string_empty(str)` | `include/ovx/types.h` — null/empty check |

## Troubleshooting

- Do not pass `ovx_string_t::ptr` directly to functions that expect a specific length (e.g. `strcmp`) without also checking `length`. Use `strncmp` or `std::string_view` instead.
- Error strings from `ovrtx_get_last_error()` are in thread-local storage and are invalidated by the next API call on the same thread. Copy or consume them immediately.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
