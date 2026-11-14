.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

.. Internal feature inventory: pipeline-processing.profiling

.. _profiling:

Profiling
=========

Use profiling to find expensive rendering stages, track resource memory, and
compare workloads. ovrtx collects CPU and GPU measurements, grouped RTX stage
timings, and memory categories. You can read these measurements while rendering
continues, save them to files, or do both.

Capture lifecycle
-----------------

Profiling is process-wide. Create a renderer before starting capture, and assign
one part of your application responsibility for starting and stopping it. A
second start fails while profiling is active; it does not replace the capture.

Start with :py:func:`ovrtx.start_profiling()` or
:c:func:`ovrtx_start_profiling()`. With no output arguments, capture collects live
data without saving files. Rendering can continue concurrently with capture and
data reads.

Stop with :py:func:`ovrtx.stop_profiling()` or
:c:func:`ovrtx_stop_profiling()` before destroying the last renderer. Stopping
flushes and closes file output and may block. Arrange cleanup so it also runs
when your workload fails. Stopping an inactive capture succeeds while the
renderer system remains initialized.

Serialize capture-control calls with renderer teardown. Serialize data reads
with capture restart and teardown. Stopping profiling and starting it again
resets the capture clock and automatically resets each retained batch's progress
on its next read. Keep the batch alive between reads, including across restarts.

Profile a render loop
---------------------

The examples below capture 60 rendered frames and read profiling data every
500 ms, plus once after the last frame. The frame count is an example choice;
use your application's own loop condition. Rendering continues between reads.
The final read collects samples available at that time; it does not wait for
all asynchronously published measurements. Use file capture when you need a
saved recording.

These examples assume a live ``renderer`` attached to a populated ovstage,
with ``/Render/Camera`` committed at ``ordinal``. The C example also assumes
that :c:func:`ovrtx_update_from_stage()` has completed for that state; Python
performs that update as part of :py:meth:`ovrtx.Renderer.step()`.
See :doc:`ovstage_integration` for stage setup.

The Python example retains its copied batches for processing after capture.
The C++ example uses the C API and processes each batch before reusing its
storage. Both stop capture before the application destroys the renderer:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-render-loop-python]
         :end-before: # [/snippet:doc-profiling-render-loop-python]
         :dedent:

   .. tab-item:: C++ (C API)

      Include ``<ovrtx/ovrtx.h>``, ``<chrono>``, and ``<cstdio>``.

      .. filtered-literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-render-loop-c]
         :end-before: // [/snippet:doc-profiling-render-loop-c]
         :omit-markers:
         :dedent:

Read live measurements
----------------------

Use :py:func:`ovrtx.get_performance_data_update()` or
:c:func:`ovrtx_get_performance_data_update()` to copy a batch of measurements.
Initialize one batch per consumer and reuse it for subsequent reads:

* The first read returns all samples still retained by the active capture.
* Later reads return newly available samples, independently for each batch.
* Structured and JSON reads using the same batch share progress.
* A separate, initially empty batch rereads retained history without changing
  another consumer's progress.

Samples follow collection order within each metric, including across reads.
Timestamps are nanoseconds since capture started, but a measurement published
later can have an earlier timestamp. Preserve the returned order.
``collection_time_ns`` describes when the copy completed; it is informational,
not a filter or a bound on sample timestamps. Do not use it as a cursor.

Each metric provides:

* ``uid`` and ``parent_uid`` to identify the metric and its default hierarchy.
  Metric identities belong to the current capture; do not retain them across restarts.
* ``name``, ``units``, ``info``, and ``group_name`` to describe the measurement.
* ``values`` containing ``timestamp_ns``, ``value``, ``parent_uid``, and
  ``execution_id``. The sample parent identifies that invocation's parent;
  execution identity attributes the sample to a CPU thread or RTX GPU, with
  zero meaning unspecified.
* ``average``, ``minimum``, and ``maximum`` across the active capture, rather
  than just the newly copied samples.

Use the supplied units when displaying values. Timestamp units and measurement
units are separate: a timestamp is in nanoseconds even when its value describes
milliseconds, a percentage, or memory in MiB.

In Python, initialize ``data = ovrtx.ovrtx_performance_data_update_t()`` before
the first read. Each read returns a collection time and a list of dictionaries.
These copies are owned by Python and remain valid after another read or batch
release. Call :py:func:`ovrtx.release_performance_data_update()` in a ``finally``
block before renderer teardown; the retained native batch still owns resources.

In C, zero-initialize an ``ovrtx_performance_data_update_t`` before first use.
Its strings and arrays remain valid until you update or release that container.
Copy any data you need to keep before reusing it. Do not copy the container's
ownership or access the same container concurrently. Call
:c:func:`ovrtx_release_performance_data_update()` before destroying the last
renderer, including on error paths.

The snippets below print a batch. In C, include ``<ovrtx/ovrtx.h>`` and
``<stdio.h>``, initialize ``ovrtx_performance_data_update_t data = {0};`` once, and
retain ``data`` for subsequent reads. In Python, initialize the batch as
described above and retain it too.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-read-python]
         :end-before: # [/snippet:doc-profiling-read-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-read-c]
         :end-before: // [/snippet:doc-profiling-read-c]
         :dedent:

Reread retained history
~~~~~~~~~~~~~~~~~~~~~~~

The snippets below use a separate batch to reread retained history without
resetting capture or advancing the original ``data`` reader. Release the history
batch after copying or inspecting it, then resume incremental reads with ``data``:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-replay-python]
         :end-before: # [/snippet:doc-profiling-replay-python]
         :dedent:

   .. tab-item:: C

      .. filtered-literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-replay-c]
         :end-before: // [/snippet:doc-profiling-replay-c]
         :omit-markers:
         :dedent:

Polling and retained history
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copy every 500 ms to 1 s for background collection, or every 200 to 250 ms for a
live display. These are recommended starting points, not sampling controls.
Reading more often does not increase the producer's sampling rate.

Live history is bounded. A fresh batch cannot recover overwritten samples.
Choose a polling interval with room for scheduling delays, bursts, and the
time needed to copy the batch. Use the sample rate of each metric, not just
application FPS: a scope can produce several samples per frame.

Longer intervals produce larger batches. Copying and JSON serialization cost
also grows with the number of metrics, particularly RTX and memory metrics.
File capture is independent of live polling; enable it when you need a saved
recording instead of relying on retained live history.

JSON updates
~~~~~~~~~~~~

Use :py:func:`ovrtx.get_performance_data_update_as_json()` or
:c:func:`ovrtx_get_performance_data_update_as_json()` when your consumer needs
JSON. The document contains ``collection_time_ns`` and a ``metrics`` array.
The retained progress is shared with structured updates on the same batch. Non-finite sample
values are represented by JSON ``null``.

Python returns a timestamp and an owned string. C returns UTF-8 text in the
batch's ``json`` field, with the same container lifetime and release rules as
structured updates.

The snippets below request JSON using the batch from the preceding read:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-json-python]
         :end-before: # [/snippet:doc-profiling-json-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-json-c]
         :end-before: // [/snippet:doc-profiling-json-c]
         :dedent:

Stop capture
~~~~~~~~~~~~

The snippets below release capture resources. Put Python cleanup in a
``finally`` block after a successful start so release and stop both run,
including on failed reads. Ensure the C cleanup path is reached
on failed reads as well, and inspect both cleanup results.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-stop-python]
         :end-before: # [/snippet:doc-profiling-stop-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-stop-c]
         :end-before: // [/snippet:doc-profiling-stop-c]
         :dedent:

Interpret RTX timings
---------------------

RTX timings group rendering work by GPU, render graph, viewport, and render
tile. Groups describe stages such as G-Buffer, Path Tracing, Light Cache,
Radiance Cache, DLSS, Post Processing, and Output Processing. Availability
depends on the work performed; a missing stage is not a measured zero.

Grouped durations can combine separate operations. They do not describe a
single contiguous period of GPU execution or GPU occupancy. Compare the same
groups under comparable workloads, render settings, hardware, and capture
conditions.

