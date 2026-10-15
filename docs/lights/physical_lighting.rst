.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Physical Lighting
=================

Overview
--------

Physical lighting lets you describe light color and brightness using measured
quantities. You can specify luminous power in lumens, target illuminance in lux,
or an illuminant spectrum. This is useful when matching product datasheets,
on-set measurements, or real lighting conditions.

The physical-lighting schemas are codeless API schemas supplied with ovrtx.
Apply the schema that matches the light type:

.. csv-table::
   :header: "API schema", "Supported light types", "Provides"
   :widths: 31, 31, 38
   :class: compact-table

   "``PhysicalLightIlluminantAPI``", "Rect, Sphere, Disk, Cylinder, Dome, and Distant", "Spectral illuminant selection without photometric brightness controls."
   "``PhotometricAreaLightAPI``", "Rect, Sphere, Disk, and Cylinder", "Power in lumens or target illuminance in lux at a distance in meters."
   "``PhotometricDomeLightAPI``", "Dome", "Illuminance in lux on an upward-facing surface."
   "``PhotometricDistantLightAPI``", "Distant", "Illuminance in lux on a surface perpendicular to the light."

Each photometric schema automatically applies ``PhysicalLightIlluminantAPI``.
You do not need to apply both schemas yourself.

Illuminants
-----------

An illuminant describes the spectrum emitted by a light. In RGB rendering,
ovrtx converts that spectrum to a color. In spectral rendering, ovrtx samples
the spectrum directly. See :doc:`../sensors/cameras/render_modes/spectral_rendering`
for the required startup configuration and paired RGB/spectral comparisons.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``token physical:illuminant = ""white""``", "Selects ``white``, ``blackbody``, ``illuminant D``, or ``custom``."
   "``float2[] physical:customIlluminant``", "Ordered wavelength and radiance pairs. Wavelengths are in nanometers and must increase monotonically. Values outside the supplied wavelength range emit no energy."

The following comparison holds luminous power constant while changing the
illuminant:

.. figure:: ../img/light-physical-illuminant.avif
   :alt: Rect lights using white, 3000 Kelvin blackbody, 6504 Kelvin illuminant D, and CIE FL5 fluorescent illuminants
   :align: center

   *Illuminant selection changes spectral color while photometric power remains constant.*

``blackbody`` and ``illuminant D`` use ``inputs:colorTemperature`` as their
temperature in Kelvin. They do not require ``inputs:enableColorTemperature``.
The ``custom`` mode uses ``physical:customIlluminant``. The ``white`` mode
matches the white point of the rendering color space.

Area-Light Power
----------------

``PhotometricAreaLightAPI`` supports total luminous power:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float photometric:power = 1600``", "Total luminous flux in lumens. Must be non-negative."

The renderer accounts for source size, shape, color, illuminant, and shaping
when converting power to emitted radiance. Changing those properties therefore
does not change the requested total luminous flux.

.. figure:: ../img/light-physical-power.avif
   :alt: Rect lights with luminous power values of 1600, 6400, and 16000 lumens
   :align: center

   *Increasing photometric power increases total light output in lumens.*

.. warning::

   Applying ``PhotometricAreaLightAPI`` gives the light its 1600-lumen schema
   fallback even when you do not author ``photometric:power``.

Area-Light Illuminance At Distance
----------------------------------

You can target a measured illuminance instead of total power:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``float photometric:illuminance = 0``", "Target illuminance in lux on a surface directly facing the light. Must be non-negative."
   "``float photometric:illuminance:distance = 0``", "Distance from the light to the measurement surface in meters. A positive value enables the illuminance target."

When both values are positive, the illuminance target takes precedence over
``photometric:power``. Set power to zero when authoring this mode so your intent
is explicit.

.. figure:: ../img/light-physical-illuminance.avif
   :alt: Rect lights targeting 250, 1000, and 4000 lux at two meters
   :align: center

   *Illuminance sets the light level measured at the reference distance.*

Increasing the reference distance requires more output to maintain the same
illuminance at that distance:

.. figure:: ../img/light-physical-illuminance-distance.avif
   :alt: Rect lights targeting 1000 lux at distances of one, two, and four meters
   :align: center

   *A farther reference distance produces a brighter source for the same target lux value.*

Dome And Distant Illuminance
----------------------------

Dome and distant lights use illuminance without a reference distance:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``float photometric:illuminance = 10000``", "On ``PhotometricDomeLightAPI``, specifies lux received by an upward-facing surface."
   "``float photometric:illuminance = 10000``", "On ``PhotometricDistantLightAPI``, specifies lux received by a surface perpendicular to the light direction."

.. _physical-lighting-ies:

IES Profiles And Physical Units
-------------------------------

UsdLux uses an IES file as an angular distribution. On its own, it does not
define the profile's sampled candela values as the light's measured output.
``inputs:shaping:ies:normalize`` controls whether that distribution is
normalized to preserve the light's existing energy.

Apply ``PhysicalLightIlluminantAPI`` directly to use the measured candela
values from the IES file. This changes IES processing in these ways:

* ovrtx converts the profile's candela values to emitted radiance using the
  area of the light source.
* ``inputs:intensity`` remains a linear multiplier and ``inputs:exposure``
  remains a base-2 multiplier. Use intensity 1 and exposure 0 to preserve the
  measured magnitude.
* The API does not force IES normalization. Set
  ``inputs:shaping:ies:normalize`` to false to preserve the measured candela
  values. When it is true, ovrtx divides the samples by the profile's
  integrated power, so their original measured magnitude is not preserved.

``PhotometricAreaLightAPI`` automatically applies
``PhysicalLightIlluminantAPI``, but it also supplies a default
``photometric:power`` of 1600 lumens. A positive power target forces correct
IES unit conversion and normalization regardless of
``inputs:shaping:ies:normalize``. In that mode, the IES profile controls only
the angular distribution and ``photometric:power`` controls total luminous
flux.

To make the IES file's measured candela values determine brightness, apply only
``PhysicalLightIlluminantAPI``, set ``inputs:intensity`` to 1,
``inputs:exposure`` to 0, and set ``inputs:shaping:ies:normalize`` to false.
Use ``PhotometricAreaLightAPI`` when the IES distribution should be normalized
and rescaled to a separately specified lumen value.

Interactions With Other Controls
--------------------------------

The photometric target determines brightness while preserving the chromaticity
from ``inputs:color`` and the selected illuminant. ``inputs:diffuse`` and
``inputs:specular`` continue to control material response.

An IES profile from :doc:`Shaping & IES <shaping_and_ies>` defines angular
distribution. Its brightness behavior depends on the physical-lighting schema
as described in :ref:`physical-lighting-ies`.

Authoring Physical Lights
-------------------------

The following examples show a lumen-powered area light, an area light targeting
lux at a measured distance, and a distant light targeting lux. These codeless
schemas use generic USD API application and attribute access in Python.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/physical_lighting.usda
         :language: usda
         :start-after: # [snippet:doc-physical-lighting]
         :end-before: # [/snippet:doc-physical-lighting]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-physical-lighting-python]
         :end-before: # [/snippet:doc-physical-lighting-python]
         :dedent:

Further Reading
---------------

Refer to :doc:`Common Attributes <common_attributes>` for color and material
response controls, and :doc:`Shaping & IES <shaping_and_ies>` for angular
emission profiles.
