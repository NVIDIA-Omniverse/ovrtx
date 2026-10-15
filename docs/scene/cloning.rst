.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Cloning Prims
=============

.. note::

   Python uses ovstage cloning. ``Renderer.clone_usd*`` and
   :c:func:`ovrtx_clone_usd` are deprecated compatibility APIs. Refer to
   ``skills/update-0_3-0_4-python/SKILL.md``. Ovstage cloning differs from the
   compatibility API:

   - The caller supplies an ordinal that must satisfy ovstage's configured
     :ref:`admission policy <ovstage-ordinal-admission>` and applicable write floors.
   - The ``_usd`` suffix is dropped from clone destination paths.
   - A missing source prim or an already-existing target is rejected with a
     specific status (``OVSTAGE_ERROR_NOT_FOUND`` / ``OVSTAGE_ERROR_PRIM_NOT_FOUND``)
     rather than the generic ``OVRTX_API_ERROR``. Both APIs reject before anything
     is cloned and name the offending path in the operation error.

   Refer to :doc:`/core/ovstage_integration` for the attached-stage workflow.

Cloning copies a USD subtree already present on the runtime stage to a new prim
path. Use it for making additional copies of loaded geometry, sensors, or other
stage content without re-authoring the original USD.

Clone destinations must be new absolute prim paths. If the cloned subtree
contains relationships, make sure the copied content still points at the desired
targets after cloning.

For attached ovstage clones, customizing a copied attribute under the
``STRICTLY_INCREASING`` policy requires a newer ordinal than the clone, even
before sealing. See the :ref:`admission-policy summary <ovstage-ordinal-admission>`
for other policy choices.

Wait for the clone to complete successfully before customizing its results.
Then wait for all customizations and the write-floor advance before rendering.
An accepted async enqueue alone does not establish successful publication.

Clone a Subtree
---------------

These snippets clone at an explicit ordinal and wait for write-floor publication:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_stage_mutation.py
         :language: python
         :start-after: # [snippet:doc-clone-usd]
         :end-before: # [/snippet:doc-clone-usd]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_stage_mutation.cpp
         :language: cpp
         :start-after: // [snippet:doc-clone-usd-c]
         :end-before: // [/snippet:doc-clone-usd-c]
         :dedent:

Async Cloning
-------------

Wait for the async clone before advancing and waiting for the write floor:

.. literalinclude:: ../../tests/docs/python/test_stage_mutation.py
   :language: python
   :start-after: # [snippet:doc-clone-usd-async]
   :end-before: # [/snippet:doc-clone-usd-async]
   :dedent:

Notes
-----

- Clone loaded content, then use :doc:`transforms` to place each copy.
- Use :doc:`stage_queries` to discover source paths before cloning generated or
  externally supplied scenes.
- Use :doc:`loading_usd` references when the content should remain removable by
  handle or when it has not yet been loaded onto the stage.
