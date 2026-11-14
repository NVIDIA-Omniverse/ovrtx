.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-reference-glossary:
.. _sensors-ref-glossary:

Glossary
========

Definitions of terms used in the sensor documentation. Follow the links for
model-specific behavior and examples. Entries are alphabetical within each
section; **Scope** identifies the relevant modality, or **—** for shared terms.

.. contents:: On this page
   :local:
   :depth: 1

Requesting and authoring
------------------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 22 12 66

   * - Term
     - Scope
     - Meaning
   * - **AOV**
     - —
     - Arbitrary output variable: a single-tensor output a RenderProduct requests
       through one RenderVar, such as ``LdrColor``. A camera product delivers its
       images as AOVs. See :doc:`../common/output_configuration`.
   * - **Channel**
     - —
     - One named tensor inside a composite output, with its own dtype, shape and
       units. Three other senses of the word are in use; refer to
       :ref:`the note below <sensors-reference-glossary-channel-senses>`.
   * - **Composite output**
     - —
     - An output containing named tensors (channels) and metadata (params), such as ``PointCloud``,
       ``SignalWays`` or ``Contributions``. Also called an output container; either collection can be empty. See
       :doc:`../common/sensor_outputs`, :ref:`C API <c-api-sensor-types>`, :ref:`Python API
       <python-api-render-outputs>`.
   * - **Element**
     - Generic wpm
     - One transmitter, receiver or ray within a pattern. An element index is
       distinct from the index selecting a stored pattern. See
       :ref:`Patterns and selection <sensors-nonvisual-generic-wpm-attributes-patterns>`.
   * - **Mapping page**
     - Generic wpm
     - A stored collection of ordered receiver groups used by ``map``
       connectivity. See :ref:`Receiver mapping
       <sensors-nonvisual-generic-wpm-attributes-mapping>`.
   * - **Pattern and family row**
     - Generic wpm
     - A pattern is one stored alternative for ``tx``, ``rx`` or ``ray``. Its
       index selects a role's ``patternTypes`` entry; its family row counts only
       preceding entries of that same family. See
       :doc:`USD Attributes <../nonvisual/generic_wpm/attributes>`.
   * - **Profile**
     - —
     - Attribute values that configure a generic sensor model to represent a particular device.
       Profiles are typically derived from specifications and checked against measurements or a
       known scene. ``omni:sensor:marketName`` identifies the device. See :doc:`Lidar generic core
       model <../nonvisual/lidar_core/howto/spec_sheet_profile>`, :doc:`Radar generic wpmDmat model
       <../nonvisual/radar_wpm_dmat/howto/spec_sheet_profile>`, :doc:`Camera single-view stereo
       depth model <../visual/depth_camera/howto/spec_sheet_profile>`, :doc:`tutorials
       <../nonvisual/lidar_core/tutorials/index>`.
   * - **Render var output**
     - —
     - The data delivered for one RenderVar in a frame, keyed by its prim path. It is either a
       single tensor or a composite output. Mapping yields ``ovrtx_render_var_output_t`` in C or
       ``MappedRenderVar`` in Python. See :doc:`../common/sensor_outputs`.
   * - **RenderProduct**
     - —
     - A USD prim that selects sensors through ``rel camera`` and requested outputs through ``rel
       orderedVars``. Cameras, WPM lidars and the Generic wpm model support multiple sensors as tiles in one product. See
       :doc:`../common/output_configuration`.
   * - **RenderVar**
     - —
     - A USD prim that requests one output through its ``sourceName``, such as ``LdrColor``,
       ``PointCloud``, ``SignalWays`` or ``Contributions``. See :doc:`../common/output_configuration`.
   * - **Runtime stage**
     - —
     - The scene representation held by ovstage and read by the renderer. It can be populated from
       USD; runtime attribute updates write to this stage. See :doc:`ovstage Integration
       <../../core/ovstage_integration>`, :doc:`../common/runtime_updates`.
   * - **Sensor introspection utility**
     - —
     - A utility that validates a sensor definition against the model's rules before rendering and
       reports rejected values. Available for both lidar models, radar, acoustic and Generic wpm sensors;
       unavailable for the camera models. See :doc:`../common/validation`.
   * - **Sensor model**
     - —
     - The simulation selected by a prim's type and applied API schema. It defines attribute
       behavior and available outputs; identical attribute names in different models need not have
       identical meanings. See :doc:`../common/sensor_configuration`.
   * - **Sensor prim**
     - —
     - A USD prim representing a sensor and its configuration: a Camera, OmniLidar, OmniRadar,
       OmniAcoustic or OmniGeneralSensor prim, with any applicable sensor API schemas. See
       :doc:`../common/sensor_configuration`.
   * - **Single-tensor output**
     - —
     - An output that is one tensor and carries no params, such as the camera
       image ``LdrColor``. It can be consumed directly as a DLPack tensor; in
       Python the mapping itself is the tensor. See
       :doc:`../common/sensor_outputs`.

.. _sensors-reference-glossary-channel-senses:
.. _sensors-glossary-channel-senses:

The word **channel** has four uses:

- **Output tensor:** a named tensor in a composite output, selected by the
  RenderVar's ``channels`` list where supported.
- **Lidar detector label:** the authored identifier reported by ``ChannelId``.
  See :ref:`the Lidar generic core model <sensors-nonvisual-lidar-core-outputs-channel-id>` and
  :ref:`the Lidar generic wpm model <sensors-nonvisual-lidar-wpm-outputs-channel-id>`.
- **Acoustic channel id:** a firing-event label used with the receiver index
  to select a signal way. See
  :ref:`acoustic channels <sensors-nonvisual-acoustic-outputs-channel-meanings>`.
- **Image component:** R, G, B or A. Camera documentation uses *component*
  for this meaning.

