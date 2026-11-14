.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-acoustic-howto:

How-To
======

Build a sensor with :doc:`set_up_sensor`, expand it with
:doc:`array_topology`, then use :doc:`live_retuning` to change it while it runs.
Read these in order for your first acoustic sensor.

See :doc:`../attributes` for parameter meanings and :doc:`../outputs` for the
``SignalWays`` layout. Start with :doc:`../../../first_sensor` if you are new
to ovrtx.

.. toctree::
   :maxdepth: 1

   set_up_sensor
   array_topology
   live_retuning

Related
-------

- :doc:`USD Attributes <../attributes>` — controls, array topology and runtime updates.
- :doc:`Outputs <../outputs>` — signal ways, the ``SignalWays`` channels and params, and reading an envelope.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — instantiating a sensor prim and applying its schema.
- :doc:`Output Configuration <../../../common/output_configuration>` — RenderProducts, RenderVars and the motion BVH switch.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — the output container, mapping the ``SignalWays`` output after a step and reading it back.
- :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>` — labeling the surfaces a non-visual sensor responds to.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — shared update behavior.
- :doc:`Lidar generic core model <../../lidar_core/index>` — geometric lidar point clouds.
- :doc:`Acoustic example <../../../../examples/python_sensor_acoustic>` — the runnable one-transducer scene the set-up page takes its snippets from and the array page starts from.
