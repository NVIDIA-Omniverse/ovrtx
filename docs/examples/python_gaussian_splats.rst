.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Gaussian Splats
=======================

Render 73 procedural Gaussian splats: three colored rings and a soft white
splat, above the existing documentation ground with studio lighting.
The scene uses local documentation assets and needs no captured Gaussian dataset.

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

Before running, follow the :doc:`Python setup <../python_api/getting_started>` and
check the :doc:`GPU and driver requirements <../driver_requirements>`.
The first render may take longer while shaders compile and cache.

Start in the public ovrtx repository root, ``rendering/ovrtx/public`` in a
Kit checkout. The commands below work in Windows PowerShell and Linux shells.
Run one mode per process to compare the same scene:

.. code-block:: console

   # Enter the Gaussian example project.
   cd examples/python/gaussian-splats
   # Render Real-Time Path Tracing to a PNG.
   uv run main.py --mode rtpt --png _output/rtpt.png
   # Render Path Tracing to a PNG.
   uv run main.py --mode pt --png _output/pt.png
   # Render Minimal with Full MDL and Ray Reconstruction to a PNG.
   uv run main.py --mode minimal --png _output/minimal.png
   # Save the default RTPT render as a Rerun recording.
   uv run main.py --rrd _output/gaussians.rrd

The example saves the first frame by default, with no preceding warmup frames.
Use ``--steps`` to request later frames. With neither
``--png`` nor ``--rrd``, the example opens Rerun.

``--scene`` accepts a USD scene containing a RenderProduct at
``/Render/Camera`` and an :ref:`LdrColor <camera-output-tables>` RenderVar at
``/Render/Camera/LdrColor``. The product's ``camera`` relationship must
target your Camera prim, and ``orderedVars`` must include that RenderVar.
These paths are required by this example script.

See :doc:`../sensors/configuration` for this setup. If adapting the USDA
example in the Inline Composition section of :doc:`../scene/loading_usd`,
rename its RenderProduct from ``DocsCamera`` to ``Camera`` beneath
``/Render``. The Camera prim itself can retain its name.

The following code loads the scene, overrides one mode, renders the requested frames,
and copies :ref:`LdrColor <camera-output-tables>` before releasing its mapping.

.. literalinclude:: ../../examples/python/gaussian-splats/main.py
   :language: python
   :start-after: # [snippet:gaussian-render-python]
   :end-before: # [/snippet:gaussian-render-python]
   :dedent:

See :doc:`../geometry/gaussian_splats` for the authoring contract and
:doc:`c_gaussian_splats` for the equivalent C runtime workflow.
