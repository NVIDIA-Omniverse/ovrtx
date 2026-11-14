.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-radar-howto:

How-To
======

Start with :doc:`set_up_sensor`, which builds the panel-field scene with an
approaching cube. The runnable :doc:`Python <../../../../examples/python_sensor_radar>`
and :doc:`C <../../../../examples/c_sensor_radar>` examples also offer a simpler
two-cube scene.

For a new device, follow these tasks in order; otherwise go straight to the
one you need:

- :doc:`spec_sheet_profile` — plan a profile from a vendor specification.
- :doc:`choose_parameters` — map specifications to attributes and identify values to calibrate.
- :doc:`scan_configurations` — alternate scans and identify which produced a frame.
- :doc:`moving_targets` — enable the motion BVH and advance animation to obtain radial velocity.
- :doc:`validate_parameterization` — check the profile using controlled scenes and repeated measurements.

See :doc:`../attributes` for controls and :doc:`../outputs` for detections.

.. toctree::
   :maxdepth: 1

   set_up_sensor
   spec_sheet_profile
   choose_parameters
   scan_configurations
   moving_targets
   validate_parameterization

Related
-------

- :doc:`USD Attributes <../attributes>` — attribute groups, units and coordinate controls.
- :doc:`Outputs <../outputs>` — the ``PointCloud`` channels and params of a radar frame, and how to read them.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — instantiating a sensor prim, applying its schema and overriding attributes.
- :doc:`Output Configuration <../../../common/output_configuration>` — RenderProducts, RenderVars, the motion BVH modes and the other renderer options sensors depend on.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — the output container and reading results back.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — what every sensor accepts while it runs; :ref:`the radar's own rules <sensors-nonvisual-radar-attributes-runtime>` are on its USD Attributes page.
