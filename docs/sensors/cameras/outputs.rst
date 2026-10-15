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
Click any example image to enlarge it. Buffer examples are decoded illustrations,
not raw image outputs.

.. note::

   The example images for non-color outputs have been remapped for easier visualization
   and do not represent raw output values. All output example images in the table were
   generated from the ``semantic-segmentation`` example.

   Real-Time Path-Tracing and Minimal use 50 warmup frames; Path Tracing uses one frame
   at 128 samples per pixel. The robots then move for a separate motion capture, whose
   hue shows direction and brightness shows displacement (20 pixels reaches full brightness).

   Bounding-box overlays show only robot geometry: raw box outputs show individual parts,
   while semantic box outputs show one aggregate box per top-level robot. Colors distinguish
   robots. 3D corners are transformed to world space and projected using ``CameraParams``.

   Occlusion colors loose part boxes from green (visible) to red (occluded); invalid ratios
   are omitted.

   ID-map examples pair an annotated scene with decoded metadata; delta examples use their
   first-frame entries.

.. _camera-output-tables:

.. tab-set::

   .. tab-item:: Real-Time Path-Tracing

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 20 10 10 12 23 25

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

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/NormalSD.avif
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated.** Unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane).
             Use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DepthSD.avif
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DistanceToCameraSD.avif
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DistanceToImagePlaneSD.avif
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DiffuseAlbedoSD.avif
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/Camera3dPositionSD.avif
                :width: 100%
         * - ``TargetMotionSD``
           - XYZW
           - float32
           - ``(H, W, 4)``
           - Backward screen-space displacement in pixels: add XY to the current pixel position to find its previous-frame position.
             Z is the previous-frame occlusion flag; W indicates a geometric hit within the occlusion-check range.
             Invalid correspondences are ``(-1, -1, -1, -1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/TargetMotionSD.avif
                :alt: Robot motion with direction shown as hue and displacement shown as brightness
                :width: 100%
         * - ``SemanticSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Per-pixel semantic ID. Decode ``SemanticIdMap`` to map each integer ID to its semantic label string.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/SemanticSegmentation.avif
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - uint8
           - Buffer
           - Packed metadata buffer mapping semantic IDs to label strings. Each entry contains ``uint32 id[4]``,
             label length, and label offset, followed by packed label bytes and a trailing entry count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabelled hits are ``(0, 0, 0, 1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/SemanticInstanceSegmentation.avif
                :alt: Robot lineup SemanticInstanceSegmentation visualization
                :width: 100%
         * - ``StableIdSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable geometry-instance ID per pixel. The four words form one identifier, including its subset component. Background is all zeros.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/StableIdSegmentation.avif
                :alt: Robot lineup StableIdSegmentation visualization
                :width: 100%
         * - ``NonStableInstanceSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabelled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance visible-pixel bounds. Each 24-byte record contains instance/tile IDs and integer pixel bounds. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance 2D bounds including occluded geometry. Same 24-byte layout as tight boxes. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3DValues
           - uint8
           - ``(B,)``
           - Per-instance local 3D extents and a transform to world space. Each record is 96 bytes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - Visible-pixel bounds grouped by semantic instance. Each 48-byte record contains stable instance and semantic IDs plus pixel bounds. Read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - 2D bounds including occluded geometry, grouped by semantic instance. Same layout and trailing count as semantic tight boxes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3DValues
           - uint8
           - ``(B,)``
           - Local 3D extents and world transform grouped by semantic instance. Each record is 120 bytes; read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - OcclusionValues
           - uint8
           - ``(B,)``
           - Per-instance occluded fraction in [0, 1]. A ratio of -1 means no sampled hits. Each 12-byte record contains instance/tile IDs and a float32 ratio.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/rt2/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdToken
           - uint8
           - ``(B,)``
           - Runtime instance IDs mapped to opaque prim handles, prototype indices and instancer indices. A 24-byte header precedes 24-byte records.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/rt2/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - uint32 array
           - uint8
           - ``(B,)``
           - Runtime-instance-to-semantic-instance lookup. Reinterpret the byte buffer as uint32 indices; 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/rt2/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New stable-ID/prim-path entries since the last generated delta. The first frame includes scene-creation entries. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New semantic-ID/label entries since the last generated delta. Same packed layout as ``SemanticIdMap``. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - uint8
           - ``(260,)``
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens parameters.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/rt2/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - ID pairs
           - uint8
           - ``(B,)``
           - Stable semantic-instance IDs mapped to semantic label IDs. Each 32-byte record contains uint32 stableId[4] followed by uint32 semanticId[4]. No trailing count.

             :ref:`Python/C decoding <sd-decode-id-pairs>`.
           - .. image:: ../../img/aovs/rt2/StableIdSemanticIdMap.avif
                :alt: Decoded StableIdSemanticIdMap robot lineup illustration
                :width: 100%
   .. tab-item:: Path Tracing

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 20 10 10 12 23 25

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
           - Tone-mapped sRGB color; uint8 channels decode to [0, 1]. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/LdrColor.avif
                :width: 100%
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear HDR beauty color. Convert float16 to float32 before processing. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/HdrColor.avif
                :width: 100%
         * - ``PtDirectIllumation``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct illumination. The source name intentionally uses the renderer spelling ``Illumation``. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtDirectIllumation.avif
                :width: 100%
         * - ``PtGlobalIllumination``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Indirect illumination from bounced light. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtGlobalIllumination.avif
                :width: 100%
         * - ``PtReflections``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Reflected radiance. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtReflections.avif
                :width: 100%
         * - ``PtRefractions``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Transmitted radiance. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtRefractions.avif
                :width: 100%
         * - ``PtSubsurfaceScattering``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Subsurface-scattered radiance. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtSubsurfaceScattering.avif
                :width: 100%
         * - ``PtSelfIllumination``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Surface emission. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtSelfIllumination.avif
                :width: 100%
         * - ``PtPreDenoisedResult``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Accumulated radiance before denoising. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtPreDenoisedResult.avif
                :width: 100%
         * - ``PtWorldNormal``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space geometric normal in XYZ, averaged across samples; edges can have length below one. Display [-1, 1] as [0, 1]. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtWorldNormal.avif
                :width: 100%
         * - ``PtWorldPos``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space hit position in XYZ, in scene units. The preview rescales each coordinate. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtWorldPos.avif
                :width: 100%
         * - ``PtViewNormal``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - View-space normal in XYZ, averaged across samples. Display [-1, 1] as [0, 1]. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtViewNormal.avif
                :width: 100%
         * - ``PtZDepth``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Normalized ray-hit distance, clamped to [0, 1] using the configured PT depth range; repeated in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtZDepth.avif
                :width: 100%
         * - ``PtDiffuseFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Diffuse material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtDiffuseFilter.avif
                :width: 100%
         * - ``PtReflectionFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Reflection material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtReflectionFilter.avif
                :width: 100%
         * - ``PtRefractionFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Transmission material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtRefractionFilter.avif
                :width: 100%
         * - ``PtLuminance``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - RGB radiance in RGB rendering; spectral rendering stores CIE Y in each RGB channel. The preview log-compresses values and scales them to the 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtLuminance.avif
                :width: 100%
         * - ``PtIlluminance``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - RGB irradiance at the first surface, evaluated with a unit Lambertian material. The preview log-compresses values and scales them to the 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtIlluminance.avif
                :width: 100%
         * - ``PtMotion``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - XY screen displacement in pixels; Z change in view-space depth. W is 1. Motion is captured after moving the robots. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtMotion.avif
                :width: 100%
         * - ``PtMultiMatte0`` – ``PtMultiMatte7``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Each RGBA component holds independent coverage for a selected geometry or material ID, from 0 to 1.
             Configure ``omni:rtx:pt:multimatte:rId``, ``gId``, ``bId``, ``aId`` and their
             ``rIsMat``, ``gIsMat``, ``bIsMat``, ``aIsMat`` flags on each RenderVar.
             Omitted IDs and -1 disable components. Requests determine allocation, up to eight outputs / 32 masks.
             Geometry IDs use ``primvars:multimatte_id``; material IDs use ``multimatte_id`` on the material.
             The preview combines RGB slices of outputs 0–3; the grey strip shows their full-frame alpha masks.
             Labels list RGBA selectors (G = geometry, M = material).
             See :doc:`../../examples/python_semantic_segmentation` and
             :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/MultiMatte.avif
                :width: 100%
         * - Light Path Expressions
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Up to nine expression outputs, authored with ``sourceType = "lpe"`` and the expression as ``sourceName``.
             The preview combines vertical slices from slots 0–8, left to right:
             ``E.*L``, ``E<RD>.*L``, ``E<RG>.*L``, ``E<TD>.*L``, ``E<TG>.*L``,
             ``E<RD>L``, ``E<RG>L``, ``E<RD>.+L``, ``E<RG>.+L``.
             See :doc:`light_path_expressions` and :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/LightPathExpressions.avif
                :width: 100%
         * - ``BumpNormal``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space shading normal, including material bump, in XYZ. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/BumpNormal.avif
                :width: 100%
         * - ``BumpNormalResearch``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Half-precision shading-normal diagnostic. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/BumpNormalResearch.avif
                :width: 100%
         * - ``DiffuseAlbedo``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse material RGB color, stored as UNORM bytes. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DiffuseAlbedo.avif
                :width: 100%
         * - ``SpecularAlbedo``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Specular material RGB color, stored as UNORM bytes. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/SpecularAlbedo.avif
                :width: 100%
         * - ``DepthLinearized``
           - Scalar
           - float32
           - ``(H, W, 1)``
           - Linear view-space depth in scene units. Ignore the float32 maximum-value miss sentinel. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DepthLinearized.avif
                :width: 100%
         * - ``Motion2dXYZ``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - XY screen displacement in pixels and Z view-depth change; W is 1. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dXYZ.avif
                :width: 100%
         * - ``Motion2dDilated``
           - XY
           - float32
           - ``(H, W, 2)``
           - Dilated screen displacement in pixels, in XY. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dDilated.avif
                :width: 100%
         * - ``Motion2dXYZDilated``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - Dilated XY screen displacement in pixels and Z view-depth change; W is 1. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dXYZDilated.avif
                :width: 100%
         * - ``MotionWorld``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space displacement in XYZ, in scene units; W is 1. The preview shows XY direction and scales magnitude to the captured 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/MotionWorld.avif
                :width: 100%
         * - ``EmissionAndForegroundMask``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - RGB surface emission and W foreground mask. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/EmissionAndForegroundMask.avif
                :width: 100%
         * - ``Roughness``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Material roughness in the blue channel, stored as a UNORM byte. The preview displays blue as grayscale. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Roughness.avif
                :width: 100%
         * - ``DisocclusionMask``
           - Scalar
           - float16
           - ``(H, W, 1)``
           - Disocclusion mask in [0, 1]. The preview displays it directly as grayscale. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DisocclusionMask.avif
                :width: 100%
         * - ``ViewspacePosition``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - View-space position in XYZ, in scene units. The preview rescales each coordinate. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/ViewspacePosition.avif
                :width: 100%
         * - ``XRDepth``
           - Scalar
           - float32
           - ``(H, W, 1)``
           - Normalized reversed clip depth for XR composition. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/XRDepth.avif
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/NormalSD.avif
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated.** Unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane).
             Use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DepthSD.avif
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DistanceToCameraSD.avif
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DistanceToImagePlaneSD.avif
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DiffuseAlbedoSD.avif
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/Camera3dPositionSD.avif
                :width: 100%
         * - ``TargetMotionSD``
           - XYZW
           - float32
           - ``(H, W, 4)``
           - Backward screen-space displacement in pixels: add XY to the current pixel position to find its previous-frame position.
             Z is the previous-frame occlusion flag; W indicates a geometric hit within the occlusion-check range.
             Invalid correspondences are ``(-1, -1, -1, -1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/TargetMotionSD.avif
                :alt: Robot motion with direction shown as hue and displacement shown as brightness
                :width: 100%
         * - ``SemanticSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Per-pixel semantic ID. Decode ``SemanticIdMap`` to map each integer ID to its semantic label string.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/SemanticSegmentation.avif
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - uint8
           - Buffer
           - Packed metadata buffer mapping semantic IDs to label strings. Each entry contains ``uint32 id[4]``,
             label length, and label offset, followed by packed label bytes and a trailing entry count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabelled hits are ``(0, 0, 0, 1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/SemanticInstanceSegmentation.avif
                :alt: Robot lineup SemanticInstanceSegmentation visualization
                :width: 100%
         * - ``StableIdSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable geometry-instance ID per pixel. The four words form one identifier, including its subset component. Background is all zeros.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/StableIdSegmentation.avif
                :alt: Robot lineup StableIdSegmentation visualization
                :width: 100%
         * - ``NonStableInstanceSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabelled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance visible-pixel bounds. Each 24-byte record contains instance/tile IDs and integer pixel bounds. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance 2D bounds including occluded geometry. Same 24-byte layout as tight boxes. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3DValues
           - uint8
           - ``(B,)``
           - Per-instance local 3D extents and a transform to world space. Each record is 96 bytes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - Visible-pixel bounds grouped by semantic instance. Each 48-byte record contains stable instance and semantic IDs plus pixel bounds. Read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - 2D bounds including occluded geometry, grouped by semantic instance. Same layout and trailing count as semantic tight boxes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3DValues
           - uint8
           - ``(B,)``
           - Local 3D extents and world transform grouped by semantic instance. Each record is 120 bytes; read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - OcclusionValues
           - uint8
           - ``(B,)``
           - Per-instance occluded fraction in [0, 1]. A ratio of -1 means no sampled hits. Each 12-byte record contains instance/tile IDs and a float32 ratio.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/pt/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdToken
           - uint8
           - ``(B,)``
           - Runtime instance IDs mapped to opaque prim handles, prototype indices and instancer indices. A 24-byte header precedes 24-byte records.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/pt/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - uint32 array
           - uint8
           - ``(B,)``
           - Runtime-instance-to-semantic-instance lookup. Reinterpret the byte buffer as uint32 indices; 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/pt/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New stable-ID/prim-path entries since the last generated delta. The first frame includes scene-creation entries. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New semantic-ID/label entries since the last generated delta. Same packed layout as ``SemanticIdMap``. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - uint8
           - ``(260,)``
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens parameters.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/pt/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - ID pairs
           - uint8
           - ``(B,)``
           - Stable semantic-instance IDs mapped to semantic label IDs. Each 32-byte record contains uint32 stableId[4] followed by uint32 semanticId[4]. No trailing count.

             :ref:`Python/C decoding <sd-decode-id-pairs>`.
           - .. image:: ../../img/aovs/pt/StableIdSemanticIdMap.avif
                :alt: Decoded StableIdSemanticIdMap robot lineup illustration
                :width: 100%

      The LPE row uses expression source names with ``sourceType = "lpe"``.
      Other rows use the default raw source type.

   .. tab-item:: Minimal

      .. rst-class:: compact-table aov-table

      .. list-table::
         :header-rows: 1
         :widths: 20 10 10 12 23 25

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
           - Simple-shaded color in sRGB space. Standard final image output suitable for display or saving as PNG/JPEG.
           - .. image:: ../../img/aovs/minimal/LdrColor.avif
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/NormalSD.avif
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated.** Unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane).
             Use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DepthSD.avif
                :width: 100%
         * - ``Depth`` / ``XRDepth``
           - Z
           - float32
           - ``(H, W, 1)``
           - Unitless reversed clip depth, from 1 (near clip plane) to 0 (far clip plane).
             Both names expose the same depth values as ``DepthSD`` in Minimal mode.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/Depth.avif
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DistanceToCameraSD.avif
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DistanceToImagePlaneSD.avif
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DiffuseAlbedoSD.avif
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/Camera3dPositionSD.avif
                :width: 100%
         * - ``TargetMotionSD``
           - XYZW
           - float32
           - ``(H, W, 4)``
           - Backward screen-space displacement in pixels: add XY to the current pixel position to find its previous-frame position.
             Z is the previous-frame occlusion flag; W indicates a geometric hit within the occlusion-check range.
             Invalid correspondences are ``(-1, -1, -1, -1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/TargetMotionSD.avif
                :alt: Robot motion with direction shown as hue and displacement shown as brightness
                :width: 100%
         * - ``SemanticSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Per-pixel semantic ID. Decode ``SemanticIdMap`` to map each integer ID to its semantic label string.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/SemanticSegmentation.avif
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - uint8
           - Buffer
           - Packed metadata buffer mapping semantic IDs to label strings. Each entry contains ``uint32 id[4]``,
             label length, and label offset, followed by packed label bytes and a trailing entry count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabelled hits are ``(0, 0, 0, 1)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/SemanticInstanceSegmentation.avif
                :alt: Robot lineup SemanticInstanceSegmentation visualization
                :width: 100%
         * - ``StableIdSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable geometry-instance ID per pixel. The four words form one identifier, including its subset component. Background is all zeros.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/StableIdSegmentation.avif
                :alt: Robot lineup StableIdSegmentation visualization
                :width: 100%
         * - ``NonStableInstanceSegmentation``
           - ID
           - uint32
           - ``(H, W, 1)``
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabelled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance visible-pixel bounds. Each 24-byte record contains instance/tile IDs and integer pixel bounds. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2DValues
           - uint8
           - ``(B,)``
           - Per-instance 2D bounds including occluded geometry. Same 24-byte layout as tight boxes. Reject records with inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3DValues
           - uint8
           - ``(B,)``
           - Per-instance local 3D extents and a transform to world space. Each record is 96 bytes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - Visible-pixel bounds grouped by semantic instance. Each 48-byte record contains stable instance and semantic IDs plus pixel bounds. Read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2DValues
           - uint8
           - ``(B,)``
           - 2D bounds including occluded geometry, grouped by semantic instance. Same layout and trailing count as semantic tight boxes.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3DValues
           - uint8
           - ``(B,)``
           - Local 3D extents and world transform grouped by semantic instance. Each record is 120 bytes; read the trailing valid-record count.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - OcclusionValues
           - uint8
           - ``(B,)``
           - Per-instance occluded fraction in [0, 1]. A ratio of -1 means no sampled hits. Each 12-byte record contains instance/tile IDs and a float32 ratio.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/minimal/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdToken
           - uint8
           - ``(B,)``
           - Runtime instance IDs mapped to opaque prim handles, prototype indices and instancer indices. A 24-byte header precedes 24-byte records.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/minimal/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - uint32 array
           - uint8
           - ``(B,)``
           - Runtime-instance-to-semantic-instance lookup. Reinterpret the byte buffer as uint32 indices; 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/minimal/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMap``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - Packed metadata mapping stable IDs to prim-path strings. Each entry contains ``uint32 id[4]``,
             label length and label offset, followed by packed strings and a trailing entry count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/StableIdMap.avif
                :alt: Decoded StableIdMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New stable-ID/prim-path entries since the last generated delta. The first frame includes scene-creation entries. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - uint8
           - ``(B,)``
           - New semantic-ID/label entries since the last generated delta. Same packed layout as ``SemanticIdMap``. An unchanged scene returns a four-byte zero count.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - uint8
           - ``(260,)``
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens parameters.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/minimal/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - ID pairs
           - uint8
           - ``(B,)``
           - Stable semantic-instance IDs mapped to semantic label IDs. Each 32-byte record contains uint32 stableId[4] followed by uint32 semanticId[4]. No trailing count.

             :ref:`Python/C decoding <sd-decode-id-pairs>`.
           - .. image:: ../../img/aovs/minimal/StableIdSemanticIdMap.avif
                :alt: Decoded StableIdSemanticIdMap robot lineup illustration
                :width: 100%

.. toctree::
   :hidden:

   decoding_outputs

See :doc:`decoding_outputs` for tested Python and C API decoding examples.

Debug Views
-----------

Debug views replace the RenderProduct's beauty output with diagnostic geometry
data or heat maps. G-buffer views are available in Real-Time Path-Tracing and
Path Tracing.
These views are not available in Minimal mode. Author the target on the RenderProduct using the
generated schema name:

.. code-block:: usda

   string omni:rtx:debug:view:target = "normal"

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Token
     - Description
     - Example
   * - ``depth``
     - G-buffer depth multiplied by 1000 and displayed as grayscale.
     - .. image:: ../../img/debug-views/depth.avif
          :alt: Depth
          :width: 100%
   * - ``worldPosition``
     - World-space position wrapped into a repeating diagnostic color.
     - .. image:: ../../img/debug-views/worldPosition.avif
          :alt: World position
          :width: 100%
   * - ``barycentrics``
     - Triangle barycentric coordinates.
     - .. image:: ../../img/debug-views/barycentrics.avif
          :alt: Barycentrics
          :width: 100%
   * - ``texcoord0``
     - Fractional values from the first texture-coordinate set.
     - .. image:: ../../img/debug-views/texcoord0.avif
          :alt: Texture coordinates 0
          :width: 100%
   * - ``texcoord1``
     - Fractional values from the second texture-coordinate set.
     - .. image:: ../../img/debug-views/texcoord1.avif
          :alt: Texture coordinates 1
          :width: 100%
   * - ``triangleNormal``
     - Geometric triangle normal encoded into the 0–1 color range.
     - .. image:: ../../img/debug-views/triangleNormal.avif
          :alt: Triangle normal
          :width: 100%
   * - ``normal``
     - Interpolated shading normal encoded into the 0–1 color range.
     - .. image:: ../../img/debug-views/normal.avif
          :alt: Interpolated normal
          :width: 100%
   * - ``tangentu``
     - First shading tangent encoded into the 0–1 color range.
     - .. image:: ../../img/debug-views/tangentu.avif
          :alt: Tangent U
          :width: 100%
   * - ``tangentv``
     - Second shading tangent encoded into the 0–1 color range.
     - .. image:: ../../img/debug-views/tangentv.avif
          :alt: Tangent V
          :width: 100%
   * - ``instanceId``
     - Per-pixel instance identifier color.
     - .. image:: ../../img/debug-views/instanceId.avif
          :alt: Instance ID
          :width: 100%
   * - ``stableId``
     - Per-pixel stable identifier color.
     - .. image:: ../../img/debug-views/stableId.avif
          :alt: Stable ID
          :width: 100%
   * - ``nonVisualMaterialId``
     - Per-pixel non-visual material identifier color.
     - .. image:: ../../img/debug-views/nonVisualMaterialId.avif
          :alt: Non-visual material ID
          :width: 100%
   * - ``targetMotion``
     - Per-pixel world-space motion, shown with the robots moving.
     - .. image:: ../../img/debug-views/targetMotion.avif
          :alt: 3D motion vectors
          :width: 100%
   * - ``targetMotionArrows``
     - World-space motion visualized as arrows, shown with the robots moving.
     - .. image:: ../../img/debug-views/targetMotionArrows.avif
          :alt: 3D motion-vector arrows
          :width: 100%
   * - ``wire``
     - Triangle edges derived from barycentric coordinates.
     - .. image:: ../../img/debug-views/wire.avif
          :alt: Wireframe
          :width: 100%
   * - ``anyHitCountHeatMap``
     - Color-mapped count of material any-hit calls associated with each pixel,
       including rejected candidates.
       Only supported in RealTimePathTracing.
     - .. image:: ../../img/debug-views/anyHitCountHeatMap.avif
          :alt: Any-hit count heat map
          :width: 100%

Debug views do not create dedicated RenderVars. They replace the beauty destination:

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Requested color RenderVars
     - Debug-view destination
   * - :ref:`LdrColor and HdrColor <camera-output-tables>`
     - :ref:`HdrColor <camera-output-tables>`. :ref:`LdrColor <camera-output-tables>` remains the regular beauty image.
   * - :ref:`HdrColor <camera-output-tables>` only
     - :ref:`HdrColor <camera-output-tables>`.
   * - :ref:`LdrColor <camera-output-tables>` only
     - :ref:`LdrColor <camera-output-tables>`.

The debug-view shader has already converted its diagnostic values to display colors.
Applying HDR tonemapping changes the diagnostic colors. RenderVars such as :ref:`NormalSD <camera-output-tables>` and
:ref:`DepthSD <camera-output-tables>` remain independent
sensor outputs and are not changed by this setting.

See :doc:`../../examples/python_debug_views` for a runnable example that renders
and displays all of these views.
