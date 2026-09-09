.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _cuda-vulkan-scheduling:

CUDA and Vulkan Scheduling on Linux
===================================

.. note::

   This page documents a known driver scheduling interaction on Linux and the
   workarounds available today. Windows is unaffected and needs no workaround,
   so applications that ship on both platforms should apply a workaround only on
   Linux.

Symptom
-------

ovrtx renders with Vulkan and exchanges data with the application through CUDA.
Every synchronization point between the two is a stream-ordered CUDA wait — a
stream you pass as ``sync_stream``, an event ovrtx signals when an output is
ready, or an event you hand ovrtx so it waits for your own work before touching
your buffers.

On Linux, a CUDA stream wait that is outstanding while the renderer submits
Vulkan work on the same device disturbs how that Vulkan work is scheduled. The
renderer's GPU workload develops scheduling bubbles: leading it to potentially 
occupying significantly more wall-clock time than its isolated cost.
The effect is a property of the concurrency, not of any particular ovrtx call.
Using the API correctly still triggers it — passing your consumer stream as 
``sync_stream`` is the intended pattern and is affected the same way as any 
other stream-ordered wait.

Recommended Workaround
----------------------

Set ``CUDA_DEVICE_MAX_CONNECTIONS=1`` in the process environment. The variable
caps how many hardware work queues, or *connections*, the CUDA driver opens from
the host to the device. Pinning it to one makes submissions across CUDA streams
serialize in submission order, which stops them forming unintended hardware
dependencies against concurrent graphics work. In the cases measured, the
renderer's Vulkan workload no longer showed the scheduling gaps.

The variable is read when the CUDA driver initializes, so it must be set before
the process creates its first CUDA context. Setting it from inside the process
after CUDA is already up has no effect.

.. code-block:: bash

   export CUDA_DEVICE_MAX_CONNECTIONS=1
   ./your_application

Because it collapses the host-to-device work queues, it also removes
hardware-level concurrency between the application's *own* CUDA streams. For
workloads that depend on independent streams running concurrently, measure
before adopting it globally.

Application-Side Alternative
----------------------------

If ``CUDA_DEVICE_MAX_CONNECTIONS=1`` is not acceptable, replace the
stream-ordered wait with a CPU-side wait: suppress the GPU-side wait by mapping
with a stream value of ``0``, then block the calling thread on the producer
event before consuming the data.

In Python, map with ``sync_stream=0`` and call
:meth:`ovrtx.MappedRenderVar.wait`. In C, leave
``ovrtx_map_output_description_t::sync_stream`` at ``0`` and call
``cuEventSynchronize`` on ``ovrtx_cuda_sync_t::wait_event`` from the returned
output.

This trades away CPU/GPU overlap: the calling thread stalls until rendering
completes instead of queueing dependent work and moving on. It is the narrower
workaround — it only covers the output-mapping path, and it changes application
code rather than the environment. On Windows, keep the intended pattern instead:
pass the stream that will consume the data as ``sync_stream`` and queue your
dependent work on it.
