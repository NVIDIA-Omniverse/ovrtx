.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-depth-camera:

Camera single-view stereo depth model
=====================================

The Camera single-view stereo depth model simulates stereo depth measurements
from one rendered view. It post-processes the renderer's color, distance and
position outputs.

.. _sensors-visual-depth-camera-disparity:

A stereo depth camera does not measure distance directly. It photographs the
scene from two places a known baseline apart, matches the two pictures, and turns
the horizontal displacement between matching pixels, the *disparity*, into a
distance. Everything that makes such a camera hard to use follows from that: no
depth where the two views disagree, because one imager sees what the other
cannot; no depth where a surface is too smooth to match; coarse depth far away,
because one pixel of disparity spans more distance the farther the surface is;
and a distance that is quantized rather than continuous.

The Camera single-view stereo depth model reproduces those consequences from a
**single rendered view**. It takes the distance the renderer already
computed for each pixel, converts it to a disparity, reprojects it to the pixel
where a second imager would have seen it, adds disparity noise and quantization,
and discards everything a real matcher could not have recovered. If you want to
mimic an active stereo camera, a simulated infrared projector accepts untextured
surfaces within a distance you set. The result is a depth image that behaves like
a stereo camera's, with no second render and no matching algorithm.

.. _sensors-visual-depth-camera-what-it-simulates:

What it simulates
-----------------

.. _sensors-visual-depth-camera-reconstructed-depth-data:
.. _sensors-visual-depth-camera-not-ground-truth:
.. _sensors-depth-sensor-not-ground-truth:

Reconstructed depth data
^^^^^^^^^^^^^^^^^^^^^^^^

The Camera single-view stereo depth model simulates a stereo camera's depth
measurements, including missing measurements, disparity noise and quantization.
For distances directly from the renderer, use ``DistanceToImagePlaneSD`` or
``DistanceToCameraSD``, described in :doc:`Cameras: Outputs <../../cameras/outputs>`.

.. _sensors-visual-depth-camera-where-it-sits:

Post-processing of renderer outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The model reads three renderer outputs and publishes five sensor outputs on
the same RenderProduct. :ref:`Inputs
<sensors-visual-depth-camera-outputs-inputs>` lists the required inputs, and
:doc:`Cameras: Outputs <../../cameras/outputs>` defines their types and units.
Apply ``OmniSensorGenericDepthSensorSingleViewAPI`` to the ``Camera`` prim the
RenderProduct renders through; :doc:`USD Attributes <attributes>` describes the
configuration.

The :doc:`Camera generic core model <../camera_core/index>` provides independent
sensor and ISP post-processing. Its input is ``HdrColor``; its RAW and processed
:ref:`primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` are
separate from this depth model's outputs. Both models can use the same
RenderProduct.

.. _sensors-visual-depth-camera-what-you-get:

What you get
------------

Five outputs come back, requested as RenderVars on the same product like any
camera output:

- ``DepthSensorDistance``: the simulated distance image.
- ``DepthSensorPointCloudPosition``: the point cloud, one point per pixel.
- ``DepthSensorPointCloudColor``: the color of each point.
- ``DepthSensorImager``: the luminance the simulated imager saw.
- ``DepthSensorOutputVisualization``: one diagnostic image, chosen by
  ``rgbDepthOutputMode``.

