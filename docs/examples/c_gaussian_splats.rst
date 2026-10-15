.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: Gaussian Splats
==================

This example loads the same USDA scene as :doc:`python_gaussian_splats`,
renders one frame without preceding warmup frames, and saves :ref:`LdrColor <camera-output-tables>`.
Both static-loader and shared-loader executables are built.

The scene defines a ``ParticleField3DGaussianSplat`` prim. The following
USDA declaration and equivalent Python code show one orange splat. The supplied
scene uses the same array layout for all 73 splats. See
:doc:`../geometry/gaussian_splats` for the attribute meanings.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/gaussian_splat.usda
         :language: usda
         :start-after: # [snippet:doc-gaussian-splat-prim]
         :end-before: # [/snippet:doc-gaussian-splat-prim]
         :dedent:

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-gaussian-splat-prim-python]
         :end-before: # [/snippet:doc-gaussian-splat-prim-python]
         :dedent:

Before running, follow the :doc:`C API setup <../c_api/getting_started>` and
check the :doc:`GPU and driver requirements <../driver_requirements>`.
The first render may take longer while shaders compile and cache.

Start in the public ovrtx repository root, ``rendering/ovrtx/public`` in a
Kit checkout. Choose the commands for your platform to build and run both loaders:

.. tab-set::

   .. tab-item:: Windows (PowerShell)

      .. code-block:: pwsh

         cd examples/c/gaussian-splats
         cmake -B build
         cmake --build build --config Release
         .\build\static\Release\gaussian-splats.exe `
           ../../python/gaussian-splats/gaussian_splats.usda gaussian-static.png
         .\build\shared\Release\gaussian-splats-dynamic.exe `
           ../../python/gaussian-splats/gaussian_splats.usda gaussian-shared.png

   .. tab-item:: Linux

      .. code-block:: bash

         cd examples/c/gaussian-splats
         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build
         ./build/static/gaussian-splats \
           ../../python/gaussian-splats/gaussian_splats.usda gaussian-static.png
         ./build/shared/gaussian-splats-dynamic \
           ../../python/gaussian-splats/gaussian_splats.usda gaussian-shared.png

Both loaders render the supplied ``gaussian_splats.usda`` scene. The commands
write ``gaussian-static.png`` and ``gaussian-shared.png`` in
``examples/c/gaussian-splats``. If you omit the output filename, the example
writes ``out.png`` in the current directory.

To render PT or Minimal, change ``omni:rtx:rendermode`` on ``/Render/Camera``
in the supplied scene to ``PathTracing`` or ``MinimalRendering``. For Minimal,
keep ``omni:rtx:minimal:mode = 3`` and ``omni:rtx:minimal:dlss:mode = 2``,
which the scene already supplies. Both loaders use these settings.

The following code requests one RenderProduct and waits for its first frame.

.. literalinclude:: ../../examples/c/gaussian-splats/main.cpp
   :language: cpp
   :start-after: // [snippet:gaussian-c-step-renderer]
   :end-before: // [/snippet:gaussian-c-step-renderer]
   :dedent:

The output is copied to a PNG while its CPU mapping is alive:

.. literalinclude:: ../../examples/c/gaussian-splats/main.cpp
   :language: cpp
   :start-after: // [snippet:gaussian-c-map-rendered-output-cpu]
   :end-before: // [/snippet:gaussian-c-map-rendered-output-cpu]
   :dedent:
