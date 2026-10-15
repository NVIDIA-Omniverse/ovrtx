.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Cylinder Light
==============

A ``CylinderLight`` emits outwards from a tube aligned with its local X axis.
Use it for fluorescent tubes, neon lights, and similar linear sources. It also
uses the :doc:`common light attributes <index>`.

.. figure:: ../img/light-type-cylinder.avif
   :alt: A test scene lit by a tubular cylinder light
   :align: center

   *A cylinder light emits outwards from the surface of a tube.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:length = 1``", "Cylinder length along the local X axis, in scene units."
   "``float inputs:radius = 0.5``", "Cylinder radius in scene units."
   "``bool treatAsLine = false``", "Allows the renderer to treat the source as a zero-radius line light."

The following examples create a thin, 1.2-scene-unit-long tube light:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-cylinder-light]
         :end-before: # [/snippet:doc-cylinder-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-cylinder-light-python]
         :end-before: # [/snippet:doc-cylinder-light-python]
         :dedent:
