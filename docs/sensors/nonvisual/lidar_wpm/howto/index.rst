.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-wpm-howto:

How-To
======

Configure a Lidar generic wpm model sensor with :doc:`firing_pattern`, then
choose how to process its returns:

- :doc:`return_processing` — select detections and their output representation.
- :doc:`intensity` — control how return strength is encoded.
- :doc:`tile_lidars` — combine sensors in one RenderProduct.
- :doc:`runtime_updates` — change a running sensor and verify the accepted profile.

See :doc:`../attributes` for controls and :doc:`../outputs` for the output layout.

.. toctree::
   :maxdepth: 1

   firing_pattern
   return_processing
   intensity
   tile_lidars
   runtime_updates

Related
-------

- :doc:`USD Attributes <../attributes>` — controls, units, defaults and constraints.
- :doc:`Outputs <../outputs>` — the point cloud this model delivers, its channels, params and layouts, and how to read it.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — instantiating a sensor prim and applying its schema.
- :doc:`Output Configuration <../../../common/output_configuration>` — how a RenderProduct and its RenderVars fit together.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — reading results back through the output container.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — shared update behavior.
- :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>` — the non-visual material labels and how to author them.
- :doc:`Lidar generic core model How-To <../../lidar_core/howto/index>` — the task pages of the other lidar model, including the Motion Artifacts page that applies here.
- :doc:`Symptom Index <../../../troubleshooting/symptoms>` — what to check when a how-to's result is not what you expected.
