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
name: error-handling
description: >
  Error checking patterns for both C and Python. Use when user asks about error
  handling, checking errors, debugging ovrtx failures, or troubleshooting.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - errors
  - debugging
tools:
  - Read
  - Grep
---

# Error Handling

## When to Use

Use this skill when the user asks about error handling, checking errors, debugging ovrtx failures, or troubleshooting.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Language and failure point: Python sync call, Python async wait/fetch, C enqueue, C wait, C fetch, or C map/unmap.
- Error signal available to the caller: exception text, `ovrtx_status_t`, operation index, result handle, or `ovrtx_get_last_error()`.
- Operation being debugged and whether the caller needs recovery, logging, or propagation guidance.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Determine where errors surface for the operation before adding checks; enqueue success does not guarantee async completion success.

## Instructions

1. Identify whether the failure path is Python synchronous, Python async, C enqueue, C wait, C fetch, or C map/unmap.
2. In Python, catch `RuntimeError` around the API call or around `wait()` for async operations, depending on where the operation surfaces errors.
3. In C, check every returned `ovrtx_result_t.status` or enqueue status before using output values.
4. After C wait calls, inspect operation errors before fetching results, and call `ovrtx_get_last_error()` immediately when a status indicates failure.
5. When changing code, run the narrow example or docs test that exercises the failing operation whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

In Python, ovrtx raises `RuntimeError` with descriptive messages on failure. In C, every API call returns a status code that must be checked, and error details are retrieved with `ovrtx_get_last_error()`.

## Python

### Automatic error handling

All Python API methods raise `RuntimeError` on failure. The minimal step
example shows the synchronous call shape to wrap in user code:

> **Source:** `tests/docs/python/test_error_handling.py` snippet `doc-python-sync-runtime-error`
>
> The test demonstrates the synchronous Python error surface pattern.

### Async operation errors

Errors from async operations surface when you call `wait()`:

> **Source:** `tests/docs/python/test_error_handling.py` snippet `doc-python-async-operation-error`

### Step errors

> **Source:** `examples/python/minimal/main.py` snippet `step`
>
> Wrap in `try/except RuntimeError` to handle step failures.

## C

### Check every return value

> **Source:** `examples/c/minimal/main.cpp` snippet `create-renderer`
>
> **Source (continued):** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> Every API call returns a status code. Check with the `check-error-helper` snippet pattern.

### check_and_print_error helper function

From the minimal C example -- a template helper that checks the status, prints to `std::cerr`, and returns whether an error occurred. Works with both `ovrtx_result_t` and `ovrtx_enqueue_result_t`:

> **Source:** `examples/c/minimal/main.cpp` snippet `check-error-helper`

### Per-operation errors from wait

Asynchronous errors (e.g., file not found during USD load) are reported through `ovrtx_wait_op`:

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> Check `wait_result.num_error_ops` and iterate `wait_result.error_op_ids` after `ovrtx_wait_op`.

### Log callback (C)

Set a process-global callback to receive log messages, with severity filtering and per-channel rules:

> **Source:** `tests/docs/c/test_logging.cpp` snippet `doc-log-callback-prefix-filter-c`

Log severity levels follow carb's numeric ordering: `OVRTX_LOG_INFO` (-1), `OVRTX_LOG_WARNING` (0), `OVRTX_LOG_ERROR` (1), `OVRTX_LOG_FATAL` (2); the unexposed verbose level is -2. The callback is process-global: its lifetime is `ovrtx_initialize` to `ovrtx_shutdown`, so it observes messages emitted before the first renderer is created and after the last one is destroyed (e.g. plugin-load and asset-eviction messages). The callback may be invoked from any thread but invocations are serialized for the process. Message strings are only valid during the callback.

#### channel_filter syntax

`channel_filter` is a comma-separated list of `<channel_prefix>=<level>` entries (RUST_LOG-style). The channel prefix is matched against carb's dotted source name; longest matching prefix wins. Channels not matched by any explicit rule fall back to the `severity` parameter. Accepted level names (case-insensitive): `verbose` (alias `debug`), `info`, `warn` (alias `warning`), `error`, `fatal`. Whitespace around tokens and trailing commas are tolerated; malformed entries (missing `=`, unknown level, empty channel) cause `ovrtx_set_log_callback` to return `OVRTX_API_ERROR` with a descriptive `ovrtx_get_last_error()` string and leave the previously installed callback state unchanged.

Examples:

- `""` (or `NULL`): every channel uses `severity` as its threshold.
- `"omni.usd=error"`: `omni.usd*` is admitted at error+, every other channel uses `severity`.
- `"carb=warn,carb.tasking=verbose"`: `carb.tasking` is admitted at verbose+, other `carb.*` channels at warn+, everything else uses `severity`.

## Key Types / Functions

| Python | C |
|--------|---|
| `RuntimeError` | `result.status == OVRTX_API_ERROR` |
| exception message | `ovrtx_get_last_error()` |
| async error on `wait()` | `ovrtx_get_last_op_error(op_id)` |
| (not exposed) | `ovrtx_set_log_callback(severity, channel_filter, callback, user_data)` |
| (not exposed) | `ovrtx_flush_log(timeout)` |

C status codes:
- `OVRTX_API_SUCCESS` (0) -- success
- `OVRTX_API_ERROR` (1) -- error, call `ovrtx_get_last_error()` for details
- `OVRTX_API_TIMEOUT` (2) -- timeout reached

## Troubleshooting

- On Linux systems with no display, repeatedly creating and destroying renderers may result in a native crash with the stack trace pointing into `libEGL.so` when shared graphics resources are torn down between renderers. This can happen if `keep_system_alive` is configured to `false`, or if `ovrtx_initialize()` is not called before the multi-renderer lifecycle. In the implicit-initialization pattern (when `ovrtx_initialize()` is not called), the `keep_system_alive` config setting is effectively ignored. Avoid this by both configuring `keep_system_alive` to `true` (`RendererConfig(keep_system_alive=True)` in Python, `ovrtx_config_entry_keep_system_alive(true)` in C) and calling `ovrtx_initialize()` before creating renderers. If this is not possible, or the crash persists, a further workaround is to set the environment variable `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- Error strings from `ovrtx_get_last_error()` live in thread-local storage and are invalidated by the next API call on the same thread. Copy the string if you need to keep it.
- `ovrtx_get_last_op_error()` strings are valid only until the next `ovrtx_wait_op` call.
- In C error paths, clean up explicitly: destroy step results if alive, destroy renderer if created, and call `ovrtx_shutdown()` if `ovrtx_initialize()` was called.
- In C, some enqueue operations (like `ovrtx_open_usd_from_file`) may succeed at enqueue time but fail during async execution. Always check `wait_result.error_op_ids` after waiting.
- In Python, some errors during `__del__` cleanup are printed to stderr rather than raised (since Python does not allow exceptions in destructors).

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
