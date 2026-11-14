.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-overview:

Overview
========

ovrtx brings Omniverse RTX sensor simulation into C and Python applications.
One renderer produces camera images and simulates lidar, radar and acoustic
returns from the same `OpenUSD <https://aousd.org/>`_ scene and materials.
Camera images are path-traced in the default mode.

A sensor consists of a USD prim and a request for its outputs. Start with
:doc:`first_sensor` to configure a lidar and read its point cloud, or choose a
sensor type below.

.. figure:: ../img/sensors/overview/hero_four_sensors.avif
   :align: center
   :alt: A robotics lab full of small wheeled robots seen by the four sensors of one robot: a camera image of the robot crowd, a fisheye image of the whole room, a stereo depth image with the nearest robots in blue and the far ceiling in red, and a lidar point cloud of the room with the robots as blue clusters inside the scan rings.
   :width: 1928

   One scene, four sensors on one robot: the camera's rendered ``LdrColor``
   image (top left); the ``LdrColor`` image of a camera with a 200-degree
   F-theta fisheye lens (top right); the ``DepthSensorDistance`` image of the
   Camera single-view stereo depth model, 0.3 m blue to 10 m red (bottom
   left); and the ``PointCloud`` of a 128-channel rotary Lidar generic core
   model, shaded by ``Intensity`` and seen from behind and above the sensor
   (bottom right). The robotics lab is a demonstration scene, not one of the
   shipped examples.

.. _sensors-overview-modalities:

Sensor types and modalities
---------------------------

Each sensor type produces different data:

- **Cameras:** images of color, geometry, segmentation and object IDs.
  These outputs are called arbitrary output variables (AOVs).
  See :doc:`Camera Outputs <cameras/outputs>`.
- **Lidar:** point clouds with coordinates, counts, intensity and per-point timing.
  See the outputs for :doc:`Lidar generic core <nonvisual/lidar_core/outputs>`
  or :doc:`Lidar generic wpm <nonvisual/lidar_wpm/outputs>`.
- **Radar:** detections with coordinates, counts, radar cross-section and radial
  velocity. See :doc:`Radar Outputs <nonvisual/radar_wpm_dmat/outputs>`.
- **Acoustic:** echo amplitude over time. Each waveform records one receiving
  mount on one channel id. See :doc:`Acoustic Outputs <nonvisual/acoustic_wpm/outputs>`.

- **Raw propagation:** electromagnetic or mechanical path contributions, before
  detector processing. See :doc:`Generic wpm <nonvisual/generic_wpm/index>` and
  its :doc:`Contributions output <nonvisual/generic_wpm/outputs>`.

A RenderProduct requests the outputs you want. Lidar and radar use a composite
``PointCloud`` output; acoustic sensors use ``SignalWays`` and the Generic wpm
model uses ``Contributions``. Their channels are
named tensors. :doc:`Your First Lidar Sensor <first_sensor>` introduces the shared
workflow for configuring sensors and reading outputs.

Non-visual sensors use material labels to calculate surface responses,
independently of camera shading. See :doc:`Non-Visual Sensor Materials <../materials/nonvisual_sensor_materials>`.

Cameras
^^^^^^^

A USD ``Camera`` prim defines the view. Its RenderProduct requests color,
geometry, segmentation or other camera outputs. See :doc:`cameras` for
camera attributes and outputs, and :doc:`cameras/render_modes`
for the three render modes. Real-Time Path Tracing is the default.

Camera sensor APIs add optional processing to these rendered outputs:

- The :doc:`Camera generic core model <visual/camera_core/index>` applies sensor
  response, a color filter array, noise, bit-depth compression and image signal
  processing to a rendered HDR image.
- The :doc:`Camera single-view stereo depth model <visual/depth_camera/index>`
  simulates stereo depth measurements from one rendered view, without a second
  camera render.

Apply the corresponding API schema to the same ``Camera`` prim and request its
outputs on the RenderProduct. A camera can use one of these two sensor schemas,
not both. See :doc:`visual/index` for configuration.

.. figure:: ../img/aovs/rt2/LdrColor.avif
   :align: center
   :alt: A warehouse with a humanoid robot, a quadruped, small wheeled robots, a mobile robot and forklifts, rendered in Real-Time Path Tracing.
   :width: 1280

   The ``LdrColor`` output of a camera product rendered in Real-Time
   Path Tracing: the robot lineup of the semantic-segmentation example in a
   warehouse, with path-traced lighting, reflections and shadows.

.. figure:: ../img/sensors/visual/visual_sensors_strip.avif
   :align: center
   :alt: Robot lineup shown as rendered color, camera-core ISP output, and a depth visualization.
   :width: 100%

   The robot lineup from three cameras at the same pose. Left: rendered
   ``LdrColor``. Center: ``OmniCameraSensorPostIsp`` with a sample camera
   profile. Right: ``DepthSensorOutputVisualization``, black where no
   measurement is reported.

