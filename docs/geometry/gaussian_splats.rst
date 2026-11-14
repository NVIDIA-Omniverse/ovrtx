.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

.. _gaussian-splats:

Gaussian Splats
===============

A ParticleField is a USD prim containing Gaussians (also called splats).
Each Gaussian is an oriented, translucent ellipsoid with a position, rotation,
scale, opacity, and radiance. Use a ParticleField to render captured appearance
or procedurally authored Gaussians.

.. figure:: ../img/gaussian-splats-modes.avif
   :alt: The same captured cactus rendered with RTPT, PT, and Minimal
   :align: center

   *Left to right: RTPT, PT, and Minimal, after 32 frames with the same captured ParticleField and camera.
   The modes differ in lighting, background, and image reconstruction.*

.. note::

   With the default emissive material, Gaussians store captured lighting
   in their radiance. Scene lights affect them through shadows rather than direct
   illumination: changing a light's
   intensity or color does not directly brighten or tint the Gaussians, but scene
   objects can cast shadows onto them.

   Without a bound material, ``ParticleField3DGaussianSplat`` uses
   ``ParticleFieldEmissive``. To adjust brightness on an explicitly bound instance
   of this material, set ``inputs:emission_intensity`` on its shader. The default
   is ``1.0``; lower values dim the Gaussians and higher values brighten them.

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

Convert your 3DGS file to a binary USD file, replacing the example paths with
your own:

.. code-block:: console

   uv run python -m usd_convert_gsplat -i "scene.ply" -o "scene.usdc" --rotate-x 180

The optional ``--rotate-x 180`` applies a 180-degree rotation around the X axis.
Adjust or omit it to match your source data's orientation to your scene; this
rotation is not required for every dataset.

To render the converted asset, compose it with a camera and render-output
configuration. See the Inline Composition section of
:doc:`../scene/loading_usd` for a scene-wrapper example, and
:doc:`../sensors/common/output_configuration` for the RenderProduct and RenderVar setup.
See :doc:`../examples/python_gaussian_splats` for this example's scene
requirements and run commands.

Creating a ParticleField
------------------------

Author a ParticleField using the ``ParticleField3DGaussianSplat`` prim type.
Its schema supplies the ParticleField APIs; you do not need to apply them individually. Each
per-Gaussian array must describe the same number of Gaussians.

The following equivalent examples create a ParticleField containing
one orange Gaussian. The quaternion is
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

.. csv-table:: Gaussian attributes
   :header: "USD declaration", "Meaning"
   :widths: 45, 55
   :class: compact-table

   "``point3f[] positions``", "Gaussian centers in local scene units."
   "``quatf[] orientations``", "Normalized Gaussian rotations; identity is (1, 0, 0, 0)."
   "``float3[] scales``", "Positive linear scale along each Gaussian's local axis."
   "``float[] opacities``", "Peak opacity for each Gaussian; use values from 0 to 1."
   "``int radiance:sphericalHarmonicsDegree = 3``", "Schema default; author 0 for the single-coefficient example shown here."
   "``float3[] radiance:sphericalHarmonicsCoefficients``", "RGB spherical-harmonic coefficients, grouped by Gaussian. Degree 0 uses one float3 per Gaussian."

For degree zero, convert linear RGB to a coefficient with
``SH0 = (RGB - 0.5) / 0.2820947918``. Do not put display-encoded RGB values
directly into the coefficient array. This example uses degree zero, with one
RGB coefficient per Gaussian.

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
     - Uses stochastic transparency by default; optional non-stochastic primary-ray compositing is described below.
   * - Path Tracing
     - ``PathTracing``
     - Renders the same field with path-tracing accumulation and reconstruction.
   * - Minimal
     - ``MinimalRendering``
     - Use Full MDL and DLSS Ray Reconstruction as configured below. Lighting and background differ from RTPT/PT.

For Minimal, set both ``int omni:rtx:minimal:mode = 3`` (Full MDL) and
``int omni:rtx:minimal:dlss:mode = 2`` (DLSS Ray Reconstruction). Full MDL
renders the Gaussians; Ray Reconstruction denoises their stochastic transparency.
Author the DLSS attribute explicitly; it is not declared in the generated RTX
settings schema.

