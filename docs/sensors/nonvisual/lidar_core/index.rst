.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-core-index:
.. _sensors-nonvisual-lidar-core:

Lidar generic core model
========================

The Lidar generic core model simulates rotary and solid-state scanning lidars.
An ``OmniLidar`` prim with ``OmniSensorGenericLidarCoreAPI`` defines the firing
schedule, geometric rays and return processing. Configure its
``omni:sensor:Core:*`` attributes to match a device's specifications and
calibration data. For pulse propagation and detector modeling, use the
separate :doc:`Lidar generic wpm model <../lidar_wpm/index>`.

.. figure:: ../../../../img/example-sensor-lidar.avif
   :align: center
   :alt: A rotary lidar scan in the rerun.io viewer, seen from above and behind the sensor: concentric rings of dark points on the ground plane, a brighter cluster of points where the concrete cube stands ahead of the sensor, and a yellow arrow marking the sensor's forward axis.
   :width: 1265

   *Rotary scan using the default 128-emitter profile. The sensor is 1 m above
   asphalt, facing a concrete cube 10 m away. Points are shaded by intensity:
   asphalt is dark and concrete is bright. The arrow marks the forward axis.*

Simulation
----------

The model supports rotary and solid-state scans, including flash lidar.
Rotary scans repeat a firing pattern through a full revolution, clockwise or
counterclockwise, and accept returns within the configured azimuth window.
Solid-state scans fire a fixed pattern, arranged in lines, once per scan.
``omni:sensor:Core:scanType`` selects the scan type; :doc:`attributes` lists
the controls that apply to each.

Each emitter has a firing delay relative to the start of its tick. Points in
a scan can therefore have different measurement times, reported by
:doc:`TimeOffsetNs <outputs>`. See :doc:`howto/firing_pattern` for scan timing
and emitter configuration, :doc:`attributes` for definitions of ticks and
emitter states, and :doc:`howto/field_of_view` for range and azimuth limits.

.. figure:: ../../../img/sensors/nonvisual/lidar_core_solid_state_scan.avif
   :align: center
   :alt: The same asphalt plane and concrete cube scanned by a solid-state sensor from the viewpoint of the rotary scan above: instead of full rings, a forward-facing sector of dotted lines on the ground, half a degree apart, and a dotted rectangle on the cube, points gray to white by intensity.
   :width: 1265

   *The same scene with ``scanType = SOLID_STATE``: 14,701 emitters in 61 lines
   at half-degree spacing cover 120 by 30 degrees, firing once per scan.
   The viewpoint and intensity shading match the rotary scan above.*

The default ``IDEALIZED`` ray type has no width. ``GAUSSIAN_BEAM`` and
``UNIFORM_BEAM`` model a finite beam width, with power distributed according
to a Gaussian profile or uniformly across the beam. A beam that overlaps an
object's edge can produce returns from both the object and a surface behind
it. Beam tracing costs more than idealized rays. See :doc:`attributes` for
``omni:sensor:Core:rayType``, divergence, waist and beam quality.

One firing can produce zero or more returns, up to ``maxReturns`` per detector
channel. Rays can continue beyond the first surface. The ray type determines
which returns are retained; :doc:`outputs` defines their ``EchoId`` order.
Range limits, minimum echo separation and the detection threshold can reject
returns. Configure these in :doc:`howto/field_of_view` and :doc:`howto/intensity`.

Return intensity depends on emitter power, wavelength and pulse duration;
detector aperture, efficiency and gain; range; and the surface's
:doc:`non-visual material <../../../materials/nonvisual_sensor_materials>`.
Intensity processing and scaling convert this response to the device's
reflectivity units. The detection threshold is specified by a minimum
reflectance and the range at which it must be detected.
See :doc:`howto/intensity` for configuration.

Range accuracy controls distance-dependent measurement noise. Pointing and
origin noise perturb each emitter's direction and beam origin. The means and
standard deviations are defined on :doc:`attributes`.

Sensor or target motion during a scan can distort the point cloud. This
requires the renderer's motion BVH. By default, the output retains the
distortion; ``omni:sensor:Core:outputMotionCompensationState`` enables motion
compensation. See :doc:`howto/motion_artifacts` for both settings and
:doc:`../../common/output_configuration` for motion BVH configuration.

Outputs
-------

Each ``PointCloud`` RenderVar delivers a composite output of named tensors.
Request the channels you need:

- Position: ``Coordinates``, Cartesian or spherical, in sensor, world or custom coordinates.
- Strength and firing time: ``Intensity`` and ``TimeOffsetNs``.
- Source of each return: ``EmitterId``, ``ChannelId``, ``TickId``, ``EchoId`` and ``TickState``.
- Surface normal and hit-point velocity relative to the sensor: ``HitNormal`` and ``Velocity``.
- Material and object identity: ``MaterialId`` and ``ObjectId``. Object IDs require
  a RenderProduct in the scene to request a stable-ID output.

``Counts`` and ``Flags`` are always included. ``Counts`` bounds the per-return tensors;
``Flags`` identifies valid entries.

By default, a complete scan arrives on the step that finishes it. With
``partialOutputs``, each step can deliver the portion of the scan it covers.
``instantLidar`` traces a whole scan each step; ``partialOutputs`` still controls
which steps deliver it. See :doc:`outputs` for channel definitions and delivery
rules, and :doc:`../../common/sensor_outputs` for the container.

Applications
------------

Use this model for geometric point clouds from vehicle-mounted rotary lidars,
solid-state robot sensors and industrial single-beam scanners.
:doc:`howto/spec_sheet_profile` explains how to create a device profile from a
datasheet. The :doc:`tutorials <tutorials/index>` provide profiles for the
Velodyne Alpha Prime (rotary), Blickfeld Cube 1 (solid-state) and SICK TiM781
(both representations).

Multiple sensors can run with one RenderProduct per sensor. Most attributes
can be changed while a sensor runs; see :doc:`../../common/runtime_updates`.
Use the :doc:`Lidar generic wpm model <../lidar_wpm/index>` when you need
waveform processing, detector response or multipath propagation.

Sensor definition
-----------------

Apply ``OmniSensorGenericLidarCoreAPI`` to an ``OmniLidar`` prim. Its defaults
define a 128-emitter rotary lidar with one emitter state. Override
``omni:sensor:Core:*`` attributes to configure the sensor. Apply additional
emitter-state schema instances to alternate between firing patterns.

A RenderProduct targets the sensor through ``rel camera``. Its ``PointCloud``
RenderVar selects output channels. :doc:`../../first_sensor` shows how to
create these objects, step the sensor and read valid returns. For reference,
see :doc:`attributes`, :doc:`../../common/sensor_configuration` and
:doc:`../../common/output_configuration`.

This example applies the schema and sets the output coordinate system, frame
rate and sensor transform:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../examples/python/lidar/lidar_example.usda
         :language: usda
         :start-after: # [snippet:configure-lidar-sensor]
         :end-before: # [/snippet:configure-lidar-sensor]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-lidar-sensor-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-lidar-sensor-python]
         :dedent:

The :doc:`Python <../../../examples/python_sensor_lidar>` and
:doc:`C <../../../examples/c_sensor_lidar>` examples scan a concrete cube above
an asphalt plane. They enable motion BVH, warm up the sensor and read a scan
using ``Counts``. Both report the valid-point count, mean intensity and
largest time offset; the Python example also displays the point cloud in
Rerun, as shown above.

Configuration and outputs
-------------------------

Use :doc:`attributes` for controls, :doc:`howto/index` for configuration tasks,
and :doc:`outputs` for channel layouts and valid-point handling.
The :doc:`tutorials <tutorials/index>` turn three device datasheets into profiles.

.. toctree::
   :maxdepth: 1

   attributes
   howto/index
   outputs
   tutorials/index

Related
-------

- :doc:`Your First Lidar Sensor <../../first_sensor>` — sensor setup, rendering and output mapping.
- :doc:`Sensor Configuration <../../common/sensor_configuration>` — instantiating a sensor prim, applying its schema and overriding attributes.
- :doc:`Output Configuration <../../common/output_configuration>` — RenderProducts, RenderVars and renderer settings, including motion BVH.
