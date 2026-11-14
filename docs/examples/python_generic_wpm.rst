.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Generic WPM Configurations
==================================

Run the small configurations from :doc:`../sensors/nonvisual/generic_wpm/index` and inspect their
raw :ref:`Contributions <generic-wpm-contributions>`. The example saves the channels
to an NPZ file and optionally visualizes derived hit samples with Rerun.
It does not turn contributions into detector outputs.

The shared scene reuses the documentation cube mesh to form a steel enclosure.
The sensor is at its center. The X/Z walls are 11 m from the origin; the Y walls
are 12 m away. No visual
lights are needed for this nonvisual capture.

Prerequisites and Running
-------------------------

Use Python 3.10–3.14, an RTX GPU and a :doc:`supported driver <../driver_requirements>`.
Run from ``examples/python/generic-wpm``:

.. code-block:: bash

   uv run main.py --recipe depth --no-rr --png _output/depth.png
   uv run main.py --recipe lidar --rrd _output/lidar.rrd
   uv run main.py --recipe acoustic --no-rr --output _output/acoustic.npz
   uv run main.py --recipe mixed --live-edits --no-rr

The first capture may take several minutes while shaders compile. Without
``--no-rr`` or ``--rrd``, the example opens the Rerun viewer.

.. list-table::
   :class: compact-table
   :header-rows: 1

   * - Option
     - Meaning
   * - ``--recipe NAME``
     - ``depth`` (default), ``planar``, ``cylindrical``, ``lidar``, ``gaussian``,
       ``gaussian_bloom``, ``multistatic``, ``multistatic_map``, ``acoustic`` or ``mixed``.
   * - ``--output PATH``
     - Raw channel and CPU-parameter NPZ; defaults to ``_output/NAME.npz``.
       A renderer log is written beside it.
   * - ``--no-rr``
     - Run without the viewer.
   * - ``--rrd PATH``
     - Save a headless recording; cannot be combined with ``--no-rr``.
   * - ``--png PATH``
     - Save labeled range cells for ``depth``, ``planar`` or ``cylindrical``.
   * - ``--live-edits``
     - For ``mixed`` only: switch selections, reject an invalid edit and recover.
       Saved outputs contain the final recovered capture.

Configuration
-------------

Each recipe is a sensor/RenderProduct layer under ``tests/docs/usd/data``.
The runner composes it with ``scene.usda``. Keep the public tree's relative layout
when copying the example so its recipe layers and cube reference resolve.

For example, the following override layer adds a one-cell receiver neighborhood
to the Gaussian recipe. Its sublayer supplies the sensor, patterns and output.
This increases capacity from 135 to 1,215 slots without increasing the ray count;
the guide contains the full recipes and common setup.

The USD Python tab assumes the Gaussian pattern has been authored on ``stage``.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../tests/docs/usd/data/generic_wpm_gaussian_bloom.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-gaussian-bloom]
         :end-before: # [/snippet:doc-generic-wpm-gaussian-bloom]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-gaussian-bloom-python]
         :end-before: # [/snippet:doc-generic-wpm-gaussian-bloom-python]
         :dedent:

Example Output
--------------

One recorded run of the depth recipe printed ``shape=(1, 15, 1, 1, 1), valid=15/15``. Its center
cell is 11 m away; oblique samples have longer paths to the same wall. The image
shows sampled range cells, not pinhole-camera pixels.

.. figure:: ../img/sensors/nonvisual/generic_wpm_depth_ranges.avif
   :width: 750
   :alt: Three by five labeled direct-return ranges, with an 11 meter center sample and longer oblique ranges.

   *Range derived from the depth recipe's valid direct-return contributions.*

The NPZ uses channel names as keys and prefixes CPU parameter names with
``param_``. Reshape records in ``[tile, tx, rayInTx, bounce, receiverSlot]``
order and filter every payload by ``Valid != 0``. The Rerun view plots valid
``HitPosWorld`` samples; multiple contributions can occupy the same position.

.. _generic-wpm-example-runtime:

Capture and Read Contributions
------------------------------

The following Python/C snippets use an attached ovstage and the recipe's
``/Render/GenericWpm`` RenderProduct. The :doc:`C API example <c_generic_wpm>`
provides the complete C++ application. For stage attachment and cleanup order,
see :doc:`../core/ovstage_integration`.

