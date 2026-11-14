.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-core-tutorials:

Tutorials
=========

These tutorials derive Lidar generic core model profiles from manufacturer
specifications. Each includes a completed USD layer you can reference into a
scene, the source of each parameter and checks against the device's published
behavior. See :doc:`../index` for model capabilities and
:doc:`../howto/index` for individual configuration tasks.

See :doc:`../howto/spec_sheet_profile` for the profiling method.

Tutorial profiles
-----------------

:doc:`velodyne_alpha_prime` derives a 128-channel rotary profile from the
manual's nominal channel angles and firing sequence, including maintenance
gaps. It relates RPM, frame rate and ``rotPatternFiringResDeg`` so changes
preserve the firing rate. The resulting layer is
``Velodyne_Alpha_Prime_Rev4.usda``.

:doc:`blickfeld_cube1` derives a solid-state MEMS pattern from the
manufacturer's mirror equations. It calculates 5,850 directions and firing
times and documents four conflicts in the published specifications. It
includes ``Blickfeld_Cube1_Analytic.usda`` and
``generate_blickfeld_cube1_profile.py`` for regenerating the pattern.

:doc:`sick_tim781` models a single laser and detector scanning 811 directions
over 270 degrees at 15 Hz. ``SICK_TiM781.usda`` uses a rotary emitter;
``SICK_TiM781_SolidState.usda`` uses 811 explicit directions and firing times.
The rotary schedule scales with scan rate. The solid-state timing must be
regenerated when the rate changes.

.. figure:: ../../../../img/sensors/nonvisual/lidar_core_tutorial_profiles.avif
   :alt: Three renders of the panel scene from one mount, one below the other, colored by Intensity: the Alpha Prime's 128-line rotary sweep covering the panels and the ground all around, the Cube 1's Lissajous frame on the glass pane and the wall behind it, and the TiM781's single plane as thin lines where it meets the panels at its height.
   :width: 1000

   The three shipped profiles referenced into the panel scene at one mount, one
   below the other, each scan shaded by ``Intensity``: the Alpha Prime's
   128-line rotary sweep, the Cube 1's Lissajous frame of 5,850 pulses on the
   pane ahead and the wall behind it, and the TiM781's single 270-degree plane,
   which meets only the panels at its height. The layers are
   ``Velodyne_Alpha_Prime_Rev4.usda``, ``Blickfeld_Cube1_Analytic.usda`` and
   ``SICK_TiM781.usda`` under ``tutorials/assets/``.

.. toctree::
   :maxdepth: 1

   velodyne_alpha_prime
   blickfeld_cube1
   sick_tim781

.. When adding a tutorial here, add its paragraph above and its toctree entry together
   and in the same order, so the prose and the tree never drift apart.

Configuration topics
--------------------

Each tutorial identifies its sources using
:ref:`source-confidence categories <sensors-recipes-source-confidence>`,
derives a profile, references it into a scene and validates it. Checks cover
parameter acceptance, geometry, timing, range, intensity and comparison with
real captures. The following pages explain individual configuration tasks:

- :doc:`Configure a Firing Pattern <../howto/firing_pattern>`: the
  :ref:`emitter array lengths <sensors-lidar-emitter-array-lengths>`, the
  :ref:`fire-time order <sensors-lidar-fire-time-order>`,
  :ref:`fractional ticks <sensors-lidar-fractional-ticks>`,
  :ref:`channel ids <sensors-lidar-channel-ids>` and the
  :ref:`minimum scan rate <sensors-lidar-min-scan-rate>`.
- :doc:`Constrain the Field of View <../howto/field_of_view>`: the
  :ref:`azimuth window <sensors-lidar-azimuth-window>` and the
  :ref:`range band <sensors-lidar-range-window>`.
- :doc:`Tune Intensity and Point Drops <../howto/intensity>`:
  :ref:`divergence versus waist <sensors-intensity-divergence-or-waist>` and
  :ref:`point drops <sensors-intensity-point-drops>`.
- :doc:`Configure Lidar Output <../howto/output_shaping>`: ``partialOutputs``, scan completion
  and :ref:`steps that deliver no points <sensors-output-shaping-empty-step>`.
- :doc:`Motion Artifacts <../howto/motion_artifacts>`: the
  :ref:`motion BVH and the compensation state <sensors-motion-both-settings>` and the
  :ref:`compensation tokens <sensors-motion-compensation-tokens>`.
- :doc:`USD Attributes <../attributes>`: attribute namespaces, the scan type, the
  :ref:`parameter validation <sensors-lidar-core-invalid-parameters>`,
  :ref:`range accuracy versus resolution <sensors-ref-range-accuracy-vs-resolution>` and
  why :ref:`channel ids are labels <sensors-lidar-core-channel-ids-are-labels>`.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>`:
  :ref:`model identity <sensors-ref-model-identity-vs-plugin>`.
- :doc:`Outputs <../outputs>`: reading the points back, ``Counts``, the valid entries and
  the channel layout.
- :doc:`Sensor Definition Validation <../../../common/validation>`: the introspection
  parameter validation.
- :doc:`Output Configuration <../../../common/output_configuration>`: the RenderProduct
  and RenderVar each profile layer carries.

Reading order
-------------

For rotary sensors, start with :doc:`velodyne_alpha_prime`. For solid-state
patterns, start with :doc:`blickfeld_cube1`, including its treatment of
conflicting sources. :doc:`sick_tim781` compares both representations on one
device.

Each layer includes an ``OmniLidar`` and a RenderProduct requesting
``PointCloud``. The tutorials show how to reference the default prim, select
channels, validate the layer before rendering and compare the results with
measured data.

.. note::

   The profiles are documentation-derived baselines, not certified digital twins of a
   particular hardware unit. Each contains what can be copied or reasonably inferred
   from the public manuals. Behavior those sources do not define, such as unit-specific
   optical power, receiver response and thresholds, noise, corrections and the
   intensity transfer, stays generic or approximate and has to be tuned against
   measured sensor data for higher-fidelity use.

Related
-------

- :doc:`Lidar generic core model <../index>` — what the model simulates, its vocabulary and when to choose it.
- :doc:`USD Attributes <../attributes>` — every attribute the tutorials author, with units, defaults and relations.
- :doc:`How-To <../howto/index>` — one page per decision the tutorials make along the way.
- :doc:`Build a Profile from a Spec Sheet <../howto/spec_sheet_profile>` — the method the tutorials work end to end.
- :doc:`Configure a Firing Pattern <../howto/firing_pattern>` — emitter arrays, ticks and fire times.
- :doc:`Constrain the Field of View <../howto/field_of_view>` — the azimuth window and the range band.
- :doc:`Tune Intensity and Point Drops <../howto/intensity>` — beam shape, intensity and when a return is dropped.
- :doc:`Configure Lidar Output <../howto/output_shaping>` — coordinates, frame of reference and delivery cadence.
- :doc:`Motion Artifacts <../howto/motion_artifacts>` — motion effects while the scan is in progress, and their compensation.
- :doc:`Outputs <../outputs>` — the point cloud the profiles deliver and how to read it back.
- :doc:`Sensor Definition Validation <../../../common/validation>` — the introspection utility behind the parameter validation.
- :doc:`Output Configuration <../../../common/output_configuration>` — the RenderProduct and RenderVars a profile layer carries.
- :doc:`Python: Camera calibration <../../../../examples/python_camera_calibration>` — the other worked procedure in these docs, from photographs to a calibrated camera.
