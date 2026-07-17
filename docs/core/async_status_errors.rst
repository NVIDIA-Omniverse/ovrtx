.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Async Operations, Status, and Errors
====================================

ovrtx enqueue operations are internally asynchronous and stream-ordered. Python
offers blocking convenience methods plus ``*_async`` variants. C enqueue
functions return operation ids that must be waited before fetching results or
assuming side effects are visible.

Python Operations
-----------------

``Operation.wait(timeout_ns=0)`` polls. ``Operation.wait()`` blocks indefinitely.
Operations that produce data use a two-phase lifecycle: wait returns a pending
fetch object, then ``fetch()`` retrieves the result.

.. tab-set::

   .. tab-item:: Load USD

      .. literalinclude:: ../../tests/docs/python/test_support_api.py
         :language: python
         :start-after: # [snippet:doc-open-usd-async]
         :end-before: # [/snippet:doc-open-usd-async]
         :dedent:

   .. tab-item:: Step

      .. literalinclude:: ../../tests/docs/python/test_camera_sensors.py
         :language: python
         :start-after: # [snippet:doc-step-async]
         :end-before: # [/snippet:doc-step-async]
         :dedent:

C Waits
-------

In C, check the immediate enqueue status first, then wait on ``op_index``. Some
errors, such as a missing USD file during load, are reported only when the
operation is waited.

.. literalinclude:: ../../examples/c/minimal/main.cpp
   :language: cpp
   :start-after: // [snippet:load-usd-and-wait]
   :end-before: // [/snippet:load-usd-and-wait]
   :dedent:

Status Queries
--------------

Status queries take a point-in-time snapshot of a pending operation. They are
useful for progress bars and logs while waiting for long-running work such as
USD loading, shader compilation, stage queries, or render steps.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/status-queries/main.py
         :language: python
         :start-after: # [snippet:wait-operation-with-status]
         :end-before: # [/snippet:wait-operation-with-status]

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/status-queries/main.cpp
         :language: cpp
         :start-after: // [snippet:wait-operation-with-status-c]
         :end-before: // [/snippet:wait-operation-with-status-c]

Python ``Operation.query_status()`` is available only before ``wait()`` consumes
the operation context. In C, each successful :c:func:`ovrtx_query_op_status`
call must be paired with :c:func:`ovrtx_release_op_status`.

Error Handling
--------------

Python methods raise ``RuntimeError`` on API failures or async operation
failures. In C, every API result must be checked. Error strings returned by
:c:func:`ovrtx_get_last_error` are valid only until the next API call on the
same thread.

The minimal C example uses a helper that works with both synchronous and enqueue
results:

.. literalinclude:: ../../examples/c/minimal/main.cpp
   :language: cpp
   :start-after: // [snippet:check-error-helper]
   :end-before: // [/snippet:check-error-helper]

C Log Callback
--------------

The C API can install a process-global log callback. Use it for application
logging, CI diagnostics, or routing ovrtx messages into another logging system.

.. literalinclude:: ../../tests/docs/c/test_logging.cpp
   :language: cpp
   :start-after: // [snippet:doc-log-callback-prefix-filter-c]
   :end-before: // [/snippet:doc-log-callback-prefix-filter-c]
   :dedent:

The channel filter is a comma-separated list of ``channel_prefix=level`` rules.
Accepted levels are ``verbose``/``debug``, ``info``, ``warn``/``warning``,
``error``, and ``fatal``. The longest matching channel prefix wins.
