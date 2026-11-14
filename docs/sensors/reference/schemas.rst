.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

..
   Generated from schemas/omni_sensors/schema.usda by
   schemas/omni_sensors/generate-schema-docs.py.
   Edits made here are overwritten on the next run.

.. _sensors-reference-schemas:

Sensor API Schemas
==================

Array defaults longer than three entries are truncated for display with ``...``. Read the schema files shipped in the ovrtx package for the complete defaults.

Typed Schemas
-------------

OmniSensor
~~~~~~~~~~

Transformable sensor

Describes minimal set of common sensor params (extrinsics). Mainly for
semantic purposes and for identifying sensors programmatically on the stage.

**Inherits from**: Xformable

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``rel proxyPrim``
     - The proxyPrim relationship allows us to link a prim whose purpose is "render" to its (single target) purpose="proxy" prim. This is entirely optional, but can be useful in several scenarios:
       * In a pipeline that does pruning (for complexity management) by deactivating prims composed from asset references, when we deactivate a purpose="render" prim, we will be able to discover and additionally deactivate its associated purpose="proxy" prim, so that preview renders reflect the pruning accurately.
       * DCC importers may be able to make more aggressive optimizations for interactive processing and display if they can discover the proxy for a given render prim.
       * With a little more work, a Hydra-based application will be able to map a picked proxy prim back to its render geometry for selection.
       .. note::
       It is only valid to author the proxyPrim relationship on prims whose purpose is "render".
   * - ``token purpose = "default"``
     - Allowed tokens: "default", "render", "proxy", "guide"

       Purpose is a classification of geometry into categories that can each be independently included or excluded from traversals of prims on a stage, such as rendering or bounding-box computation traversals.
       See for more detail about how purpose is computed and used.
   * - ``token visibility = "inherited"``
     - Allowed tokens: "inherited", "invisible"

       Visibility is meant to be the simplest form of "pruning" visibility that is supported by most DCC apps. Visibility is animatable, allowing a sub-tree of geometry to be present for some segment of a shot, and absent from others; unlike the action of deactivating geometry prims, invisible geometry is still available for inspection, for positioning, for defining volumes, etc.
   * - ``token[] xformOpOrder``
     - Encodes the sequence of transformation operations in the order in which they should be pushed onto a transform stack while visiting a UsdStage's prims in a graph traversal that will effect the desired positioning for this prim and its descendant prims.
       You should rarely, if ever, need to manipulate this attribute directly. It is managed by the AddXformOp(), SetResetXformStack(), and SetXformOpOrder(), and consulted by GetOrderedXformOps() and GetLocalTransformation().

OmniRadar
~~~~~~~~~

Typed schema representing a radar sensor, has all attributes of its base class

**Inherits from**: OmniSensor

OmniLidar
~~~~~~~~~

Typed schema representing a lidar sensor, has all attributes of its base class

**Inherits from**: OmniSensor

OmniAcoustic
~~~~~~~~~~~~

Typed schema representing an acoustic sensor, has all attributes of its base class

**Inherits from**: OmniSensor

OmniIDS
~~~~~~~

**Inherits from**: OmniSensor

OmniSensorSample
~~~~~~~~~~~~~~~~

**Inherits from**: OmniSensor

OmniGeneralSensor
~~~~~~~~~~~~~~~~~

Fallback schema for sensor types we haven't considered yet, but a user might want to specify, e.g. gravity wave sensor, has all attributes of its base class (currently not in use)

**Inherits from**: OmniSensor

OmniTime
~~~~~~~~

**Inherits from**: Typed

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``timecode omni:time = 0``
     -

API Schemas
-----------

OmniSensorAPI
~~~~~~~~~~~~~

This schema defines attributes necessary to specify a sensor model as a trio of model name, version and vendor.
Model implementations are expected to prepend this schema and set those attributes to the model they represent.

**Inherits from**: APISchemaBase

**Can only apply to**: OmniSensor, Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:marketName = ""``
     - Specifies the sensor market marketName for this sensor.
   * - ``string omni:sensor:modelName = ""``
     - Specifies the model to be used for evaluating this sensor. The special string 'latest' is reserved as a hint to the simulation to use the latest best model for this marketName.
   * - ``string omni:sensor:modelVersion = "latest"``
     - Specifies the model behavior version to be used for this sensor. This value must be an unsigned
       integer string counting from '0', such as '0' or '1', or the special value 'latest', that selects the latest supported model behavior version for that schema.
       The schema/API version is selected by the applied API schema class name: an un-suffixed class selects schema version 1,
       while a '_N' suffix selects schema version N. Model behavior versions are scoped to their schema version and restart at '0' when the schema version is bumped.
   * - ``string omni:sensor:modelVendor = ""``
     - Specifies the vendor that authored the given model.
   * - ``double2 omni:sensor:frameRate = (0, 1)``
     - Frame rate of the sensor as a rational number (numerator, denominator) in Hz.
       The rate in Hz = numerator / denominator.
       A value of (0, 1) means unset: a camera then renders on every step, and any other sensor is captured on the renderer's default schedule, as :ref:`Frame rate, step and delivery <sensors-common-multi-rate-frame-rate>` describes. Note: this is not the tick rate of the sensor, which can be anything.
       The frameRate is the actual rate at which the sensor completes frames/scans.
   * - ``double2 omni:sensor:startTime = (0, 1)``
     - Start time offset of the sensor as a rational number (numerator, denominator) in seconds. The time offset = numerator / denominator.
   * - ``int omni:sensor:frameLimit = -1``
     - Frame limit of the sensor.
       The sensor produces only frames numbered below the limit; -1 means unlimited and 0 pauses the sensor.
       Frame numbers follow the sensor schedule and keep advancing while frames are not produced, so raising
       the limit resumes on the current frame number, not where the sensor stopped.
       A legacy uint value keeps its former meaning, where 0 is unlimited.

OmniSensorEncryptionAPI
~~~~~~~~~~~~~~~~~~~~~~~

This schema defines attributes necessary to specify encrypted parameters for a sensor model.

**Inherits from**: APISchemaBase

**Can only apply to**: OmniSensor

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``uchar[] omni:sensor:encryption:params = []``
     - Blob of bytes that represents an encrypted parameters that the specified model will understand. If filled, the decrypted parameters trump any parameters specified in USD.

RenderVarChannelsAPI
~~~~~~~~~~~~~~~~~~~~

API schema declaring the `channels` selector on a RenderVar.

The `channels` attribute selects which output channels a producer should
populate for this RenderVar. Valid values depend on the RenderVar's
`sourceName` and are interpreted by the producing plugin:

- Lidar granular PointCloud:
    "Coordinates", "Intensity", "TimeOffsetNs", "Flags"

- Radar granular PointCloud:
    "Coordinates", "RCS", "TimeOffsetNs", "RadialVelocityMs", "Flags"

- Acoustic granular outputs:
    "rtxsensorMetadata", "transmitterIds", "receiverIds", "channelIds",
    "amplitudes", and other modality-specific names

- Generic WPM `Contributions`:
    an empty list publishes the twelve channels of the record; a non-empty
    list publishes exactly those plus "Valid", which indexes the rest.
    Listing "HitVerticesM" or "GeometryAreaM2" enables the hit-geometry
    raygen variant and publishes both

The attribute is typed as `token[]` to match the runtime contract: the
Fabric read path resolves `channels` as a token array only, so a `string[]`
value silently yields no channels. Allowed values are documented here rather
than enforced with `allowedTokens` because the valid set depends on
`sourceName`.

**Inherits from**: APISchemaBase

**Can only apply to**: RenderVar

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token[] channels = []``
     - Selector for which channels the producing plugin should populate
       for this RenderVar. See the schema-level documentation for the set of
       valid values per `sourceName`.

OmniSensorGenericLidarCoreEmitterStateAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic lidar emitter state

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:Core:emitterState

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float[] azimuthDeg = [-3, -3, -3, ...]``
     - Azimuth of the emitters in degrees; Has numberOfEmitters elements; Changing the number of elements at runtime is not supported.
   * - ``float[] elevationDeg = [-15, -14.19, -13.39, ...]``
     - Elevation of the emitters in degrees; Has numberOfEmitters elements; Changing the number of elements at runtime is not supported.
   * - ``uint[] fireTimeNs = [0, 0, 0, ...]``
     - Fire time of the emitters in ns -- delta to the azimuth tick start time; Has numberOfEmitters elements; Changing the number of elements at runtime is not supported.
   * - ``uint[] channelId = [1, 2, 3, ...]``
     - Channel id of each emitter as the vendor numbers it; any set of ids is accepted and the ChannelId output reports them unchanged, the count of distinct ids must not exceed numberOfChannels; Has numberOfEmitters elements; Changing the number of elements at runtime is not supported.
   * - ``uint[] rangeId = []``
     - Corresponding range id of the emitters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] vertOffsetM = []``
     - Vertical offset of the emitters in meters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] horOffsetM = []``
     - Horizontal offset of the emitters in meters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] distanceCorrectionM = []``
     - Distance correction of the emitters in meters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] focalDistM = []``
     - Focal distance of the emitters in meters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] focalSlope = []``
     - Focal slope of the emitters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``float[] emitterPeakPowerW = []``
     - Peak power of the emitters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``uint[] bank = []``
     - Bank/line of the emitters; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``bool[] roi = []``
     - Is the emitter part of the ROI; Has numberOfEmitters elements or empty; Changing the number of elements at runtime is not supported.
   * - ``bool isROIState = false``
     - Is the emitter state a ROI state

OmniSensorGenericLidarCoreAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic lidar using Core model

**Inherits from**: APISchemaBase

