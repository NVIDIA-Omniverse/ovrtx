.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-render-modes-real-time-path-tracing-frame-generation:

DLSS Frame Generation
=====================

DLSS Frame Generation lets an interactive viewer display smoother motion at a higher frame rate without increasing the camera simulation rate.

In Real-Time Path Tracing, it generates intermediate color frames between simulated camera frames. Your application can use these extra frames for display, selecting the frames it needs for each presentation. Frame generation is configured per RenderProduct.

To use it, enable frame generation on a color-only Real-Time Path Tracing RenderProduct, step the renderer as usual, and read the extra frames from the result. For interactive display, pace those frames between rendered captures and skip any that are no longer needed. The :doc:`C example <../../../../examples/c_frame_generation>` shows configuration and frame access; the :doc:`Vulkan interop example <../../../../examples/c_vulkan_interop>` adds presentation.

Interpolated and Simulated Frames
---------------------------------

Interpolated frames are inferred from neighboring simulated frames. They are not additional camera simulations and may be less accurate than simulated frames, particularly in regions that become newly visible between frames. Applications must decide whether interpolated frames are suitable for their downstream use.

Frame generation works with ``LdrColor`` or ``HdrColor`` only. It does not produce interpolated depth, segmentation, normals, or other render outputs.

Enabling Frame Generation
-------------------------

Author these attributes on the RenderProduct prim:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 42 10 10 38

   * - Setting
     - Type
     - Default
     - Description
   * - ``omni:rtx:dlss:frameGeneration``
     - ``bool``
     - ``false``
     - Enables frame generation.
   * - ``omni:rtx:dlss:frameGenerationInterpolatedFrameCount``
     - ``int``
     - ``0``
     - Requests the number of interpolated frames per simulated frame. ``0`` or an unset value requests one interpolated frame. Request more frames with an explicit count. Other values are limited by the :ref:`frame-generation-hardware-limits`.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../../../tests/docs/usd/data/frame_generation_render_product.usda
         :language: usda
         :start-after: # [snippet:doc-frame-generation-render-product]
         :end-before: # [/snippet:doc-frame-generation-render-product]
         :dedent:

   .. tab-item:: USD Python

      .. literalinclude:: ../../../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-frame-generation-render-product-python]
         :end-before: # [/snippet:doc-frame-generation-render-product-python]
         :dedent:

The same attributes may be written at runtime instead of authored in the loaded USD layer.

Reading the Frames
------------------

Each completed camera capture contributes its interpolated frames, if any, followed by its simulated frame. For exactly one capture per RenderProduct per step, this gives ``N + 1`` frames: ``N`` interpolated frames followed by one simulated frame. The snippets below assume this single-capture case, with all returned frames belonging to that capture, as in the unscheduled cameras used by these examples.

A scheduled camera can complete several captures during one step. For example, a 120 Hz camera stepped at 60 Hz can return two simulated captures even with frame generation disabled. Do not classify that whole result using ``frames[:-1]`` or ``output_frame_count - 1``: earlier simulated captures would be misidentified as interpolated frames. See :ref:`sensors-common-multi-rate` for camera scheduling.

Every frame exposes the same color render var path. Within a single-capture result, position in the frames array identifies the interpolated frames and the final simulated frame.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../../../tests/docs/python/test_frame_generation.py
         :language: python
         :start-after: # [snippet:doc-frame-generation-read-frames]
         :end-before: # [/snippet:doc-frame-generation-read-frames]
         :dedent:

   .. tab-item:: C++

      .. literalinclude:: ../../../../../examples/c/frame-generation/main.cpp
         :language: cpp
         :start-after: // [snippet:classify-output-frames]
         :end-before: // [/snippet:classify-output-frames]
         :dedent:

Read the frame count on every step instead of assuming the requested count was produced.

Presenting Generated Frames
---------------------------

For paced presentation, select the frame due at the current time and skip interpolated frames whose presentation times have passed. Showing those frames late would delay the rest of the batch. When a newer complete step arrives, replace the previous batch and discard its unshown frames. Re-present the current image when no newer frame is due.

The :doc:`Vulkan interop example <../../../../examples/c_vulkan_interop>` implements this policy. It waits until all frames of a step are ready and orders them by copy-submission timeline. With pacing enabled, it selects a frame using the elapsed time since that batch became ready, rather than advancing one frame per presentation. A late presentation can therefore skip several interpolated frames at once; the selection never moves backward within a batch.

