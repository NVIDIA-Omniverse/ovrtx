.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

.. _gaussian-splats:

Gaussian Splats
===============

Gaussian splats represent a scene with oriented, translucent ellipsoids.
Each splat has a position, rotation, scale, opacity, and radiance. Use them
to render captured appearance or procedurally authored particle fields.

.. figure:: ../img/gaussian-splats-modes.avif
   :alt: The same three colored Gaussian rings rendered with RTPT, PT, and Minimal
   :align: center

   *Left to right: RTPT, PT, and Minimal, with the same authored splats and camera.
   The modes differ in lighting, background, and image reconstruction.*

.. note::

   Gaussian splats store captured lighting in their radiance. Scene lights affect
   them through shadows rather than direct illumination: changing a light's
   intensity or color does not directly brighten or tint the splats, but scene
   objects can cast shadows onto them.

   Without a bound material, ``ParticleField3DGaussianSplat`` uses
   ``ParticleFieldEmissive``. To adjust brightness on an explicitly bound instance
   of this material, set ``inputs:emission_intensity`` on its shader. The default
   is ``1.0``; lower values dim the splats and higher values brighten them.

Converting 3DGS PLY Files to USD
--------------------------------

Use NVIDIA's `usd-convert-gsplat
<https://github.com/NVIDIA-Omniverse/usd-convert-gsplat>`_ to convert a 3D Gaussian
Splat (3DGS) ``.ply`` file to USD with a ``ParticleField3DGaussianSplat`` prim.
The input should contain 3DGS data, including scales, rotations, opacity, and
spherical harmonics, rather than only point positions or mesh geometry.

From your ``uv`` project directory, add the converter and OpenUSD Python bindings.
See :doc:`../python_api/getting_started` for the Python setup:

.. code-block:: console

   uv add usd-convert-gsplat usd-core

Convert your splat file to a binary USD file, replacing the example paths with
your own:

.. code-block:: console

   uv run python -m usd_convert_gsplat -i "scene.ply" -o "scene.usdc" --rotate-x 180

The optional ``--rotate-x 180`` applies a 180-degree rotation around the X axis.
Adjust or omit it to match your source data's orientation to your scene; this
rotation is not required for every dataset.

To render the converted asset, compose it with a camera and render-output
configuration. See the Inline Composition section of
:doc:`../scene/loading_usd` for a scene-wrapper example, and
:doc:`../sensors/configuration` for the RenderProduct and RenderVar setup.
See :doc:`../examples/python_gaussian_splats` for this example's scene
requirements and run commands.

Creating a Gaussian Splat Prim
------------------------------

Author a ``ParticleField3DGaussianSplat`` prim. Its schema supplies the
particle-field APIs; you do not need to apply them individually. Each
per-particle array must describe the same number of splats.

The following equivalent examples create one orange splat. The quaternion is
written with its real component first, and the scales are linear values in
scene units. The example uses degree-zero spherical harmonics (SH0), so the
color does not depend on viewing direction.

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

.. csv-table:: Splat attributes
   :header: "USD declaration", "Meaning"
   :widths: 45, 55
   :class: compact-table

   "``point3f[] positions``", "Particle centers in local scene units."
   "``quatf[] orientations``", "Normalized particle rotations; identity is (1, 0, 0, 0)."
   "``float3[] scales``", "Positive linear scale along each particle's local axis."
   "``float[] opacities``", "Peak opacity for each particle; use values from 0 to 1."
   "``int radiance:sphericalHarmonicsDegree = 3``", "Schema default; author 0 for the single-coefficient example shown here."
   "``float3[] radiance:sphericalHarmonicsCoefficients``", "RGB spherical-harmonic coefficients, grouped by particle. Degree 0 uses one float3 per particle."

For degree zero, convert linear RGB to a coefficient with
``SH0 = (RGB - 0.5) / 0.2820947918``. Do not put display-encoded RGB values
directly into the coefficient array. This example uses degree zero, with one
RGB coefficient per splat.

Render Modes
------------

Select the mode on the RenderProduct using ``omni:rtx:rendermode``.

.. list-table::
   :header-rows: 1
   :widths: 22 32 46

   * - Mode
     - Token
     - Example behavior
   * - Real-Time Path Tracing
     - ``RealTimePathTracing``
     - Renders the particle field; accumulate frames for stochastic transparency.
   * - Path Tracing
     - ``PathTracing``
     - Renders the same field with path-tracing accumulation and reconstruction.
   * - Minimal
     - ``MinimalRendering``
     - Use Full MDL and DLSS Ray Reconstruction as configured below. Lighting and background differ from RTPT/PT.

For Minimal, set both ``int omni:rtx:minimal:mode = 3`` (Full MDL) and
``int omni:rtx:minimal:dlss:mode = 2`` (DLSS Ray Reconstruction). Full MDL
renders the splats; Ray Reconstruction denoises their stochastic transparency.
Author the DLSS attribute explicitly; it is not declared in the generated RTX
settings schema.

For accumulated Gaussian depth and albedo settings, see
:doc:`../sensors/cameras/render_modes/real_time_path_tracing`.

Limitations
-----------

* A single frame can be noisy because transparency is stochastic. Warm up and
  inspect the result at the resolution and frame count your application uses.

Further Reading
---------------

* :doc:`../examples/python_gaussian_splats`
* :doc:`../examples/c_gaussian_splats`
