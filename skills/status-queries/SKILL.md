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
name: status-queries
description: >
  Querying progress for asynchronous ovrtx operations. Use when user asks how to
  monitor long-running operations, show loading progress, inspect OperationStatus
  counters, use Operation.query_status(), or call
  ovrtx_query_op_status()/ovrtx_release_op_status().
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - status
  - operations
tools:
  - Read
  - Grep
---

# Status Queries

## When to Use

Use this skill when the user asks how to monitor long-running operations, show loading progress, inspect OperationStatus counters, use Operation.query_status(), or call ovrtx_query_op_status()/ovrtx_release_op_status().

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Operation whose progress should be queried: Python `Operation` or C operation index.
- Status fields the caller needs, such as progress, counters, labels, pending/running state, or log output.
- Poll interval, timeout behavior, and whether the final result still needs `wait()`/`fetch()`.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `async-operations` for the broader wait/fetch lifecycle; this skill covers progress snapshots while the operation is pending.

## Instructions

1. Identify the async operation whose progress should be displayed or logged.
2. Poll status only while the operation is pending; treat a completed wait result as the authority for success or failure.
3. In Python, use `Operation.query_status()` for progress fields and keep the final `wait()`/`fetch()` lifecycle intact.
4. In C, use `ovrtx_query_op_status()` with the operation index and release the returned status object after reading it.
5. When changing code, run the status-query example for the operation type whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Status queries take a point-in-time snapshot of an async operation. Use them for
long-running work such as USD loading, shader/material preparation, stage
queries, attribute writes, or render steps when an application needs progress
feedback instead of only blocking on completion.

Status queries complement waits:

1. Enqueue an operation and keep its operation object or `op_index`.
2. Query status before or during polling.
3. Wait until the operation completes.
4. Fetch any second-phase results if the operation has them.

Progress is operation-dependent. `progress < 0.0` means indeterminate, and a
counter `total` of `0` means the total is not currently known.

## Python

Python async methods return `Operation` objects. Call `Operation.query_status()`
while the operation is still active. After `Operation.wait()` completes, the
operation releases its wait-phase context and `query_status()` is no longer
available for that `Operation`.

### Format an `OperationStatus`

> **Source:** `examples/python/status-queries/main.py` snippet `format-operation-status`

### Poll with status

> **Source:** `examples/python/status-queries/main.py` snippet `wait-operation-with-status`

### Load USD with status

> **Source:** `examples/python/status-queries/main.py` snippet `load-usd-with-status`

### Shader-cache warm-up with status

> **Source:** `examples/python/status-queries/main.py` snippet `compile-shader-cache-with-status`

### Step with status

> **Source:** `examples/python/status-queries/main.py` snippet `step-with-status`

## C

C enqueue calls return `ovrtx_enqueue_result_t`. Check `.status` first, then use
`.op_index` with `ovrtx_query_op_status()` and `ovrtx_wait_op()`.

Every successful `ovrtx_query_op_status()` call must be paired with
`ovrtx_release_op_status()`. Strings and counters inside `ovrtx_op_status_t`
are invalid after release, so copy anything that must outlive the query.

### Format an `ovrtx_op_status_t`

> **Source:** `examples/c/status-queries/main.cpp` snippet `format-operation-status-c`

### Poll with status

> **Source:** `examples/c/status-queries/main.cpp` snippet `wait-operation-with-status-c`

### Shader-cache warm-up with status

> **Source:** `examples/c/status-queries/main.cpp` snippet `compile-shader-cache-with-status-c`

### Step with status

> **Source:** `examples/c/status-queries/main.cpp` snippet `step-with-status-c`

## Key Types / Functions

| Python | C |
|--------|---|
| `Operation.query_status()` | `ovrtx_query_op_status(renderer, op_id, &status)` |
| `OperationStatus.state` | `ovrtx_op_status_t::state` |
| `OperationStatus.progress` | `ovrtx_op_status_t::progress` |
| `OperationStatus.counters` | `ovrtx_op_status_t::counters` / `counter_count` |
| `OperationCounter.name/current/total` | `ovrtx_op_counter_t::name/current/total` |
| automatic release after copying | `ovrtx_release_op_status(renderer, &status)` |
| `Operation.wait(timeout_ns=...)` | `ovrtx_wait_op(renderer, op_id, timeout, &wait_result)` |

## Troubleshooting

- Query status before `Operation.wait()` completes in Python. Once `wait()`
  returns a final result, `query_status()` raises because the operation context
  has been released.
- In C, call `ovrtx_release_op_status()` once for each successful
  `ovrtx_query_op_status()` call.
- Status query snapshots are not completion barriers. Continue to call
  `wait()` / `ovrtx_wait_op()` before using results from the operation.
- `ovrtx_wait_op()` waits for all queued operations up to and including the
  requested `op_id`, so status for one operation may reflect progress while
  earlier operations are also draining.
- Counters are operation-dependent. Do not hard-code a fixed set of counter
  names unless the application owns the operation type and runtime version.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
