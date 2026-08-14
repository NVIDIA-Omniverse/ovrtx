.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Render Modes
============

Camera sensors in ovrtx support three render modes, each offering a different trade-off between image quality and performance. The render mode is set per RenderProduct using the ``omni:rtx:rendermode`` attribute.

.. filtered-literalinclude:: ../../../tests/docs/python/test_render_modes.py
   :language: usda
   :start-after: # [snippet:doc-path-tracing-render-product]
   :end-before: # [/snippet:doc-path-tracing-render-product]
   :omit-markers:

Available Modes
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Mode
     - ``omni:rtx:rendermode``
     - Description
   * - Real-Time Path-Tracing
     - ``RealTimePathTracing``
     - Full path-traced rendering with real-time denoising. Produces high-quality images with accurate global illumination, reflections, and shadows. This is the default mode and the best choice for most applications requiring visual fidelity.
   * - Path Tracing
     - ``PathTracing``
     - Progressive path tracing that accumulates samples over multiple frames for ground-truth-quality rendering. Best suited for offline or reference-quality workflows where convergence time is acceptable.
   * - Minimal
     - ``Minimal``
     - Lightweight rasterization-based rendering with minimal GPU cost. Use this when you need maximum throughput and do not require path-traced lighting -- for example, segmentation masks, bounding-box visualization, or high-FPS reinforcement learning loops.

Choosing a Mode
---------------

- **Default to Real-Time Path-Tracing** for sensor simulation, synthetic data generation, and any workflow that requires physically accurate lighting.
- Use **Path Tracing** when you need converged, reference-quality images and can afford to accumulate samples across frames.
- Use **Minimal** when rendering throughput matters more than visual quality -- for example, thousands of environments stepping in parallel for RL training.

Different RenderProducts in the same scene can use different render modes. For example, one camera could use **Real-Time Path-Tracing** for RGB output while another uses **Minimal** for fast segmentation.

Refer to :doc:`outputs` for the available outputs per render mode.

.. toctree::
   :maxdepth: 1

   render_modes/real_time_path_tracing
   render_modes/path_tracing
   render_modes/minimal
