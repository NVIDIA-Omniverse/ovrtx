.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-common-index:

Common Concepts
===============

Configure a sensor prim, request outputs through a RenderProduct, step the
renderer and map the results. :doc:`Your First Lidar Sensor <../first_sensor>`
walks through this sequence; camera users can start with
:doc:`../cameras`.

These concepts apply across models except where stated; partial-output
policies differ by model.

What each page covers
---------------------

- :doc:`sensor_configuration` — prims, applied schemas, identity and timing attributes.
- :doc:`output_configuration` — RenderProducts, RenderVars, channels and renderer options.
- :doc:`sensor_outputs` — tensors, params, counts, validity, mapping and lifetime.
- :doc:`multi_rate` — capture rates, stepping and partial-output delivery.
- :doc:`validation` — check a definition before rendering, through C++ or Python.
- :doc:`runtime_updates` — live edits, fixed parameters and rejected updates.

.. toctree::
   :maxdepth: 1

   sensor_configuration
   output_configuration
   sensor_outputs
   multi_rate
   validation
   runtime_updates

Related
-------

- :doc:`Your First Lidar Sensor <../first_sensor>` — the worked walk-through that applies these concepts to one sensor, from prim to consumed output.
- :doc:`Overview <../overview>` — what ovrtx sensors are for, the modalities, and how this documentation is organized.
- :doc:`Cameras <../cameras>` — camera output straight from the renderer: attributes, render modes, outputs and the camera how-tos.
- :doc:`Visual Sensors <../visual/index>` — the Camera generic core model and the Camera single-view stereo depth model.
- :doc:`Non-Visual Sensors <../nonvisual/index>` — the lidar, radar and acoustic models.
- :doc:`Reference <../reference/index>` — the generated schema tables, the composite output types and the glossary.
- :doc:`Troubleshooting <../troubleshooting/index>` — the symptom index and the by-design limitations.
