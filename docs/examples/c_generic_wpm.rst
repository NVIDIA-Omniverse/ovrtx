.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C API: Generic WPM Contributions
================================

This C++ example uses the C API to read
:ref:`Contributions <generic-wpm-contributions>`, copy named tensors and CPU
parameters, and save valid records to CSV. It also demonstrates coordinated
selector updates, rejected-edit retention and recovery. The
:doc:`Python example <python_generic_wpm>` uses the same recipes and scene.

Build and Run
-------------

Use a C++17 compiler, CMake 3.16 or newer, an RTX GPU and a
:doc:`supported driver <../driver_requirements>`. Both ovrtx and ovstage SDKs
must contain the APIs and schemas used by this checkout and come from the same
release train. The neighboring examples' package pins are not a verified
minimum version for Generic WPM. See :doc:`../c_api/getting_started` for SDK
setup and loader requirements.

The program takes the ovrtx public-source root as its first argument. Keep its
``tests/docs`` and ``examples/python/generic-wpm`` directories available: the
consumer reuses their recipe layers, scene and cube mesh. It does not bake in
a build-machine asset path.

From ``examples/c/generic-wpm``, configure against containing SDKs and run:

.. code-block:: bash

   cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="<ovrtx-sdk>;<ovstage-sdk>"
   cmake --build build --config Release
   ./build/generic-wpm ../../.. depth _output/depth.csv
   ./build/generic-wpm ../../.. gaussian_bloom _output/bloom.csv
   ./build/generic-wpm ../../.. mixed _output/mixed.csv --live-edits

On Windows, use ``build/Release/generic-wpm.exe``. The example links both shared
loaders; CMake prepares their runtime dependencies. The first capture may spend
several minutes compiling shaders.

The final three arguments are optional: recipe defaults to ``depth`` and output
defaults to ``_output/contributions.csv``. ``--live-edits`` requires ``mixed``
and an explicit output argument. Renderer logs are saved beside the CSV.

Read and Filter the Output
--------------------------

The consumer steps the attached stage, waits, fetches the results, and finds the
output by its full RenderVar path. It maps to CPU, looks up tensors and parameters
by name, and copies them before unmapping. The
:ref:`capture workflow <generic-wpm-example-runtime>` shows the paired Python/C
stepping and mapping calls, including their lifetime rules.

The snippets below preserve logical coordinates while filtering invalid slots.
The C API example writes each valid path to CSV; the Python example gathers
the corresponding arrays for NPZ/Rerun output:

.. tab-set::

   .. tab-item:: C API (C++)
      :sync: c

      .. literalinclude:: ../../examples/c/generic-wpm/main.cpp
         :caption: ``main.cpp``, from the runnable :doc:`C example <c_generic_wpm>`.
         :language: cpp
         :start-after: // [snippet:doc-generic-wpm-valid-slots-c]
         :end-before: // [/snippet:doc-generic-wpm-valid-slots-c]
         :dedent:

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../examples/python/generic-wpm/main.py
         :caption: ``main.py``, from the runnable :doc:`Python example <python_generic_wpm>`.
         :language: python
         :start-after: # [snippet:doc-generic-wpm-read-output]
         :end-before: # [/snippet:doc-generic-wpm-read-output]
         :dedent:

Example Results
---------------

One recorded ``depth`` run wrote 15 records. Slot 7 has an 11 m range; oblique paths are longer.
Only this co-located, one-bounce recipe fills ``range_m``. The other recipes
leave that column empty and report total ``round_trip_m`` instead.

``gaussian_bloom`` allocates 1,215 slots; one recorded run wrote 819 valid records. Their
original slot IDs preserve the gaps caused by clipped receiver neighborhoods.

One recorded ``mixed --live-edits`` run wrote five captures with 2, 6, 18, 18
and 2 records. The corresponding allocated capacities are 2, 6, 18, 18 and 2.
The fourth request, Tx/Rx/page ``0/1/0``, is invalid and retains accepted
selectors ``2/1/1``. The last request restores ``0/0/0``. The console prints
requested and accepted selectors, while the CSV identifies captures by ordinal.
See :ref:`generic-wpm-example-live-edits` for the coordinated write/seal/step calls.
The program exits nonzero if its scene-specific count, depth-range or retention
checks fail. These checks verify this example scene, not a valid-count guarantee
for arbitrary scenes.

Positions in this origin-centered, meter-unit scene can be plotted directly.
For other coordinate systems, consult the guide's channel units; do not assume
``HitPosWorld`` is absolute world meters. The example does not read
``DeltaTimeNs``.
