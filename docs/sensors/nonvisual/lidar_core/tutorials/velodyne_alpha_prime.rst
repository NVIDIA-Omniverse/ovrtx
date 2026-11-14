.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-recipes-lidar-velodyne-alpha-prime:

Parameterize a Rotary Lidar: Velodyne Alpha Prime
=================================================

A sensor profile combines published specifications, derived values,
approximations and parameters that need calibration. This tutorial distinguishes
those sources while configuring a 128-channel Velodyne Alpha Prime (VLS-128)
with the Lidar generic core model.

The completed layer is available as
:download:`Velodyne_Alpha_Prime_Rev4.usda <assets/Velodyne_Alpha_Prime_Rev4.usda>`.
It contains the full per-emitter arrays and an ``OmniLidar`` with
``OmniSensorGenericLidarCoreAPI``. The sections below derive its values and
show how to reference it into a scene.

.. _sensors-recipes-alpha-prime-vanilla-baseline:

The USD layer is a documentation-derived starting profile, not a certified
model of a particular hardware unit. It contains what can be copied or
reasonably inferred from the public manuals. Emitter and detector behavior that
those sources do not define — including unit-specific optical power, receiver
response and thresholds, noise, corrections, and intensity transfer — remains
generic or approximate and must be tuned against measured sensor data for
higher-fidelity use.

See :doc:`../index` for the model's capabilities.

Source documents
----------------

This recipe uses these exact manufacturer documents:

* `Alpha Prime Rev. 4 User Manual <https://data.ouster.io/downloads/velodyne/user-manual/alpha-prime-rev4-user-manual.pdf>`_,
  document 63-9483 Rev. 2, last updated February 14, 2019. The title inside the PDF
  is *VLS-128 User Manual*.
* `Alpha Prime Datasheet <https://data.ouster.io/downloads/datasheets/velodyne/63-9679_Rev-B_DATASHEET_ALPHA-PRIME_web.pdf>`_,
  document 63-9679 Rev-B, published in 2021.

The manual's Appendix A explicitly moves product specifications to the separate
datasheet. The two files therefore form one source set: the manual defines packet
layout, firing order, timing, coordinates, return behavior, and nominal channel
angles; the datasheet supplies range, accuracy, field of view, frame-rate,
detection, optical, electrical, and environmental specifications.

When the revisions differ, this recipe uses the newer datasheet for product-level
specifications and the manual for detailed VLS-128 operation. The one material
conflict is wavelength: the manual describes 903 nm channels while the newer
datasheet specifies approximately 905 nm. The profile uses 905 nm and records the
difference so a profile for older hardware can use 903 nm instead.

The public ROS VLS-128 calibration file was examined only as an implementation
cross-check. Its nominal angles match Figure 9-8 in the manual, and its additional
distance, focal, and origin corrections are zero. It is not a manufacturer
specification, does not provide per-unit factory calibration, and is not used as the
source for this profile.

.. _sensors-recipes-source-confidence:

Source confidence
-----------------

Each mapping identifies whether its value is directly sourced, calculated,
approximated or requires calibration:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 20 35 45

   * - Category
     - Meaning
     - How to use it
   * - Direct
     - The source value and simulation attribute have the same physical meaning and
       units.
     - Copy the value, then verify units, coordinate conventions, and array order.
   * - Derived
     - The source contains enough information to calculate the simulation value
       uniquely.
     - Keep the equation and source assumptions next to the result.
   * - Approximation
     - A published claim exists, but the simulator uses a different statistical or
       physical model.
     - Use the published value as an initial condition, then validate and tune
       against measurements.
   * - Calibration
     - The public sources do not define the value, or a particular hardware unit can
       differ.
     - Start from a documented model default and replace it with measured or
       unit-specific data.

Read the product-level specifications
-------------------------------------

The datasheet's sensor and laser specification table, on page 2 of 63-9679 Rev-B,
is the product-level envelope this profile copies: 128 channels, a 300 to 1200 RPM
motor range, a 360-degree horizontal by 40-degree vertical field of view spanning
-25 to +15 degrees, measurement range up to 300 m, ±3 cm typical range accuracy,
detection of a 10% NIST target out to 300 m and of a 5% target at 180 m, 4 mm
distance-field granularity, one or two returns, and an emitter wavelength of
approximately 905 nm.

.. figure:: ../../../../img/sensors/lidar/alpha_prime_datasheet_sensor_specs.avif
   :alt: Alpha Prime Rev-B datasheet sensor and laser specification rows
   :width: 100%

   Excerpt from the Alpha Prime datasheet, 63-9679 Rev-B, page 2.

The following mapping combines these specifications with the manual's
operating details.

Bare attribute names in the table are in the ``omni:sensor:Core:`` namespace on the
sensor prim. ``omni:sensor:frameRate`` sits one level up, in the namespace every
sensor model shares; refer to :ref:`the two namespaces
<sensors-ref-attributes-namespaces>` for why the distinction matters.

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 23 24 20 13 20

   * - Manufacturer information
     - Attribute or action
     - Value in this profile
     - Category
     - Notes
   * - 128 channels
     - ``numberOfEmitters``, ``numberOfChannels``
     - ``128``, ``128``
     - Direct
     - One nominal emitter maps to one detector channel.
   * - Rotating VLS-128 architecture
     - ``scanType``, ``rotationDirection``
     - ``ROTARY``, ``CW``
     - Direct
     - The manual's azimuth increases clockwise from its zero axis.
   * - 600 RPM selected from the 300-1200 RPM range
     - ``omni:sensor:frameRate``
     - ``(10, 1)``
     - Derived
     - Complete scans per second equal RPM divided by 60.
   * - 53.3 us average firing sequence at 600 RPM
     - ``rotPatternFiringResDeg``
     - ``0.19188``
     - Derived
     - Matches Table 8-1 in the manual.
   * - 360-degree horizontal field of view
     - ``validStartAzimuthDeg``, ``validEndAzimuthDeg``
     - ``0.0``, ``360.0``
     - Direct
     - Runtime field-of-view clipping can narrow this interval.
   * - 40-degree vertical field of view, -25 to +15 degrees
     - ``emitterState:s001:elevationDeg``
     - 128-value non-linear array
     - Direct
     - Use Figure 9-8 rather than a uniformly spaced approximation.
   * - Per-laser ``AziOffset`` values
     - ``emitterState:s001:azimuthDeg``
     - Eight offsets repeated for 16 firing groups
     - Direct
     - Preserve the signs after aligning the coordinate frames.
   * - Groups of eight every 2.665 us, with maintenance periods
     - ``emitterState:s001:fireTimeNs``
     - 128 derived offsets
     - Derived
     - Packet timestamp adjustment is not part of this array.
   * - 4 mm distance-field granularity
     - ``rangeResolutionM``
     - ``0.004``
     - Direct
     - This is packet/reporting resolution, not the accuracy distribution.
   * - Measurement range up to 300 m
     - ``farRangeM``
     - ``300.0``
     - Direct
     - Datasheet footnote says configuration dependent.
   * - Typical range accuracy of ±3 cm
     - ``rangeAccuracyM``
     - ``0.03``
     - Approximation
     - The model uses a distance-dependent Gaussian error scale, not a guaranteed
       bound.
   * - Detection at 180 m on a 5% NIST target
     - Validation target
     - 5% at 180 m
     - Approximation
     - Retain this published point as a secondary validation check.
   * - Detection up to 300 m on a 10% NIST target
     - ``minReflectance``, ``minReflectionRangeM``
     - ``0.10``, ``300.0``
     - Direct anchor
     - Use the farthest published detection point for the model's single threshold
       anchor.
   * - One or two returns
     - ``maxReturns``
     - ``2``
     - Direct
     - Strongest/last selection policy is separate from return capacity.
   * - Dual returns recorded for surfaces at least 1 m apart
     - ``minDistBetweenEchosM``
     - ``1.0``
     - Direct
     - From the manual's dual-return behavior.
   * - Horizontal and vertical beam divergence
     - ``divergenceHorDeg``, ``divergenceVerDeg``
     - ``0.1197482``, ``0.06016057``
     - Direct
     - Values are published in both mrad and degrees.
   * - Approximately 905 nm in the newer datasheet
     - ``waveLengthNm``
     - ``905.0``
     - Direct, revision-specific
     - Use 903 nm when targeting the older manual/hardware definition.
   * - Calibrated reflectivity byte from 0 to 255
     - ``intensityScalePercent`` and intensity mapping
     - ``255.0`` retained from the model default
     - Calibration
     - With linear mapping, this produces 0–2.55. Matching the device's
       0–255 encoding requires calibrated scaling and a transfer curve.
   * - Data origin 66.11 mm above the sensor base
     - ``emitterState:s001:vertOffsetM``
     - 128 values of ``0.06611``
     - Direct
     - Places every emitter origin relative to a sensor prim located at the
       mechanical base.

Build the profile
-----------------

Start with an ``OmniLidar`` prim and apply the generic core API. The model metadata
selects the configurable generic lidar model; ``marketName`` identifies this
parameterization rather than a different model.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_1.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1-python]
         :dedent:

The identification attributes select the model; ``frameRate`` sets scans
per second. See :doc:`../attributes` for their definitions and
:ref:`model identity <sensors-ref-model-identity-vs-plugin>` for the distinction
between schema and implementation names used during validation.

Choose a rotation rate
~~~~~~~~~~~~~~~~~~~~~~

The manual permits 300 through 1200 RPM in increments of 60 RPM. For a rotary
sensor:

.. code-block:: text

   frame_rate_hz = rpm / 60
   angular_step_deg = 360 * frame_rate_hz * 53.3e-6

At 600 RPM, ``frame_rate_hz`` is 10 and the average angular advance during one
53.3 us firing sequence is 0.19188 degrees. The same derivation gives the manual's
operating points:

.. _sensors-recipes-alpha-prime-rpm-coupling:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 25 25 50

   * - Motor speed
     - Frame rate
     - ``rotPatternFiringResDeg``
   * - 300 RPM
     - 5 Hz
     - 0.09594 degrees
   * - 600 RPM
     - 10 Hz
     - 0.19188 degrees
   * - 900 RPM
     - 15 Hz
     - 0.28782 degrees
   * - 1200 RPM
     - 20 Hz
     - 0.38376 degrees

When changing RPM, update both ``frameRate`` and ``rotPatternFiringResDeg``
using the table. Updating only ``frameRate`` changes the firing rate and no
longer represents the device.

At 10 Hz, ``q = 360 / 0.19188 = 1876.1726`` firing-pattern ticks per modeled
rotation. The model carries the absolute fractional firing phase across rotations,
so a completed rotation contains either 1876 or 1877 ticks as that phase crosses an
integer boundary. This preserves the long-run rate of 18,761.726 ticks per second
and ``q * 10 * 128``, about 2,401,500.9, candidate single-return measurements per
second. The datasheet's approximately 2.3 million figure is a rounded product-output
claim; valid output points can also be reduced by range, field-of-view, reflectance,
and scene misses.

Allow for varying tick counts when allocating per-rotation buffers; see
:ref:`fractional ticks <sensors-lidar-fractional-ticks>`.

Align the coordinate frames
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Figure 9-1 in the manual defines zero azimuth along the sensor's +Y axis and
increases azimuth clockwise toward +X. The model's unshifted zero direction is +X,
so the profile uses:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_2.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2-python]
         :dedent:

After this frame alignment, copy the manual's ``AziOffset`` signs directly into
``emitterState:s001:azimuthDeg``. For example, the manual's laser ID 0 remains
``-6.354`` degrees and laser ID 7 remains ``+6.354`` degrees. Do not negate the
table merely because Cartesian rendering uses a right-handed frame; the model
performs that conversion after applying ``startAzimuthOffsetDeg``.

Map the channel pattern
~~~~~~~~~~~~~~~~~~~~~~~

The 40-degree vertical field of view is not uniformly distributed. Figure 9-8 in the
manual, on page 65, is a table of the nominal azimuth offset and elevation of every
one of the 128 lasers: its elevation column spans -25 to +15 degrees non-uniformly,
and its azimuth column repeats one group of eight offsets across the 16 firing
groups.

.. figure:: ../../../../img/sensors/lidar/alpha_prime_manual_channel_angles.avif
   :alt: VLS-128 nominal azimuth offset and elevation table for all 128 lasers
   :width: 100%

   Figure 9-8 from the exact Alpha Prime/VLS-128 user manual, page 65.

The resulting azimuth and elevation arrays each contain 128 values. Elevation spans
-25 to +15 degrees, and the first azimuth group is
``[-6.354, -4.548, -2.732, -0.911, 0.911, 2.732, 4.548, 6.354]``.

The user manual uses zero-based channel IDs ``0`` through ``127``, while this
profile authors one-based ``channelId`` values ``1`` through ``128``, the numbering
of the schema's default emitter state. Manual channel ID ``n`` is therefore
authored as ``channelId`` ``n + 1``, and because the model reports the authored
value unchanged, ``PointCloud`` ``ChannelId`` ``n + 1`` is manual channel ID and
figure laser ID ``n``. Channel ids are labels to the model, so authoring the
manual's own ``0`` through ``127`` would be accepted as well and would make
``ChannelId`` match the manual directly. Keep the one-based numbering if anything
downstream indexes per-channel data by the id minus one. Refer to
:ref:`channel ids <sensors-lidar-channel-ids>`.

All emitters use ``rangeId = 0``, which selects the single 0.3-300 m range region
authored by the profile. The arrays themselves, their required lengths and the rest
of the per-emitter corrections are in :doc:`../howto/firing_pattern`.

Derive the firing times
~~~~~~~~~~~~~~~~~~~~~~~

Figure 9-5 on page 63 defines a 53.3 us firing sequence. The
128 lasers fire in groups of eight, one group every 2.665 us, with maintenance
periods interrupting the sequence, one of them before laser IDs 64 to 71 and one
after the last group.

.. figure:: ../../../../img/sensors/lidar/alpha_prime_manual_firing_timing.avif
   :alt: VLS-128 firing groups and maintenance periods over one 53.3 microsecond sequence
   :width: 100%

   Figure 9-5 from the exact Alpha Prime/VLS-128 user manual, page 63.

For the zero-based laser ID ``i`` used by Figure 9-5, integer division gives the
firing group:

.. code-block:: text

   firing_group_index = (i // 8) + (i // 64)
   fire_time_ns = 2665 * firing_group_index

The ``i // 64`` term inserts the first 2.665 us maintenance interval before laser IDs
and manual channel IDs 64-71. The resulting ``fireTimeNs`` values run from 0 through
42,640 ns. The 53.3 us tick period includes the remaining maintenance time after the
last group.

The manual's ``-8.7 us`` adjustment aligns a data point with the top-of-hour
timestamp stored in a physical UDP packet. It is not added to ``fireTimeNs``,
because the simulation array stores a non-negative delta from the model's
firing-pattern tick. Apply packet timestamp conventions in an encoder or downstream
packet comparison, not by making the emitter times negative.

Configure range and returns
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The profile sets range limits, return capacity and detection calibration as follows:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_3.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3-python]
         :dedent:

``farRangeM``, ``rangeResolutionM``, ``maxReturns``, and ``minDistBetweenEchosM``
map directly to published behavior. ``nearRangeM`` does not: neither source
publishes a minimum range, so 0.3 m is the model's initial value and must be checked
against hardware. It is a validity limit like the far one, so a surface inside it is
as absent from the point cloud as one beyond 300 m — refer to
:ref:`the range window <sensors-lidar-range-window>`. In this profile, though, the
0.3 m limit never takes effect: the model also drops a firing's first return when it
lies nearer than the minimum separation between echoes, ``minDistBetweenEchosM``, so
with the 1.0 m authored above and the profile's ``IDEALIZED`` rays nothing nearer
than about 1 m is reported.

The 4 mm value is the resolution of the physical packet's integer distance field. It
is available to packet encoders, but raw point-cloud coordinates are not necessarily
quantized to 4 mm. Do not use it as a quantization requirement for the internal
floating-point point-cloud output, and do not reach for it to make a scan noisier:
:ref:`range accuracy and range resolution are different things
<sensors-ref-range-accuracy-vs-resolution>`.

The datasheet's ±3 cm claim is typical wall-test accuracy across most channels and
varies with range, temperature, and reflectivity. ``rangeAccuracyM`` controls a
distance-dependent Gaussian uncertainty, so ``0.03`` is an initial approximation,
not an exact translation of a hard bound.

The model supports one reflectance/range calibration point. This profile
uses 10% at 300 m and retains 5% at 180 m as an independent validation target.
Matching either point does not guarantee the other; results depend on
intensity processing and radiometry. See
:ref:`detection thresholds <sensors-intensity-point-drops>`.

Configure beam and intensity behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table F-1 in the manual, on page 117, publishes both beam-divergence axes, in
milliradians and in degrees.

.. figure:: ../../../../img/sensors/lidar/alpha_prime_manual_beam_divergence.avif
   :alt: VLS-128 horizontal and vertical beam-divergence values
   :width: 90%

   Table F-1 from the exact Alpha Prime/VLS-128 user manual, page 117.

The degree values are the ones copied here: 0.1197482 horizontally and
0.06016057 vertically.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_4.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4-python]
         :dedent:

The divergence values participate in radiometric threshold and intensity
calculations even with the default, single-ray ``IDEALIZED`` type. Both divergence angles are nonzero, so the model retains them rather than
deriving them from beam waist. See :ref:`waist and divergence
<sensors-intensity-divergence-or-waist>`.

The manual depicts the real spot as a rectangular pattern made of three bands, which
none of the available idealized, Gaussian, or uniform representations reproduces
exactly. Start with ``IDEALIZED``. ``GAUSSIAN_BEAM`` traces multiple rays to
represent a geometric footprint, has a substantial performance cost, and should be
enabled only when higher-fidelity footprint and partial-hit behavior is required and
validated against measurements.

The manual describes distance- and power-independent reflectivity, with
diffuse targets in the lower part of the 0–255 range and retroreflectors in
the upper part. The profile uses ``NORMALIZATION`` and retains the model's
default scale of 255. With linear mapping this reports 0–2.55, so it does
not reproduce the device encoding. The starting settings are:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_5.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5-python]
         :dedent:

``NORMALIZATION`` approximates range-independent reflectivity. Matching
Velodyne's 0–255 encoding, proprietary calibration curve and diffuse/
retroreflector transition requires measured data and calibrated mapping.
Use ``CORRECTION`` only when calibration data shows that its
range-dependent correction better represents the target sensor. ``peakPowerW``,
``pulseTimeNs``, detector properties, and multi-return power fractions are not
published in these documents. The profile retains the model's generic starting values
for the required radiometric calculation and labels them as calibration inputs; what
each of them does is in :doc:`../howto/intensity`.

Parameter mapping and calibration
----------------------------------

Direct and derived parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The product-mapping table identifies the directly sourced and derived values:
scan geometry, RPM and firing schedule, channel identities, range and return
specifications, optical geometry and the data-origin offset. Preserve their
source conventions when applying unit-specific calibration.

Approximated parameters
~~~~~~~~~~~~~~~~~~~~~~~

These values are available, but the model cannot represent the claim exactly with one
attribute:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 28 32 40

   * - Published behavior
     - Model limitation
     - Recommended treatment
   * - Detection at 5%/180 m and 10%/300 m
     - One ``minReflectance``/``minReflectionRangeM`` anchor
     - Use 10%/300 m as the profile anchor to preserve the published far-range
       detection point, and keep 5%/180 m as a validation point.
   * - Typical ±3 cm accuracy
     - ``rangeAccuracyM`` is a distance-dependent Gaussian scale
     - Start at 0.03 m and fit the simulated residual distribution to wall-test data
       by distance, channel, reflectivity, and temperature.
   * - Three-band rectangular laser spot
     - Available ray types are idealized, Gaussian, or uniform
     - Start with ``IDEALIZED`` and use ``GAUSSIAN_BEAM`` only when higher-fidelity
       footprint behavior is needed and its performance cost is acceptable.
   * - Calibrated 0-255 reflectivity with diffuse/retro ranges
     - A linear mapping does not reproduce the proprietary transfer function
     - Fit encoding/decoding curves from NIST reflectance panels and retroreflectors
       at multiple ranges.
   * - Strongest, last, and dual return modes
     - ``maxReturns`` sets capacity but does not by itself reproduce every firmware
       selection rule
     - If two returns do not expose enough candidates for the desired selection,
       increase ``maxReturns`` and select strongest, last, or dual returns in
       post-processing.

