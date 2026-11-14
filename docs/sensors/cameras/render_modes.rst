.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-render-modes:

Render Modes
============

ovrtx provides three render modes with different balances of throughput and
image fidelity. Each RenderProduct selects its mode independently, so cameras
in the same scene can use different modes: for example, Real-Time Path Tracing
for color images and Minimal for segmentation.

Choosing a render mode
----------------------

Choose a mode based on the lighting and outputs your application needs.
Real-Time Path Tracing is the default.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50
   :class: compact-table

   * - Mode
     - ``omni:rtx:rendermode``
     - Use and behavior
   * - :doc:`Real-Time Path Tracing <render_modes/real_time_path_tracing>`
     - ``RealTimePathTracing``
     - Path-traced lighting with real-time denoising, including indirect
       illumination, reflections and shadows. Use for camera simulation and
       synthetic images that need these lighting effects at interactive rates.
   * - :doc:`Path Tracing <render_modes/path_tracing>`
     - ``PathTracing``
     - Accumulates samples within a render step. Use for offline or reference
       images when the additional convergence time is acceptable.
   * - :doc:`Minimal <render_modes/minimal>`
     - ``MinimalRendering``
     - Simplified shading for workloads that prioritize throughput over
       path-traced lighting, such as segmentation, bounding-box visualization
       and reinforcement learning across many environments.

Output support differs by mode; see :doc:`Camera Outputs <outputs>`.
Minimal does not produce :ref:`HdrColor <camera-output-tables>` and cannot
supply the input required by the Camera generic core model.

Selecting a render mode
-----------------------

Author the token attribute ``omni:rtx:rendermode`` on the RenderProduct.
These snippets select Path Tracing for a 640 × 480 product and request
:ref:`LdrColor <camera-output-tables>`. They use an existing Camera prim at
``/World/Camera``; the Python snippet uses an existing USD ``stage``.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. filtered-literalinclude:: ../../../tests/docs/python/test_render_modes.py
         :language: usda
         :start-after: # [snippet:doc-path-tracing-render-product]
         :end-before: # [/snippet:doc-path-tracing-render-product]
         :omit-markers:
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-path-tracing-render-product-python]
         :end-before: # [/snippet:doc-path-tracing-render-product-python]
         :dedent:

.. _sensors-cameras-render-modes-availability:
.. _sensors-render-modes-availability:

Mode availability
-----------------

All three modes are available by default. Disable unused modes when creating
the renderer to avoid allocating resources needed only by those modes.
For example, a Minimal-only workload can save memory by disabling both
path-tracing modes. Selecting Minimal on a RenderProduct alone does not
disable the others or release their resources.

Availability is configured through :py:class:`~ovrtx.RendererConfig` in
Python or configuration entries passed to :c:func:`ovrtx_create_renderer()`
in C:

.. list-table::
   :header-rows: 1
   :widths: 40 60
   :class: compact-table

   * - Python option
     - C configuration entry
   * - ``enable_realtimepathtracing``
     - :c:func:`ovrtx_config_entry_enable_realtimepathtracing()`
   * - ``enable_pathtracing``
     - :c:func:`ovrtx_config_entry_enable_pathtracing()`
   * - ``enable_minimal``
     - :c:func:`ovrtx_config_entry_enable_minimal()`

At least one mode must remain enabled; disabling all three fails renderer
creation. With the default renderer settings, if a RenderProduct requests an
unavailable mode, the renderer logs a warning and uses the first available
mode in this order: Real-Time Path Tracing, Path Tracing, Minimal.

Renderer instances in one process share mode availability. A later instance
inherits it when the options are omitted; an explicit conflicting option
fails that instance's creation. The choice stays fixed while shared graphics
resources remain alive, including when retained by ``keep_system_alive``.
See :ref:`Startup render mode availability <renderer-startup-mode-availability>`
for Python/C examples and the resource-lifetime rules for changing that choice.

.. toctree::
   :maxdepth: 1

   render_modes/real_time_path_tracing
   render_modes/path_tracing
   render_modes/minimal

Related
-------

- :doc:`outputs` — outputs supported by each mode.
- :doc:`../common/output_configuration` — RenderProducts, render settings and warm-up.
- :doc:`../../core/renderer_configuration` — renderer creation and shared resources.
