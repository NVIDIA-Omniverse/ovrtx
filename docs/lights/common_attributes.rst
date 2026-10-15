.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Common Attributes
=================

Overview
--------

Concrete UsdLux light types automatically provide ``UsdLuxLightAPI`` and its
common emission controls. These attributes work with the type-specific shape
and dimensions described on each light page. Refer to :doc:`Overview <index>`
for the units and normalization model.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:intensity = 1``", "Base luminance in nits for an unnormalized light. ``DistantLight`` overrides the fallback to 50000."
   "``float inputs:exposure = 0``", "Base-2 exposure in stops. Each increase of one doubles emission."
   "``color3f inputs:color = (1, 1, 1)``", "Emission color in the rendering color space."
   "``bool inputs:enableColorTemperature = false``", "Enables multiplication by the color computed from ``inputs:colorTemperature``."
   "``float inputs:colorTemperature = 6500``", "White-point temperature in Kelvin. The valid range is 1000–10000 K; lower values appear warmer and higher values cooler."
   "``bool inputs:normalize = false``", "Divides emission by a type-specific size factor so changing source size does not change total power."
   "``float inputs:diffuse = 1``", "Unitless multiplier for diffuse material response. This is a non-physical control."
   "``float inputs:specular = 1``", "Unitless multiplier for specular material response. This is a non-physical control."

Intensity
---------

The following comparison increases intensity while holding exposure at zero:

.. figure:: ../img/light-common-intensity.avif
   :alt: Rect lights with intensity values of 250000, 1000000, and 4000000
   :align: center

   *Intensity scales light emission linearly.*

Exposure
--------

The following comparison changes exposure from -2 to +2 stops:

.. figure:: ../img/light-common-exposure.avif
   :alt: Rect lights with exposure values of negative 2, 0, and positive 2
   :align: center

   *Each increase of one exposure stop doubles emission.*

Color
-----

The following comparison changes the energy-linear emission color:

.. figure:: ../img/light-common-color.avif
   :alt: Rect lights with white, blue, and red emission colors
   :align: center

   *The color attribute tints all light contributions.*

Enable Color Temperature
------------------------

The following comparison toggles color temperature at 3000 K:

.. figure:: ../img/light-common-enable-color-temperature.avif
   :alt: Rect lights with 3000 Kelvin color temperature disabled and enabled
   :align: center

   *Color temperature affects emission only when enabled.*

Color Temperature
-----------------

The following comparison increases color temperature from 2000 to 10000 K:

.. figure:: ../img/light-common-color-temperature.avif
   :alt: Rect lights with color temperatures of 2000, 6500, and 10000 Kelvin
   :align: center

   *Lower temperatures appear warmer; higher temperatures appear cooler.*

Normalize
---------

The following comparison toggles normalization on the same small rect light:

.. figure:: ../img/light-common-normalize.avif
   :alt: Rect lights with normalization disabled and enabled
   :align: center

   *Normalization divides luminance by emitting area to preserve total power as source size changes.*

Diffuse
-------

The following comparison changes the diffuse contribution multiplier:

.. figure:: ../img/light-common-diffuse.avif
   :alt: Rect lights with diffuse contribution multipliers of 0, 0.5, and 1
   :align: center

   *Diffuse changes the light's contribution to diffuse material response.*

Specular
--------

The following comparison changes the specular contribution multiplier:

.. figure:: ../img/light-common-specular.avif
   :alt: Rect lights with specular contribution multipliers of 0, 0.5, and 1
   :align: center

   *Specular changes the light's contribution to specular material response.*

Authoring Common Attributes
---------------------------

The following examples configure the same common attributes in USDA and with
the USD Python API:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-common-light-attributes]
         :end-before: # [/snippet:doc-common-light-attributes]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-common-light-attributes-python]
         :end-before: # [/snippet:doc-common-light-attributes-python]
         :dedent:

Further Reading
---------------

Refer to the `UsdLuxLightAPI reference <https://openusd.org/25.05/api/class_usd_lux_light_a_p_i.html>`_
for the complete OpenUSD common-light model.