Parameters requiring calibration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These model inputs cannot be recovered from the two public PDFs:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 30 30 40

   * - Attribute or behavior
     - Why the source is insufficient
     - Useful calibration experiment
   * - ``nearRangeM`` and any near-field blind zone
     - Only maximum/detection ranges are published
     - Move a diffuse target through the near field and record first reliable
       detection by channel.
   * - ``peakPowerW``, ``pulseTimeNs``, ``focusDistM``, ``Msquared``, and beam waist
     - Laser class, wavelength, and divergence do not uniquely determine these values
     - Use optical characterization if available; otherwise fit intensity and
       close-echo behavior without claiming physical laser power.
   * - Detector aperture, quantum efficiency, pixel pitch, bit depth, and calibration
       gain
     - No detector transfer characteristics are published
     - Fit returned intensity against calibrated reflectance targets over range and
       incidence angle.
   * - Angular noise distributions
     - Nominal angles are published, but random and temperature-dependent error are
       not
     - Fit per-channel angular residuals from large planar targets. Keep synthetic
       jitter at zero until measured.
   * - Per-unit angle, origin, and distance corrections
     - Figure 9-8 is a nominal model table, not a serial-number calibration
     - Import unit-specific calibration when available or estimate channel residuals
       from a controlled target survey.
   * - Reflection/transmission power split for multiple returns
     - The manual describes causes and selection rules, not an energy split
     - Use layered vegetation, mesh, glass, and partial-occlusion targets and compare
       echo intensity/order.
   * - Full intensity encoding curve
     - The diffuse and retroreflector ranges are described, but no transfer curve is
       published
     - Capture 0-100% NIST targets plus retroreflectors at several distances and fit
       a non-linear mapping.
   * - Interference mitigation and adverse-weather detection probability
     - Product capability is stated without an exposed algorithm or probability model
     - Treat interference and atmospheric models as separate validated effects using
       controlled multi-sensor and weather data.

Unmodeled device properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Power consumption, supply voltage, weight, enclosure dimensions, IP67 protection,
operating/storage temperature, Ethernet packet transport, GPS/NMEA input, and
proprietary sensor-to-sensor interference mitigation are useful integration
requirements but do not map to any attribute of the generic lidar model.

Represent physical dimensions in mounting, visual, and collision assets. This profile
represents the 66.11 mm data-origin offset with the emitters' ``vertOffsetM`` values;
do not apply the same offset again in the mounting transform. Represent environment,
networking, synchronization, and power behavior in their corresponding simulation
systems rather than inventing lidar parameters.

Use the profile in a scene
--------------------------

Save the finished layer beside the scene that will use it, and reference its default
prim instead of copying its attributes into every scenario. For example, a parent
scene can include and position the sensor as follows:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_core_tutorials_velodyne_alpha_prime_6.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6-python]
         :dedent:

A profile layer usually carries its RenderProduct and RenderVars as well as the
sensor prim. This one requests ``PointCloud``; trim its ``channels`` to the ones
you need. :doc:`../../../common/output_configuration` covers how the
sensor prim and its RenderProduct fit together, and :doc:`../outputs` lists
what can be asked for.

Place the referenced prim at the real sensor's mechanical base. The profile's emitter
origins are offset by 0.06611 m along the sensor's +Z axis to represent the published
data origin.

For moving sensors or moving targets, enable the renderer's motion BVH and choose the
required output motion-compensation state. They are two separate settings and setting
one does not set the other: :doc:`../howto/motion_artifacts` covers the pairing.

Validate the profile
--------------------

Parameter validation
~~~~~~~~~~~~~~~~~~~~

Install the introspection package as described in
:doc:`Sensor Definition Validation <../../../common/validation>`.

Run both parameter and scheduler validation as described in
:doc:`Sensor Definition Validation <../../../common/validation>`, using
``/Velodyne_Alpha_Prime_Rev4`` in the downloaded layer. Parameter acceptance
alone does not establish that the scan schedule is valid.

``ModelInfo`` selects the generic lidar introspection implementation; it does not
replace the product metadata authored in the USD layer. Note that it names the
implementation in the implementation's own spelling — ``lidar.core``, vendor ``nv`` —
rather than in the schema's ``LidarCore`` and ``NVIDIA``, which is expected and is
described in :ref:`model identity <sensors-ref-model-identity-vs-plugin>`.

``validateParams`` checks attribute types and that the arrays agree: every non-empty
emitter-state array against ``numberOfEmitters``, the range regions and every
``rangeId`` against ``rangeCount``, every ``bank`` against ``numLines`` (and, for a
solid-state sensor, the length of ``numRaysPerLine`` against ``numLines`` and the sum
of its entries against ``numberOfEmitters``), the number of distinct channel ids
against ``numberOfChannels``, and the fire times, which must never decrease and must
fit inside one firing period (one tick for a rotary sensor, one frame for a
solid-state one). It also rejects a positive frame rate below 0.466 Hz; refer to
:ref:`the minimum scan rate <sensors-lidar-min-scan-rate>`. Called without a prim,
as here, ``getSchedulerInfo`` does not re-check the firing pattern; given a prim, it
validates that prim first. It reports the scheduling the profile resolves to: frame
rate, start time, capture duration, frame limit and whether outputs are partial. Its
``errorString`` is set if validation failed or one of the attributes it reads is
missing.

