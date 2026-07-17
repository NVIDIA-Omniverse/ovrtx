.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Reading Sensor PointClouds
==========================

Lidar and radar ``PointCloud`` RenderVars are composite render outputs. Mapping
one output exposes one named tensor per requested channel plus CPU params that
describe the output. Use ``Counts`` to bound per-point or per-detection tensors
before reading channel values.

For the output container format, refer to :doc:`sensor_outputs`. For sensor-specific
channel meanings, refer to :doc:`lidar` and :doc:`radar`.

Python
------

.. tab-set::

   .. tab-item:: Lidar

      .. literalinclude:: ../../examples/python/lidar/main.py
         :language: python
         :start-after: # [snippet:read-lidar-pointcloud]
         :end-before: # [/snippet:read-lidar-pointcloud]
         :dedent:

   .. tab-item:: Radar

      .. literalinclude:: ../../examples/python/radar/main.py
         :language: python
         :start-after: # [snippet:read-radar-pointcloud]
         :end-before: # [/snippet:read-radar-pointcloud]
         :dedent:

In Python, ``frame.render_vars["PointCloud"].map(device=ovrtx.Device.CPU)``
returns a mapped composite output. Index by exact channel name, then pass the
channel object to a DLPack consumer such as NumPy. The mapping is
consumer-owned: a held DLPack view keeps the data valid past ``unmap``, so copy
only when data must outlive the last held view.

C
-

.. tab-set::

   .. tab-item:: Lidar

      .. literalinclude:: ../../examples/c/lidar/main.cpp
         :language: cpp
         :start-after: // [snippet:read-lidar-pointcloud]
         :end-before: // [/snippet:read-lidar-pointcloud]
         :dedent:

   .. tab-item:: Radar

      .. literalinclude:: ../../examples/c/radar/main.cpp
         :language: cpp
         :start-after: // [snippet:read-radar-pointcloud]
         :end-before: // [/snippet:read-radar-pointcloud]
         :dedent:

In C, map the ``PointCloud`` render var with
:c:func:`ovrtx_map_render_var_output`, find named tensors in
``ovrtx_render_var_output_t::tensors``, then unmap with
:c:func:`ovrtx_unmap_render_var_output`.

CPU and CUDA Mapping
--------------------

CPU mapping is easiest for examples, logging, and validation. CUDA mapping is
available for GPU point-cloud pipelines:

- Python uses ``map(device=ovrtx.Device.CUDA)``.
- C uses ``OVRTX_MAP_DEVICE_TYPE_CUDA`` for linear CUDA memory.

GPU-mapped tensors are CUDA DLTensors. Consume them with GPU-aware code and
respect the synchronization hints on the mapped output. ``CUDA_ARRAY`` mapping
is intended for image-style outputs, not point-cloud channel tensors.

Rules
-----

- Use ``Counts[0]`` before slicing or iterating per-point tensors.
- Treat channel names as part of the data contract; they must match the
  ``channels`` authored on the ``PointCloud`` RenderVar.
- ``Counts`` and ``Flags`` are auto-enabled by lidar and radar models.
- Other payload channels are present only when requested.
- In Python the mapping is consumer-owned: a held DLPack consumer view (for example, a NumPy array) keeps the
  buffer valid even after unmap, so lifetime is not a manual concern — copy only if
  you need data beyond the last view.
- In C, mapped tensor pointers are valid only until unmap; copy CPU data, or
  synchronize and copy GPU data, before unmapping if it must outlive the mapping.


.. note::

   The shapes shown below are the current non-tiled ``PointCloud`` layouts.
   Read tensor shapes from the mapped output descriptor at runtime instead of
   hard-coding allocation sizes.

Lidar Point Cloud
-----------------

Produced by the lidar sensor model.

.. code-block:: text

    ovrtx_render_var_output_t "PointCloud"
      name:    "PointCloud"

      tensors (all CUDA, Nmax is the per-frame allocation bound):
        "Coordinates"    -- [3, Nmax]   float32   (x, y, z per point; spherical or cartesian per coordsType)
        "Intensity"      -- [Nmax]      float32   (return intensity per point)
        "Flags"          -- [Nmax]      uint8     (validity / classification flags; auto-enabled)
        "Counts"         -- [1]         int32     (actual number of valid points this frame; auto-enabled)
        "TimeOffsetNs"   -- [Nmax]      int32     (per-point time offset from frame start)
        "EmitterId"      -- [Nmax]      uint32    (emitter / beam index)
        "ChannelId"      -- [Nmax]      uint32    (channel / detector index)
        "MaterialId"     -- [Nmax]      uint32    (material of hit surface)
        "TickId"         -- [Nmax]      uint32    (tick / scan index)
        "HitNormal"      -- [Nmax, 3]   float32   (surface normal at hit)
        "Velocity"       -- [Nmax, 3]   float32   (velocity at hit point)
        "ObjectId"       -- [Nmax, 4]   uint32    (128-bit instance ID, 4x uint32)
        "EchoId"         -- [Nmax]      uint8     (echo / return index)
        "TickState"      -- [Nmax]      uint8     (per-tick state)

      params (CPU):
        "frameId"                  -- uint64
        "timestampNs"              -- uint64
        "modality"                 -- uint32
        "coordsType"               -- uint32     (spherical | cartesian)
        "frameOfReference"         -- uint16     (sensor | parent | world | custom)
        "motionCompensationState"  -- uint16
        "modelToAppTransform"      -- float32 [4, 4]
        "frameStartTimeStampNs"    -- uint64
        "frameStartPosM"           -- float32 [3]
        "frameStartOrientation"    -- float32 [4]
        "frameEndTimeStampNs"      -- uint64
        "frameEndPosM"             -- float32 [3]
        "frameEndOrientation"      -- float32 [4]
        "maxPoints"                -- uint32     (maximum point allocation; use Counts for the valid per-frame count)

Field-by-field meaning, units, and visualization patterns are in :doc:`lidar`.

Radar Point Cloud
-----------------

Produced by the radar sensor model.

.. code-block:: text

    ovrtx_render_var_output_t "PointCloud"
      name:    "PointCloud"

      tensors (all CUDA, Nmax is the per-frame allocation bound):
        "Coordinates"      -- [3, Nmax]  float32   (range, azimuth, elevation -- or x, y, z per coordsType)
        "RCS"              -- [Nmax]     float32   (radar cross section)
        "RadialVelocityMs" -- [Nmax]     float32   (radial velocity, m/s -- negative for approaching)
        "TimeOffsetNs"     -- [Nmax]     int32     (per-detection time offset from frame start)
        "Flags"            -- [Nmax]     uint8     (auto-enabled)
        "Counts"           -- [1]        int32     (actual number of valid detections this frame; auto-enabled)

      params (CPU):
        "frameId"                  -- uint64
        "timestampNs"              -- uint64
        "modality"                 -- uint32
        "coordsType"               -- uint32
        "frameOfReference"         -- uint16
        "modelToAppTransform"      -- float32 [4, 4]
        "frameStartTimeStampNs"    -- uint64
        "frameStartPosM"           -- float32 [3]
        "frameStartOrientation"    -- float32 [4]
        "frameEndTimeStampNs"      -- uint64
        "frameEndPosM"             -- float32 [3]
        "frameEndOrientation"      -- float32 [4]
        "maxPoints"                -- uint32     (maximum detection allocation; use Counts for the valid per-frame count)

Field-by-field meaning is in :doc:`radar`.
