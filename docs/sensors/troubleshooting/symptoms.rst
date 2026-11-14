.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-troubleshooting-symptoms:
.. _sensors-diagnose-symptoms:

Symptom Index
=============

Find the symptom you are seeing below, check the listed causes and follow the linked guide for
configuration details. Use the renderer log and output metadata to verify a diagnosis
before changing parameters.

.. contents:: Symptoms
   :local:
   :depth: 1

.. _sensors-troubleshooting-symptoms-nothing:
.. _sensors-diagnose-symptom-nothing:

Missing output
--------------

No output arrives, or one arrives with a delivered count of zero on every step.
For the Radar generic wpmDmat model, a published scan with ``Counts[0] == 0``
is an acquisition that detected no targets; a step with no radar firing returns
no radar frame. See :ref:`empty radar scans
<sensors-nonvisual-radar-outputs-empty-scan>`.

Output not requested
~~~~~~~~~~~~~~~~~~~~

Check that the RenderProduct lists the required RenderVars in ``orderedVars`` and that
each RenderVar has the correct ``sourceName``. For lidar and radar the ``channels`` list
on a ``PointCloud`` RenderVar names the tensors to produce; ``Counts`` and ``Flags`` are
published whether or not they were requested. See :doc:`Output Configuration
<../common/output_configuration>` and :doc:`Sensor Outputs <../common/sensor_outputs>`.

Requested channel missing
~~~~~~~~~~~~~~~~~~~~~~~~~

Check spelling, case and the model's supported channel names.

- The Lidar generic core and Radar generic wpmDmat models log a warning for an unknown name and omit that channel.
  The rest of the output is still produced.
- The Lidar generic wpm model also omits unknown names. If an explicit list contains none of its
  eight supported channels, it reports an error and produces no ``PointCloud``
  output until the list is corrected.

See the Outputs pages for :doc:`core lidar <../nonvisual/lidar_core/outputs>`, :doc:`WPM
lidar <../nonvisual/lidar_wpm/outputs>` and :doc:`radar
<../nonvisual/radar_wpm_dmat/outputs>`.

Wrong channels attribute type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``channels`` is a ``token[]`` attribute, and only a token array is read: a ``string[]``
value is read as an empty list. On the Lidar generic core model and the Radar generic
wpmDmat model an empty list leaves only ``Counts`` and ``Flags``; on the Lidar generic wpm
model an empty list selects all eight channels, so there the sign is every channel
arriving rather than none. Author ``token[] channels = [...]``. See :doc:`Output
Configuration <../common/output_configuration>` and, for the radar's selectable names,
:ref:`the radar's channels <sensors-nonvisual-radar-outputs-channels>`.

.. _sensors-troubleshooting-symptoms-nothing-rejected-parameters:

Lidar initialization rejected
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run :doc:`Sensor Definition Validation <../common/validation>` and check the renderer log.
Core lidar :ref:`produces no output until its initial parameters are valid
<sensors-lidar-core-invalid-parameters>`. Check for:

- Emitter arrays that are neither empty nor ``numberOfEmitters`` long.
- Fire times that decrease or exceed one tick.
- More distinct channel ids than ``numberOfChannels`` across the emitter states.
- A positive scan rate below 0.466 Hz.

WPM lidar reports an error and produces no output after rejecting its initial parameters.
Correct invalid parameters. Check for:

- Malformed firing arrays or invalid ranges.
- Non-positive physical parameters or unsupported token combinations.
- A direct return-processing mode combined with ``gaussianBeam``.
- ``tiledSubSampling`` that removes all rows from a firing pattern or rotary scan.

See :ref:`rejected core lidar parameters <sensors-lidar-core-invalid-parameters>`,
:ref:`array lengths <sensors-lidar-emitter-array-lengths>`, :ref:`fire-time order
<sensors-lidar-fire-time-order>`, :ref:`minimum scan rate <sensors-lidar-min-scan-rate>`,
:doc:`Configure a Firing Pattern <../nonvisual/lidar_core/howto/firing_pattern>` and
:doc:`WPM lidar attributes <../nonvisual/lidar_wpm/attributes>`.

Lidar detection threshold too high
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the Lidar generic core model, ``minReflectance`` and ``minReflectionRangeM`` are one
calibration point rather than two knobs, and together they set the minimum signal a hit
has to produce before it becomes a point. Lowering the reference reflectance allows weaker
returns. Increasing the reference range also lowers the threshold under ``RAW`` or
``CORRECTION``, but under the default ``NORMALIZATION`` with ``IDEALIZED`` rays it barely
moves the floor. See :ref:`the calibration pair <sensors-intensity-point-drops>`.

Acoustic envelopes have no valid echoes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check that motion BVH is enabled. The Acoustic generic wpm model requires it; without it,
envelopes contain no echo data. See :doc:`Set Up an Acoustic Sensor
<../nonvisual/acoustic_wpm/howto/set_up_sensor>` for renderer setup and to :ref:`Motion
BVH <sensors-common-output-configuration-motion-bvh>` for the switch.

Radar array geometry left unset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The element counts and spacings of the transmit element, the receive element and the
receiving aperture all default to zero, and zero is not a legal value: the defaults are
placeholders rather than a working array. Left at zero, a ``PATCH_ARRAY_MODEL`` element
evaluates to zero gain in every direction, and a ``WAVEFORM`` scan whose aperture element
spacing is zero cannot turn its spectrum into detections at all. Author the geometry
together with the mode. See :doc:`the radar USD attributes
<../nonvisual/radar_wpm_dmat/attributes>`.

Invalid radar RCS coefficients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``rcsTuningCoefficients`` must hold exactly three values. See :ref:`the RCS
coefficients <sensors-nonvisual-radar-attributes-rcs-tuning>`.

Camera sensor pipeline not enabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Camera generic core model requires exactly one sensor schema on the camera:
``OmniSensorGenericCameraCoreAPI``. A product activates the pipeline by requesting one of
its seven reserved output names.

Check that the camera has the required schema and that the product requests ``HdrColor``
and at least one primary output. Missing requirements cause the product to be skipped with
an error. Avoid using the reserved names for custom outputs, since those names activate
the sensor pipeline.

See :ref:`reserved output names <sensors-visual-camera-core-outputs-reserved-names>`.

Camera pipeline input or primary output missing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The pipeline's only input is the ``HdrColor`` AOV, which must sit on the same product, and
one of the two primary outputs, ``OmniCameraSensorPreIsp`` or ``OmniCameraSensorPostIsp``,
has to be present as well. If either is missing, the product is skipped and an error is
logged; a diagnostic tap on its own does not build a pipeline for the tap to sit on. See
:ref:`the primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` and
:doc:`Compand to a RAW Format and Run the ISP
<../visual/camera_core/howto/companding_and_isp>`.

Companding output exceeds 16 bits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The curve's last *y* exceeds 65535. Keep it at or below that for the full pipeline; the
pre-ISP pipeline alone has no such limit. See :ref:`Stay within 16 bits
<sensors-visual-camera-core-howto-companding-and-isp-16bit-gate>` and :ref:`companding <sensors-visual-camera-core-attributes-companding>`.

ISP outputs missing
~~~~~~~~~~~~~~~~~~~

Check both the output request and the ISP program:

- Request ``OmniCameraSensorPostIsp`` to build the ISP portion of the pipeline.
  A pre-ISP-only request does not support the ISP diagnostic taps.
- Set ``ispSmodelCameraProgram`` to an ISP program. Its default is empty;
  without a program, ``OmniCameraSensorPostYuvIsp`` and
  ``OmniCameraSensorPostIsp`` contain no processed image.

See :doc:`the ISP guide <../visual/camera_core/howto/companding_and_isp>`, :ref:`primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` and :ref:`ISP attributes
<sensors-visual-camera-core-attributes-isp>`.

Incomplete depth-sensor output request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Camera single-view stereo depth model requires all three input RenderVars and at least one depth output on its
RenderProduct. A missing input prevents depth processing and logs an error. See :doc:`the model's Outputs <../visual/depth_camera/outputs>`.

Empty WPM lidar startup output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Empty startup output is expected. An accepted point cloud request publishes an output marked empty:
the requested channel tensors hold zero points, ``Counts[0]`` is zero, and the configured
``maxPoints``, layout, channel types and coordinate metadata are all still present. See
:ref:`the empty output <sensors-nonvisual-lidar-wpm-outputs-empty-output>`.

Point-cloud mapping failed
~~~~~~~~~~~~~~~~~~~~~~~~~~

The array map device (``Device.CUDA_ARRAY`` in Python) is the zero-copy path for image
outputs, which are array-backed. The channels of a ``PointCloud`` output are held in
linear device memory, so requesting the array mode for them fails and directs you to the
linear CUDA mode. Map point clouds on the CPU or on the CUDA device. See :doc:`Sensor
Outputs <../common/sensor_outputs>`.

.. _sensors-troubleshooting-symptoms-fewer:
.. _sensors-diagnose-symptom-fewer:

Fewer points or pixels than expected
------------------------------------

Returns arrive, but not as many as the sensor should have produced, or some steps carry
none at all; on a depth image, the same symptom is pixels that hold no distance where you
expected one.

WPM lidar subsampling enabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Lidar generic wpm model, an ``omni:sensor:LidarWpm:tiledSubSampling`` above ``1``,
read from tile zero, reduces the emitter rows fired by every tile; ``0`` and ``1`` mean no
reduction. Leave the default ``0``, or author ``1``, on tile zero when every tile should
trace at full fidelity. See :ref:`Tiling and subsampling
<sensors-nonvisual-lidar-wpm-attributes-tiled-subsampling>` on the Lidar generic wpm
model's USD attributes.

Nearby lidar returns missing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the near-range limits if nearby objects are missing while distant objects appear.
With the default ``IDEALIZED`` rays ``minDistBetweenEchosM`` also imposes a near limit.
The larger limit applies. See :ref:`the near range <sensors-lidar-range-window>`.

Step ends before the lidar scan completes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default — ``omni:sensor:Core:partialOutputs`` is ``false`` — a Lidar generic core model
that is part-way through a scan when a step ends delivers no output for its product on
that step, and the whole scan arrives on the step that completes it. If you need the
points as they are traced, author ``partialOutputs`` ``true``; in either case bound every
read by ``Counts[0]``. See :ref:`partial outputs <sensors-output-shaping-empty-step>`,
:doc:`Sensor Scheduling <../common/multi_rate>` and :doc:`Sensor Outputs
<../common/sensor_outputs>`.

Radar steps without a scan
~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Radar generic wpmDmat model, a step that fires no scan returns no radar
``PointCloud`` frame and leaves the pending scan and its ambiguity entry unchanged.
A scan that fires but detects no targets still delivers a frame with ``Counts[0] == 0``
and scan metadata. Inspect those params when checking the scan sequence. Step at the
scan period, and read the scan index from the ``scanIdx`` param of the ``PointCloud``
output rather than inferring it from how many steps ran. A ``timestampNs`` of ``0`` is
valid for a scan acquired at time zero. See
:ref:`Step at the scan period
<sensors-nonvisual-radar-howto-scan-configurations-stepping>` and :doc:`Sensor Scheduling
<../common/multi_rate>`.

Radar detection capacity reached
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A radar scan is capped at 2500 detections by design: detections past the cap are dropped,
the count stops rising, and the only hint is a ``Counts[0]`` that stays at 2500. Narrow
what the scan sees, with a smaller ``maxRangeM`` or smaller ``maxAzAngDeg`` and
``maxElAngDeg`` half-angles (what lies beyond them is discarded while
``enableRangeAliasing`` and ``enAngAliasing`` stay ``false``), or raise ``cfarOffset`` so
that fewer cells pass the detection threshold. See :ref:`the detection cap
<sensors-nonvisual-radar-outputs-detection-cap>`, :ref:`field of view, range and resolution <sensors-nonvisual-radar-attributes-fov>` and :ref:`CFAR
<sensors-nonvisual-radar-attributes-cfar>`.

Unexpected acoustic signal-way count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``numSignalWays`` param counts the signal ways the frame is laid out for — one per
receiving mount per channel id — not the ones that heard something; count those by the
``VALID`` bit of ``Flags``. If the layout count itself is not the number of mounts times
the number of distinct channel ids, check the mounts you authored and the channel ids of
your firing sequences: the ids must run from ``0`` without gaps, so renumber them if they
do not. See :ref:`the layout <sensors-nonvisual-acoustic-outputs-slots>` on the acoustic
Outputs and :ref:`channel ids <sensors-nonvisual-acoustic-attributes-channel-ids>` on its
USD attributes.

No returns through transmissive surfaces
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Lidar generic core model raising ``maxReturns`` is what keeps the return from
behind the surface, and on the Lidar generic wpm model the ``waveform`` return-processing
mode is. See :doc:`the Lidar generic core model's USD attributes
<../nonvisual/lidar_core/attributes>` and :doc:`Choose a Return-Processing Mode
<../nonvisual/lidar_wpm/howto/return_processing>`.

Nearby surfaces merge into one lidar return
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Lidar generic core model they lie closer than the down-range separation. With the
default ``IDEALIZED`` ray type that separation is ``minDistBetweenEchosM`` alone; with a
beam ray type it is the larger of ``minDistBetweenEchosM`` and half the distance light
travels in ``pulseTimeNs``, so there a long pulse merges them. See :doc:`Tune Intensity
and Point Drops <../nonvisual/lidar_core/howto/intensity>` and :doc:`the model's USD
attributes <../nonvisual/lidar_core/attributes>`.

Invalid or narrow radar gain grid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``CUSTOM`` grid whose angle vectors or gain arrays break :ref:`the grid rules
<sensors-nonvisual-radar-attributes-gain-grid>` is rejected: the reason is logged as an
error, and a running sensor keeps the configuration it had (:ref:`Batch validation
<sensors-common-runtime-updates-batch>`). A grid that passes still has zero gain outside
its angular extent, so a scan whose targets lie beyond the grid's angles produces far
fewer detections than expected, or none. See :doc:`the radar USD attributes
<../nonvisual/radar_wpm_dmat/attributes>`.

Radar targets merge at the same range and velocity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a ``FAST`` scan, check ``cfarMode``. Use ``4D`` instead of ``2D`` to distinguish
targets by angle as well as range and velocity. See :ref:`the scope of cfarMode
<sensors-nonvisual-radar-attributes-cfar-mode-scope>`.

Zero regions in a depth image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Camera single-view stereo depth model, occlusion holes, failed confidence,
distances outside the range limits and disparities above the maximum all resolve to the
same zero distance, and widening the product moves the near limit outward without anything
being authored. See :doc:`the model's Outputs <../visual/depth_camera/outputs>` and
:doc:`its USD attributes <../visual/depth_camera/attributes>`.

.. _sensors-troubleshooting-symptoms-wrong-place:
.. _sensors-diagnose-symptom-wrong-place:

Incorrect coordinates or units
------------------------------

Points, or the distances of a depth image, arrive in a plausible shape but are measured
from somewhere other than what the consumer assumed: the prim faces the wrong way, or the
output is read against another coordinate representation, frame or unit. Each of these
produces an output that looks right on its own.

Incorrect sensor orientation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A sensor prim follows the camera convention, whatever model it runs: it looks along its
local ``-Z`` with ``+Y`` up, and a lidar's beam pattern, a radar's field of view and an
acoustic sensor's lobe are all aimed along that axis. A transform authored for a device
that looks along its own ``+X`` therefore aims the scan elsewhere. A prim with no rotation
authored looks along world ``-Z``, which in a Z-up stage is straight down.

Rotate the prim until its ``-Z`` points where the sensor should look: to look along world
``+X`` in a Z-up stage, the lidar and radar examples author ``xformOp:rotateXYZ = (90, 0,
-90)``.

See :ref:`Orienting the prim <sensors-common-sensor-configuration-orientation>` and to the
forward-axis statements of :doc:`the Lidar generic core model
<../nonvisual/lidar_core/attributes>`, :doc:`the Radar generic wpmDmat model
<../nonvisual/radar_wpm_dmat/attributes>` and :ref:`the Acoustic generic wpm model
<sensors-nonvisual-acoustic-attributes-firing-axis>`.

Spherical output interpreted as Cartesian
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``elementsCoordsType`` defaults to ``SPHERICAL`` on both lidar models and on the Radar
generic wpmDmat model alike. Author it explicitly rather than relying on the default being
what you expect, and read the ``coordsType`` param back to see which one was actually
used. See :doc:`Configure Lidar Output <../nonvisual/lidar_core/howto/output_shaping>`,
:doc:`the Lidar generic wpm model's USD attributes <../nonvisual/lidar_wpm/attributes>`
and :doc:`the radar Outputs <../nonvisual/radar_wpm_dmat/outputs>`.

Angular units confused
~~~~~~~~~~~~~~~~~~~~~~

The three components are azimuth in degrees, elevation in degrees and distance in meters,
in that order, and the spherical-to-Cartesian conversion that the lidar and radar models
use reads them that way. On the radar, the scan-limit params (``minAzRad`` through
``maxElRad``) are in radians while the spherical ``Coordinates`` are in degrees. Confirm
against the values before scaling them. See :doc:`Sensor Outputs
<../common/sensor_outputs>` and :doc:`the radar Outputs
<../nonvisual/radar_wpm_dmat/outputs>`.

Incorrect output reference frame
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``outputFrameOfReference`` decides whether the coordinates are measured against the
sensor, the world or a frame you place yourself, and a custom transform is read only when
that attribute says ``CUSTOM``. The Lidar generic core model rotates ``HitNormal`` and
``Velocity`` into that frame along with the coordinates. See :doc:`Configure Lidar Output
<../nonvisual/lidar_core/howto/output_shaping>` and :doc:`the model's Outputs
<../nonvisual/lidar_core/outputs>`.

Incorrect tensor layout
~~~~~~~~~~~~~~~~~~~~~~~

Read the mapped tensor's shape and strides; packing differs by model:

- Core lidar and radar ``Coordinates`` are component-first: all x values,
  then all y values, then all z values.
- Core lidar ``HitNormal``, ``Velocity`` and ``ObjectId`` are point-first.
- WPM lidar ``Coordinates`` are point-first.

See :doc:`Sensor Outputs <../common/sensor_outputs>` and the model Outputs pages for
:doc:`core lidar <../nonvisual/lidar_core/outputs>`, :doc:`WPM lidar
<../nonvisual/lidar_wpm/outputs>` and :doc:`radar <../nonvisual/radar_wpm_dmat/outputs>`.

Motion-distorted lidar scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For core lidar, select ``COMPENSATED`` output or deskew downstream using per-point
``TimeOffsetNs``. Check the delivered ``motionCompensationState``: ``0`` means
compensation was not applied; ``1`` means it was applied.

Also check the renderer's motion BVH setting. Without it, there is no within-frame motion
in the trace to compensate. Lidar and radar can still produce output, so an empty point
cloud does not diagnose the motion BVH setting.

See :doc:`Motion Artifacts <../nonvisual/lidar_core/howto/motion_artifacts>`,
:ref:`compensation and motion BVH <sensors-motion-both-settings>` and :ref:`Motion BVH
<sensors-common-output-configuration-motion-bvh>`.

Lidar channel ids used as indices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Lidar generic core model reports each point's ``ChannelId`` exactly as its emitter's
``channelId`` was authored, so a consumer that adds or subtracts one to recover a beam
number, or indexes a table by the reported value, attributes points to the neighboring
detector. See :ref:`channel ids are labels <sensors-lidar-core-channel-ids-are-labels>`
and :ref:`ChannelId <sensors-nonvisual-lidar-core-outputs-channel-id>`.

Radar field of view twice the intended size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A total angle was authored into an attribute that expects a half-angle: ``maxAzAngDeg``
and ``maxElAngDeg`` each describe the positive half of a symmetric interval, so a 150°
field of view is authored as 75. See :doc:`Choose Parameter Values
<../nonvisual/radar_wpm_dmat/howto/choose_parameters>`.

Radar coordinate attributes in the wrong namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The attributes were authored under ``omni:sensor:Core:``, the Lidar generic core model's
namespace, instead of ``omni:sensor:WpmDmat:``. A radar prim does not carry the lidar's
attribute, and authoring it there changes nothing; the delivered ``coordsType`` and
``frameOfReference`` params report what the model actually used. See :doc:`the radar USD
attributes <../nonvisual/radar_wpm_dmat/attributes>` and to :ref:`incorrect attribute
names or namespaces <sensors-troubleshooting-symptoms-retune-namespace>` below.

Depth image and point cloud use different units
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Camera single-view stereo depth model applies no scene-unit conversion of its own. Its
distance output and its ``minDistance`` and ``maxDistance`` range limits are in meters,
because the renderer delivers ``DistanceToImagePlaneSD`` in meters whatever the stage's
``metersPerUnit``; its point positions come from ``Camera3dPositionSD``, which is in scene
units. On a stage whose ``metersPerUnit`` is not 1 the two differ by that factor. See
:doc:`the model's Outputs <../visual/depth_camera/outputs>`.

Sensors return identical point clouds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check whether the sensors have the same transform. The sensors are separate prims — each
on its own RenderProduct on the Lidar generic core model, tiles of one product on the
Lidar generic wpm model — and each needs its own placement. See :ref:`independent RenderProducts <sensors-common-output-configuration-independent-products>` and, for the
Lidar generic wpm model, :doc:`its tiling how-to
<../nonvisual/lidar_wpm/howto/tile_lidars>`.

ROI wraps around the sensor
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A ``minAzimuthROI`` greater than ``maxAzimuthROI`` is a wrapping interval rather than an
error. See :doc:`Constrain the Field of View
<../nonvisual/lidar_core/howto/field_of_view>`.

Motion distortion affects scan alignment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check for motion distortion in the scans. Compensate at the sensor, or deskew before the
mapper. See :doc:`Motion Artifacts <../nonvisual/lidar_core/howto/motion_artifacts>`.

Incorrect units in a device profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Half-angles against a full field of view, millimeters against meters, and a rational Hz
pair against a plain number are the three that catch people building a profile from a
vendor specification. See the spec-sheet how-to of the model: :doc:`Lidar generic core
model <../nonvisual/lidar_core/howto/spec_sheet_profile>`, :doc:`Radar generic wpmDmat
model <../nonvisual/radar_wpm_dmat/howto/spec_sheet_profile>` or :doc:`Camera single-view
stereo depth model <../visual/depth_camera/howto/spec_sheet_profile>`.

Depth image and point cloud use different frames
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The distance image sits on the second imager's pixel grid; the point cloud positions are
read from the rendered view's camera-space positions. Projecting one with the other's
geometry mixes two frames. See :doc:`the model's Outputs
<../visual/depth_camera/outputs>`.

.. _sensors-troubleshooting-symptoms-plausible:
.. _sensors-diagnose-symptom-plausible:

Values look plausible but are wrong
-----------------------------------

Check output interpretation and model configuration when values are in range but do not
match the expected measurements.

Reading beyond the delivered count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The shape is the capacity. Bound every per-entry read by ``Counts[0]``, the first element
of the ``Counts`` tensor, not by the tensor's length; on the Radar generic wpmDmat model
the capacity is a fixed 2500, so reading to the tensor length gives 2500 entries of which
most are not detections. See :ref:`Delivered-entry count
<sensors-common-sensor-outputs-counts-bound>`.

Incorrect validity-bit test
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A lidar or radar entry is real when the ``VALID`` bit (``0x40``) of ``Flags`` is set.
``Flags`` is a bit field: the Lidar generic core model can also set :ref:`the new-scan bit
(0x20) <sensors-common-sensor-outputs-new-scan-bit>` on a real return, so an equality test
against the ``VALID`` value rejects perfectly good returns. Acoustic ``Flags`` carry the
same bit, once per signal way rather than once per sample, and a test for the value ``1``
rejects every signal way. See :doc:`Sensor Outputs <../common/sensor_outputs>`, :doc:`the
Lidar generic core model's Outputs <../nonvisual/lidar_core/outputs>` and :doc:`the
acoustic Outputs <../nonvisual/acoustic_wpm/outputs>`.

