.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Sphere Light
============

A ``SphereLight`` emits outwards in every direction. Increase its radius for a
larger visible source and softer shadows. It also uses the
:doc:`common light attributes <index>`.

.. figure:: ../img/light-type-sphere.avif
   :alt: A test scene lit by a spherical area light
   :align: center

   *A sphere light behaves like an omnidirectional bulb with a finite size.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:radius = 0.5``", "Sphere radius in scene units."
   "``bool treatAsPoint = false``", "Allows the renderer to treat the source as a zero-radius point light."

The following examples create a sphere light with a 0.05 scene-unit radius:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-sphere-light]
         :end-before: # [/snippet:doc-sphere-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-sphere-light-python]
         :end-before: # [/snippet:doc-sphere-light-python]
         :dedent:
