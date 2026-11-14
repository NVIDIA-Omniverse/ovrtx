.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Application Flow
================

Most ovrtx applications follow the same sequence:

**Standalone mode** (ovrtx owns the stage):

This compatibility path remains functional in 0.4, but its scene population,
query, read/write, binding, and mapping APIs are deprecated in favor of ovstage.

1. Create a renderer.
2. Load USD content into the renderer's runtime stage.
3. Step one or more RenderProducts to produce output.
4. Map render variables or read stage attributes.
5. Release mappings, results, bindings, and renderer resources.

**Attached mode** (ovrtx 0.4+, rendering an externally owned ovstage):

1. Create a renderer.
2. Attach an ``ovstage_instance_t`` through :c:func:`ovrtx_attach_ovstage`.
3. Advance ovstage's write floor after committed scene mutations.
4. In C, call :c:func:`ovrtx_update_from_stage`, then step through
   :c:func:`ovrtx_step_with_stage` at that ordinal. In Python, call
   ``Renderer.step(..., ordinal=...)``, which performs both operations.
5. Map render variables and consume outputs as usual.
6. Detach and release renderer resources.

Refer to :doc:`ovstage_integration` for the full attached-stage lifecycle, including
ordinals and write-floor gates.

The USD stage normally contains three related kinds of prims:

- A **sensor prim**, such as a ``UsdGeomCamera``, ``OmniLidar``, or ``OmniRadar``.
- A **RenderProduct** prim, which is the path passed to ``step`` / :c:func:`ovrtx_step`.
- One or more **RenderVar** prims, which declare the outputs produced by the RenderProduct.

``step`` takes RenderProduct paths, not sensor paths. Render settings such as
``omni:rtx:rtpt:maxBounces`` are also authored on the RenderProduct, not on the
Camera, lidar, or radar prim.

Minimal Lifecycle
-----------------

.. tab-set::

   .. tab-item:: Python

      The minimal Python example shows the complete synchronous flow: create a
      renderer, load USD, step the RenderProduct, map the color output, and
      consume the tensor.

      .. filtered-literalinclude:: ../../examples/python/minimal/main.py
         :language: python
         :start-after: # its affiliates is strictly prohibited.
         :exclude-pattern: ^\s*#\s*\[/?snippet:
         :dedent:

   .. tab-item:: C

      The minimal C example shows the same flow with explicit waits, fetches,
      mapping, unmapping, result destruction, and renderer destruction.

      .. filtered-literalinclude:: ../../examples/c/minimal/main.cpp
         :language: cpp
         :start-after: // its affiliates is strictly prohibited.
         :exclude-pattern: ^\s*//\s*\[/?snippet:
         :dedent:

Python vs. C
------------

.. list-table::
   :header-rows: 1

   * - Concern
     - Python
     - C
   * - Renderer lifetime
     - Managed by Python object lifetime.
     - Call :c:func:`ovrtx_destroy_renderer`.
   * - USD loading
     - Synchronous methods block; ``*_async`` methods return ``Operation``.
     - Enqueue functions return an operation id and must be waited.
   * - Stepping
     - ``step`` returns outputs; ``step_async`` returns an ``Operation`` whose result must be fetched.
     - :c:func:`ovrtx_step`, :c:func:`ovrtx_wait_op`, then :c:func:`ovrtx_fetch_results`.
   * - Output access
     - Map a ``RenderVarOutput`` and use DLPack consumers such as NumPy.
     - Map with :c:func:`ovrtx_map_render_var_output` and unmap explicitly.
   * - Error handling
     - Methods raise ``RuntimeError``.
     - Check status codes and inspect :c:func:`ovrtx_get_last_error`.

Process Exit
------------

Destroy every renderer and call :c:func:`ovrtx_shutdown` once per :c:func:`ovrtx_initialize`
before the process exits. That is the only path that releases ovrtx's GPU resources and plug-ins.

A host that exits without doing so, by returning from ``main`` or calling ``exit()``, keeps its own
exit code: ovrtx does not tear the renderer system down from an exit handler. The process ends in
an exit handler that ovrtx's runtime installs. That handler does three things:

1. It deregisters ovrtx's profiler, crash-reporter and localization clients without tearing down
   the runtime. Plug-ins stay loaded, and no GPU teardown runs.
2. It flushes ``stdout`` and ``stderr``.
3. It ends the process with the host's exit code: ``_exit()`` on Linux, ``TerminateProcess()`` on Windows.

What the host gives up depends on the platform:

- **Linux**: the handler runs from ``atexit``. ovrtx re-registers it whenever a plug-in is
  registered, which happens during ovrtx initialization and renderer creation, so it runs before
  every handler registered earlier. ``atexit`` handlers and static destructors registered before
  that last re-registration do not run. This includes host handlers registered before
  :c:func:`ovrtx_initialize`. Handlers registered later run first.
- **Linux**: other open ``FILE*`` streams are not flushed. ``fflush`` or ``fclose`` them before
  exiting.
- **Windows**: ``exit()`` runs the executable's ``atexit`` handlers and static destructors and
  flushes all streams before the handler runs. DLL static destructors and other DLL detach work
  do not run.

Where to Go Next
----------------

- :doc:`renderer_configuration` - renderer config entries and deployment layout.
- :doc:`ovstage_integration` - ovstage integration, ordinals, and write-floor gates.
- :doc:`async_status_errors` - async operation waits, status queries, and errors.
- :doc:`../scene/loading_usd` - loading files, URLs, inline USDA, and references (standalone mode).
- :doc:`../sensors/common/sensor_outputs` - mapping rendered output on CPU or CUDA.
- :doc:`../scene/attributes` - reading and writing runtime stage attributes.