In WPM lidar, a *receiver* is the detector side of an emitter row, not a unique
channel id. Two retained rows with the same ``channelId`` count as two
receivers in ``receiversPerTile``. See
:ref:`scan schedule <sensors-nonvisual-lidar-wpm-attributes-scan-schedule>`.

Reading the output
------------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 22 12 66

   * - Term
     - Scope
     - Meaning
   * - **Capacity**
     - Point clouds
     - The allocated size of a per-point output tensor, shown as ``Nmax`` and reported by
       ``maxPoints``. It can exceed the number of entries delivered in a frame. See
       :doc:`../common/sensor_outputs`.
   * - **Capture**
     - —
     - One camera exposure or sensor scan. ``omni:sensor:frameRate`` schedules captures; supported
       models can deliver intermediate results through ``partialOutputs``. See
       :doc:`../common/multi_rate`.
   * - **Contribution slot**
     - Generic wpm
     - One dense slot for a tile, transmitter, emitted ray, bounce and receiver
       slot. Read its payload only when ``Valid`` is nonzero. See
       :doc:`Outputs <../nonvisual/generic_wpm/outputs>`.
   * - **Count**
     - Point clouds
     - The delivered-entry count, ``Counts[0]``. It bounds per-entry reads; the tensor capacity and
       the length of ``Counts`` do not. See :ref:`Delivered-entry count
       <sensors-common-sensor-outputs-counts-bound>`, :doc:`../common/sensor_outputs`.
   * - **Detection**
     - —
     - One delivered point-cloud entry. Radar detections are extracted from the detection matrix by
       CFAR. See :doc:`the radar Outputs page <../nonvisual/radar_wpm_dmat/outputs>`, :ref:`Detection processing <sensors-nonvisual-radar-index-detections>`.
   * - .. _sensors-reference-glossary-dlpack:

       **DLPack**
     - —
     - A tensor-exchange convention describing a data pointer, shape, data type and device.
       Compatible consumers can share tensor storage without copying. Strides are measured in
       elements, not bytes. See :doc:`../common/sensor_outputs`.
   * - **Frame**
     - —
     - One delivery of a RenderProduct's outputs. A step can return zero or more frames. Depending
       on the model and delivery settings, a frame may contain a partial scan or a complete scan.
       Also used for a coordinate frame. See :doc:`../common/multi_rate`, :doc:`Configure Lidar
       Output <../nonvisual/lidar_core/howto/output_shaping>`, :ref:`the note below
       <sensors-reference-glossary-frame-senses>`.
   * - **Frame rate**
     - —
     - The scheduled capture rate, authored as rational Hz in ``omni:sensor:frameRate``. Also called
       scan rate or capture rate; its reciprocal is the capture period. Internal firing and sampling
       rates can differ. See :ref:`Frame rate, step and delivery
       <sensors-common-multi-rate-frame-rate>`, :doc:`../common/multi_rate`.
   * - **Mapping**
     - —
     - Making an output's tensors readable. After a step, a render var output is
       mapped on the host (CPU) or on a CUDA device before application code
       reads its data; params are CPU-resident whatever the mapping. See
       :doc:`../common/sensor_outputs`.
   * - .. _sensors-reference-glossary-param:

       **Param**
     - —
     - Named, typed output metadata such as ``frameId``, ``timestampNs`` or ``coordsType``. Params
       are CPU-resident DLPack tensors and can contain scalars, vectors or matrices. See
       :doc:`../common/sensor_outputs`.
   * - **Point cloud**
     - —
     - A set of points and associated data. Lidar and radar deliver it as a composite ``PointCloud``
       output containing coordinates and model-specific channels. See
       :doc:`../common/sensor_outputs`.
   * - **Receiver slot**
     - Generic wpm
     - A position in an ordered receiver group, rather than a receiver's global
       index. Repeated receiver indices retain distinct slots. See
       :doc:`Outputs <../nonvisual/generic_wpm/outputs>`.
   * - **Signal way**
     - Acoustic
     - The acoustic envelope and metadata for one receiving mount and channel id, delivered in
       ``SignalWays``. Events from different transmitters can share a signal way. See :doc:`the
       acoustic Outputs page <../nonvisual/acoustic_wpm/outputs>`.
   * - .. _sensors-reference-glossary-stable-id:

       **Stable id**
     - Camera, Lidar
     - The renderer's 128-bit identifier of a prim or geometry instance, carried
       as four ``uint32`` words that are read together: per pixel in
       ``StableIdSegmentation`` and ``SemanticInstanceSegmentation``, per point
       in the Lidar generic core model's ``ObjectId`` channel. ``StableIdMap``
       and ``StableIdMapDeltas`` map each id to its prim path;
       ``NonStableInstanceSegmentation`` carries a runtime index instead, which
       can change as the scene changes. Stable ids are active only while some
       RenderProduct in the scene requests a stable-id output. See
       :ref:`Identifier maps and deltas <sensors-cameras-howto-decode-outputs-identifiers>`
       on :doc:`Decoding camera outputs <../cameras/decoding_outputs>` and to
       :ref:`ObjectId <sensors-nonvisual-lidar-core-outputs-object-id>` on the
       Lidar generic core model's Outputs page.
   * - **Step**
     - —
     - One renderer call that advances simulation by ``delta_time`` and requests outputs for a set
       of RenderProducts. Include every active product on every step. See :ref:`Step every
       RenderProduct on every step <sensors-common-multi-rate-stepping>`,
       :doc:`../common/multi_rate`.
   * - **Step result**
     - —
     - The outputs returned by a step: zero or more frames per requested RenderProduct, with one
       output per RenderVar in each frame. See :ref:`Frame delivery <sensors-common-sensor-outputs-frames>`, :doc:`../common/sensor_outputs`.
   * - **Tensor**
     - —
     - A named multi-dimensional array carrying the bulk data of an output,
       described through DLPack. A variable-sized tensor's shape is its capacity,
       and a scalar is a one-element tensor of shape ``[1]``. See
       :doc:`../common/sensor_outputs`.

