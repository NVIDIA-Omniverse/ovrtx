.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Lidar Sensors
=============

An ovrtx lidar scene needs an ``OmniLidar`` sensor prim and a RenderProduct
whose ``PointCloud`` RenderVar requests the channels the application will read.
C and Python use the same USDA pattern: application code loads the scene,
steps the RenderProduct, and maps the output.

Configure the Lidar Prim
------------------------

.. tab-set::

   .. tab-item:: Python Example Scene

      .. literalinclude:: ../../examples/python/lidar/lidar_example.usda
         :language: usda
         :start-after: # [snippet:configure-lidar-sensor]
         :end-before: # [/snippet:configure-lidar-sensor]

   .. tab-item:: C Example Scene

      .. literalinclude:: ../../examples/c/lidar/lidar_example.usda
         :language: usda
         :start-after: # [snippet:configure-lidar-sensor]
         :end-before: # [/snippet:configure-lidar-sensor]

Use ``OmniSensorGenericLidarCoreAPI`` for the generic lidar model. In Z-up
scenes, keep the scene Z-up and rotate the lidar prim so sensor ``+X`` points in
the intended forward direction.

Important Output Attributes
---------------------------

.. list-table::
   :header-rows: 1

   * - Attribute
     - Values
     - Use
   * - ``omni:sensor:Core:elementsCoordsType``
     - ``CARTESIAN`` or ``SPHERICAL``
     - Coordinate representation for point tensors.
   * - ``omni:sensor:Core:outputFrameOfReference``
     - ``SENSOR``, ``WORLD``, or ``CUSTOM``
     - Frame of reference for all outputs.
   * - ``omni:sensor:Core:customFrameOfReferenceTrafo``
     - ``[x, y, z, roll, pitch, yaw]``
     - Custom transform used when the output frame is ``CUSTOM``.
   * - ``omni:sensor:Core:outputMotionCompensationState``
     - ``NONCOMPENSATED`` or ``COMPENSATED``
     - Motion compensation state for outputs.
   * - ``omni:sensor:Core:includeInvalidPoints``
     - ``true`` or ``false``
     - Preserve invalid returns in the point tensors when true.
   * - ``omni:sensor:Core:partialOutputs``
     - ``true`` or ``false``
     - Emit partial scans as the sensor sweeps.
   * - ``omni:sensor:Core:instantLidar``
     - ``true`` or ``false``
     - Emit a full scan every frame for simplified workflows.


Configure PointCloud Output
---------------------------

.. tab-set::

   .. tab-item:: Python Example Scene

      .. literalinclude:: ../../examples/python/lidar/lidar_example.usda
         :language: usda
         :start-after: # [snippet:configure-lidar-pointcloud-output]
         :end-before: # [/snippet:configure-lidar-pointcloud-output]

   .. tab-item:: C Example Scene

      .. literalinclude:: ../../examples/c/lidar/lidar_example.usda
         :language: usda
         :start-after: # [snippet:configure-lidar-pointcloud-output]
         :end-before: # [/snippet:configure-lidar-pointcloud-output]

Request only the channels the consumer needs. ``Counts`` and ``Flags`` are
auto-enabled and delivered like ordinary channel tensors.

Lidar Channels
--------------

.. list-table::
   :header-rows: 1

   * - Channel
     - Meaning
   * - ``Counts``
     - Number of delivered point entries. Use it to bound every per-point tensor.
   * - ``Coordinates``
     - Point coordinates in the configured coordinate representation and frame.
   * - ``Intensity``
     - Processed return strength.
   * - ``TimeOffsetNs``
     - Per-point time offset relative to the sensor timestamp.
   * - ``Flags``
     - Per-point status bits. The ``VALID`` bit is ``0x40``.
   * - ``EmitterId``, ``ChannelId``, ``TickId``, ``EchoId``
     - Emitter, detector/channel, scan tick, and return identifiers.
   * - ``TickState``
     - Active scan pattern state for the tick that produced the point.
   * - ``MaterialId``, ``ObjectId``
     - Hit material and object identifiers.
   * - ``HitNormal``, ``Velocity``
     - Surface normal and velocity at the hit point.

Interpreting Lidar Output
-------------------------

Within the first ``Counts[0]`` entries, a point is valid when
``Flags[i] & 0x40`` is non-zero. Do not compare ``Flags[i] == 0x40`` because
other lidar-specific bits can be set at the same time.

With ``includeInvalidPoints = false``, invalid returns are dropped before output.
With ``includeInvalidPoints = true``, invalid entries can be present inside the
``Counts`` range and must be filtered by ``Flags`` before using channels such as
``Coordinates``, ``Intensity``, ``HitNormal``, or ``Velocity`` as real returns.

For map/read code, refer to :doc:`pointclouds`.
