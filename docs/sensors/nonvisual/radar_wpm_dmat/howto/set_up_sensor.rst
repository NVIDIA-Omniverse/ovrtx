.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-radar-howto-set-up-sensor:

Set Up a Radar Sensor
=====================

The Radar generic wpmDmat model produces detections with position, radial
velocity and radar cross section. A scene needs an ``OmniRadar`` prim with
``OmniSensorGenericRadarWpmDmatAPI`` and a RenderProduct requesting
``PointCloud``. This procedure configures a radar viewing a moving cube and
a field of panels, then reads the detections.

The example ships two scenes. Its default, ``radar_example.usda``, holds a
moving steel cube and a static concrete cube and is described on
:doc:`Python: Radar Sensor <../../../../examples/python_sensor_radar>`. This
page builds the alternative, ``radar_example_field.usda``, selected with
``--scene radar_example_field.usda``: the same moving cube crossing a field of
33 thin steel panels, scanned by a radar whose single scan is laid out
explicitly, bins and limits included, rather than left at the schema defaults.

Before you start. See :doc:`../index` for the simulation model and :doc:`../outputs` for
channel definitions. If this is your first sensor scene, start with
:doc:`../../../first_sensor`.

Run the :doc:`Python radar example <../../../../examples/python_sensor_radar>`
with the panel-field scene:

.. code-block:: bash

   cd examples/python/radar
   uv run main.py --scene radar_example_field.usda

The :doc:`C radar example <../../../../examples/c_sensor_radar>` drives the same
scene when you pass the file's path as its first argument. Both examples ship an
identical copy of the file, and the USDA snippets below are taken from the
Python example's copy.

.. _sensors-nonvisual-radar-howto-set-up-sensor-prim:

Author the sensor prim
----------------------

Apply ``OmniSensorGenericRadarWpmDmatAPI`` to an ``OmniRadar`` prim.
It includes the shared attributes and first scan, ``s001``. The
:doc:`defaults <../attributes>` produce a working radar without further
attributes; see :ref:`schema instances
<sensors-common-sensor-configuration-instances>` and
:doc:`sensor authoring <../../../common/sensor_configuration>`.

The example below explicitly sets coordinate representation and reference
frame, trace depth, CFAR mode, 10 Hz frame rate and prim transform. It also
sets the scan's bins, limits, antenna gain, CFAR neighborhood, noise and
velocity sequence.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../examples/python/radar/radar_example_field.usda
         :language: usda
         :start-after: # [snippet:configure-radar-field-sensor]
         :end-before: # [/snippet:configure-radar-field-sensor]
         :caption: ``radar_example_field.usda``, from the runnable :doc:`Python radar example <../../../../examples/python_sensor_radar>`; the :doc:`C radar example <../../../../examples/c_sensor_radar>` ships the same scene
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-radar-field-sensor-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-radar-field-sensor-python]
         :dedent:

``omni:sensor:WpmDmat:elementsCoordsType`` chooses how the three coordinates of
a detection arrive. The scene sets it to ``CARTESIAN`` in place of the
``SPHERICAL`` default, so the ``Coordinates`` channel arrives as x, y and z in
meters, and writes ``outputFrameOfReference`` out at its ``SENSOR`` default;
:ref:`the output group <sensors-nonvisual-radar-attributes-output-group>`
on USD Attributes explains both representations and the frame of reference
that goes with them. The two other sensor-level attributes the scene authors
are covered on the same page, under
:ref:`traceTreeDepth <sensors-nonvisual-radar-attributes-trace-depth>` and
:ref:`cfarMode <sensors-nonvisual-radar-attributes-cfar-mode-scope>`.
``omni:sensor:frameRate`` is a rational number in Hz, so ``(10, 1)`` is 10 Hz:
how often the radar completes a scan, which
:ref:`the radar frame rate <sensors-nonvisual-radar-attributes-frame-rate>` on
USD Attributes and
:ref:`frame-rate behavior <sensors-common-multi-rate-frame-rate>` on
Sensor Scheduling explain.

The example authors these values under ``scan:s001``:

- **Bins:** with ``binsFromSpec = false``, the authored counts are used directly:
  112 range, 161 velocity, 12 azimuth and 2 elevation bins.
  See :ref:`Bins <sensors-nonvisual-radar-attributes-bins>`.
- **Coverage:** maximum range 90 m; azimuth and elevation half-angles 75° and 10°.
  See :ref:`Field of view <sensors-nonvisual-radar-attributes-fov>`.
- **Antenna:** both elements use ``CONSTANT`` gain.
  See :ref:`Antenna <sensors-nonvisual-radar-attributes-antenna>`.
- **Detection:** CFAR uses one neighboring test cell on each side in range and
  velocity, with no guard cells. See :ref:`CFAR <sensors-nonvisual-radar-attributes-cfar>`.
- **Noise:** all inputs, including CFAR noise, have zero mean and deviation.
  See :ref:`Noise <sensors-nonvisual-radar-attributes-noise>`.
- **Velocity sequence:** one entry, ``16.33``.
  See :ref:`Velocity sequence <sensors-nonvisual-radar-attributes-velocity-cycle>`.

Some values explicitly repeat the schema defaults. Unauthored settings,
including processing mode and aliasing switches, retain the defaults listed
in :doc:`../attributes`.

.. _sensors-nonvisual-radar-howto-set-up-sensor-orientation:

Orient the prim
^^^^^^^^^^^^^^^

The sensor looks along its local ``-Z`` axis, as every sensor prim does (refer
to :ref:`sensors-common-sensor-configuration-orientation`), so in a Z-up scene
rotate the prim until ``-Z`` points where you want the field of view to go. The
scene's ``xformOp:rotateXYZ = (90, 0, -90)`` turns local ``-Z`` onto world
``+X``, toward the field of panels and the moving cube, and keeps local ``+Y``
pointing up, so that the field of view stays level; ``xformOp:translate = (0, 0, 1)``
puts the radar 1 m above the ground plane, at the height of the panels'
centers. The mount is the one the default scene uses.

.. _sensors-nonvisual-radar-howto-set-up-sensor-output:

Request the PointCloud output
-----------------------------

A RenderProduct whose ``camera`` relationship targets the sensor prim renders
through it, and the RenderVars in its ``orderedVars`` say what it delivers
(refer to :ref:`sensors-common-output-configuration-renderproduct` and
:ref:`sensors-common-output-configuration-rendervar`). This model has one output
to request, a RenderVar with ``sourceName`` ``PointCloud``, and the RenderVar's
``channels`` attribute lists the per-detection tensors the frame should carry:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../examples/python/radar/radar_example_field.usda
         :language: usda
         :start-after: # [snippet:configure-radar-field-output]
         :end-before: # [/snippet:configure-radar-field-output]
         :caption: ``radar_example_field.usda``, from the runnable :doc:`Python radar example <../../../../examples/python_sensor_radar>`
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-example-configure-radar-field-output-python]
         :end-before: # [/snippet:doc-nonvisual-example-configure-radar-field-output-python]
         :dedent:

The scene requests ``RCS`` as well as ``RadialVelocityMs``, so every detection
arrives with its radar cross section beside its radial velocity, and the
figures under :ref:`Verification <sensors-nonvisual-radar-howto-set-up-sensor-verify>`
color the detections by each in turn. ``Counts`` and ``Flags`` arrive whether or
not you list them.
:ref:`Requesting the output <sensors-nonvisual-radar-outputs-requesting>` on
Outputs names every channel you can list, and its
:ref:`channel table <sensors-nonvisual-radar-outputs-channels>` says what each
one holds.

The second product in the same ``Render`` scope, ``CameraProduct``, is not a
sensor output. It renders through the scene's ``PreviewCamera`` and requests
``LdrColor``: the camera view of the field, there so that the scene can be
looked at, and the example never steps it. The camera animation under
:ref:`Verification <sensors-nonvisual-radar-howto-set-up-sensor-verify>`
was rendered through it.

