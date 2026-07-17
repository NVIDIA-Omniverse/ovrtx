.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C API Practical Patterns
========================

The C API reference lists functions and types. This page covers the common
usage patterns that make those functions safe to combine in applications.

Version and Configuration
-------------------------

Build the renderer configuration from ``ovrtx_config_entry_t`` values, then pass
the array to :c:func:`ovrtx_create_renderer`.

.. literalinclude:: ../../tests/docs/c/test_support_api.cpp
   :language: cpp
   :start-after: // [snippet:doc-version-and-config-c]
   :end-before: // [/snippet:doc-version-and-config-c]
   :dedent:

String Handling
---------------

ovrtx C strings use ``ovx_string_t``: a ``ptr`` and explicit ``length``. The
strings are null-terminated where practical, but C and C++ code should use the
length field for printing, comparison, and copying.

The minimal C example's error helper demonstrates safe conversion to
``std::string_view`` and length-aware printing:

.. literalinclude:: ../../examples/c/minimal/main.cpp
   :language: cpp
   :start-after: // [snippet:check-error-helper]
   :end-before: // [/snippet:check-error-helper]
   :dedent:

Error Lifetimes
---------------

Immediate API failures report details through :c:func:`ovrtx_get_last_error`.
Consume or copy the returned string before the next API call on the same thread.

.. literalinclude:: ../../tests/docs/c/test_support_api.cpp
   :language: cpp
   :start-after: // [snippet:doc-get-last-error-c]
   :end-before: // [/snippet:doc-get-last-error-c]
   :dedent:

Asynchronous failures are reported when waiting. The wait result contains op ids
that failed, and each id can be queried with :c:func:`ovrtx_get_last_op_error`.
Those wait-result arrays and strings are transient and invalidated by the next
wait on the same thread.

.. literalinclude:: ../../tests/docs/c/test_error_handling.cpp
   :language: cpp
   :start-after: // [snippet:doc-wait-op-error-retrieval-c]
   :end-before: // [/snippet:doc-wait-op-error-retrieval-c]
   :dedent:

No explicit error-release call is needed.

.. literalinclude:: ../../tests/docs/c/test_error_handling.cpp
   :language: cpp
   :start-after: // [snippet:doc-wait-op-no-release-errors-c]
   :end-before: // [/snippet:doc-wait-op-no-release-errors-c]
   :dedent:

Status Queries
--------------

Status queries are snapshots for pending or recently completed operations. Use
them for progress indicators and diagnostics. Release each successful status
query with :c:func:`ovrtx_release_op_status`.

.. literalinclude:: ../../tests/docs/c/test_support_api.cpp
   :language: cpp
   :start-after: // [snippet:doc-query-op-status-c]
   :end-before: // [/snippet:doc-query-op-status-c]
   :dedent:

Logging Callback
----------------

The log callback is process-global. The channel filter is a comma-separated
list of ``channel_prefix=level`` rules; the longest matching channel prefix
wins. Accepted levels include ``verbose``, ``debug``, ``info``, ``warn``,
``warning``, ``error``, and ``fatal``.

.. literalinclude:: ../../tests/docs/c/test_logging.cpp
   :language: cpp
   :start-after: // [snippet:doc-log-callback-prefix-filter-c]
   :end-before: // [/snippet:doc-log-callback-prefix-filter-c]
   :dedent:

Resource Cleanup
----------------

- Destroy renderers with :c:func:`ovrtx_destroy_renderer`.
- Destroy fetched step results with :c:func:`ovrtx_destroy_results`.
- Unmap render-var outputs with :c:func:`ovrtx_unmap_render_var_output`.
- Destroy attribute bindings with :c:func:`ovrtx_destroy_attribute_binding`.
- Release operation status snapshots with :c:func:`ovrtx_release_op_status`.
