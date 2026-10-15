.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Acoustic Sensor
=======================

This example loads ``acoustic_example.usda``, renders one acoustic
``SignalWays`` frame, maps the composite render variable to CPU memory, and plots
the echo envelopes in `rerun.io <https://rerun.io/>`_.

The scene is Z-up and contains an acoustic sensor at ``(0, 0, 0.5)`` oriented to
fire along world +X, an asphalt ground plane, and a concrete wall whose near face
stands at 3.0 m. The example reports the strongest echo, which locates the wall.

.. pull-quote::

   *“Create a Python sensor example that loads a scene containing a configured ultrasonic sensor facing a wall, warms up the sensor pipeline, renders one frame, reads the echo envelopes from the composite output, converts the strongest sample to a range, and optionally plots the envelopes.”*

Unlike the point-cloud sensors, the acoustic model reports an amplitude series
per signal way rather than discrete returns, and publishes the frame's extent as
composite parameters rather than as a ``Counts`` channel. For the channel and
parameter reference, see :doc:`../sensors/acoustic`.

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_

Running
-------

.. code-block:: bash

   cd examples/python/acoustic
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
   * - ``--log [PATH]``
     - Write a carb log file, by default under ``_output/``

A successful run prints one summary line. Amplitude carries detector noise and
varies slightly between runs, but the range locates the wall at 3.0 m:

.. code-block:: text

   signal ways=1, responding=1, median peak range=3.022 m, median peak amplitude=4593
