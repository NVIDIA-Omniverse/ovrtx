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

All operations return a status code indicating success or failure:

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

Handle Types
^^^^^^^^^^^^

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
