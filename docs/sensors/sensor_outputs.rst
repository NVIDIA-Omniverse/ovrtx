.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Sensor Outputs
==============

This page describes how to map and read RenderVar outputs after stepping a
RenderProduct. For authoring RenderProducts and RenderVars in USD, refer to
:doc:`configuration`. For available camera outputs, refer to :doc:`cameras/outputs`.
For lidar and radar PointCloud readback, refer to :doc:`pointclouds`.

.. _mapping-outputs:

Mapping Outputs
---------------

After a renderer step completes, each RenderProduct result contains one or more
render var outputs. A render var output must be mapped before application code
can read its tensor data.

In C, map with :c:func:`ovrtx_map_render_var_output`. In Python, use
``RenderVarOutput.map(device=Device.CPU | Device.CUDA)``. Tensor data is
returned on the requested device, while params are always CPU-resident.

Single-tensor camera outputs such as ``LdrColor`` can be consumed directly as a
DLPack tensor. Composite outputs such as lidar and radar ``PointCloud`` expose
named tensors and params.

CPU Mapping
^^^^^^^^^^^

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/minimal/main.py
         :language: python
         :start-after: # [snippet:read-render-output]
         :end-before: # [/snippet:read-render-output]
         :dedent:

   .. tab-item:: C

      In C, find the render variable, map it, consume the returned DLTensor, and
      unmap explicitly:

      .. literalinclude:: ../../examples/c/minimal/main.cpp
         :language: cpp
         :start-after: // [snippet:map-rendered-output-cpu]
         :end-before: // [/snippet:map-rendered-output-cpu]
         :dedent:

CUDA Mapping
^^^^^^^^^^^^

Map to CUDA when downstream GPU code should consume output without a CPU
readback.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_camera_sensors.py
         :language: python
         :start-after: # [snippet:doc-map-render-output-cuda]
         :end-before: # [/snippet:doc-map-render-output-cuda]
         :dedent:

   .. tab-item:: C

      Linear CUDA memory is selected with ``OVRTX_MAP_DEVICE_TYPE_CUDA``:

      .. literalinclude:: ../../tests/docs/c/test_camera_sensors.cpp
         :language: cpp
         :start-after: // [snippet:doc-map-render-output-cuda-c]
         :end-before: // [/snippet:doc-map-render-output-cuda-c]
         :dedent:

CUDA Arrays
^^^^^^^^^^^

The C API also exposes ``OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`` for image outputs.
Use this when a CUDA texture/surface or graphics interop path can consume a
``CUarray`` directly and avoid an extra copy into linear device memory.

.. literalinclude:: ../../tests/docs/c/test_camera_sensors.cpp
   :language: cpp
   :start-after: // [snippet:doc-map-render-output-cuda-array-c]
   :end-before: // [/snippet:doc-map-render-output-cuda-array-c]
   :dedent:

Synchronization and Lifetime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- A mapped C output is valid until :c:func:`ovrtx_unmap_render_var_output`.
- A Python mapping stays alive while the ``MappedRenderVar`` or any DLPack
  consumer such as a NumPy, Warp, PyTorch, or CuPy tensor still references it.
- GPU mappings carry synchronization hints. Wait on the producer event before
  accessing CUDA data on a different stream, and pass a stream or event when
  unmapping after your own CUDA work.
- Dropping a step-result object does not invalidate live mappings; mappings have
  independent lifetime.
- In Python the mapping is consumer-owned — a held view keeps the buffer valid past
  unmap, so copying for lifetime is not required (copy only for data beyond the last
  view). In C, copy before unmap if the data must outlive the mapping.

The Vulkan interop example shows a full double-buffered C path using CUDA arrays,
timeline semaphores, and explicit synchronization. Refer to
:doc:`../examples/c_vulkan_interop`.

Composite Output Format
-----------------------

The C output container is :c:struct:`ovrtx_render_var_output_t`; the Python
equivalent is ``MappedRenderVar``. This type is a self-describing, named
container that pairs zero or more bulk *tensors* with zero or more lightweight
*params*:

.. code-block:: text

    ovrtx_render_var_output_t
       |
       |-- name        : string    -- identifies this output (matches the RenderVar prim name in USD)
       |-- type        : string    -- semantic type tag (e.g. "PointCloud", "HdrColor")
       |-- doc         : string    -- human-readable description
       |-- version     : int       -- version of this output's schema, for forward/backward compatibility
       |-- status      : enum      -- pending / completed / failed
       |-- cuda_sync   : struct    -- stream + event guarding access to GPU-resident tensors
       |
       |-- tensors[]              -- zero or more named tensors (the bulk data)
       |     |-- name  : string
       |     |-- doc   : string
       |     |-- dl    : DLTensor  -- pointer, shape, dtype, device (CPU or CUDA)
       |
       |-- params[]               -- zero or more named CPU-resident params (the metadata)
             |-- name  : string
             |-- doc   : string
             |-- dl    : DLTensor  -- always {kDLCPU, 0}; dtype encodes value type, shape encodes scalar vs. array

Tensors
^^^^^^^

Tensors carry the bulk data of an output. Each tensor is a named multi-dimensional array described by the widely adopted DLPack convention, which specifies:

- A data pointer (may point to CPU or CUDA memory).
- Shape (number of dimensions and size of each).
- Data type (element type and bit-width).
- Device (CPU, CUDA, ...).

