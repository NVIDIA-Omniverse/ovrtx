.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-index:
.. _sensors-nonvisual:

Non-Visual Sensors
==================

Non-visual sensors simulate lidar, radar and ultrasonic measurements by tracing
rays through the scene. They produce point clouds, radar detections or echo
envelopes. Surface materials affect the strength and timing of returns;
wave-propagation models also account for paths with multiple surface interactions.

Sensor models
-------------

ovrtx provides five non-visual sensor models. The sensor prim type and applied
API schema select the model. Each model has its own attributes and output
channels; see :doc:`Sensor Configuration <../common/sensor_configuration>`
for the shared setup.

.. list-table::
   :header-rows: 1
   :widths: 23 49 28
   :class: compact-table

   * - Model
     - Simulation
     - Output
   * - :doc:`Lidar generic core <lidar_core/index>`
     - Rotary or solid-state scanning lidar, using scheduled emitter firings
       and geometric ray intersections.
     - :doc:`PointCloud <lidar_core/outputs>`: lidar returns.
   * - :doc:`Lidar generic wpm <lidar_wpm/index>`
     - Pulsed time-of-flight lidar with wave propagation, surface interactions
       and detector response.
     - :doc:`PointCloud <lidar_wpm/outputs>`: returns derived from the received
       signal and the selected return-processing mode.
   * - :doc:`Radar generic wpmDmat <radar_wpm_dmat/index>`
     - Radio-wave propagation into a detection matrix, including multiple
       bounces, material response and transmit/receive antenna patterns.
     - :doc:`PointCloud <radar_wpm_dmat/outputs>`: detections with position,
       radial velocity and radar cross section (RCS).
   * - :doc:`Acoustic generic wpm <acoustic_wpm/index>`
     - Ultrasonic pulses. Each firing event selects a transmitting mount and
       a group of receiving mounts.
     - :doc:`SignalWays <acoustic_wpm/outputs>`: echo amplitude over time for
       each receiving mount and channel ID.

   * - :doc:`Generic wpm <generic_wpm/index>`
     - Scalar electromagnetic or mechanical propagation with independently
       authored transmitter, receiver and ray patterns.
     - :doc:`Contributions <generic_wpm/outputs>`: raw paths, scalar transport
       power and validity, before detector processing.

.. _sensors-nonvisual-index-which-lidar:

The two lidar models both use an ``OmniLidar`` prim. Apply
``OmniSensorGenericLidarCoreAPI`` for geometric scanning, or
``OmniSensorGenericLidarWpmAPI`` when pulse propagation and detector response
matter. Their attributes and output channels differ; the
:doc:`Lidar wpm overview <lidar_wpm/index>` compares them.

Radar uses ``OmniRadar`` with ``OmniSensorGenericRadarWpmDmatAPI``. Its default
carrier frequency is approximately 77 GHz. One radar can have multiple scan
configurations, such as near and far scans; see the
:doc:`radar overview <radar_wpm_dmat/index>`.
Acoustic sensors use ``OmniAcoustic`` with ``OmniSensorGenericAcousticWpmAPI``.
Their repeating firing sequence determines which mounts transmit and listen.
The Generic wpm model uses ``OmniGeneralSensor`` with
``OmniSensorGenericWpmAPI``. Choose it when your application consumes raw path
contributions and supplies its own detector processing.

Configuration and outputs
-------------------------

Bind materials with non-visual labels to describe surface response. The labels
are separate from visual shading; some models can also use visual material
inputs. See :doc:`Non-Visual Sensor Materials <../../materials/nonvisual_sensor_materials>`.

Motion BVH accounts for sensor and geometry motion within a scan. Use ``AUTO``
or ``ENABLE`` for lidar and radar motion effects and for acoustic simulation. See :ref:`Motion BVH <sensors-common-output-configuration-motion-bvh>`
for renderer configuration and hardware requirements.

Each model returns a composite output containing named tensors and parameters.
See :doc:`Sensor Outputs <../common/sensor_outputs>` for mapping and reading it.
Lidar and radar positions default to spherical coordinates: azimuth and
elevation in degrees, and range in meters. Cartesian output uses x, y and z in
meters. Acoustic output contains signal samples rather than positions.
Generic wpm output uses a dense contribution layout with explicit validity.
The linked Outputs pages above define each model's channels and coordinate options.

Examples
--------

Start with :doc:`Your First Lidar Sensor <../first_sensor>` for a Lidar core setup.
The runnable lidar example is available in
:doc:`Python <../../examples/python_sensor_lidar>` and
:doc:`C <../../examples/c_sensor_lidar>`; the Lidar core tutorials configure
three physical devices. For Lidar wpm, see the rotary example scene in
:doc:`Configure a Firing Pattern <lidar_wpm/howto/firing_pattern>`.

The radar example is available in :doc:`Python <../../examples/python_sensor_radar>`
and :doc:`C <../../examples/c_sensor_radar>`.

.. figure:: ../../img/sensors/nonvisual/radar_field_hero.avif
   :align: center
   :alt: Radar scene with steel panels and a moving cube, beside a top view of detections colored by signed radial velocity.
   :width: 1200

   *Radar example: a steel cube moves among steel panels over asphalt. Left:
   camera view. Right: detections colored by radial velocity. Blue approaches
   the sensor, green is near zero, and red recedes.*

The :doc:`Python acoustic example <../../examples/python_sensor_acoustic>`
shows an ultrasonic echo from a wall. There is no corresponding C example.

.. figure:: ../../img/sensors/nonvisual/acoustic_echo_envelope.avif
   :align: center
   :alt: Echo amplitude plotted over range, aligned with a side view of a sensor and a concrete wall 3 meters ahead.
   :width: 1200

   *Acoustic example: a sensor 0.5 m above asphalt faces a concrete wall 3 m
   ahead. The echo peak aligns with the wall. The plot converts round-trip
   time to range and shows one signal way.*

The Generic wpm recipes run in :doc:`Python <../../examples/python_generic_wpm>`
and :doc:`C <../../examples/c_generic_wpm>`. They demonstrate depth sampling,
full-circle scans, finite beams, independent receivers and mechanical propagation.

.. toctree::
   :maxdepth: 1

   lidar_core/index
   lidar_wpm/index
   radar_wpm_dmat/index
   acoustic_wpm/index
   generic_wpm/index

Related
-------

- :doc:`../common/sensor_configuration` — sensor prims, model schemas and shared attributes.
- :doc:`../common/output_configuration` — RenderProducts, RenderVars and renderer setup.
- :doc:`../common/sensor_outputs` — mapping and reading composite outputs.
- :doc:`../../materials/nonvisual_sensor_materials` — surface-response labels.
- :doc:`../visual/index` — camera-based sensor models.
