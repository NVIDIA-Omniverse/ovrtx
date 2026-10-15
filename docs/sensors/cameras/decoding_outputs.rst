.. _sd-output-decoding:

Decoding camera outputs
=======================

.. _sd-decode-images:

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
The table gives each output's units and channels.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-map-image-python]
         :end-before: # [/snippet:doc-sd-map-image-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-map-image-c]
         :end-before: // [/snippet:doc-sd-map-image-c]
         :dedent:


.. _sd-decode-records:

Packed record buffers
---------------------

Buffer outputs map to one-dimensional ``uint8`` tensors. In shape ``(B,)``,
``B`` is the byte length, not the record count. Decode the little-endian bytes
using the field types shown below; do not normalize them as image pixels.

The helpers validate buffer lengths before reading records. In C, copy records
with ``memcpy()`` to avoid alignment assumptions about the mapped pointer.
``counted=true`` reads the final uint32 count; uncounted arrays use the byte length.
Semantic boxes reserve unused capacity: read only the populated records.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-records-python]
         :end-before: # [/snippet:doc-sd-records-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-records-c]
         :end-before: // [/snippet:doc-sd-records-c]
         :dedent:


.. _sd-decode-boxes:

Bounding boxes
--------------

Applies to ``BoundingBox2DTightSD``, ``BoundingBox2DLooseSD``, ``BoundingBox3DSD``, ``SemanticBoundingBox2DTight``, ``SemanticBoundingBox2DLoose``, and ``SemanticBoundingBox3D``.

Use ``semantic=True`` for semantic boxes and ``three_d=True`` for 3D boxes in Python.
In C, pass the corresponding structure size to ``sd_records()`` and set ``counted``
only for semantic boxes. Skip records whose maximum is below their minimum.
2D coordinates are pixel bounds; draw rectangles over the color image. Raw boxes
join visibility and token records by instance/tile ID. Semantic boxes carry full
128-bit instance and class IDs.

Each 3D bounding-box record contains local bounds and a 4×4 ``transform``
matrix from local space to world space. The decoders below name this field
``local_to_world``. Use the matrix from the same record to transform the eight
box corners before projecting into the camera.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-boxes-python]
         :end-before: # [/snippet:doc-sd-boxes-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-boxes-c]
         :end-before: // [/snippet:doc-sd-boxes-c]
         :dedent:


.. _sd-decode-occlusion:

Occlusion
---------

Applies to ``OcclusionSD``.

Read 12-byte records without a trailing count. Join each instance/tile key to
its raw bounding box, then annotate that box with the ratio. Skip negative ratios;
valid ratios range from zero (unoccluded) to one (fully occluded).

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-occlusion-python]
         :end-before: # [/snippet:doc-sd-occlusion-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-occlusion-c]
         :end-before: // [/snippet:doc-sd-occlusion-c]
         :dedent:


.. _sd-decode-tokens:

Instance token map
------------------

Applies to ``InstanceIdTokenMapSD``.

Read 24-byte records without a trailing count. The first record is a header:
``instance_id`` is the number of following records; the low/high uint32 words of
``prim_token`` give the minimum/maximum instance ID; ``prototype`` gives the tile
count. Subsequent records contain an opaque runtime token, prototype index, and
instance index. The token is not a string address or a persistent network ID.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-tokens-python]
         :end-before: # [/snippet:doc-sd-tokens-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-tokens-c]
         :end-before: // [/snippet:doc-sd-tokens-c]
         :dedent:


.. _sd-decode-instance-map:

Instance map
------------

Applies to ``InstanceMap``.

Read uint32 semantic indices without a trailing count. Element ``i`` corresponds
to ``minInstanceId + i`` from the token-map header. Use these indices with the
non-stable instance/semantic outputs; they are not the four-word stable IDs.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-instance-map-python]
         :end-before: # [/snippet:doc-sd-instance-map-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-instance-map-c]
         :end-before: // [/snippet:doc-sd-instance-map-c]
         :dedent:


.. _sd-decode-identifiers:

Identifier maps and deltas
--------------------------

Applies to ``SemanticIdMap``, ``SemanticIdMapDeltas``, ``StableIdMap``, and ``StableIdMapDeltas``.

Each record contains four uint32 ID words, a UTF-8 byte length, and a byte offset
from the start of the buffer. Strings follow the records; the final uint32 gives
the record count. Read exactly the declared byte length: do not use ``strlen``
or require a NUL terminator. Keep repeated ID/path pairs; multiple paths can share one ID.

Accumulate delta pairs from the first delivered frame and merge subsequent additions
into that history. An empty delta after warmup is normal. Clear this history when
starting a different scene; deltas do not describe removals. Author these RenderVars
before scene start so initial IDs are allocated and delivered. ``SemanticIdMap``
is a full class-label map; stable deltas associate geometry IDs with USD paths.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-identifiers-python]
         :end-before: # [/snippet:doc-sd-identifiers-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-identifiers-c]
         :end-before: // [/snippet:doc-sd-identifiers-c]
         :dedent:


.. _sd-decode-id-pairs:

Stable-to-semantic pairs
------------------------

Applies to ``StableIdSemanticIdMap``.

Read 32-byte records without a trailing count. Join all four words of each stable
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

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-id-pairs-python]
         :end-before: # [/snippet:doc-sd-id-pairs-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-id-pairs-c]
         :end-before: // [/snippet:doc-sd-id-pairs-c]
         :dedent:


.. _sd-decode-camera:

Camera parameters
-----------------

Applies to ``CameraParams``.

Read exactly one 260-byte record, including the three padding bytes after the
25-byte model name. The first matrix is world-to-camera; both matrices multiply
row vectors. Camera matrices and box transforms share scene units. The scale
field converts scene units to meters. Projection model parameters follow the
matrices and image resolution.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/python/test_camera_aovs.py
         :language: python
         :start-after: # [snippet:doc-sd-camera-python]
         :end-before: # [/snippet:doc-sd-camera-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-sd-camera-c]
         :end-before: // [/snippet:doc-sd-camera-c]
         :dedent:

.. _pt-decode-pixels:

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

      .. literalinclude:: ../../../examples/python/semantic-segmentation/main.py
         :language: python
         :start-after: # [snippet:doc-pt-pixels-python]
         :end-before: # [/snippet:doc-pt-pixels-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../tests/docs/c/test_camera_aovs.cpp
         :language: cpp
         :start-after: // [snippet:doc-pt-pixels-c]
         :end-before: // [/snippet:doc-pt-pixels-c]
         :dedent:
