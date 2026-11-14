.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-radar-howto-choose-parameters:
.. _sensors-do-choose-radar-parameters:

Choose Parameter Values
=======================

A radar profile combines published device specifications, measured calibration
values and simulation settings. Map each operating mode to a scan instance on
an ``OmniRadar`` prim, then choose its coverage, resolution, antenna and
processing parameters. Keep the source and uncertainty of each value so the
profile can be validated against the device.

**Before you start.** :doc:`../index`, :doc:`../attributes`,
:doc:`scan_configurations`.

.. note::

   Per-scan attributes appear here without their
   ``omni:sensor:WpmDmat:scan:<instance>:`` prefix; ``waveLengthMm``,
   ``traceTreeDepth`` and ``cfarMode`` live under ``omni:sensor:WpmDmat:`` and
   ``frameRate`` under ``omni:sensor:``. Which attribute lives where is
   :ref:`the three namespaces <sensors-nonvisual-radar-attributes-namespaces>`.

Parameter selection
-------------------

A radar prim carries three kinds of value: values copied from a datasheet,
values that describe the simulation, and values calibrated against
measurements. The USDA tab authors one of each kind on a prim; the USD Python
tab authors the same prim with ``usd-core``:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/radar_wpm_dmat_howto_choose_parameters_1.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1]
         :end-before: # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1-python]
         :end-before: # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1-python]
         :dedent:

This page is about which of the three kinds a value belongs to. The meaning,
units and relations of each attribute are on :doc:`../attributes`; the types,
defaults and allowed tokens are in the generated
:doc:`../../../reference/schemas`.

.. _sensors-nonvisual-radar-howto-choose-parameters-one-operating-mode:
.. _sensors-radar-one-operating-mode:

Stay inside one operating mode
------------------------------

Use values from one published operating mode per scan configuration. Do not
combine maximum range, field of view, resolution or waveform values from
different modes. Use :doc:`multiple scans <scan_configurations>` when the
device interleaves modes, such as near/far or wide/narrow scans.

.. _sensors-nonvisual-radar-howto-choose-parameters-datasheet-table:

Map the datasheet onto attributes
---------------------------------

The table maps specifications from datasheets, manuals, integration guides
and antenna files to radar attributes:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 26 32 42

   * - Real-sensor information
     - Radar attributes
     - Mapping guidance
   * - Frame, cycle or scan rate
     - ``omni:sensor:frameRate``
     - Author the complete output-frame rate as the rational pair
       ``(numerator, denominator)``; ``(10, 1)`` is ten complete scans per
       second. Refer to :ref:`the frame rate
       <sensors-nonvisual-radar-attributes-frame-rate>`.
   * - Scan modes
     - Scan configuration instances
     - Use one instance per published scan mode, and give a scan the device
       acquires later in its cycle its delay in ``timeOffsetUsec`` (:ref:`the
       frame rate <sensors-nonvisual-radar-attributes-frame-rate>`); refer to
       :doc:`scan_configurations`.
   * - Carrier frequency or wavelength
     - ``waveLengthMm``
     - Author the wavelength in millimeters, converting a published carrier
       frequency with λ = c / f (77 GHz gives ``3.8934085``). It is the one
       wavelength of the sensor, for every scan and both processing modes;
       refer to :ref:`the wavelength
       <sensors-nonvisual-radar-attributes-wavelength>`.
   * - Maximum range and field of view
     - ``maxRangeM``, ``maxAzAngDeg``, ``maxElAngDeg``
     - ``maxRangeM`` is the unambiguous range in meters. The angular attributes
       are positive half-angles; the total symmetric field of view is twice
       each value (see the warning below).
   * - Range, velocity and angular resolution
     - ``rangeResM``, ``velResMps``, ``boreAzResDeg``, ``boreElResDeg``
     - These configure separation and bin resolution in ``FAST`` mode with
       ``binsFromSpec`` true; they are not accuracy values.
   * - Explicit bin counts
     - ``rBins``, ``vBins``, ``azBins``, ``elBins``
     - Read in ``FAST`` mode when ``binsFromSpec`` is false, for a vendor that
       publishes the detection-matrix dimensions rather than resolutions.
   * - Unambiguous velocity sequence
     - ``maxVelMpsSequence``
     - Preserve the documented sequence when the limit varies across frames or
       chirp groups; only a ``FAST`` scan folds radial velocity by the active
       entry. How the active entry advances with several scans is under
       :ref:`the velocity cycle
       <sensors-nonvisual-radar-attributes-velocity-cycle>`.
   * - Range or angular ambiguity
     - ``enableRangeAliasing``, ``enAngAliasing``
     - Enable only when the real operating mode folds ambiguous detections into
       its unambiguous interval; with both false, contributions outside the
       interval are discarded. Refer to :ref:`aliasing
       <sensors-nonvisual-radar-attributes-aliasing>`.
   * - Waveform timing and sampling
     - ``chirpDuration``, ``chirpBandwidth``, ``chirpRepetitionTimeSequence``,
       ``slowTimeSamples``, ``fastTimeSamples``, the padding and window
       attributes
     - Use the values of the selected waveform mode when the profile is modeled
       in ``WAVEFORM`` mode or a vendor mode is specified by waveform timing.
       Check derived values against the published range and velocity behavior.
   * - Antenna pattern or array geometry
     - Tx and Rx custom gain arrays, or patch-array and aperture attributes
     - Prefer measured gain grids and documented element spacing, steering and
       windowing over the defaults, which are only an approximation; refer to
       :ref:`antenna data <sensors-nonvisual-radar-howto-choose-parameters-antenna-data>`.
   * - Detection processing
     - ``cfarMode`` and the per-scan CFAR attributes
     - Map these only when the vendor publishes the processing dimensions,
       guard and test cells and threshold behavior; refer to :ref:`cfarMode
       <sensors-nonvisual-radar-attributes-cfar-mode-scope>`.

.. _sensors-nonvisual-radar-howto-choose-parameters-half-angles:

Half-angles
^^^^^^^^^^^

.. warning::

   The angular limits are half-angles: a 150 degree field of view is authored
   as ``75``, not ``150`` (:ref:`the half-angles
   <sensors-nonvisual-radar-attributes-half-angles>` on the attributes page).
   Authoring the total doubles the coverage; :ref:`Verification <sensors-nonvisual-radar-howto-choose-parameters-reach-the-model>` shows how
   to catch the mistake.

.. _sensors-nonvisual-radar-howto-choose-parameters-resolution-not-accuracy:

Resolution and measurement noise
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``rangeResM``, ``velResMps``, ``boreAzResDeg`` and ``boreElResDeg`` control detection-matrix bin sizes. They affect separation and quantization;
the noise attributes add measurement noise independently. When the four are read, and why angular separation also
needs ``cfarMode`` ``4D``, is :ref:`resolution and accuracy
<sensors-nonvisual-radar-attributes-resolution-vs-accuracy>` on the attributes
page.

.. _sensors-nonvisual-radar-howto-choose-parameters-calibration:

Calibration and simulation parameters
-------------------------------------

The following settings require calibration or control simulation cost:

- Tune ``raysPerDeg`` for stable geometric coverage at an acceptable frame time
  (:ref:`raysPerDeg <sensors-nonvisual-radar-attributes-sampling>`).
- Increase ``traceTreeDepth`` only when indirect paths are required by the
  validation scenario.
- Calibrate ``powerFactor`` and ``rcsTuningCoefficients`` against measured return
  strength or detection probability.
- Set the measurement-noise and CFAR-noise attributes from error distributions
  or recordings, not from resolution alone.
- Enable range or angular aliasing only when the real operating mode exhibits
  the corresponding ambiguity.
- When measured antenna data is unavailable, treat the analytic antenna modes
  and array geometry as an approximation and validate sensitivity across the
  field of view.

.. _sensors-nonvisual-radar-howto-choose-parameters-antenna-data:

Pick ``txAntennaGainMode``
and ``rxAntennaGainMode`` from what the vendor gives you: a measured gain grid
is authored as ``CUSTOM``, documented element geometry (element counts,
spacings, steering angles and windows) as ``PATCH_ARRAY_MODEL``, and
``CONSTANT`` or ``COSINE_FALLOFF`` (the default) stand in as analytic
approximations when you have neither; the four modes are :ref:`the antenna
<sensors-nonvisual-radar-attributes-antenna>`. Author the element and aperture
geometry whenever you select ``PATCH_ARRAY_MODEL`` or ``WAVEFORM`` processing,
because the geometry defaults are placeholders rather than a working array
(:ref:`the array defaults <sensors-nonvisual-radar-attributes-array-defaults>`).
Give a ``CUSTOM`` grid exactly ``len(ElDeg) × len(AzDeg)`` values per gain
array, in elevation-major order; the layout and the size rules are :ref:`the
gain grid <sensors-nonvisual-radar-attributes-gain-grid>`.

.. _sensors-nonvisual-radar-howto-choose-parameters-mode-split:

Processing-mode controls
------------------------

``datacubeMode`` selects ``FAST`` detection-matrix approximation or
``WAVEFORM`` sampled-waveform processing. ``FAST`` uses bin and resolution
controls; ``WAVEFORM`` uses waveform, sampling, padding, window and aperture
controls. See :ref:`processing-mode controls
<sensors-nonvisual-radar-attributes-mode-split>` for shared attributes,
antenna-mode conditions and CFAR behavior.

The example configures a 77 GHz ``WAVEFORM`` scan with an 85 × 14 receiving
aperture and otherwise uses schema defaults. It illustrates the controls;
it is not a calibrated device profile. Aperture attributes
:ref:`default to zero <sensors-nonvisual-radar-attributes-array-defaults>`
and must be supplied. Each :ref:`padding length
<sensors-nonvisual-radar-attributes-padding>` must be at least the corresponding
sample or element count. The Python tab authors the same settings on the
``radar`` prim defined above:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/radar_wpm_dmat_howto_choose_parameters_2.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2]
         :end-before: # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2-python]
         :end-before: # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2-python]
         :dedent:

.. _sensors-nonvisual-radar-howto-choose-parameters-reach-the-model:

Verification
------------

Compare the active configuration with the authored values. Request a radar
``PointCloud`` and inspect a returned frame, including one with
``Counts[0] == 0``. Its
:ref:`scan parameters <sensors-nonvisual-radar-outputs-scan-params>` report
``maxRangeM``, ``minVelMps``, ``maxVelMps``, ``minAzRad``, ``maxAzRad``,
``minElRad`` and ``maxElRad``.

Author ``maxAzAngDeg = 75`` on the scan and ``minAzRad`` and ``maxAzRad`` must
come back as -1.309 and 1.309, ±75 degrees in radians (the limit params are
radians while spherical ``Coordinates`` are degrees; refer to :ref:`angle
units <sensors-nonvisual-radar-outputs-angle-units>`). If they still report the
schema default, ±1.152 for the default half-angle of 66 degrees, check this
attribute's name, scan-instance segment and effective value. An unchanged
value does not show whether other attributes were applied. See :ref:`the naming pattern
<sensors-nonvisual-radar-howto-scan-configurations-naming>`. The check also
catches the half-angle mistake: a datasheet's 150 degree total field of view
authored directly gives ±2.618, ±150 degrees in radians.

Wait for a radar frame before checking the scan parameters. A scan that
detects no targets still publishes its metadata with ``Counts[0] == 0``;
steps without a radar firing return no radar frame. A zero timestamp is
valid for a scan at time zero; see :ref:`scan parameters
<sensors-nonvisual-radar-outputs-scan-params>`.

Detection counts can vary between frames. A count change does not establish
that a parameter edit took effect; use :ref:`multi-frame comparisons
<sensors-nonvisual-radar-howto-validate-parameterization-distributions>`.
Then validate the measurements using :doc:`validate_parameterization`.

Potential issues
----------------

- The field of view is twice as wide as the datasheet says: a total angle was
  authored into a half-angle attribute. Refer to :ref:`half-angles <sensors-nonvisual-radar-howto-choose-parameters-half-angles>`.
- Tightening ``rangeResM`` or ``velResMps`` does not make the measurements
  noisier: the resolution attributes set what a scan can separate, not its
  error. Refer to :ref:`Resolution and measurement noise <sensors-nonvisual-radar-howto-choose-parameters-resolution-not-accuracy>`.
- Raising ``raysPerDeg`` costs frame time but does not sharpen angular
  resolution: it controls geometric sampling density, not angular resolution
  (:ref:`raysPerDeg <sensors-nonvisual-radar-attributes-sampling>`).
- Waveform or bin values have no effect: they belong to the
  other ``datacubeMode``. Refer to :ref:`the mode split
  <sensors-nonvisual-radar-attributes-mode-split>`.
- Targets appear at a plausible but wrong range or angle: range or angular
  aliasing is enabled for a mode that has no such ambiguity, so out-of-interval
  contributions are kept rather than discarded, and a ``FAST`` scan folds them
  into the interval. Refer to :ref:`aliasing
  <sensors-nonvisual-radar-attributes-aliasing>`.
- Targets appear at a plausible but wrong radial velocity: their radial speed
  exceeds the scan's unambiguous velocity, the active ``maxVelMpsSequence``
  entry for a ``FAST`` scan or the bound the waveform timing sets for a
  ``WAVEFORM`` scan, and radial velocity has no aliasing switch to turn off
  (:ref:`aliasing <sensors-nonvisual-radar-attributes-aliasing>`).
- Two targets at the same range and radial velocity come back as one detection,
  whatever the angular resolution: the scan is ``FAST`` and ``cfarMode`` is
  ``2D``, which keeps at most one detection per range-velocity cell. Refer to
  :ref:`cfarMode <sensors-nonvisual-radar-attributes-cfar-mode-scope>`.
- RCS is systematically off across the whole scene: calibrate ``powerFactor``
  and ``rcsTuningCoefficients`` against measured return strength, not a
  geometric parameter. Refer to :ref:`check 4 of Validate a
  Parameterization <sensors-nonvisual-radar-howto-validate-parameterization-materials>`.
- One scan does not use the expected settings: the second scan is at schema
  defaults because its attributes were never authored, or were authored without
  its instance segment. Refer to :ref:`the naming pattern
  <sensors-nonvisual-radar-howto-scan-configurations-naming>`.

Related
-------

- :doc:`Run More Than One Scan Pattern <scan_configurations>` — one scan configuration per published operating mode, the attribute naming pattern and reading back which scan produced a frame.
- :doc:`Validate a Parameterization <validate_parameterization>` — validation scenarios and multi-frame comparisons.
- :doc:`Build a Profile from a Spec Sheet <spec_sheet_profile>` — the end-to-end procedure from a vendor's published specification to a sensor prim.
- :doc:`Outputs <../outputs>` — the ``PointCloud`` channels and params, including the scan limits configuration verification reads back.
- :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>` — the non-visual material labels and how to author them.
