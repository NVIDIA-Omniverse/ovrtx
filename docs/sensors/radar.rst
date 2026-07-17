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
   * - ``omni:sensor:WpmDmat:auxOutputType``
     - ``NONE``, ``BASIC``, ``EXTRA``, ``FULL``
     - Controls auxiliary data in ``GenericModelOutput``. It does not add
       ``PointCloud`` channels.
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

   * - Channel
     - Meaning
   * - ``Counts``
     - Number of delivered detections. Use it to bound every per-detection tensor.
   * - ``Coordinates``
     - Detection coordinates in the configured coordinate representation and frame.
   * - ``RCS``
     - Radar cross section in dBsm.
   * - ``RadialVelocityMs``
     - Signed Doppler radial velocity in meters per second.
   * - ``TimeOffsetNs``
     - Per-detection time offset relative to scan start.
   * - ``Flags``
     - Per-detection status bits. The ``VALID`` bit is ``0x40``.

Interpreting Radar Output
-------------------------

Within the first ``Counts[0]`` entries, a detection is valid when
``Flags[i] & 0x40`` is non-zero. ``RadialVelocityMs`` is signed; approaching
detections can be negative, so use absolute value when checking only for
motion.

For map/read code, refer to :doc:`pointclouds`. For material behavior that affects
radar returns, refer to :doc:`nonvisual_materials`.
