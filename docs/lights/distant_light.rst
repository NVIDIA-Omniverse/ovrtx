.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Distant Light
=============

A ``DistantLight`` emits parallel light along its local -Z axis. Its position
does not affect illumination; rotate it to set the direction. Increasing its
angular diameter produces softer shadows. It also uses the
:doc:`common light attributes <index>`.

.. figure:: ../img/light-type-distant.avif
   :alt: A test scene lit by a distant light, producing directional illumination and shadows
   :align: center

   *A distant light illuminates the scene from one direction.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:angle = 0.53``", "Angular diameter in degrees, clipped to the range 0 ≤ angle < 360. Zero produces parallel rays; larger values soften shadows."

The following examples create a distant light approximating the angular size
and brightness of the Sun:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-distant-light]
         :end-before: # [/snippet:doc-distant-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-distant-light-python]
         :end-before: # [/snippet:doc-distant-light-python]
         :dedent:
