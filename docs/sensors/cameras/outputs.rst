.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-outputs:

Outputs
=======

The tables below list the RenderVar source names available for camera sensors,
grouped by render mode. Shapes are channel-last DLPack tensor shapes.

.. _sensors-cameras-outputs-attributes:

Use the **sourceName** value as the ``sourceName`` attribute on a ``RenderVar`` prim.
Click any example image to enlarge it. Buffer examples are decoded illustrations,
not raw image outputs.

Bounding boxes, occlusion, identifier maps, instance maps, and stable-to-semantic
ID pairs expose named, typed tensors through
``ovrtx_render_var_output_t``. Field tensors may be strided views of one
allocation. Semantic boxes also expose ``valid_count`` on the requested device;
only the first ``valid_count[0]`` rows are populated. Keep the mapping alive
while using its tensors. Token-map range and tile metadata are CPU parameters;
``CameraParams`` contains only CPU parameters. Structured outputs use schema version 0.

.. note::

   The example images for non-color outputs have been remapped for easier visualization
   and do not represent raw output values. All output example images in the table were
   generated from the ``semantic-segmentation`` example.

   Real-Time Path Tracing and Minimal use 50 warmup frames; Path Tracing uses one frame
   at 128 samples per pixel after an initial step that creates instances for selection.
   The robots then move for a separate motion capture, whose
   hue shows direction and brightness shows displacement (20 pixels reaches full brightness).

   Bounding-box overlays show only robot geometry: raw box outputs show individual parts,
   while semantic box outputs show one aggregate box per top-level robot. Colors distinguish
   robots. 3D corners are transformed to world space and projected using ``CameraParams``.

   ``SelectionState`` previews decode each of the four coverage samples before
   averaging their colors. Selected robots use cyan (group 1), orange (group 2),
   and purple (group 3); visible samples have full brightness, hidden samples 25%,
   and background is black. These colors illustrate data, not renderer styling.

   Occlusion colors loose part boxes from green (visible) to red (occluded); invalid ratios
   are omitted.

   ID-map examples pair an annotated scene with decoded metadata; delta examples use their
   first-frame entries.

.. _sensors-cameras-outputs-tables:
.. _camera-output-tables:

.. tab-set::

   .. tab-item:: Real-Time Path Tracing

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
                :alt: LdrColor example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear-space HDR color preserving full scene luminance (the beauty output; see the :doc:`Glossary <../reference/glossary>`).
             Use for post-processing, compositing, or linear-space workflows.
             Delivered as float16 unless the RenderProduct sets ``omni:rtx:rt:fp32Target``, which delivers float32;
             see :ref:`HdrColor precision <sensors-visual-camera-core-howto-input-image-precision>`.
           - .. image:: ../../img/aovs/rt2/HdrColor.avif
                :alt: HdrColor example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``SelectionState``
           - Four coverage samples
           - uint16
           - ``(H, W, 4)``
           - Selected-surface classification at output resolution. Each channel stores
             group in bits 0–7 (zero means background) and visibility in bit 8
             (1 visible, 0 hidden); bits 9–15 are zero. Channels are adaptive coverage
             samples, not RGBA colors. Only the nearest selected surface is represented;
             objects sharing a group form one mask. Requesting this output replaces
             the built-in selection overlay for this RenderProduct.
             XR foveation unwarp is unsupported: the output is cleared and a warning
             is logged. Disable unwarp to read selection in warped coordinates.

             See the :doc:`selection SPG example <../../examples/c_selection_spg>`
             for custom outlines, fills, and hidden-surface cross-hatching.
           - .. image:: ../../img/aovs/rt2/SelectionState.avif
                :alt: Selected robot groups in cyan, orange, and purple; occluded samples are dim and background is black
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/NormalSD.avif
                :alt: NormalSD example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated** and still delivered; use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.
             For a perspective camera, unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane);
             an orthographic camera reverses the mapping, and a fisheye or other
             :doc:`lens projection <lens_calibration>` stores the distance from the camera.
             A pixel whose ray hit nothing holds the far-clip value, which is 0 for a perspective camera.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DepthSD.avif
                :alt: DepthSD example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DistanceToCameraSD.avif
                :alt: DistanceToCameraSD example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DistanceToImagePlaneSD.avif
                :alt: DistanceToImagePlaneSD example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/DiffuseAlbedoSD.avif
                :alt: DiffuseAlbedoSD example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units, with W = 1.
             A pixel whose ray hit nothing has W = 0 and holds a point far along the ray, so test W rather than
             the position magnitude to find background; a min/max-stretched preview of the raw values comes out flat.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/Camera3dPositionSD.avif
                :alt: Camera3dPositionSD example image rendered in Real-Time Path Tracing
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
             Class index 1 marks unlabeled geometry. Class indices occupy the first word of the four-word class ID
             in ``SemanticIdMap``, so the matching class tuple is ``(1, 0, 0, 0)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/SemanticSegmentation.avif
                :alt: SemanticSegmentation example image rendered in Real-Time Path Tracing
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Semantic IDs and UTF-8 labels as uint32 IDs, uint64 offsets and uint8 label bytes.
             Row order, sparse empty rows and all four ID words are preserved.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabeled hits are ``(0, 0, 0, 1)``.

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
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabeled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/rt2/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance visible-pixel bounds: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2). Reject inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance bounds including occluded geometry: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2).

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3D
           - uint32, float32
           - Named tensors
           - Per-instance local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``instance_id`` and ``render_tile_id``.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Visible-pixel bounds grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Bounds including occluded geometry grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3D
           - uint32, float32
           - Named tensors
           - Local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``id`` and ``semantic_id``. Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/rt2/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - Occlusion
           - uint32, float32
           - Named tensors
           - ``instance_id``, ``render_tile_id``, and ``occlusion_ratio`` have shape (N,). Ratios range from 0 to 1; -1 means no sampled hits.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/rt2/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdTokenMap
           - uint32, uint64
           - Named tensors + CPU params
           - ``instance_id``, ``prim_token``, ``prototype_index``, and ``instance_index`` have shape (N,). CPU scalar params provide ``min_instance_id``, ``max_instance_id``, and ``render_tile_count``. Tensor rows contain no header.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/rt2/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - InstanceMap
           - uint32
           - ``semantic_instance_index (N,)``
           - Runtime-instance-to-semantic-instance lookup. 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/rt2/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Stable IDs and USD prim paths as uint32 IDs, uint64 offsets and uint8 UTF-8 bytes.
             Repeated IDs retain their separate rows.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/StableIdMap.avif
                :alt: Decoded StableIdMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New stable-ID/prim-path entries since the last generated delta, using the named identifier-map tensors.
             The first frame includes scene-creation entries; an empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New semantic-ID/label entries since the last generated delta, using the same named tensors as ``SemanticIdMap``.
             An empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/rt2/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - Named CPU params
           - No tensors
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens fields as named CPU parameters, for every requested mapping device.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/rt2/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - StableIdSemanticIdMap
           - uint32
           - Named tensors
           - ``stable_id`` and ``semantic_id`` both have shape (N,4). Preserve all four words and repeated rows when joining semantic instances to their labels.

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
                :alt: LdrColor example image rendered in Path Tracing
                :width: 100%
         * - ``HdrColor``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Linear-space HDR color preserving full scene luminance (the beauty output; see the :doc:`Glossary <../reference/glossary>`).
             Use for post-processing, compositing, or linear-space workflows.
             Delivered as float16 unless the RenderProduct sets ``omni:rtx:rt:fp32Target``, which delivers float32;
             see :ref:`HdrColor precision <sensors-visual-camera-core-howto-input-image-precision>`.
             :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/HdrColor.avif
                :alt: HdrColor example image rendered in Path Tracing
                :width: 100%
         * - ``PtDirectIllumation``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct diffuse reflection. The source name intentionally uses the renderer spelling ``Illumation``. See :ref:`camera-aov-compositing` and :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtDirectIllumation.avif
                :alt: PtDirectIllumation example image rendered in Path Tracing
                :width: 100%
         * - ``PtGlobalIllumination``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Indirect diffuse reflection. Excludes the glossy reflection and transmission passes. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtGlobalIllumination.avif
                :alt: PtGlobalIllumination example image rendered in Path Tracing
                :width: 100%
         * - ``PtReflections``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct and indirect glossy/specular reflection, including direct highlights. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtReflections.avif
                :alt: PtReflections example image rendered in Path Tracing
                :width: 100%
         * - ``PtRefractions``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct and indirect glossy/specular transmission. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtRefractions.avif
                :alt: PtRefractions example image rendered in Path Tracing
                :width: 100%
         * - ``PtSubsurfaceScattering``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct and indirect diffuse transmission, including the subsurface-scattering contribution. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtSubsurfaceScattering.avif
                :alt: PtSubsurfaceScattering example image rendered in Path Tracing
                :width: 100%
         * - ``PtSelfIllumination``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Camera-visible emission, lights, and environment misses. Includes the visible background. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtSelfIllumination.avif
                :alt: PtSelfIllumination example image rendered in Path Tracing
                :width: 100%
         * - ``PtVolumes``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Direct and indirect volume-scattering contribution. Include in the :ref:`seven-pass sum <camera-aov-compositing>`.

             The captured RGB values are zero in this scene.
           - .. image:: ../../img/aovs/pt/PtVolumes.avif
                :alt: Black PtVolumes output from the factory scene
                :width: 100%
         * - ``PtBackground``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Separate background output for background/matte workflows. Do not add it to the seven-pass sum: visible background is already included.

             The captured RGB values are zero in this scene.
           - .. image:: ../../img/aovs/pt/PtBackground.avif
                :alt: Black PtBackground output from the factory scene
                :width: 100%
         * - ``PtPreDenoisedResult``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Accumulated radiance before denoising. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtPreDenoisedResult.avif
                :alt: PtPreDenoisedResult example image rendered in Path Tracing
                :width: 100%
         * - ``PtWorldNormal``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space geometric normal in XYZ, averaged across samples; edges can have length below one. Display [-1, 1] as [0, 1]. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtWorldNormal.avif
                :alt: PtWorldNormal example image rendered in Path Tracing
                :width: 100%
         * - ``PtWorldPos``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space hit position in XYZ, in scene units. The preview rescales each coordinate. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtWorldPos.avif
                :alt: PtWorldPos example image rendered in Path Tracing
                :width: 100%
         * - ``PtViewNormal``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - View-space normal in XYZ, averaged across samples. Display [-1, 1] as [0, 1]. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtViewNormal.avif
                :alt: PtViewNormal example image rendered in Path Tracing
                :width: 100%
         * - ``PtZDepth``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Ray-hit distance normalized linearly over the depth range from ``omni:rtx:pathtracing:zDepthMin`` to
             ``omni:rtx:pathtracing:zDepthMax`` (render settings on the RenderProduct; 0.1 and 10000 scene units by default)
             and clamped to [0, 1]; repeated in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtZDepth.avif
                :alt: PtZDepth example image rendered in Path Tracing
                :width: 100%
         * - ``PtDiffuseFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Diffuse material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtDiffuseFilter.avif
                :alt: PtDiffuseFilter example image rendered in Path Tracing
                :width: 100%
         * - ``PtReflectionFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Reflection material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtReflectionFilter.avif
                :alt: PtReflectionFilter example image rendered in Path Tracing
                :width: 100%
         * - ``PtRefractionFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Transmission material color filter in RGB. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtRefractionFilter.avif
                :alt: PtRefractionFilter example image rendered in Path Tracing
                :width: 100%
         * - ``PtSubsurfaceFilter``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Subsurface material albedo at the first camera hit, estimated from volume absorption and scattering coefficients and weighted by diffuse transmission.
             :ref:`PtSubsurfaceScattering <camera-output-tables>` also includes diffuse transmission without volume scattering, so it can be nonzero while this filter is zero, for example with thin-walled materials.
             Like the other filters, this is not an additive beauty pass.

             The captured RGB values are zero in this scene.
           - .. image:: ../../img/aovs/pt/PtSubsurfaceFilter.avif
                :alt: Black PtSubsurfaceFilter output from the factory scene
                :width: 100%
         * - ``PtLuminance``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - RGB radiance in RGB rendering; spectral rendering stores CIE Y in each RGB channel. The preview log-compresses values and scales them to the 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtLuminance.avif
                :alt: PtLuminance example image rendered in Path Tracing
                :width: 100%
         * - ``PtIlluminance``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - RGB irradiance at the first surface, evaluated with a unit Lambertian material. The preview log-compresses values and scales them to the 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtIlluminance.avif
                :alt: PtIlluminance example image rendered in Path Tracing
                :width: 100%
         * - ``PtMotion``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - XY screen displacement in pixels; Z change in view-space depth. W is 1. Motion is captured after moving the robots. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/PtMotion.avif
                :alt: PtMotion example image rendered in Path Tracing
                :width: 100%
         * - .. _sensors-cameras-render-modes-path-tracing-multimatte:

             ``PtMultiMatte0`` – ``PtMultiMatte7``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Each RGBA component holds independent coverage for a selected geometry or material ID, from 0 to 1.
             Configure ``omni:rtx:pt:multimatte:rId``, ``gId``, ``bId``, ``aId`` and their
             ``rIsMat``, ``gIsMat``, ``bIsMat``, ``aIsMat`` flags on each RenderVar.
             Omitted IDs and -1 disable components. Requests determine allocation, up to eight outputs / 32 masks.
             Geometry IDs use ``primvars:multimatte_id``; material IDs use ``multimatte_id`` on the material.
             The preview combines RGB slices of outputs 0–3; the gray strip shows their full-frame alpha masks.
             Labels list RGBA selectors (G = geometry, M = material).
             See :doc:`../../examples/python_semantic_segmentation` and
             :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/MultiMatte.avif
                :alt: PtMultiMatte0 through PtMultiMatte7 example image rendered in Path Tracing
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
                :alt: Light Path Expressions example image rendered in Path Tracing
                :width: 100%
         * - ``BumpNormal``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space shading normal, including material bump, in XYZ. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/BumpNormal.avif
                :alt: BumpNormal example image rendered in Path Tracing
                :width: 100%
         * - ``BumpNormalResearch``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - Half-precision shading-normal diagnostic. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/BumpNormalResearch.avif
                :alt: BumpNormalResearch example image rendered in Path Tracing
                :width: 100%
         * - ``DiffuseAlbedo``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse material RGB color, stored as UNORM bytes. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DiffuseAlbedo.avif
                :alt: DiffuseAlbedo example image rendered in Path Tracing
                :width: 100%
         * - ``SpecularAlbedo``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Specular material RGB color, stored as UNORM bytes. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/SpecularAlbedo.avif
                :alt: SpecularAlbedo example image rendered in Path Tracing
                :width: 100%
         * - ``DepthLinearized``
           - Scalar
           - float32
           - ``(H, W, 1)``
           - Linear view-space depth in scene units. Ignore the float32 maximum-value miss sentinel. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DepthLinearized.avif
                :alt: DepthLinearized example image rendered in Path Tracing
                :width: 100%
         * - ``Motion2dXYZ``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - XY screen displacement in pixels and Z view-depth change; W is 1. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dXYZ.avif
                :alt: Motion2dXYZ example image rendered in Path Tracing
                :width: 100%
         * - ``Motion2dDilated``
           - XY
           - float32
           - ``(H, W, 2)``
           - Dilated screen displacement in pixels, in XY. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dDilated.avif
                :alt: Motion2dDilated example image rendered in Path Tracing
                :width: 100%
         * - ``Motion2dXYZDilated``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - Dilated XY screen displacement in pixels and Z view-depth change; W is 1. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Motion2dXYZDilated.avif
                :alt: Motion2dXYZDilated example image rendered in Path Tracing
                :width: 100%
         * - ``MotionWorld``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - World-space displacement in XYZ, in scene units; W is 1. The preview shows XY direction and scales magnitude to the captured 99th percentile. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/MotionWorld.avif
                :alt: MotionWorld example image rendered in Path Tracing
                :width: 100%
         * - ``EmissionAndForegroundMask``
           - RGBA
           - float16
           - ``(H, W, 4)``
           - RGB surface emission and W foreground mask. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/EmissionAndForegroundMask.avif
                :alt: EmissionAndForegroundMask example image rendered in Path Tracing
                :width: 100%
         * - ``Roughness``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Material roughness in the blue channel, stored as a UNORM byte. The preview displays blue as grayscale. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/Roughness.avif
                :alt: Roughness example image rendered in Path Tracing
                :width: 100%
         * - ``DisocclusionMask``
           - Scalar
           - float16
           - ``(H, W, 1)``
           - Disocclusion mask in [0, 1]. The preview displays it directly as grayscale. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/DisocclusionMask.avif
                :alt: DisocclusionMask example image rendered in Path Tracing
                :width: 100%
         * - ``ViewspacePosition``
           - RGBA
           - float32
           - ``(H, W, 4)``
           - View-space position in XYZ, in scene units. The preview rescales each coordinate. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/ViewspacePosition.avif
                :alt: ViewspacePosition example image rendered in Path Tracing
                :width: 100%
         * - ``XRDepth``
           - Scalar
           - float32
           - ``(H, W, 1)``
           - Normalized reversed clip depth for XR composition. :ref:`Python/C pixel decoding <pt-decode-pixels>`.
           - .. image:: ../../img/aovs/pt/XRDepth.avif
                :alt: XRDepth example image rendered in Path Tracing
                :width: 100%
         * - ``SelectionState``
           - Four coverage samples
           - uint16
           - ``(H, W, 4)``
           - Selected-surface classification at output resolution. Each channel stores
             group in bits 0–7 (zero means background) and visibility in bit 8
             (1 visible, 0 hidden); bits 9–15 are zero. Channels are adaptive coverage
             samples, not RGBA colors. Only the nearest selected surface is represented;
             objects sharing a group form one mask. Requesting this output replaces
             the built-in selection overlay for this RenderProduct.
             XR foveation unwarp is unsupported: the output is cleared and a warning
             is logged. Disable unwarp to read selection in warped coordinates.

             See the :doc:`selection SPG example <../../examples/c_selection_spg>`
             for custom outlines, fills, and hidden-surface cross-hatching.
           - .. image:: ../../img/aovs/pt/SelectionState.avif
                :alt: Selected robot groups in cyan, orange, and purple; occluded samples are dim and background is black
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/NormalSD.avif
                :alt: NormalSD example image rendered in Path Tracing
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated** and still delivered; use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.
             For a perspective camera, unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane);
             an orthographic camera reverses the mapping, and a fisheye or other
             :doc:`lens projection <lens_calibration>` stores the distance from the camera.
             A pixel whose ray hit nothing holds the far-clip value, which is 0 for a perspective camera.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DepthSD.avif
                :alt: DepthSD example image rendered in Path Tracing
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DistanceToCameraSD.avif
                :alt: DistanceToCameraSD example image rendered in Path Tracing
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DistanceToImagePlaneSD.avif
                :alt: DistanceToImagePlaneSD example image rendered in Path Tracing
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/DiffuseAlbedoSD.avif
                :alt: DiffuseAlbedoSD example image rendered in Path Tracing
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units, with W = 1.
             A pixel whose ray hit nothing has W = 0 and holds a point far along the ray, so test W rather than
             the position magnitude to find background; a min/max-stretched preview of the raw values comes out flat.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/Camera3dPositionSD.avif
                :alt: Camera3dPositionSD example image rendered in Path Tracing
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
             Class index 1 marks unlabeled geometry. Class indices occupy the first word of the four-word class ID
             in ``SemanticIdMap``, so the matching class tuple is ``(1, 0, 0, 0)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/SemanticSegmentation.avif
                :alt: SemanticSegmentation example image rendered in Path Tracing
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Semantic IDs and UTF-8 labels as uint32 IDs, uint64 offsets and uint8 label bytes.
             Row order, sparse empty rows and all four ID words are preserved.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabeled hits are ``(0, 0, 0, 1)``.

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
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabeled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/pt/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance visible-pixel bounds: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2). Reject inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance bounds including occluded geometry: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2).

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3D
           - uint32, float32
           - Named tensors
           - Per-instance local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``instance_id`` and ``render_tile_id``.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Visible-pixel bounds grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Bounds including occluded geometry grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3D
           - uint32, float32
           - Named tensors
           - Local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``id`` and ``semantic_id``. Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/pt/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - Occlusion
           - uint32, float32
           - Named tensors
           - ``instance_id``, ``render_tile_id``, and ``occlusion_ratio`` have shape (N,). Ratios range from 0 to 1; -1 means no sampled hits.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/pt/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdTokenMap
           - uint32, uint64
           - Named tensors + CPU params
           - ``instance_id``, ``prim_token``, ``prototype_index``, and ``instance_index`` have shape (N,). CPU scalar params provide ``min_instance_id``, ``max_instance_id``, and ``render_tile_count``. Tensor rows contain no header.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/pt/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - InstanceMap
           - uint32
           - ``semantic_instance_index (N,)``
           - Runtime-instance-to-semantic-instance lookup. 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/pt/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Stable IDs and USD prim paths as uint32 IDs, uint64 offsets and uint8 UTF-8 bytes.
             Repeated IDs retain their separate rows.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/StableIdMap.avif
                :alt: Decoded StableIdMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New stable-ID/prim-path entries since the last generated delta, using the named identifier-map tensors.
             The first frame includes scene-creation entries; an empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New semantic-ID/label entries since the last generated delta, using the same named tensors as ``SemanticIdMap``.
             An empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/pt/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - Named CPU params
           - No tensors
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens fields as named CPU parameters, for every requested mapping device.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/pt/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - StableIdSemanticIdMap
           - uint32
           - Named tensors
           - ``stable_id`` and ``semantic_id`` both have shape (N,4). Preserve all four words and repeated rows when joining semantic instances to their labels.

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
                :alt: LdrColor example image rendered in Minimal
                :width: 100%
         * - ``NormalSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - World-space surface normals.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/NormalSD.avif
                :alt: NormalSD example image rendered in Minimal
                :width: 100%
         * - ``DepthSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - **Deprecated** and still delivered; use ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD`` instead.
             For a perspective camera, unitless raster depth mapped from 1 (near clip plane) to 0 (far clip plane);
             an orthographic camera reverses the mapping, and a fisheye or other
             :doc:`lens projection <lens_calibration>` stores the distance from the camera.
             A pixel whose ray hit nothing holds the far-clip value, which is 0 for a perspective camera.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DepthSD.avif
                :alt: DepthSD example image rendered in Minimal
                :width: 100%
         * - ``Depth`` / ``XRDepth``
           - Z
           - float32
           - ``(H, W, 1)``
           - Unitless reversed clip depth, from 1 (near clip plane) to 0 (far clip plane).
             Both names expose the same depth values as ``DepthSD`` in Minimal mode.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/Depth.avif
                :alt: Depth example image rendered in Minimal
                :width: 100%
         * - ``DistanceToCameraSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Euclidean distance from the camera origin to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DistanceToCameraSD.avif
                :alt: DistanceToCameraSD example image rendered in Minimal
                :width: 100%
         * - ``DistanceToImagePlaneSD``
           - Z
           - float32
           - ``(H, W, 1)``
           - Perpendicular distance from the image plane to each surface point, in meters whatever the stage's ``metersPerUnit``.
             A pixel whose ray hit nothing holds infinity.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DistanceToImagePlaneSD.avif
                :alt: DistanceToImagePlaneSD example image rendered in Minimal
                :width: 100%
         * - ``DiffuseAlbedoSD``
           - RGBA
           - uint8
           - ``(H, W, 4)``
           - Diffuse surface albedo (base color without lighting).

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/DiffuseAlbedoSD.avif
                :alt: DiffuseAlbedoSD example image rendered in Minimal
                :width: 100%
         * - ``Camera3dPositionSD``
           - XYZA
           - float32
           - ``(H, W, 4)``
           - Camera-space 3D position of each visible surface point, in scene units, with W = 1.
             A pixel whose ray hit nothing has W = 0 and holds a point far along the ray, so test W rather than
             the position magnitude to find background; a min/max-stretched preview of the raw values comes out flat.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/Camera3dPositionSD.avif
                :alt: Camera3dPositionSD example image rendered in Minimal
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
             Class index 1 marks unlabeled geometry. Class indices occupy the first word of the four-word class ID
             in ``SemanticIdMap``, so the matching class tuple is ``(1, 0, 0, 0)``.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/SemanticSegmentation.avif
                :alt: SemanticSegmentation example image rendered in Minimal
                :width: 100%
         * - ``SemanticIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Semantic IDs and UTF-8 labels as uint32 IDs, uint64 offsets and uint8 label bytes.
             Row order, sparse empty rows and all four ID words are preserved.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/SemanticIdMap.avif
                :alt: Decoded SemanticIdMap robot lineup illustration
                :width: 100%

         * - ``SemanticInstanceSegmentation``
           - ID[4]
           - uint32
           - ``(H, W, 4)``
           - Stable ID of the semantic prim associated with each pixel. Maintain a prim-path lookup from ``StableIdMapDeltas``. Background is all zeros; unlabeled hits are ``(0, 0, 0, 1)``.

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
           - Runtime semantic-instance index plus 2 per pixel. Zero is background; 1 is an unlabeled hit. These indices can change as scene contents change.

             :ref:`Python/C decoding <sd-decode-images>`.
           - .. image:: ../../img/aovs/minimal/NonStableInstanceSegmentation.avif
                :alt: Robot lineup NonStableInstanceSegmentation visualization
                :width: 100%
         * - ``BoundingBox2DTightSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance visible-pixel bounds: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2). Reject inverted bounds.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox2DTightSD.avif
                :alt: Decoded BoundingBox2DTightSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox2DLooseSD``
           - BoundingBox2D
           - uint32, int32
           - Named tensors
           - Per-instance bounds including occluded geometry: ``instance_id``, ``render_tile_id`` and ``extent`` (N,2,2).

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox2DLooseSD.avif
                :alt: Decoded BoundingBox2DLooseSD robot lineup illustration
                :width: 100%
         * - ``BoundingBox3DSD``
           - BoundingBox3D
           - uint32, float32
           - Named tensors
           - Per-instance local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``instance_id`` and ``render_tile_id``.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/BoundingBox3DSD.avif
                :alt: Decoded BoundingBox3DSD robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DTight``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Visible-pixel bounds grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox2DTight.avif
                :alt: Decoded SemanticBoundingBox2DTight robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox2DLoose``
           - SemanticBoundingBox2D
           - uint32, int32
           - Named tensors
           - Bounds including occluded geometry grouped by semantic instance: ``id``, ``semantic_id`` and ``extent`` (N,2,2). Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox2DLoose.avif
                :alt: Decoded SemanticBoundingBox2DLoose robot lineup illustration
                :width: 100%
         * - ``SemanticBoundingBox3D``
           - SemanticBoundingBox3D
           - uint32, float32
           - Named tensors
           - Local ``extent`` (N,2,3), ``object_to_world`` (N,4,4), ``id`` and ``semantic_id``. Consume only ``valid_count[0]`` rows.

             :ref:`Python/C decoding <sd-decode-boxes>`.
           - .. image:: ../../img/aovs/minimal/SemanticBoundingBox3D.avif
                :alt: Decoded SemanticBoundingBox3D robot lineup illustration
                :width: 100%
         * - ``OcclusionSD``
           - Occlusion
           - uint32, float32
           - Named tensors
           - ``instance_id``, ``render_tile_id``, and ``occlusion_ratio`` have shape (N,). Ratios range from 0 to 1; -1 means no sampled hits.

             :ref:`Python/C decoding <sd-decode-occlusion>`.
           - .. image:: ../../img/aovs/minimal/OcclusionSD.avif
                :alt: Decoded OcclusionSD robot lineup illustration
                :width: 100%
         * - ``InstanceIdTokenMapSD``
           - InstanceIdTokenMap
           - uint32, uint64
           - Named tensors + CPU params
           - ``instance_id``, ``prim_token``, ``prototype_index``, and ``instance_index`` have shape (N,). CPU scalar params provide ``min_instance_id``, ``max_instance_id``, and ``render_tile_count``. Tensor rows contain no header.

             :ref:`Python/C decoding <sd-decode-tokens>`.
           - .. image:: ../../img/aovs/minimal/InstanceIdTokenMapSD.avif
                :alt: Decoded InstanceIdTokenMapSD robot lineup illustration
                :width: 100%
         * - ``InstanceMap``
           - InstanceMap
           - uint32
           - ``semantic_instance_index (N,)``
           - Runtime-instance-to-semantic-instance lookup. 0xFFFFFFFF means no semantic parent. Indices address semantic-instance records, not ``SemanticIdMap`` label IDs.

             :ref:`Python/C decoding <sd-decode-instance-map>`.
           - .. image:: ../../img/aovs/minimal/InstanceMap.avif
                :alt: Decoded InstanceMap robot lineup illustration
                :width: 100%
         * - ``StableIdMap``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - Stable IDs and USD prim paths as uint32 IDs, uint64 offsets and uint8 UTF-8 bytes.
             Repeated IDs retain their separate rows.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/StableIdMap.avif
                :alt: Decoded StableIdMap robot lineup illustration
                :width: 100%
         * - ``StableIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New stable-ID/prim-path entries since the last generated delta, using the named identifier-map tensors.
             The first frame includes scene-creation entries; an empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/StableIdMapDeltas.avif
                :alt: Decoded StableIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``SemanticIdMapDeltas``
           - IdentifierMap
           - Named tensors
           - ``id (N, 4)``, ``label_offsets (N+1,)``, ``label_data (B,)``
           - New semantic-ID/label entries since the last generated delta, using the same named tensors as ``SemanticIdMap``.
             An empty delta has zero rows and ``label_offsets = [0]``.

             :ref:`Python/C decoding <sd-decode-identifiers>`.
           - .. image:: ../../img/aovs/minimal/SemanticIdMapDeltas.avif
                :alt: Decoded SemanticIdMapDeltas robot lineup illustration
                :width: 100%
         * - ``CameraParams``
           - CameraParams
           - Named CPU params
           - No tensors
           - View and projection matrices, scene-unit scale, resolution, clipping range, camera-model name and lens fields as named CPU parameters, for every requested mapping device.

             :ref:`Python/C decoding <sd-decode-camera>`.
           - .. image:: ../../img/aovs/minimal/CameraParams.avif
                :alt: Decoded CameraParams robot lineup illustration
                :width: 100%
         * - ``StableIdSemanticIdMap``
           - StableIdSemanticIdMap
           - uint32
           - Named tensors
           - ``stable_id`` and ``semantic_id`` both have shape (N,4). Preserve all four words and repeated rows when joining semantic instances to their labels.

             :ref:`Python/C decoding <sd-decode-id-pairs>`.
           - .. image:: ../../img/aovs/minimal/StableIdSemanticIdMap.avif
                :alt: Decoded StableIdSemanticIdMap robot lineup illustration
                :width: 100%

