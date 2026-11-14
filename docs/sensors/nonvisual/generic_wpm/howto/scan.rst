.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm-howto-scan:

Configure a Full-Circle Scan
============================

Sample a full azimuth circle with a specified firing order. Use the grid's
layout to choose which direction is visited next and its time offsets to choose
when that sample is emitted within a capture.

**Before you start.** Author the base and depth patterns from :doc:`Sample a Depth Grid <depth_sampling>`; the USD Python tab modifies that existing ``stage``.

Timed angular grid
------------------

A 4 by 16 spherical grid represents four elevation rows scanned over a full
azimuth circle. Matching transmitter/receiver grids and one Free ray per
transmitter retain direct ``1to1`` pairing and produce 64 slots.

The override below uses ``columnMajor`` so all four elevations are visited before
advancing azimuth. Transmitter offsets span 0 to 1,000,000 ns across all 64
elements, not a separate interval for each row. The inherited single-ray bundle
has zero ray-local offset, so each ray fires at its transmitter's offset.
The sensor capture rate and these within-capture offsets are separate controls;
see :ref:`firing times <sensors-nonvisual-generic-wpm-attributes-timing>`.
The layer below authors the scan geometry and timing together:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/generic_wpm_lidar.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-lidar]
         :end-before: # [/snippet:doc-generic-wpm-lidar]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-lidar-python]
         :end-before: # [/snippet:doc-generic-wpm-lidar-python]
         :dedent:


The final azimuth column does not repeat the first direction. Timing still
includes both endpoints. The enclosure supplies targets around the full circle;
an open scene can leave invalid slots. The complete scan is traced each frame.
This configures sampling and firing offsets, not a rotating-device scheduler
or lidar detector. The static enclosure does not demonstrate motion distortion.

Attribute meanings are on :doc:`USD Attributes <../attributes>`; complete
types and defaults are in :doc:`Sensor API Schemas <../../../reference/schemas>`.

Verification
------------

1. Confirm ``numTx = 64``, ``raysPerTx = 1`` and ``groupSize = 1`` in the completed output.

2. The reported transmitter grid has four rows, sixteen columns and column-major order.

3. Inspect valid ``DeltaTimeNs`` values against the firing schedule.

4. Compare the first and final azimuth directions: the final column must not repeat the first.

Potential issues
----------------

Use the :ref:`Generic wpm checks <sensors-troubleshooting-symptoms-generic-wpm>`
for confirming checks and recovery.

- **Some directions have no return.** Open scene directions can leave allocated slots invalid. Refer to :doc:`Outputs <../outputs>`.
- **A scan does not extend into later captures.** Firing offsets select motion samples inside one complete capture. Refer to :ref:`firing times <sensors-nonvisual-generic-wpm-attributes-timing>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the meanings and constraints of the controls.
- :doc:`Outputs <../outputs>` — contribution channels, layout and validity.
- :doc:`Limitations <../../../troubleshooting/limitations>` — model scope and bounds.
