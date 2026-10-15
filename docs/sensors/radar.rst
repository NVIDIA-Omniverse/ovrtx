.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Radar Sensors
=============

An ovrtx radar scene needs an ``OmniRadar`` sensor prim and a RenderProduct
whose ``PointCloud`` RenderVar requests the detection channels the application
will read. C and Python use the same USDA pattern.

Configure the Radar Prim
------------------------

.. tab-set::

   .. tab-item:: Python Example Scene

      .. literalinclude:: ../../examples/python/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-radar-sensor]
         :end-before: # [/snippet:configure-radar-sensor]

   .. tab-item:: C Example Scene

      .. literalinclude:: ../../examples/c/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-radar-sensor]
         :end-before: # [/snippet:configure-radar-sensor]

Use ``OmniSensorGenericRadarWpmDmatAPI`` for the generic WPM DMAT radar model.
The default scan is ``s001``. Apply additional scan configuration API schemas
only when authoring multiple scan patterns.

Important Output Attributes
---------------------------

.. list-table::
   :header-rows: 1

   * - Attribute
     - Values
     - Use
   * - ``omni:sensor:WpmDmat:elementsCoordsType``
     - ``CARTESIAN`` or ``SPHERICAL``
     - Coordinate representation for detections.
   * - ``omni:sensor:WpmDmat:outputFrameOfReference``
     - ``SENSOR``, ``WORLD``, or ``CUSTOM``
     - Frame of reference for all outputs.
   * - ``omni:sensor:WpmDmat:customFrameOfReferenceTrafo``
     - ``[x, y, z, roll, pitch, yaw]``
     - Custom transform used when the output frame is ``CUSTOM``.


Configure PointCloud Output
---------------------------

.. tab-set::

   .. tab-item:: Python Example Scene

      .. literalinclude:: ../../examples/python/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-radar-pointcloud-output]
         :end-before: # [/snippet:configure-radar-pointcloud-output]

   .. tab-item:: C Example Scene

      .. literalinclude:: ../../examples/c/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-radar-pointcloud-output]
         :end-before: # [/snippet:configure-radar-pointcloud-output]

Request only the channels the consumer needs. ``Counts`` and ``Flags`` are
auto-enabled and delivered like ordinary channel tensors.

Radar Channels
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 16 44

   * - Channel
     - Type and shape
     - Unit
     - Meaning
   * - ``Counts``
     - ``int32 [1]``
     - detections
     - Number of delivered detections. Use it to bound every per-detection tensor.
   * - ``Coordinates``
     - ``float32 [3, Nmax]``
     - m, or deg / deg / m
     - Detection coordinates in the configured representation and frame. Cartesian rows
       are x, y, and z in meters. Spherical rows are azimuth and elevation in degrees,
       followed by range in meters.
   * - ``RCS``
     - ``float32 [Nmax]``
     - dBsm
     - Radar cross section, a logarithmic measure of radar detectability. Its value
       range depends on sensor and scene attributes.
   * - ``RadialVelocityMs``
     - ``float32 [Nmax]``
     - m/s
     - Signed Doppler radial velocity. Approaching detections can be negative.
   * - ``TimeOffsetNs``
     - ``int32 [Nmax]``
     - ns
     - Per-detection time offset relative to scan start.
   * - ``Flags``
     - ``uint8 [Nmax]``
     - unitless
     - Per-detection status bits. The ``VALID`` bit is ``0x40``.

``Nmax`` is the allocation bound reported by the ``maxPoints`` param. Only the
first ``Counts[0]`` entries are delivered; use ``Flags`` within that range when
status-aware filtering is required.

Radar PointCloud Parameters
---------------------------

Every param is CPU-resident, including when channel tensors are mapped to CUDA.
Scalar params use shape ``[1]``.

.. list-table::
   :header-rows: 1
   :widths: 24 18 14 44

   * - Param
     - Type and shape
     - Unit
     - Meaning
   * - ``frameId``
     - ``uint64 [1]``
     - unitless
     - Model frame counter for this output.
   * - ``timestampNs``
     - ``uint64 [1]``
     - ns
     - Instance scan timestamp for the output.
   * - ``modality``
     - ``uint32 [1]``
     - unitless
     - Sensor modality identifier; this output reports radar.
   * - ``frameOfReference``
     - ``uint16 [1]``
     - unitless
     - Coordinate frame for the output: ``SENSOR``, ``WORLD``, or ``CUSTOM``.
   * - ``coordsType``
     - ``uint32 [1]``
     - unitless
     - Coordinate representation: ``CARTESIAN`` or ``SPHERICAL``.
   * - ``modelToAppTransform``
     - ``float32 [4, 4]``
     - m / unitless
     - Homogeneous transform from model coordinates to application coordinates;
       translation entries are meters and linear entries are unitless.
   * - ``frameStartTimeStampNs``
     - ``uint64 [1]``
     - ns
     - Start of the scan interval.
   * - ``frameStartPosM``
     - ``float32 [3]``
     - m
     - Sensor position in the global frame at scan start.
   * - ``frameStartOrientation``
     - ``float32 [4]``
     - unitless
     - Sensor orientation in the global frame at scan start as an xyzw unit quaternion.
   * - ``frameEndTimeStampNs``
     - ``uint64 [1]``
     - ns
     - End of the scan interval.
   * - ``frameEndPosM``
     - ``float32 [3]``
     - m
     - Sensor position in the global frame at scan end.
   * - ``frameEndOrientation``
     - ``float32 [4]``
     - unitless
     - Sensor orientation in the global frame at scan end as an xyzw unit quaternion.
   * - ``maxPoints``
     - ``uint32 [1]``
     - detections
     - Maximum allocated detection capacity; use ``Counts`` for the delivered range.
   * - ``sensorID``
     - ``uint8 [1]``
     - unitless
     - Process-assigned identifier, stable for the model instance but not a persistent or globally unique ID.
   * - ``scanIdx``
     - ``uint8 [1]``
     - unitless
     - Active scan configuration index for a multi-scan radar.
   * - ``cycleCnt``
     - ``uint64 [1]``
     - unitless
     - Advancing cycle count for the active scan index; it is independent of ``frameId``.
   * - ``maxRangeM``
     - ``float32 [1]``
     - m
     - Maximum unambiguous range of the active scan.
   * - ``minVelMps``
     - ``float32 [1]``
     - m/s
     - Negative of the active scan's maximum unambiguous radial velocity.
   * - ``maxVelMps``
     - ``float32 [1]``
     - m/s
     - Maximum unambiguous radial velocity of the active scan.
   * - ``minAzRad``
     - ``float32 [1]``
     - rad
     - Negative of the active scan's maximum unambiguous azimuth.
   * - ``maxAzRad``
     - ``float32 [1]``
     - rad
     - Maximum unambiguous azimuth of the active scan.
   * - ``minElRad``
     - ``float32 [1]``
     - rad
     - Negative of the active scan's maximum unambiguous elevation.
   * - ``maxElRad``
     - ``float32 [1]``
     - rad
     - Maximum unambiguous elevation of the active scan.

Do not infer angular-param units from SPHERICAL ``Coordinates``. The coordinate
tensor stores azimuth and elevation in degrees, while the four ``*Rad`` scan
limit params are radians.

Interpreting Radar Output
-------------------------

``Counts[0]`` is the delivered-detection count; delivered indices are
``[0, Counts[0])``. Within that range, a detection is valid when
``Flags[i] & 0x40`` is non-zero. Use this bit test instead of comparing
``Flags[i] == 0x40`` because other status bits can be set at the same time.
``RadialVelocityMs`` is signed; approaching detections can be negative, so use
absolute value when checking only for motion.

Visualizing Radar Output
------------------------

Apply the ``Counts`` bound and ``Flags`` validity filter before visualizing
detections. For Cartesian ``Coordinates``, plot each detection as an xyz point.
For spherical ``Coordinates``, convert azimuth, elevation, and range to Cartesian
coordinates or use a visualization that understands the spherical representation.

Coloring by signed ``RadialVelocityMs`` is a useful default: blue for approaching
detections, green near zero, and red for receding detections. Color by ``RCS``
instead when inspecting material response or radar detectability. The complete
Python pattern is in :doc:`../examples/python_sensor_radar`.

For map/read code, refer to :doc:`pointclouds`. For material behavior that affects
radar returns, refer to :doc:`nonvisual_materials`.
