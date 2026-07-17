.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Outputs
=======

The tables below list the RenderVar source names available for camera sensors,
grouped by render mode. Use the **sourceName** value as the ``sourceName``
attribute on a ``RenderVar`` prim. Shapes are channel-last DLPack tensor shapes.
Click any example image to enlarge it.

.. note::

   The example images for non-color outputs have been remapped for easier visualization and do not represent raw output values.
   All output example images in the table were generated from the ``semantic-segmentation`` example.

.. tab-set::

   .. tab-item:: Real-Time Path-Tracing

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 18 9 9 14 35 15

         * - ``sourceName``
           - Format
           - Type
           - Shape
           - Description
           - Example
         * - ``LdrColor``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Tone-mapped color in sRGB space. Standard final image output suitable for display or saving as PNG/JPEG.
           - .. image:: ../../img/aovs/rt2/LdrColor.avif
                :width: 100%
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear-space HDR color preserving full scene luminance. Use for post-processing, compositing, or linear-space workflows.
           - .. image:: ../../img/aovs/rt2/HdrColor.avif
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.
           - .. image:: ../../img/aovs/rt2/NormalSD.avif
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Unitless depth mapped from 1 (near clip plane) to 0 (far clip plane). Known C API issue: currently returns all zeros through C readback.
           - .. image:: ../../img/aovs/rt2/DepthSD.avif
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters.
           - .. image:: ../../img/aovs/rt2/DistanceToCameraSD.avif
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters.
           - .. image:: ../../img/aovs/rt2/DistanceToImagePlaneSD.avif
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).
           - .. image:: ../../img/aovs/rt2/DiffuseAlbedoSD.avif
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units.
           - .. image:: ../../img/aovs/rt2/Camera3dPositionSD.avif
                :width: 100%
         * - ``SemanticSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Per-pixel semantic ID. Decode ``SemanticIdMap`` to map each integer ID to its semantic label string.
           - .. image:: ../../img/aovs/rt2/SemanticSegmentation.avif
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - uint8
           - Buffer
           - Packed metadata buffer mapping semantic IDs to label strings. Each entry contains ``uint32 id[4]``,
             label length, and label offset, followed by packed label bytes and a trailing entry count.
           - N/A

   .. tab-item:: Path Tracing

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 18 9 9 14 35 15

         * - ``sourceName``
           - Format
           - Type
           - Shape
           - Description
           - Example
         * - ``LdrColor``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Tone-mapped color in sRGB space.
           -
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear-space HDR color preserving full scene luminance.
           -

      .. note::

         Additional outputs for the Path Tracing mode will be documented here as they become available.

   .. tab-item:: Minimal

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 18 9 9 14 35 15

         * - ``sourceName``
           - Format
           - Type
           - Shape
           - Description
           - Example
         * - ``LdrColor``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Tone-mapped color in sRGB space.
           -
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear-space HDR color preserving full scene luminance.
           -

      .. note::

         Additional outputs for the Minimal mode will be documented here as they become available.
