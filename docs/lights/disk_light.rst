.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Disk Light
==========

A ``DiskLight`` emits from one side of a circular disk along its local -Z axis.
Use it for circular panels and downlights. It also uses the
:doc:`common light attributes <index>`.

.. figure:: ../img/light-type-disk.avif
   :alt: A test scene lit by a circular disk area light
   :align: center

   *A disk light produces illumination from a circular emitting surface.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:radius = 0.5``", "Disk radius in scene units."

The following examples create a disk light with a 0.25 scene-unit radius:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-disk-light]
         :end-before: # [/snippet:doc-disk-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-disk-light-python]
         :end-before: # [/snippet:doc-disk-light-python]
         :dedent:
