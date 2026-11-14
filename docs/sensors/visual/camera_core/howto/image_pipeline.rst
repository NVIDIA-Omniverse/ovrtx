.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-camera-core-howto-image-pipeline:
.. _sensors-do-camera-isp-pipeline:

Shape an Image Like a Camera Sensor
===================================

**Goal.** Add a mosaic pattern, sensor noise, bit-depth compression and optional
image signal processor (ISP) processing to a rendered image. Apply the model's
schema, request its input and a primary output, then inspect the output shapes.
Optional diagnostic outputs expose intermediate stages.

**Before you start.** Have a camera that renders an image and
:doc:`configure its input <input_image>`. See :doc:`../index` for the simulated
stages, :doc:`../attributes` for controls, and :doc:`../outputs` for output names
and formats. The :doc:`companding_and_isp` guide verifies ISP processing.

Apply the schema
----------------

Apply ``OmniSensorGenericCameraCoreAPI`` to the ``Camera`` prim you already
render through. What that implies, that the sensor is the camera itself and its
intrinsics keep governing the view, is on :doc:`USD Attributes <../attributes>`.
How an API schema is applied to a prim, in USDA or through the ``usd-core``
Python API, is described in
:doc:`Sensor Configuration <../../../common/sensor_configuration>`.

This task leaves every attribute of the schema at its default. One default has
a scheduling consequence: the schema sets ``omni:sensor:frameRate`` to
``(30, 1)``, so the camera is scheduled at 30 Hz rather than rendering on every
step; author ``(0, 1)`` to leave it unscheduled, as
:doc:`Sensor Scheduling <../../../common/multi_rate>` explains. The
model's own attributes live in the ``omni:sensor:core:`` namespace, spelled
with a lower-case ``core``; :doc:`USD Attributes <../attributes>` explains that
namespace and what each attribute group does. The sibling how-tos are where you
change them:
:doc:`Author a Color Filter Array <color_filter_array>` for the mosaic,
:doc:`Compand to a RAW Format and Run the ISP <companding_and_isp>` for the
transport bit depth and the ISP program, and
:doc:`Configure the Input Image <input_image>` for the product-side choices
that decide what the model sees.

Request the input and a primary output
--------------------------------------

The model publishes its results as AOVs on the RenderProduct bound to the
camera, requested like any other output: a ``RenderVar`` whose ``sourceName``
names them (:doc:`Output Configuration <../../../common/output_configuration>`
introduces RenderProduct and RenderVar). On that product, request two things:

- ``HdrColor``, the linear high-dynamic-range render that is the pipeline's
  only input, requested on the same product as the model's outputs.
  :doc:`Configure the Input Image <input_image>` states that requirement and
  what happens without it, the input precision and the render mode behind it.
- One :ref:`primary output <sensors-visual-camera-core-outputs-primary-outputs>`:
  ``OmniCameraSensorPostIsp`` for the full pipeline, or
  ``OmniCameraSensorPreIsp`` to stop before the ISP and read the sensor's RAW
  codes. The linked section of :doc:`Outputs <../outputs>` states which
  primary output builds how much of the pipeline and what happens when both or
  neither are requested.

``OmniCameraSensorPostIsp`` carries a processed image only once you have
authored an ISP program (:ref:`Supply the ISP program
<sensors-visual-camera-core-howto-companding-and-isp-isp-program>`); until
then, use ``OmniCameraSensorPreIsp`` as the primary output, which needs none.

The fragment below applies the schema to a camera and binds a RenderProduct to
it that requests ``HdrColor`` and ``OmniCameraSensorPostIsp``. Swap the
primary output's name for ``OmniCameraSensorPreIsp`` to stop before the ISP.

.. code-block:: usda

   def Camera "SensorCamera" (
       prepend apiSchemas = ["OmniSensorGenericCameraCoreAPI"]
   )
   {
   }

   def Scope "Render"
   {
       def RenderProduct "SensorCamera"
       {
           int2 resolution = (1920, 1080)
           rel camera = </SensorCamera>
           rel orderedVars = [<HdrColor>, <OmniCameraSensorPostIsp>]

           def RenderVar "HdrColor"
           {
               string sourceName = "HdrColor"
           }

           def RenderVar "OmniCameraSensorPostIsp"
           {
               string sourceName = "OmniCameraSensorPostIsp"
           }
       }
   }

In the ``usd-core`` Python API the same product is authored as the RenderProduct
examples on :doc:`Output Configuration <../../../common/output_configuration>`
show, one ``RenderVar`` per name listed in ``orderedVars``, with the schema
prepended to the camera prim as
:doc:`Sensor Configuration <../../../common/sensor_configuration>` shows.

Add diagnostic taps
-------------------

The model has seven output names. Two are the primary outputs of the previous step;
the other five are :ref:`diagnostic taps <sensors-visual-camera-core-outputs-taps>` on the intermediate stages. Add any
of them to the same product the same way, one ``RenderVar`` per name. Which
tap shows which stage, and the rule that a tap behind a stage that was not
built publishes nothing, are in the linked section of
:doc:`Outputs <../outputs>`.

Requesting every name at once, as the model's example scene does, lets you
follow one frame through the whole pipeline. The product then lists all eight
names, with a ``RenderVar`` for each written as in the previous step:

.. code-block:: usda

   def RenderProduct "SensorCamera"
   {
       int2 resolution = (1920, 1080)
       rel camera = </SensorCamera>
       rel orderedVars = [
           <HdrColor>,
           <OmniCameraSensorInputSource>,
           <OmniCameraSensorPostColorCorrection>,
           <OmniCameraSensorPostCfa>,
           <OmniCameraSensorPostNoise>,
           <OmniCameraSensorPreIsp>,
           <OmniCameraSensorPostYuvIsp>,
           <OmniCameraSensorPostIsp>,
       ]

       # one RenderVar per name, as in the previous step
   }