For accumulated Gaussian depth and albedo settings, see
:doc:`../sensors/cameras/render_modes/real_time_path_tracing`.

Non-Stochastic Rendering
------------------------

RTPT can composite emissive Gaussians in a ParticleField on primary camera rays without
randomly accepting or rejecting each Gaussian for transparency. Enable
``omni:rtx:rtpt:gaussian:nonStochastic:enabled`` on the RenderProduct; its default
is ``false``. This reduces transparency noise without waiting for temporal
accumulation, at a performance cost compared with stochastic rendering. It does
not make lighting, shadows, or the entire image noise-free.

.. figure:: ../img/gaussian-splats-non-stochastic.avif
   :alt: Close-up of the cactus with non-stochastic rendering disabled and enabled
   :align: center

   *RTPT first frame through Camera_close: disabled (left), enabled (right).
   Both use the same scene and disable adaptive disocclusion sampling;
   only the non-stochastic attribute differs. Matching crops enlarged 3×
   without smoothing.*

The following overrides enable this mode on an existing ``/Render/Camera``
RenderProduct and disable incompatible adaptive disocclusion sampling:

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

Non-stochastic mode is only supported in Real-Time Path Tracing.
The non-stochastic path is for
``ParticleFieldEmissive``; it does not apply to the diffuse material below.

At most three overlapping ParticleFields are retained for primary-ray
compositing. Each field can contain many Gaussians. Fields are ordered by their
mean depth; Gaussians belonging to different fields are not interleaved.
Intersecting ParticleFields can therefore show ordering artifacts.

Diffuse Relighting
------------------

ovrtx supplies ``ParticleFieldSHDiffuse.mdl`` with its runtime materials, at
``bin/mdl/ParticleFieldSHDiffuse.mdl`` in the extracted SDK package.
You do not need to write an MDL material. Bind it to a ParticleField to
illuminate its Gaussians with scene lights in PT or RTPT. Unlike the default
emissive material, this material has no emission.
It derives diffuse albedo from the degree-zero spherical-harmonics coefficient
(SH0). Light intensity and color then affect the rendered Gaussians.

.. figure:: ../img/gaussian-splats-sh-diffuse.avif
   :alt: Cactus with captured emissive appearance and scene-lit SH diffuse material
   :align: center

   *RTPT after 32 frames through Camera: default emissive material (left),
   ParticleFieldSHDiffuse with normal tone mapping (right).
   The scene, camera, and studio lighting are shared.*

Captured illumination remains baked into SH0: this is not a method for recovering
unlit surface color from a captured scene, but can serve as a reasonable
approximation for many use cases.

The following overrides bind the packaged material to an existing
``/World/Splats`` ParticleField and select normal tone mapping on
``/Render/Camera``. The material has no exposed inputs; keep the SH coefficients
on the ParticleField itself:

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

These examples keep non-stochastic compositing disabled because diffuse Gaussians
use stochastic transparency. Accumulate frames as needed. See
:doc:`../examples/python_gaussian_splats` and
:doc:`../examples/c_gaussian_splats` for runnable variants of the same scene.

.. _gaussian-diffuse-material-source:

Supplied Material Source
~~~~~~~~~~~~~~~~~~~~~~~~

The supplied material derives diffuse albedo from SH0 and uses a diffuse
reflection BSDF. Its source is shown below and is also available as a
:download:`download <../_static/mdl/ParticleFieldSHDiffuse.mdl>`:

.. literalinclude:: ../_static/mdl/ParticleFieldSHDiffuse.mdl
   :language: c++
   :start-at: mdl 1.6;

Limitations
-----------

* With stochastic transparency, a single frame can be noisy. Warm up and
  inspect the result at the resolution and frame count your application uses.

Further Reading
---------------

* :doc:`../examples/python_gaussian_splats`
* :doc:`../examples/c_gaussian_splats`