.. _sensors-nonvisual-radar-howto-set-up-sensor-materials:

Label the surfaces
------------------

The non-visual sensors use the non-visual material labels
(``omni:simready:nonvisual:*``) on the ``Material`` prim bound to a surface for
calculating their responses, not the surface shader. The scene has two
materials, labeled ``asphalt`` for the ground plane and ``steel`` for the panels
and the moving cube:

The complete material definitions are in
:download:`radar_example_field.usda <../../../../../examples/python/radar/radar_example_field.usda>`.

Each ``Material`` prim also carries a visual shader, so one prim serves the
radar and the preview camera; :doc:`../../../../materials/nonvisual_sensor_materials` explains the
label vocabulary, where the labels live and how a material that also drives
visual rendering keeps its shader beside them.

.. _sensors-nonvisual-radar-howto-set-up-sensor-targets:

Place the targets
-----------------

The targets are what the scan above is laid out for. Thirty-three thin steel
panels, 2 m tall, a quarter of a meter thick and wider the farther out they
stand, are spread across the field of view from about 10 m out to nearly the
90 m maximum range, each turned to face the radar with its front face centered
in a range bin of its own, so that no two panels share a range bin; their
angular footprints do not overlap either. The moving steel cube of the default
scene crosses the field with its transform time-sampled from ``(30, 4, 0.75)``
at time code 0 to ``(20, 4, 0.75)`` at time code 10, one meter closer to the
radar per 0.1 s step, a closing speed of 10 m/s.

The complete target layout are in
:download:`radar_example_field.usda <../../../../../examples/python/radar/radar_example_field.usda>`.

.. _sensors-nonvisual-radar-howto-set-up-sensor-motion-bvh:

Create the renderer with the motion BVH enabled
-----------------------------------------------

This model needs an active motion BVH for motion effects, with ``AUTO`` or
``ENABLE``. Create the renderer with ``ENABLE``, as the example does. The Python
snippet also creates the stage the scene is loaded into and attaches it to the
renderer:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../../../examples/python/radar/main.py
         :language: python
         :start-after: # [snippet:create-renderer]
         :end-before: # [/snippet:create-renderer]
         :dedent:
         :emphasize-lines: 9
         :caption: ``main.py``, from the runnable :doc:`Python radar example <../../../../examples/python_sensor_radar>`

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../../../examples/c/radar/main.cpp
         :language: cpp
         :start-after: // [snippet:create-renderer]
         :end-before: // [/snippet:create-renderer]
         :dedent:
         :emphasize-lines: 11
         :caption: ``main.cpp``, from the runnable :doc:`C radar example <../../../../examples/c_sensor_radar>`

:ref:`sensors-common-output-configuration-motion-bvh` describes the switch in
full: the modes, the C call, its lifetime and GPU support.
:ref:`sensors-nonvisual-radar-index-motion-bvh` states the requirement for this
model, and
:ref:`the motion BVH on Simulate Moving Targets <sensors-nonvisual-radar-howto-moving-targets-motion-bvh>`
says what the radar does without it.

.. _sensors-nonvisual-radar-howto-set-up-sensor-warm-up:

Load the scene and warm up
--------------------------

Open the USDA named by ``--scene`` into the attached stage and wait until that
write has landed, so the sensor and its product exist before the first step:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../../../examples/python/radar/main.py
         :language: python
         :start-after: # [snippet:load-radar-scene]
         :end-before: # [/snippet:load-radar-scene]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../../../examples/c/radar/main.cpp
         :language: cpp
         :start-after: // [snippet:load-radar-scene]
         :end-before: // [/snippet:load-radar-scene]
         :dedent:

Warm the renderer up before you read a frame. The example places the scene's
animation at time zero and takes three steps there before the animated loop
begins; each step renders the radar product and advances the simulation by
0.1 s, one scan period at the authored 10 Hz, so that every step fires one
scan:

.. tab-set::

   .. tab-item:: Python
      :sync: python

      .. literalinclude:: ../../../../../examples/python/radar/main.py
         :language: python
         :start-after: # [snippet:warm-up-radar]
         :end-before: # [/snippet:warm-up-radar]
         :dedent:

   .. tab-item:: C
      :sync: c

      .. literalinclude:: ../../../../../examples/c/radar/main.cpp
         :language: cpp
         :start-after: // [snippet:warm-up-radar]
         :end-before: // [/snippet:warm-up-radar]
         :dedent:

.. note::

   :ref:`sensors-common-output-configuration-warmup` counts the sensor
   pipeline among the reasons to warm the renderer up, beside texture
   streaming and path-tracing convergence. Why the step length matters is on
   :ref:`the radar frame rate <sensors-nonvisual-radar-attributes-frame-rate>` and, for every
   sensor, on :doc:`../../../common/multi_rate`.

.. _sensors-nonvisual-radar-howto-set-up-sensor-read:

Step the scene and read the detections
--------------------------------------

The :doc:`Python <../../../../examples/python_sensor_radar>` and
:doc:`C <../../../../examples/c_sensor_radar>` examples step by 0.1 s and
print the valid-entry count and radial-velocity range for each frame.

To read detections, map ``PointCloud`` to CPU memory, limit reads to
``Counts[0]`` and filter by the ``VALID`` bit. Convert the component-first
``Coordinates`` layout to one row per detection if needed. See the paired
:ref:`reading examples <sensors-nonvisual-radar-outputs-reading>` and
:doc:`sensor-output mapping, synchronization and lifetime rules
<../../../common/sensor_outputs>`.

.. _sensors-nonvisual-radar-howto-set-up-sensor-verify:

Verification
------------

Run the example with the panel-field scene and expect one printed line per
step. In the recorded run shown below, frames contained 35–37 valid points.
The minimum radial velocity was near −9.9 m/s for the approaching cube;
the maximum was near zero for the stationary panels. Its first line was
``step 1: valid points=35, radial velocity min/max=[-9.921682357788086, 0.0003972465347032994] m/s``.
These are example observations, not required counts or exact results for
other runs.

Expect negative radial velocity from the approaching cube. Its motion is the
same in both example scenes; see :ref:`Doppler measurements
<sensors-nonvisual-radar-howto-moving-targets-reports>` for the derivation.
The expected velocity is within the ±16.33 m/s interval configured by the
scan's one-entry velocity sequence.

.. list-table::
   :class: compact-table
   :widths: 34 33 33

   * - .. image:: ../../../../img/sensors/nonvisual/radar_field_camera.gif
          :alt: The field scene from its preview camera over the ten steps: thin steel panels standing on dark asphalt in an arc that sweeps from near the radar to the far side of the field, the steel cube advancing through the middle of the field, and the radar's position marked by a white dot; each frame is labeled with its step number and time.
          :width: 100%
     - .. image:: ../../../../img/sensors/nonvisual/radar_field_top_doppler.gif
          :alt: Top view of each step's detections, the radar at the bottom edge looking up the image inside 10 m range rings: the panels' detections in green along an arc across the field of view, the cube's detection in blue moving down the image step by step, and a color bar from -10 to +10 m/s of RadialVelocityMs; each frame is labeled with its step number and time.
          :width: 100%
     - .. image:: ../../../../img/sensors/nonvisual/radar_field_top_rcs.gif
          :alt: The same top view of each step's detections, colored by RCS on a color bar from 15 to 55 dBsm; each frame is labeled with its step number and time.
          :width: 100%

