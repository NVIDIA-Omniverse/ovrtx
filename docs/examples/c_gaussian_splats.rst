.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: Gaussian Splats
==================

This example demonstrates two ParticleField rendering features using the same cactus scene:

* **Smoother Gaussians:** non-stochastic rendering reduces transparency noise in RTPT,
  making fine details smoother from the first frame.
* **Relighting:** ``ParticleFieldSHDiffuse.mdl`` lets scene lights illuminate the
  Gaussians using their captured color as diffuse albedo.

Smoother Gaussians with Non-Stochastic Rendering
------------------------------------------------

The close-up compares ``stochastic.usda`` and ``non_stochastic.usda`` through
``Camera_close``. Both use the default emissive material and identical settings
apart from ``omni:rtx:rtpt:gaussian:nonStochastic:enabled``.
Enabling it reduces the grain around the cactus spines without waiting for
multiple frames to accumulate, at a performance cost. Lighting and shadows can
still contain noise.

.. figure:: ../img/gaussian-splats-non-stochastic.avif
   :alt: Camera_close with non-stochastic compositing off and on
   :align: center

   *Camera_close, RTPT first frame: non-stochastic compositing off (left)
   and on (right). Matching crops enlarged 3× without smoothing.
   Only the non-stochastic attribute differs.*

Enable non-stochastic compositing on the RenderProduct. This feature requires
RTPT; disable adaptive disocclusion sampling, which would force stochastic
rendering:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/gaussian-splats/non_stochastic.usda
         :language: usda
         :start-after: # [snippet:doc-gaussian-non-stochastic]
         :end-before: # [/snippet:doc-gaussian-non-stochastic]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_gaussian_splats_usda.py
         :language: python
         :start-after: # [snippet:doc-gaussian-non-stochastic-python]
         :end-before: # [/snippet:doc-gaussian-non-stochastic-python]
         :dedent:

Relighting with the Diffuse MDL
-------------------------------

The wider view through ``Camera`` compares the default emissive appearance with
``sh_diffuse.usda`` under the same studio lighting. The default material displays
the captured appearance; ``ParticleFieldSHDiffuse`` uses the SH0 color as diffuse
albedo so scene lights can shade the cactus and pot.

.. figure:: ../img/gaussian-splats-sh-diffuse.avif
   :alt: Camera with default emissive and SH diffuse Gaussian materials
   :align: center

   *Camera, RTPT after 32 frames: default emissive material (left) and
   ParticleFieldSHDiffuse with normal tone mapping (right).*

ovrtx supplies ``ParticleFieldSHDiffuse.mdl`` with its runtime materials, at
``bin/mdl/ParticleFieldSHDiffuse.mdl`` in the extracted SDK package. You do not
need to write an MDL material; see :ref:`gaussian-diffuse-material-source`. The snippet below references and binds the
supplied material to the ParticleField and enables normal tone mapping.
Diffuse relighting works in PT and RTPT and uses stochastic transparency.
Captured lighting remains in SH0, so this does not recover unlit surface color.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/gaussian-splats/sh_diffuse.usda
         :language: usda
         :start-after: # [snippet:doc-gaussian-sh-diffuse]
         :end-before: # [/snippet:doc-gaussian-sh-diffuse]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_gaussian_splats_usda.py
         :language: python
         :start-after: # [snippet:doc-gaussian-sh-diffuse-python]
         :end-before: # [/snippet:doc-gaussian-sh-diffuse-python]
         :dedent:

Run the Scenes
--------------

Follow the :doc:`C API setup <../c_api/getting_started>` and
:doc:`GPU requirements <../driver_requirements>`. From the ovrtx repository root,
build and run the example for your platform:

.. tab-set::

   .. tab-item:: Windows (PowerShell)

      .. code-block:: pwsh

         cd examples/c/gaussian-splats
         cmake -B build
         cmake --build build --config Release
         .\build\static\Release\gaussian-splats.exe `
           ../../python/gaussian-splats/non_stochastic.usda non-stochastic.png
         .\build\shared\Release\gaussian-splats-dynamic.exe `
           ../../python/gaussian-splats/sh_diffuse.usda sh-diffuse.png

   .. tab-item:: Linux

      .. code-block:: bash

         cd examples/c/gaussian-splats
         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build
         ./build/static/gaussian-splats \
           ../../python/gaussian-splats/non_stochastic.usda non-stochastic.png
         ./build/shared/gaussian-splats-dynamic \
           ../../python/gaussian-splats/sh_diffuse.usda sh-diffuse.png

Both loaders accept the same scene layers. Use ``stochastic.usda`` for the
close-up with non-stochastic rendering disabled, or ``gaussian_splats.usda`` for
the wider view with the default emissive material.

The C example saves one frame. The diffuse comparison above was rendered with
32 frames using the :doc:`Python example <python_gaussian_splats>`.

Scene and Source
----------------

The scene references `cactus-100.usdc
<https://huggingface.co/buckets/nvidia/ovrtx-storage/resolve/cactus-100.usdc>`__
and requires internet access on first load. The capture is by
`Steam Studio <https://www.steam-studio.jp>`__, released under CC0-1.0;
see the `original dataset <https://note.com/steam_studio/n/ne9736d94f162>`__.

See :doc:`../geometry/gaussian_splats` for the Gaussian attribute layout,
render-mode support, and feature limitations.
