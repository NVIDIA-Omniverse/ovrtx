.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-render-modes-minimal:

Minimal
=======

Minimal mode uses lightweight shading for high-throughput rendering. Use it for
segmentation masks, bounding-box visualization, or reinforcement learning loops
that do not need full path-traced lighting.

.. code-block:: usda

   token omni:rtx:rendermode = "MinimalRendering"

.. _sensors-cameras-render-modes-minimal-lighting:

Lighting Behavior
-----------------

Minimal mode only respects the first ``DistantLight`` found in the scene, and shadows from that light are hard shadows. This restriction keeps Minimal mode fast and stable for speed-of-light rendering workloads.

Other light types, such as ``DomeLight``, are not used for Minimal mode lighting. If the scene has no ``DistantLight``, Minimal mode falls back to a single camera light.

For improved visibility without adding scene lights, use ambient lighting through the ``omni:rtx:sceneDb:ambientLightColor`` and ``omni:rtx:sceneDb:ambientLightIntensity`` attributes listed below, or disable shadows with ``omni:rtx:minimal:castShadows``.

.. _sensors-cameras-render-modes-minimal-settings:

Settings
--------

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``int omni:rtx:minimal:mode = 2``
     - Selects the shading mode.

       | 0: No Rendering -- no path tracing is performed and LdrColor is black; use when only data outputs such as depth and albedo are required.
       | 1: Constant Diffuse -- uses a single constant color for all surfaces.
       | 2: Texture Diffuse -- uses diffuse texture colors.
       | 3: Diffuse/Glossy/Emission -- full material evaluation with diffuse, glossy, and emission.
   * - ``color3f omni:rtx:minimal:constantColor = (0.5, 0.5, 0.5)``
     - The color to use in Constant Diffuse shading mode.
   * - ``bool omni:rtx:minimal:castShadows = true``
     - Global toggle to cast hard shadows from the first ``DistantLight`` in Minimal render mode.
   * - ``color3f omni:rtx:sceneDb:ambientLightColor = (0, 0, 0)``
     - Color of the global ambient environment lighting.
   * - ``float omni:rtx:sceneDb:ambientLightIntensity = 0``
     - Brightness of the global ambient environment lighting. A value of 0 disables ambient lighting.

.. _minimal-anti-aliasing-dlss:

.. _sensors-cameras-render-modes-minimal-dlss:

Anti-Aliasing and DLSS
----------------------

Anti-aliasing reduces jagged edges and shimmer in rendered images. Minimal mode
supports DLSS Super Resolution (DLSS-SR) for image upscaling and anti-aliasing,
and DLSS Ray Reconstruction (DLSS-RR) for upscaling, anti-aliasing, and denoising.
DLSS is optional and disabled when ``omni:rtx:minimal:dlss:mode`` is unset or zero.

Use DLSS-SR for textured geometry when you want smoother edges or a larger output
image from a lower internal render resolution. Use DLSS-RR when the image also
needs denoising, particularly for Gaussians. Rendering Gaussians in
Minimal mode requires ``omni:rtx:minimal:mode = 3`` for full material evaluation;
DLSS-SR does not provide their denoising.

Both controls belong to ``OmniRtxSettingsMinimalAPI_1``. Configure them on the
**RenderProduct** that produces the image. These are Minimal-specific controls;
``omni:rtx:post:dlss:execMode`` and the
Path Tracing pixel filter do not select Minimal's DLSS behavior.

.. csv-table:: DLSS controls
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``int omni:rtx:minimal:dlss:mode = 0``", "Selects the image reconstruction method: ``0`` disables DLSS, ``1`` enables DLSS-SR, and ``2`` enables DLSS-RR. Author this integer attribute explicitly to enable DLSS."
   "``token omni:rtx:minimal:dlss:execMode = ""auto""``", "Selects how the internal render resolution is chosen when DLSS is enabled. The output resolution remains the RenderProduct's ``resolution``."

Choose one of the following execution modes:

.. csv-table:: Resolution modes
   :header: "Token", "Behavior"
   :widths: 25, 75
   :class: compact-table

   "``auto``", "Selects a preset based on the output resolution."
   "``performance``", "Uses a lower internal resolution to favor rendering throughput."
   "``balanced``", "Balances internal resolution and image quality."
   "``quality``", "Uses a higher internal resolution than Balanced or Performance."
   "``rtxaa``", "Selects DLAA: anti-aliasing at native output resolution, without upscaling. Keep DLSS enabled with mode ``1`` or ``2``."

.. figure:: ../../../img/sensors/camera/minimal-dlss-comparison.avif
   :alt: Matching enlarged crops of Jetbot and Kaya with DLSS disabled, DLSS-SR Quality, DLSS-RR Quality, and DLAA.
   :width: 100%

   *Matching 170 × 112 crops of Jetbot (left) and Kaya (right) from
   ovrtx-robot-lineup.usda, captured at frame 32 with 1280 × 720 output.
   DLSS smooths the robot silhouettes and reconstructs fine details. The camera,
   Texture Diffuse shading, and disabled shadows stay the same across modes.
   Crops are enlarged 3× without additional filtering.*

The following equivalent USDA and OpenUSD Python snippets configure a
1280 × 720 RenderProduct with DLSS-SR and the Quality preset. Both controls are
authored before loading the scene into the renderer; the same USD configuration
works with the ovrtx Python and C APIs.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../examples/python/minimal-dlss/minimal_dlss.usda
         :language: usda
         :start-after: # [snippet:doc-minimal-dlss-render-product]
         :end-before: # [/snippet:doc-minimal-dlss-render-product]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../tests/docs/usd/test_minimal_dlss.py
         :language: python
         :start-after: # [snippet:doc-minimal-dlss-render-product-python]
         :end-before: # [/snippet:doc-minimal-dlss-render-product-python]
         :dedent:

DLSS uses information from earlier frames. Keep the renderer alive and render
several frames before capturing a comparison image. Compare the same scene,
camera, output resolution, and shading mode so that changes in
:ref:`LdrColor <camera-output-tables>` show the effect of DLSS. Denoising and
reconstruction add processing work; a lower internal resolution does not
guarantee a speedup for every scene or output size.

See the :doc:`Minimal DLSS example <../../../examples/python_minimal_dlss>` for
a runnable scene, image capture, and Rerun output. The
:doc:`C example <../../../examples/c_minimal_dlss>` loads the same scene.

Related
-------

- :doc:`../render_modes`
- :doc:`../outputs`