The scene over the ten steps, three views of the same frames. Left, the camera
view through ``PreviewCamera``, the radar marked white: the moving cube
crossing the field of panels.
Center, a top view of each step's detections with the radar at the bottom edge
looking up the image and 10 m range rings, colored by ``RadialVelocityMs`` on a
±10 m/s scale, blue closing, green still, red receding: the cube's detection
comes out blue, the panels' green. Right, the same detections colored by
``RCS`` on a fixed 15 to 55 dBsm scale. The three animations are
frame-synchronous and carry the step number and time in their corner.

The example's Rerun viewer also colors detections by signed radial velocity.
Use the :ref:`enabled/disabled comparison
<sensors-nonvisual-radar-howto-moving-targets-verify>` on this scene to check
that motion BVH affects target velocity.

A scan that detects no targets is still published with ``Counts[0] = 0``
and scan metadata; the example prints ``valid points=0``. A step without a
radar firing returns no radar ``PointCloud`` frame. See :ref:`empty scans
<sensors-nonvisual-radar-outputs-empty-scan>`.

.. _sensors-nonvisual-radar-howto-set-up-sensor-symptoms:

Potential issues
----------------

- The viewer shows two targets instead of the panel field: check which scene
  was loaded. The example prints the scene it opens
  (``Loading radar scene from ...``); pass ``--scene radar_example_field.usda``
  from the example's directory, or the file's full path from anywhere else.
- Some steps return no radar frame: the steps may be shorter than the radar's
  scan period, so only a step that contains one of the radar's acquisition
  times fires a scan. Step the product at the scan period, as the example does
  (:ref:`Step at the scan period <sensors-nonvisual-radar-howto-scan-configurations-stepping>`).
- Detections arrive, but the moving cube's radial velocity stays near zero, so
  the printed minimum sits near zero instead of near -10 m/s: the renderer was
  created without the motion BVH, or on a GPU that cannot trace against motion.
  :ref:`The model needs the motion BVH <sensors-nonvisual-radar-howto-moving-targets-motion-bvh>`
  says what the radar does without it, and
  :ref:`sensors-common-output-configuration-motion-bvh` how to set it and which
  GPUs support it.
- The cloud looks plausible but lies in the wrong place, or carries angles where
  you expected meters: the coordinate system or the frame of reference is not
  the one you assumed. Read the ``coordsType`` and ``frameOfReference`` params
  of the frame first
  (:ref:`Reading the output <sensors-nonvisual-radar-outputs-reading>`) and
  check the three attributes of
  :ref:`the output group <sensors-nonvisual-radar-attributes-output-group>`.
- Published frames print ``valid points=0``: the acquisitions produced no valid
  detections. Check the target's position, range, materials and detection
  thresholds per :doc:`validate_parameterization`. An :ref:`empty scan
  <sensors-nonvisual-radar-outputs-empty-scan>` has a delivered count of zero;
  tensor capacity does not imply that detections are present.
- The labels seem to make no difference: an attribute of the wrong type or a
  misspelled token keeps a label from being read.
  :doc:`../../../../materials/nonvisual_sensor_materials` describes label authoring;
  :doc:`../../../troubleshooting/symptoms` lists the checks to make, in order.

Related
-------

- :doc:`Radar generic wpmDmat model <../index>` — what the model simulates and how a detection comes about.
- :doc:`USD Attributes <../attributes>` — the output group, the frame rate, the bins, field of view, antenna, CFAR and noise attributes the scan authors, and the model's other attribute groups.
- :doc:`Outputs <../outputs>` — the ``PointCloud`` channels and params, empty scans and reading a frame back.
- :doc:`Simulate Moving Targets <moving_targets>` — the animation loop in full, what the radar does without the motion BVH and how to check that it was active.
- :doc:`Output Configuration <../../../common/output_configuration>` — RenderProducts, RenderVars, warm-up and the motion BVH switch.
- :doc:`Python radar example <../../../../examples/python_sensor_radar>` and :doc:`C radar example <../../../../examples/c_sensor_radar>` — the runnable examples this page takes its snippets from: the field scene both ship and the Python example's code; the Python page describes the default scene and the ``--scene`` option.