Non-visual sensors
^^^^^^^^^^^^^^^^^^

Lidar, radar and acoustic sensors trace rays to simulate signals reflected
by scene surfaces. See :doc:`Non-Visual Sensors <nonvisual/index>` for the
available models and the differences between the Lidar generic core and
Lidar generic wpm models.

.. figure:: ../../img/example-sensor-lidar.avif
   :align: center
   :alt: Concentric lidar scan rings on a ground plane shaded by intensity, an arrow marking world +X at the center, and a cluster of points on a cube.
   :width: 1265

   The point cloud of the lidar example, a Lidar generic core model rotated to
   look along world +X, the arrow in the picture, at an asphalt ground plane
   and a concrete cube; the scan rings are shaded by ``Intensity`` and the cube
   appears as the dense cluster of points.

.. figure:: ../img/sensors/nonvisual/radar_field_hero.avif
   :align: center
   :alt: Two panels side by side. Left, the radar example's field scene from its preview camera: steel panels on an arc, a steel cube crossing the field, the radar marked with a white dot. Right, a top view of the same step's detections over 10 m range rings, colored by signed radial velocity: the cube's blue, the panels' green.
   :width: 1200

   The radar example's field scene: a Radar generic wpmDmat model watches a
   steel cube cross a field of steel panels over asphalt. Left, the scene from
   its preview camera at one step; right, a top view of that step's detections,
   colored by signed radial velocity: blue approaches the sensor, green is near
   zero, red recedes.

.. figure:: ../img/sensors/nonvisual/acoustic_echo_envelope.avif
   :align: center
   :alt: Top, a line plot of echo amplitude over range from 0 to 5.6 m, flat except for one sharp peak just past 3 m. Bottom, on the same horizontal axis, a side view of the scene: a green dot for the sensor 0.5 m above a gray ground band at the left, arrows for the pulse and its echo, and a 1.25 m tall concrete wall whose near face stands at 3 m, under the peak.
   :width: 1200

   The acoustic example's echo amplitude plotted against range, calculated
   from round-trip travel time. Below, the scene uses the same distance axis:
   the sensor sits 0.5 m above asphalt and fires along +X toward a concrete
   wall 3 m ahead. The peak marks the wall's echo.

.. _sensors-overview-finding-your-way:

Documentation guide
-------------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 26 74

   * - Section
     - Covers
   * - :doc:`Your First Lidar Sensor <first_sensor>`
     - Learn how to configure a lidar, render a scan and read its point cloud in Python or C.
   * - :doc:`Common Concepts <common/index>`
     - Sensor configuration, RenderProducts, outputs, runtime changes,
       capture rates.
   * - :doc:`Cameras <cameras>`
     - Camera settings, lens calibration, rolling shutter, render modes, outputs
       and :doc:`scene partitions <cameras/scene_partitions>`.
   * - :doc:`Visual Sensors <visual/index>`
     - Camera sensor response, noise, image signal processing and stereo depth.
   * - :doc:`Non-Visual Sensors <nonvisual/index>`
     - Lidar, radar and acoustic models, their settings and outputs.
   * - :doc:`Reference <reference/index>`
     - :doc:`Sensor schemas <reference/schemas>`,
       :doc:`lens distortion schemas <reference/schemas_lens_distortion>`, and the
       :doc:`glossary <reference/glossary>`.
   * - :doc:`Troubleshooting <troubleshooting/index>`
     - :doc:`Symptoms, causes and fixes <troubleshooting/symptoms>` and
       :doc:`model limitations <troubleshooting/limitations>`.

Each model section has an overview, settings, how-tos and output reference.
How-tos cover specific tasks. For step-by-step guides to configuring sensors
from real-world data, use these tutorials:

- :doc:`Camera calibration <../examples/python_camera_calibration>`: calibrate a USD camera
  from checkerboard photographs taken with a physical camera.
- :doc:`Lidar generic core profiles <nonvisual/lidar_core/tutorials/index>`:
  build lidar profiles from manufacturer specifications and manuals.

For runnable Python and C code, see the :doc:`example gallery <../examples/index>`.

Related
-------

The sections of the Sensors part, in reading order, are in the
:ref:`table above <sensors-overview-finding-your-way>`. The pages it does not
list:

- :doc:`Glossary <reference/glossary>` — the shared vocabulary, from AOV and channel to signal way.
- :doc:`Examples <../examples/index>` — the runnable Python and C examples, including sensor simulation examples.
- :doc:`Getting Started in Python <../python_api/getting_started>` and :doc:`Getting Started in C <../c_api/getting_started>` — installing ovrtx and running the minimal example before you add a sensor.
- :doc:`Hardware & Driver Requirements <../driver_requirements>` — the hardware and the NVIDIA drivers ovrtx runs on.
