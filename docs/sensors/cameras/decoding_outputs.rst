.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-howto-first-camera-image:
.. _sd-output-decoding:

.. _sensors-cameras-howto-decode-outputs:

Decoding camera outputs
=======================

Example USD
-----------

A RenderProduct that outputs both :ref:`LdrColor <camera-output-tables>` and
:ref:`HdrColor <camera-output-tables>` from a camera:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../tests/docs/usd/data/camera_sensor_render_product.usda
         :language: usda
         :start-after: # [snippet:doc-camera-sensor-render-product]
         :end-before: # [/snippet:doc-camera-sensor-render-product]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-sensor-render-product-python]
         :end-before: # [/snippet:doc-camera-sensor-render-product-python]
         :dedent:

Accessing Outputs in Code
-------------------------

After stepping the renderer with a RenderProduct path, the outputs are available by full RenderVar prim path:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_sensors.py
         :language: python
         :start-after: # [snippet:doc-step-and-map-camera-outputs]
         :end-before: # [/snippet:doc-step-and-map-camera-outputs]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_sensors.cpp
         :language: cpp
         :start-after: // [snippet:doc-step-and-map-camera-outputs-c]
         :end-before: // [/snippet:doc-step-and-map-camera-outputs-c]
         :dedent:

.. _sd-decode-images:

.. _sensors-cameras-howto-decode-outputs-images:

Image tensors
-------------

Applies to ``NormalSD``, ``DepthSD``, ``Depth``, ``XRDepth``, ``DistanceToCameraSD``, ``DistanceToImagePlaneSD``, ``DiffuseAlbedoSD``, ``Camera3dPositionSD``, ``TargetMotionSD``, ``SemanticSegmentation``, ``SemanticInstanceSegmentation``, ``StableIdSegmentation``, and ``NonStableInstanceSegmentation``.

Image tensors already carry their scalar type and shape in DLPack. Python preserves
that type; C callers inspect ``dtype.code``, ``dtype.bits``, and ``shape`` before
reading pixels. The C helper checks CPU placement and contiguous layout and adds
``byte_offset``. Keep mappings alive while using their pointers.

Float images use float32; albedo uses uint8. Segmentation images use uint32:
keep all four words for stable and semantic IDs. Color IDs only for display;
do not normalize them before joining records. Non-stable IDs are runtime indices.
Map normals from [-1, 1] to display colors, normalize finite distances for display,
and encode motion direction as hue and displacement magnitude as brightness.
The table gives each output's units and channels. See :ref:`sd-identifier-domains`
before joining segmentation pixels to record outputs.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-map-image-python]
         :end-before: # [/snippet:doc-sd-map-image-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-map-image-c]
         :end-before: // [/snippet:doc-sd-map-image-c]
         :dedent:


.. _sd-identifier-domains:

Identifier domains and stability
--------------------------------

These outputs use several identifier domains. Join outputs from the same scene
snapshot and compare every word of a four-word ID. A row number, runtime instance
ID, semantic class ID, and stable ID are different keys even when their numeric
values happen to match.

.. list-table:: Identifier domains
   :header-rows: 1
   :widths: 22 43 35

   * - Key
     - Where it appears and how to join it
     - Lifetime and consistency
   * - Runtime instance ID (uint32)
     - ``instance_id`` in raw bounding boxes, occlusion, and the instance token
       map. Join raw boxes and occlusion on ``(instance_id, render_tile_id)``.
       The token map supplies the instance metadata.
     - Assigned to renderer instances. Scene edits, rebuilding instances, or
       reloading a stage can change or reuse these values. They are not persistent
       prim IDs and have no run-to-run or cross-machine guarantee.
   * - Semantic-instance row index (uint32)
     - ``InstanceMap.semantic_instance_index`` indexes
       ``StableIdSemanticIdMap`` rows. Index the instance map at
       ``instance_id - min_instance_id``, using the token-map parameter as the
       origin. ``0xFFFFFFFF`` means no semantic parent.
     - An index into the current semantic data. Preserve sparse rows; do not
       cache the index across scene edits or assume it identifies a class.
   * - Non-stable semantic-instance pixel (uint32)
     - ``NonStableInstanceSegmentation`` stores the semantic-instance row index
       **plus 2**, not the raw runtime instance ID. Pixels 0 and 1 mean background
       and unlabelled; subtract 2 only from values at least 2.
     - Has the same lifetime as the semantic-instance row index. It cannot be
       compared directly with a raw box's ``instance_id``.
   * - Geometry stable ID (four uint32 words)
     - ``StableIdSegmentation`` joins ``StableIdMap.id`` and
       ``StableIdMapDeltas.id`` to rendered geometry paths. Keep repeated map
       entries: one ID can have more than one associated path.
     - Derived from instance identity, including the canonical instance path
       and subset identity. Motion alone does not change that identity; renaming,
       reparenting, or changing instancing/subsets can change it.
   * - Semantic-instance stable ID (four uint32 words)
     - ``SemanticInstanceSegmentation``, semantic bounding-box ``id``, and
       ``StableIdSemanticIdMap.stable_id`` identify the semantic instance.
       Several geometry instances can resolve to one labelled ancestor. Do not
       assume this key equals their geometry stable IDs.
     - Derived from the semantic instance's identity. Inheritance, point-instance
       identity and subset identity matter; the visible leaf prim path alone
       does not determine it.
   * - Semantic class ID
     - ``SemanticSegmentation`` pixels match the first word of
       ``SemanticIdMap.id`` (the other three words are currently zero).
       Semantic bounding-box ``semantic_id`` and
       ``StableIdSemanticIdMap.semantic_id`` use that same four-word map key.
       Class pixels 0 and 1 mean background and unlabelled.
     - Allocated for compound label sets in the current runtime. Equal label
       sets share a class ID while that registry is retained. Labels, filters,
       initialization order or stage resets can change the mapping; the same
       label is not guaranteed the same number across runs or machines.
   * - Prim token (uint64)
     - ``InstanceIdTokenMapSD.prim_token`` is an opaque runtime token, separate
       from every ID above. ``prototype_index`` and ``instance_index`` describe
       instancing and are not class or stable IDs either.
     - Runtime metadata, not a portable path string or a persistent identifier.

For example, to connect a raw box to a label, use its ``instance_id`` to look up
the semantic-instance row through :ref:`sd-decode-instance-map`. Read that row's
``semantic_id`` from :ref:`sd-decode-id-pairs`, then find the matching
four-word ``id`` in :ref:`sd-decode-identifiers`. Use the row's ``stable_id`` to
join semantic boxes or semantic-instance pixels. This also handles a labelled
parent that groups several rendered children.

``Stable`` means derived from scene identity rather than allocation order.
Repeated runs with the same identity inputs and ID-generation implementation
can reproduce these IDs, but the SDK does not promise a portable hash format
across versions, rendering backends, or machines. A matching visible prim path
alone is insufficient, especially for instancing and subsets. For persistent
datasets, save the accompanying path and label maps with each capture, and use
application-owned identifiers when you require a cross-run or cross-machine
identity contract. Always consume delta maps from the first frame; an empty
later delta is not a replacement for the full map.


.. _sd-decode-records:

.. _sensors-cameras-howto-decode-outputs-records:

Legacy byte buffers
-------------------

The structured outputs documented below expose named fields and do not require
private record layouts. For a remaining legacy one-dimensional ``uint8`` buffer,
``B`` in shape ``(B,)`` is its byte length. Use its documented record type before
applying these generic helpers; do not normalize metadata as image pixels.

The helpers validate byte lengths. In C, ``memcpy()`` avoids alignment assumptions.
``counted=true`` reads a final uint32 count only for formats that specify one.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-records-python]
         :end-before: # [/snippet:doc-sd-records-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-records-c]
         :end-before: // [/snippet:doc-sd-records-c]
         :dedent:


.. _sd-decode-boxes:

.. _sensors-cameras-howto-decode-outputs-boxes:

Bounding boxes
--------------

Applies to ``BoundingBox2DTightSD``, ``BoundingBox2DLooseSD``, ``BoundingBox3DSD``, ``SemanticBoundingBox2DTight``, ``SemanticBoundingBox2DLoose``, and ``SemanticBoundingBox3D``.

Bounding-box outputs use schema version 0 and expose typed named tensors.
Inspect names, DLPack types, shapes, strides and byte offsets; fields may be
non-contiguous views of one allocation. Semantic boxes reserve capacity: consume
only ``valid_count[0]`` rows. The count is on the requested device, so CUDA
consumers can use it without a host readback. Synchronize CUDA access with the
output and keep the mapping alive while using its fields.

Use ``semantic=True`` for semantic boxes and ``three_d=True`` for 3D boxes in Python.
In C, look up ``extent`` and read elements with their DLPack strides.
Use ``sd_box_count()`` to select valid semantic rows. Skip records whose maximum is below their minimum.
2D coordinates are pixel bounds; draw rectangles over the color image. Raw boxes
join visibility and token records by instance/tile ID. Semantic boxes carry full
128-bit instance and class IDs.

Each 3D bounding-box output contains local ``extent`` bounds and an
``object_to_world`` tensor with one 4×4 matrix per row from local space to world space. The decoders below name this field
``local_to_world``. Use the matrix from the same record to transform the eight
box corners before projecting into the camera.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-boxes-python]
         :end-before: # [/snippet:doc-sd-boxes-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-boxes-c]
         :end-before: // [/snippet:doc-sd-boxes-c]
         :dedent:


.. _sd-decode-occlusion:

.. _sensors-cameras-howto-decode-outputs-occlusion:

Occlusion
---------

Applies to ``OcclusionSD``.

Schema ``Occlusion`` version 0 exposes ``instance_id`` and ``render_tile_id`` as
uint32 tensors and ``occlusion_ratio`` as float32, all shape ``(N,)``. Fields may
be strided views of one backing allocation. Explicit CUDA mappings return GPU
tensors; default follows producer placement (normally GPU). CPU mappings read
back GPU data. CUDA-array mapping is unsupported. Join each instance/tile key to its raw bounding box,
then annotate that box with the ratio. Skip negative ratios;
valid ratios range from zero (unoccluded) to one (fully occluded).

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-occlusion-python]
         :end-before: # [/snippet:doc-sd-occlusion-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-occlusion-c]
         :end-before: // [/snippet:doc-sd-occlusion-c]
         :dedent:


.. _sd-decode-tokens:

.. _sensors-cameras-howto-decode-outputs-tokens:

Instance token map
------------------

Applies to ``InstanceIdTokenMapSD``.

Schema ``InstanceIdTokenMap`` version 0 exposes ``instance_id``, ``prototype_index``,
and ``instance_index`` as uint32 tensors, and ``prim_token`` as uint64. Each has
shape ``(N,)``; there is no header row. CPU uint32 scalar params
``min_instance_id``, ``max_instance_id``, and ``render_tile_count`` describe the
instance range and tile count; each param has shape ``(1,)``. A zero-row map
may have a minimum greater than its maximum. The token is an opaque runtime
handle, not a string address or a persistent network ID.

Default and CPU mappings return CPU tensors; explicit CUDA mappings return CUDA
tensors while params stay on CPU. CUDA-array mapping is unsupported. Honor the
returned CUDA synchronization and keep the mapping alive while consuming fields.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-tokens-python]
         :end-before: # [/snippet:doc-sd-tokens-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-tokens-c]
         :end-before: // [/snippet:doc-sd-tokens-c]
         :dedent:


.. _sd-decode-instance-map:

.. _sensors-cameras-howto-decode-outputs-instance-map:

Instance map
------------

Applies to ``InstanceMap``.