Radar values read from an empty scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a published radar scan has ``Counts[0] == 0``, none of its allocated
per-detection tensor elements is a measurement. Read the scan metadata, but do
not read coordinates, RCS or velocity beyond the delivered count. See
:ref:`empty scans <sensors-nonvisual-radar-outputs-empty-scan>`.

Incorrect radial-velocity sign
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Radial velocity is signed and approaching detections are negative, so use the sign to
distinguish approaching and receding targets. Use the absolute value when testing radial
speed regardless of direction. See :doc:`the radar Outputs
<../nonvisual/radar_wpm_dmat/outputs>`.

Aliased radar detections
~~~~~~~~~~~~~~~~~~~~~~~~

With range or angular aliasing enabled, out-of-interval contributions fold into the
configured interval instead of being discarded, and a folded detection is
indistinguishable from a real one by inspection. A target whose radial speed exceeds the
scan's unambiguous velocity folds the same way, and that folding has no switch to turn it
off. Aliasing belongs in the parameterization only when the real operating mode has the
same ambiguity. See :doc:`the radar USD attributes
<../nonvisual/radar_wpm_dmat/attributes>` and :doc:`Validate a Parameterization
<../nonvisual/radar_wpm_dmat/howto/validate_parameterization>`.

Non-visual material id is zero
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The labels are not being read. An unmatched base token, an absent attribute and a
deliberate ``none`` all read as ``none``, base index 0, so the number itself does not say
which happened. Work through the authoring checklist on :doc:`Non-Visual Sensor Materials
<../../materials/nonvisual_sensor_materials>`; :doc:`the Lidar generic core model's
Outputs <../nonvisual/lidar_core/outputs>` explains how to read ``MaterialId``.

Material label has no effect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On a lidar, read the reported ``MaterialId`` first: a label missing there was not read or
did not match. See :doc:`the Lidar generic core model's Outputs
<../nonvisual/lidar_core/outputs>`.

Radar per-detection time offsets are zero
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Radar ``TimeOffsetNs`` is zero by design, because the model simulates each scan as a
single instant, and each model measures the offset from its own instant. Take the scan's
time from the frame's params instead: ``timestampNs`` is the scan's instant, and
``frameStartTimeStampNs`` and ``frameEndTimeStampNs`` bound the frame's time window, which
can be wider than that instant. See :ref:`Timestamps <sensors-nonvisual-radar-outputs-time-offset>` and :ref:`Model-specific channel
definitions <sensors-common-sensor-outputs-shared-names>`.

WPM lidar firing-pattern indices changed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Lidar generic wpm model, ``FiringPatternIndex`` is the pattern's position in
lexicographic order, so renaming one, adding one, or removing one that sorts earlier
changes the value reported for every pattern after it. Do not store the index as a
pattern's identity across edits, and name the instances with zero-padded numbers, such as
``p001`` and ``p002``, so that a new pattern sorts where you expect it. See
:ref:`FiringPatternIndex is a position
<sensors-nonvisual-lidar-wpm-outputs-firing-pattern-index>` and :ref:`the firing-pattern
instances <sensors-nonvisual-lidar-wpm-attributes-firing-patterns>`.

Lidar scans are instantaneous
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``instantLidar`` delivers a complete scan per frame, which is convenient for a
demonstration and is not representative of a time-resolved scan. An
``omni:sensor:frameRate`` of ``(0, 1)`` does the same on the Lidar generic core
model: the rate reads as unset and every capture flashes a whole scan, on the
renderer's default capture schedule. For a time-resolved scan, leave
``instantLidar`` at its default ``false`` and author a positive scan rate of at
least 0.466 Hz, such as ``(10, 1)``. See
:ref:`the scan rate <sensors-lidar-core-frame-rate-floor>` on the Lidar generic core model's USD attributes and
:ref:`instant lidar <sensors-lidar-core-instant-lidar>` on Configure Lidar Output.

Unprocessed depth required
~~~~~~~~~~~~~~~~~~~~~~~~~~

Read ``DistanceToImagePlaneSD`` or ``DistanceToCameraSD``, described in :doc:`Cameras:
Outputs <../cameras/outputs>`. The :doc:`Camera single-view stereo depth model
<../visual/depth_camera/index>` applies stereo-camera effects to the rendered distances.

Results differ between runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The scene, the motion or the material assignments moved, or the two runs did not start
from the same point or take the same steps. No sensor model takes a seed. Each model's
noise starts from a fixed, built-in point when its RenderProduct is first stepped and
again after :py:meth:`~ovrtx.Renderer.reset` (:c:func:`ovrtx_reset` in C). It advances
with every frame the model traces. An attribute edit applied after a reallocation restarts
the noise of the Lidar generic core, Radar generic wpmDmat and Acoustic generic wpm models
as well (:doc:`Runtime Parameter Updates <../common/runtime_updates>`). Compare multiple
frames when evaluating noise; a single frame does not establish the distribution. See
:doc:`Validate a Parameterization
<../nonvisual/radar_wpm_dmat/howto/validate_parameterization>`.

Radar calibration does not transfer between scenes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detection settings tuned before materials and antenna response were stable do not carry
across scenes, and a radar cross section that is systematically off across the whole scene
is a calibration matter — the material assignments, the antenna gain data, ``powerFactor``
and ``rcsTuningCoefficients`` — rather than a geometric parameter. Re-run the checks of
Validate a Parameterization in their order. Hold the scene, the motion and the material
assignments fixed between runs.

Calibrate ``powerFactor`` and ``rcsTuningCoefficients`` against measured return strength
before you touch CFAR. See :ref:`the order of the checks
<sensors-nonvisual-radar-howto-validate-parameterization-order>` and :ref:`materials and
antenna response <sensors-nonvisual-radar-howto-validate-parameterization-materials>` on
Validate a Parameterization, and :ref:`values from calibration
<sensors-nonvisual-radar-howto-choose-parameters-calibration>` on Choose Parameter Values.

