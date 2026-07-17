.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: Status Queries Example
=========================

This example is based on the minimal C example and adds operation status queries
for USD loading and rendering.

It demonstrates:

1. Loading a USD layer from a remote S3 scene URL with ``ovrtx_open_usd_from_file()``
2. Polling ``ovrtx_query_op_status()`` while waiting
3. Running one shader-cache warm-up step with shader compilation progress
4. Stepping the renderer with ``ovrtx_step()``
5. Fetching, mapping, and writing the rendered output to ``out.png``

Renderer logs are written to ``_output/status-queries-ovrtx.log``.

.. pull-quote::

   *“Create a C/C++ rendering example that demonstrates operation status queries, including logging, asynchronous scene loading, progress and counter polling while waiting, shader warmup feedback, final image output, and both API and asynchronous operation error checks.”*

.. image:: ../../img/example-minimal.jpg
   :alt: Status queries example output
   :align: center

Build and Run
-------------

.. tab-set::

   .. tab-item:: Linux

      **Prerequisites**

      .. code-block:: bash

         sudo apt-get install build-essential cmake

      Runtime requires an NVIDIA RTX-capable GPU, a supported NVIDIA driver, internet access to download the remote S3 scene asset, and unsandboxed execution.

      The ovrtx library is downloaded automatically at configure time. If ovrtx is already installed and available through ``CMAKE_PREFIX_PATH``, the local installation is used instead.

      **Building**

      .. code-block:: bash

         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build

      **Running**

      .. code-block:: bash

         ./build/status-queries

   .. tab-item:: Windows

      **Prerequisites**

      - `Visual Studio 2017+ <https://visualstudio.microsoft.com/downloads/>`_
      - NVIDIA RTX-capable GPU
      - Supported NVIDIA driver
      - Internet access to download the remote S3 scene asset
      - Unsandboxed runtime execution

      The ovrtx library is downloaded automatically at configure time. If ovrtx is already installed and available through ``CMAKE_PREFIX_PATH``, the local installation is used instead.

      **Building**

      .. code-block:: pwsh

         cmake -B build
         cmake --build build --config Release

      **Running**

      .. code-block:: pwsh

         .\build\Release\status-queries.exe

Licensing
---------

This example uses ``stb_image_write.h`` from the minimal example, (c) Sean Barrett,
released under Public Domain.