.. _sensors-reference-glossary-frame-senses:

A **coordinate frame** defines the axes used to express a measurement:

- **Sensor frame:** the ISO 8855 convention used by composite sensor outputs.
- **World or custom frame:** selected through ``outputFrameOfReference`` and
  reported by the ``frameOfReference`` output param.
- **Application frame:** the application's axes; ``modelToAppTransform`` maps
  the sensor frame into them.

See :ref:`sensor coordinates <sensors-common-sensor-outputs-sensor-frame>`
and :doc:`Sensor Configuration <../common/sensor_configuration>` for the
relationship to the sensor prim's axes.

Scanning and propagation terms
------------------------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 22 12 66

   * - Term
     - Scope
     - Meaning
   * - **Acquisition time**
     - Radar
     - The instant at which the Radar generic wpmDmat model acquires a scan:
       its scan time plus that scan's ``timeOffsetUsec`` delay, reported as the
       frame's ``timestampNs``. See :ref:`the frame rate
       <sensors-nonvisual-radar-attributes-frame-rate>` on the model's USD
       attributes page.
   * - .. _sensors-reference-glossary-aliasing:

       **Aliasing**
     - Radar
     - The folding of a contribution whose range, angle or radial velocity lies
       outside a scan's unambiguous interval back into that interval, so that
       the detection appears inside that interval at a plausible value other
       than the true one: a target beyond
       ``maxRangeM`` comes back at a shorter range. ``enableRangeAliasing`` and
       ``enAngAliasing`` switch it on for range and for angle in a ``FAST``
       scan, which always folds radial velocity. See
       :ref:`Aliasing and the unambiguous intervals <sensors-nonvisual-radar-attributes-aliasing>`
       on the Radar generic wpmDmat model's USD attributes page. Camera
       *anti-aliasing*, the smoothing of jagged edges in a rendered image, is
       unrelated; refer to *DLSS* under *Camera terms*.
   * - **Beam divergence**
     - Lidar
     - The opening angle of a beam in each axis: how fast its width grows with
       distance. You author either the divergence or the beam waist, and the
       model derives the other. See :ref:`Divergence or beam waist
       <sensors-intensity-divergence-or-waist>` on :doc:`Tune Intensity and
       Point Drops <../nonvisual/lidar_core/howto/intensity>`.
   * - **Beam quality factor (M²)**
     - Lidar
     - How far a real beam departs from an ideal Gaussian beam: ``1`` is the
       ideal, and a larger value spreads the beam faster for the same waist.
       Authored as ``Msquared``. See
       :doc:`Tune Intensity and Point Drops
       <../nonvisual/lidar_core/howto/intensity>`.
   * - **Beam waist**
     - Lidar
     - The beam's radius at its focus, in each axis: the narrowest point, from
       which the beam diverges. See :doc:`Tune Intensity and Point Drops
       <../nonvisual/lidar_core/howto/intensity>`.
   * - **Boresight**
     - Lidar, Radar
     - The reference direction at zero azimuth and elevation, used to measure angular limits and
       antenna or detector response. See :ref:`Field of view, range and resolution
       <sensors-nonvisual-radar-attributes-fov>`, :ref:`Detector and detection thresholds
       <sensors-nonvisual-lidar-wpm-attributes-detector>`.
   * - **Chirp**
     - Radar
     - One frequency-swept pulse of a ``WAVEFORM`` scan's waveform, described by
       ``chirpDuration``, ``chirpBandwidth`` and the selected
       ``chirpRepetitionTimeSequence`` entry. Refer
       to :ref:`Waveform processing <sensors-nonvisual-radar-attributes-waveform>`
       on the Radar generic wpmDmat model's USD attributes page.
   * - **Contribution**
     - —
     - Energy arriving at one receiver along one propagation path in a WPM model. A surface hit
       alone is not a contribution; paths with multiple interactions can produce contributions at
       different arrival times. See :ref:`Detection processing <sensors-wpm-contribution>`.
       For the Generic wpm model's raw path records, see
       :ref:`Paths and contributions <sensors-nonvisual-generic-wpm-outputs-paths>`.
   * - **Detection floor**
     - Lidar
     - The processed signal level below which the Lidar generic core model drops
       a return, set by a reflectance calibration pair on its USD attributes.
       See :doc:`Tune Intensity and Point Drops
       <../nonvisual/lidar_core/howto/intensity>`.
   * - **Doppler**
     - Radar
     - The frequency shift used to measure radial motion between sensor and target.
       ``RadialVelocityMs`` reports signed radial velocity; approaching targets have negative
       values. Motion perpendicular to the line of sight has no radial component. See
       :ref:`RadialVelocityMs <sensors-nonvisual-radar-outputs-radial-velocity>`, :doc:`Simulate
       Moving Targets <../nonvisual/radar_wpm_dmat/howto/moving_targets>`.
   * - **Echo**
     - Lidar, Acoustic
     - For the lidar models, one of several returns from the same firing,
       numbered by ``EchoId``; refer to the Outputs pages of the :doc:`Lidar
       generic core model <../nonvisual/lidar_core/outputs>` and the
       :doc:`Lidar generic wpm model <../nonvisual/lidar_wpm/outputs>`. For the
       Acoustic generic wpm model, one arrival of the transmitted pulse at a
       receiving mount, recorded as amplitude over time in that mount's signal
       way; the sampled series is the *echo envelope*, and an echo from a path
       that bounced more than once is a *ghost echo*. See :ref:`Simulation <sensors-nonvisual-acoustic-what-it-hears>` on the model's
       overview.
   * - **Emitter**
     - Lidar
     - One laser in a firing pattern: offset from the tick in azimuth and in fire
       time, aimed at an absolute elevation. See
       :doc:`Configure a Firing Pattern
       <../nonvisual/lidar_core/howto/firing_pattern>` for the Lidar generic core
       model. The Lidar generic wpm model calls the same thing an *emitter row*
       of its firing pattern; refer to
       :doc:`its counterpart <../nonvisual/lidar_wpm/howto/firing_pattern>`.
   * - **Emitter state**
     - Lidar
     - An instance of the core lidar emitter-state multi-apply API, containing per-emitter arrays
       for one application of the firing pattern. The WPM lidar equivalent is a firing-pattern
       instance. See :doc:`Configure a Firing Pattern
       <../nonvisual/lidar_core/howto/firing_pattern>`, :doc:`its counterpart
       <../nonvisual/lidar_wpm/howto/firing_pattern>`.
   * - **Field of view (FoV)**
     - —
     - The observable region a sensor covers. The Lidar generic core model
       authors it as how near and how far a return may be plus, for a rotary
       sensor, which slice of the rotation counts; refer to
       :doc:`Constrain the Field of View
       <../nonvisual/lidar_core/howto/field_of_view>`. The Radar generic wpmDmat
       model authors angular limits per scan configuration; refer to
       :doc:`its USD attributes <../nonvisual/radar_wpm_dmat/attributes>`.
   * - **Firing event**
     - Acoustic
     - An acoustic transmission defined by its time within the cycle, transmitting mount, receiver
       group and channel id. See :ref:`Mounts, receiver groups and firing sequences
       <sensors-nonvisual-acoustic-attributes-topology>`, :doc:`Lay Out a Transducer Array
       <../nonvisual/acoustic_wpm/howto/array_topology>`.
   * - **Firing pattern**
     - Lidar
     - The directions and timing of lidar emissions. Core lidar combines scan and tick settings with
       emitter-state API instances. WPM lidar uses firing-pattern API instances, such as ``p001``,
       whose emitter rows fire during one tick. See :doc:`Configure a Firing Pattern
       <../nonvisual/lidar_core/howto/firing_pattern>`, :doc:`its counterpart
       <../nonvisual/lidar_wpm/howto/firing_pattern>`.
   * - **Firing sequence**
     - Acoustic
     - A repeating cycle of timed firing events, each naming a transmitting
       mount, a receiver group and a channel id. See :ref:`Mounts, receiver
       groups and firing sequences <sensors-nonvisual-acoustic-attributes-topology>`
       on the model's USD attributes page.
   * - .. _sensors-reference-glossary-half-angle:

       **Half-angle**
     - Lidar, Radar
     - An angular limit measured from boresight to one edge of the field of
       view, so that the total field of view is twice the value: the Radar
       generic wpmDmat model's ``maxAzAngDeg`` and ``maxElAngDeg`` are
       half-angles, and so are the limits of the Lidar generic wpm model's
       detector field of view. See
       :ref:`the half-angles <sensors-nonvisual-radar-attributes-half-angles>` on the
       Radar generic wpmDmat model's USD attributes page
       and to :ref:`Detector and detection thresholds <sensors-nonvisual-lidar-wpm-attributes-detector>`
       on the Lidar generic wpm model's USD attributes page.
   * - **Intensity processing mode**
     - Lidar
     - The Lidar generic core model's choice of what the reported ``Intensity``
       number means: raw, normalized or corrected. See
       :ref:`Intensity processing <sensors-intensity-processing>` on :doc:`Tune
       Intensity and Point Drops <../nonvisual/lidar_core/howto/intensity>`.
   * - .. _sensors-reference-glossary-membrane:

       **Membrane**
     - Acoustic
     - The vibrating surface of an acoustic transducer. ``omni:sensor:WpmAcoustic:membraneDiameter``
       specifies the receiving membrane diameter. See :doc:`the model's overview
       <../nonvisual/acoustic_wpm/index>`, :ref:`Physical sensor
       <sensors-nonvisual-acoustic-attributes-physical-sensor>`.
   * - **Motion artifacts**
     - —
     - Distortion caused by sensor or scene motion during a scan, because measurements are taken at
       different times. See :doc:`Motion Artifacts
       <../nonvisual/lidar_core/howto/motion_artifacts>`.
   * - **Motion BVH**
     - —
     - Renderer support for tracing against sensor and scene transforms that vary during a scan. The
       mode is selected when creating the renderer and cannot be changed afterwards. See
       :doc:`../common/output_configuration`.
   * - **Motion compensation**
     - —
     - Also called deskewing: transforming measurements using their timestamps and sensor motion
       into a common reference pose. Core lidar selects it with ``outputMotionCompensationState =
       COMPENSATED``; WPM lidar uses ``true``. The output param ``motionCompensationState`` reports
       the applied mode. See :doc:`Motion Artifacts
       <../nonvisual/lidar_core/howto/motion_artifacts>`, :doc:`Lidar generic core model
       <../nonvisual/lidar_core/outputs>`, :doc:`Lidar generic wpm model
       <../nonvisual/lidar_wpm/outputs>`.
   * - **Mount**
     - Acoustic
     - An acoustic transducer with a position and rotation in the sensor frame. Firing sequences
       determine whether it transmits, receives or both. See :ref:`Mounts, receiver groups and
       firing sequences <sensors-nonvisual-acoustic-attributes-topology>`, :doc:`Lay Out a
       Transducer Array <../nonvisual/acoustic_wpm/howto/array_topology>`.
   * - **Multipath**
     - —
     - Propagation along indirect reflected paths. These can produce ghost detections with different
       apparent ranges, angles, velocities or strengths. See :doc:`the radar USD attributes
       <../nonvisual/radar_wpm_dmat/attributes>`.
   * - **Partial beam coverage**
     - Lidar
     - A beam of finite width landing partly on an object and partly past it at
       an edge, so that one firing returns from two distances; only the beam ray
       types reproduce it. See :ref:`Ray type
       <sensors-nonvisual-lidar-core-attributes-ray-type>` on the Lidar generic
       core model's USD attributes page.
   * - **Pending scan**
     - Radar
     - The scan configuration whose turn is next in the Radar generic wpmDmat
       model's cycle; a frame that fires no scan leaves it unchanged. See
       :ref:`Scan configuration sequence
       <sensors-nonvisual-radar-howto-scan-configurations-cycle>`.
   * - **Ray bundle**
     - Generic wpm
     - An ordered ray pattern reused at each transmitter pose. See
       :ref:`Patterns and selection <sensors-nonvisual-generic-wpm-attributes-patterns>`.
   * - **Receiver group**
     - Acoustic, Generic wpm
     - - Acoustic: the set of mounts that listen together to a firing event,
         named by their mount indices. See :ref:`Mounts, receiver groups and
         firing sequences <sensors-nonvisual-acoustic-attributes-topology>`
         on the model's USD attributes page and :doc:`Lay Out a Transducer Array
         <../nonvisual/acoustic_wpm/howto/array_topology>`.
       - Generic wpm: an ordered list of indices into the active receiver
         pattern. See :ref:`Receiver mapping
         <sensors-nonvisual-generic-wpm-attributes-mapping>`.
   * - **Region of interest (ROI)**
     - Lidar
     - The azimuth interval in which ROI-tagged emitter states of a multi-state
       firing pattern participate; it is not the field of view. See
       :doc:`Constrain the Field of View
       <../nonvisual/lidar_core/howto/field_of_view>` and
       :doc:`the model's USD attributes <../nonvisual/lidar_core/attributes>`.
   * - **Return**
     - Lidar, Radar
     - For the lidar models, a detection: one point; a firing may produce
       several or none. See the Outputs pages of the :doc:`Lidar generic
       core model <../nonvisual/lidar_core/outputs>` and the :doc:`Lidar
       generic wpm model <../nonvisual/lidar_wpm/outputs>`. In radar prose a
       return is the reflected signal, whose strength and RCS a detection
       reports; the delivered unit there is a detection (:doc:`the radar
       Outputs page <../nonvisual/radar_wpm_dmat/outputs>`).
   * - **Scan**
     - —
     - One complete pass of a sensor pattern, scheduled at ``omni:sensor:frameRate``. In radar
       configuration, also an applied scan-configuration instance such as ``s001``. See
       :doc:`../common/multi_rate`, :doc:`Run More Than One Scan Pattern
       <../nonvisual/radar_wpm_dmat/howto/scan_configurations>`.
   * - **Scan time**
     - Radar
     - One point of the Radar generic wpmDmat model's scan grid:
       ``omni:sensor:startTime`` plus a whole number of scan periods. Each scan
       time serves one scan. See :ref:`the frame rate
       <sensors-nonvisual-radar-attributes-frame-rate>`.
   * - **Sweep**
     - —
     - The same pass as a scan, named to stress that it takes time. See
       :ref:`the note below <sensors-reference-glossary-scan-vs-sweep>`.
   * - **Tick**
     - Lidar
     - One application of the firing pattern, and the Lidar generic core model's
       unit of both time and angle; refer to
       :doc:`the model's USD attributes <../nonvisual/lidar_core/attributes>`.
       The Lidar generic wpm model's tick is the same unit; refer to
       :ref:`its scan schedule <sensors-nonvisual-lidar-wpm-attributes-scan-schedule>`.
   * - .. _sensors-reference-glossary-tile:

       **Tile**
     - —
     - One of several sensors that share a RenderProduct through its
       ``rel camera`` list: a camera product splits its output image into
       tiles, one per camera, and a Lidar generic wpm model product lays every
       tile's points out in one aggregate point cloud; refer to
       :doc:`its Tile Lidars page <../nonvisual/lidar_wpm/howto/tile_lidars>`.
       The Lidar generic core model does not tile: it takes one RenderProduct
       per sensor
       (:ref:`one RenderProduct per sensor <sensors-nonvisual-lidar-core-attributes-one-product-per-sensor>`).
       See :doc:`../common/output_configuration` for independent products.
   * - **Trace tree depth**
     - —
     - The maximum number of material interactions followed along a propagation path. Greater depth
       allows more indirect paths and increases tracing cost. See :ref:`Radar generic wpmDmat model
       <sensors-nonvisual-radar-attributes-trace-depth>`, :ref:`Acoustic generic wpm model
       <sensors-nonvisual-acoustic-attributes-ray-tracing>`, :ref:`Choose a Return-Processing Mode
       <sensors-lidar-wpm-trace-depth>`.

