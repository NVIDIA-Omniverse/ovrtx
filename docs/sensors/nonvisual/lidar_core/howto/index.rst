.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-core-howto-index:
.. _sensors-nonvisual-lidar-core-howto:

How-To
======

Start from a working Lidar generic core model sensor
(:doc:`../../../first_sensor`). Choose a task below:

- :doc:`firing_pattern` — schedule emitters and aim their rays.
- :doc:`field_of_view` — limit return range and the accepted rotary scan sector.
- :doc:`output_shaping` — choose coordinates, reference frame and delivery cadence.
- :doc:`motion_artifacts` — simulate motion during a scan and choose compensation.
- :doc:`intensity` — tune signal strength and dropped returns.
- :doc:`spec_sheet_profile` — distinguish measured specifications from estimates.

The :doc:`../tutorials/index` apply profiling to rotary and solid-state devices.
See :doc:`../attributes` for controls and :doc:`../outputs` for the point-cloud layout.

.. toctree::
   :maxdepth: 1

   firing_pattern
   field_of_view
   output_shaping
   motion_artifacts
   intensity
   spec_sheet_profile

Related
-------

- :doc:`USD Attributes <../attributes>` — the attribute groups that matter, their units, defaults and relations.
- :doc:`Outputs <../outputs>` — the point cloud this model delivers, its channels and params, and how to read it.
- :doc:`Tutorials <../tutorials/index>` — three devices parameterized end to end, with the finished profiles.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — instantiating a sensor prim and applying its schema.
- :doc:`Output Configuration <../../../common/output_configuration>` — how a RenderProduct and its RenderVars fit together.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — reading results back through the output container.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — what every sensor accepts while it runs.
- :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>` — the non-visual material labels and how to author them.
- :doc:`Symptom Index <../../../troubleshooting/symptoms>` — what to check when a how-to's result is not what you expected.
