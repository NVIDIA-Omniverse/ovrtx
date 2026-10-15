.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Acoustic Sensors
================

An ovrtx acoustic scene needs an ``OmniAcoustic`` sensor prim and a
RenderProduct whose ``SignalWays`` RenderVar delivers the sensor's output.

Unlike lidar and radar, the acoustic model does not report discrete returns. It
transmits a pulse and reports the received *echo envelope*: an amplitude series
sampled uniformly in time, one series per signal way. A signal way is one
transmitter/receiver-group pairing from the sensor's firing sequence. This is
why the acoustic composite is ``SignalWays`` rather than ``PointCloud``, and why
it has no ``Counts`` channel and no per-point valid flag -- the frame's extent
comes from its parameters instead.

Configure the Acoustic Prim
---------------------------

.. literalinclude:: ../../examples/python/acoustic/acoustic_example.usda
   :language: usda
   :start-after: # [snippet:configure-acoustic-sensor]
   :end-before: # [/snippet:configure-acoustic-sensor]

Apply ``OmniSensorGenericAcousticWpmAPI`` for the generic WPM acoustic model.
The sensor fires along its local ``-Z``, so in a Z-up scene rotate the prim so
that ``-Z`` points in the intended forward direction.

.. note::

   Motion BVH is required, not preferred. The acoustic model runs the
   multi-tick trace path, and every envelope comes back empty without it. Set
   it on ``RendererConfig`` at renderer creation time -- see
   :doc:`../core/renderer_configuration`. The model also publishes nothing on
   its first frames, so take a few warm-up steps before reading an envelope.

Important Output Attributes
---------------------------

.. list-table::
   :header-rows: 1

   * - Attribute
     - Use
   * - ``omni:sensor:WpmAcoustic:sampleDuration``
     - Time between envelope samples. Sets the range resolution, and is
       republished as the ``sampleDurationUs`` parameter that a consumer needs
       to convert a sample index back to a range.
   * - ``omni:sensor:WpmAcoustic:membraneDiameter``
     - Membrane diameter. The model derives the detector area
       ``pi * d^2 / 4`` from it, so the received amplitude rises with it.
   * - ``omni:sensor:WpmAcoustic:enableInterference``
     - Select the interference trace kernel. Read at configuration time and
       cannot be changed at runtime: the model logs a warning and keeps the old
       value, so exercising both paths needs two sensor prims.
   * - ``omni:sensor:WpmAcoustic:centerFrequency``
     - Transmit center frequency, republished verbatim as the
       ``centerFrequencyHz`` parameter.

The lobe and tracing controls -- ``azSpanDeg``, ``elSpanDeg``, ``raysPerDeg``,
``traceTreeDepth`` -- shape what the sensor sees rather than how the output is
laid out. They and the remaining model parameters are documented with their
defaults in the ``OmniSensorGenericAcousticWpmAPI`` schema.

The firing sequence (``firingSeq``), receiver groups (``rxGroup``), and mount
transforms (``sensorMount``) determine how many signal ways a frame carries.
Their schema defaults describe a single transmitter, a single receiver group and
one firing event, which yields one signal way per frame.

Configure SignalWays Output
---------------------------

.. literalinclude:: ../../examples/python/acoustic/acoustic_example.usda
   :language: usda
   :start-after: # [snippet:configure-acoustic-output]
   :end-before: # [/snippet:configure-acoustic-output]

``SignalWays`` is a composite render variable: it carries every channel plus the
frame header in one output, so the RenderProduct requests a single var rather
than one per channel.

SignalWays Channels
-------------------

.. list-table::
   :header-rows: 1

   * - Channel
     - Type
     - Meaning
   * - ``Amplitudes``
     - ``float32``
     - Echo amplitude at each envelope sample.
   * - ``TimeOffsetNs``
     - ``int32``
     - Time offset relative to the sensor timestamp, one entry per signal way.
   * - ``Flags``
     - ``uint8``
     - ``ElementFlags::VALID`` (``0x40``) at the signal way's own index, set when
       that way produced a return; zero elsewhere. Indexed per signal way, not per
       element, in both trace modes.
   * - ``TransmitterIds``
     - ``float32``
     - Transmitter that emitted the signal way.
   * - ``ReceiverIds``
     - ``float32``
     - Receiver group that observed it.
   * - ``ChannelIds``
     - ``float32``
     - Transmit/receive channel pairing.

SignalWays Parameters
---------------------

The frame header arrives as composite *params* rather than as channels, which is
the role ``Counts`` plays for a point cloud.

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Meaning
   * - ``frameId``
     - ``uint64``
     - The model's own frame counter, never reset across a live reconfiguration.
   * - ``numSignalWays``
     - ``uint32``
     - Signal ways in this frame.
   * - ``numSamplesPerSignalWay``
     - ``uint32``
     - Samples of the echo envelope per signal way.
   * - ``numElements``
     - ``uint32``
     - Entries in each channel: ``numSignalWays * numSamplesPerSignalWay``.
   * - ``cycleIndex``
     - ``uint32``
     - Firing cycle this frame belongs to.
   * - ``centerFrequencyHz``
     - ``float32``
     - Transmit center frequency, in Hz.
   * - ``sampleDurationUs``
     - ``float32``
     - Time between envelope samples, in microseconds.

Interpreting Acoustic Output
----------------------------

Every channel is a 1D array of ``numElements`` entries. ``Amplitudes`` fills all
of them, one per envelope sample, so it reshapes to one row per signal way. The
others describe a signal way as a whole and carry one entry per signal way, in
the first ``numSignalWays`` positions; the remainder are zero.

.. literalinclude:: ../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:read-acoustic-signal-ways]
   :end-before: # [/snippet:read-acoustic-signal-ways]

An envelope is sampled uniformly at ``sampleDurationUs``, so a sample's index is
its round-trip echo time in units of that duration, and range is half the round
trip at the speed of sound. Read the sample duration from the parameter rather
than hardcoding it: it is an authored sensor setting.

.. literalinclude:: ../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:acoustic-sample-index-to-range]
   :end-before: # [/snippet:acoustic-sample-index-to-range]

At the default ``sampleDuration`` of 102.4 us, one sample spans about 1.8 cm of
range, which bounds how precisely a peak can be located.

For the runnable end-to-end version of the above, see
:doc:`../examples/python_sensor_acoustic`.
