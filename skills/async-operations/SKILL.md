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
name: async-operations
description: >
  Asynchronous operation patterns including polling, timeouts, and non-blocking
  workflows. Use when user asks about async rendering, non-blocking operations,
  polling, timeouts, or parallel rendering.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - async
  - operations
tools:
  - Read
  - Grep
---

# Async Operations

## When to Use

Use this skill when the user asks about async rendering, non-blocking operations, polling, timeouts, or parallel rendering.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Operation type: USD load/reference, render step, reset, clone, query, attribute read/write, or result fetch.
- Desired control flow: blocking wait, non-blocking poll, finite timeout, progress reporting, or two-stage result fetching.
- Language-specific handle involved: Python `Operation`, pending fetch object, C `ovrtx_op_id_t`, or result handle.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Know whether the async operation completes directly or returns a second-phase object that must be fetched after wait.

## Instructions

1. Identify whether the caller needs blocking execution, non-blocking polling, progress reporting, or two-phase result fetching.
2. In Python, use the two-stage pattern for result-bearing operations: call the `_async` method, `wait()` for a pending fetch object, then `fetch()` the final result.
3. For non-blocking Python waits, call `wait(timeout_ns=0)` first and handle `None` as "still running"; use a finite or infinite wait only when the workflow is ready to block.
4. In C, treat every enqueue result as asynchronous: check the enqueue status, wait on `op_index`, inspect operation errors, then fetch or destroy result handles as required.
5. When changing code, run the narrow async/status docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

All ovrtx enqueue operations (`open_usd`, `add_usd_reference`, `step`, `write_attribute`, etc.) are internally asynchronous and stream-ordered. In Python, the default methods (e.g., `open_usd`, `add_usd_reference`, `step`) block until completion. The `_async` variants return `Operation` objects that support polling and custom timeouts.

In C, all enqueue calls return immediately with an `ovrtx_op_id_t` that can be polled or waited on.

## Python

### Non-blocking USD load

> **Source:** `tests/docs/python/test_support_api.py` snippet `doc-open-usd-async`
>
> The same polling pattern applies to `open_usd_async` and `add_usd_reference_async` — call `op.wait(timeout_ns=0)` to poll, or `op.wait()` to block.

### Non-blocking step with two-stage timeout

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-async`

### Infinite wait (default)

> **Source:** `examples/python/minimal/main.py` snippet `step`
>
> The synchronous `step()` is equivalent to `step_async().wait()`.

### step_async returns Operation[PendingFetch[RenderProductSetOutputs]]

In 0.3.0 the Python `RendererResult` return type was removed; `step_async()` now follows the standard two-phase `Operation` / `PendingFetch` lifecycle.

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-async`

### Query progress on long-running operations

`Operation.query_status()` returns a point-in-time `OperationStatus` (state, progress, resource counters). Safe to call repeatedly while the op is `PENDING`; it becomes unavailable after `wait()` consumes the operation.

> **Source:** `tests/docs/python/test_base.py` snippet `doc-operation-status`

## C

### Poll with zero timeout

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> The load snippet demonstrates polling with `ovrtx_timeout_t{0}`.

### Poll loop with sleep

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`

### Block indefinitely

> **Source:** `examples/c/minimal/main.cpp` snippet `step-renderer`
>
> Uses `ovrtx_timeout_infinite` to block until completion.

### Check for errors after wait

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> Check `wait_result.num_error_ops` after any `ovrtx_wait_op` call.

### Query operation progress

For long-running operations (e.g., USD loading), call `ovrtx_query_op_status(renderer, op_id, &status)` to get progress and named resource counters, then `ovrtx_release_op_status(renderer, &status)` to release the returned pointers. Counter names are operation-dependent (e.g., `"shaders"`, `"textures"`, `"materials"` during USD loading). A `total` of 0 means the total is not yet known.

> **Source:** `examples/python/status-queries/main.py` snippet `wait-operation-with-status`
>
> **Source:** `examples/c/status-queries/main.cpp` snippet `wait-operation-with-status-c`

For the full pattern, use the `status-queries` skill.

## Key Types / Functions

| Python | C |
|--------|---|
| `Operation.wait(timeout_ns=None)` | `ovrtx_wait_op(renderer, op_id, timeout, &wait_result)` |
| `Operation.wait(timeout_ns=0)` | `ovrtx_wait_op` with `timeout.time_out_ns = 0` |
| `Operation.wait()` → `PendingFetch`, then `.fetch()` | `ovrtx_wait_op` + per-op fetch call (`ovrtx_fetch_results` / `ovrtx_fetch_read_result` / `ovrtx_fetch_query_results`) |
| `Operation.query_status()` → `OperationStatus` | `ovrtx_query_op_status(renderer, op_id, &status)` + `ovrtx_release_op_status(renderer, &status)` |
| `RuntimeError` on failure | `wait_result.num_error_ops > 0` |
| Python copies status into dataclasses | `ovrtx_release_op_status(renderer, &status)` -- must call after each successful query |

C timeout constants:
- `ovrtx_timeout_t{0}` -- non-blocking poll
- `ovrtx_timeout_infinite` -- block indefinitely
- `ovrtx_timeout_t{5000000000}` -- 5 seconds in nanoseconds

C wait result fields:
- `error_op_ids` / `num_error_ops` -- operations that errored since last wait
- `lowest_pending_op_id` -- 0 if all operations complete, nonzero if still pending

## Troubleshooting

- In Python, `Operation.wait()` with no arguments blocks forever -- this is usually what you want.
- `wait(timeout_ns=0)` returns `None` on timeout, which is distinct from a successful result. For operations that return `None` on success (like `reset_stage`), use the `Operation` object's state to distinguish.
- In Python, call `Operation.query_status()` before `Operation.wait()` completes; completed operations release their wait-phase context.
- In C, `ovrtx_wait_op` waits for all operations up to and including the given `op_id`, not just that single operation.
- In C, check the `ovrtx_wait_op` return status before interpreting `wait_result` fields.
- In C, release each successful `ovrtx_query_op_status()` result with `ovrtx_release_op_status()`.
- Error strings from `ovrtx_get_last_op_error()` are valid only until the next `ovrtx_wait_op` call on the same thread.

## In Attached Mode (ovrtx 0.4+)

When ovrtx is attached to ovstage, the write side of the async model moves to
ovstage's ordinal-keyed submit/observe: ovstage enqueues return an ``op_index``
immediately, and ordinal sealing (``ovstage_advance_write_floor``) is what makes
writes observable. ovrtx observes the sealed state by passing the same ordinal
to ``ovrtx_step_with_stage(..., ordinal)`` and
``ovrtx_update_from_stage(ordinal)``. See ovstage
``skills/cpu-ahead-gpu-async/SKILL.md`` for the authoritative async model.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
