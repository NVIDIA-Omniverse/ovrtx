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
one output exposes one named tensor per requested payload channel, model-added
``Counts`` and ``Flags`` tensors, and CPU params that describe the output.
``Counts[0]`` is the delivered-entry count; delivered indices are
``[0, Counts[0])``. When invalid entries may be present, use the ``Flags``
``VALID`` bit (``Flags[i] & 0x40``) to determine per-entry validity.

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

In Python, ``frame.render_vars`` is keyed by the full RenderVar prim path, for
example ``frame.render_vars["/World/Render/Vars/PointCloud"]`` in the lidar and
radar examples. Mapping that output returns the composite ``PointCloud`` data.
Index by exact channel name, then pass the channel object to a DLPack consumer
such as NumPy. The mapping is consumer-owned: a held DLPack view keeps the data
valid past ``unmap``, so copy only when data must outlive the last held view.

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
:c:func:`ovrtx_map_render_var_output()`, find named tensors in
``ovrtx_render_var_output_t::tensors``, then unmap with
:c:func:`ovrtx_unmap_render_var_output()`.

CPU and CUDA Mapping
--------------------

CPU mapping is easiest for examples, logging, and validation. CUDA mapping is
available for GPU point-cloud pipelines:

- Python uses ``map(device=ovrtx.Device.CUDA)``.
- C uses ``OVRTX_MAP_DEVICE_TYPE_CUDA`` for linear CUDA memory.

Each mapped ``DLTensor`` object's ``device`` field reports its actual storage
device type and ID. Explicit CPU mapping returns ``kDLCPU`` tensors, and
explicit CUDA mapping returns linear ``kDLCUDA`` tensors. In C,
``OVRTX_MAP_DEVICE_TYPE_DEFAULT`` lets the runtime choose the most efficient
representation; inspect ``device`` on every returned ``DLTensor``. Params remain
CPU-resident for every mapping mode.

Consume CUDA tensors with GPU-aware code and respect the synchronization hints
on the mapped output. ``CUDA_ARRAY`` mapping is intended for image-style
outputs, not point-cloud channel tensors.

Rules
-----

- Use ``Counts[0]`` as the delivered-entry count before slicing or iterating
  per-point or per-detection tensors.
- Do not treat ``Counts`` as proof that every delivered entry is valid. When
  invalid entries may be present, keep entries whose ``Flags`` ``VALID`` bit is
  set (``Flags[i] & 0x40``).
- Treat requested payload channel names as part of the data contract; they must
  match the ``channels`` authored on the ``PointCloud`` RenderVar.
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

    ovrtx_render_var_output_t
      name:    "/World/Render/Vars/PointCloud"
      type:    "PointCloud"

      tensors (device reported by each DLTensor; Nmax is the per-frame allocation bound):
        "Coordinates"    -- [3, Nmax]   float32   (x, y, z per point; spherical or cartesian per coordsType)
        "Intensity"      -- [Nmax]      float32   (return intensity per point)
        "Flags"          -- [Nmax]      uint8     (validity / classification flags; auto-enabled)
        "Counts"         -- [1]         int32     (number of delivered point entries this frame; auto-enabled)
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

      params (always CPU):
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
        "maxPoints"                -- uint32     (maximum point allocation; use Counts for the delivered per-frame range)

Field-by-field meaning, units, and visualization patterns are in :doc:`lidar`.

Radar Point Cloud
-----------------

Produced by the radar sensor model.

.. code-block:: text

    ovrtx_render_var_output_t
      name:    "/World/Render/Vars/PointCloud"
      type:    "PointCloud"

      tensors (device reported by each DLTensor; Nmax is the per-frame allocation bound):
        "Coordinates"      -- [3, Nmax]  float32   (range, azimuth, elevation -- or x, y, z per coordsType)
        "RCS"              -- [Nmax]     float32   (radar cross section)
        "RadialVelocityMs" -- [Nmax]     float32   (radial velocity, m/s -- negative for approaching)
        "TimeOffsetNs"     -- [Nmax]     int32     (per-detection time offset from frame start)
        "Flags"            -- [Nmax]     uint8     (auto-enabled)
        "Counts"           -- [1]        int32     (number of delivered detections this frame; auto-enabled)

      params (always CPU):
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
        "maxPoints"                -- uint32     (maximum detection allocation; use Counts for the delivered per-frame range)

Field-by-field meaning is in :doc:`radar`.