.. _sensors-reference-glossary-scan-vs-sweep:
.. _sensors-glossary-scan-vs-sweep:

**Scan** and **sweep** refer to the same pass of a firing pattern. *Sweep*
emphasizes measurements taken over time; an instantaneous scan, such as
lidar with ``instantLidar`` enabled, does not sweep through the scene.

Camera terms
------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 22 12 66

   * - Term
     - Scope
     - Meaning
   * - **Alignment**
     - Camera
     - Which bit of the output integer a companded code's most significant bit
       occupies. See :ref:`Choose the alignment
       <sensors-visual-camera-core-howto-companding-and-isp-alignment>` on the
       companding how-to.
   * - **Bayer pattern**
     - Camera
     - A 2×2 color filter array with two green, one red and one blue filter;
       RGGB, GRBG and BGGR name where each sits. The Camera generic core
       model's default weights form a GRBG pattern. See
       :doc:`../visual/camera_core/howto/color_filter_array`.
   * - **Beauty output**
     - Camera
     - The final shaded image a RenderProduct delivers, as ``HdrColor`` and
       ``LdrColor``; a debug view replaces it. See
       :ref:`the camera output tables <camera-output-tables>`.
   * - **Camera responsivity**
     - Camera
     - Spectral sensitivity curves for the camera color components.
       ``PhysicalCameraResponsivityAPI`` uses these curves in place of the CIE standard observer
       during spectral rendering. See :doc:`../cameras/render_modes/spectral_rendering`.
   * - **CIE standard observer**
     - Camera
     - The color-matching functions that turn a spectrum into CIE XYZ, and so
       into an image, in spectral rendering. The renderer offers the 1931
       2-degree observer, the default, and the 1964 10-degree observer. See
       :doc:`../cameras/render_modes/spectral_rendering`.
   * - **Color filter array (CFA)**
     - Camera
     - Optical filters over sensor photosites, typically in a repeating 2×2 pattern. Each photosite
       records one filtered value, producing a single-component mosaic. The Camera generic core
       model specifies the pattern with four RGB weight triples. See
       :doc:`../visual/camera_core/howto/color_filter_array`.
   * - **Companding**
     - Camera
     - Compressing internal sensor values into a narrower RAW transport format using a
       piecewise-linear curve, then expanding them in the ISP. The curve controls how output codes
       are distributed across the signal range. See
       :doc:`../visual/camera_core/howto/companding_and_isp`, :ref:`Companding
       <sensors-visual-camera-core-attributes-companding>`.
   * - **Dark shot noise**
     - Camera
     - Noise from thermally generated charge carriers, present even without incident light. See
       :ref:`Sensor noise <sensors-visual-camera-core-attributes-noise>`.
   * - **Debug view**
     - Camera
     - A diagnostic quantity, G-buffer data or a heat map, routed into the beauty
       output in place of the shaded image; selected on the RenderProduct with
       ``omni:rtx:debug:view:target``. See :doc:`../cameras/outputs`.
   * - **Demosaicing**
     - Camera
     - Reconstructing three color components per pixel from the one component the
       mosaic recorded at each photosite; a step of the ISP. See
       :doc:`../visual/camera_core/howto/companding_and_isp`.
   * - **Denoiser**
     - Camera
     - A filter that removes the sampling noise of a path-traced image.
       Real-Time Path Tracing denoises every frame, Path Tracing has its own
       denoising settings, and in Minimal mode DLSS Ray Reconstruction denoises.
       See :doc:`../cameras/render_modes`.
   * - **Disparity**
     - Camera
     - The horizontal pixel shift between two imagers' views of one point, which
       a stereo camera turns into distance; the Camera single-view stereo depth
       model computes it from rendered distance and applies its noise and
       quantization to it. See :doc:`the model's overview
       <../visual/depth_camera/index>`.
   * - **Distortion coefficients**
     - Camera
     - The numbers that describe how a real lens bends the ideal pinhole
       mapping; which coefficients each OpenCV schema takes is on
       :doc:`../cameras/lens_calibration`.
   * - **DLSS**
     - Camera
     - Deep Learning Super Sampling, the image reconstruction Minimal mode offers:
       DLSS Super Resolution (DLSS-SR) upscales and anti-aliases, DLSS Ray
       Reconstruction (DLSS-RR) upscales, anti-aliases and denoises, and DLAA
       anti-aliases at native resolution without upscaling. See
       :doc:`../cameras/render_modes/minimal`.
   * - **Firefly**
     - Camera
     - A bright, isolated pixel produced by a rare high-energy light path. The
       firefly filter clamps per-sample intensity to suppress them, at some cost
       in energy. See
       :doc:`../cameras/render_modes/real_time_path_tracing`.
   * - **Fixed-pattern noise**
     - Camera
     - Per-photosite offsets and gains that do not change from frame to frame:
       photo-response non-uniformity (PRNU) in gain and dark-signal
       non-uniformity (DSNU) in offset. The Camera generic core model does not
       simulate them; refer to :ref:`Sensor noise
       <sensors-visual-camera-core-attributes-noise>` on its USD attributes
       page.
   * - **G-buffer**
     - Camera
     - The per-pixel geometry and material data (depth, normal, position,
       texture coordinates and the like) the renderer keeps before shading;
       debug views expose it. See :doc:`../cameras/outputs`.
   * - **Global illumination**
     - Camera
     - Light that reaches a surface indirectly, after bouncing off other
       surfaces, in addition to direct light; the path-tracing modes compute it.
       See :doc:`../cameras/render_modes`.
   * - **Global shutter**
     - Camera
     - A shutter that exposes all photosites over the same time interval. See
       :doc:`../cameras/rolling_shutter`.
   * - **HDR and LDR**
     - Camera
     - High dynamic range: linear color with a range wider than a display can
       show, as the ``float16`` ``HdrColor`` output. Low dynamic range:
       display-ready color, as the tone-mapped 8-bit sRGB ``LdrColor`` output.
       See :ref:`the camera output tables <camera-output-tables>`.
   * - **HDR zone**
     - Camera
     - One of the gain ranges an HDR image sensor captures and stitches into one
       code space; the Camera generic core model's noise follows the zones.
       See :ref:`Sensor noise <sensors-visual-camera-core-attributes-noise>`
       on its USD attributes page.
   * - **Illuminant**
     - Camera
     - A light source's spectrum. In spectral rendering, ``physical:illuminant`` selects the
       rendering-space white, a blackbody, CIE daylight or custom spectral samples. See
       :doc:`../cameras/render_modes/spectral_rendering`.
   * - **Image signal processor (ISP)**
     - Camera
     - The processing chain that turns RAW sensor codes into a viewable image:
       decompanding, demosaicing, denoising and conversion to a working color
       space. In the Camera generic core model it runs a program you supply.
       See :doc:`../visual/camera_core/howto/companding_and_isp`.
   * - **Interpupillary distance (IPD)**
     - Camera
     - The separation of the two eyes of a stereo camera, in meters; the
       omni-directional stereo projection renders one eye at a time. See
       :ref:`Omni-directional stereo <sensors-cameras-lens-calibration-ods>` on
       :doc:`../cameras/lens_calibration`.
   * - **Intrinsics**
     - Camera
     - The parameters of a camera's projection: the focal lengths ``fx`` and
       ``fy`` and the principal point ``cx`` and ``cy``, in pixels of the
       calibration ``imageSize``, together with the distortion coefficients.
       See :doc:`../cameras/lens_calibration`.
   * - **Knee point**
     - Camera
     - One ``(x, y)`` pair of a companding curve: an internal value and the
       output code it maps to. See
       :doc:`../visual/camera_core/howto/companding_and_isp`.
   * - **Light path expression (LPE)**
     - Camera
     - An expression that selects which light-transport paths accumulate into a
       RenderVar, splitting a Path Tracing image into passes such as diffuse
       reflection, glossy reflection, emission or caustics. See
       :doc:`../cameras/light_path_expressions`.
   * - **Lookup-table (LUT) projection**
     - Camera
     - A non-parametric lens model defined by two lookup textures: one gives the
       ray direction for every image position, the other the image-plane
       position a ray direction is emitted from. See
       :ref:`Generalized Projection <sensors-cameras-lens-calibration-lut>`.
   * - **Mosaic**
     - Camera
     - The single-component image a color filter array produces, one filtered
       value per photosite; defined under *Color filter array (CFA)*.
   * - **Omni-directional stereo (ODS)**
     - Camera
     - A 360-degree stereo projection rendered one eye at a time, with separate
       left- and right-eye cameras. See
       :ref:`Omni-directional stereo <sensors-cameras-lens-calibration-ods>` on
       :doc:`../cameras/lens_calibration`.
   * - **Path tracing**
     - Camera
     - Rendering by tracing light paths through the scene with random sampling
       and accumulating samples per pixel until the image converges. Path
       Tracing mode does it progressively toward a sample limit; Real-Time
       Path Tracing adds caching and denoising for real-time rates. See
       :doc:`../cameras/render_modes`.
   * - **Pedestal**
     - Camera
     - A constant offset added before or after the companding curve so that
       noise around black does not clip at zero. See
       :doc:`../visual/camera_core/howto/companding_and_isp`.
   * - **Photon shot noise**
     - Camera
     - Noise caused by random photon arrivals. Absolute noise increases with signal level, while
       noise relative to the signal decreases. See :ref:`Sensor noise
       <sensors-visual-camera-core-attributes-noise>`.
   * - **Primary output and tap**
     - Camera
     - Camera generic core output categories: two primary images, at least one of which each product
       must request, and five optional diagnostic outputs from intermediate pipeline stages. See
       :ref:`Primary outputs <sensors-visual-camera-core-outputs-primary-outputs>`, :ref:`Diagnostic
       taps <sensors-visual-camera-core-outputs-taps>`, :doc:`../visual/camera_core/outputs`.
   * - **Principal point**
     - Camera
     - The pixel where the optical axis meets the image: ``cx`` and ``cy`` in
       calibration pixels. See :doc:`../cameras/lens_calibration`.
   * - **RAW8, RAW10, RAW12, RAW14**
     - Camera
     - The transport formats of an image sensor, named by bits per sample. The
       companding curve maps the internal range onto one of them, and the
       alignment says where the code sits in the output integer. The Camera
       generic core model's ``ispSmodelSensorRawFormat`` also names ``RAW20``
       and ``RAW24``, which do not fit the 16-bit unsigned integer its ISP reads.
       See
       :doc:`../visual/camera_core/howto/companding_and_isp`.
   * - **RCCB, RCCC, CCCC**
     - Camera
     - Color filter arrays with clear, unfiltered positions. Red-Clear-Clear-Blue
       trades color separation for low-light sensitivity; RCCC and CCCC go
       further, toward a monochrome sensor. See
       :doc:`../visual/camera_core/howto/color_filter_array`.
   * - **Rolling shutter**
     - Camera
     - A shutter that offsets the sample time across the image, one row or
       column at a time, so moving straight edges appear curved or skewed. Refer
       to :doc:`../cameras/rolling_shutter`.
   * - **Samples per pixel**
     - Camera
     - The number of light paths accumulated for each pixel. Path Tracing
       accumulates toward ``omni:rtx:pt:samplesPerPixel`` before returning
       output. See :doc:`../cameras/render_modes/path_tracing`.
   * - **Spectral rendering**
     - Camera
     - Light transport sampled over wavelengths and converted to RGB using an observer or camera
       responsivity. This accounts for spectral variation in lighting and sensor response. See
       :doc:`../cameras/render_modes/spectral_rendering`.
   * - **Subsurface scattering (SSS)**
     - Camera
     - Light entering a translucent material, scattering inside it and leaving
       at a different point; the ``maxVolumeBounces`` settings bound its
       bounces. See :doc:`../cameras/render_modes/path_tracing`.
   * - **Tone mapping**
     - Camera
     - Compressing high-dynamic-range color into the display range; it produces
       the sRGB ``LdrColor`` image from the linear scene radiance. See
       :doc:`../cameras/outputs`.