Step a Sealed Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finish stage writes and advance the write floor before rendering their ordinal.
The snippets below step the 10 Hz example and obtain its frame. Initial repeated
steps allow pipeline warmup:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../examples/python/generic-wpm/main.py
         :caption: ``main.py``, from the runnable :doc:`Python example <python_generic_wpm>`.
         :language: python
         :start-after: # [snippet:doc-generic-wpm-step]
         :end-before: # [/snippet:doc-generic-wpm-step]
         :dedent:

   .. tab-item:: C API (C++)
      :sync: c

      .. literalinclude:: ../../examples/c/generic-wpm/main.cpp
         :caption: ``main.cpp``, from the runnable :doc:`C example <c_generic_wpm>`.
         :language: cpp
         :start-after: // [snippet:doc-generic-wpm-step-c]
         :end-before: // [/snippet:doc-generic-wpm-step-c]
         :dedent:

Copy the CPU Output
~~~~~~~~~~~~~~~~~~~

Find :ref:`Contributions <generic-wpm-contributions>` by its full RenderVar prim
path, ``/Render/GenericWpm/Contributions``, not just its ``sourceName``. CPU
mapping waits for the producing GPU work and copies tensors to host memory.
The following snippets find channels and CPU parameters by name, then take
independent copies before releasing the mapping:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../examples/python/generic-wpm/main.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-copy-contributions]
         :end-before: # [/snippet:doc-generic-wpm-copy-contributions]
         :dedent:

   .. tab-item:: C API (C++)
      :sync: c

      The application has found the RenderVar's ``handle`` in the fetched
      results. Its ``copy_tensor()`` helper validates tensor type and layout,
      then copies the data into an owning vector:

      .. literalinclude:: ../../examples/c/generic-wpm/main.cpp
         :language: cpp
         :start-after: // [snippet:doc-generic-wpm-read-output-c]
         :end-before: // [/snippet:doc-generic-wpm-read-output-c]
         :dedent:

In C, mapped pointers expire when you unmap. After processing a step, release
its results with :c:func:`ovrtx_destroy_results()`. Python DLPack views retain
their mapping while referenced, even beyond a ``with`` block. Independent copies
make ownership explicit and allow prompt release of renderer buffers. Dropping
step results does not invalidate a live mapping.

For GPU consumers, use linear CUDA mapping with producer and completion
synchronization; see :ref:`mapping-outputs`. This output is not a CUDA image array.

Filter Valid Slots
~~~~~~~~~~~~~~~~~~

The snippet below reconstructs logical slot coordinates from copied CPU
parameters and filters copied payloads. The data remains usable after the
renderer is destroyed. Keeping coordinates before compacting the records
preserves which transmitter, ray, bounce and receiver slot produced each sample:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../examples/python/generic-wpm/main.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-read-output]
         :end-before: # [/snippet:doc-generic-wpm-read-output]
         :dedent:

   .. tab-item:: C API (C++)
      :sync: c

      .. literalinclude:: ../../examples/c/generic-wpm/main.cpp
         :language: cpp
         :start-after: // [snippet:doc-generic-wpm-valid-slots-c]
         :end-before: // [/snippet:doc-generic-wpm-valid-slots-c]
         :dedent:

Before reshaping, distinguish a completed capture from EMPTY output: an EMPTY
capture still has named channels, but their leading dimensions are zero.
Warmup may report accepted capacity parameters while the channel tensors are
still empty. Wait for a completed capture rather than reshaping empty tensors
to that capacity. Allocated slots with all ``Valid = 0`` instead mean the capture
completed without positive-power contributions.

.. _generic-wpm-example-live-edits:

Change Active Patterns
----------------------

Without ``--live-edits``, ``mixed`` renders its initial authored selection.
With it, the requested Tx/Rx/page triplets are ``(0,0,0)``, ``(1,1,1)``,
``(2,1,1)``, ``(0,1,0)`` and ``(0,0,0)``. The fourth is invalid: the accepted
triplet stays ``(2,1,1)`` with 18 slots. The final valid request restores two
slots. The console reports both requested and accepted selectors.

The snippets below publish all three scalar writes at one new ordinal and
advance the write floor once, after the writes complete. Do not step between
the writes. Python receives the requested ``tx``, ``rx`` and ``page`` values;
C receives the ``requested`` triplet and a single-prim ``sensor`` query for
``/World/Sensor``:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../examples/python/generic-wpm/main.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-select-patterns]
         :end-before: # [/snippet:doc-generic-wpm-select-patterns]
         :dedent:

   .. tab-item:: C API (C++)
      :sync: c

      .. literalinclude:: ../../examples/c/generic-wpm/main.cpp
         :language: cpp
         :start-after: // [snippet:doc-generic-wpm-select-patterns-c]
         :end-before: // [/snippet:doc-generic-wpm-select-patterns-c]
         :dedent:

Render the sealed ordinal and compare the accepted selector CPU parameters with
the requested values. A rejected edit retains the complete accepted
configuration, not the previous frame: tracing continues against the current
scene. See :ref:`generic-wpm-live-edits` for the model's acceptance rules.

The guide covers modality limits.
