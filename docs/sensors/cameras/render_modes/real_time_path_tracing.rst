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
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:rtpt:cached:enabled``

       Enables caching path-tracing results for improved performance at the cost of some accuracy.
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:lightcache:cached:enabled``

       Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:ris:meshLights``

       Enables direct illumination sampling of geometry with emissive materials.
     - ``bool``
     - ``false``

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

``omni:rtx:rtpt:maxSpecularAndTransmissionBounces``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maximum number of ray bounces for specular and transmission. Affects reflections and refractions through transparent materials like glass.

| Type: ``uint`` | Default: ``3``

.. grid:: 3
   :class-container: setting-comparison

   .. grid-item-card:: maxSpecularAndTransmissionBounces = 2
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-2.0001.avif
      :link: ../../../_images/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-2.0001.avif
      :link-type: url

   .. grid-item-card:: maxSpecularAndTransmissionBounces = 3
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-3.0001.avif
      :link: ../../../_images/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-3.0001.avif
      :link-type: url

   .. grid-item-card:: maxSpecularAndTransmissionBounces = 23
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-23.0001.avif
      :link: ../../../_images/settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-23.0001.avif
      :link-type: url

Other Ray Bounce and Shading Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:rtpt:maxVolumeBounces``

       Maximum number of ray bounces for SSS.
     - ``uint``
     - ``3``
   * - ``omni:rtx:pt:fractionalCutoutOpacity``

       If enabled, fractional cutout opacity values are treated as a measure of surface 'presence', resulting in a translucency effect similar to alpha-blending.
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:maxRoughness``

       Roughness threshold above which a surface is considered rough and rendered with performance-favoring approximations.
     - ``float``
     - ``0.3``
   * - ``omni:rtx:rt:reflections:roughnessCacheThreshold``

       Roughness threshold above which a surface is considered rough and rendered with performance-favoring approximations.
     - ``float``
     - ``0.3``
   * - ``omni:rtx:rtpt:translucency:virtualMotion:enabled``

       Enables motion vectors for translucent (refractive) objects, which can improve temporal rendering such as denoising but can reduce performance.
     - ``bool``
     - ``true``

Firefly Filter
~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:rtpt:fireflyFilter:enabled``
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSample``

       Clamps the maximum ray intensity for glossy bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``
   * - ``omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse``

       Clamps the maximum ray intensity for diffuse bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``
   * - ``omni:rtx:rtpt:fireflyFilter:maxPerEmissiveUnexposedIntensity``

       Clamps the maximum ray intensity for emissive contribution after primary bounce. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``

Gaussian Splatting
~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:rtpt:gaussian:accumulatedDepth:enabled``

       When enabled, gaussian hit depth is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits, producing a more stable depth than the stochastic single-hit depth. Useful for reducing ghosting in DLSS-RR.
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:gaussian:accumulatedAlbedo:enabled``

       When enabled, gaussian SH0 albedo is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits and the result overrides the GBuffer diffuse albedo, which usually improves image quality.
     - ``bool``
     - ``true``
   * - ``omni:rtx:rtpt:gaussian:maxGaussiansToAccumulate``

       Total hit budget for gaussian depth/albedo accumulation. Values up to 48 use a single pass over the closest N hits. Values above 48 enable a multi-batch traversal that continues until the budget is reached, the 95% opacity threshold is hit, or no more candidates are found. Set to -1 for unlimited accumulation (stops only on opacity threshold or BVH exhaust). Set to 0 to disable accumulation entirely (depth/albedo accumulation settings are ignored).
     - ``int``
     - ``48``
