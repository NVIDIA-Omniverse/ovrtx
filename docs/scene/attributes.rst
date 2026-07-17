.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Attribute Reads and Writes
==========================

.. note::

   Python examples query, read, and write through ovstage. The renderer
   read/write wrappers and their destination-buffer and CUDA forms are
   deprecated compatibility APIs. Refer to ``skills/update-0_3-0_4-python/SKILL.md``.

Ovstage reads and writes runtime stage attributes using DLPack tensors. The
dtype and shape must match the USD attribute schema. Scalar attributes contain
one value per prim. Array attributes contain variable-length values such as mesh
points or relationships.

Tensor Layout
-------------

Ovstage and C attribute tensors use ``DLDataType::lanes`` for multi-component
values. NumPy backing arrays and DLPack consumers expose lane components as
trailing dimensions:

.. list-table::
   :header-rows: 1

   * - USD value
     - Python shape
     - C shape and dtype
   * - ``int`` for N prims
     - ``(N,)`` ``int32``
     - ``shape=[N]``, ``{kDLInt, 32, 1}``
   * - ``point3f`` for N prims
     - ``(N, 3)`` ``float32``
     - ``shape=[N]``, ``{kDLFloat, 32, 3}``
   * - ``matrix4d`` for N prims
     - ``(N, 16)`` ``float64``
     - ``shape=[N]``, ``{kDLFloat, 64, 16}``
   * - 4x4 transform semantic for N prims
     - ``(N, 4, 4)`` ``float64``
     - ``shape=[N]``, ``{kDLFloat, 64, 16}``
   * - ``point3f[]`` with M elements
     - ``(M, 3)`` ``float32``
     - ``shape=[M]``, ``{kDLFloat, 32, 3}``

Reading Attributes
------------------

.. tab-set::

   .. tab-item:: Python Scalar

      .. literalinclude:: ../../tests/docs/python/test_attribute_read.py
         :language: python
         :start-after: # [snippet:doc-read-attribute-scalar]
         :end-before: # [/snippet:doc-read-attribute-scalar]
         :dedent:

   .. tab-item:: Python Array

      .. literalinclude:: ../../tests/docs/python/test_attribute_read.py
         :language: python
         :start-after: # [snippet:doc-read-array-attribute]
         :end-before: # [/snippet:doc-read-array-attribute]
         :dedent:

   .. tab-item:: C Scalar

      .. literalinclude:: ../../tests/docs/c/test_attribute_read.cpp
         :language: cpp
         :start-after: // [snippet:doc-read-attribute-scalar-c]
         :end-before: // [/snippet:doc-read-attribute-scalar-c]
         :dedent:

   .. tab-item:: C Array

      .. literalinclude:: ../../tests/docs/c/test_attribute_read.cpp
         :language: cpp
         :start-after: // [snippet:doc-read-array-attribute-c]
         :end-before: // [/snippet:doc-read-array-attribute-c]
         :dedent:

The deprecated renderer read wrappers can write directly into caller-provided
CPU or CUDA DLPack destinations:

.. tab-set::

   .. tab-item:: CPU destination

      .. literalinclude:: ../../tests/docs/python/test_attribute_read.py
         :language: python
         :start-after: # [snippet:doc-read-attribute-dest-tensor]
         :end-before: # [/snippet:doc-read-attribute-dest-tensor]
         :dedent:

   .. tab-item:: CUDA destination

      .. literalinclude:: ../../tests/docs/python/test_attribute_read.py
         :language: python
         :start-after: # [snippet:doc-read-attribute-cuda-dest]
         :end-before: # [/snippet:doc-read-attribute-cuda-dest]
         :dedent:

Writing Attributes
------------------

.. tab-set::

   .. tab-item:: Python Array

      .. literalinclude:: ../../tests/docs/python/test_attribute_shapes.py
         :language: python
         :start-after: # [snippet:doc-shape-float3-array]
         :end-before: # [/snippet:doc-shape-float3-array]
         :dedent:

   .. tab-item:: Python Token Array

      .. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
         :language: python
         :start-after: # [snippet:doc-write-token-array]
         :end-before: # [/snippet:doc-write-token-array]
         :dedent:

   .. tab-item:: C Scalar

      .. literalinclude:: ../../tests/docs/c/test_attribute_bindings.cpp
         :language: cpp
         :start-after: // [snippet:doc-write-bound-attribute-c]
         :end-before: // [/snippet:doc-write-bound-attribute-c]
         :dedent:

Compatibility Data Access
-------------------------

Synchronous writes copy data before the call returns. Asynchronous writes can
access the caller's memory later during stream execution, so the source tensor
must remain alive until the operation completes. String data supports only
synchronous access.

The deprecated Python wrappers expose this through ``DataAccess.SYNC`` and
``DataAccess.ASYNC``. C uses the access mode argument to
:c:func:`ovrtx_write_attribute`.

Type Notes
----------

- Pass ``is_array=True`` to ovstage writes for USD array attributes and
  relationships.
- Ovstage writes use ``AttributeSemantic`` to preserve authored interpretation.
  Deprecated ovrtx reads use raw storage layout and ``OVRTX_SEMANTIC_NONE``.
- Quaternion tensor order is ``(i, j, k, real)`` even though USDA authors values
  as ``(real, i, j, k)``.
- ``string`` attributes are represented as UTF-8 byte arrays. String arrays are
  not supported; use ``token[]`` for string-like arrays.
- Python ovstage code interns token and relationship values through
  ``ovstage.PathDictionary``.
- Ovstage asset values use byte rows with ``AttributeSemantic.ASSET_STRING``.
  Deprecated C compatibility writes represent scalar assets as token pairs.

C Convenience Helpers
---------------------

For path, token, and transform attributes, prefer helpers in
``<ovrtx/ovrtx_attributes.h>`` where available. For token strings:

.. literalinclude:: ../../tests/docs/c/test_attribute_helpers.cpp
   :language: cpp
   :start-after: // [snippet:doc-set-token-attributes-c]
   :end-before: // [/snippet:doc-set-token-attributes-c]
   :dedent:

Troubleshooting
---------------

- Match the runtime dtype, not the Python or C default numeric type.
- Ovstage array writes use lane-aware DLTensors and ``is_array=True``.
- ``PrimMode.UPSERT`` creates absent prims and updates existing prims;
  ``PrimMode.INSERT`` is create-only.
- In C, binding descriptors borrow path storage. Keep the strings and arrays
  alive until the operation that uses the descriptor has completed.
- Generic authored USD attributes require
  ``customLayerData.populateAllAuthoredAttributes = true`` on the root layer.
