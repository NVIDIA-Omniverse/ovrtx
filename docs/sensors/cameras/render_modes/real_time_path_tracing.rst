.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Real-Time Path-Tracing
======================

Real-Time Path-Tracing (RTPT) is the default render mode. It produces high-quality images with accurate global illumination, reflections, and shadows using a cached path-tracing approach optimized for real-time performance.

.. code-block:: usda

   token omni:rtx:rendermode = "RealTimePathTracing"

Settings
--------

Sampling and Caching
~~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:cached:enabled = true``
     - Enables caching path-tracing results for improved performance at the cost of some accuracy.
   * - ``bool omni:rtx:rtpt:lightcache:cached:enabled = true``
     - Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
   * - ``bool omni:rtx:rtpt:ris:meshLights = false``
     - Enables direct illumination sampling of geometry with emissive materials.

Ray Bounces and Shading
~~~~~~~~~~~~~~~~~~~~~~~

``omni:rtx:rtpt:maxBounces``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maximum number of ray bounces for any ray type. Higher values give more accurate global illumination, but worse performance.

| Type: ``uint`` | Default: ``3``

.. grid:: 3
   :class-container: setting-comparison

   .. grid-item-card:: maxBounces = 2
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-2.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-2.0001.avif
      :link-type: url

   .. grid-item-card:: maxBounces = 3
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-3.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-3.0001.avif
      :link-type: url

   .. grid-item-card:: maxBounces = 23
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-23.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-23.0001.avif
      :link-type: url

``omni:rtx:rtpt:extraSpecularAndTransmissiveBounces``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Additional number of specular and transmission ray bounces beyond ``maxBounces``. Affects reflections and refractions through transparent materials like glass.

| Type: ``uint`` | Default: ``0``

..
   The comparisons below use ``maxBounces = 2``.

   .. grid:: 3
      :class-container: setting-comparison

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 0
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-0.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-0.0001.avif
         :link-type: url

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 2
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-2.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-2.0001.avif
         :link-type: url

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 23
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-23.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-23.0001.avif
         :link-type: url

Other Ray Bounce and Shading Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``uint omni:rtx:rtpt:maxVolumeBounces = 3``
     - Maximum number of ray bounces for SSS.
   * - ``bool omni:rtx:pt:fractionalCutoutOpacity = true``
     - If enabled, fractional cutout opacity values are treated as a measure of surface 'presence', resulting in a translucency effect similar to alpha-blending.
   * - ``float omni:rtx:rtpt:maxRoughness = 0.3``
     - Roughness threshold above which a surface is considered rough and rendered with performance-favoring approximations.
   * - ``float omni:rtx:rt:reflections:roughnessCacheThreshold = 0.3``
     - Roughness threshold above which a surface is considered rough and rendered with performance-favoring approximations.
   * - ``bool omni:rtx:rtpt:translucency:virtualMotion:enabled = true``
     - Enables motion vectors for translucent (refractive) objects, which can improve temporal rendering such as denoising but can reduce performance.

Firefly Filter
~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:fireflyFilter:enabled = true``
     - Enables the firefly filter.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSample = 3200.0``
     - Clamps the maximum ray intensity for glossy bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse = 3200.0``
     - Clamps the maximum ray intensity for diffuse bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxPerEmissiveUnexposedIntensity = 3200.0``
     - Clamps the maximum ray intensity for emissive contribution after primary bounce. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.

Gaussian Splatting
~~~~~~~~~~~~~~~~~~

See :doc:`../../../geometry/gaussian_splats` for particle-field authoring and runnable examples.

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:gaussian:accumulatedDepth:enabled = true``
     - When enabled, gaussian hit depth is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits, producing a more stable depth than the stochastic single-hit depth. Useful for reducing ghosting in DLSS-RR.
   * - ``bool omni:rtx:rtpt:gaussian:accumulatedAlbedo:enabled = true``
     - When enabled, gaussian SH0 albedo is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits and the result overrides the GBuffer diffuse albedo, which usually improves image quality.
   * - ``int omni:rtx:rtpt:gaussian:maxGaussiansToAccumulate = 48``
     - Total hit budget for gaussian depth/albedo accumulation. Values up to 48 use a single pass over the closest N hits. Values above 48 enable a multi-batch traversal that continues until the budget is reached, the 95% opacity threshold is hit, or no more candidates are found. Set to -1 for unlimited accumulation (stops only on opacity threshold or BVH exhaust). Set to 0 to disable accumulation entirely (depth/albedo accumulation settings are ignored).
   * - ``bool omni:rtx:rtpt:gaussian:nonStochastic:enabled = false``
     - When enabled, RTPT deterministically composites supported Gaussian splats for primary camera rays instead of using stochastic transparency. This requires inline Gaussian tracing. Pipeline fallback, secondary rays, spectral materials, and shadows remain stochastic. At most three overlapping Gaussian objects are composited.
