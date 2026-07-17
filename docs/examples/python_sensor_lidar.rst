.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Lidar Sensor
====================

This example loads ``lidar_example.usda``, renders a lidar ``PointCloud``,
maps the composite render variable to CPU memory, and visualizes detections in
`rerun.io <https://rerun.io/>`_. Point color is derived from the ``Intensity``
channel.

The scene is Z-up and contains a lidar at ``(0, 0, 1)`` rotated to look along
world +X, an asphalt ground plane, and a concrete cube. The USD requests
``Coordinates``, ``Intensity``, ``Counts``, and ``TimeOffsetNs`` channels.

.. pull-quote::

   *“Create a Python sensor example that loads a scene containing a configured lidar, warms up the sensor pipeline, renders one point-cloud frame, reads valid point data using the count channel, prints summary statistics, and optionally visualizes the points with intensity-based colors.”*

.. image:: ../../img/example-sensor-lidar.avif
   :alt: Lidar sensor example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_

Running
-------

.. code-block:: bash

   cd examples/python/lidar
   uv run main.py

Options
^^^^^^^

.. list-table::
   :header-rows: 1

   * - Flag
     - Description
   * - ``--scene PATH``
     - Load a different USDA scene
   * - ``--no-rr``
     - Disable Rerun visualization and print only the frame summary
   * - ``--rrd PATH``
     - Write a Rerun recording instead of spawning a viewer

Expected console output values vary, but a successful run prints the number of
valid points, mean intensity, and maximum time offset in nanoseconds.
