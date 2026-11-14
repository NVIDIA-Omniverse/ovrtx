.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: Runtime textures
===================

Update an attached runtime texture from red to green using CUDA texels.
The material continues referencing ``dynamic://runtimeTextureExample``.
Both states are rendered and checked for the expected primary color.

Use matching ovrtx and ovstage packages containing ``OmniRuntimeTexture``;
older releases do not support this example. The shared scene reuses the
documentation test plane, camera, and studio environment.

The following sequence publishes texels at a coherent ordinal:

.. literalinclude:: ../../examples/c/runtime-textures/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-runtime-texture-c-update]
   :end-before: // [/snippet:doc-runtime-texture-c-update]
   :dedent:

Running
-------

.. code-block:: bash

   cd examples/c/runtime-textures
   cmake -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   ./build/static/runtime-textures
   ./build/shared/runtime-textures-dynamic



Requires CMake 3.18+, a C++17 compiler, and an RTX-capable GPU with a supported driver.
The code uses the C APIs; C++ provides file handling and containers.
On Windows use ``build/static/Release/runtime-textures.exe`` and
``build/shared/Release/runtime-textures-dynamic.exe``.
CUDA production requires a CUDA development toolkit at configure time;
set ``-DCUDAToolkit_ROOT=/path/to/cuda`` if needed.
Both producer and renderer use CUDA device 0.
Each executable writes ``runtime-textures_before.png`` (red) and
``runtime-textures.png`` (green) beside itself. Both loader models use attached ovstage.

The images show :ref:`LdrColor <camera-output-tables>`. For supported formats,
lifetime rules, and attachment behavior, see :doc:`../materials/runtime_textures`.
