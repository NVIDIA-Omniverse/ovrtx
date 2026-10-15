.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Shaping & IES
=============

Overview
--------

Apply ``UsdLuxShapingAPI`` to an area light when you need to concentrate,
limit, or tint its angular emission. You can shape emission procedurally with
focus and cone controls, or use an IES profile measured from a real luminaire.

Shaping changes where a light sends its energy. The light's dimensions and
:doc:`common intensity, exposure, color, and normalization controls <index>`
still determine its source geometry and base emission.

Cone And Focus
--------------

Cone controls limit emission around the light's primary axis. Focus
concentrates emission toward that axis without establishing a hard cutoff.
The default primary axis is local -Z. Sphere and cylinder lights emit on both
sides unless a cone restricts them. Use ``omni:rtx:shaping:forwardAxis`` to
orient shaping in local space without rotating the light prim.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``float inputs:shaping:cone:angle = 90``", "Angular cutoff from the primary axis, in degrees. Emission outside the cone is zero."
   "``float inputs:shaping:cone:softness = 0``", "Unitless edge transition. Use 0 for a hard cutoff and values through 1 for an increasingly smooth transition."
   "``float inputs:shaping:focus = 0``", "Unitless exponent. Higher non-negative values concentrate emission toward the primary axis."
   "``color3f inputs:shaping:focusTint = (0, 0, 0)``", "Color applied away from the focused axis. The default fades off-axis emission toward black."
   "``token omni:rtx:shaping:forwardAxis = ""-Z""``", "Local shaping and IES axis: ``-Z``, ``+Z``, ``-Y``, ``+Y``, ``-X``, or ``+X``. This Omni API attribute is auto-applied to sphere, disk, rect, and cylinder lights."

Cone Angle
^^^^^^^^^^

The following comparison reduces cone angle from 90 to 30 degrees:

.. figure:: ../img/light-shaping-cone-angle.avif
   :alt: Rect lights with cone angles of 90, 60, and 30 degrees
   :align: center

   *Smaller cone angles restrict emission to a narrower region.*

Cone Softness
^^^^^^^^^^^^^

The following comparison increases cone softness while holding cone angle at
35 degrees:

.. figure:: ../img/light-shaping-cone-softness.avif
   :alt: Rect lights with cone softness values of 0, 0.5, and 1
   :align: center

   *Higher softness values produce a smoother transition at the cone edge.*

Focus
^^^^^

The following comparison increases focus from 0 to 8:

.. figure:: ../img/light-shaping-focus.avif
   :alt: Rect lights with focus values of 0, 2, and 8
   :align: center

   *Higher focus values concentrate more emission around the primary axis.*

Focus Tint
^^^^^^^^^^

The following comparison changes focus tint while holding focus at 4:

.. figure:: ../img/light-shaping-focus-tint.avif
   :alt: Focused rect lights with black, blue, and red focus tints
   :align: center

   *Focus tint colors the off-axis portion of the shaped emission.*

Forward Axis
^^^^^^^^^^^^

The following comparison changes the local forward axis without rotating the
sphere light:

.. figure:: ../img/light-shaping-forward-axis.avif
   :alt: Sphere lights shaped along the local negative Z, positive X, and negative X axes
   :align: center

   *Changing the forward axis redirects the shaped emission in local space.*

The following examples apply ``UsdLuxShapingAPI`` and configure cone and focus
shaping:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_shaping.usda
         :language: usda
         :start-after: # [snippet:doc-light-shaping]
         :end-before: # [/snippet:doc-light-shaping]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-light-shaping-python]
         :end-before: # [/snippet:doc-light-shaping-python]
         :dedent:

IES Profiles
------------

An IES profile stores luminous intensity samples over direction. Assigning a
profile lets a light reproduce the measured beam distribution of a luminaire.
The profile is evaluated in the light's local space. Rotate the light or set
``omni:rtx:shaping:forwardAxis`` to aim the distribution.

.. note::

   UsdLux uses an IES file only as an angular distribution. To preserve its
   sampled candela values as measured light output, apply
   ``PhysicalLightIlluminantAPI`` and set
   ``inputs:shaping:ies:normalize`` to false. See
   :ref:`IES Profiles And Physical Units <physical-lighting-ies>` for the
   resulting unit conversion, multiplier, and normalization behavior.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``asset inputs:shaping:ies:file``", "Path to an IES profile using the LM-63 photometric data format."
   "``float inputs:shaping:ies:angleScale = 0``", "Rescales the profile's vertical polar angle. Zero preserves the original distribution. For a downward-facing profile, positive values below 1 narrow it and values above 1 broaden it."
   "``bool inputs:shaping:ies:normalize = false``", "Normalizes the profile so it changes angular distribution while preserving overall energy."

IES File
^^^^^^^^

The following comparison shows the disk light without a profile and with the
BEGA 50898.4K3 profile:

.. figure:: ../img/light-shaping-ies-file.avif
   :alt: Disk lights without an IES profile and with the BEGA 50898.4K3 profile
   :align: center

   *An IES profile replaces the unshaped angular distribution with measured photometric data.*

IES Angle Scale
^^^^^^^^^^^^^^^

The following comparison changes angle scale from 0.5 to 1.5:

.. figure:: ../img/light-shaping-ies-angle-scale.avif
   :alt: IES disk lights with angle scale values of 0.5, 1, and 1.5
   :align: center

   *For this downward-facing profile, values below 1 narrow the distribution and values above 1 broaden it.*

IES Normalization
^^^^^^^^^^^^^^^^^

The following comparison toggles profile normalization:

.. figure:: ../img/light-shaping-ies-normalize.avif
   :alt: IES disk lights with profile normalization disabled and enabled
   :align: center

   *Normalization prevents the profile amplitude from changing the light's overall energy.*

Use a negative angle scale for an upward-facing profile. Values between -1 and
0 narrow that profile; values below -1 broaden it.

The following examples assign the bundled BEGA 50898.4K3 profile and preserve
the light's overall energy:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_shaping.usda
         :language: usda
         :start-after: # [snippet:doc-light-shaping-ies]
         :end-before: # [/snippet:doc-light-shaping-ies]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-light-shaping-ies-python]
         :end-before: # [/snippet:doc-light-shaping-ies-python]
         :dedent:

Further Reading
---------------

Refer to the `UsdLuxShapingAPI reference <https://openusd.org/25.05/api/class_usd_lux_shaping_a_p_i.html>`_
for the OpenUSD shaping model.
