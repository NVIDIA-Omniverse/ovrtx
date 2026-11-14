.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-core-howto-spec-sheet-profile:

Build a Profile from a Spec Sheet
=================================

A Lidar generic core model profile combines manufacturer specifications,
derived values and parameters that need calibration. Record each value's
source and uncertainty, then validate the profile in controlled scenes
before using it to represent a device.

Before you start, see :doc:`../index` for model capabilities and :doc:`../attributes` for
attribute definitions and namespaces.

Profiling workflow
------------------

Start with published specifications, retain defaults for unavailable values,
and record each value's source. Validate the profile against recordings or
controlled scenes. Calibration data, firmware behavior and proprietary
post-processing may be absent from public specifications.

Record whether each parameter value is copied from a specification, derived,
approximate or left at its default. See :ref:`source-confidence categories
<sensors-recipes-source-confidence>` for definitions.

Fields every sensor has
~~~~~~~~~~~~~~~~~~~~~~~

The published output, update, scan or frame rate, a start delay or trigger
offset and the device's name go to the shared ``omni:sensor:*`` attributes
(``frameRate``, ``startTime``, ``marketName``) as :ref:`Shared attributes
<sensors-common-sensor-configuration-shared-attributes>` describes for every
sensor; the table below maps the remaining fields.

Map the sheet to the model
~~~~~~~~~~~~~~~~~~~~~~~~~~

For an ``OmniLidar`` carrying ``OmniSensorGenericLidarCoreAPI``, map the spec
sheet to the core attributes and to the emitter-state attributes of
``OmniSensorGenericLidarCoreEmitterStateAPI``. Every attribute below except the
shared ``omni:sensor:frameRate`` is prefixed ``omni:sensor:Core:``, and ``s#``
stands for an emitter-state instance such as ``s001``. Types and defaults are in
the :doc:`generated schema reference <../../../reference/schemas>`; the Notes
column holds the spec-sheet advice and names the page that explains each
attribute in full.

The :doc:`tutorials <../tutorials/index>` work three real sensors end to end
through this table and ship the finished profiles.

.. _sensors-nonvisual-lidar-core-howto-spec-sheet-profile-table:

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 24 32 44

   * - Spec sheet field
     - Lidar attribute
     - Notes
   * - Scan rate or update rate
     - ``omni:sensor:frameRate``
     - The complete-scan rate as rational Hz. On a rotary sensor it also sets the
       firing-pattern tick rate together with ``rotPatternFiringResDeg``; refer to
       :doc:`firing_pattern`. A positive rate has
       :ref:`a floor of 0.466 Hz <sensors-lidar-min-scan-rate>`.
   * - Rotary or solid-state scanning principle
     - ``scanType``
     - ``ROTARY`` for a rotating sensor, ``SOLID_STATE`` for a fixed-pattern one.
       The principle is chosen when the sensor is created; refer to
       :doc:`../attributes`.
   * - Horizontal and vertical field of view, angular sample positions
     - ``validStartAzimuthDeg``, ``validEndAzimuthDeg``,
       ``emitterState:s#:azimuthDeg``, ``emitterState:s#:elevationDeg``,
       ``numLines``, ``numRaysPerLine``
     - Spec sheets often give only the field of view and the angular resolution.
       Build the emitter arrays from the published pattern, or from calibration
       data when you have it. The azimuth pair is :ref:`the rotary field of view
       <sensors-lidar-azimuth-window>`; a solid-state sensor takes its extent from
       the emitter arrays alone, as :doc:`firing_pattern` describes.
   * - Rotary angular firing resolution
     - ``rotPatternFiringResDeg``
     - The angular step at which the firing pattern is applied. A step that does
       not divide 360 evenly has consequences for anything you size per rotation;
       refer to :ref:`fractional ticks <sensors-lidar-fractional-ticks>`.
   * - Minimum and maximum detection range
     - ``nearRangeM``, ``farRangeM``, ``rangesMinM``, ``rangesMaxM``,
       ``rangeCount``, ``emitterState:s#:rangeId``
     - A single published range becomes the ``nearRangeM``/``farRangeM`` band.
       When the sheet gives several range regions, set ``rangeCount`` to their
       number, author one ``rangesMinM``/``rangesMaxM`` window per region, and pick
       each emitter's region with ``rangeId``. How the windows and the band
       combine, and that ``farRangeM`` still bounds how far a ray is traced, is on
       :ref:`the range band <sensors-lidar-range-window>`.
   * - Range precision terms
     - ``rangeAccuracyM``, ``rangeResolutionM``
     - The accuracy or precision figure on the sheet goes into ``rangeAccuracyM``;
       ``rangeResolutionM`` does not change the delivered coordinates. Refer to
       :ref:`range accuracy and range resolution
       <sensors-ref-range-accuracy-vs-resolution>`.
   * - Number of returns
     - ``maxReturns``
     - Raise it when the model should publish several returns per channel, for
       example when you validate against transparent or multi-surface scenes;
       refer to :doc:`../attributes`.
   * - Wavelength, peak power, pulse duration
     - ``waveLengthNm``, ``peakPowerW``, ``pulseTimeNs``
     - These shape intensity and radiometry, and the wavelength also affects the
       material's spectral response; refer to :doc:`intensity` for what each one
       does.
   * - Beam divergence or beam waist
     - ``divergenceHorDeg``, ``divergenceVerDeg``, ``beamWaistHorM``,
       ``beamWaistVerM``, ``focusDistM``
     - Author the pair the sheet gives and set both values of the other pair to
       ``0`` so the model derives it. The derivation rule, what the defaults do
       and which values each ``rayType`` consumes are under :ref:`divergence and
       beam waist <sensors-intensity-divergence-or-waist>`.
   * - Minimum reflectance detection claim
     - ``minReflectance``, ``minReflectionRangeM``
     - Approximate a guaranteed-detection claim, such as a target reflectance at a
       published range, with this pair; refer to :ref:`the detection floor
       <sensors-intensity-point-drops>`.

Verification
------------

Validate the profile against known targets in simple scenes before using it
in a full simulation.

- Check the basic geometry and the field of view against known targets.
- Compare point clouds against the expected range, angular coverage and return
  count.
- Confirm that the material, transparency, multi-return and motion settings match
  the behavior you are validating: the :doc:`material labels on the targets
  <../../../../materials/nonvisual_sensor_materials>`, ``maxReturns``, and the motion settings on
  :doc:`motion_artifacts`.

Each :doc:`tutorial <../tutorials/index>` ends with a validation step of its own,
and :doc:`Sensor Definition Validation <../../../common/validation>` checks the
parameter set against the model's rules before you render at all.

Potential issues
----------------

.. _sensors-nonvisual-lidar-core-howto-spec-sheet-profile-gap:

If a published property has no matching attribute, record it as an unmodeled
behavior. Calibration, firmware or proprietary post-processing may account
for it. Do not substitute an unrelated attribute; document any defaults or
approximations used.

If several attributes appear to match a specification, check how the selected
mode uses them. For :ref:`divergence and beam waist
<sensors-intensity-divergence-or-waist>`, specify one pair and set the other
to zero so the model derives it.

For missing or unexpectedly few returns, check validation errors, then range and intensity
limits. Invalid initial parameters
:ref:`prevent initialization until corrected <sensors-lidar-core-invalid-parameters>`.
:doc:`firing_pattern` describes the array and timing requirements, and
:doc:`Sensor Definition Validation <../../../common/validation>` checks the
layer before rendering. See :doc:`field_of_view` and :doc:`intensity` for
return filtering, and :ref:`empty-output troubleshooting
<sensors-troubleshooting-symptoms-nothing>` for other causes.

.. _sensors-nonvisual-lidar-core-howto-spec-sheet-profile-units:

Check units. The
usual lidar transcription traps are a rational Hz pair against a plain number, and
divergence in degrees against beam waist in meters: ``omni:sensor:frameRate`` is
``(10, 1)``, not ``10``, and ``divergenceHorDeg`` is an angle in degrees while
``beamWaistHorM`` is the beam radius at the waist, in meters.

Related
-------

- :doc:`Parameterize a Rotary Lidar: Velodyne Alpha Prime <../tutorials/velodyne_alpha_prime>` — a rotary lidar from the published manual and datasheet: the firing schedule, the RPM-to-resolution coupling, and how far each value can be trusted.
- :doc:`Parameterize a Solid-State Lidar: Blickfeld Cube 1 <../tutorials/blickfeld_cube1>` — a solid-state MEMS lidar derived analytically from the vendor equations, including where the published figures contradict each other.
- :doc:`Parameterize One Sensor Two Ways: SICK TiM781 <../tutorials/sick_tim781>` — one sensor modeled rotary and solid-state, with the trade-off between the two stated explicitly.
- :doc:`Constrain the Field of View <field_of_view>` — the azimuth window, the range band and per-range windows.