**Can only apply to**: OmniLidar

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI
   - OmniSensorGenericLidarCoreEmitterStateAPI:s001

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "LidarCore"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (10, 1)``
     - Complete scan/frame rate of the sensor as rational Hz (numerator, denominator). For example, (10, 1) means 10 complete scans per second.
   * - ``token omni:sensor:Core:elementsCoordsType = "SPHERICAL"``
     - Allowed tokens: "CARTESIAN", "SPHERICAL"

       sets the desired coordinate system for the output basic elements (not auxiliary data))
   * - ``token omni:sensor:Core:outputMotionCompensationState = "NONCOMPENSATED"``
     - Allowed tokens: "NONCOMPENSATED", "COMPENSATED"

       Sets the desired output motion compensation state for all outputs, including auxiliary data. NONCOMPENSATED reports detections without per-point compensation for sensor motion during the scan. COMPENSATED uses point timestamps and sensor motion to compensate output coordinates into the requested output frame. This output setting does not enable renderer Motion BVH by itself.
   * - ``token omni:sensor:Core:outputFrameOfReference = "SENSOR"``
     - Allowed tokens: "SENSOR", "WORLD", "CUSTOM"

       sets the desired frame of reference for all outputs (including auxiliary data)
   * - ``float[] omni:sensor:Core:customFrameOfReferenceTrafo = [0, 0, 0, ...]``
     - used only if outputFrameOfReference = CUSTOM. defines the transformation for the custom frame of reference. structured as [x,y,z,roll,pitch,yaw]
   * - ``bool omni:sensor:Core:includeInvalidPoints = false``
     - when false the model will drop invalid points; Runtime changes not supported, yet.
   * - ``bool omni:sensor:Core:partialOutputs = false``
     - Indicates whether the sensor should produce partial outputs.
       By default (false), the sensor accumulates points and only outputs when the entire scan is complete.
       If true, the sensor will output parts of the scan at every call. The amount of the partial output corresponds to the time span of the call and the frame rate of the sensor.
       Author true explicitly to retain partial-scan output.
   * - ``bool omni:sensor:Core:instantLidar = false``
     - when true the sensor will output a full scan at every frame
   * - ``token omni:sensor:Core:scanType = "ROTARY"``
     - Allowed tokens: "ROTARY", "SOLID_STATE"

       Scanning principle of the sensor; Runtime changes not supported, yet.
   * - ``token omni:sensor:Core:intensityProcessing = "NORMALIZATION"``
     - Allowed tokens: "RAW", "NORMALIZATION", "CORRECTION"

       Intensity processing mode
   * - ``token omni:sensor:Core:rotationDirection = "CW"``
     - Allowed tokens: "CW", "CCW"

       Rotation direction of the sensor -- only for rotary sensors
   * - ``token omni:sensor:Core:rayType = "IDEALIZED"``
     - Allowed tokens: "IDEALIZED", "GAUSSIAN_BEAM", "UNIFORM_BEAM"

       Ray type of the sensor; Runtime changes not supported, yet.
   * - ``float omni:sensor:Core:nearRangeM = 0.3``
     - Minimum range of the sensor in meters
   * - ``float omni:sensor:Core:farRangeM = 200.0``
     - Maximum range of the sensor in meters
   * - ``float omni:sensor:Core:reflectionPowerFraction = 0.5``
     - Fraction of the reflection power for multiple returns.
   * - ``float omni:sensor:Core:transmissionPowerFraction = 1.0``
     - Fraction of the transmission power for multiple returns.
   * - ``float omni:sensor:Core:startAzimuthOffsetDeg = 0.0``
     - Start azimuth offset angle of the sensor in degrees -- in sensor market model frame
   * - ``float omni:sensor:Core:validStartAzimuthDeg = 0.0``
     - Valid start azimuth angle of the sensor in degrees -- in sensor market model frame
   * - ``float omni:sensor:Core:validEndAzimuthDeg = 360.0``
     - Valid end azimuth angle of the sensor in degrees -- in sensor market model frame
   * - ``float omni:sensor:Core:minAzimuthROI = 400.0``
     - Start azimuth of the region-of-interest interval in degrees, in sensor market model frame. Together with maxAzimuthROI, this interval controls where ROI-tagged emitter states participate in a rotary firing pattern; it does not define the general field of view. The default value of 400 indicates that no ROI is configured. If minAzimuthROI > maxAzimuthROI, the interval wraps through 360 degrees.
   * - ``float omni:sensor:Core:maxAzimuthROI = 400.0``
     - End azimuth of the region-of-interest interval in degrees, in sensor market model frame. See minAzimuthROI for how the interval controls ROI-tagged firing patterns.
   * - ``float omni:sensor:Core:rangeResolutionM = 0.004``
     - Distance quantization step in meters used by vendor packet encoders that consume the profile resolution. This attribute does not add random error to the delivered PointCloud coordinates; use rangeAccuracyM for simulated range uncertainty.
   * - ``float omni:sensor:Core:rangeAccuracyM = 0.02``
     - Range error scale in meters. The model uses this to add distance-dependent Gaussian range uncertainty; uncertainty grows with distance relative to farRangeM.
   * - ``float omni:sensor:Core:minDistBetweenEchosM = 0.4``
     - Minimum distance between two resolvable echos in meters
   * - ``float omni:sensor:Core:rangeOffsetM = 0.0``
     - Range for which objects are invisible -- useful for sensors inside objects
   * - ``float omni:sensor:Core:peakPowerW = 10.0``
     - Peak emitted optical power per emitter in watts. It contributes to returned irradiance and intensity processing.
   * - ``float omni:sensor:Core:minReflectance = 0.1``
     - Minimum reflectance value of an object for a guarantueed Pointcloud at minReflectionRange
   * - ``float omni:sensor:Core:minReflectionRangeM = 200.0``
     - Minimum range for a guaranteed detection of an object with minReflectance
   * - ``float omni:sensor:Core:waveLengthNm = 903.0``
     - Emitter wavelength in nanometers. It affects photon/count conversion and material spectral response.
   * - ``uint omni:sensor:Core:pulseTimeNs = 6``
     - Beam pulse duration in nanoseconds. It scales received photon counts and contributes to down-range return separation.
   * - ``float omni:sensor:Core:focusDistM = 0.15``
     - Focus distance of the sensor in meters
   * - ``float omni:sensor:Core:Msquared = 1.4``
     - M squared value of the sensor
   * - ``float omni:sensor:Core:beamWaistHorM = 0.002``
     - Beam waist horizontal of the sensor in meters
   * - ``float omni:sensor:Core:beamWaistVerM = 0.002``
     - Beam waist vertical of the sensor in meters
   * - ``float omni:sensor:Core:divergenceHorDeg = 0.0``
     - Divergence horizontal of the sensor in degrees
   * - ``float omni:sensor:Core:divergenceVerDeg = 0.0``
     - Divergence vertical of the sensor in degrees
   * - ``float omni:sensor:Core:aspectRatio = 1.0``
     - Aspect ratio of the detector
   * - ``float omni:sensor:Core:effectiveApertureSizeM = 0.01``
     - Effective aperture size of the sensor in meters
   * - ``float omni:sensor:Core:quantumEfficiency = 0.9``
     - Quantum efficiency of the detector
   * - ``float omni:sensor:Core:pixelPitch = 40.0``
     - Pixel pitch of the detector
   * - ``float omni:sensor:Core:calibrationGain = 40.0``
     - Calibration gain of the sensor
   * - ``float omni:sensor:Core:bitDepthResolution = 65536.0``
     - Bit depth resolution of the sensor
   * - ``float omni:sensor:Core:rotPatternFiringResDeg = 0.1``
     - Resolution at which the firing patterns are applied in degrees. Only applicable for rotary lidar.
   * - ``uint omni:sensor:Core:numberOfEmitters = 128``
     - Number of emitters of the sensor; Runtime changes not supported, yet.
   * - ``uint omni:sensor:Core:numberOfChannels = 128``
     - Number of channels of the sensor; Runtime changes not supported, yet.
   * - ``uint omni:sensor:Core:maxReturns = 2``
     - Maximum number of returns or detections per channel.
   * - ``float omni:sensor:Core:azimuthErrorMean = 0.0``
     - Mean value of the azimuth error in degrees
   * - ``float omni:sensor:Core:azimuthErrorStd = 0.005``
     - Standard deviation of the azimuth error in degrees
   * - ``float omni:sensor:Core:elevationErrorMean = 0.0``
     - Mean value of the elevation error in degrees
   * - ``float omni:sensor:Core:elevationErrorStd = 0.0``
     - Standard deviation of the elevation error in degrees
   * - ``float[] omni:sensor:Core:originErrorMean = [0.0,0.0,0.0]``
     - Mean value of the origin error in meters
   * - ``float[] omni:sensor:Core:originErrorStd = [0.0,0.0,0.0]``
     - Standard deviation of the origin error in meters
   * - ``token omni:sensor:Core:intensityMappingType = "LINEAR"``
     - Allowed tokens: "LINEAR", "NONLINEAR", "NONLINEAR_ENCODING_ONLY", "NONLINEAR_DECODING_ONLY"

       Intensity mapping type
   * - ``float omni:sensor:Core:intensityScalePercent = 255.0``
     - Intensity scale percent
   * - ``float[] omni:sensor:Core:intensityMappingEncoding = []``
     - Intensity mapping encoding; Changing the number of elements at runtime is not supported.
   * - ``float[] omni:sensor:Core:intensityMappingDecoding = []``
     - Intensity mapping decoding; Changing the number of elements at runtime is not supported.
   * - ``uint omni:sensor:Core:numLines = 0``
     - Number of lines of the sensor; Runtime changes not supported, yet.
   * - ``uint[] omni:sensor:Core:numRaysPerLine = []``
     - Number of points per line of the sensor; Has numLines elements; Changing the number of elements at runtime is not supported.
   * - ``uint omni:sensor:Core:rangeCount = 0``
     - Number of range regions of the emitters
   * - ``float[] omni:sensor:Core:rangesMinM = []``
     - Minimum ranges of the emitters in meters; Has rangeCount elements; Changing the number of elements at runtime is not supported.
   * - ``float[] omni:sensor:Core:rangesMaxM = []``
     - Maximum ranges of the emitters in meters; Has rangeCount elements; Changing the number of elements at runtime is not supported.
   * - ``uint omni:sensor:Core:stateResolutionStep = 1``
     - State resolution step of the sensor -- Handles switching between states
   * - ``string omni:sensor:Core:emitterStatesFile = ""``
     - File containing the emitter states of the sensor; Not supported, yet.
   * - ``uint omni:sensor:Core:tiledSubSampling = 0``
     - Sensor workload should be sub sampled by this factor (e.g. a value of 2 could equal half the rays traced).

OmniSensorGenericLidarWpmFiringPatternAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines one generic WPM lidar firing pattern

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:LidarWpm:firingPattern

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float[] azimuthDeg = [-3, -3, -3, ...]``
     - Azimuth of each firing-pattern emitter row in degrees.
   * - ``float[] elevationDeg = [-15, -14.19, -13.39, ...]``
     - Elevation of each firing-pattern emitter row in degrees.
   * - ``uint[] fireTimeNs = [0, 0, 0, ...]``
     - Fire time of each firing-pattern emitter row in ns relative to the tick start
   * - ``uint[] channelId = [1, 2, 3, ...]``
     - Receiver channel id for each firing-pattern emitter row; any set of ids is accepted and the ChannelId output reports them unchanged
   * - ``uint[] rangeId = []``
     - Range id for each firing-pattern emitter row; empty means default range

OmniSensorGenericLidarWpmAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic lidar using the WPM model

**Inherits from**: APISchemaBase

**Can only apply to**: OmniLidar

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI
   - OmniSensorGenericLidarWpmFiringPatternAPI:p001

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "LidarWpm"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (10, 1)``
     -
   * - ``token omni:sensor:LidarWpm:elementsCoordsType = "SPHERICAL"``
     - Allowed tokens: "CARTESIAN", "SPHERICAL"

       Sets the desired coordinate system for the output elements.
   * - ``bool omni:sensor:LidarWpm:outputMotionCompensationState = false``
     - Enables motion compensation output state.
   * - ``token omni:sensor:LidarWpm:outputFrameOfReference = "SENSOR"``
     - Allowed tokens: "SENSOR", "WORLD", "CUSTOM"

       Sets the desired frame of reference for outputs.
   * - ``float[] omni:sensor:LidarWpm:customFrameOfReferenceTrafo = [0, 0, 0, ...]``
     - Used only if outputFrameOfReference = CUSTOM. Structured as [x,y,z,roll,pitch,yaw].
   * - ``bool omni:sensor:LidarWpm:includeInvalidPoints = false``
     - If false, invalid points are dropped and valid points are published in a stable GPU prefix-compacted range. True publishes the capacity-shaped output with validity carried by Flags.
   * - ``bool omni:sensor:LidarWpm:partialOutputs = false``
     - If true, partial outputs may be emitted before a full frame is complete.
   * - ``bool omni:sensor:LidarWpm:instantLidar = false``
     - If true, all rays are emitted at the frame timestamp.
   * - ``token omni:sensor:LidarWpm:returnProcessingMode = "waveform"``
     - Allowed tokens: "waveform", "directDetector", "directMaterial"

       Return processing pipeline. Direct modes require idealized rays.
   * - ``bool omni:sensor:LidarWpm:useVisualMaterialInputs = false``
     - Enabling WPM visual-material inputs has a significant performance impact and reads visual-material diffuse reflectance, roughness, and shading normal. If false, WPM uses nonvisual/default material inputs.
   * - ``float omni:sensor:LidarWpm:directMaterialReferenceDistanceM = 1.0``
     - Positive physical one-way reference distance in meters for direct-material range attenuation.
   * - ``float omni:sensor:LidarWpm:directMaterialIntensityThreshold = 0.0``
     - Normalized base-intensity threshold for accepting direct-material returns.
   * - ``token omni:sensor:LidarWpm:intensityProcessing = "rangeNormalized"``
     - Allowed tokens: "rangeNormalized", "raw"

       PointCloud intensity processing mode. rangeNormalized reports apparent reflectivity; raw reports the range-dependent normalized detector response.
   * - ``token omni:sensor:LidarWpm:intensityMappingType = "linear"``
     - Allowed tokens: "linear", "nonlinear", "nonlinearEncodingOnly", "nonlinearDecodingOnly"

       Presentation-only PointCloud intensity mapping type.
   * - ``float omni:sensor:LidarWpm:intensityScale = 2.55``
     - Nonnegative output full-scale for PointCloud intensity after processing and mapping.
   * - ``float[] omni:sensor:LidarWpm:intensityMappingEncoding = []``
     - Optional nonlinear encoding lookup values; tables shorter than intensityScale * 100 provide additive corrections, while larger tables replace the base intensity.
   * - ``token omni:sensor:LidarWpm:scanType = "rotary"``
     - Allowed tokens: "rotary", "solidState"

       Scan type of the sensor.
   * - ``token omni:sensor:LidarWpm:rayType = "idealized"``
     - Allowed tokens: "idealized", "gaussianBeam"

       Ray model used by the WPM lidar.
   * - ``float omni:sensor:LidarWpm:nearRangeM = 0.3``
     - Minimum range of the sensor in meters.
   * - ``float omni:sensor:LidarWpm:farRangeM = 200.0``
     - Maximum range of the sensor in meters.
   * - ``float omni:sensor:LidarWpm:startAzimuthOffsetDeg = 0.0``
     - Start azimuth offset angle of the sensor in degrees.
   * - ``float omni:sensor:LidarWpm:validStartAzimuthDeg = 0.0``
     - Valid start azimuth angle of the sensor in degrees.
   * - ``float omni:sensor:LidarWpm:validEndAzimuthDeg = 360.0``
     - Valid end azimuth angle of the sensor in degrees.
   * - ``float omni:sensor:LidarWpm:rotPatternFiringResDeg = 0.1``
     - Resolution at which firing patterns are applied in degrees.
   * - ``uint omni:sensor:LidarWpm:firingPatternDwellTicks = 1``
     - Number of consecutive logical firing ticks for which each firing pattern remains selected before advancing. A rotary tick is one angular firing step; a solid-state tick is one scan.
   * - ``uint omni:sensor:LidarWpm:maxReturns = 2``
     - Maximum number of returns of the sensor.
   * - ``float omni:sensor:LidarWpm:jitterAzimuthMeanDeg = 0.0``
     - Mean noise added to azimuth radial measurements in degrees.
   * - ``float omni:sensor:LidarWpm:jitterAzimuthStdDevDeg = 0.005``
     - Standard deviation of azimuth radial noise at boresight in degrees.
   * - ``float omni:sensor:LidarWpm:jitterElevationMeanDeg = 0.0``
     - Mean noise added to elevation radial measurements in degrees.
   * - ``float omni:sensor:LidarWpm:jitterElevationStdDevDeg = 0.0``
     - Standard deviation of elevation radial noise at boresight in degrees.
   * - ``float omni:sensor:LidarWpm:offsetAzimuthMeanDeg = 0.0``
     - Mean offset added to azimuth radial measurements in degrees.
   * - ``float omni:sensor:LidarWpm:offsetAzimuthStdDevDeg = 0.0``
     - Standard deviation of azimuth radial noise at boresight in degrees.
   * - ``float omni:sensor:LidarWpm:offsetElevationMeanDeg = 0.0``
     - Mean offset added to elevation radial measurements in degrees.
   * - ``float omni:sensor:LidarWpm:offsetElevationStdDevDeg = 0.0``
     - Standard deviation of elevation radial noise at boresight in degrees.
   * - ``float omni:sensor:LidarWpm:peakPowerW = 5.35``
     - Peak power per emitter in watts.
   * - ``float omni:sensor:LidarWpm:waveLengthNm = 903.0``
     - Wavelength of the sensor in nm.
   * - ``uint omni:sensor:LidarWpm:pulseTimeNs = 2``
     - Pulse time of the sensor in ns.
   * - ``float omni:sensor:LidarWpm:focusDistM = 0.15``
     - Focus distance of the sensor in meters.
   * - ``float omni:sensor:LidarWpm:Msquared = 1.4``
     - M squared value of the sensor.
   * - ``float omni:sensor:LidarWpm:beamDivergenceHorDeg = 0.024``
     - Horizontal divergence of the sensor in degrees.
   * - ``float omni:sensor:LidarWpm:beamDivergenceVerDeg = 0.018``
     - Vertical divergence of the sensor in degrees.
   * - ``float omni:sensor:LidarWpm:effectiveApertureSizeM = 0.01``
     - Effective aperture size of the sensor in meters.
   * - ``float omni:sensor:LidarWpm:quantumEfficiency = 0.9``
     - Quantum efficiency of the sensor.
   * - ``float omni:sensor:LidarWpm:pixelPitch = 40.0``
     - Pixel pitch of the sensor in micrometers.
   * - ``float omni:sensor:LidarWpm:calibrationGain = 40.0``
     - Calibration gain of the sensor.
   * - ``float omni:sensor:LidarWpm:bitDepthResolution = 65536.0``
     - Bit depth resolution of the sensor.
   * - ``float omni:sensor:LidarWpm:detectorNoiseVariance = 0.135``
     - Detector shot-noise variance coefficient. Set to 0 to disable detector noise.
   * - ``float omni:sensor:LidarWpm:tofBinWidthNs = 0.0``
     - Sparse TOF histogram bin width in nanoseconds. A value of 0 selects a pulse-derived default.
   * - ``uint omni:sensor:LidarWpm:sparseTofBinCapacity = 32``
     - Maximum sparse TOF photon histogram bins retained per receiver.
   * - ``float omni:sensor:LidarWpm:pulseDepositSupportSigma = 3.0``
     - Gaussian pulse deposit support radius in standard deviations.
   * - ``float omni:sensor:LidarWpm:pulseDepositWeightEpsilon = 0.0001``
     - Minimum Gaussian pulse deposit weight to materialize a sparse TOF bin.
   * - ``float omni:sensor:LidarWpm:peakPhotonThreshold = 0.0``
     - Strict per-bin photon threshold used to form and split contiguous TOF histogram lobes.
   * - ``float omni:sensor:LidarWpm:peakSumThresholdScale = 1.0``
     - Positive multiplier applied to the derived minimum accumulated waveform-lobe photon-sum threshold. This does not affect the per-bin peakPhotonThreshold or direct return-processing modes.
   * - ``float omni:sensor:LidarWpm:detectorFovHorizontalDeg = 1.5``
     - Full horizontal detector field of view in degrees. Contributions outside half this angle from detector boresight are rejected; accepted contributions receive a smooth angular sensitivity taper.
   * - ``float omni:sensor:LidarWpm:detectorFovVerticalDeg = 1.5``
     - Full vertical detector field of view in degrees. Contributions outside half this angle from detector boresight are rejected; accepted contributions receive a smooth angular sensitivity taper.
   * - ``float omni:sensor:LidarWpm:minDetectableReflectance = 0.1``
     - Nominal minimum Lambertian reflectance at minDetectableReflectanceRangeM. This deterministic normal-incidence reference does not specify a probability of detection.
   * - ``float omni:sensor:LidarWpm:minDetectableReflectanceRangeM = 200.0``
     - Positive one-way range in meters for the nominal minimum-detectable-reflectance reference.
   * - ``float omni:sensor:LidarWpm:minDistBetweenReturnsM = 0.4``
     - Minimum distance between selected returns in meters.
   * - ``uint omni:sensor:LidarWpm:tiledSubSampling = 0``
     - Sensor workload should be subsampled by this factor.

OmniSensorGenericRadarWpmDmatScanCfgAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic radar scan configuration

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:WpmDmat:scan

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float raysPerDeg = 8.0``
     - Geometric ray-tracing sample density per degree across the scan field of view. Higher values can improve coverage at increased cost. This is not radar angular resolution.
   * - ``uint timeOffsetUsec = 0``
     - Non-negative offset of this scan from the radar frame time, in microseconds.
   * - ``float powerFactor = 1.0``
     - Unitless transmit-power scaling factor for this scan. It scales contribution strength before detection and is not a value in watts.
   * - ``bool binsFromSpec = true``
     - In FAST mode, derive range, velocity, azimuth, and elevation bin counts from the configured limits and resolution attributes when true; use the explicit bin-count attributes when false.
   * - ``bool enAngAliasing = false``
     - When false, discard contributions outside the configured azimuth/elevation limits. When true, allow angular aliasing by wrapping angular contributions into the configured angular interval in FAST datacube mode.
   * - ``bool enableRangeAliasing = false``
     - When false, discard contributions beyond maxRangeM. When true, allow range aliasing by wrapping over-range contributions into the configured unambiguous range in FAST datacube mode.
   * - ``bool detValFromBinIdx = false``
     - In FAST mode, report range and radial velocity from the detection-bin index when true; use contribution-weighted values within the bin when false.
   * - ``token elevMode = "FULL_EL"``
     - Allowed tokens: "NO_EL", "POS_EL", "FULL_EL"

       Elevation coverage mode: NO_EL uses zero elevation, POS_EL uses positive elevation only, and FULL_EL uses positive and negative elevation.
   * - ``token datacubeMode = "FAST"``
     - Allowed tokens: "FAST", "WAVEFORM"

       Detection processing mode. FAST uses the detection-matrix approximation; WAVEFORM uses sampled waveform processing.
   * - ``uint waveformMode = 0``
     - Waveform processing mode: 0 is per-contribution, 1 is per-bin, and 2 is sample-based. Active only when datacubeMode is WAVEFORM.
   * - ``float maxRangeM = 200``
     - Maximum unambiguous range of the scan in meters. Contributions beyond this value are discarded or folded according to enableRangeAliasing.
   * - ``float maxAzAngDeg = 66``
     - Positive azimuth half-angle in degrees. The symmetric azimuth field of view extends from -maxAzAngDeg to +maxAzAngDeg.
   * - ``float maxElAngDeg = 20``
     - Positive elevation half-angle in degrees. The symmetric elevation field of view extends from -maxElAngDeg to +maxElAngDeg, subject to elevMode.
   * - ``float rangeResM = 0.4``
     - Range separation and bin resolution in meters. Active in FAST mode when binsFromSpec is true; this does not add random range measurement noise. Binning and estimation can affect measured values.
   * - ``float velResMps = 0.147``
     - Radial-velocity separation and bin resolution in meters per second. Active in FAST mode when binsFromSpec is true; this does not add random velocity measurement noise. Binning and estimation can affect measured values.
   * - ``float boreAzResDeg = 1.3``
     - Azimuth separation and bin resolution at boresight in degrees. Active in FAST mode when binsFromSpec is true; this does not add random angular measurement noise. Binning and estimation can affect measured values.
   * - ``float boreElResDeg = 5.0``
     - Elevation separation and bin resolution at boresight in degrees. Active in FAST mode when binsFromSpec is true; this does not add random angular measurement noise. Binning and estimation can affect measured values.
   * - ``uint rBins = 112``
     - Number of range bins. Active in FAST mode when binsFromSpec is false.
   * - ``uint vBins = 160``
     - Number of velocity bins. Active in FAST mode when binsFromSpec is false.
   * - ``uint azBins = 12``
     - Number of azimuth bins. Active in FAST mode when binsFromSpec is false.
   * - ``uint elBins = 2``
     - Number of elevation bins. Active in FAST mode when binsFromSpec is false.
   * - ``uint slowTimeSamples = 379``
     - slow-time number of samples
   * - ``uint fastTimeSamples = 625``
     - fast-time number of samples
   * - ``uint azimuthPaddingSamples = 128``
     - Total azimuth transform length after zero padding in WAVEFORM mode, including the original samples.
   * - ``uint elevationPaddingSamples = 32``
     - Total elevation transform length after zero padding in WAVEFORM mode, including the original samples.
   * - ``uint slowTimePaddingSamples = 512``
     - Total slow-time transform length after zero padding in WAVEFORM mode, including the original samples.
   * - ``uint fastTimePaddingSamples = 1024``
     - Total fast-time transform length after zero padding in WAVEFORM mode, including the original samples.
   * - ``float chirpDuration = 2.5e-05``
     - chirp duration in seconds
   * - ``float chirpBandwidth = 3.75e+08``
     - chirp bandwidth in Hz
   * - ``float[] chirpRepetitionTimeSequence = [3.5e-05]``
     - Non-empty sequence of finite positive chirp repetition times in seconds. Active only in WAVEFORM mode, where every entry must be at least chirpDuration and define a nonsingular range/velocity inversion. The sequence advances only when this WAVEFORM scan fires. Firings of other scans and frames that fire no scan leave its entry unchanged. The selected entry holds for every chirp of a firing. The sequence restarts at element zero when the sensor is created, after an accepted attribute update and after a renderer reset. A single entry preserves fixed chirp timing. Velocity ambiguity bounds are derived from the selected timing and the global waveLengthMm.
   * - ``float frequencyStepBetweenChirps = 0``
     - frequency step between chirps in Hz
   * - ``float supportFactor = 1``
     - support factor in units of main lobe width (1 = one main lobe)
   * - ``token windowSlowTime = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Window kind for slow time (Doppler)
   * - ``token windowFastTime = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Window kind for fast time (range)
   * - ``token txAntennaGainMode = "COSINE_FALLOFF"``
     - Allowed tokens: "CONSTANT", "COSINE_FALLOFF", "CUSTOM", "PATCH_ARRAY_MODEL"

       antenna gain profile for Tx element
   * - ``uint txArrayAzimuthElements = 4``
     - Tx: number of azimuth elements
   * - ``uint txArrayElevationElements = 4``
     - Tx: number of elevation elements
   * - ``float txAzimuthElementSpacing = 0.00195``
     - Tx: azimuth element spacing in meters
   * - ``float txElevationElementSpacing = 0.00195``
     - Tx: elevation element spacing in meters
   * - ``token txWindowAzimuth = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Tx: window kind for azimuth
   * - ``token txWindowElevation = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Tx: window kind for elevation
   * - ``float txAzimuthSteeringAngleDeg = 0``
     - Tx: azimuth steering angle in degrees
   * - ``float txElevationSteeringAngleDeg = 0``
     - Tx: elevation steering angle in degrees
   * - ``token rxAntennaGainMode = "COSINE_FALLOFF"``
     - Allowed tokens: "CONSTANT", "COSINE_FALLOFF", "CUSTOM", "PATCH_ARRAY_MODEL"

       antenna gain profile for Rx element
   * - ``uint rxArrayAzimuthElements = 4``
     - Rx: number of azimuth elements
   * - ``uint rxArrayElevationElements = 4``
     - Rx: number of elevation elements
   * - ``float rxAzimuthElementSpacing = 0.00195``
     - Rx: azimuth element spacing in meters
   * - ``float rxElevationElementSpacing = 0.00195``
     - Rx: elevation element spacing in meters
   * - ``token rxWindowAzimuth = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Rx: window kind for azimuth
   * - ``token rxWindowElevation = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Rx: window kind for elevation
   * - ``float rxAzimuthSteeringAngleDeg = 0``
     - Rx: azimuth steering angle in degrees
   * - ``float rxElevationSteeringAngleDeg = 0``
     - Rx: elevation steering angle in degrees
   * - ``uint apertureArrayAzimuthElements = 4``
     - Aperture: number of azimuth elements
   * - ``uint apertureArrayElevationElements = 4``
     - Aperture: number of elevation elements
   * - ``float apertureAzimuthElementSpacing = 0.00195``
     - Aperture: azimuth element spacing in meters
   * - ``float apertureElevationElementSpacing = 0.00195``
     - Aperture: elevation element spacing in meters
   * - ``token apertureWindowAzimuth = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Aperture: window kind for azimuth
   * - ``token apertureWindowElevation = "RECT"``
     - Allowed tokens: "RECT", "HANN", "HAMMING", "BLACKMAN"

       Aperture: window kind for elevation
   * - ``uint cfarRnT = 1``
     - Number of range test cells used to estimate the local CFAR background.
   * - ``uint cfarRnG = 0``
     - Number of range guard cells excluded around the CFAR candidate.
   * - ``uint cfarVnT = 1``
     - Number of velocity test cells used to estimate the local CFAR background.
   * - ``uint cfarVnG = 0``
     - Number of velocity guard cells excluded around the CFAR candidate.
   * - ``uint cfarAznT = 1``
     - Number of azimuth test cells used in 4D CFAR mode.
   * - ``uint cfarAznG = 0``
     - Number of azimuth guard cells used in 4D CFAR mode.
   * - ``uint cfarElnT = 1``
     - Number of elevation test cells used in 4D CFAR mode.
   * - ``uint cfarElnG = 0``
     - Number of elevation guard cells used in 4D CFAR mode.
   * - ``float cfarMinVal = 7e-17``
     - Absolute minimum candidate value for CFAR detection. Lower-valued cells are discarded.
   * - ``float cfarOffset = 1.0``
     - Multiplier applied to the estimated local CFAR background when forming the detection threshold.
   * - ``float cfarNoiseMean = 0.0``
     - Mean of configured CFAR-cell noise.
   * - ``float cfarNoiseSDev = 0.0``
     - Standard deviation of configured CFAR-cell noise.
   * - ``float[] maxVelMpsSequence = [50.0, 55.0]``
     - Non-empty sequence of finite positive maximum unambiguous radial velocities in meters per second. In FAST mode the active value defines the symmetric interval into which Doppler values fold. WAVEFORM velocity bounds are derived from the global waveLengthMm and chirp timing instead. The sequence starts at element zero when the sensor is created, after an accepted attribute update and after a renderer reset, and advances only when this FAST scan fires. Firings of other scans and frames that fire no scan leave its entry unchanged.
   * - ``float[] rcsTuningCoefficients = [-12, 150, 0.0]``
     - Three RCS calibration values: element 0 is the minimum accepted RCS in dBsm; element 1 scales RCS before conversion to dBsm, with 1 meaning no scaling; element 2 is the standard deviation of added RCS noise in dBsm, with 0 meaning no added noise.
   * - ``float azimuthRadNoiseMean = 0.0``
     - Mean of Gaussian azimuth angle-noise samples at boresight, in radians. Samples are converted to phase noise before angle reconstruction; off-boresight errors follow the nonlinear direction-of-arrival mapping.
   * - ``float azimuthRadNoiseSDev = 0.0``
     - Standard deviation of Gaussian azimuth angle-noise samples at boresight, in radians. Samples are converted to phase noise before angle reconstruction; off-boresight errors follow the nonlinear direction-of-arrival mapping.
   * - ``float rangeNoiseMean = 0.0``
     - mean value of the range noise in meters
   * - ``float rangeNoiseSDev = 0.0``
     - standard deviation of the range noise in meters
   * - ``float velocityNoiseMean = 0``
     - mean value of the velocity noise in meters per second
   * - ``float velocityNoiseSDev = 0``
     - standard deviation of the velocity noise in meters per second
   * - ``float elevationRadNoiseMean = 0``
     - Mean of Gaussian elevation angle-noise samples at boresight, in radians. Samples are converted to phase noise before angle reconstruction; off-boresight errors follow the nonlinear direction-of-arrival mapping.
   * - ``float elevationRadNoiseSDev = 0``
     - Standard deviation of Gaussian elevation angle-noise samples at boresight, in radians. Samples are converted to phase noise before angle reconstruction; off-boresight errors follow the nonlinear direction-of-arrival mapping.
   * - ``float exponentialDecayFactor = 1``
     - Exponent controlling distance-dependent contribution decay. Higher values attenuate indirect and distant contributions more strongly. It has no effect in ovrtx.
   * - ``bool debugForceDetection = false``
     - Generates one valid synthetic contribution for debugging in FAST and WAVEFORM modes using debugForceRange, debugForceV, debugForceAz, debugForceEl, and debugForceDetectionPower. Ignores scene contributions and does not require a scene intersection or traced energy. Downstream CFAR, noise, and RCS processing remain active and can still reject the contribution.
   * - ``float debugForceDetectionPower = 1``
     - Finite nonnegative linear power of the synthetic contribution when debugForceDetection is enabled in FAST or WAVEFORM mode. Uses internal CFAR power units, on the same scale as cfarMinVal, not watts or dBsm. Waveform windows and spectral spreading determine the power in individual bins. Zero supplies no synthetic signal.
   * - ``float debugForceRange = 20``
     - Forced range in meters when debugForceDetection is enabled in FAST or WAVEFORM mode.
   * - ``float debugForceV = -40``
     - Forced radial velocity in meters per second when debugForceDetection is enabled in FAST or WAVEFORM mode.
   * - ``float debugForceAz = 0``
     - Forced azimuth in radians when debugForceDetection is enabled in FAST or WAVEFORM mode.
   * - ``float debugForceEl = 0``
     - Forced elevation in radians when debugForceDetection is enabled in FAST or WAVEFORM mode.
   * - ``float[] rxAntennaAzDeg = [-66, 66]``
     - Directivity data for CUSTOM antenna gain mode. Vector of azimuth angles in degrees for the Rx antenna gain pattern grid. Must be ordered lowest to highest.
   * - ``float[] rxAntennaElDeg = [-20, 20]``
     - Directivity data for CUSTOM antenna gain mode. Vector of elevation angles in degrees for the Rx antenna gain pattern grid. Must be ordered lowest to highest.
   * - ``float[] rxAntennaCoGain = [0.8, 0.7, 0.6, ...]``
     - Vector of linear co-polarization gain values for Rx antenna. Represents a row-major 2D grid with elevation rows and azimuth columns. The index is elevationIndex * azimuthCount + azimuthIndex, corresponding to `rxAntennaAzDeg` and `rxAntennaElDeg`.
   * - ``float[] rxAntennaCrossGain = [0.2, 0.3, 0.4, ...]``
     - Vector of linear cross-polarization gain values for Rx antenna. Represents a row-major 2D grid with elevation rows and azimuth columns. The index is elevationIndex * azimuthCount + azimuthIndex, corresponding to `rxAntennaAzDeg` and `rxAntennaElDeg`.
   * - ``float[] txAntennaAzDeg = [-66, 66]``
     - Directivity data for CUSTOM antenna gain mode. Vector of azimuth angles in degrees for the Tx antenna gain pattern grid. Must be ordered lowest to highest.
   * - ``float[] txAntennaElDeg = [-20, 20]``
     - Directivity data for CUSTOM antenna gain mode. Vector of elevation angles in degrees for the Tx antenna gain pattern grid. Must be ordered lowest to highest.
   * - ``float[] txAntennaCoGain = [0.8, 0.7, 0.6, ...]``
     - Vector of linear co-polarization gain values for Tx antenna. Represents a row-major 2D grid with elevation rows and azimuth columns. The index is elevationIndex * azimuthCount + azimuthIndex, corresponding to `txAntennaAzDeg` and `txAntennaElDeg`.
   * - ``float[] txAntennaCrossGain = [0.2, 0.3, 0.4, ...]``
     - Vector of linear cross-polarization gain values for Tx antenna. Represents a row-major 2D grid with elevation rows and azimuth columns. The index is elevationIndex * azimuthCount + azimuthIndex, corresponding to `txAntennaAzDeg` and `txAntennaElDeg`.

OmniSensorGenericRadarWpmDmatAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic radar using WpmDMAT model

**Inherits from**: APISchemaBase

**Can only apply to**: OmniRadar

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI
   - OmniSensorGenericRadarWpmDmatScanCfgAPI:s001

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "RadarWPMDMAT"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (20, 1)``
     -
   * - ``double2 omni:sensor:startTime = (0, 1000)``
     -
   * - ``token omni:sensor:WpmDmat:elementsCoordsType = "SPHERICAL"``
     - Allowed tokens: "CARTESIAN", "SPHERICAL"

       Sets the desired coordinate system for the output basic elements (not auxiliary data).
   * - ``token omni:sensor:WpmDmat:outputFrameOfReference = "SENSOR"``
     - Allowed tokens: "SENSOR", "WORLD", "CUSTOM"

       Sets the frame of reference for detection coordinates only. Doppler velocities remain sensor-relative, and scan angular limits remain in the sensor frame, including when coordinates use WORLD or CUSTOM.
   * - ``float[] omni:sensor:WpmDmat:customFrameOfReferenceTrafo = [0, 0, 0, ...]``
     - Defines the transformation for the custom frame of reference as [x,y,z,roll,pitch,yaw], used only when outputFrameOfReference is CUSTOM.
   * - ``float omni:sensor:WpmDmat:waveLengthMm = 3.9``
     - Finite positive operating wavelength in millimeters, shared by all scan configurations in FAST and WAVEFORM modes. Selects spectral material data and sets receive aperture, patch-antenna gain and RCS normalization. WAVEFORM derives its carrier frequency from this wavelength for range, velocity, and phase processing.
   * - ``uint omni:sensor:WpmDmat:traceTreeDepth = 3``
     - Maximum propagation depth. Higher values allow more indirect paths and possible ghost detections at increased tracing cost.
   * - ``token omni:sensor:WpmDmat:cfarMode = "2D"``
     - Allowed tokens: "2D", "4D"

       CFAR processing dimensions in FAST mode. 2D uses range and velocity; 4D also uses azimuth and elevation. WAVEFORM always uses 4D CFAR.

OmniSensorWpmAcousticSensorMountAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines a single acoustic sensor mount (position and orientation)

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:WpmAcoustic:sensorMount

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float3 position = (0.0, 0.0, 0.0)``
     - Sensor mount position in meters [x, y, z] relative to the sensor prim origin. Runtime updatable.
   * - ``float3 rotation = (0.0, 0.0, 0.0)``
     - Sensor mount rotation in degrees [roll, pitch, yaw] relative to the sensor prim orientation. Runtime updatable.

OmniSensorWpmAcousticRxGroupAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines a receiver group (set of sensor mount indices that listen together)

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:WpmAcoustic:rxGroup

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``uint[] receiverIndices = [0]``
     - Array of sensor mount indices that form this receiver group

OmniSensorWpmAcousticFiringSeqAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines a firing sequence cycle (one sequence in the repeating firing pattern)

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:WpmAcoustic:firingSeq

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float[] eventTimeNs = [0.0]``
     - Time offset in nanoseconds for each firing event in this sequence
   * - ``uint[] txSensorId = [0]``
     - Transmitter sensor mount index for each event
   * - ``uint[] rxGroupId = [0]``
     - Receiver group index for each event
   * - ``uint[] channel = [0]``
     - Channel ID for each event

OmniSensorGenericAcousticWpmAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic acoustic sensor using WPM model

Default configuration: Single sensor at origin with minimal topology.
Users can add more sensor mounts, Rx groups, and firing sequences by applying additional schemas:

- Add mounts: prepend apiSchemas = ["OmniSensorWpmAcousticSensorMountAPI:m002", ...]
- Add Rx groups: prepend apiSchemas = ["OmniSensorWpmAcousticRxGroupAPI:g002", ...]
- Add firing sequences: prepend apiSchemas = ["OmniSensorWpmAcousticFiringSeqAPI:seq002", ...]

**Inherits from**: APISchemaBase

**Can only apply to**: OmniAcoustic

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI
   - OmniSensorWpmAcousticSensorMountAPI:m001
   - OmniSensorWpmAcousticRxGroupAPI:g001
   - OmniSensorWpmAcousticFiringSeqAPI:seq001

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "AcousticWPM"``
     - Sensor model name
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     - Sensor vendor name
   * - ``string omni:sensor:marketName = "Generic"``
     - Sensor market name
   * - ``double2 omni:sensor:frameRate = (30, 1)``
     -
   * - ``float omni:sensor:WpmAcoustic:azSpanDeg = 90.0``
     - azimuth span in degrees
   * - ``float omni:sensor:WpmAcoustic:elSpanDeg = 90.0``
     - elevation span in degrees
   * - ``uint omni:sensor:WpmAcoustic:raysPerDeg = 3``
     - ray density per degree
   * - ``uint omni:sensor:WpmAcoustic:traceTreeDepth = 2``
     - maximum number of ray bounces
   * - ``float omni:sensor:WpmAcoustic:membraneDiameter = 0.03``
     - membrane diameter in meters
   * - ``float omni:sensor:WpmAcoustic:centerFrequency = 51200.0``
     - center frequency in Hz
   * - ``float omni:sensor:WpmAcoustic:bandwidth = 3000.0``
     - bandwidth in Hz
   * - ``float omni:sensor:WpmAcoustic:pulseDuration = 0.0025``
     - pulse duration in seconds
   * - ``float omni:sensor:WpmAcoustic:pulsePower = 513.57``
     - dimensionless pulse power
   * - ``float omni:sensor:WpmAcoustic:sampleDuration = 0.0001024``
     - time sampling of waveform in seconds
   * - ``float omni:sensor:WpmAcoustic:closeRange = 1.423360522414186091``
     - Close range threshold in meters. Runtime updatable.
   * - ``float omni:sensor:WpmAcoustic:closeRangeDecay = 1.260887305061087815``
     - Close range decay factor
   * - ``float omni:sensor:WpmAcoustic:closeIndirectAmplBase = 1.1213053540018527``
     - Base amplitude for indirect close range reflections. Runtime updatable.
   * - ``float omni:sensor:WpmAcoustic:closeDirectAmplBase = 1.3868006405050346``
     - Base amplitude for direct close range reflections. Runtime updatable.
   * - ``float omni:sensor:WpmAcoustic:closeIndirectAmpl = 17.638103929366554``
     - Amplitude multiplier for indirect close range reflections. Runtime updatable.
   * - ``float omni:sensor:WpmAcoustic:closeDirectAmpl = 12.655099113296389``
     - Amplitude multiplier for direct close range reflections. Runtime updatable.
   * - ``float omni:sensor:WpmAcoustic:noiseMin = 0.3``
     - Minimum noise level
   * - ``float omni:sensor:WpmAcoustic:noiseMax = 1.7``
     - Maximum noise level
   * - ``float[] omni:sensor:WpmAcoustic:gainCoeffs = [-0.1167095, 1.81197, -1.359988, ...]``
     - Gain polynomial coefficients for signal processing (7 elements). Runtime updatable.
   * - ``float[] omni:sensor:WpmAcoustic:directivityCoeffs = [0.711616, 0.2579289, -2.109056, ...]``
     - Directivity polynomial coefficients for beam pattern modeling (7 elements). Runtime updatable.
   * - ``token omni:sensor:WpmAcoustic:signalMode = "CHIRP"``
     - Allowed tokens: "CHIRP", "AM"

       signal mode
   * - ``bool omni:sensor:WpmAcoustic:enableInterference = false``
     - enable interference model
   * - ``float3 omni:sensor:WpmAcoustic:sensorMount:m001:position = (0, 0, 0)``
     -
   * - ``float3 omni:sensor:WpmAcoustic:sensorMount:m001:rotation = (0, 0, 0)``
     -
   * - ``uint[] omni:sensor:WpmAcoustic:rxGroup:g001:receiverIndices = [0]``
     -
   * - ``float[] omni:sensor:WpmAcoustic:firingSeq:seq001:eventTimeNs = [0]``
     -
   * - ``uint[] omni:sensor:WpmAcoustic:firingSeq:seq001:txSensorId = [0]``
     -
   * - ``uint[] omni:sensor:WpmAcoustic:firingSeq:seq001:rxGroupId = [0]``
     -
   * - ``uint[] omni:sensor:WpmAcoustic:firingSeq:seq001:channel = [0]``
     -

