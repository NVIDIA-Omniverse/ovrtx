.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Radar Sensor
====================

This example loads ``radar_example.usda``, renders a radar ``PointCloud``,
maps the composite render variable to CPU memory, and visualizes detections in
`rerun.io <https://rerun.io/>`_. Point color is derived from signed
``RadialVelocityMs``: blue is approaching the sensor, green is near zero, and
red is receding.

This example retains the deprecated standalone population APIs because attached
ovstage rendering in ovrtx 0.4 does not preserve the radar motion output
demonstrated here. Use ovstage for CPU stage workflows that do not
depend on radar motion history.

The scene is Z-up and contains a radar at ``(0, 0, 1)`` rotated to look along
world +X, an asphalt ground plane, a moving steel cube, and a fixed concrete
cube. The moving cube advances toward the radar across 10 simulation steps.

.. pull-quote::

   *“Create a Python sensor example that loads a scene containing a configured radar and moving target, advances scene time over multiple steps, reads valid detections and signed radial velocity, prints per-step summaries, and optionally visualizes detections with velocity-based colors.”*

.. image:: ../../img/example-sensor-radar.avif
   :alt: Radar sensor example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_

Running
-------

.. code-block:: bash

   cd examples/python/radar
   uv run main.py

Options
^^^^^^^

.. list-table::
   :header-rows: 1

   * - Flag
     - Description
   * - ``--scene PATH``
     - Load a different USDA scene
   * - ``--steps N``
     - Number of animated radar steps
   * - ``--no-rr``
     - Disable Rerun visualization and print only the per-step summary
   * - ``--rrd PATH``
     - Write a Rerun recording instead of spawning a viewer

Expected console output values vary, but a successful run prints per-step valid
point counts and radial velocity min/max values.
