.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Attribute Mapping
=================

.. note::

   Python stage attribute mapping uses ovstage query and map-group APIs.
   Renderer map/unmap methods are deprecated compatibility APIs. Refer to
   ``skills/update-0_3-0_4-python/SKILL.md``.

Mapping an attribute gives application code direct access to its stage buffer.
This avoids a copy when code writes directly into the buffer.

The lifecycle is:

1. Map the attribute.
2. Write into the mapped tensor while the mapping is active.
3. Unmap the attribute, passing CUDA stream or event synchronization when GPU
   work wrote the data.

CPU Mapping
-----------

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
         :language: python
         :start-after: # [snippet:doc-map-attribute-cpu]
         :end-before: # [/snippet:doc-map-attribute-cpu]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_attribute_bindings.cpp
         :language: cpp
         :start-after: // [snippet:doc-map-attribute-cpu-c]
         :end-before: // [/snippet:doc-map-attribute-cpu-c]
         :dedent:

CUDA Mapping
------------

The deprecated renderer wrapper can map attributes to CUDA memory for GPU-side
writes. The example below documents its stream-synchronization requirements.

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-map-attribute-cuda]
   :end-before: # [/snippet:doc-map-attribute-cuda]
   :dedent:

Explicit Unmap
--------------

Context managers are preferred in Python, but explicit async unmap is available
when the application needs to coordinate mapping lifetime manually.

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-unmap-attribute-async]
   :end-before: # [/snippet:doc-unmap-attribute-async]
   :dedent:

Limits and Lifetime
-------------------

- Ovstage maps ragged array attributes when ``element_sizes`` supplies one
  element count per queried prim. Omit ``element_sizes`` for fixed-size
  attributes.
- The tensor returned by a mapping is valid only until unmap. Copy data if it
  must outlive the mapping.
- For deprecated renderer CUDA mappings, pass a stream or event on unmap so
  ovrtx knows when GPU writes are complete.
- Do not pass CUDA sync objects for CPU mappings.
- Multiple mappings can be outstanding; effects are applied in unmap order.
