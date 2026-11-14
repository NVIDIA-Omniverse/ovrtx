.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-depth-camera-howto:

How-To
======

Start with :doc:`set_up_depth_product`, then use :doc:`spec_sheet_profile`
to match a device and :doc:`noise_and_confidence` to tune noise and coverage.

The model reads and publishes outputs on one RenderProduct; its schema and
parameters belong on the ``Camera``. See :doc:`../attributes` for controls,
:doc:`../outputs` for formats and invalid values, and
:doc:`../../../troubleshooting/symptoms` when the result is wrong.

.. toctree::
   :maxdepth: 1

   set_up_depth_product
   spec_sheet_profile
   noise_and_confidence

Related
-------

- :doc:`USD Attributes <../attributes>` — the fourteen attributes in their groups, with units, clamps and relations.
- :doc:`Outputs <../outputs>` — the five outputs, what a zero means, which frame the distance image and the point cloud are in, and the visualization modes.
- :doc:`Output Configuration <../../../common/output_configuration>` — how a RenderProduct and its RenderVars fit together.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — applying an API schema and overriding its attributes.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — reading results back through the output container.