Schema ``InstanceMap`` version 0 exposes one named uint32 tensor,
``semantic_instance_index`` with shape ``(N,)``. Element ``i`` corresponds to
``min_instance_id + i`` from the token-map CPU params; request
``InstanceIdTokenMapSD`` alongside this output to obtain that origin. ``0xFFFFFFFF`` means no
semantic parent. These values index semantic-instance rows, not semantic label
IDs or the four-word stable IDs. Default/CPU mappings return CPU tensors;
explicit CUDA mappings return CUDA tensors. CUDA-array mapping is unsupported.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-instance-map-python]
         :end-before: # [/snippet:doc-sd-instance-map-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-instance-map-c]
         :end-before: // [/snippet:doc-sd-instance-map-c]
         :dedent:


.. _sd-decode-identifiers:

.. _sensors-cameras-howto-decode-outputs-identifiers:

Identifier maps and deltas
--------------------------

Applies to ``SemanticIdMap``, ``SemanticIdMapDeltas``, ``StableIdMap``, and ``StableIdMapDeltas``.

These outputs have type ``IdentifierMap``, version 0, and three named tensors:

.. list-table::
   :header-rows: 1

   * - Tensor
     - Dtype and shape
     - Contents
   * - ``id``
     - uint32 ``(N, 4)``
     - All four words of each identifier, in producer row order.
   * - ``label_offsets``
     - uint64 ``(N+1,)``
     - Offsets into ``label_data``. The first is zero and the last is ``B``.
   * - ``label_data``
     - uint8 ``(B,)``
     - Concatenated UTF-8 label or prim-path bytes, without terminal NULs.

For row ``i``, decode ``label_data[label_offsets[i]:label_offsets[i+1]]``.
Do not use ``strlen``: embedded NUL bytes are preserved. Keep repeated ID/path
pairs and sparse empty rows; multiple paths can share one ID, and semantic
class indices can address the original row positions. Empty outputs have
``id.shape == (0, 4)``, ``label_offsets == [0]`` and no label bytes.

CPU and default mappings return CPU tensors. CUDA mappings return all three
tensors on the GPU; CUDA-array mappings are unsupported. Follow the mapping's
CUDA synchronization contract before device access. Keep the mapping alive
while using tensor views, or copy the values before unmapping.

The C example reuses ``sd_field()`` and ``sd_read()`` from
:ref:`bounding-box decoding <sd-decode-boxes>` to read the named fields.

Accumulate delta pairs from the first delivered frame and merge subsequent additions
into that history. An empty delta after warmup is normal. Clear this history when
starting a different scene; deltas do not describe removals. Author these RenderVars
before scene start so initial IDs are allocated and delivered. ``SemanticIdMap``
is a full class-label map; stable deltas associate geometry IDs with USD paths.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-identifiers-python]
         :end-before: # [/snippet:doc-sd-identifiers-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-identifiers-c]
         :end-before: // [/snippet:doc-sd-identifiers-c]
         :dedent:


.. _sd-decode-id-pairs:

.. _sensors-cameras-howto-decode-outputs-id-pairs:

Stable-to-semantic pairs
------------------------

Applies to ``StableIdSemanticIdMap``.

Schema ``StableIdSemanticIdMap`` version 0 exposes ``stable_id`` and ``semantic_id``
as uint32 tensors of shape ``(N,4)``. Default/CPU mappings return CPU tensors;
explicit CUDA mappings return CUDA tensors. CUDA-array mapping is unsupported.
Respect DLPack strides and synchronize GPU access. Join all four words of each stable
ID to ``SemanticInstanceSegmentation`` and its semantic class ID
to ``SemanticIdMap``. This maps labeled semantic instances rather than every raw
geometry ID in ``StableIdSegmentation``. Preserve
one-to-many relationships rather than overwriting repeated keys. Zero IDs denote
background. ``SemanticInstanceSegmentation`` uses ``(0, 0, 0, 1)`` for unlabeled
geometry; ``SemanticSegmentation`` uses class index ``1``. Class indices occupy the
first word of the four-word class ID, so the corresponding class tuple is
``(1, 0, 0, 0)``. Non-stable instance pixels use ``0`` for background and ``1``
for unlabeled geometry. For a labeled pixel, subtract two from its non-stable
instance value to index the pair-record array.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-id-pairs-python]
         :end-before: # [/snippet:doc-sd-id-pairs-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-id-pairs-c]
         :end-before: // [/snippet:doc-sd-id-pairs-c]
         :dedent:


.. _sd-decode-camera:

.. _sensors-cameras-howto-decode-outputs-camera:

Camera parameters
-----------------

Applies to ``CameraParams``.

``CameraParams`` has output-format version 0, no tensors, and 23 named CPU
parameters. These parameters remain on the CPU for every requested mapping
device. Read them from ``params`` and keep the mapping alive while using their
values. Each mapped result owns a snapshot of the camera that produced its frame.

``view_matrix`` and ``projection_matrix`` are float32 arrays of shape (4,4).
The view matrix is world-to-camera; both matrices multiply row vectors.
Camera transforms and box transforms share scene units. The scalar
``meters_per_scene_unit`` converts scene units to meters.
``render_product_resolution`` is uint32 with shape (2,), and ``near_far``
is float32 with shape (2,). ``camera_model`` is a uint8 array containing UTF-8
bytes without a terminator.

The remaining float32 parameters preserve the producer's values and units:
``focal_length``, ``focal_distance``, ``f_stop``, ``fov_x_radians``,
``ftheta_width``, ``ftheta_height``, ``ftheta_cx``, ``ftheta_cy``,
``ftheta_max_fov``, ``ftheta_poly_a`` through ``ftheta_poly_f``,
``lens_p`` (2,) and ``lens_s`` (4,). The fields without a listed shape are
scalars with shape ``(1,)``.
The examples below read camera parameters and use them to project a box corner.
The C example reuses ``sd_field()`` and ``sd_read()`` from
:ref:`bounding-box decoding <sd-decode-boxes>` to find parameters and read their
values with the declared DLPack strides.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-camera-python]
         :end-before: # [/snippet:doc-sd-camera-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-camera-c]
         :end-before: // [/snippet:doc-sd-camera-c]
         :dedent:

.. _sensors-cameras-howto-decode-outputs-project:

Project a box corner into the image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The decoded record is enough to draw a 3D box over the image. For a pinhole
camera, transform a local corner by the box's ``local_to_world``, then by
``world_to_camera``, then by ``projection``, all as row vectors; divide by W;
and map the normalized device coordinates to pixels with Y inverted. A corner
behind the camera (W at or below zero) has no pixel: clip box edges against the
near plane before you draw them. Camera and box coordinates already share scene
units, so do not apply the meters-per-scene-unit scale to them.

The snippets below project one local point and return its pixel position, or
nothing when the point lies behind the camera.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-project-python]
         :end-before: # [/snippet:doc-sd-project-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-project-c]
         :end-before: // [/snippet:doc-sd-project-c]
         :dedent:

.. _pt-decode-pixels:

.. _sensors-cameras-howto-decode-outputs-pt-pixels:

Path Tracing pixels
-------------------

The Path Tracing table gives each tensor's actual type and channel count.
Convert float16 to float32 before arithmetic. Divide uint8 color and roughness
by 255; float32 values keep their original units. The C reader accepts CPU,
contiguous mappings and accounts for ``byte_offset``. Keep the mapping alive
while reading pixels.

Lighting outputs use RGB; normals and positions use XYZ. Motion uses XY pixel
displacement, with view-depth change in Z for four-channel screen-motion outputs.
``MotionWorld`` uses scene units instead. ``Roughness`` uses the blue channel.
These values need the display
remapping described in the table; decoding alone does not tone-map them.

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../examples/python/semantic-segmentation/main.py
         :language: python
         :start-after: # [snippet:doc-pt-pixels-python]
         :end-before: # [/snippet:doc-pt-pixels-python]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-pt-pixels-c]
         :end-before: // [/snippet:doc-pt-pixels-c]
         :dedent:

Related
-------

- :doc:`outputs`
- :doc:`../common/sensor_outputs`