Variable tick count per rotation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ticks-per-rotation ratio is real-valued rather than integral, and the Lidar generic
core model carries the fractional phase across rotations, so a completed rotation holds
either the floor or the ceiling of it. A fixed integer tick count per scan is only
nominal: do not size a per-rotation buffer from it, and do not assume that every rotation
reports the same number of ticks. See :ref:`fractional ticks
<sensors-lidar-fractional-ticks>` and :doc:`the model's USD attributes
<../nonvisual/lidar_core/attributes>`.

Unexpected lidar intensity
~~~~~~~~~~~~~~~~~~~~~~~~~~

Changing the wavelength can change intensity because it affects photon conversion. For an unexpected intensity
range, check the scale and processing mode. If every return carries the same value,
``intensityScalePercent`` / 100 under ``LINEAR`` mapping, the cause is the output clip
instead: the detection floor is compared before the clip, so when the floor is above 1
every kept return is clipped to the same intensity.

On the Lidar generic wpm model, when intensity saturates, check the raw versus
range-normalized mode, ``intensityScale``, ``calibrationGain``, the detector field of view
and the material assignment before touching detection thresholds: mapping cannot recover a
signal the return pipeline already rejected.

See :doc:`Tune Intensity and Point Drops <../nonvisual/lidar_core/howto/intensity>`,
:doc:`the Lidar generic wpm model's intensity how-to
<../nonvisual/lidar_wpm/howto/intensity>` and :doc:`its USD attributes
<../nonvisual/lidar_wpm/attributes>`.

Camera mosaic is black or saturated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``colorFilterArrayMaximalValue`` is a multiplier, not a clamp, so check it
against the range the image actually occupies. See :doc:`the color filter
array how-to <../visual/camera_core/howto/color_filter_array>` and :ref:`the
color filter array attributes <sensors-visual-camera-core-attributes-cfa>`.

Camera exposure differs from OpenUSD defaults
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``exposure:fStop``, ``exposure:responsivity`` or ``exposure:time`` that is not authored
takes the renderer's defaults — f/5, 1.10267091 and 1/50 s — rather than the OpenUSD
schema fallbacks of 1, 1 and 1. Each attribute is decided on its own, and ``exposure:iso``
is not affected. Author all three when you compute exposure from them. See :doc:`the
camera USD attributes <../cameras/usd_camera_attributes>`.

Acoustic identity channels use floating-point storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``TransmitterIds``, ``ReceiverIds`` and ``ChannelIds`` use floating-point storage. Convert
valid entries to integers before using them as array indices. See :doc:`the acoustic
Outputs <../nonvisual/acoustic_wpm/outputs>`.

Implausible acoustic parameters accepted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Acoustic generic wpm model's parameter validation checks the types of its scalar and
coefficient attributes and the ``signalMode`` token, not physical plausibility, so an
implausible value can be accepted and affect the output. A receiver index or ``rxGroupId``
that names no mount or group is repaired by the model, which logs an error. See :doc:`the
acoustic USD attributes <../nonvisual/acoustic_wpm/attributes>` and :doc:`Sensor
Definition Validation <../common/validation>`.

.. _sensors-troubleshooting-symptoms-retune:
.. _sensors-diagnose-symptom-retune:
.. _sensors-diagnose-symptom-reopen:

Runtime edits have no effect
----------------------------

The stage shows the new value; the output does not.

Attribute cannot change at runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check runtime-update support on the model's USD Attributes page; support varies by
attribute and model. On the Lidar generic core model ``scanType`` and ``rayType`` are the
fixed ones: author them before the sensor starts producing, and recreate the sensor to
change either. See :doc:`Runtime Parameter Updates <../common/runtime_updates>` and
:ref:`what the Lidar generic core model holds fixed
<sensors-lidar-core-no-runtime-changes>`.

Rejected update retained the old configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the renderer log for a rejected update. An output frame has no general
update-acceptance flag; compare the relevant output params and behavior. See
:ref:`refusals show in the log <sensors-common-runtime-updates-quiet-refusal>`.

Reading a frame created before the edit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read the delivered params of a later frame. The frame in flight when you edit finishes
with the values it started with, so compare a frame built after it. If that frame's params
— ``coordsType``, ``frameOfReference``, ``motionCompensationState`` — still report the old
value, the edit did not reach the model: it was refused, and the log says so, or it was
authored where nothing reads it. See :doc:`Runtime Parameter Updates
<../common/runtime_updates>` and :doc:`the Lidar generic core model's Outputs
<../nonvisual/lidar_core/outputs>`.

Invalid parameter rejects the update batch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Several edits made together all failed to apply, and the log names one value. The model
rebuilds its configuration from the sensor's entire parameter set, so one bad value drops
the well-formed edits that traveled with it, on that update and on every later one until
it is corrected. Correct it, and change one thing at a time while diagnosing; the rules a
firing pattern is checked against are listed under :ref:`the rejected parameter set
<sensors-troubleshooting-symptoms-nothing-rejected-parameters>` above. See :ref:`Batch
validation <sensors-common-runtime-updates-batch>`.

.. _sensors-troubleshooting-symptoms-retune-namespace:

Incorrect attribute name or namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the exact schema name, spelling and instance prefix. USD attribute names are
case-sensitive; an unrecognized attribute does not configure the model.

- WPM lidar uses ``omni:sensor:LidarWpm:tiledSubSampling``, with a capital ``S``
  in ``Sampling``.
- Radar scan attributes require the ``scan:<instance>:`` segment.
- Pinhole and fisheye lens-distortion attributes use different namespaces.
  Author attributes for the selected lens model.

