.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: Radar Sensor
===============

This example populates an ovstage instance from ``radar_example.usda``,
attaches it to the renderer, renders a radar ``PointCloud`` output through
``ovrtx_step_with_stage``, maps the composite render variable to CPU memory,
and reads the named tensor channels. ovstage owns scene ingest and stepping;
sensor output fetch/map stays a renderer-side concern on the ovrtx APIs. The
moving target approaches the radar, so its ``RadialVelocityMs`` values are
expected to be negative.

The scene is Z-up and contains a radar at ``(0, 0, 1)`` rotated to look along
world +X, an asphalt ground plane, a moving steel cube, and a fixed concrete
cube. The USD requests ``Coordinates``, ``Counts``, ``RCS``, and
``RadialVelocityMs`` channels.

The executable enables MotionBVH through ``ovrtx_config_t`` at renderer
creation because it is required for moving-object radial velocity.

.. pull-quote::

   *“Create a C/C++ radar sensor example that configures the renderer for sensor output, loads an animated radar scene, advances scene time across several simulation steps, reads valid detection data including signal strength and signed radial velocity, prints per-step summaries, reports moving-target observations, and cleans up all resources.”*

.. image:: ../../img/example-sensor-radar.avif
   :alt: Radar sensor example output
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

         cd examples/c/radar
         cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build

      **Running**

      .. code-block:: bash

         ./build/radar-composite-tensor

      You can also pass an explicit scene path:

      .. code-block:: bash

         ./build/radar-composite-tensor path/to/radar_example.usda

   .. tab-item:: Windows

      **Prerequisites**

      - `Visual Studio 2017+ <https://visualstudio.microsoft.com/downloads/>`_

      **Building**

      .. code-block:: pwsh

         cd examples/c/radar
         cmake -S . -B build
         cmake --build build --config Release

      **Running**

      .. code-block:: pwsh

         .\build\Release\radar-composite-tensor.exe

Expected output values vary, but a successful run prints 10 steps and a final
observation line summarizing detections with nonzero radial velocity.