.. toctree::
   :hidden:
   :maxdepth: 1

   decoding_outputs

See :doc:`decoding_outputs` for tested Python and C API decoding examples.

.. _sensors-cameras-outputs-debug-views:

Debug Views
-----------

Debug views replace the RenderProduct's beauty output, the shaded color image
that normally lands in ``LdrColor`` and ``HdrColor``, with diagnostic geometry
data or heat maps. Most of them visualize the G-buffer: the per-pixel geometry
attributes such as depth, normals, texture coordinates and identifiers that the
renderer resolves before shading. Both terms are in the
:doc:`Glossary <../reference/glossary>`. Debug views need Real-Time
Path Tracing or Path Tracing; Minimal does not serve them. Select a view by
authoring its token on the RenderProduct:

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
       ``omni:rtx:debug:view:scaling`` rescales the view; the example image uses 0.005,
       which fits a scene authored in meters.
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
     - Per-pixel stable identifier color. Stable identifiers exist only while a
       RenderProduct in the same update requests a stable-ID output (``StableIdMap``,
       ``StableIdMapDeltas``, ``StableIdSegmentation``, ``StableIdSemanticIdMap`` or
       ``SemanticInstanceSegmentation``); the example image was captured with
       ``StableIdSegmentation`` requested alongside.
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
   * - .. _debug-view-any-hit-count:

       ``anyHitCountHeatMap``
     - Color-mapped count of material any-hit calls associated with each pixel,
       including rejected candidates.
       Only supported in Real-Time Path Tracing.
     - .. image:: ../../img/debug-views/anyHitCountHeatMap.avif
          :alt: Any-hit count heat map
          :width: 100%

Debug views do not create dedicated RenderVars. They replace the beauty
destination:

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

Debug views arrive already converted to display colors, so convert a view read
from :ref:`HdrColor <camera-output-tables>` to 8-bit directly; applying HDR
tonemapping would change the diagnostic colors. RenderVars such as
:ref:`NormalSD <camera-output-tables>` and :ref:`DepthSD <camera-output-tables>`
remain independent sensor outputs and are not changed by
``omni:rtx:debug:view:target``.

See :doc:`../../examples/python_debug_views` for a runnable example that
renders and displays all of these views.

Related
-------

- :doc:`decoding_outputs`
- :doc:`../common/output_configuration`
- :doc:`../common/sensor_outputs`
