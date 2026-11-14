.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-wpm-howto-intensity:

Tune Intensity
==============

The Lidar generic wpm model can report raw or range-normalized intensity.
Choose the convention, scale and optional lookup table to match the device's
output encoding. These controls change the intensity assigned to detected
returns; they do not determine which returns are detected.

The :doc:`Lidar generic core model intensity controls <../../lidar_core/howto/intensity>`
use different names, modes and scales.

Before you start. The controls are ``intensityProcessing``, ``intensityMappingType``,
``intensityScale`` and ``intensityMappingEncoding``, all under
``omni:sensor:LidarWpm:``. See :doc:`../attributes` and
:doc:`../../../reference/schemas` for values and defaults. Range normalization
depends on the selected :doc:`return-processing mode <return_processing>`.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-presentation-only:
.. _sensors-lidar-wpm-intensity-is-presentation:

Intensity encoding
------------------

``Intensity`` is a ``float32`` channel encoded after detection. Encoding does
not change peak selection, return counts, ordering or scan merging, and
cannot recover rejected returns. Detection depends on the processing mode and
thresholds defined in :doc:`../attributes`.

Accepted edits to the four intensity attributes preserve the scan and apply
to detected returns at the next publication. See :doc:`runtime_updates`.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-conventions:
.. _sensors-lidar-wpm-apparent-reflectivity:

Raw and range-normalized intensity
----------------------------------

``intensityProcessing`` selects one of two conventions. Both end in the same
presentation stage: a *base intensity* between 0 and 1 is passed through the
mapping selected by ``intensityMappingType`` and multiplied by
``intensityScale``.

.. code-block:: text

    raw:
        Intensity = intensityScale * map(clamp(rawDetectorIntensity, 0, 1))

    rangeNormalized, intensityScale > 0:
        fraction = clamp(apparentReflectivity / intensityScale, 0, 1)
        Intensity = intensityScale * map(fraction)

With ``raw``, base intensity is the detector's normalized response, clamped
to ``[0, 1]``. The same surface generally produces a weaker response at a
greater range.

With ``rangeNormalized`` (default), base intensity is apparent reflectivity
divided by ``intensityScale``. Apparent reflectivity is the reflectivity an
ideal diffuse surface facing the sensor would need to produce the detected
signal at that range, relative to the model's reference signal.

Normalization removes the modeled range and calibration response. In
``waveform`` and ``directDetector`` modes it also removes aperture response,
but retains detector noise. In ``directMaterial`` mode it removes range,
gain and divergence factors while retaining detector angular response.
Apparent reflectivity therefore depends on viewing angle, specularity and
model calibration; it is not a vendor-independent measurement or the material's
reflectivity alone.

