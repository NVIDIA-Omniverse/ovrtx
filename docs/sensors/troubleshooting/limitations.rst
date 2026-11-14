.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-troubleshooting-limitations:

Limitations
===========

Model constraints and unsupported features, grouped by sensor type. For
configuration errors and corrective actions, see the :doc:`Symptom Index
<symptoms>`.

.. contents:: Models
   :local:
   :depth: 1

.. _sensors-troubleshooting-limitations-every-model:

Shared constraints
------------------

- **Runtime updates.** Runtime-update support varies by attribute and model. Check the model's
  USD Attributes page before changing a running sensor. See
  :doc:`Runtime Parameter Updates <../common/runtime_updates>`.
- **Output selection.** RenderVars select the requested outputs. Channel selection depends on the
  model; some channels are always included. See :ref:`the channels list
  <sensors-common-output-configuration-channels>` in Output Configuration and to
  each model's Outputs page.
- **Point-cloud capacity and count.** A variable-length point tensor's shape is the capacity the sensor may fill, not the
  number of entries it produced; the delivered count arrives separately, in
  ``Counts``. For point clouds, the exception is the Lidar generic wpm model's empty output,
  whose point tensors have zero length. See :doc:`Sensor Outputs
  <../common/sensor_outputs>` and to :doc:`the Lidar generic wpm model's Outputs
  <../nonvisual/lidar_wpm/outputs>`.
- **Mapping status.** Successful mapping does not establish that a frame contains data. Whether a frame is
  empty, partial or complete follows each output's contract. Point clouds report
  ``Counts`` and params; :doc:`Generic wpm Contributions <../nonvisual/generic_wpm/outputs>`
  uses its dimensions and ``Valid``, while :doc:`acoustic SignalWays
  <../nonvisual/acoustic_wpm/outputs>` uses its own params and flags. See
  :doc:`Sensor Outputs <../common/sensor_outputs>`.
- **Mapping mode.** The array mapping mode is for array-backed image outputs. Point-cloud channels
  are linear device memory, so asking for that mode on a ``PointCloud`` output
  fails the whole map rather than falling back. See :doc:`Sensor Outputs
  <../common/sensor_outputs>`.
- **Motion BVH.** Motion BVH, the renderer's support for tracing against a scene that moves
  while a frame is in progress, is chosen when the renderer is created and takes
  effect only on a GPU that supports ray-traced motion. Without it, motion within
  a frame leaves no trace in any sensor's output; the entries below say what each
  model delivers then. See :doc:`Output Configuration
  <../common/output_configuration>` for the modes and which models need it, and
  to :doc:`Driver Requirements <../../driver_requirements>` for the GPUs that
  support it.
- **Device profiles.** Generic models do not reproduce every device feature, calibration process
  or firmware algorithm. Record unsupported behavior in the profile
  assumptions; unrelated attributes cannot reproduce it. See the spec-sheet how-tos of the
  :doc:`Lidar generic core model <../nonvisual/lidar_core/howto/spec_sheet_profile>`,
  the :doc:`Radar generic wpmDmat model
  <../nonvisual/radar_wpm_dmat/howto/spec_sheet_profile>` and the :doc:`Camera
  single-view stereo depth model <../visual/depth_camera/howto/spec_sheet_profile>`.
- **GPU picking.** Picking works only for RenderProducts running on the first CUDA-visible GPU, so
  a product that serves pick queries must be pinned to it with
  ``deviceIds = [0]``. See :doc:`Picking <../../scene/picking>` and to
  device pinning in :doc:`Output Configuration <../common/output_configuration>`.
- **Encrypted parameters.** ``omni:sensor:encryption:params``, brought by the ``OmniSensorEncryptionAPI``
  that every generic sensor schema prepends, is not read by the models. The authored
  attributes determine the active configuration. See
  :doc:`Sensor Configuration <../common/sensor_configuration>`.

.. _sensors-troubleshooting-limitations-lidar-core:

Lidar generic core model
------------------------