Geometry and timing checks
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use a simple scene before a vehicle-scale environment:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 24 38 38

   * - Check
     - Test setup
     - Expected result
   * - Coordinate orientation
     - Put narrow targets on +Y and +X and inspect the first scan sector
     - Tick zero is centered on +Y and the scan proceeds clockwise toward +X.
   * - Channel pattern
     - Put a large vertical wall around the sensor and plot elevation by
       ``ChannelId``
     - ``PointCloud`` ``ChannelId`` *n* + 1 is manual channel ID and Figure 9-8
       laser ID *n*, for *n* from 0 to 127, and the channels span -25 to +15
       degrees non-linearly.
   * - Full rotation rate
     - Run with a stable simulation clock for several seconds
     - Ten complete rotations per second at the selected 600 RPM configuration.
   * - Firing rate
     - Count candidate rays/ticks before scene filtering
     - Rotations contain 1876 or 1877 ticks as the absolute fractional phase
       accumulates, giving 18,761.726 ticks and about 2,401,500.9 single-return
       candidates per second in the long run.
   * - Intra-tick time
     - Request ``TickId`` as well and compare ``TimeOffsetNs`` within one tick
     - Groups of eight share fire times; output ``ChannelId`` 65, corresponding to
       Figure 9-5 laser ID and manual channel ID 64, fires 23,985 ns after
       ``ChannelId`` 1 of the same tick, the first maintenance gap included.

Reading the returns back — which entries of a delivered buffer are valid, and how
many of them there are — is described in :doc:`../outputs`.

Range, intensity, and return checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use flat targets whose geometry, reflectivity, and separation are known:

* Place diffuse walls at several known distances and compare mean range and residual
  standard deviation per channel. Do not treat the datasheet's typical ±3 cm
  statement as a guaranteed Gaussian sigma.
* Verify that returns beyond 300 m are rejected. Determine the real near-field cutoff
  separately and replace the 0.3 m starting value. A cutoff below 1 m changes nothing
  by itself, because the authored ``minDistBetweenEchosM`` of 1.0 m already rejects
  any first return nearer than about 1 m. It takes effect only if that attribute is
  lowered as well, which also lets the model resolve echo pairs less than 1 m apart.
* Use a 10% NIST-equivalent material at 300 m to validate the selected threshold
  anchor. Also verify the published 5%/180 m point without weakening the required
  10%/300 m detection behavior.
* Place two partially visible surfaces less than and greater than 1 m apart.
  Dual-return output should not resolve the closer pair and can report two echoes for
  the separated pair when the material/geometry permits both paths.
* Compare diffuse and retroreflective targets over distance. Fit a non-linear
  intensity mapping only after collecting enough points to reproduce the real 0-255
  distribution.

Compare with real sensor data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a high-fidelity profile, record a stationary Alpha Prime at 600 RPM in strongest,
last, and dual-return modes. Use surveyed planar targets at multiple distances and
reflectances, then compare simulation and capture channel by channel. This profile
authors manual channel ID ``n`` as ``n + 1`` and the output reports it unchanged, so
simulated ``ChannelId`` ``n + 1`` is the capture's channel ``n``:

* detection probability and dropout rate;
* range bias and spread;
* elevation and azimuth residuals;
* intensity distribution;
* echo count, ordering, and separation;
* timing within a rotation.

Tune only the parameters identified as approximations or calibration inputs. Keep the
directly sourced geometry and timing fixed unless unit-specific calibration
demonstrates a real difference. This separation prevents a radiometric mismatch from
being hidden by changing the documented scan pattern.

Result and limitations
----------------------

The completed profile reproduces the public nominal scan geometry, firing schedule,
range envelope, return capacity, echo separation and beam divergence
of the Alpha Prime/VLS-128 source set. Its remaining uncertainty is explicit: minimum
range, beam shape beyond divergence, laser/detector radiometry, proprietary
reflectivity calibration, per-unit corrections, angular-noise distributions, and
firmware-specific return selection require measured data.

Calibrate unspecified values against measurements. Validate approximations
where the model differs from the published behavior. Use other simulation
systems for environmental and electrical properties without lidar attributes.

Related
-------

- :doc:`../index`
- :doc:`../howto/firing_pattern`
- :doc:`../howto/intensity`
- :doc:`../howto/field_of_view`
- :doc:`../attributes`
- :doc:`../../../common/validation`
- :doc:`index`