Rendering and copying continue independently of presentation. The example's ten-image ring holds the published batch and the next batch being copied, plus spare slots, so holding a displayed frame does not block the next copy. It reports render steps, visible frames, presents, dropped frames, and visible-frame gaps separately. The presentation loop selects the frame as follows:

.. literalinclude:: ../../../../../examples/c/vulkan-interop/src/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-frame-pacing-promote]
   :end-before: // [/snippet:doc-frame-pacing-promote]
   :dedent:

Detecting Whether Frame Generation Is Active
--------------------------------------------

Count-based detection requires exactly one completed camera capture per RenderProduct per step. Under this precondition, more than one frame indicates that interpolation occurred. The renderer handles warm-up automatically; you do not need to discard initial steps. Multiple scheduled captures invalidate this detector, even when frame generation is disabled.

There is no public capability query. For the single-capture case, inspect each returned frame count:

.. literalinclude:: ../../../../../tests/docs/python/test_frame_generation.py
   :language: python
   :start-after: # [snippet:doc-frame-generation-detect]
   :end-before: # [/snippet:doc-frame-generation-detect]
   :dedent:

If subsequent single-capture steps still contain one frame, check the requirements below. The step succeeds and returns its normal simulated outputs when frame generation is unavailable or a requirement is not met.

.. _frame-generation-hardware-limits:

Requirements and Limits
-----------------------

The known public requirements and common renderer blockers are listed below. Meeting them does not guarantee that the installed driver and operating system support frame generation, so always inspect the returned frame count. When frame generation is unavailable, the step normally succeeds with only its simulated frame. The renderer logs warnings for some, but not all, causes.

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 35 35 30

   * - Requirement
     - Behavior when the requirement is not met
     - Application action
   * - The RenderProduct uses an Ada (RTX 40-series) or newer GPU.
     - Unsupported GPUs return only the simulated frame. No warning is logged.
     - Use Ada for one interpolated frame or Blackwell for up to three. Inspect the frame count because no public capability query is available.
   * - The RenderProduct uses a GPU that has an active display attached to it.
     - A display-less GPU returns only the simulated frame. No warning is logged.
     - Select a display-connected GPU with :ref:`render-product-device-pinning`.
   * - The driver and operating system support DLSS Frame Generation.
     - The RenderProduct returns only the simulated frame. Startup logs may report an NGX, driver, or operating-system requirement.
     - Use a supported NVIDIA driver and operating system.
   * - ``omni:rtx:rendermode`` is ``RealTimePathTracing``.
     - Other render modes return only the simulated frame.
     - Change the RenderProduct render mode.
   * - The RenderProduct requests only ``LdrColor`` or only ``HdrColor``.
     - Frame generation is disabled for the whole RenderProduct. The step still returns the requested simulated outputs.
     - Remove every additional RenderVar, including SPG outputs.
   * - The color output does not contain alpha.
     - The RenderProduct returns only the simulated frame and logs ``output contains alpha``.
     - Disable alpha output.
   * - Both resolution dimensions are at least 126 pixels.
     - The RenderProduct returns only the simulated frame and logs ``unsupported viewport resolution``.
     - Increase the RenderProduct resolution.
   * - OmniGraph postprocessing is not active on the RenderProduct.
     - The RenderProduct returns only the simulated frame and logs ``OmniGraph postprocessing being active``.
     - Remove the OmniGraph postprocessing graph.
   * - No renderer debug view is active.
     - The RenderProduct returns only the simulated frame and logs ``not supported with debug views``.
     - Disable the debug view.
   * - SDG disable-color rendering is not active.
     - The RenderProduct returns only the simulated frame and logs ``not supported with SDG disable color render mode``.
     - Enable color rendering.

Requests above the hardware maximum are reduced rather than rejected. Ada produces at most one interpolated frame per simulated frame; Blackwell produces at most three. For example, requesting three on Ada produces one interpolated frame.

For incompatible outputs, alpha, resolution, or OmniGraph postprocessing, the renderer logs ``Disabling DLSS Frame Generation for at least one view due to ...`` once for each distinct combination of causes. Debug views and SDG disable-color mode use ``Disabling DLSS Frame Generation for ... because it is ...``. Inspect the log from the start of the run. Unsupported and display-less GPUs do not produce these blocker warnings.

Related
-------

- :doc:`../real_time_path_tracing`
- :doc:`../../../../examples/c_frame_generation` — headless example that writes every returned frame
- :doc:`../../../../examples/c_vulkan_interop` — swapchain presentation and frame pacing
- :ref:`sensors-common-sensor-outputs-frames` — the general frame-delivery contract
- :doc:`../../../common/output_configuration` — authoring RenderProducts and render settings
