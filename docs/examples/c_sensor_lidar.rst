.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: Lidar Sensor
===============

This example populates an ovstage instance from ``lidar_example.usda``, attaches
it to the renderer, renders a lidar ``PointCloud`` output through
``ovrtx_step_with_stage``, maps the composite render variable to CPU memory, and
reads the named tensor channels. ovstage owns scene ingest and stepping; sensor
output fetch/map stays a renderer-side concern on the ovrtx APIs.

The scene is Z-up and contains a lidar at ``(0, 0, 1)`` rotated to look along
world +X, an asphalt ground plane, and a concrete cube. The USD requests
``Coordinates``, ``Intensity``, ``Counts``, and ``TimeOffsetNs`` channels.

The executable enables MotionBVH through ``ovrtx_config_t`` at renderer
creation because it is required by the lidar sensor pipeline.

.. pull-quote::

   *“Create a C/C++ lidar sensor example that configures the renderer for sensor output, loads a lidar scene, warms up the sensor pipeline, renders one point-cloud output, reads valid point data safely through the count channel, prints summary statistics, and cleans up all results and mappings.”*

.. image:: ../../img/example-sensor-lidar.avif
   :alt: Lidar sensor example output
   :align: center

Build and Run
-------------

.. tab-set::

   .. tab-item:: Linux

      **Prerequisites**

      .. code-block:: bash

         sudo apt install build-essential cmake

      **Building**

      .. code-block:: bash

         cd examples/c/lidar
         cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build

      **Running**

      .. code-block:: bash

         ./build/lidar-composite-tensor

      You can also pass an explicit scene path:

      .. code-block:: bash

         ./build/lidar-composite-tensor path/to/lidar_example.usda

   .. tab-item:: Windows

      **Prerequisites**

      - `Visual Studio 2017+ <https://visualstudio.microsoft.com/downloads/>`_

      **Building**

      .. code-block:: pwsh

         cd examples/c/lidar
         cmake -S . -B build
         cmake --build build --config Release

      **Running**

      .. code-block:: pwsh

         .\build\Release\lidar-composite-tensor.exe

Expected output values vary, but a successful run prints the number of valid
points, mean intensity, and maximum time offset in nanoseconds.
