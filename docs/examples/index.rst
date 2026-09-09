.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Examples
========

This section contains example projects demonstrating various features of ovrtx.

Example Projects
----------------

.. grid:: 2
   :gutter: 2

   .. grid-item-card:: Minimal
      :img-top: ../../img/example-minimal.jpg
      :img-alt: Minimal example output

      .. container:: example-prompt

         *“Create the smallest useful ovrtx example that loads an existing USD scene, renders one camera frame, maps the color output, and saves or displays the result while cleaning up resources appropriately.”*
      +++
      Build and run in: :doc:`C → <c_minimal>`, :doc:`Python → <python_minimal>`

   .. grid-item-card:: Status Queries
      :img-top: ../../img/example-minimal.jpg
      :img-alt: Status queries example output

      .. container:: example-prompt

         *“Create a rendering example that demonstrates operation status queries, including logging, asynchronous scene loading, progress and counter polling while waiting, shader warmup feedback, final frame rendering, output handling, and error checks.”*
      +++
      Build and run in: :doc:`C → <c_status_queries>`, :doc:`Python → <python_status_queries>`

   .. grid-item-card:: Vulkan Interop
      :img-top: ../../img/example-vulkan-interop.gif
      :img-alt: Vulkan Interop example output

      .. container:: example-prompt

         *“Create a C++ interactive viewer that renders ovrtx camera output directly into a Vulkan presentation path through CUDA interop, with GPU selection, GPU image mapping, exported-image copies, explicit synchronization, double buffering, orbit camera controls, finite-frame capture, and click or marquee picking with selection outlines.”*
      +++
      Build and run in: :doc:`C → <c_vulkan_interop>`

   .. grid-item-card:: Planet System
      :img-top: ../../img/example-planet-system.jpg
      :img-alt: Planet System example output

      .. container:: example-prompt

         *“Create an animation example that loads a base scene, injects generated runtime geometry, creates persistent transform bindings, updates many transforms efficiently each simulation step using CPU or GPU compute, renders frames, optionally streams or saves them, and cleans up bindings explicitly.”*
      +++
      Build and run in: :doc:`Python → <python_planet_system>`

   .. grid-item-card:: Tiled Rendering
      :img-top: ../../img/example-tiled-rendering.avif
      :img-alt: Tiled Rendering example output

      .. container:: example-prompt

         *“Create an example that composes multiple referenced scene instances into a grid, assigns per-instance visual variation at runtime, renders all cameras through one tiled output, warms up for image quality, and saves or displays the final tiled image.”*
      +++
      Build and run in: :doc:`Python → <python_tiled_rendering>`

   .. grid-item-card:: Crop Window
      :img-top: ../../img/example-crop-window.png
      :img-alt: Center crop rendered with dataWindowNDC

      .. container:: example-prompt

         *“Create an example that renders a centered dataWindowNDC crop from a full-resolution RenderProduct, verifies the cropped output dimensions, and saves or displays the result.”*
      +++
      Build and run in: :doc:`Python → <python_crop_window>`

   .. grid-item-card:: Sliced Rendering
      :img-top: ../../img/example-sliced-rendering.png
      :img-alt: Full image stitched from four rendered crops

      .. container:: example-prompt

         *“Render one image as four successive dataWindowNDC crops, warm up each crop, and stitch the captured TL, TR, BL, and BR tiles into a full-resolution image.”*
      +++
      Build and run in: :doc:`Python → <python_sliced_rendering>`

   .. grid-item-card:: Projectors
      :img-top: ../img/projectors-lineup.avif
      :img-alt: Projectors example output

      .. container:: example-prompt

         *“Create an example that loads an authored projector-mapping scene without editing it, warms up the renderer, renders one frame, and saves the result as a PNG.”*
      +++
      Build and run in: :doc:`Python → <python_projectors>`

   .. grid-item-card:: Semantic Segmentation
      :img-top: ../../img/example-semantic-segmentation.avif
      :img-alt: Semantic Segmentation example output

      .. container:: example-prompt

         *“Create an example that composes an existing scene with semantic label overrides and camera annotation outputs, renders several camera AOVs including semantic segmentation and its ID map, decodes metadata into human-readable labels, logs a useful visual layout to a viewer, and supports headless image export.”*
      +++
      Build and run in: :doc:`Python → <python_semantic_segmentation>`

   .. grid-item-card:: Lidar Sensor
      :img-top: ../../img/example-sensor-lidar.avif
      :img-alt: Lidar sensor example output

      .. container:: example-prompt

         *“Create a lidar sensor example that applies required sensor runtime settings as needed, loads a configured lidar scene, warms up the sensor pipeline, renders one point-cloud output, reads valid point data safely through the count channel, prints summary statistics, and cleans up resources appropriately.”*
      +++
      Build and run in: :doc:`C → <c_sensor_lidar>`, :doc:`Python → <python_sensor_lidar>`

   .. grid-item-card:: Radar Sensor
      :img-top: ../../img/example-sensor-radar.avif
      :img-alt: Radar sensor example output

      .. container:: example-prompt

         *“Create a radar sensor example that applies required runtime settings as needed, loads an animated radar scene, advances scene time across several simulation steps, reads valid detections including signal strength and signed radial velocity, prints per-step summaries, and cleans up resources appropriately.”*
      +++
      Build and run in: :doc:`C → <c_sensor_radar>`, :doc:`Python → <python_sensor_radar>`

   .. grid-item-card:: Material Editor
      :img-top: ../../img/example-material-editor.avif
      :img-alt: Material Editor example output

      .. container:: example-prompt

         *“Create a C++ Qt desktop application that combines live ovrtx rendering with read-only USD material introspection, showing materials, a rendered viewport, a shader graph, and editable shader properties, while keeping runtime material edits and rendering resets separate from introspection.”*
      +++
      Build and run in: :doc:`C → <c_material_editor>`

   .. grid-item-card:: SPG: Grayscale
      :img-top: ../../img/example-spg-grayscale.png
      :img-alt: SPG grayscale example output

      .. container:: example-prompt

         *“Create the smallest useful SPG example: a CUDA kernel that converts the LdrColor render output to grayscale, wired into a RenderProduct and read back from Python as a new AOV.”*
      +++
      Build and run in: :doc:`Python → <python_spg_grayscale>`

   .. grid-item-card:: SPG: Pipeline
      :img-top: ../../img/example-spg-pipeline.png
      :img-alt: SPG two-shader pipeline example output

      .. container:: example-prompt

         *“Chain two SPG shaders so the renderer's color output is converted to grayscale and then inverted in a single RenderProduct, reading back only the final result.”*
      +++
      Build and run in: :doc:`Python → <python_spg_pipeline>`

   .. grid-item-card:: SPG: Built-in Nodes
      :img-top: ../../img/example-spg-builtin-nodes.png
      :img-alt: SPG built-in node example output

      .. container:: example-prompt

         *“Chain two built-in SPG nodes (no custom CUDA) that brighten the color output and downscale it to half resolution, wired into a RenderProduct via info:id.”*
      +++
      Build and run in: :doc:`Python → <python_spg_builtin_nodes>`

   .. grid-item-card:: SPG: Generating Node
      :img-top: ../../img/example-spg-generate.png
      :img-alt: SPG generating node example output

      .. container:: example-prompt

         *“Write an SPG node with no input AOV that draws a checkerboard from typed USD attributes, and publish it as a render output.”*
      +++
      Build and run in: :doc:`Python → <python_spg_generate>`

   .. grid-item-card:: SPG: Separable Blur
      :img-top: ../../img/example-spg-blur.png
      :img-alt: SPG separable blur example output, sharp on the left and blurred on the right

      .. container:: example-prompt

         *“Chain two SPG nodes into a separable blur whose tap weights are built once in the launch script, and retune the radius from the host between renders.”*
      +++
      Build and run in: :doc:`Python → <python_spg_blur>`

   .. grid-item-card:: SPG: Stateful Node
      :img-top: ../../img/example-spg-stateful.png
      :img-alt: SPG stateful node example output

      .. container:: example-prompt

         *“Make an SPG node read back its own previous output, so a moving object drags a fading trail behind it.”*
      +++
      Build and run in: :doc:`Python → <python_spg_stateful>`

   .. grid-item-card:: SPG: Previous Frame
      :img-top: ../../img/example-spg-previous-frame.png
      :img-alt: SPG previous-frame example output, the rendered ball beside the frame-to-frame difference

      .. container:: example-prompt

         *“Have an SPG node read the same AOV twice, once live and once a frame back, and publish the difference so only what moved lights up.”*
      +++
      Build and run in: :doc:`Python → <python_spg_previous_frame>`

   .. grid-item-card:: SPG: Composite AOV
      :img-top: ../../img/example-spg-composite-aov.png
      :img-alt: SPG composite AOV example output

      .. container:: example-prompt

         *“Feed an SPG node from a lidar instead of a camera, reading the point cloud's named channels and publishing a histogram of returns by distance.”*
      +++
      Build and run in: :doc:`Python → <python_spg_composite_aov>`

   .. grid-item-card:: SPG: Ray Generation
      :img-top: ../../img/example-spg-raygen.png
      :img-alt: SPG ray-generation example output

      .. container:: example-prompt

         *“Have an SPG node trace the scene itself: a Cornell box with ray-traced shadows and the geometric normal recovered from probe rays alone.”*
      +++
      Build and run in: :doc:`Python → <python_spg_raygen>`

.. toctree::
   :hidden:

   python_minimal
   python_planet_system
   python_tiled_rendering
   python_crop_window
   python_sliced_rendering
   python_projectors
   python_status_queries
   python_semantic_segmentation
   python_sensor_lidar
   python_sensor_radar
   python_spg_grayscale
   python_spg_pipeline
   python_spg_builtin_nodes
   python_spg_generate
   python_spg_blur
   python_spg_stateful
   python_spg_previous_frame
   python_spg_composite_aov
   python_spg_raygen
   c_minimal
   c_vulkan_interop
   c_status_queries
   c_material_editor
   c_sensor_lidar
   c_sensor_radar