Parent containers include child work. Do not sum a container and its children
to calculate a total. Keep GPU and viewport hierarchies separate when
comparing measurements.

Interpret memory measurements
-----------------------------

``RTX Memory`` measurements report tracked resource allocations in MiB
(1 MiB = 1,048,576 bytes). GPU allocations, host allocations, and virtual
reservations have separate hierarchies.

.. list-table:: Memory categories
   :header-rows: 1
   :class: compact-table
   :widths: 30 70

   * - Category
     - Contents
   * - Geometry
     - BVH, vertex attributes and primvars, instance and scene data, and
       geometry buffers, with subcategories where available.
   * - Textures
     - Tracked texture resources.
   * - Volumes
     - Tracked volume resources.
   * - Gaussians
     - Gaussian-owned resources, including their geometry and acceleration
       structures.
   * - SPG
     - Resources owned by Sensor Processing Graphs.
   * - Output Buffers
     - Tracked output buffers.
   * - Internal
     - Shared reserves and resources not assigned to the other categories.

Parents include their descendants. Do not add parent totals to child values,
or add virtual reservations to allocated memory. Tracked host allocations are
not process physical memory, and these resource totals are not a complete
measurement of process heap usage or residency. Treat process-memory and
device-memory indicators as separate measurements.

Save a capture
--------------

Provide an output directory or basename when starting capture to enable file
output. The directory must already exist and be writable. The basename must
not contain path separators; provide it without an extension.

In Python, either argument being non-``None`` enables saving. An empty string
selects that argument's default. In C, either non-null string pointer enables
saving, including a pointer to an empty string. A null configuration, or two
null string pointers, selects live-only capture.

The default output location is the persistent user directory, and the default
basename is timestamp-based. Existing recordings are not overwritten; name
collisions add a timestamp suffix. C configuration strings are copied before
the start call returns.

To save the render-loop example, replace its start call with the corresponding
snippet below. Keep the polling and cleanup unchanged. In Python,
``output_path`` is your chosen directory path. In C++, ``output_path`` and
``file_name`` are ``std::string`` values and the directory must already exist.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_profiling.py
         :language: python
         :start-after: # [snippet:doc-profiling-file-python]
         :end-before: # [/snippet:doc-profiling-file-python]
         :dedent:

   .. tab-item:: C++ (C API)

      .. literalinclude:: ../../tests/docs/c/test_profiling.cpp
         :language: cpp
         :start-after: // [snippet:doc-profiling-file-c]
         :end-before: // [/snippet:doc-profiling-file-c]
         :dedent:

Capture writes three CSV files with the chosen basename:

* ``<name>.rpm_info.csv`` describes the recorded metrics.
* ``<name>.rpm_data.csv`` contains sampled values with timestamp, value,
  parent UID, and execution ID for each metric UID.
* ``<name>.rpm_summary.csv`` contains summary statistics.

Stop capture before consuming the completed file set so pending output has
been flushed. The public capture contains public measurements; it does not
export detailed private render-pass or thread instrumentation.

Troubleshooting
---------------

**Capture does not start.** Check the error returned by the start call. Create
a renderer first, ensure another capture is not already active, and verify
that any requested output directory exists and is writable. Python raises
``RuntimeError``; C callers check the result and use
:c:func:`ovrtx_get_last_error()` for details.

**No new samples.** Confirm that capture is active and that the workload
produces the metric you are reading. Continue polling at an appropriate
cadence. Reuse the same batch for incremental reads; a new batch rereads
retained history. Progress resets automatically after restarting capture.

**History has gaps.** Check the time between reads, including scheduling and
copy delays, against the actual per-metric sampling rate. Poll more often or
enable file capture for future recordings. Reading again with a fresh batch only
returns samples still retained.

Further reading
---------------

* :doc:`application_flow` — renderer lifetime and the application loop.
* :doc:`../python_api/index` — Python profiling API reference.
* :doc:`../c_api/index` — C profiling API reference.
