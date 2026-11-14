.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-radar-howto-spec-sheet-profile:

Build a Profile from a Spec Sheet
=================================

Build a Radar generic wpmDmat model profile by separating published values,
derived values and parameters that need calibration. The :doc:`lidar profiling
guide <../../lidar_core/howto/spec_sheet_profile>` explains this method;
:doc:`choose_parameters` maps radar specifications to attributes.

Before you start. Review the :doc:`model <../index>`, :doc:`attributes <../attributes>`,
:doc:`parameter mapping <choose_parameters>` and
:doc:`scan authoring <scan_configurations>` before building a profile.

Profiling workflow
------------------

Start with published specifications, retain defaults for unavailable values,
and record each value's source. Validate the profile against recordings or
controlled scenes. See the :doc:`lidar profiling guide
<../../lidar_core/howto/spec_sheet_profile>` for the shared method.

.. _sensors-nonvisual-radar-howto-spec-sheet-profile-procedure:

Build the profile in this order:

1. **List the device's operating modes.** A radar datasheet usually describes
   several: a near and a far scan, a short-range and a long-range mode, a wide
   and a narrow field of view. Each mode has its own maximum range, field of
   view, resolution and waveform, and often its own cycle time. Write them down
   separately.
2. **Author one scan configuration per mode.** The first scan, ``s001``, comes
   with the model's schema; every further mode is one more instance of the scan
   schema, ``s002`` and upward. :doc:`scan_configurations` covers the authoring.
3. **Transfer the datasheet values of each mode into its scan**, and stay inside
   that mode. The table on :doc:`choose_parameters` says which attribute takes
   which field.
4. **Fill the shared identification and rate attributes** on the prim: the
   output rate, the start offset and the identification strings. The next
   section says what goes where.
5. **Leave calibration-dependent values at their defaults and mark them.**
   Record which values you copied, which you derived and which are defaults
   waiting for a measurement; the four source-confidence
   categories the lidar tutorials use (:ref:`Source confidence <sensors-recipes-source-confidence>`) serve a radar profile just as well.
6. Compare authored limits with the output parameters using
   :doc:`choose_parameters`, then run the seven checks in
   :doc:`validate_parameterization`.

.. _sensors-nonvisual-radar-howto-spec-sheet-profile-modes:
.. _sensors-nonvisual-radar-howto-spec-sheet-profile-shared:
.. _sensors-nonvisual-radar-howto-spec-sheet-profile-groups:

Parameter sources
-----------------

Keep each scan's values within one :ref:`operating mode
<sensors-nonvisual-radar-howto-choose-parameters-one-operating-mode>`.
:doc:`Multiple scans <scan_configurations>` share the authored frame rate and
run in :ref:`sequence <sensors-nonvisual-radar-howto-scan-configurations-cycle>`.

Author identification, rate and start offset with the
:ref:`shared sensor attributes <sensors-common-sensor-configuration-shared-attributes>`.
See :ref:`radar defaults <sensors-nonvisual-radar-attributes-identification>`
and :ref:`scan-rate behavior <sensors-nonvisual-radar-attributes-frame-rate>`.

Map the remaining specifications using the
:ref:`datasheet table <sensors-nonvisual-radar-howto-choose-parameters-datasheet-table>`.
Check which controls apply to the selected
:ref:`processing mode <sensors-nonvisual-radar-attributes-mode-split>`.
Label default values that still need :ref:`calibration or simulation tuning
<sensors-nonvisual-radar-howto-choose-parameters-calibration>`.

.. _sensors-nonvisual-radar-howto-spec-sheet-profile-verify:

Verification
------------

Run :doc:`Sensor Definition Validation <../../../common/validation>` to
check the layer before rendering. Then compare authored scan limits with
output parameters using the :ref:`configuration check
<sensors-nonvisual-radar-howto-choose-parameters-reach-the-model>`.

Use targets at known ranges and angles to verify coverage and coordinates.
Check material labels, scan order and motion against the intended behavior.
Scene motion requires an active :ref:`motion BVH <sensors-common-output-configuration-motion-bvh>` (``AUTO`` or ``ENABLE``);
see :doc:`moving_targets` for setup and behavior when disabled.
Follow the seven scenarios in :doc:`validate_parameterization`.

Potential issues
----------------

.. _sensors-nonvisual-radar-howto-spec-sheet-profile-gap:

If a published field has no corresponding attribute, it may describe
calibration data, processing firmware or proprietary post-processing that the
model does not simulate: a tracked object list, a vendor's clutter suppression, a
per-unit antenna calibration. Record the gap as a labeled default rather than
using an unrelated attribute. See :ref:`unmapped specifications
<sensors-nonvisual-lidar-core-howto-spec-sheet-profile-gap>`.

.. _sensors-nonvisual-radar-howto-spec-sheet-profile-units:

Check units.
``maxAzAngDeg`` and ``maxElAngDeg`` take half-angles, not the full field of
view; :ref:`Half-angles
<sensors-nonvisual-radar-howto-choose-parameters-half-angles>` shows how to
catch the mistake. ``waveLengthMm`` is in millimeters (about ``3.9`` for a
77 GHz radar), and ``WAVEFORM`` processing derives the carrier frequency from
it. The chirp duration and
``chirpRepetitionTimeSequence`` entries are in seconds and the chirp bandwidth
in hertz, not in
microseconds and megahertz. ``omni:sensor:frameRate`` is the rational pair
``(20, 1)``, not the plain number ``20``.

Related
-------

- :doc:`Choose Parameter Values <choose_parameters>` — the datasheet-to-attribute table, the three kinds of value, the half-angle warning and configuration verification.
- :doc:`Validate a Parameterization <validate_parameterization>` — ordered validation scenarios for each scan configuration.
- :doc:`Run More Than One Scan Pattern <scan_configurations>` — one scan per operating mode, how scans are ordered and cycled, and reading back which scan produced a frame.
- :doc:`Sensor API Schemas <../../../reference/schemas>` — the generated tables of every attribute, type, default and doc string.
- :doc:`Build a Profile from a Spec Sheet, depth camera <../../../visual/depth_camera/howto/spec_sheet_profile>` — the same method for the Camera single-view stereo depth model.