See :ref:`attribute namespaces <sensors-common-sensor-configuration-namespaces>`, the
model's USD Attributes page and :ref:`lens-model selection
<sensors-recipes-calibration-model-selector>`.

Legacy lens-distortion schema warning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The camera applies ``OmniLensDistortionFthetaAPI``, ``OmniLensDistortionKannalaBrandtK3API`` or
``OmniLensDistortionRadTanThinPrismAPI``, one of the three compatibility schemas, and it
still renders through that model. Migrate the calibration to the OpenCV, lookup-table or
omni-directional stereo schema. See :ref:`the lens-distortion schemas
<sensors-cameras-lens-calibration-schemas>`.

Emitter state not applied
~~~~~~~~~~~~~~~~~~~~~~~~~

No API schema instance is applied to the prim, or its arrays are authored under a prefix
that does not match the instance name. See :doc:`Configure a Firing Pattern
<../nonvisual/lidar_core/howto/firing_pattern>`.

Acoustic firing arrays have different lengths
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A firing sequence is four parallel arrays with one entry per event; author all four
together, with the same length. See :ref:`the parallel arrays
<sensors-nonvisual-acoustic-attributes-parallel-arrays>`.

Control does not apply to the scan type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The azimuth limits do nothing on a solid-state sensor, where they do not apply at all. See
:ref:`the azimuth window <sensors-lidar-azimuth-window>` and :doc:`Constrain the Field of
View <../nonvisual/lidar_core/howto/field_of_view>`.

Unsupported attributes
~~~~~~~~~~~~~~~~~~~~~~

A few declared attributes are not read by any model. On the Lidar generic core model the
emitter-states file, ``omni:sensor:Core:emitterStatesFile``, is one; on the Camera generic
core model the three color-correction flags ``colorCorrectionRedBlueSwap``,
``colorCorrectionOutputFloat16`` and ``colorCorrectionOutputFloat32`` are three more.
Authoring them changes nothing. See :doc:`Limitations <limitations>` for the complete list
and to the USD attributes page of the model.

Basic-mode acoustic attribute used in interference mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The attribute belongs to the basic mode, and the interference mode leaves it unread. See
:ref:`what each mode reads <sensors-nonvisual-acoustic-attributes-mode-reads>`.

CFA label changed without changing its weights
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The token is a label, not a control; see :ref:`the color filter array
attributes <sensors-visual-camera-core-attributes-cfa>`.

Required control not enabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``colorCorrectionBlack`` and ``colorCorrectionFullwellBlack`` are read only when
``colorCorrectionApplySaturation`` is ``true``, which is not the default, and a custom
frame transform is read only when the frame of reference says ``CUSTOM``. See :ref:`color correction <sensors-visual-camera-core-attributes-color-correction>` and :doc:`Configure
Lidar Output <../nonvisual/lidar_core/howto/output_shaping>`.

ROI or radar scan configuration ineffective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A region-of-interest window does not narrow a lidar's field of view; the azimuth pair does
that. An authored ROI has no effect while one of its two limits is still at the default
400, or while no emitter state is tagged with ``isROIState``. On the radar, a second scan
configuration left unauthored sits at schema defaults that are a working scan rather than
an inert one, which looks like success. See :doc:`Constrain the Field of View
<../nonvisual/lidar_core/howto/field_of_view>` and :doc:`Run More Than One Scan Pattern
<../nonvisual/radar_wpm_dmat/howto/scan_configurations>`.

Unexpected radar scan index or order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If every acquired scan reports ``scanIdx = 0``, check that each additional
``OmniSensorGenericRadarWpmDmatScanCfgAPI:<name>`` instance is applied. Applying the
instance supplies the attributes used to discover the scan configurations.

Inspect every returned radar frame, including scans with ``Counts[0] == 0``;
their metadata still identifies the scan that fired. Steps without a radar firing
return no radar frame and do not advance the configuration sequence. Instances run in
lexicographic name order; use zero-padded names
such as ``s002`` rather than ``s2``.

See :doc:`Run More Than One Scan Pattern
<../nonvisual/radar_wpm_dmat/howto/scan_configurations>`.

Radar resolution and processing-mode mismatch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``rangeResM`` and ``velResMps`` set detection-cell sizes. Use the noise attributes to
configure measurement error.

Check that the attributes you edit apply to the selected ``datacubeMode``:

- ``FAST`` uses bin dimensions and resolutions, and ignores explicit waveform
  parameters.
- ``WAVEFORM`` uses waveform, sampling, padding, window and aperture parameters,
  and ignores bin dimensions and resolutions.

See :doc:`radar attributes <../nonvisual/radar_wpm_dmat/attributes>` and :doc:`Choose
Parameter Values <../nonvisual/radar_wpm_dmat/howto/choose_parameters>`.

WPM lidar edit applied to the wrong tile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

WPM lidar reads its parameters from the first sensor in the product; edit that sensor. See
:ref:`tile zero <sensors-nonvisual-lidar-wpm-attributes-tile-zero>`.

WPM lidar subsampling update rejected
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On the Lidar generic wpm model, a value that leaves a firing pattern, or the whole rotary
scan, with no emitter rows is rejected. The last valid profile remains active; a sensor
created with an invalid value publishes nothing. Reduce
``omni:sensor:LidarWpm:tiledSubSampling``. See :doc:`Tile Lidars
<../nonvisual/lidar_wpm/howto/tile_lidars>` and :doc:`Retune the Sensor While It Runs
<../nonvisual/lidar_wpm/howto/runtime_updates>`.

.. _sensors-troubleshooting-symptoms-slow:
.. _sensors-diagnose-symptom-slow:

Performance problems
--------------------

Check the following causes of increased frame time or memory use.

Sensor count increases workload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runtime and memory grow with every sensor you add. On the Lidar generic core model each
sensor renders on its own RenderProduct and is traced and stored on its own. On the Lidar
generic wpm model every tile of a product adds its workload and its share of the point
cloud. Use ``tiledSubSampling`` on tile zero to reduce the number of emitter rows traced
by every tile. See :doc:`its tiling how-to <../nonvisual/lidar_wpm/howto/tile_lidars>`.

Ray density increases tracing cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``raysPerDeg`` controls geometric sampling density; raising it costs frame time and does
not sharpen the configured angular resolution. Tune it for stable geometric coverage at an
acceptable frame time. See :doc:`Choose Parameter Values
<../nonvisual/radar_wpm_dmat/howto/choose_parameters>`.

Trace depth increases tracing cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Frame time grew with ``traceTreeDepth`` on the Radar generic wpmDmat model or the Acoustic
generic wpm model, or with ``maxReturns`` on the Lidar generic wpm model, which derives
its depth from it. Raise the depth only when the scenario needs indirect paths. See
:ref:`traceTreeDepth <sensors-nonvisual-radar-attributes-trace-depth>` on the radar,
:doc:`the acoustic USD attributes <../nonvisual/acoustic_wpm/attributes>` and :doc:`Choose
a Return-Processing Mode <../nonvisual/lidar_wpm/howto/return_processing>`.

Acoustic interference mode costs more
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Modeling interference between concurrent transmissions costs more than the basic mode,
which is the default. Where interference is not needed, set ``enableInterference`` back to
``false`` on the running sensor: the model rebuilds its buffers for the basic mode, so the
prim need not be recreated, and a frame already in flight finishes in the mode it started
in. See :doc:`the acoustic USD attributes <../nonvisual/acoustic_wpm/attributes>`.

Runtime edit increases step time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An edit that changes how much memory the sensor needs — a longer firing sequence, an extra
mount, a larger return capacity — makes the step it lands on longer, and on the Acoustic
generic wpm model so does a change to a scalar such as ``noiseMax``. See :ref:`the four
outcomes <sensors-common-runtime-updates-outcomes>` and :doc:`the acoustic USD attributes
<../nonvisual/acoustic_wpm/attributes>`.

Mapping transfers data between devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Asking for a CPU mapping of device-resident data blocks until the copy has arrived, and
asking for a device pointer from host-resident data allocates and copies the other way.
Map on the device where you consume the data. See :doc:`Sensor Outputs
<../common/sensor_outputs>` and :ref:`C API <c-api-sensor-types>` and :ref:`Python API
<python-api-render-outputs>`.

Camera startup and render-mode costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Textures stream on demand and the path tracer accumulates samples, so warm-up
frames are the cost of both. The render mode underneath a camera sensor is the
other lever: the Camera generic core model reads only ``HdrColor``, which
``MinimalRendering`` does not produce, so only a path-tracing product can feed
it; :doc:`Render Modes <../cameras/render_modes>` compares the two
path-tracing modes. See :doc:`Configure the Input Image
<../visual/camera_core/howto/input_image>` and the warm-up section of
:doc:`Output Configuration <../common/output_configuration>`.

.. _sensors-troubleshooting-symptoms-diagnostics:
.. _sensors-diagnose-symptom-diagnostics:

Diagnostics
-----------

Configure logging before diagnosing rejected parameters or runtime updates:

- In C, install a callback with ``ovrtx_set_log_callback``. Its filter is a
  comma-separated list of ``<channel prefix>=<level>`` rules; allow errors from
  ``omni.rtx``.
- In Python, set ``RendererConfig.log_level`` and
  ``RendererConfig.log_file_path``. Matching configuration entries are
  available in C. Use ``error`` or a more verbose level to retain rejection
  messages.

Parameter-validation failures and rejected updates are logged as errors. See
:doc:`Renderer Configuration <../../core/renderer_configuration>`, :doc:`logging and error
handling <../../core/async_status_errors>`, :doc:`Sensor Definition Validation
<../common/validation>` and :ref:`rejected updates
<sensors-common-runtime-updates-quiet-refusal>`.

Use output metadata to check the configuration that produced a frame:

- Compare params such as ``coordsType`` and ``frameOfReference`` with the
  authored values on a frame built after the edit. See
  :doc:`Runtime Parameter Updates <../common/runtime_updates>`.
- Request ``MaterialId`` to check resolved material labels on valid core or
  WPM lidar returns. See the :doc:`core lidar Outputs
  <../nonvisual/lidar_core/outputs>` and :doc:`WPM lidar Outputs
  <../nonvisual/lidar_wpm/outputs>` pages, and
  :doc:`Non-Visual Sensor Materials <../../materials/nonvisual_sensor_materials>`.

.. _sensors-troubleshooting-symptoms-generic-wpm:

Generic wpm output is empty or differs from the requested configuration
-----------------------------------------------------------------------

A missing output can mean that the product requests no ``Contributions``
RenderVar, the sensor has no complete pattern, or the configuration was refused.
Use ``OmniGeneralSensor`` with ``OmniSensorGenericWpmAPI``, author every required
pattern array and request one ``Contributions`` output. Start with
:doc:`Set Up a Sensor <../nonvisual/generic_wpm/howto/setup>`.

A zero-length tensor is an empty output, including startup before an accepted
configuration. A tensor with allocated slots whose ``Valid`` entries are all
zero is a completed capture without valid contributions. Geometry intersections
alone do not guarantee positive transport power or receiver visibility. See
:doc:`Outputs <../nonvisual/generic_wpm/outputs>` before reading payloads.

If an edit appears ineffective, read the accepted selectors in output params.
A rejected batch retains its previous accepted controls and patterns, while the
scene keeps advancing. Check array cardinalities, positive counts, active-local
receiver indices and every group on the selected mapping page. A shape or
capacity incompatibility rejects the whole batch. Publish related writes
at one ordinal and finish them before rendering. See
:doc:`Switch Stored Patterns <../nonvisual/generic_wpm/howto/runtime_updates>`.

If distances appear too large, check the emission and receiver origins.
``RoundTripDistanceM`` is total path length. Dividing by two gives direct-return
range only when the ray's emission origin and the receiver origin coincide;
coincident transmitter and receiver origins alone do not ensure this. Check
:ref:`coordinate frames <sensors-nonvisual-generic-wpm-attributes-frames>` and
use receiver-slot order when reading mapped groups.

Related
-------

- :doc:`Limitations <limitations>` — the by-design limits of the models, for the symptoms that are not misconfigurations.
- :doc:`Sensor Definition Validation <../common/validation>` — checking a sensor definition before it runs.
- :doc:`Runtime Parameter Updates <../common/runtime_updates>` — supported edits, rejected updates and batch validation.
- :doc:`Your First Lidar Sensor <../first_sensor>` — the walkthrough from prim to output.
- :doc:`Glossary <../reference/glossary>` — the terms used on this page.