.. figure:: ../../../../img/sensors/visual/camera_core_same_frame_four_taps.avif
   :align: center
   :alt: Four panels of one Cornell box frame: the color HdrColor input; two gray single-component images that look alike, the second carrying a small inset of amplified random grain; and the color processed image.
   :width: 1000

   One frame of the Camera generic core model example scene at four outputs,
   left to right ``HdrColor`` (the rendered input, scaled for display),
   ``OmniCameraSensorPostCfa`` (the single-component mosaic, shown gray),
   ``OmniCameraSensorPostNoise`` (the same mosaic after the noise stage, on
   the same gray scale; its inset shows the difference to the previous tap,
   amplified, since the grain is a fraction of a percent of the signal at the
   example's settings) and ``OmniCameraSensorPostIsp`` (the processed image).

Verify it worked
----------------

Request ``OmniCameraSensorPostCfa`` and ``OmniCameraSensorPostNoise`` beside
your primary output, then read the outputs back as you would any output:
:doc:`Sensor Outputs <../../../common/sensor_outputs>` covers mapping an output,
:doc:`Decoding camera outputs <../../../cameras/decoding_outputs>` the image
outputs in particular. Check three things, in this order.

1. **The shape of** ``OmniCameraSensorPostCfa``, before you look at any value.
   It is a single-component image of sensor codes where ``HdrColor`` is
   four-component RGBA: a two-dimensional array, or one whose last dimension is
   1. If what you map has four components, the color filter array stage did
   not run, and nothing after it did either.

2. **That the noise stage changed something.** Compare
   ``OmniCameraSensorPostCfa`` with ``OmniCameraSensorPostNoise`` from the
   *same* frame over a lit region; compare within one frame rather than across
   runs, because the noise pattern repeats from run to run for the same scene
   and codes. Noise is added in whole sensor codes, so a pixel whose draw falls
   below one code keeps its value; over a lit region that is rare, and the two
   taps differ at almost every pixel. If they are identical everywhere, no
   noise was added at all. Photon shot noise has no attribute and is always on,
   so identical taps mean the codes are too small for it to register (check
   ``colorFilterArrayMaximalValue``, which scales them) and the dark-shot noise
   was authored away (``noiseDarkShotNoiseSigma`` times
   ``noiseDarkShotNoiseGain`` is zero or well below one code).

3. **The sequence of format changes.** Absolute pixel values are not a portable
   check: they depend on the render mode, the sample count and the scene. What
   is reproducible is the sequence of element formats along the pipeline, one
   component after the color filter array and four again after the ISP, which
   the stage table on :doc:`Outputs <../outputs>` lists. The formats do not
   show that the ISP ran: with no program authored they are the same, and the
   post-ISP outputs carry no processed image. The verify step of :doc:`Compand
   to a RAW Format and Run the ISP <companding_and_isp>` checks the ISP itself.

When it goes wrong
------------------

When nothing arrives at all, or an error names the product, the
:doc:`Symptom Index <../../../troubleshooting/symptoms>` lists the configuration
mistakes behind it. Each entry below names the mechanism and the page that
states it in full.

- **A camera pipeline is not enabled.** Naming one of the seven on a product
  starts the pipeline only when the product's camera carries
  ``OmniSensorGenericCameraCoreAPI`` and no other sensor schema; a camera with
  none, or with two, is rejected and the product delivers none of the outputs.
  Refer to
  :ref:`What enables the pipeline
  <sensors-visual-camera-core-outputs-reserved-names>` and the entry under
  :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **A camera product is missing its input or its primary output.** ``HdrColor`` must
  sit on the same product and one of the two primary outputs has to be present as
  well; if either is missing, the product is skipped and an error is logged, and
  a diagnostic tap on its own does not build a pipeline for the tap to sit on.
  Refer to :doc:`Configure the Input Image <input_image>`, :ref:`the primary outputs
  <sensors-visual-camera-core-outputs-primary-outputs>` and the entry under
  :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **The camera does not render on every step.** The schema sets
  ``omni:sensor:frameRate`` to ``(30, 1)``, so the camera is scheduled at 30 Hz
  rather than rendering on every step; author ``(0, 1)`` to leave it
  unscheduled. Refer to :doc:`Sensor Scheduling
  <../../../common/multi_rate>`.
- **The ISP taps produce nothing, or nothing processed, while the earlier taps
  work.** Either ``OmniCameraSensorPostIsp`` was not requested, so only the
  pre-ISP pipeline was built and the ISP-side taps have no stage behind them, or
  no ISP program is authored in ``ispSmodelCameraProgram``, the schema default,
  and the post-ISP outputs are published without a processed image. Refer to
  :ref:`Supply the ISP program
  <sensors-visual-camera-core-howto-companding-and-isp-isp-program>`, :ref:`the
  primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` and the entry under
  :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **A camera image is black or saturated although the mosaic is there.**
  ``colorFilterArrayMaximalValue`` is a multiplier, not a clamp, so check it
  against the range the image actually occupies. Refer to :doc:`Author a Color
  Filter Array <color_filter_array>` and the entry under :ref:`Values look
  plausible but are wrong <sensors-troubleshooting-symptoms-plausible>`.

Related
-------

- :doc:`Camera generic core model <../index>` — why each stage exists, and what the model does not do
- :doc:`USD Attributes <../attributes>` — the ``omni:sensor:core:`` attributes behind every stage
- :doc:`Outputs <../outputs>` — the seven output names, the primary output requirement and the per-stage element formats
