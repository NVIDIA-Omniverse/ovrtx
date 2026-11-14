.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Gaussian Splats
=======================

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

Run the Comparisons
-------------------

Follow the :doc:`Python setup <../python_api/getting_started>` and
:doc:`GPU requirements <../driver_requirements>`, then run from the ovrtx
repository root:

.. code-block:: console

   cd examples/python/gaussian-splats
   uv run main.py --scene stochastic.usda --png _output/stochastic.png
   uv run main.py --scene non_stochastic.usda --png _output/non-stochastic.png
   uv run main.py --scene gaussian_splats.usda --steps 32 --png _output/emissive.png
   uv run main.py --scene sh_diffuse.usda --steps 32 --png _output/sh-diffuse.png

RTPT is the default. The first two commands render one frame; the material
comparison renders 32 frames. Add ``--mode pt`` to render the diffuse scene in PT.
The first run may take longer while shaders compile.

Scene and Source
----------------

The scene references `cactus-100.usdc
<https://huggingface.co/buckets/nvidia/ovrtx-storage/resolve/cactus-100.usdc>`__
and requires internet access on first load. The capture is by
`Steam Studio <https://www.steam-studio.jp>`__, released under CC0-1.0;
see the `original dataset <https://note.com/steam_studio/n/ne9736d94f162>`__.

See :doc:`../sensors/common/output_configuration` for this setup. If adapting the USDA
example in the Inline Composition section of :doc:`../scene/loading_usd`,
rename its RenderProduct from ``DocsCamera`` to ``Camera`` beneath
``/Render``. The Camera prim itself can retain its name.

See :doc:`../geometry/gaussian_splats` for the Gaussian attribute layout,
render-mode support, and feature limitations.
