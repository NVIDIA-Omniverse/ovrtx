.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor:

Set Up an Acoustic Sensor
=========================

The Acoustic generic wpm model records sampled echo envelopes from ultrasonic
pulses. A scene needs an ``OmniAcoustic`` prim with
``OmniSensorGenericAcousticWpmAPI`` and a RenderProduct requesting
``SignalWays``. This procedure uses the :doc:`acoustic example
<../../../../examples/python_sensor_acoustic>` to configure the sensor,
materials and renderer, then read the strongest echo. See :doc:`../outputs`
for the signal-way layout and validity rules.

Before you start. Use the :doc:`acoustic example <../../../../examples/python_sensor_acoustic>`
to run these steps. If you are new to sensor scenes, first read
:doc:`../../../first_sensor`.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-prim:

Author the sensor prim
----------------------

``OmniSensorGenericAcousticWpmAPI`` applies only to ``OmniAcoustic``.
Its defaults define one transducer that transmits and receives once per cycle,
using one mount, receiver group and firing sequence. See :doc:`../attributes`
and :ref:`schema instances <sensors-common-sensor-configuration-instances>`
for details. The example overrides frame rate, tracing angles, trace depth
and transform; other attributes retain their defaults:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../examples/python/acoustic/acoustic_example.usda
         :language: usda
         :start-after: # [snippet:configure-acoustic-sensor]
         :end-before: # [/snippet:configure-acoustic-sensor]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
         :dedent:

The example captures at 10 Hz with a 90° azimuth by 60° elevation lobe.
``raysPerDeg`` controls ray density and ``traceTreeDepth`` limits surface
interactions. See :doc:`../attributes` for defaults and units, and
:ref:`sensor scheduling <sensors-common-multi-rate-frame-rate>` for frame-rate
behavior.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-orientation:

Orient the prim
^^^^^^^^^^^^^^^

The sensor fires along its local ``-Z`` axis, as every sensor prim does (refer
to :ref:`sensors-common-sensor-configuration-orientation`), so in a Z-up scene
rotate the prim until ``-Z`` points where you want the lobe to go. The example's
transform maps local ``-Z`` onto world ``+X``, toward the wall, keeps local
``+Y`` as world ``+Z`` so that the lobe stays level, and puts the sensor 0.5 m
above the ground. It authors that pose as a single
matrix. Every mount of the array is placed relative to this prim frame, so the
whole array turns with the prim; :doc:`../attributes` states the mount frame and
:doc:`array_topology` shows how to lay several mounts out.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-output:

Request the SignalWays output
-----------------------------

Target the sensor with the RenderProduct's ``camera`` relationship and add
a RenderVar with ``sourceName = "SignalWays"`` to ``orderedVars``.
See :ref:`RenderProducts <sensors-common-output-configuration-renderproduct>`
and :ref:`RenderVars <sensors-common-output-configuration-rendervar>`.
This is the model's only output type:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../examples/python/acoustic/acoustic_example.usda
         :language: usda
         :start-after: # [snippet:configure-acoustic-output]
         :end-before: # [/snippet:configure-acoustic-output]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-acoustic-output-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-acoustic-output-python]
         :dedent:

``SignalWays`` is a composite output, so this one RenderVar carries every
channel and param of the frame; :doc:`../outputs` lists them and shows how to
read them.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-materials:

Label the surfaces
------------------

Surface response uses ``omni:simready:nonvisual:*`` labels on the bound
``Material`` prim. The example's asphalt ground and concrete wall use these
materials without visual shaders:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../examples/python/acoustic/acoustic_example.usda
         :language: usda
         :start-after: # [snippet:configure-nonvisual-materials]
         :end-before: # [/snippet:configure-nonvisual-materials]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-nonvisual-materials-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-nonvisual-materials-python]
         :dedent:

:doc:`../../../../materials/nonvisual_sensor_materials` explains the label vocabulary and how to
author it.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-motion-bvh:

Create the renderer with the motion BVH enabled
-----------------------------------------------

This model needs an active motion BVH (see :doc:`../outputs`). Select ``AUTO``
or ``ENABLE`` when creating the renderer; this example uses ``ENABLE``. The
snippet also creates the stage and attaches it to the renderer:

.. literalinclude:: ../../../../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:create-renderer]
   :end-before: # [/snippet:create-renderer]
   :emphasize-lines: 11
   :caption: ``main.py``, from the runnable :doc:`acoustic example <../../../../examples/python_sensor_acoustic>`
   :dedent:

:ref:`sensors-common-output-configuration-motion-bvh` describes the switch in
full: the modes, the C call, its lifetime and GPU support.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-warm-up:

Load the scene and warm up
--------------------------

Open the USDA into the attached stage and wait until that write has landed, so
the sensor and its product exist before the first step:

.. literalinclude:: ../../../../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:load-acoustic-scene]
   :end-before: # [/snippet:load-acoustic-scene]
   :dedent:

The model's first frames carry no echo data
(:ref:`Startup frames <sensors-nonvisual-acoustic-outputs-first-frames>`), so
take a few steps before you read one. The example takes three; each step
renders the acoustic product and advances time by 0.1 s, one frame period at
the authored 10 Hz:

.. literalinclude:: ../../../../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:warm-up-acoustic]
   :end-before: # [/snippet:warm-up-acoustic]
   :dedent:

.. note::

   :ref:`sensors-common-output-configuration-warmup` counts this settling
   among the reasons to warm the renderer up, beside texture streaming and
   path-tracing convergence.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-read:

Render a frame and read the strongest echo
------------------------------------------

One more step returns the product's frame. The snippet reads the frame through
the example's two helpers, which map the ``SignalWays`` output to the CPU,
reshape the envelopes to one row per signal way and convert a sample index to a
range; it then takes the strongest sample of each row and prints the median peak
range and amplitude over the signal ways that responded:

.. literalinclude:: ../../../../../examples/python/acoustic/main.py
   :language: python
   :start-after: # [snippet:step-and-visualize-acoustic]
   :end-before: # [/snippet:step-and-visualize-acoustic]
   :dedent:

Both helpers are shown and explained on :doc:`../outputs`. The runnable
:doc:`acoustic example <../../../../examples/python_sensor_acoustic>` adds a
plot of the envelopes and its command-line options.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-verify:

Verification
------------

The example prints four values:

- ``signal ways``: the number of waveforms the frame is laid out for.
- ``responding``: how many contain a response.
- ``median peak range``: the median range, in meters, over responding waveforms.
- ``median peak amplitude``: their median peak amplitude.

Expect one signal way, one response and a peak near the wall at 3.0 m.
Noise causes the amplitude to vary slightly between runs. The default topology
has one mount listening to itself on one channel id; see
:ref:`Layout <sensors-nonvisual-acoustic-outputs-slots>`.

The strongest sample locates the wall. At the default sample duration, each
sample spans about 1.8 cm of range and 320 samples reach about 5.6 m. See
:ref:`Sample ranges <sensors-nonvisual-acoustic-outputs-range>`.

A frame with no signal ways prints ``no signal ways reported``. If you see that,
or only noise with no peak, read `Potential issues`_.

.. _sensors-nonvisual-acoustic-howto-set-up-sensor-symptoms:

Potential issues
----------------

Each of these is a configuration you can correct; the :doc:`Symptom Index
<../../../troubleshooting/symptoms>` collects them with the symptoms of the
other models.

- **Every envelope is noise or zero, and no signal way carries the VALID bit.**
  The renderer was created without the motion BVH, which this model needs
  enabled when the renderer is created; without it every envelope comes back
  empty. Refer to :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>` and to
  :ref:`Motion BVH <sensors-common-output-configuration-motion-bvh>`.
- **The frame carries no echo data although the renderer has the motion BVH
  enabled.** It is one of the first frames after the sensor was created, which
  carry no echo data, and nothing in the params marks such a frame; step past
  them as `Load the scene and warm up`_ does. Refer to :ref:`Startup frames <sensors-nonvisual-acoustic-outputs-first-frames>` and to :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **The peak range is not the wall's, or no echo is detected where the wall
  stands.** The prim is not oriented along its firing axis: the lobe goes
  where the prim's local ``-Z`` points, and a transform that does not map that
  axis onto the wall aims it elsewhere. Refer to :ref:`Incorrect coordinates or units <sensors-troubleshooting-symptoms-wrong-place>` and to `Orient the prim`_.
- **Every surface responds alike.** The ``Material`` prims bound to them carry
  no non-visual material label, or the labels they carry are not being read.
  Refer to :ref:`Values look plausible but are wrong
  <sensors-troubleshooting-symptoms-plausible>` and to
  :doc:`Non-Visual Sensor Materials <../../../../materials/nonvisual_sensor_materials>`.

Related
-------

- :doc:`Acoustic generic wpm model <../index>` — ultrasonic simulation and echo envelopes.
- :doc:`USD Attributes <../attributes>` — every attribute group, the mount frame and the default topology.
- :doc:`Outputs <../outputs>` — the ``SignalWays`` channels and params, the first-frames rule and reading an envelope.
- :doc:`Output Configuration <../../../common/output_configuration>` — RenderProducts, RenderVars and the motion BVH switch.
