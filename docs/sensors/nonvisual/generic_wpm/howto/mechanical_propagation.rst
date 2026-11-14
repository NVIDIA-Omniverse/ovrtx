.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm-howto-mechanical-propagation:

Select Mechanical Propagation
=============================

Trace scalar mechanical contributions with an acoustic wavelength. Keep a
single transmitter, receiver and ray while choosing the wave type and
wavelength, so the resulting path can be interpreted before expanding the
sensor layout.

**Before you start.** Create the base sensor and output in :doc:`Set Up a Sensor <setup>`; the USD Python tab assumes that base exists on ``stage``.

Mechanical paths
----------------

Select ``waveType = "mechanical"`` and author an acoustic wavelength.
This example uses 6,700,000 nm (6.7 mm).
Changing wave type alone would leave the default electromagnetic wavelength.

One co-located Free transmitter/receiver pair and one Free ray keep the geometry
simple, producing one slot and a 22 m direct-return path from the front wall:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/generic_wpm_acoustic.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-acoustic]
         :end-before: # [/snippet:doc-generic-wpm-acoustic]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-acoustic-python]
         :end-before: # [/snippet:doc-generic-wpm-acoustic-python]
         :dedent:


Geometry and pose conventions are unchanged. The output contains scalar
path contributions, not an ultrasound waveform.
``DeltaTimeNs`` remains a firing offset, not an arrival timestamp.

Attribute meanings are on :doc:`USD Attributes <../attributes>`; complete
types and defaults are in :doc:`Sensor API Schemas <../../../reference/schemas>`.

Verification
------------

1. Read the accepted dimensions and a nonzero ``Valid`` slot from the example.

2. Its direct path to the front wall and back is 22 m. ``DeltaTimeNs`` records firing offset; it must not be interpreted as acoustic arrival time.

3. Refer to :doc:`Outputs <../outputs>` for its timestamp reference.

Potential issues
----------------

Use the :ref:`Generic wpm checks <sensors-troubleshooting-symptoms-generic-wpm>`
for confirming checks and recovery.

- **The wavelength does not match the intended wave type.** Changing wave type does not convert wavelength; author both together. Refer to :ref:`propagation controls <sensors-nonvisual-generic-wpm-attributes-propagation>`.
- **Firing offsets do not equal acoustic arrival times.** They represent emission timing rather than wave travel time. Refer to :ref:`firing times <sensors-nonvisual-generic-wpm-attributes-timing>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the meanings and constraints of the controls.
- :doc:`Outputs <../outputs>` — contribution channels, layout and validity.
- :doc:`Limitations <../../../troubleshooting/limitations>` — model scope and bounds.
