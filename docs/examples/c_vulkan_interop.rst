.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: Vulkan Interop
==================

This example demonstrates how to integrate ovrtx with Vulkan by sharing renders on the GPU.

The example maps ovrtx outputs to CUDA arrays every frame, then copies them to CUDA-exported VkImage memory. A fullscreen quad samples the resulting textures to display the render in real time in a GLFW window. Memory access between CUDA and Vulkan is synchronized using timeline semaphores.

The example also demonstrates viewport picking, marquee selection, and styled selection rendering. Left-click picks the prim under the cursor, left-drag performs marquee selection with a Vulkan overlay rectangle, selected prim paths are printed to stderr, and selected prims are highlighted with a custom outline color and translucent fill.

Any scene used with picking must restrict the picked RenderProduct to CUDA-visible GPU 0 with ``uint[] deviceIds = [0]``.

.. pull-quote::

   *“Create a C++ interactive viewer that renders ovrtx camera output directly into a Vulkan presentation path through CUDA interop, with GPU selection, GPU image mapping, exported-image copies, explicit synchronization, double buffering, orbit camera controls, finite-frame capture, and click or marquee picking with selection outlines.”*

.. image:: ../../img/example-vulkan-interop.gif
   :alt: Vulkan interop example
   :align: center

Build and Run
-------------

.. tab-set::

   .. tab-item:: Linux

      **Prerequisites**

      - ``sudo apt install build-essential cmake``
      - `Vulkan SDK 1.3.250+ <https://vulkan.lunarg.com/sdk/home>`_
      - `CUDA Toolkit 12.0+ <https://developer.nvidia.com/cuda-downloads>`_
      - NVIDIA RTX-capable GPU
      - Supported NVIDIA driver
      - Internet access to download the default remote S3 scene asset
      - Unsandboxed runtime execution

      If ovrtx or glfw3 are already installed and available through ``CMAKE_PREFIX_PATH``, the local installations are used. Otherwise they are downloaded automatically at configure time. Other dependencies (GLM, volk, unordered_dense) are always downloaded using FetchContent.

      **Building**

      .. code-block:: bash

         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build

      **Running**

      .. code-block:: bash

         ./build/ovrtx-interop

   .. tab-item:: Windows

      **Prerequisites**

      - `Visual Studio 2017+ <https://visualstudio.microsoft.com/downloads/>`_
      - `Vulkan SDK 1.3.250+ <https://vulkan.lunarg.com/sdk/home>`_
      - `CUDA Toolkit 12.0+ <https://developer.nvidia.com/cuda-downloads>`_
      - NVIDIA RTX-capable GPU
      - Supported NVIDIA driver
      - Internet access to download the default remote S3 scene asset
      - Unsandboxed runtime execution

      If ovrtx or glfw3 are already installed and available through ``CMAKE_PREFIX_PATH``, the local installations are used. Otherwise they are downloaded automatically at configure time. Other dependencies (GLM, volk, unordered_dense) are always downloaded using FetchContent.

      **Building**

      .. code-block:: pwsh

         cmake -B build
         cmake --build build --config Release

      **Running**

      .. code-block:: pwsh

         .\build\Release\ovrtx-interop.exe

Scene Configuration
-------------------

The example is configured to load the robot scene from Omniverse. Running the default configuration requires internet access to download this remote S3 scene asset:

.. list-table::
   :header-rows: 1

   * - Setting
     - Value
   * - USD Scene
     - ``https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda``
   * - Render Product
     - ``/Render/Camera``
   * - Up Axis
     - Z
   * - Units
     - Meters

Controls
--------

- **Right-click and drag** — Rotate camera around the target point
- **Left-click** — Pick the prim under the cursor and print its path
- **Left-click and drag** — Marquee-select prims and print their paths
- **Mouse wheel** — Dolly camera in/out

Licensing
---------

This example contains ``stb_image_write.h``, © Sean Barrett, released under Public Domain.
