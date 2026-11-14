.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C API Reference
===============

The C API provides low-level access to the ovrtx rendering library.

For lifecycle, error-handling, status-query, logging, and ``ovx_string_t``
usage patterns, start with :doc:`practical_patterns`.

.. contents:: Contents
   :local:
   :depth: 2

Overview
--------

Functions returning ``ovrtx_result_t`` report success or failure through a status code:

- **OVRTX_API_SUCCESS**: The operation completed successfully
- **OVRTX_API_ERROR**: The operation failed (use :c:func:`ovrtx_get_last_error` for details)
- **OVRTX_API_TIMEOUT**: The operation timed out

Many operations are stream-ordered and execute asynchronously. They return handles that can be used in subsequent operations, but the actual effects may not be produced until stream execution completes.
For these asynchronous operations, enqueue may still succeed while execution fails later. Check
:c:func:`ovrtx_wait_op` and inspect ``ovrtx_op_wait_result_t.error_op_ids``, then retrieve per-op
details with :c:func:`ovrtx_get_last_op_error`.

Functions
---------

Version
^^^^^^^

.. doxygengroup:: ovrtx_version
   :project: ovrtx
   :content-only:

Creation and Destruction
^^^^^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_creation
   :project: ovrtx
   :content-only:

Data Providers
^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_data_provider
   :project: ovrtx
   :content-only:

Stage Building
^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_stage_building
   :project: ovrtx
   :content-only:

Attribute Writes
^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_attribute_write
   :project: ovrtx
   :content-only:

Attribute Reads
^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_attribute_read
   :project: ovrtx
   :content-only:

Stage Queries
^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_stage_query
   :project: ovrtx
   :content-only:

.. _c-api-sensor-simulation:

Sensor Simulation
^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_sensor_simulation
   :project: ovrtx
   :content-only:

Stream Operations
^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_stream
   :project: ovrtx
   :content-only:

Extensions
^^^^^^^^^^

.. doxygengroup:: ovrtx_extension
   :project: ovrtx
   :content-only:

Performance Profiling
^^^^^^^^^^^^^^^^^^^^^

Collect simplified performance metrics, grouped RTX stages, and grouped memory data.
The update functions document retained-batch ownership, measurement meanings, and recommended
copy intervals for data collection and live visualization. Each sample includes an
execution ID identifying its CPU thread or RTX GPU, or zero if unspecified.
Injection variants accept no ID, attribute the calling thread, or preserve a supplied ID.

Retain a zero-initialized batch and reuse ``ovrtx_get_performance_data_update``
or its JSON counterpart. Each batch has independent progress.
Per-metric samples follow collection order, not timestamp order. A sample timestamp
can precede an earlier returned sample or a previous collection time.
``collection_time_ns`` is informational, not a bound on sample timestamps. Release the batch
before renderer teardown. No timestamp input is needed.
Copying does not recover overwritten history or guarantee a complete concurrent snapshot.

.. doxygengroup:: ovrtx_profiling
   :project: ovrtx
   :content-only:

Error Handling
^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_error
   :project: ovrtx
   :content-only:

Configuration Helpers
^^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_config_helpers
   :project: ovrtx
   :content-only:

Attribute Helpers
^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_attribute_helpers
   :project: ovrtx
   :content-only:

Types
-----

Core Types
^^^^^^^^^^

.. doxygengroup:: ovrtx_core_types
   :project: ovrtx
   :content-only:

.. _c-api-handle-types:

Handle Types
^^^^^^^^^^^^

Renderer resources, operations, provider registrations, and accessor array
leases use distinct structs containing ``uint64_t raw_id``. Keep that type
through function arguments, arrays, callbacks, and result fields. Use
``.raw_id`` for numeric diagnostics, C comparisons, or serialization; C++
supports same-kind comparison and hashing.

C++ value initialization (``Handle{}``) produces the invalid value for renderer
handles and provider IDs. Use the matching typed invalid constant for resets
and comparisons, such as ``query == OVRTX_INVALID_QUERY_HANDLE`` in C++.
These sentinels reserve zero for invalid renderer handles and provider IDs;
``OVRTX_INVALID_HANDLE`` is the raw numeric zero sentinel, not a typed handle.
An array lease is different: zero is a valid accessor-local ID and must be
released after a successful acquisition. Copying any identity does not retain
its resource, prove liveness, or identify its renderer or accessor.

For Python handle types and usage, see :ref:`python-handle-types`.

.. doxygengroup:: ovrtx_handle_types
   :project: ovrtx
   :content-only:

Result Types
^^^^^^^^^^^^

.. doxygengroup:: ovrtx_result_types
   :project: ovrtx
   :content-only:

Operation Wait Types
^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_op_wait_types
   :project: ovrtx
   :content-only:

Synchronization Types
^^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_sync_types
   :project: ovrtx
   :content-only:

Attribute Types
^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_attribute_types
   :project: ovrtx
   :content-only:

Query Types
^^^^^^^^^^^

.. doxygengroup:: ovrtx_query_types
   :project: ovrtx
   :content-only:

Read Types
^^^^^^^^^^

.. doxygengroup:: ovrtx_read_types
   :project: ovrtx
   :content-only:

.. _sensors-reference-composite-output:

.. _c-api-sensor-types:

Sensor Types
^^^^^^^^^^^^

.. doxygengroup:: ovrtx_sensor_types
   :project: ovrtx
   :content-only:

Picking Types
^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_pick_types
   :project: ovrtx
   :content-only:

Selection Styling Types
^^^^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_selection_style_types
   :project: ovrtx
   :content-only:

Operation Status Types
^^^^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_op_status_types
   :project: ovrtx
   :content-only:

Logging Types
^^^^^^^^^^^^^

.. doxygengroup:: ovx_log_types
   :project: ovrtx
   :content-only:

Configuration Types
^^^^^^^^^^^^^^^^^^^

.. doxygengroup:: ovrtx_config_types
   :project: ovrtx
   :content-only:
