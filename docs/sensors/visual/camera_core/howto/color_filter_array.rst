.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-camera-core-howto-color-filter-array:

Author a Color Filter Array
===========================

**Goal.** Convert the color image into one sensor code per pixel using a 2×2
mosaic. Set its four weight triples, pattern token and maximum code value for
the sensor's bit depth.

**Before you start.** Have a running :doc:`image_pipeline`: apply the model's
schema to the ``Camera`` and request ``HdrColor`` plus one primary output on
its RenderProduct. Attributes below use the ``omni:sensor:core:`` namespace;
prose omits that prefix. See :doc:`../attributes` for the weighted-sum formula.

.. _sensors-visual-camera-core-color-filter-array:

Why the color filter array matters
----------------------------------

A camera sensor measures brightness, not color. A photosite counts photons; it
cannot tell you which wavelength they were. Color comes from putting a different
optical filter over each photosite and then reconstructing the missing
components later from the neighbors. That grid of filters is the color filter
array, and it is almost always a 2×2 pattern repeated across the sensor.

RCCB trades color separation for low-light sensitivity, and that trade is the
reason it exists. Red-Clear-Clear-Blue replaces the two green filters of a Bayer
block, the classic 2×2 arrangement of one red, two green and one blue filter,
with clear pixels. A clear pixel is unfiltered, so it collects far more
light than a filtered one, which is why RCCB is common in driver assistance and
autonomous driving, where the hard scenes are the dark ones and noise at low
light is what limits you. The cost is color discrimination: with only two
filtered positions per block, colors that differ in hue but not much in
luminance become hard to separate. Distinguishing a red traffic light from an
amber one is the classic case.

.. figure:: ../../../../img/sensors/camera/sensors_camera_CFAEncoder001.avif
   :width: 250
   :alt: An RCCB mosaic: a 2×2 block with one red and one blue filter, and the
         two green positions of a Bayer block replaced by clear pixels.

   An RCCB mosaic. The two clear positions collect unfiltered light; only the
   red and the blue position carry color.

RGGB and the other Bayer orderings sit at the other end of the same trade:
better color separation and an easier conversion to RGB or YUV, less light per
block; the Bayer mosaic is pictured beside the color filter array group of
:doc:`USD Attributes <../attributes>`, which also explains the four weight triples
that let any 2×2 mosaic be expressed. An RCCC or CCCC arrangement pushes further
still, effectively a monochrome sensor with the sensitivity that implies. The
sections below walk through choosing a pattern and authoring it.

.. _sensors-visual-camera-core-howto-color-filter-array-patterns:

Choose the pattern
------------------

Each of the four positions in the 2×2 block carries its own triple of red,
green and blue weights, so any 2×2 mosaic can be expressed. The shipped defaults
are green, red, blue, green, reading across and then down: a GRBG Bayer
pattern. The table lists the patterns you will most often author as the triples
of their top row (``Cf00`` top left, ``Cf01`` top right) and bottom row (``Cf10``
bottom left, ``Cf11`` bottom right), with the token that names each.

========================== =========================== ============================= ===========
Pattern                    Top row: ``Cf00`` ``Cf01``  Bottom row: ``Cf10`` ``Cf11`` Token
========================== =========================== ============================= ===========
GRBG Bayer (default)       ``[0, 1, 0]`` ``[1, 0, 0]`` ``[0, 0, 1]`` ``[0, 1, 0]``   ``GRBG``
RGGB Bayer (example scene) ``[1, 0, 0]`` ``[0, 1, 0]`` ``[0, 1, 0]`` ``[0, 0, 1]``   ``RGGB``
RCCB                       ``[1, 0, 0]`` ``[1, 1, 1]`` ``[1, 1, 1]`` ``[0, 0, 1]``   ``RCCB``
RCCC (monochrome)          ``[1, 0, 0]`` ``[1, 1, 1]`` ``[1, 1, 1]`` ``[1, 1, 1]``   ``RCCC``
All clear (monochrome)     ``[1, 1, 1]`` ``[1, 1, 1]`` ``[1, 1, 1]`` ``[1, 1, 1]``   none exists
========================== =========================== ============================= ===========

The schema allows nine tokens; the :doc:`USD attributes page <../attributes>`
lists them. The weights alone produce the pattern, so a mosaic without a token,
such as all clear, can still be authored. RGGB is the most common pattern.
Which pattern suits a sensor is the question :ref:`Why the color filter array
matters <sensors-visual-camera-core-color-filter-array>` answers above: Bayer
orderings separate colors best, RCCB trades the two green filters for clear
pixels that gather more light, and RCCC or all clear is effectively a
monochrome sensor. The Bayer orderings are the same repeating mosaic; they
differ only in where the 2×2 block's top left falls on it. The mosaic is
pictured beside the
:ref:`color filter array group <sensors-visual-camera-core-attributes-cfa>` of
the USD attributes page.

.. _sensors-visual-camera-core-howto-color-filter-array-triples:

Author the four triples
-----------------------

Write the triples of your pattern into ``colorFilterArrayCfaCf00`` (top left),
``colorFilterArrayCfaCf01`` (top right), ``colorFilterArrayCfaCf10`` (bottom
left) and ``colorFilterArrayCfaCf11`` (bottom right); the table above gives
the triples of each pattern. How the weights and the maximal value you set two
steps on combine into the code of a pixel, with a diagram of the four
positions, is in the
:ref:`color filter array group <sensors-visual-camera-core-attributes-cfa>` of
the USD attributes page.

The fragment authors an RCCB mosaic on the camera that :doc:`image_pipeline`
set up, together with the token and the maximal value that the next two steps
explain.

.. code-block:: usda

   def Camera "SensorCamera" (
       prepend apiSchemas = ["OmniSensorGenericCameraCoreAPI"]
   )
   {
       float[] omni:sensor:core:colorFilterArrayCfaCf00 = [1, 0, 0]
       float[] omni:sensor:core:colorFilterArrayCfaCf01 = [1, 1, 1]
       float[] omni:sensor:core:colorFilterArrayCfaCf10 = [1, 1, 1]
       float[] omni:sensor:core:colorFilterArrayCfaCf11 = [0, 0, 1]
       token omni:sensor:core:colorFilterArrayCfaSemantic = "RCCB"
       float omni:sensor:core:colorFilterArrayMaximalValue = 16777215.0
   }

An all-clear mosaic is the same block with four ``[1, 1, 1]`` triples and the
token left alone, for the reason the next step gives.

.. _sensors-visual-camera-core-howto-color-filter-array-token:

Set the semantic token to match
-------------------------------

Set ``colorFilterArrayCfaSemantic`` to the token of the pattern you authored,
in the same edit as the weights; the stage never reads the token, so nothing
keeps the two in step for you (the
:ref:`color filter array group <sensors-visual-camera-core-attributes-cfa>` of
the USD attributes page says what the label is for).

.. note::

   The schema has no token for an all-clear mosaic. Author the four clear
   triples and the stage produces the monochrome mosaic whatever the token
   says. The token then keeps whatever it holds, ``GRBG`` unless you changed
   it, and does not describe the mosaic; do not rely on it for an all-clear
   sensor.

.. _sensors-visual-camera-core-howto-color-filter-array-maximal-value:

Set the maximal value
---------------------

Set ``colorFilterArrayMaximalValue`` to the largest code of the bit depth you
simulate when the image reaching the stage is normalized to 1; the 24-bit
default is ``16777215``. How the value scales the weighted sum, what it does to
an input that is not normalized, and the precision of its ``float`` type are in
the :ref:`color filter array group <sensors-visual-camera-core-attributes-cfa>`
of the USD attributes page.

.. warning::

   The value multiplies; it does not clamp. The companding stage then maps the
   codes through a curve that clamps everything beyond its last knee, so the
   curve's *x* range must cover the codes this value produces. A clear position
   sums all three color components, so with a normalized input it can reach up
   to three times the maximal value. Choose the value and the curve together;
   :doc:`companding_and_isp` authors the curve.

.. _sensors-visual-camera-core-howto-color-filter-array-verify:

Verify it worked
----------------

Request ``OmniCameraSensorPostCfa`` on the RenderProduct, next to the primary output
you already request. It is a :ref:`diagnostic tap
<sensors-visual-camera-core-outputs-taps>`, and a tap on its own does not build
a pipeline (the :doc:`Outputs page <../outputs>` has the rule and the element
formats). Then check three things in the mapped output:

- It has one component where ``HdrColor`` has four. Four components mean the
  stage did not run, and nothing after it did either.
- Over a flat, evenly lit region the 2×2 pattern shows as codes that repeat
  every two pixels in both directions. A clear position is brighter than any
  filtered one in its block, because it sums all three components; a filtered
  position carries one component, so the Bayer filters differ with the color
  of the light and the color correction in front of them.
- The codes sit in the range the maximal value implies. An image whose level
  is black or saturated although the 2×2 pattern is there means the maximal
  value does not match the range the input occupies; the
  :doc:`Symptom Index <../../../troubleshooting/symptoms>` lists it under that
  observation.

Changing the token changes nothing in this output; that is by design, and the
weights are what you edit.

.. _sensors-visual-camera-core-howto-color-filter-array-when-it-goes-wrong:

When it goes wrong
------------------

**The image is black or saturated although the 2×2 pattern is there.**
``colorFilterArrayMaximalValue`` is a multiplier, not a clamp, and its value
does not match the range the input occupies. Refer to :ref:`Values look
plausible but are wrong <sensors-troubleshooting-symptoms-plausible>` and the
:ref:`color filter array group <sensors-visual-camera-core-attributes-cfa>` of
the USD attributes page.

**Changing the semantic token changed nothing in the output.** The token is a
label, not a control: the four weight triples alone produce the mosaic, and
nothing keeps the two in step for you. Refer to :ref:`Runtime edits have no effect <sensors-troubleshooting-symptoms-retune>` and the :ref:`color filter
array group <sensors-visual-camera-core-attributes-cfa>` of the USD attributes
page.

**Nothing arrives on the post-CFA tap.** ``OmniCameraSensorPostCfa`` is a tap,
and a tap on its own does not build a pipeline: the product must also request
``HdrColor`` and one of the two primary outputs, or it is skipped and an error is
logged. Refer to :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>` and the :ref:`primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` on the Outputs page.

**Codes beyond the companding curve's last knee are clamped.** The maximal
value multiplies and does not clamp, and a clear position sums all three color
components, so with a normalized input it can reach up to three times the
maximal value; the curve's *x* range must cover the codes this value produces.
Refer to :doc:`companding_and_isp` and the :ref:`companding group
<sensors-visual-camera-core-attributes-companding>` of the USD attributes page.

The first three are entries of the :doc:`Symptom Index <../../../troubleshooting/symptoms>`,
which lists the misconfigurations of every sensor; the fourth is this page's own
by-design limit.

Related
-------

- :doc:`Camera generic core model <../index>` — the pipeline this stage belongs to, and what the model does to the image.
- :doc:`USD attributes <../attributes>` — the color filter array group, with the formula, the token list, the type, the figures and the output format.
- :doc:`Outputs <../outputs>` — ``OmniCameraSensorPostCfa`` among the taps, the primary outputs and the element formats.
- :doc:`Sensor API Schemas <../../../reference/schemas>` — the attribute table with types and defaults.
- :doc:`Glossary <../../../reference/glossary>` — CFA, Bayer and the other terms used here.
