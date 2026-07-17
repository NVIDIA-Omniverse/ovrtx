.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Semantic Labels
===============

Semantic labels are USD ``SemanticsAPI`` metadata used by annotation outputs
such as semantic segmentation. In ovrtx, labels can be authored directly in USD
or layered over an existing scene with inline USDA.

Author Labels in USDA
---------------------

.. tab-set::

   .. tab-item:: Base Scene

      .. literalinclude:: ../../tests/docs/data/ovrtx-test-base-semantic-labels.usda
         :language: usda
         :start-after: # [snippet:doc-test-base-semantic-class-layer]
         :end-before: # [/snippet:doc-test-base-semantic-class-layer]

   .. tab-item:: Override Layer

      .. literalinclude:: ../../tests/docs/usd/data/semantic_label_overrides.usda
         :language: usda
         :start-after: # [snippet:doc-semantic-label-overrides]
         :end-before: # [/snippet:doc-semantic-label-overrides]

Runtime Overrides
-----------------

Use ordinary attribute writes to update semantic class and label metadata after
the stage is loaded.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_semantic_labels.py
         :language: python
         :start-after: # [snippet:doc-semantic-class-overrides-python]
         :end-before: # [/snippet:doc-semantic-class-overrides-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_semantic_labels.cpp
         :language: cpp
         :start-after: // [snippet:doc-semantic-class-overrides-c]
         :end-before: // [/snippet:doc-semantic-class-overrides-c]
         :dedent:

Interpreting Segmentation Output
--------------------------------

Semantic segmentation output maps pixels to numeric semantic identifiers. Use
the identifier information in the render output to map those ids back to labels.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_semantic_labels.py
         :language: python
         :start-after: # [snippet:doc-interpret-semantic-segmentation-python]
         :end-before: # [/snippet:doc-interpret-semantic-segmentation-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_semantic_labels.cpp
         :language: cpp
         :start-after: // [snippet:doc-interpret-semantic-segmentation-c]
         :end-before: // [/snippet:doc-interpret-semantic-segmentation-c]
         :dedent:

Notes
-----

- Put labels on the prims whose pixels or hits should carry that semantic
  meaning.
- Inline override layers are useful when a source asset cannot be edited.
- For sensor material behavior, use :doc:`../sensors/nonvisual_materials`
  instead. Semantic labels and non-visual material labels serve different
  systems.