:doc:`Outputs <outputs>` gives each one's type and shape, :ref:`what a zero
means <sensors-visual-depth-camera-outputs-invalid-entries>` and :ref:`the
stages that discard a value <sensors-visual-depth-camera-outputs-stages>`, in
the order to check when a value is missing. The attributes that set how much
disparity a distance produces, and with it the width of the holes and the near
limit, are the optics group on :doc:`USD Attributes <attributes>`.

.. figure:: ../../../img/sensors/visual/depth_camera_beauty_shot.avif
   :alt: Three panels of one fisheye frame of a Cornell box: the rendered color image with a red wall, a green wall, a magenta box and a blue sphere; the renderer's distance output in a magenta-to-yellow color scale; the model's depth visualization in the same scale, shifted to the right, with black holes beside the box and the sphere, a black band along the left edge, black where the floor is nearer than the near limit, and black outside the lens's image area.
   :width: 1408

   One frame of a Cornell box test scene's fisheye depth product, three times.
   Left, the rendered ``LdrColor`` input; center, the renderer's
   ``DistanceToImagePlaneSD`` input, displayed with the color
   scale of the right panel; right, the model's
   ``DepthSensorOutputVisualization`` in mode 3, near surfaces magenta and
   red, far ones yellow, no measurement black. The depth image has holes
   beside the tall box and the sphere where the second imager would not see
   the surface, an empty band along the left edge where that imager would
   look past the rendered view, and nothing for the floor nearest the camera,
   closer than its near limit. Noise is off, so every missing value comes from
   the geometry.

.. _sensors-visual-depth-camera-features:

Features at a glance
--------------------

- A RenderProduct that renders through a camera, has the model's API schema applied
  and requests the three camera outputs the model reads and the five it writes,
  with several depth products in one step, cameras with different projections
  and a tiled product
  (:doc:`Set Up a Depth Product <howto/set_up_depth_product>`).
- Noise and quantization that move measurements along their image row, and a
  confidence test that decides which pixels get a measurement at all, each
  change checked against the model's own confidence map
  (:doc:`Tune Noise, Quantization and Confidence <howto/noise_and_confidence>`).
- A device's published specification turned into a depth product that behaves
  like the device, with the datasheet fields and their attributes, the near
  limit that the maximum disparity and the product width set together, and the
  unit conversions
  (:doc:`Build a Profile from a Spec Sheet <howto/spec_sheet_profile>`).
- The inputs and the set of RenderVars the pipeline needs, the stages that produce
  and discard values, the five outputs with type and shape, what a zero means,
  the two frames, units and the visualization modes (:doc:`Outputs <outputs>`).

.. _sensors-visual-depth-camera-when-to-use:

When to use it
--------------

Use this model when the thing under test is a perception stack that will consume
a depth camera's output, on a robot, a vehicle or a virtual factory floor. Such a
system must process occlusion holes, missing measurements on smooth surfaces,
quantization that coarsens with distance and noise that changes between frames.
The model simulates these effects in a controlled scene. The parameters belong to the Camera prim. To simulate different devices in
the same step, use separate Cameras and RenderProducts, with each Camera
authoring its own baseline, optics and noise;
:doc:`Set Up a Depth Product <howto/set_up_depth_product>` shows how, and
:doc:`Build a Profile from a Spec Sheet <howto/spec_sheet_profile>` takes the
numbers from a device's published specification.

.. _sensors-visual-depth-camera-what-it-does-not-model:

What it does not model
^^^^^^^^^^^^^^^^^^^^^^

These are by-design limits of the model, not misconfigurations; the
:doc:`Limitations <../../troubleshooting/limitations>` page points here.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Not modeled
     - Consequence
   * - A second render
     - There is one rendered view. The second imager exists only as a
       reprojection of the first, so anything hidden from the rendered view is
       hidden from both.
   * - Stereo matching
     - No correspondence search is performed and no mismatches are produced.
       The errors present are the ones these pages describe, occlusion holes,
       confidence culling, disparity quantization and noise, and not the false
       matches a real matcher makes on repeating patterns.
   * - Per-pixel timing
     - The model adds no time structure of its own: no output contains a
       timestamp or a per-pixel time offset, and every pixel of a frame is
       processed identically. Whatever timing the rendered frame already had,
       for example from a :doc:`rolling shutter <../../cameras/rolling_shutter>`,
       is what you have.
   * - Materials and illumination, physically
     - Surface response reaches this model only through the tone-mapped color
       image, as texture in the confidence test. There is no infrared
       reflectance, and no :doc:`material property <../../../materials/nonvisual_sensor_materials>`
       changes the reported distance.
   * - Scene units
     - No unit conversion is applied to the inputs, so the distance image and
       the point cloud inherit the units of the outputs they are computed from;
       :ref:`Outputs <sensors-visual-depth-camera-outputs-units>` states which
       unit each one is in.

.. _sensors-visual-depth-camera-how-it-is-authored:

How it is authored
------------------

The model's attributes are authored on the ``Camera`` prim; its outputs are
requested on the RenderProduct that renders through that camera. The smallest
complete setup applies ``OmniSensorGenericDepthSensorSingleViewAPI`` to the camera,
points the product's ``rel camera`` at it, and requests the three camera outputs
the model reads and the five it writes (the RenderProduct and its RenderVars are
:doc:`Output Configuration <../../common/output_configuration>`); the five
attribute values written out are the schema defaults. Applying an API schema in general
is on :doc:`Sensor Configuration <../../common/sensor_configuration>`.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../tests/docs/usd/data/depth_sensor_render_product.usda
         :language: usda
         :start-after: # [snippet:doc-depth-sensor-render-product]
         :end-before: # [/snippet:doc-depth-sensor-render-product]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-depth-sensor-render-product-python]
         :end-before: # [/snippet:doc-depth-sensor-render-product-python]
         :dedent:

This model ships without a public example: no project in the
:doc:`example gallery <../../../examples/index>` runs it. The authoring is on
the pages under this model.
:doc:`Set Up a Depth Product <howto/set_up_depth_product>` builds a complete
product, with the schema applied and all eight RenderVars requested, and runs
and reads it. :doc:`USD Attributes <attributes>` gives the attributes you
author on that product, and :doc:`Outputs <outputs>` gives the outputs and how
to read them. Creating a renderer, stepping it and reading an output back are
the same for every sensor and are walked through in
:doc:`Your First Lidar Sensor <../../first_sensor>`. Warm the renderer up before you
judge coverage
(:ref:`Outputs <sensors-visual-depth-camera-outputs-invalid-entries>` has the
note).

Pages under this model
----------------------

Use :doc:`attributes` for controls and clamps, and :doc:`howto/index` to build
and tune a depth product. Read :doc:`outputs` before mapping images or points:
it defines required inputs, invalid values, units and coordinate frames.

.. toctree::
   :maxdepth: 1

   attributes
   howto/index
   outputs

Related
-------

- :doc:`Cameras <../../cameras>` and its :doc:`Outputs <../../cameras/outputs>` — the rendered color and distance inputs used by this model.
- :doc:`Camera generic core model <../camera_core/index>` — sensor and ISP post-processing of the renderer's ``HdrColor`` output.
- :doc:`Output Configuration <../../common/output_configuration>` — authoring the RenderProduct and its RenderVars.
- :doc:`Sensor Outputs <../../common/sensor_outputs>` — mapping an output and reading it back.
- :doc:`Lidar generic core model <../../nonvisual/lidar_core/index>` and :doc:`Radar generic wpmDmat model <../../nonvisual/radar_wpm_dmat/index>` — sensors that trace the scene themselves, for comparison.
- :doc:`Glossary <../../reference/glossary>` — AOV and the other terms shared by every sensor, with pointers to the model pages for the ones that mean different things per model.
