.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-acoustic-index:
.. _sensors-nonvisual-acoustic:

Acoustic generic wpm model
==========================

The Acoustic generic wpm model simulates ultrasonic pulses and the echoes
received by a transducer array. A *mount* locates each transducer; a *receiver
group* selects the receiving mounts. A repeating *firing sequence*
selects the transmitting mount, receiver group and channel id for each pulse.
Each receiving membrane records an *echo envelope*: amplitude sampled over time.

A *signal way* is the envelope recorded by one receiving mount on one channel
id. Request :doc:`SignalWays <outputs>` to receive these envelopes. Define the
sensor with an ``OmniAcoustic`` prim and ``OmniSensorGenericAcousticWpmAPI``.

.. figure:: ../../../img/sensors/nonvisual/acoustic_echo_envelope.avif
   :alt: Top, a line plot of echo amplitude over range from 0 to 5.6 m, flat except for one sharp peak just past 3 m. Bottom, on the same horizontal axis, a side view of the scene: a green dot for the sensor 0.5 m above a gray ground band at the left, arrows for the pulse and its echo, and a 1.25 m tall concrete wall whose near face stands at 3 m, under the peak.
   :width: 1200

   *Echo amplitude plotted against range, aligned with the scene below. The
   sensor is 0.5 m above asphalt; the concrete wall is 3 m ahead, at the echo
   peak.*

.. _sensors-nonvisual-acoustic-what-it-hears:

Simulation
----------

Each firing event traces a pulse from the transmitting mount using the
configured azimuth span, elevation span and ray density. The default trace
depth allows two surface interactions. Indirect paths arrive later than direct
paths and can produce ghost echoes, so one pulse can produce several echoes
in an envelope. See :ref:`ray tracing
<sensors-nonvisual-acoustic-attributes-ray-tracing>` for these controls.

Surface response uses :doc:`non-visual material labels
<../../../materials/nonvisual_sensor_materials>`. A visual shader is not
required.

Outputs
-------

The :doc:`SignalWays <outputs>` output contains one amplitude envelope per
receiving-mount/channel-id pair. Request it with a single RenderVar; all six
channels and the frame metadata are delivered together. The output contains
signal samples, with dimensions specified by its params.

.. _sensors-nonvisual-acoustic-features:

Capabilities
------------

- Transducer arrays use sensor mounts, receiver groups and firing sequences
  on one ``OmniAcoustic`` prim. The main schema includes one of each, defining
  a single transducer that transmits and receives once per cycle. Add schema
  instances to expand the array; see :doc:`howto/array_topology` and
  :ref:`topology attributes <sensors-nonvisual-acoustic-attributes-topology>`.
- Basic mode (default) has a lower processing cost. Interference mode also
  models interference between concurrent transmissions from multiple mounts.
  See :ref:`operating modes <sensors-nonvisual-acoustic-attributes-operating-modes>` for their controls.
- Membrane and pulse parameters describe the transducer and emitted signal.
  Signal mode, range-dependent gain, polynomial directivity, close-range boost
  and bounded noise control the envelope; see :doc:`attributes`.
- Most attributes, including operating mode, can change at runtime. See
  :ref:`runtime updates <sensors-nonvisual-acoustic-attributes-runtime-updates>`
  for exceptions and :doc:`howto/live_retuning` for examples and verification.

.. _sensors-nonvisual-acoustic-where-it-fits:

Applications
------------

Use this model for short-range ultrasonic sensing, including parking,
proximity sensing and obstacle detection around vehicles and robots. One
sensor prim can represent an array whose transducers transmit and receive in
sequence. The scene's non-visual material labels can also be used by lidar and
radar sensors.

This model produces sampled echo envelopes. For point detections, use a
:doc:`lidar <../lidar_core/index>` or
:doc:`radar <../radar_wpm_dmat/index>` model.

.. _sensors-nonvisual-acoustic-before-you-start:

Sensor definition
-----------------

Apply ``OmniSensorGenericAcousticWpmAPI`` to an ``OmniAcoustic`` prim.
See :doc:`../../common/sensor_configuration` for sensor authoring,
:doc:`../../common/output_configuration` for RenderProducts and RenderVars,
and :doc:`attributes` for acoustic controls. :doc:`../../first_sensor`
introduces the shared stepping and mapping workflow.

.. _sensors-nonvisual-acoustic-example:

The :doc:`Python: Acoustic Sensor <../../../examples/python_sensor_acoustic>`
example places a sensor 0.5 m above asphalt ground, facing a concrete wall 3 m
away along world +X. Both surfaces have non-visual material labels and no
visual shader. It plots echo envelopes in Rerun or prints a summary.
:doc:`howto/set_up_sensor` explains the setup.

The following sensor definition applies the schema and sets a 10 Hz frame
rate, tracing angles, trace depth and transform:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../examples/python/acoustic/acoustic_example.usda
         :language: usda
         :start-after: # [snippet:configure-acoustic-sensor]
         :end-before: # [/snippet:configure-acoustic-sensor]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
         :dedent:

The model requires an active motion BVH. Select ``AUTO`` or ``ENABLE`` at
renderer creation; see :ref:`motion BVH configuration
<sensors-common-output-configuration-motion-bvh>`. Initial frames contain no
echo data. See :ref:`startup frames
<sensors-nonvisual-acoustic-outputs-first-frames>` and :doc:`howto/set_up_sensor`
for warm-up and output handling.

Configuration and outputs
-------------------------

Use :doc:`attributes` to tune the sensor and :doc:`outputs` before reading
``SignalWays``: it defines slots, validity, startup frames and range conversion.
The :doc:`how-tos <howto/index>` build a sensor, expand its array and retune it;
follow them in that order initially.

.. toctree::
   :maxdepth: 1

   attributes
   howto/index
   outputs

Related
-------

- :doc:`Sensor Configuration <../../common/sensor_configuration>` — instantiating a sensor prim, applying its schema and overriding attributes.
- :doc:`Output Configuration <../../common/output_configuration>` — RenderProducts, RenderVars and the renderer options sensors depend on.
- :doc:`Sensor Outputs <../../common/sensor_outputs>` — the composite output and how to map it.
- :doc:`Symptom Index <../../troubleshooting/symptoms>` — diagnosing missing or unexpected output.