- **Scan type.** ``omni:sensor:Core:scanType`` is fixed once the model is built. An edit to the
  other scanning principle is refused together with the rest of that update;
  author it before the sensor starts producing, and recreate the sensor to change
  it. See :doc:`USD Attributes <../nonvisual/lidar_core/attributes>`.
- **Ray type.** ``omni:sensor:Core:rayType`` cannot move between ``IDEALIZED`` and a beam ray
  type on a running sensor. Recreate the sensor to change it. See :doc:`USD
  Attributes <../nonvisual/lidar_core/attributes>`.
- **Minimum scan rate.** A scheduled scan slower than 0.466 Hz is refused, because the per-point
  time offset is a signed 32-bit nanosecond count and cannot span a longer scan.
  See :ref:`the minimum scan rate <sensors-lidar-min-scan-rate>`.
- **Unsupported attributes.** These declared attributes have no effect:
  ``omni:sensor:Core:emitterStatesFile`` is not supported, so emitter states are
  authored on the prim; ``omni:sensor:Core:rangeResolutionM`` changes no
  delivered coordinate, and ``rangeAccuracyM`` is the simulated range
  uncertainty. See :doc:`USD Attributes <../nonvisual/lidar_core/attributes>`.
- **Motion without motion BVH.** Without the motion BVH the model keeps producing points, each traced from the
  sensor's pose at the end of its frame against a scene that does not move, so
  they carry no motion effects. See :doc:`Motion Artifacts
  <../nonvisual/lidar_core/howto/motion_artifacts>`.
- **Beam sampling.** A beam ray type, ``GAUSSIAN_BEAM`` or ``UNIFORM_BEAM``, covers a surface in
  discrete steps: partial coverage at an edge changes the returned beam
  fraction stepwise, and a Gaussian beam weights the center of its
  footprint more than its rim. See :doc:`Tune Intensity and Point Drops
  <../nonvisual/lidar_core/howto/intensity>`.
- **Transmission.** Transmission does not refract the ray: it continues straight through the
  surface. Keeping the return from behind such a surface generally
  means raising ``maxReturns``. See :doc:`USD Attributes
  <../nonvisual/lidar_core/attributes>`.
- **Weather and atmosphere.** The model simulates no weather or atmosphere: returns are not attenuated by
  rain, fog, haze or snow, weather produces no return of its own, and there is
  no background light. Every scan is traced through a clear atmosphere, and the
  scene's geometry and materials determine the returns. See
  :doc:`the model overview <../nonvisual/lidar_core/index>` for what the model
  does simulate.

.. _sensors-troubleshooting-limitations-lidar-wpm:

Lidar generic wpm model
-----------------------

- **Minimum scan rate.** Keep the scan rate at or above about 0.47 Hz: ``TimeOffsetNs`` is a signed
  32-bit nanosecond count and cannot represent a point fired more than about
  2.147 s into a scan. See :doc:`Outputs <../nonvisual/lidar_wpm/outputs>`.
- **Return count.** The return index, ``EchoId``, is one byte, so ``omni:sensor:LidarWpm:maxReturns``
  is at most 255, and at most 8 in the two direct return-processing modes. Refer
  to :doc:`USD Attributes <../nonvisual/lidar_wpm/attributes>`.
- **Tiled configuration.** A RenderProduct that tiles several of these sensors runs one profile, read from
  the first sensor; the attributes of the others are not read. See :doc:`USD
  Attributes <../nonvisual/lidar_wpm/attributes>`.
- **Output capacity.** The point capacity of a product, the kept emitter rows times ``maxReturns``
  times the number of tiles, may not exceed 2147483647 in compact output or
  4294967295 in dense output, and in ``waveform`` mode the kept rows times the
  tiles times ``sparseTofBinCapacity`` may not exceed 4294967295 either. See
  :doc:`USD Attributes <../nonvisual/lidar_wpm/attributes>`.
- **Transmission.** A path may continue through a transmissive surface such as glass or water, and
  outside the direct return modes the straight connection from a bounce back to
  the receiver may cross one transmissive surface, attenuated by it. Anything
  behind such a surface is returned only in ``waveform`` mode, and through at
  most one surface. See :doc:`Choose a Return-Processing Mode
  <../nonvisual/lidar_wpm/howto/return_processing>`.