OmniSensorGenericIDSAPI
~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic Ideal Depth Sensor (IDS) using emitter grid model.

Supports multiple emitter types:

- SPHERICAL: Uniform angular grid on a sphere (numRows x numCols, row=elevation, col=azimuth in degrees)
- PLANAR: Uniform grid on a plane (numRows x numCols, row/col units in meters)
- CYLINDRICAL: Uniform angular grid on a cylinder (numRows x numCols, row=height in meters, col=azimuth in degrees)
- GRIDLESS_SPHERICAL: Non-grid spherical sampling (elementSize/radius control density)
- BOX: Axis-aligned box volume (bottomLeft/topRight define bounds, elementSize spacing per axis)

**Inherits from**: APISchemaBase

**Can only apply to**: OmniIDS

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "IDSCore"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (30, 1)``
     - desired framerate of the sensor
   * - ``token omni:sensor:Core:type = "SPHERICAL"``
     - Allowed tokens: "SPHERICAL", "PLANAR", "CYLINDRICAL", "GRIDLESS_SPHERICAL", "BOX"

       Emitter grid type
   * - ``uint omni:sensor:Core:numRows = 400``
     - Number of rows (elevation for SPHERICAL, z for CYLINDRICAL, y for PLANAR)
   * - ``uint omni:sensor:Core:numCols = 3600``
     - Number of columns (azimuth for SPHERICAL/CYLINDRICAL, x for PLANAR)
   * - ``float omni:sensor:Core:minColUnit = 0``
     - Minimum column value (azimuth in deg for SPHERICAL, x in m for PLANAR)
   * - ``float omni:sensor:Core:maxColUnit = 360``
     - Maximum column value
   * - ``float omni:sensor:Core:minRowUnit = -20``
     - Minimum row value (elevation in deg for SPHERICAL, not used in CYLINDRICAL, y in m for PLANAR)
   * - ``float omni:sensor:Core:maxRowUnit = 20``
     - Maximum row value (elevation in deg for SPHERICAL, z in m for CYLINDRICAL, y in m for PLANAR)
   * - ``float3 omni:sensor:Core:origin = (0, 0, 0)``
     - Origin of the emitter grid in meters
   * - ``float3 omni:sensor:Core:bottomLeft = (-10, -10, -10)``
     - Bottom-left corner of box emitter volume in meters
   * - ``float3 omni:sensor:Core:topRight = (10, 10, 10)``
     - Top-right corner of box emitter volume in meters
   * - ``float3 omni:sensor:Core:elementSize = (0.2, 0.2, 0.5)``
     - Element spacing per axis for BOX type, or scalar element size for GRIDLESS_SPHERICAL (uses x component)
   * - ``float omni:sensor:Core:radius = 0``
     - Radius/distance in m at which elementSize is defined (GRIDLESS_SPHERICAL only)

OmniSensorGenericWpmAPI
~~~~~~~~~~~~~~~~~~~~~~~

API Defines a generic Wave Propagation Model (WPM) sensor.

Path-traces a flattened transmitter/receiver/ray pattern and publishes the raw
per-contribution path data as one composite RenderOutput, `Contributions`:
one dense slot per (tile, transmitter, ray, bounce, receiver slot). Firing
timing is authored on the transmitter and ray patterns; detector models and
return processing are left to a consumer built on top. Supports scalar electromagnetic
or mechanical propagation using WPM's acoustic material model, selected by waveType.
Scalar transport carries power, not coherent phase or polarization.

Tx, Rx, Ray and TxRxMapping APIs are built in. Each role's patternTypes array
orders its selectable patterns; successive occurrences of a family consume
successive rows of that family's arrays. There is no instance-name ordering.
The active Tx and Rx patterns are selected independently. One Tx pattern row
selects one ray bundle and one pairing rule shared by all of its elements.
Receiver indices are local to the active Rx pattern; explicit target-group
indices are local to the selected mapping page.

Pattern geometry, counts, poses and selectors must have their declared
cardinalities, including inactive patterns. Only documented optional numeric
arrays may be empty, meaning zero values materialized by the consumer.
An empty fallback does not imply a usable pattern, identity pose or singleton
broadcast. Mapping-page receiver bounds are checked against the active Rx
pattern for the entire selected page; other pages may require another Rx.

Pattern orientations are unit quaternions stored as float4 in (x, y, z, w) order;
identity is (0, 0, 0, 1). Authored firing offsets are uint nanoseconds in
[0, 4294967295] (at most 4.294967295 seconds per offset). Widen Tx and ray offsets
to uint64 before adding them to each other or to the frame start time. Internal
WPM timing and the Contributions DeltaTimeNs output remain uint64.

The generator's pattern-input checker validates all stored patterns and the
active selection. The sensor checker validates model controls and basic scheduler
settings; descriptor validation checks tensor sizes, types, devices and CPU
metadata, never GPU buffer contents. The complete configuration is accepted only
after capacity and backend checks pass. Contributions is EMPTY until a valid
initial configuration exists. A rejected live edit retains the entire last
accepted snapshot. Accepted active indices are CPU output parameters, not
per-contribution channels.

**Inherits from**: APISchemaBase

**Can only apply to**: OmniGeneralSensor

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI
   - OmniSensorGenericWpmTxAPI
   - OmniSensorGenericWpmRxAPI
   - OmniSensorGenericWpmRayAPI
   - OmniSensorGenericWpmTxRxMappingAPI

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "GenericWpm"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (10, 1)``
     - desired frame rate of the sensor
   * - ``uint omni:sensor:GenericWpm:maxBounces = 3``
     - Maximum material-hit evaluations per path. Must be within [1, 255].
   * - ``uint omni:sensor:GenericWpm:maxContributionRayDepth = 1``
     - Maximum material evaluations between a bounce and a receiver. Must be within [0, 255].
   * - ``float omni:sensor:GenericWpm:minHitDistanceM = 0.005``
     - Minimum distance in meters at which any ray hit is accepted
   * - ``float omni:sensor:GenericWpm:minPrimaryHitDistanceM = 0.005``
     - Minimum distance in meters at which a primary ray hit is accepted
   * - ``float omni:sensor:GenericWpm:maxHitDistanceM = 1000``
     - Distance in meters after which the ray hit search terminates
   * - ``float omni:sensor:GenericWpm:sourceDivergence = 0.001``
     - Source beam divergence angle in radians
   * - ``float omni:sensor:GenericWpm:contributionRayRxHitOffsetM = 0.05``
     - Receiver-side acceptance distance in meters for contribution rays
   * - ``float omni:sensor:GenericWpm:wavelengthNm = 903``
     - Positive operating wavelength in nanometers, resolving the shared WPM material table. Author a wavelength appropriate to the selected waveType; changing waveType does not change this value.
   * - ``float omni:sensor:GenericWpm:bandwidthFactor = 0.15``
     - Unitless spectral bandwidth factor applied to the material table lookup
   * - ``token omni:sensor:GenericWpm:waveType = "electroMagnetic"``
     - Allowed tokens: "electroMagnetic", "mechanical"

       Propagation family: electroMagnetic uses electromagnetic materials; mechanical uses WPM's acoustic material model. Both use scalar power transport, not coherent signal or detector processing.
   * - ``uint omni:sensor:GenericWpm:activeTxPatternIndex = 0``
     - Index into tx:patternTypes, selecting one Tx pattern; may change per frame
   * - ``uint omni:sensor:GenericWpm:activeRxPatternIndex = 0``
     - Index into rx:patternTypes, independently selecting one Rx pattern; may change per frame
   * - ``uint omni:sensor:GenericWpm:activeMappingPageIndex = 0``
     - Shared mapping-page index into txRxMappings:numRxGroupsPerPages, used only in map mode

OmniSensorGenericWpmGridPatternsAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened regular-grid patterns, independently instantiated for tx, rx and ray.

Every array has one entry per grid occurrence in that role's patternTypes.
All geometry arrays are required when the family is used; an unused family
has empty arrays. Poses are sensor-relative for tx/rx and transmitter-relative
for ray. Positions are meters; orientations are finite unit float4 xyzw
quaternions, with identity (0, 0, 0, 1), authored explicitly.

SPHERICAL uses elevation rows and azimuth columns in degrees. PLANAR uses
Z rows and Y columns in meters, facing +X. CYLINDRICAL uses height rows in
meters and azimuth columns in degrees. Nonperiodic axes include both endpoints;
singleton axes use start. A full-circle azimuth span excludes the duplicate
endpoint. rowMajor uses row * numCols + col; columnMajor uses col * numRows + row.

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:GenericWpm:gridPatterns

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token[] modes = []``
     - Allowed tokens: "SPHERICAL", "PLANAR", "CYLINDRICAL"

       Required grid modes, one per grid pattern.
   * - ``uint[] numRows = []``
     - Required positive row counts, one per grid pattern
   * - ``uint[] numCols = []``
     - Required positive column counts, one per grid pattern
   * - ``float[] startRowUnits = []``
     - Required first-row coordinates in the grid mode's units
   * - ``float[] endRowUnits = []``
     - Required last-row coordinates; a singleton row uses start
   * - ``float[] startColUnits = []``
     - Required first-column coordinates in the grid mode's units
   * - ``float[] endColUnits = []``
     - Required last-column coordinates, except the duplicate full-circle azimuth endpoint is excluded
   * - ``token[] layouts = []``
     - Allowed tokens: "rowMajor", "columnMajor"

       Required traversal order per grid pattern.
   * - ``float3[] positions = []``
     - Required pattern translations in meters, one per grid pattern
   * - ``float4[] orientations = []``
     - Required unit pattern quaternions in xyzw order, one per grid pattern; no empty-pose fallback

OmniSensorGenericWpmGaussianPatternsAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened Gaussian ray bundles, instantiated for the ray role.

Required counts and poses have one entry per gaussian occurrence in
ray:patternTypes. Optional seed and angular-spread arrays are empty or have
that same length; empty means zero. Positions are transmitter-relative meters;
unit xyzw orientations rotate the local +X bundle axis and its horizontal and
vertical sampling axes. Generation is deterministic for a given seed.

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:GenericWpm:gaussianPatterns

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``uint[] numElements = []``
     - Required positive authored ray counts, one per Gaussian bundle
   * - ``uint[] seeds = []``
     - Sampler seeds, one per bundle or empty for zero
   * - ``float[] stdDevsHorizontal = []``
     - Nonnegative horizontal angular standard deviations in degrees, one per bundle or empty for zero
   * - ``float[] stdDevsVertical = []``
     - Nonnegative vertical angular standard deviations in degrees, one per bundle or empty for zero
   * - ``float3[] positions = []``
     - Required common ray origins in transmitter-relative meters, one per bundle
   * - ``float4[] orientations = []``
     - Required unit bundle quaternions in xyzw order, one per bundle; no empty-pose fallback

OmniSensorGenericWpmFreePatternsAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened explicit element poses, independently instantiated for tx, rx and ray.

numElementsPerPattern has one positive count per free occurrence in that
role's patternTypes. Its sum is the exact length of both packed pose arrays.
Prefix sums partition those arrays in family-row order, preserving element
order within each pattern. No pose is inferred from an empty array.
Tx/Rx poses are sensor-relative; ray poses are transmitter-relative. A ray's
unit xyzw orientation rotates local +X to its direction.

**Inherits from**: APISchemaBase

**Multiple Apply API**: Yes

**Property Namespace Prefix**: omni:sensor:GenericWpm:freePatterns

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``float3[] positions = []``
     - Required packed element positions in meters; length equals the sum of numElementsPerPattern
   * - ``float4[] orientations = []``
     - Required packed unit element quaternions in xyzw order; length equals the sum of numElementsPerPattern
   * - ``uint[] numElementsPerPattern = []``
     - Required positive counts partitioning the packed poses, one per free pattern

OmniSensorGenericWpmTxAPI
~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened transmitter pattern order, timing and per-pattern pairing controls.

patternTypes, rayPatternIndices and mappingModes are required and have the
same nonzero length. Controls are per selectable Tx pattern, not per element.
Each family occurrence consumes its next family row. Timing arrays are empty
for zero offsets or have their family's full cardinality. Grid timing has one
start/end pair per grid pattern; free timing has one offset per packed element.
Grid offsets interpolate in layout order including both endpoints; a singleton
uses start. End must not precede start. Offsets are sensor/frame-relative uint
nanoseconds; widen before adding transmitter-relative ray offsets.

**Inherits from**: APISchemaBase

**Prepend API Schemas**:
   - OmniSensorGenericWpmGridPatternsAPI:tx
   - OmniSensorGenericWpmFreePatternsAPI:tx

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token[] omni:sensor:GenericWpm:tx:patternTypes = []``
     - Allowed tokens: "grid", "free"

       Ordered selectable Tx pattern families, consuming successive rows of each family.
   * - ``uint[] omni:sensor:GenericWpm:gridPatterns:tx:startTimeOffsetsNs = []``
     - First-cell firing offsets from sensor/frame start, one per Tx grid or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:gridPatterns:tx:endTimeOffsetsNs = []``
     - Last-cell firing offsets from sensor/frame start, one per Tx grid or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:freePatterns:tx:timeOffsetsNs = []``
     - Firing offsets from sensor/frame start, one per packed free Tx element or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:tx:rayPatternIndices = []``
     - Required index into ray:patternTypes per Tx pattern; its entire ray bundle is shared by every element
   * - ``uint[] omni:sensor:GenericWpm:tx:mappingTargetRxGroups = []``
     - Page-local target-group index per Tx pattern. Full length is required if any pattern uses map; otherwise empty or full length. Entries for other modes are unused.
   * - ``token[] omni:sensor:GenericWpm:tx:mappingModes = []``
     - Allowed tokens: "nton", "1to1", "map"

       Required pairing mode per Tx pattern: nton targets all active Rx; 1to1 pairs matching local indices with equal active counts; map targets a group in the selected page.
   * - ``uint[] omni:sensor:GenericWpm:tx:mappingBloomFactors = []``
     - Per-Tx-pattern 1to1 grid neighbourhood radius, or empty for zero; ignored for nton/map. Nonzero values require compatible Tx/Rx grids and are capped at 7 by WPM's 255-receiver group limit.

OmniSensorGenericWpmRxAPI
~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened receiver pattern order with independent grid and free family arrays.

patternTypes is required and nonempty. Each family occurrence consumes its
next family row. The active Rx pattern is selected independently of the Tx
pattern; mapping receiver indices address its local elements only.

**Inherits from**: APISchemaBase

**Prepend API Schemas**:
   - OmniSensorGenericWpmGridPatternsAPI:rx
   - OmniSensorGenericWpmFreePatternsAPI:rx

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token[] omni:sensor:GenericWpm:rx:patternTypes = []``
     - Allowed tokens: "grid", "free"

       Required ordered selectable Rx pattern families, consuming successive rows of each family.

OmniSensorGenericWpmRayAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~

Flattened ray-bundle order with independent grid, free and Gaussian families.

patternTypes is required and nonempty. Each family occurrence consumes its
next family row. Ray poses and firing offsets are transmitter-relative.
Optional timing arrays are empty for zero or have the family's full length:
one start/end pair per grid, one offset per packed free element and one global
offset per Gaussian bundle. A Gaussian global offset is applied uniformly to
every ray in that bundle, not relative to the sensor. Grid offsets interpolate
in layout order including endpoints; singleton uses start; end must not precede
start. Widen uint offsets before adding them to Tx offsets or absolute time.

**Inherits from**: APISchemaBase

**Prepend API Schemas**:
   - OmniSensorGenericWpmGridPatternsAPI:ray
   - OmniSensorGenericWpmFreePatternsAPI:ray
   - OmniSensorGenericWpmGaussianPatternsAPI:ray

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token[] omni:sensor:GenericWpm:ray:patternTypes = []``
     - Allowed tokens: "grid", "free", "gaussian"

       Required ordered ray-bundle families, consuming successive rows of each family.
   * - ``uint[] omni:sensor:GenericWpm:gridPatterns:ray:startTimeOffsetsNs = []``
     - First-ray offsets from transmitter firing, one per ray grid or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:gridPatterns:ray:endTimeOffsetsNs = []``
     - Last-ray offsets from transmitter firing, one per ray grid or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:freePatterns:ray:timeOffsetsNs = []``
     - Offsets from transmitter firing, one per packed free ray or empty for zero
   * - ``uint[] omni:sensor:GenericWpm:gaussianPatterns:ray:globalTimeOffsetsNs = []``
     - Uniform offset from transmitter firing applied to every ray in a Gaussian bundle, one per bundle or empty for zero

OmniSensorGenericWpmTxRxMappingAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Packed receiver groups partitioned into shared mapping pages.

Prefix sums of numRxGroupsPerPages partition numRxPerGroups; prefix sums of
numRxPerGroups partition rxIndices. Counts must partition both arrays exactly.
These arrays are required when any Tx pattern uses map; nton and 1to1 do not
consume pages. Groups contain 1..255 ordered receiver slots; duplicate indices
remain distinct slots. Pages contain positive group counts.

activeMappingPageIndex selects one page. The active Tx pattern's
mappingTargetRxGroups entry selects a group local to that page. Every rxIndices
entry in the entire selected page must fit the active Rx pattern's local
element count, including groups not targeted by the active Tx. Other pages
may require other Rx patterns. Never filter, renumber or deduplicate slots.

**Inherits from**: APISchemaBase

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``uint[] omni:sensor:GenericWpm:txRxMappings:rxIndices = []``
     - Packed ordered receiver slots, each local to the active Rx pattern when its page is selected
   * - ``uint[] omni:sensor:GenericWpm:txRxMappings:numRxPerGroups = []``
     - Positive receiver-slot counts per group, each at most 255; sum equals rxIndices length
   * - ``uint[] omni:sensor:GenericWpm:txRxMappings:numRxGroupsPerPages = []``
     - Positive group counts per page; sum equals numRxPerGroups length

OmniSensorSampleWpmAPI
~~~~~~~~~~~~~~~~~~~~~~

API Defines sample WPM-based sensor parameters.

Consolidates parameters from sample_config.json (macro-parameters) and
wpm_config_manyRays.json (ray tracing / WPM configuration) into a single
USD API schema.  The former wpm_cfg file path is no longer needed since all
parameters are expressed directly as schema attributes.

**Inherits from**: APISchemaBase

**Can only apply to**: OmniSensorSample

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "SampleWpm"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``float omni:sensor:tickRate = 10``
     -
   * - ``string omni:sensor:SampleWpm:savePath = ""``
     - Directory path for saving output data
   * - ``bool omni:sensor:SampleWpm:save = false``
     - Enable saving of output data to disk
   * - ``bool omni:sensor:SampleWpm:streamSave = false``
     - Stream saving of output data to disk
   * - ``bool omni:sensor:SampleWpm:planeWaveConfig = false``
     - Use plane wave configuration for source divergence
   * - ``bool omni:sensor:SampleWpm:randomStates = true``
     - Include random states in WPM allocation
   * - ``float omni:sensor:SampleWpm:planeWaveExtent = 0.5``
     - Plane wave extent parameter
   * - ``uint omni:sensor:SampleWpm:numElements = 12``
     - Number of signal elements per ray
   * - ``float omni:sensor:SampleWpm:wavelengthNm = 3900000``
     - Operational wavelength in nanometers
   * - ``uint omni:sensor:SampleWpm:maxFrames = 3``
     - Maximum number of frames to save
   * - ``uint omni:sensor:SampleWpm:numCols = 300``
     - Number of columns (azimuth samples)
   * - ``uint omni:sensor:SampleWpm:numRows = 130``
     - Number of rows (elevation samples)
   * - ``float omni:sensor:SampleWpm:minAzimuthDeg = -6``
     - Minimum azimuth angle in degrees
   * - ``float omni:sensor:SampleWpm:maxAzimuthDeg = 6``
     - Maximum azimuth angle in degrees
   * - ``float omni:sensor:SampleWpm:downElevationDeg = -3.2``
     - Down-facing elevation angle in degrees
   * - ``float omni:sensor:SampleWpm:upElevationDeg = 2``
     - Up-facing elevation angle in degrees
   * - ``uint omni:sensor:SampleWpm:maxTraceTreeDepth = 1``
     - Maximum ray bounce depth
   * - ``bool omni:sensor:SampleWpm:isTransmittersOnHost = false``
     - Place transmitter data on host memory
   * - ``bool omni:sensor:SampleWpm:isReceiversOnHost = false``
     - Place receiver data on host memory
   * - ``bool omni:sensor:SampleWpm:isDetectorsOnHost = false``
     - Place detector data on host memory
   * - ``bool omni:sensor:SampleWpm:enHitGeometry = true``
     - Enable hit geometry in return data
   * - ``bool omni:sensor:SampleWpm:enTransmission = false``
     - Enable transmission computation
   * - ``bool omni:sensor:SampleWpm:enBackscatterFromR = false``
     - Enable backscatter from receiver
   * - ``bool omni:sensor:SampleWpm:enBackscatterFromT = false``
     - Enable backscatter from transmitter
   * - ``bool omni:sensor:SampleWpm:enRtVelocity = false``
     - Enable ray-traced velocity in return data
   * - ``float omni:sensor:SampleWpm:minHitDistanceM = 0.005``
     - Minimum hit distance in meters
   * - ``float omni:sensor:SampleWpm:minPrimaryHitDistanceM = 5``
     - Minimum primary hit distance in meters
   * - ``float omni:sensor:SampleWpm:maxHitDistanceM = 250``
     - Maximum hit distance in meters
   * - ``float omni:sensor:SampleWpm:avePower = 1``
     - Average transmit power

OmniSensorGenericCameraCoreAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic camera sensor and ISP using Core model

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "CameraCore"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``double2 omni:sensor:frameRate = (30, 1)``
     - desired frame rate of the camera as rational Hz (numerator/denominator); Runtime changes not supported, yet.
   * - ``bool omni:sensor:core:colorCorrectionRedBlueSwap = false``
     - Indicates whether the first and the third color component shall be swapped during color correction.
   * - ``float omni:sensor:core:colorCorrectionFullwellBlack = 1.0``
     - Maximal allowed value of the input array until it saturates during color correction processing.
   * - ``bool omni:sensor:core:colorCorrectionOutputFloat16 = true``
     - Indicates whether the color correction output should be in float16 format.
   * - ``bool omni:sensor:core:colorCorrectionOutputFloat32 = false``
     - Indicates whether the color correction output should be in float32 format.
   * - ``bool omni:sensor:core:colorCorrectionApplySaturation = false``
     - Indicates whether black level and fullwell saturation shall be applied during color correction.
   * - ``float omni:sensor:core:colorCorrectionSensorResponseScale = 1.0``
     - Scalar sensor response multiplier applied to input values.
   * - ``float omni:sensor:core:colorCorrectionBlack = 0.0``
     - Black floor level for color correction processing.
   * - ``float omni:sensor:core:colorCorrectionMatrixRr = 1.0``
     - Color correction matrix coefficient: Red channel contribution to output Red (Red from Red).
   * - ``float omni:sensor:core:colorCorrectionMatrixRg = 0.0``
     - Color correction matrix coefficient: Green channel contribution to output Red (Red from Green).
   * - ``float omni:sensor:core:colorCorrectionMatrixRb = 0.0``
     - Color correction matrix coefficient: Blue channel contribution to output Red (Red from Blue).
   * - ``float omni:sensor:core:colorCorrectionMatrixGr = 0.0``
     - Color correction matrix coefficient: Red channel contribution to output Green (Green from Red).
   * - ``float omni:sensor:core:colorCorrectionMatrixGg = 1.0``
     - Color correction matrix coefficient: Green channel contribution to output Green (Green from Green).
   * - ``float omni:sensor:core:colorCorrectionMatrixGb = 0.0``
     - Color correction matrix coefficient: Blue channel contribution to output Green (Green from Blue).
   * - ``float omni:sensor:core:colorCorrectionMatrixBr = 0.0``
     - Color correction matrix coefficient: Red channel contribution to output Blue (Blue from Red).
   * - ``float omni:sensor:core:colorCorrectionMatrixBg = 0.0``
     - Color correction matrix coefficient: Green channel contribution to output Blue (Blue from Green).
   * - ``float omni:sensor:core:colorCorrectionMatrixBb = 1.0``
     - Color correction matrix coefficient: Blue channel contribution to output Blue (Blue from Blue).
   * - ``float[] omni:sensor:core:colorCorrectionWhiteBalance = [1.0, 1.0, 1.0]``
     - White balance correction factors for RGB channels to compensate for light source color temperature.
   * - ``float[] omni:sensor:core:colorFilterArrayCfaCf00 = [0, 1, 0]``
     - Top Left pixel RGB coefficients of the 2x2 Color Filter Array pattern.
   * - ``float[] omni:sensor:core:colorFilterArrayCfaCf01 = [1, 0, 0]``
     - Top Right pixel RGB coefficients of the 2x2 Color Filter Array pattern.
   * - ``float[] omni:sensor:core:colorFilterArrayCfaCf10 = [0, 0, 1]``
     - Bottom Left pixel RGB coefficients of the 2x2 Color Filter Array pattern.
   * - ``float[] omni:sensor:core:colorFilterArrayCfaCf11 = [0, 1, 0]``
     - Bottom Right pixel RGB coefficients of the 2x2 Color Filter Array pattern.
   * - ``token omni:sensor:core:colorFilterArrayCfaSemantic = "GRBG"``
     - Allowed tokens: "RGGB", "GRBG", "BGGR", "RCCB", "CRBC", "BCCR", "RCCC", "CCCR", "CRCC"

       Semantic description of the Color Filter Array pattern. Valid values: RGGB, GRBG, BGGR, RCCB, CRBC, BCCR, RCCC, CCCR, or CRCC.
   * - ``token omni:sensor:core:colorFilterArrayOutputDataTypeFormat = "UINT32"``
     - Allowed tokens: "FLOAT32", "UINT32"

       Data type format for the Color Filter Array output. Valid values: FLOAT32 or UINT32.
   * - ``float omni:sensor:core:colorFilterArrayMaximalValue = 16777215.0``
     - The maximal value of the internal processing. Default for 24 bits: 16777215, for 20 bits: 1048575, for passthrough: 1. Authored as float so non-integer radiometric scales can be expressed; note that float32 represents integers exactly only up to 2^24.
   * - ``bool omni:sensor:core:colorFilterArrayFlipHorizontal = false``
     - Enable horizontal mirroring of the Color Filter Array output.
   * - ``bool omni:sensor:core:colorFilterArrayFlipVertical = false``
     - Enable vertical mirroring of the Color Filter Array output.
   * - ``float omni:sensor:core:noiseDarkShotNoiseGain = 10.0``
     - Gain applied to the dark shot noise component during noise simulation.
   * - ``float omni:sensor:core:noiseDarkShotNoiseSigma = 0.5``
     - Standard deviation (sigma) of the dark shot noise for realistic noise simulation.
   * - ``float2[] omni:sensor:core:noiseHdrCombinationData = [[5.8, 4000], [58, 8000], [70, 16000]]``
     - Array of HDR region parameters as [gain, exposure_time] pairs defining the gains and exposure times for different HDR regions in noise simulation.
   * - ``int omni:sensor:core:compandingAlignment = 15``
     - Alignment of the MSB (Most Significant Bit) of the companding operation, with LSB starting at 0.
   * - ``int omni:sensor:core:compandingPostPedestal = 0``
     - Pedestal value added after applying the companding operation.
   * - ``int omni:sensor:core:compandingPrePedestal = 0``
     - Pedestal value added before applying the companding operation.
   * - ``float2[] omni:sensor:core:compandingLinearCompandCoeff = [(0, 0), (512, 512), (1024, 851), ...]``
     - Array of companding parameters defining the non-linear compression curve as [input_value, output_value] pairs.
   * - ``string omni:sensor:core:ispSmodelCameraProgram = ""``
     - Base64 encoded ISP (Image Signal Processor) program file for advanced camera image processing.
   * - ``string omni:sensor:core:ispSmodelRawDataPaddingMode = "NONE"``
     - Allowed tokens: "NONE", "RIGHT", "LEFT"

       Raw data padding mode for ISP processing.
   * - ``string omni:sensor:core:ispSmodelSensorRawFormat = "RAW8"``
     - Allowed tokens: "RAW8", "RAW10", "RAW12", "RAW14", "RAW20", "RAW24"

       Sensor raw format for ISP processing.
   * - ``bool omni:sensor:core:introspectionOutputFile = false``
     - Enable file saving.
   * - ``bool omni:sensor:core:introspectionOutputFileEachFrameOneFile = false``
     - Indicates whether all frames shall be concatenated into a single file or stored as separate files.
   * - ``bool omni:sensor:core:introspectionOutputFileOnlyLastFrame = false``
     - Save only the most recent frame. Only works when saving each frame in one file with the 'EachFrameOneFile' option.
   * - ``string omni:sensor:core:introspectionOutputFileDirectory = ""``
     - Location where output files will be saved.
   * - ``bool omni:sensor:core:introspectionOutputViz = false``
     - Enable texture viewing in the Sensor Visualizer panel.
   * - ``int omni:sensor:core:introspectionOutputVizInputChannel = 101``
     - Channel for input texture visualization.
   * - ``int omni:sensor:core:introspectionOutputVizRawChannel = 102``
     - Channel for RAW texture visualization.
   * - ``int omni:sensor:core:introspectionOutputVizOutputChannel = 103``
     - Channel for output texture visualization.
   * - ``bool omni:sensor:core:introspectionInputRaw = false``
     - Inject a RAW input file that will be processed by the ISP.
   * - ``string omni:sensor:core:introspectionInputRawPath = ""``
     - Path to the RAW input file.
   * - ``int omni:sensor:core:introspectionInputRawWidth = 0``
     - Image Width.
   * - ``int omni:sensor:core:introspectionInputRawHeight = 0``
     - Image Height.
   * - ``int omni:sensor:core:introspectionInputRawSkipFront = 0``
     - Bytes to skip before each frame.
   * - ``int omni:sensor:core:introspectionInputRawSkipBack = 0``
     - Bytes to skip after each frame.
   * - ``string omni:sensor:core:introspectionInputRawFileDataType = "UINT16"``
     - Allowed tokens: "UINT8", "UINT16", "UINT32", "FLOAT16", "FLOAT32"

       Data type of the RGB.
   * - ``bool omni:sensor:core:introspectionInputRawLoop = true``
     - Indicates whether the input file shall be loop infinitely.

OmniSensorGenericDepthSensorSingleViewAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Defines generic depth sensor camera using Core model

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

**Prepend API Schemas**:
   - OmniSensorAPI
   - OmniSensorEncryptionAPI

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``string omni:sensor:modelName = "DepthSensorSingleView"``
     -
   * - ``string omni:sensor:modelVendor = "NVIDIA"``
     -
   * - ``string omni:sensor:marketName = "Generic"``
     -
   * - ``float omni:sensor:depthSensor:baselineMM = 55``
     - Distance between the two cameras in millimeters.
   * - ``float omni:sensor:depthSensor:focalLengthPixel = 897``
     - Focal length of the camera in pixels.
   * - ``float omni:sensor:depthSensor:sensorSizePixel = 1280``
     - Size of the camera sensor in pixels.
   * - ``float omni:sensor:depthSensor:maxDisparityPixel = 110``
     - Maximum disparity value in pixels.
   * - ``float omni:sensor:depthSensor:noiseMean = 0.25``
     - Mean value for noise generation.
   * - ``float omni:sensor:depthSensor:noiseSigma = 0.25``
     - Standard deviation for noise generation.
   * - ``float omni:sensor:depthSensor:noiseDownscaleFactorPixel = 1``
     - Factor to downscale noise texture in pixels.
   * - ``float omni:sensor:depthSensor:confidenceThreshold = 0.7``
     - Threshold for confidence filtering.
   * - ``bool omni:sensor:depthSensor:outlierRemovalEnabled = true``
     - Remove outliers caused by reconstruction and reprojection.
   * - ``float omni:sensor:depthSensor:minDistance = 0.5``
     - Minimum distance for disparity generation.
   * - ``float omni:sensor:depthSensor:maxDistance = 1e+07``
     - Maximum distance for disparity generation.
   * - ``int omni:sensor:depthSensor:rgbDepthOutputMode = 0``
     - RGB output mode.
   * - ``bool omni:sensor:depthSensor:showDistance = false``
     - Show distance for disparity generation.
   * - ``float omni:sensor:depthSensor:effectiveDistance = 0``
     - Emulates an IR-projection with a distance based confidence fall-off metric.
       When enabled, combines distance confidence with texture-based confidence.
       Set to 0 to disable IR emulation.