Abbreviations
-------------

.. csv-table::
   :header: "Short", "Full term", "Scope", "Meaning"
   :widths: 12, 26, 12, 50
   :class: compact-table

   "**AOV**", "Arbitrary output variable", "—", "Defined under *Requesting and authoring*."
   "**CFA**", "Color filter array", "Camera", "Defined under *Camera terms*."
   "**CFAR**", "Constant false alarm rate", "Radar", "The algorithm that extracts detections from the detection matrix while holding the false-alarm rate constant, by comparing a candidate cell against neighboring test cells and excluding guard cells around it. See :doc:`the radar USD attributes <../nonvisual/radar_wpm_dmat/attributes>`."
   "**dBsm**", "Decibel square meters", "Radar", "The logarithmic unit radar cross section is reported in."
   "**DLAA, DLSS, DLSS-RR, DLSS-SR**", "Deep Learning Anti-Aliasing; Deep Learning Super Sampling and its Ray Reconstruction and Super Resolution variants", "Camera", "Defined under *Camera terms* (DLSS)."
   "**DMAT**", "Detection matrix", "Radar", "The discretized representation of radar returns: a range, velocity, azimuth and elevation datacube populated with ray-tracing contributions, from which CFAR extracts detections. See :doc:`the Radar generic wpmDmat model <../nonvisual/radar_wpm_dmat/index>`."
   "**DSNU**", "Dark-signal non-uniformity", "Camera", "Defined under *Camera terms* (Fixed-pattern noise)."
   "**FMCW**", "Frequency-modulated continuous wave", "Radar", "A waveform whose frequency varies over time; the Generic wpm model does not perform FMCW processing. See :ref:`model limits <sensors-troubleshooting-limitations-generic-wpm>`."
   "**FoV**", "Field of view", "—", "Defined under *Scanning and propagation terms*."
   "**HDR, LDR**", "High dynamic range, low dynamic range", "Camera", "Defined under *Camera terms*."
   "**IPD**", "Interpupillary distance", "Camera", "Defined under *Camera terms*."
   "**ISO 8855**", "The ISO road-vehicle coordinate convention", "—", "The coordinate convention used as the sensor frame of the composite outputs. See :ref:`The sensor frame <sensors-common-sensor-outputs-sensor-frame>` on :doc:`../common/sensor_outputs` for the statement and the figure."
   "**I/Q**", "In-phase and quadrature", "Signals", "Two components representing a coherent signal. Generic wpm scalar contributions do not supply coherent phase. See :ref:`model limits <sensors-troubleshooting-limitations-generic-wpm>`."
   "**ISP**", "Image signal processor", "Camera", "Defined under *Camera terms*."
   "**LPE**", "Light path expression", "Camera", "Defined under *Camera terms*."
   "**LUT**", "Lookup table", "Camera", "Defined under *Camera terms* (Lookup-table projection)."
   "**M²**", "Beam quality factor", "Lidar", "Defined under *Scanning and propagation terms*."
   "**MIMO**", "Multiple input, multiple output", "Radar", "A radar with several transmitting and receiving elements: a real aperture of 1 Tx and *N* Rx, or a virtual aperture of *M* Tx and *N* Rx that behaves as 1 Tx and *M* × *N* Rx. See :ref:`the receiving aperture <sensors-nonvisual-radar-attributes-aperture>`."
   "**ODS**", "Omni-directional stereo", "Camera", "Defined under *Camera terms*."
   "**PRNU**", "Photo-response non-uniformity", "Camera", "Defined under *Camera terms* (Fixed-pattern noise)."
   "**RCS**", "Radar cross section", "Radar", "A measure of how detectable an object is by radar, reported per detection in dBsm. See :doc:`the radar Outputs page <../nonvisual/radar_wpm_dmat/outputs>`."
   "**ROI**", "Region of interest", "Lidar", "Defined under *Scanning and propagation terms*."
   "**RTPT**", "Real-Time Path Tracing", "Camera", "The default render mode: path tracing with caching and denoising for real-time rates. See :doc:`../cameras/render_modes/real_time_path_tracing`."
   "**Rx**", "Receiver", "—", "The receiving side of a sensor: in radar, the receiving antenna system; in the Acoustic generic wpm model, the mounts a receiver group names in its ``receiverIndices``; in the Lidar generic wpm model, the detector side of one emitter row of the firing schedule (refer to the channel note under *Requesting and authoring*)."
   "**SPG**", "Sensor Processing Graph", "Camera", "Processing graph used by camera sensor pipelines."
   "**SSS**", "Subsurface scattering", "Camera", "Defined under *Camera terms*."
   "**Tx**", "Transmitter", "—", "The transmitting side of a sensor: in radar, the transmitting antenna system; in the Acoustic generic wpm model, the mount a firing event names in ``txSensorId``."
   "**USD**", "Universal Scene Description", "—", "The scene description the sensor prim, its API schemas and its RenderProduct are authored in."
   "**USS**", "Ultrasonic sensor", "Acoustic", "An acoustic sensor operating at ultrasonic frequencies. See :doc:`the overview of the Acoustic generic wpm model <../nonvisual/acoustic_wpm/index>`."
   "**WPM**", "Wave propagation model", "—", "A physics-based wave-propagation approach to sensor simulation, named in the Lidar generic wpm model, the Radar generic wpmDmat model, the Acoustic generic wpm model and the Generic wpm model; each model's pages describe what it does to the signal."

Related
-------

- :doc:`Output Configuration <../common/output_configuration>` — RenderProducts, RenderVars, channels and the renderer options sensors depend on.
- :doc:`Sensor Outputs <../common/sensor_outputs>` — mapping, tensors, params, capacity and count, and the sensor frame.
- :doc:`Sensor Configuration <../common/sensor_configuration>` — prims, applied schemas and the shared attributes.
- :doc:`Sensor Scheduling <../common/multi_rate>` — frame rate, captures, steps and the delivery policy.
- :ref:`C API <c-api-sensor-types>` and :ref:`Python API <python-api-render-outputs>` — the C and Python definition of the output container.
- :doc:`Sensor API Schemas <schemas>` — every attribute of every sensor schema, with its type, default and doc string.
- :doc:`Symptom Index <../troubleshooting/symptoms>` — diagnosing sensor output problems.
