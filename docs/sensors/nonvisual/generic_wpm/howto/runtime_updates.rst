.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm-howto-runtime-updates:
.. _generic-wpm-mixed-recipe:

Switch Stored Patterns
======================

Change geometry, ray counts and receiver groups without replacing their stored arrays.

**Before you start.** Create the base sensor and output in :doc:`Set Up a Sensor <setup>`. The USD Python tab below adds the alternative patterns to that ``stage``.

Stored pattern alternatives
---------------------------

Store alternatives when different captures should use different geometry,
ray counts or receiver connections. A stored transmitter pattern may contain
several transmitter elements; selecting it activates that complete pattern,
not one element within it. Receiver patterns are selected independently.

Each transmitter pattern also assigns its ray bundle and receiver-mapping rule.
Changing the transmitter selector also selects that pattern's bundle and mapping
rule. When using ``map``, a mapping-page change selects another page of receiver
groups. Refer to
:ref:`patterns and selection <sensors-nonvisual-generic-wpm-attributes-patterns>`
for the role-local indices and packed family arrays.

The layer below combines Free/Grid
transmitter and receiver patterns, Free/Grid/Gaussian ray bundles, and two
mapping pages. Switching uses the three scalar selectors rather than replacing
the arrays:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/generic_wpm_mixed.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-mixed]
         :end-before: # [/snippet:doc-generic-wpm-mixed]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-mixed-python]
         :end-before: # [/snippet:doc-generic-wpm-mixed-python]
         :dedent:


The stored pages contain groups ``[0, 1, 2]`` and ``[2, 0]`` on page 0,
and ``[1]`` and ``[0, 1]`` on page 1. The following selections are valid:

.. csv-table::
   :header: "Tx / Rx / page", "Active Tx / Rx", "Rays per Tx", "Ordered Rx IDs", "Slots"
   :widths: 22, 20, 18, 25, 15
   :class: compact-table

   "``0 / 0 / 0``", "1 / 3", "1 (Free)", "``[2, 0]``", "2"
   "``1 / 1 / 1``", "2 / 2", "3 (Grid)", "``[1]``", "6"
   "``2 / 1 / 1``", "1 / 2", "9 (Gaussian)", "``[0, 1]``", "18"

For the initial selection, transmitter pattern 0 assigns ray bundle 0 and
page-local group 1. Page 0's first group consumes the first three entries of
``rxIndices``, so group 1 reads entries 3 and 4: receiver IDs ``[2, 0]``.
Its two slots address elements of receiver pattern 0, not stored global IDs.

Requesting ``0 / 1 / 0`` is invalid because page 0 includes receiver ID 2 while
receiver pattern 1 has only two elements. If the previous accepted selection
was ``2 / 1 / 1``, it remains active with 18 slots. Selecting ``0 / 0 / 0``
again returns to two slots. This demonstrates why page and receiver selections
must be coordinated and why output metadata reports the accepted selectors.

Publish coordinated edits
-------------------------

Write all related selectors at one new ordinal, finish the writes, and advance
the write floor once before rendering. Do not step between those writes.
The :ref:`paired Python and C example <generic-wpm-example-live-edits>` shows
this sequence. Read the accepted selector parameters from the completed output
before deciding that an edit took effect.
Attribute meanings are on :doc:`USD Attributes <../attributes>`; complete
types and defaults are in :doc:`Sensor API Schemas <../../../reference/schemas>`.

Verification
------------

1. Run the example with live edits.

2. The requested selector triplets are ``0/0/0``, ``1/1/1``, ``2/1/1``, ``0/1/0`` and ``0/0/0``.

3. Read the accepted triplet and capacity after each request: capacities are 2, 6, 18, 18 and 2.

4. The invalid fourth request must retain ``2/1/1``; the final request must restore ``0/0/0``.

5. This verifies configuration acceptance rather than a scene-dependent valid-return count.

Potential issues
----------------

Use the :ref:`Generic wpm checks <sensors-troubleshooting-symptoms-generic-wpm>`
for confirming checks and recovery.

- **The accepted selectors stay unchanged.** A rejected batch retains the complete previously accepted configuration while the scene continues to advance. Refer to :ref:`configuration acceptance <sensors-nonvisual-generic-wpm-attributes-live-edits>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the meanings and constraints of the controls.
- :doc:`Outputs <../outputs>` — contribution channels, layout and validity.
- :doc:`Limitations <../../../troubleshooting/limitations>` — model scope and bounds.