DLPack is the format that NumPy, PyTorch, Warp, JAX, and CuPy use to exchange tensor data zero-copy. Receiving a DLPack tensor lets the consumer build a view in any of those libraries without copying the underlying bytes.

Tensor shapes for variable-sized outputs (for example, point clouds) encode the *maximum* extent rather than the actual count. The shape itself is in the descriptor, so it is available synchronously -- consumers read it to pre-allocate before the bulk data is ready. The actual per-frame count is delivered post-render through a separate scalar tensor (for example, ``Counts`` for sensor point clouds).

Two DLPack conventions worth surfacing: ``strides`` are expressed in *number of elements*, not bytes. A scalar value is represented as a one-element tensor with shape ``[1]`` (or ``[T]`` for one-per-tile).

Examples of tensors within an output:

- A lidar ``PointCloud`` output:

  - ``Coordinates`` -- ``[3, maxPoints]`` ``float32``, CUDA
  - ``Intensity`` -- ``[maxPoints]`` ``float32``, CUDA
  - ``Flags`` -- ``[maxPoints]`` ``uint8``, CUDA
  - ``TimeOffsetNs`` -- ``[maxPoints]`` ``int32``, CUDA
  - ``Counts`` -- ``[1]`` ``int32``, CUDA (actual number of valid points produced this frame)
  - ...plus other channels (``EmitterId``, ``HitNormal``, ``Velocity``, ...) depending on what the ``RenderVar`` requests.

- A camera ``HdrColor`` output:

  - one image tensor -- ``[H, W, 4]`` ``float16``, CUDA, accessed as the mapping itself through DLPack.

The set of tensors that an output type publishes is determined by the output's semantic ``type`` and documented through the ``doc`` strings (and the higher-level wrappers, when one exists).

For convenience, if an output has only a single tensor--such as camera outputs like ``LdrColor`` or ``DepthSD``--the Python wrapper exposes the mapping itself as the DLPack tensor. Composite render variables such as sensor ``PointCloud`` expose named tensors and params.

Params
^^^^^^

Params carry lightweight metadata as named, typed key-value pairs. They are always CPU-resident and always available synchronously once the output is mapped.

A param is structurally a DLTensor whose dtype encodes the value type and whose shape encodes scalar compared to array (``{1}`` for scalar, ``{N}`` for a vector, ``{4, 4}`` for a matrix). This keeps the descriptor uniform with the tensor list: the same DLPack consumer code works for both, and there is no separate enum-tagged value type to switch over.

Examples of params (drawn from the sensor ``PointCloud`` output):

- ``frameId`` (uint64) -- identifies the simulation frame.
- ``timestampNs`` (uint64) -- simulation time in nanoseconds.
- ``modelToAppTransform`` (float32 ``[4, 4]``) -- coordinate transform from sensor frame to application frame.
- ``coordsType`` (uint32) -- spherical compared to cartesian coordinate encoding.
- ``frameStartTimeStampNs`` / ``frameEndTimeStampNs`` (uint64) -- shutter open / close.

Sizing information (e.g. the per-point tensor's maximum extent) is carried by the tensor's shape in the descriptor and does not need a separate param. The post-render *actual* count for a variable-sized output is carried by a tensor (e.g. ``Counts``) so that it stays on the producing stream.

Python Representation
^^^^^^^^^^^^^^^^^^^^^

The ovrtx Python module wraps the raw C struct in a small, ergonomic API. ``RenderVarOutput.map(...)`` returns a ``MappedRenderVar`` whose tensors and params can be reached by name:

- ``np.from_dlpack(rv)`` -- for a single-tensor render variable, the mapping itself is the DLPack view of that tensor (used for ``HdrColor`` / ``LdrColor``).
- ``rv["Coordinates"]`` -- for a multi-tensor render variable, index by tensor name to get a ``RenderVarTensor`` (DLPack-compatible, zero-copy).
- ``rv.params["frameId"]`` -- look up a ``RenderVarParam`` by name; also DLPack-compatible.
- ``rv.name`` / ``rv.type`` / ``rv.doc`` / ``rv.version`` -- the output's identity and schema metadata.

These wrappers cover the common case. Consumers that need direct access can fall back to walking ``num_tensors`` / ``tensors`` and ``num_params`` / ``params`` (in C) or iterating the ``MappedRenderVar`` (in Python). Third-party sensor models can publish new output types without shipping any wrapper code -- the generic API works on anything that conforms to the format.


USD Schema Mapping
------------------

Each render variable output corresponds to one ``RenderVar`` in USD, and ``orderedVars`` on the ``RenderProduct`` selects which ones to produce. A minimal lidar product authored to emit a four-channel ``PointCloud`` looks like:

.. literalinclude:: ../../examples/python/lidar/lidar_example.usda
   :language: usda
   :start-after: # [snippet:configure-lidar-pointcloud-output]
   :end-before: # [/snippet:configure-lidar-pointcloud-output]

See :doc:`configuration` for the full RenderProduct / RenderVar authoring story.

See Also
--------

- :doc:`configuration` -- declaring RenderProducts and RenderVars in USD.
- :doc:`cameras/outputs` -- the catalog of camera RenderVar source names.
- :ref:`Mapping render variables in C or Python <mapping-outputs>`.
- :doc:`pointclouds` -- reading lidar and radar ``PointCloud`` tensors.
- :doc:`lidar` and :doc:`radar` -- sensor-specific channel meanings.
- :c:struct:`ovrtx_render_var_output_t` in the :doc:`../c_api/index` -- the C type reference, including the tensor and param sub-structs.
