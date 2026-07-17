.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Writing Transforms
==================

Transforms are ordinary runtime stage attributes with a transform semantic.
The canonical transform attribute is ``omni:xform``. The legacy
``omni:fabric:localMatrix`` name is also accepted, but new code should prefer
``omni:xform``.

ovrtx uses the USD row-vector matrix convention: translation is stored in the
last row of a 4x4 matrix, at ``matrix[3][0..2]`` or flat indices ``12..14``.

4x4 Matrix Writes
-----------------

.. tab-set::

   .. tab-item:: Python

      Python uses NumPy-style tensor shapes. A batch of N 4x4 transforms has
      shape ``(N, 4, 4)`` and dtype ``float64``.

      .. literalinclude:: ../../tests/docs/python/test_attribute_shapes.py
         :language: python
         :start-after: # [snippet:doc-shape-mat4-array]
         :end-before: # [/snippet:doc-shape-mat4-array]
         :dedent:

   .. tab-item:: C

      C convenience helpers in ``<ovrtx/ovrtx_attributes.h>`` hide the
      DLTensor descriptor boilerplate for common transform layouts.

      .. literalinclude:: ../../tests/docs/c/test_transform_helpers.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-xform-mat-c]
         :end-before: // [/snippet:doc-set-xform-mat-c]
         :dedent:

C Transform Helpers
-------------------

The C API also provides compact helpers for position/rotation/scale layouts and
for authoring ``omni:resetXformStack``.

.. tab-set::

   .. tab-item:: Position, Quaternion, Scale

      .. literalinclude:: ../../tests/docs/c/test_transform_helpers.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-xform-pos-rot-scale-c]
         :end-before: // [/snippet:doc-set-xform-pos-rot-scale-c]
         :dedent:

   .. tab-item:: Position and 3x3 Rotation

      .. literalinclude:: ../../tests/docs/c/test_transform_helpers.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-xform-pos-rot3x3-c]
         :end-before: // [/snippet:doc-set-xform-pos-rot3x3-c]
         :dedent:

   .. tab-item:: Reset Stack

      .. literalinclude:: ../../tests/docs/c/test_transform_helpers.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-reset-xform-stack-c]
         :end-before: // [/snippet:doc-set-reset-xform-stack-c]
         :dedent:

Repeated Updates
----------------

For per-frame transform animation, avoid rebuilding descriptors on every
update:

- Use :doc:`attribute_bindings` when the application already owns the transform
  tensors and copying into ovrtx is acceptable.
- Use :doc:`attribute_mapping` when CUDA or CPU code should write directly into
  ovrtx-owned attribute buffers.

Notes
-----

- Transform matrices are ``float64``.
- Semantics are write-side conversion hints. Attribute reads use the raw storage
  layout.
- In C, a 4x4 matrix attribute is represented as ``shape=[N]`` with
  ``DLDataType{kDLFloat, 64, 16}``.
- In Python, a 4x4 matrix attribute is represented as ``shape=(N, 4, 4)``.
