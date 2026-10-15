.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Overview
========

ovrtx renders six intrinsic UsdLux light types. Choose a light whose emitting
shape matches the source you want to represent.

.. csv-table::
   :header: "Light type", "Typical use"
   :widths: 30, 70
   :class: compact-table

   ":doc:`Distant Light <distant_light>`", "Sunlight, moonlight, or another directional source that is effectively infinitely far away."
   ":doc:`Sphere Light <sphere_light>`", "A bulb or another source that emits outwards in every direction."
   ":doc:`Rect Light <rect_light>`", "A rectangular panel or softbox that emits from one side."
   ":doc:`Disk Light <disk_light>`", "A circular panel or downlight that emits from one side."
   ":doc:`Cylinder Light <cylinder_light>`", "A fluorescent, neon, or other tubular source."
   ":doc:`Dome Light <dome_light>`", "Image-based or constant-color environment lighting around the scene."

Light Units
-----------

UsdLux defines ``inputs:intensity`` as the base luminance of an unnormalized
light. A value of 1 at zero exposure corresponds to 1 nit
(:math:`\mathrm{cd}/\mathrm{m}^2`) when the light is viewed normally by a
camera at exposure value 0. ``inputs:exposure`` applies a base-2 multiplier,
so the scalar emission is:

.. math::

   L = \mathtt{inputs:intensity} \times 2^{\mathtt{inputs:exposure}}

For example, intensity 1000 at exposure 2 produces the same scalar emission as
intensity 4000 at exposure 0, before color and normalization are applied.

The meaning changes when ``inputs:normalize`` is enabled:

* Sphere, disk, rect, and cylinder lights divide luminance by their world-space
  emitting surface area. This keeps total emitted power constant when you alter
  their dimensions or transform scale.
* A normalized distant light treats intensity at zero exposure as illuminance
  in lux on a surface facing the light. Its angular diameter supplies the size
  factor.
* Dome lights ignore normalization.

Radius, width, height, and length use scene units before the prim's transform is
applied. Set ``metersPerUnit`` on the stage so those values have an unambiguous
physical scale. Distant-light angle uses degrees. Color temperature uses Kelvin.
Color and the diffuse and specular multipliers are unitless.

Further Reading
---------------

Refer to the `UsdLux 25.05 overview <https://openusd.org/25.05/api/usd_lux_page_front.html>`_
and `UsdLuxLightAPI reference <https://openusd.org/25.05/api/class_usd_lux_light_a_p_i.html>`_
for the complete OpenUSD lighting model.