.. _sensors-troubleshooting-limitations-radar:

Radar generic wpmDmat model
---------------------------

- **Detection capacity.** A scan delivers at most 2500 detections. Additional detections are dropped;
  the output has no saturation indicator. See :doc:`Outputs
  <../nonvisual/radar_wpm_dmat/outputs>`.
- **Per-detection timing.** A radar frame carries no per-detection timing: each scan is simulated as one
  instant, and ``TimeOffsetNs`` is zero for every entry. See :doc:`Outputs
  <../nonvisual/radar_wpm_dmat/outputs>`.
- **Motion without motion BVH.** Without the motion BVH a radar still runs, tracing each scan from the sensor's
  pose at the scan's acquisition time, but nothing moves within a frame; a moving
  radar's
  radial velocities still include its own movement. See :doc:`Simulate
  Moving Targets <../nonvisual/radar_wpm_dmat/howto/moving_targets>`.
- **Motion compensation.** The model has no motion-compensation attribute: motion effects, radial
  velocity above all, come from the renderer's motion BVH. See :doc:`USD
  Attributes <../nonvisual/radar_wpm_dmat/attributes>`.
- **Propagation limits.** The propagation limits other than ``traceTreeDepth`` are fixed by the model
  and have no attribute; the far distance is the largest ``maxRangeM`` among
  the sensor's scan configurations. See :doc:`USD Attributes
  <../nonvisual/radar_wpm_dmat/attributes>`.
- **CFAR dimensions.** One CFAR dimensionality governs every ``FAST`` scan: ``cfarMode`` is a
  sensor-level attribute, so a sensor whose ``FAST`` scans want different
  dimensionalities cannot express that, and a ``WAVEFORM`` scan always runs the
  four-dimensional CFAR whatever it says. See :doc:`USD Attributes
  <../nonvisual/radar_wpm_dmat/attributes>`.
- **Processing mode.** Every scan of one sensor uses the same ``datacubeMode``: the model does not
  support mixing ``FAST`` and ``WAVEFORM`` scans on one prim. See
  :ref:`which mode reads what <sensors-nonvisual-radar-attributes-mode-split>`.
- **Unused decay attribute.** ``exponentialDecayFactor`` is accepted on every scan configuration and does not
  change the output in ovrtx; its row in :doc:`Sensor API Schemas
  <../reference/schemas>` says so.

.. _sensors-troubleshooting-limitations-acoustic:

Acoustic generic wpm model
--------------------------

- **Envelope length.** Each signal way has a fixed 320-sample envelope. In the basic mode that is about 5.6 m of
  range at the default ``sampleDuration``, and a longer sample duration reaches
  further at a coarser resolution. See :doc:`Outputs
  <../nonvisual/acoustic_wpm/outputs>`.
- **Output layout.** ``SignalWays`` is not a point cloud: it has no ``Counts`` channel, it always
  carries all six of its channels, and its ``VALID`` bit marks a signal way
  rather than a point. See :doc:`Outputs <../nonvisual/acoustic_wpm/outputs>`.
- **Interference-mode controls.** In the interference mode the pulse power, gain curve, directivity fit and
  close-range boost are fixed by the model and no noise is added; the
  attributes that act in the basic mode only are listed under :ref:`what each
  mode reads <sensors-nonvisual-acoustic-attributes-mode-reads>`.
- **Motion BVH.** Motion BVH is required to produce echoes. The output has no diagnostic
  parameter identifying a disabled motion BVH. See
  :doc:`Outputs <../nonvisual/acoustic_wpm/outputs>` for the rule and to
  :doc:`Set Up an Acoustic Sensor <../nonvisual/acoustic_wpm/howto/set_up_sensor>`
  for the renderer creation.
- **Propagation limits.** How near a surface may be hit (no hit nearer than 5 mm along a path and no
  first hit nearer than 10 cm to the mount), how far a pulse is followed (20 m)
  and how close a path must pass a receiving mount to count are fixed by the
  model, and they are not configurable. ``traceTreeDepth`` controls the number of
  material interactions. See :ref:`Ray tracing
  <sensors-nonvisual-acoustic-attributes-ray-tracing>`.

.. _sensors-troubleshooting-limitations-cameras:

Cameras
-------

- **Light path expressions.** A RenderProduct can request at most nine light-path-expression (LPE)
  RenderVars, and LPE outputs are supported only in ``PathTracing``. Of the light
  markers, only area (``La``) and environment (``Le``) lights are produced;
  contributions served from the radiance cache are left out of LPE outputs unless
  radiance caching is disabled; and volume scattering is classified as glossy.
  See :doc:`Light Path Expressions <../cameras/light_path_expressions>`.
- **LUT resolution.** Lookup-table projection needs lookup textures at or above the output
  resolution; lower-resolution textures show artifacts at larger output
  resolutions. See :doc:`Lens Calibration <../cameras/lens_calibration>`.
- **Spectral materials.** Spectral rendering has no spectral material response: material colors are
  uplifted from RGB to the spectral domain during rendering. See
  :doc:`Spectral Rendering <../cameras/render_modes/spectral_rendering>`.
- **Rolling shutter.** A rolling shutter samples each line at one instant, at the end of its exposure
  interval; motion within a line's interval is not integrated into motion blur.
  At most two exposures are in flight per camera, so for a camera with an
  authored frame rate keep the total exposure span,
  ``(lineCount - 1) * lineOffset + lineExposure`` where ``lineCount`` is the
  output resolution along the scan direction, at or below two frame intervals.
  See :doc:`Rolling Shutter <../cameras/rolling_shutter>`.
- **Camera partition isolation.** Enabling ``showAllPartitionsByDefault``
  allows geometry from other environments to appear in cameras assigned to a
  partition, even when the environments do not overlap. See :ref:`Viewing all partitions
  <sensors-common-scene-partitions-render-settings>` for the setting and workaround.
- **Non-camera scene partitions.** ``OmniLidar``, ``OmniRadar`` and ``OmniAcoustic`` cannot select a named scene
  partition. With ``showAllPartitionsByDefault = false``, their rays see only
  unpartitioned geometry; with ``true``, they can see all partitions without
  environment isolation. See :ref:`Non-camera sensors
  <sensors-cameras-scene-partitions-non-camera-sensors>`.
- **Neural-reconstruction partitions.** Scene partitions do not isolate neural-reconstruction volumes, whose
  compositing does not filter by the camera's partition. See :doc:`Scene Partitions
  <../cameras/scene_partitions>`.
- **Minimal-mode color output.** ``MinimalRendering`` renders its shaded image only into the 8-bit
  ``LdrColor``; it produces no ``HdrColor``. See :ref:`the output tables
  <camera-output-tables>`.
- **Debug views.** Debug views need Real-Time Path Tracing or Path Tracing, and
  ``anyHitCountHeatMap`` exists only in Real-Time Path Tracing. A debug view
  replaces the beauty destination, ``HdrColor`` when both color outputs are
  requested and otherwise the one requested, and creates no RenderVar of its
  own. See :ref:`debug views <sensors-cameras-outputs-debug-views>`.

.. _sensors-troubleshooting-limitations-camera-core:

Camera generic core model
-------------------------

- **Pipeline scope.** The model processes a rendered image. Lens geometry, depth of field,
  exposure time, global illumination, reflections, shadows and denoising are
  renderer responsibilities. Its outputs are images, with no point counts,
  returns or per-point timestamps. See :doc:`the
  model overview <../visual/camera_core/index>`.
- **Input image.** The model consumes exactly one input, the linear high-dynamic-range render
  ``HdrColor``. The tone-mapped 8-bit ``LdrColor`` output is not an input to it.
  See :doc:`Outputs <../visual/camera_core/outputs>`.
- **Tiled configuration.** A RenderProduct that renders several cameras into one frame runs one pipeline,
  with the settings of the first camera. See :doc:`Outputs
  <../visual/camera_core/outputs>`.
- **CFA label.** The color filter array semantic token is a label recording which mosaic the
  authored weights represent; it changes no pixel. See :doc:`USD Attributes
  <../visual/camera_core/attributes>`.
- **ISP program.** The ISP stage runs a program you supply, and the schema default is empty, so
  until you author one the post-ISP outputs carry no processed image. See
  :doc:`Compand to a RAW Format and Run the ISP
  <../visual/camera_core/howto/companding_and_isp>`.
- **Companding range.** The full pipeline requires the companding stage to produce 16-bit codes: a
  companding curve whose largest output exceeds 65535 is rejected and the
  pipeline does not build. The pre-ISP pipeline has no such constraint. See
  :ref:`Stay within 16 bits
  <sensors-visual-camera-core-howto-companding-and-isp-16bit-gate>`.
- **Noise models.** Only photon shot noise and dark shot noise are modeled. Spatial noise, that is
  fixed-pattern noise, photo-response non-uniformity (PRNU) and dark-signal
  non-uniformity (DSNU), is not simulated. See :doc:`USD Attributes
  <../visual/camera_core/attributes>`.
- **Unused color-correction controls.** Three color-correction controls, ``colorCorrectionRedBlueSwap``,
  ``colorCorrectionOutputFloat16`` and ``colorCorrectionOutputFloat32``, are
  not used. The stage always writes four-component 16-bit float output. See :doc:`USD Attributes
  <../visual/camera_core/attributes>`.

.. _sensors-troubleshooting-limitations-depth-camera:

Camera single-view stereo depth model
-------------------------------------

- **Stereo simulation.** The model performs no stereo matching, renders no second view, adds no timing
  of its own and applies no scene-unit conversion. See :doc:`the model
  overview <../visual/depth_camera/index>`.
- **Validity.** There is no validity channel. A zero distance marks a pixel without a
  valid distance. See :doc:`Outputs <../visual/depth_camera/outputs>`.

.. _sensors-troubleshooting-limitations-generic-wpm:

Generic wpm model
-----------------

- Output consists of scalar path contributions. There is no detector model,
  coherent phase or polarization, FMCW processing, beamforming or sensor-noise
  model. Supply application-specific processing or choose a specialized sensor
  model. Mechanical propagation is not a waveform, a selectable-medium model
  or an elastic-wave solver.
- A capture traces the complete selected pattern. Firing offsets are motion
  sample times, not an external trigger or a scheduler that spreads a scan over
  multiple frames. See :ref:`firing times
  <sensors-nonvisual-generic-wpm-attributes-timing>`.
- Patterns specify poses and firing times, not arbitrary gain tables, per-ray
  weights or custom payloads. Gaussian spread chooses sample directions;
  ``sourceDivergence`` controls propagation separately.
- A configured capture must fit the contribution capacity. Receiver groups
  contain at most 255 slots; bloom radius is at most 7 and bounce depth at most
  255. See :doc:`USD Attributes <../nonvisual/generic_wpm/attributes>` for the
  complete bounds and compatibility rules, and :ref:`capacity
  <sensors-nonvisual-generic-wpm-outputs-capacity>` for storage cost.
- Raw output includes invalid slots. Read ``Valid`` before every payload and
  do not interpret scalar transport power as calibrated detector power. See
  :doc:`Outputs <../nonvisual/generic_wpm/outputs>` for units, frames and limits
  on converting total path distance to range.

Related
-------

- :doc:`Symptom Index <symptoms>` — what to check when an output is empty, wrong or missing.
- :doc:`Runtime Parameter Updates <../common/runtime_updates>` — what a running sensor accepts, refuses and holds fixed.
- :doc:`Sensor Outputs <../common/sensor_outputs>` — reading the composite output, with capacity, counts, status and mapping modes.
- :doc:`Non-Visual Sensor Materials <../../materials/nonvisual_sensor_materials>` — the non-visual material labels and how to author them.
- :doc:`Glossary <../reference/glossary>` — the terms this page uses.
