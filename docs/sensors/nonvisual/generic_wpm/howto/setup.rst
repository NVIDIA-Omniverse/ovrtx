.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm-howto-setup:
.. _generic-wpm-examples:

Set Up a Sensor
================

Create a sensor, select a complete pattern and read its first capture.
Start with a simple direct-return layout so each valid contribution has a clear
geometric interpretation before adding more rays, bounces or receivers.

**Before you start.** Read :doc:`Your First Lidar Sensor <../../../first_sensor>` for the shared workflow and have the :doc:`Python example <../../../../examples/python_generic_wpm>` or :doc:`C example <../../../../examples/c_generic_wpm>` available.

Author the sensor and output
----------------------------

The sensor prim carries the trace definition: the propagation controls and
transmitter, receiver and ray patterns, plus their receiver mappings. The
RenderProduct selects that sensor,
and its RenderVar requests the :ref:`Contributions output
<sensors-nonvisual-generic-wpm-outputs-requesting>`.

The base layer establishes the sensor and its RenderProduct. The 10 Hz frame
rate is configured through the shared ``omni:sensor:frameRate`` attribute.
One bounce keeps the examples' path interpretation simple. The rotation aligns
the sensor's +X-forward basis with world +X in this Z-up, meter-unit scene.
The USD Python snippets use an existing USD ``stage``; keep these imports for
the pattern recipes that follow. The base deliberately leaves patterns for
those recipes to define:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/generic_wpm_base.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-base]
         :end-before: # [/snippet:doc-generic-wpm-base]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-imports-python]
         :end-before: # [/snippet:doc-generic-wpm-imports-python]
         :dedent:

      .. literalinclude:: ../../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-base-python]
         :end-before: # [/snippet:doc-generic-wpm-base-python]
         :dedent:

Choose a complete pattern
-------------------------

The base layer leaves the transmitter, receiver and ray arrays empty. Complete it
with :doc:`Sample a Depth Grid <depth_sampling>` or one of the other
:doc:`configuration recipes <index>`. A complete recipe makes four choices:

1. Place the transmitter elements relative to the sensor.
2. Assign a ray bundle to the stored transmitter pattern. Every element of that
   pattern emits the bundle in its own transmitter frame.
3. Place the receiver elements relative to the sensor. Their poses are authored
   separately from the transmitter poses.
4. Choose which receivers are evaluated for each transmitter's paths through the
   :ref:`receiver mapping <sensors-nonvisual-generic-wpm-attributes-mapping>`.

The depth recipe starts with matching transmitter and receiver grids, one ray
per transmitter and paired receivers. Refer to
:ref:`patterns and selection <sensors-nonvisual-generic-wpm-attributes-patterns>`
for the relationship between stored patterns and the active capture.

Author the stage units, up-axis and time-code rate on the root layer; sublayers
do not supply stage metadata. Keep the referenced layers together.

The runnable examples compose the recipe with a steel enclosure. Its walls are
11 m from the sensor along world X/Z and 12 m along world Y. The scene uses the
``steel`` label.
Refer to :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>`
for authoring labels.

Render and read a capture
-------------------------

Load the composed root into an attached stage, complete its writes, and step
its RenderProduct. The examples' one-tile, one-bounce configuration allocates
``numTx * raysPerTx * groupSize`` slots. Read the output dimensions and
``Valid`` before consuming their payloads. A slot identifies one transmitter,
one emitted ray and one receiver connection at the single allowed bounce.
Only a valid slot supplies a contribution to your application's processing.

The sensor returns paths rather than a completed detector result. For the depth
recipe, the first useful processing step is to derive range from a valid direct
path whose emission and receiver origins coincide. The conditions for that
calculation are in :doc:`Sample a Depth Grid <depth_sampling>` and the
:ref:`channel descriptions <sensors-nonvisual-generic-wpm-outputs-channels>`.

Refer to the :doc:`Python example <../../../../examples/python_generic_wpm>`
and :doc:`C example <../../../../examples/c_generic_wpm>` for the complete
applications and their run commands.
Attribute meanings are on :doc:`USD Attributes <../attributes>`; complete
types and defaults are in :doc:`Sensor API Schemas <../../../reference/schemas>`.

Verification
------------

1. Run the ``depth`` recipe and inspect the accepted dimensions and nonempty ``Valid`` tensor.

2. Read valid path distances as described in :doc:`Sample a Depth Grid <depth_sampling>`.

3. A zero-length tensor is an empty output, not an allocated capture with no valid returns.

Potential issues
----------------

Use the :ref:`Generic wpm checks <sensors-troubleshooting-symptoms-generic-wpm>`
for confirming checks and recovery.

- **No capture.** Required patterns may be empty or the output request may be missing. Refer to :doc:`USD Attributes <../attributes>` and :doc:`Outputs <../outputs>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the meanings and constraints of the controls.
- :doc:`Outputs <../outputs>` — contribution channels, layout and validity.
- :doc:`Limitations <../../../troubleshooting/limitations>` — model scope and bounds.
