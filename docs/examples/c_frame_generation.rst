.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: DLSS Frame Generation Example
================================

DLSS Frame Generation makes motion smoother in an interactive viewer by adding color frames between simulated camera frames. You can display these extra frames without increasing the camera simulation rate. It works in Real-Time Path Tracing.

This example shows how to enable the feature, read the returned frames, and save them as PNGs. It moves an NVIDIA logo across a grid so you can see the intermediate positions. To display the frames in a window, use the :doc:`Vulkan interop example <c_vulkan_interop>`, which also shows how to pace presentation and drop interpolated frames that are no longer needed.

.. image:: ../../img/example-frame-generation.avif
   :alt: Three interpolated frames followed by the simulated frame, with the NVIDIA logo advancing across the ground
   :align: center

The animation shows all four frames returned by one step on a Blackwell GPU: three interpolated frames followed by the simulated frame.

Hardware Requirements
---------------------

Frame generation requires an Ada (RTX 40-series) or newer GPU. The RenderProduct must run on a GPU with an active display attached and use a supported NVIDIA driver and operating system; a GPU used only for display-less rendering does not generate interpolated frames. On unsupported hardware, the example still runs and reports one simulated frame per step. Refer to :doc:`../driver_requirements` for driver requirements.

Ada supports one interpolated frame per simulated frame. Blackwell supports up to three. Requests above the hardware maximum are reduced rather than rejected. Refer to :doc:`../sensors/cameras/render_modes/real_time_path_tracing/frame_generation` for all requirements.

Build and Run
-------------

Configuring the packaged example requires network access so CMake can download the pinned ovrtx and ovstage archives. The scene ships with the example, so runtime network access is not required.

.. tab-set::

   .. tab-item:: Linux

      **Prerequisites**

      .. code-block:: bash

         sudo apt-get install build-essential cmake

      Runtime requires a supported NVIDIA driver and unsandboxed execution.

      **Building**

      .. code-block:: bash

         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build

      **Running**

      .. code-block:: bash

         ./build/frame-generation --frames 3

   .. tab-item:: Windows

      **Prerequisites**

      - `Visual Studio 2022 17.8 or newer <https://visualstudio.microsoft.com/downloads/>`_ with C++ tools
      - A supported NVIDIA driver
      - Unsandboxed runtime execution

      **Building**

      .. code-block:: pwsh

         cmake -B build
         cmake --build build --config Release

      **Running**

      .. code-block:: pwsh

         .\build\Release\frame-generation.exe --frames 3

Interpreting Results
--------------------

The example saves every requested step to the current working directory. The default two steps let you inspect startup and the next capture. A startup or reset step may contain only the simulated frame while interpolation history is established.

On Blackwell, ``--frames 3`` can produce ``step1_interp0.png``, ``step1_interp1.png``, ``step1_interp2.png``, and ``step1_simulated.png`` for the second step. Ada supports one interpolated frame, so the same request can produce two files. Requests above the hardware maximum are reduced rather than rejected.

The printed ``output_frame_count`` tells you what was returned. For the bundled camera, a count greater than one means frame generation is active. A successful run with one frame per step still rendered and saved the simulated images. If later steps have no interpolated frames, check the :doc:`feature requirements <../sensors/cameras/render_modes/real_time_path_tracing/frame_generation>`.

Using Frame Generation in Your Application
------------------------------------------

Configure your RenderProduct for Real-Time Path Tracing with a single color output, then enable frame generation. This USD example requests three interpolated frames; the camera at ``/World/Camera`` must already exist:

.. literalinclude:: ../../tests/docs/usd/data/frame_generation_render_product.usda
   :language: usda
   :prepend: #usda 1.0
   :start-after: # [snippet:doc-frame-generation-render-product]
   :end-before: # [/snippet:doc-frame-generation-render-product]

You can also write these attributes at runtime. This example uses ``author_frame_generation()`` in ``main.cpp`` to apply the command-line options through ovstage before stepping.

Step the renderer as usual, then select the RenderProduct from the result. For the unscheduled camera used here, every step completes one capture: its interpolated frames come first and its simulated frame comes last. The following code derives their indices from the returned count:

.. literalinclude:: ../../examples/c/frame-generation/main.cpp
   :language: cpp
   :start-after: // [snippet:classify-output-frames]
   :end-before: // [/snippet:classify-output-frames]

Select a frame before looking up its color RenderVar, then map, consume, and unmap the output. Each frame uses the same RenderVar path. The example saves all frames; a viewer should select the frame due for presentation and drop overdue interpolated frames.

Custom ``--usd`` scenes must retain the expected ``/Render/Camera``, ``/Render/LdrColor``, and ``/World/Logo`` prims and complete exactly one capture per step. A scheduled camera can return several simulated captures in one step, so this example's count-based classification does not apply to that case.

Options
-------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 30 70

   * - Option
     - Meaning
   * - ``--frames <n>``
     - Requests a non-negative interpolated frame count. ``0`` or an unset value requests one interpolated frame. Request more frames with an explicit count. The renderer reduces requests above the hardware maximum.
   * - ``--steps <n>``
     - Sets a positive number of steps to render and save. The default is 2.
   * - ``--sweep <units>``
     - Sets how far the logo moves along X per step. The default is 5 world units.
   * - ``--no-frame-gen``
     - Disables frame generation for comparison with the same scene.
   * - ``--usd <path>``
     - Selects the USD layer to render. The default is the bundled ``frame-generation.usda``.

Licensing
---------

This example uses ``stb_image_write.h`` from the minimal example, (c) Sean Barrett, released under Public Domain.
