.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Attribute Bindings
==================

.. note::

   Python examples replace persistent bindings with reusable ovstage queries.
   Persistent renderer bindings remain deprecated compatibility APIs. Refer to
   ``skills/update-0_3-0_4-python/SKILL.md``.

For repeated Python writes or maps, retain one ovstage query for the target prims
and reuse it at successive ordinals. C compatibility code can retain a binding
descriptor for the same purpose.

Use regular writes from :doc:`attributes` for one-shot edits. Use
:doc:`attribute_mapping` when the hot path needs zero-copy writes into
ovrtx-owned buffers.

Create a Reusable Target and Write
----------------------------------

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
         :language: python
         :start-after: # [snippet:doc-bind-attribute-write]
         :end-before: # [/snippet:doc-bind-attribute-write]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_attribute_bindings.cpp
         :language: cpp
         :start-after: // [snippet:doc-create-attribute-binding-c]
         :end-before: // [/snippet:doc-create-attribute-binding-c]
         :dedent:

      .. literalinclude:: ../../tests/docs/c/test_attribute_bindings.cpp
         :language: cpp
         :start-after: // [snippet:doc-write-bound-attribute-c]
         :end-before: // [/snippet:doc-write-bound-attribute-c]
         :dedent:

      .. literalinclude:: ../../tests/docs/c/test_attribute_bindings.cpp
         :language: cpp
         :start-after: // [snippet:doc-destroy-attribute-binding-c]
         :end-before: // [/snippet:doc-destroy-attribute-binding-c]
         :dedent:

Async Queries and Writes
------------------------

Ovstage query and write handles can be waited explicitly for non-blocking update
pipelines.

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-bind-attribute-async]
   :end-before: # [/snippet:doc-bind-attribute-async]
   :dedent:

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-binding-write-async]
   :end-before: # [/snippet:doc-binding-write-async]
   :dedent:

Array Attributes
----------------

Use ``is_array=True`` for variable-length USD array attributes such as mesh
``points``.

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-bind-array-attribute]
   :end-before: # [/snippet:doc-bind-array-attribute]
   :dedent:

Mapping Through a Query
-----------------------

The same ovstage query can be reused for repeated map/unmap cycles.

.. literalinclude:: ../../tests/docs/python/test_attribute_bindings.py
   :language: python
   :start-after: # [snippet:doc-map-bound-attribute]
   :end-before: # [/snippet:doc-map-bound-attribute]
   :dedent:

Lifetime Rules
--------------

- Release reusable ovstage queries when the hot path is done.
- In C, keep strings and descriptor arrays alive until binding creation has
  completed.
- ``OVRTX_BINDING_FLAG_OPTIMIZE`` is intended for frequent high-volume writes.