Surface response depends on its non-visual material labels
(:doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>`). When
``omni:sensor:LidarWpm:useVisualMaterialInputs`` is on, the visual material is
consulted as well; refer to :doc:`USD Attributes <../attributes>`.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-nonlinear:

Non-linear mapping
------------------

``intensityMappingType = linear`` (the default) applies no lookup-table
adjustment to the base intensity.

``nonlinear`` and ``nonlinearEncodingOnly`` use ``intensityMappingEncoding``,
a table of finite values. For each return, the selected entry has index
``floor(baseIntensity * (encodingCount - 1))``, where ``encodingCount`` is the
number of table entries.

The table length determines how the selected entry is used:

- Fewer than ``intensityScale * 100`` entries: add it to the base intensity.
- At least ``intensityScale * 100`` entries: replace the base intensity with it.

At the default scale, the threshold is 255 entries. The mapped value is then
multiplied by ``intensityScale``.

``nonlinear`` and ``nonlinearEncodingOnly`` require a non-empty
``intensityMappingEncoding``. An empty table (the default) rejects the whole
parameter set; see :doc:`Retune the Sensor While It Runs <runtime_updates>`
for rejection behavior. ``nonlinearDecodingOnly`` requires no table and acts
like ``linear`` because this model has no decoding table.

.. note::

   The base intensity is clamped to the unit range before the lookup; the
   entries of the table are not. Author the table so that the mapped value
   stays in the unit range: replacement entries between 0 and 1, correction
   entries small enough that base plus entry stays between 0 and 1. Every
   published value then lies between 0 and ``intensityScale``, as it does
   with ``linear`` mapping.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-worked-numbers:

Calculation example
-------------------

With ``linear`` mapping and the default scale of ``2.55``, apparent
reflectivities of 8%, 10%, 100%, 180% and 255% are published as ``0.08``,
``0.10``, ``1.0``, ``1.8`` and ``2.55``. Values at or above 255% clamp to
``2.55``: the scale is the full scale, and, read as a fraction, the apparent
reflectivity at which the value saturates. A scale of ``1.0`` publishes the
apparent reflectivity itself, saturating at 100%. A zero scale publishes zero
intensity for every return, in every mode.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-verify:

Verification
------------

Read ``Intensity`` within :ref:`Counts[0]
<sensors-common-sensor-outputs-counts-bound>` and select entries with the
:ref:`VALID bit <sensors-common-sensor-outputs-valid-bit>` set in ``Flags``.
Check the following:

- Every value lies between 0 and ``intensityScale``.
- Face two plates of the same material to the sensor at two different
  ranges, both far enough that neither reads the full scale in ``raw``: a
  plate close to the sensor saturates the detector response and reads the
  full scale whatever its range. In
  ``rangeNormalized`` the two plates read about the same apparent
  reflectivity; in ``raw`` the farther plate reads smaller. If switching the convention leaves both values unchanged, check
  saturation and the update log; unchanged output alone does not establish
  that the edit was rejected.
- Switch ``intensityProcessing`` while the sensor runs. The new encoding applies at
  the next publication. It changes intensity for the same detected returns,
  preserving their count and order. Consecutive publications can still have
  different detections because of scene motion, scan timing or noise; a
  changed count alone says nothing about whether the edit was accepted.

.. _sensors-nonvisual-lidar-wpm-howto-intensity-troubleshooting:

Potential issues
----------------

- **Intensity saturates.** Check the convention first, ``raw`` against
  ``rangeNormalized``, then ``intensityScale``, then
  ``omni:sensor:LidarWpm:calibrationGain``, the detector field of view and the
  material assignment of the surfaces, before touching the detection
  thresholds: mapping cannot recover a signal the return pipeline already
  rejected, and a threshold edit changes which returns exist.
- **The values are on a different scale than the consumer expects.** A
  consumer has to know which processing mode and scale were selected, because
  no separate ``Reflectivity`` channel is published; see the ``Intensity`` description in
  :doc:`Outputs <../outputs>`.
- **An intensity edit appears to do nothing.** Either the table is not read,
  because only ``nonlinear`` and ``nonlinearEncodingOnly`` read
  ``intensityMappingEncoding``, or the parameter set was refused:
  ``intensityScale`` must be finite and non-negative, every entry of
  ``intensityMappingEncoding`` must be finite, the values of
  ``intensityProcessing`` and ``intensityMappingType`` must be spelled exactly
  as the schema lists them, and ``nonlinear`` or ``nonlinearEncodingOnly``
  needs a non-empty table. The reason is logged as an error; refer to
  :doc:`Retune the Sensor While It Runs <runtime_updates>` for what a refused
  set leaves in place and to
  :doc:`Sensor Definition Validation <../../../common/validation>`.

See also the :doc:`Symptom Index <../../../troubleshooting/symptoms>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the four presentation attributes, the detection thresholds and the material inputs.
- :doc:`Outputs <../outputs>` — channel layout and interpretation.
- :doc:`Choose a Return-Processing Mode <return_processing>` — return detection and ordering.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — bounding a read by ``Counts[0]`` and selecting valid points by ``Flags``.
