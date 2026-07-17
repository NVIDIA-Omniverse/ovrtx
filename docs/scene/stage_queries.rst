.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Stage Queries
=============

.. note::

   Python examples query ovstage directly. ``Renderer.query_prims*`` and the C
   renderer query API are deprecated compatibility surfaces. Refer to
   ``skills/update-0_3-0_4-python/SKILL.md``.

Stage queries discover prims on the runtime stage and optionally report
attribute schema metadata. A typical workflow is:

1. Query prims by type, attribute existence, or a filter combination.
2. Inspect returned paths and attribute descriptors.
3. Reuse the Python query handle, or the returned C prim-list handles, in later
   reads or writes.

Ovstage filters use predicates such as ``usd-prim-type`` and ``usd-path``. The
deprecated renderer query supports its existing AND/OR/NOT compatibility shape.

Python Queries
--------------

.. tab-set::

   .. tab-item:: Basic

      .. literalinclude:: ../../tests/docs/python/test_stage_query.py
         :language: python
         :start-after: # [snippet:doc-query-prims-basic]
         :end-before: # [/snippet:doc-query-prims-basic]
         :dedent:

   .. tab-item:: By Type

      .. literalinclude:: ../../tests/docs/python/test_stage_query.py
         :language: python
         :start-after: # [snippet:doc-query-prims-by-type]
         :end-before: # [/snippet:doc-query-prims-by-type]
         :dedent:

   .. tab-item:: Attributes

      .. literalinclude:: ../../tests/docs/python/test_stage_query.py
         :language: python
         :start-after: # [snippet:doc-query-prims-with-attributes]
         :end-before: # [/snippet:doc-query-prims-with-attributes]
         :dedent:

   .. tab-item:: Compatibility OR/NOT

      .. literalinclude:: ../../tests/docs/python/test_stage_query.py
         :language: python
         :start-after: # [snippet:doc-query-require-any-exclude]
         :end-before: # [/snippet:doc-query-require-any-exclude]
         :dedent:

C Queries
---------

.. tab-set::

   .. tab-item:: Basic

      .. literalinclude:: ../../tests/docs/c/test_stage_query.cpp
         :language: cpp
         :start-after: // [snippet:doc-query-prims-basic-c]
         :end-before: // [/snippet:doc-query-prims-basic-c]
         :dedent:

   .. tab-item:: By Type

      .. literalinclude:: ../../tests/docs/c/test_stage_query.cpp
         :language: cpp
         :start-after: // [snippet:doc-query-prims-by-type-c]
         :end-before: // [/snippet:doc-query-prims-by-type-c]
         :dedent:

   .. tab-item:: Has Attribute

      .. literalinclude:: ../../tests/docs/c/test_stage_query.cpp
         :language: cpp
         :start-after: // [snippet:doc-query-has-attribute-c]
         :end-before: // [/snippet:doc-query-has-attribute-c]
         :dedent:

   .. tab-item:: Combined

      .. literalinclude:: ../../tests/docs/c/test_stage_query.cpp
         :language: cpp
         :start-after: // [snippet:doc-query-require-any-exclude-c]
         :end-before: // [/snippet:doc-query-require-any-exclude-c]
         :dedent:

Async Queries
-------------

Ovstage queries can be waited before reading their result and must be released
when they are no longer needed:

.. literalinclude:: ../../tests/docs/python/test_stage_query.py
   :language: python
   :start-after: # [snippet:doc-query-prims-async]
   :end-before: # [/snippet:doc-query-prims-async]
   :dedent:

Path Dictionary
---------------

C query results use token and prim-path ids. In standalone mode, resolve them
through the renderer's path dictionary. In attached mode, obtain the
owner-provided dictionary with ``ovstage_get_path_dictionary(instance)``. Do not
free it or assume dictionaries are shared across instances.

Path lists borrowed from ovstage results remain valid only while the producing
handle owns them. Add a path-list reference before releasing the producer when
the list must remain usable, and release that reference when finished.

Resolve them while the query results are still valid:

.. literalinclude:: ../../tests/docs/c/test_stage_query.cpp
   :language: cpp
   :start-after: // [snippet:doc-path-dictionary-resolve-c]
   :end-before: // [/snippet:doc-path-dictionary-resolve-c]
   :dedent:

Python uses ``ovstage.PathDictionary`` to intern attribute tokens and create
path lists.

Troubleshooting
---------------

- Release C query results only after copying any strings, descriptors, or ids you
  need to keep.
- ``AttributeFilterMode.SPECIFIC`` with an empty attribute-name list returns no
  descriptors. Use ``ALL`` to dump every descriptor or ``NONE`` for lightweight
  discovery.
- Relationship-valued attributes surface as path ids in C. Resolve them through
  the path dictionary before printing or storing string paths.
