.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-camera-core-howto-input-image:

Configure the Input Image
=========================

**Goal.** Supply the Camera generic core model with ``HdrColor`` on the same
RenderProduct as its sensor outputs. This linear HDR image is the model's only
input. Choose its precision and render mode below.

**Before you start.** Read the :doc:`model overview <../index>` and know how to
:doc:`configure a RenderProduct <../../../common/output_configuration>`.

.. _sensors-visual-camera-core-howto-input-image-hdrcolor:

Request ``HdrColor`` on the same product
----------------------------------------

The input is one AOV: ``HdrColor``. A RenderProduct that asks for any output of
the model must also ask for ``HdrColor``, and on the same product. This holds
for the two :ref:`primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` as
much as for the five optional :ref:`taps <sensors-visual-camera-core-outputs-taps>`;
:doc:`Outputs <../outputs>` lists the seven names and carries the other half of
the rule, that one of the two primary outputs must be requested.
Without ``HdrColor`` the model skips the product and the reason is logged as an
error: the product's other outputs still arrive, but none of the model's do.

``HdrColor`` is the right input because of what it is: the linear-light,
high-dynamic-range render of the scene that the
:ref:`camera output tables <sensors-cameras-outputs-tables>` document. Its
values are neither tone-mapped nor clipped, so they can stand in for the light
falling on a sensor, which is what the model's response, noise and companding
stages work on. You request it like any other output, with a ``RenderVar``
whose ``sourceName`` is ``HdrColor`` listed in the product's ``orderedVars``
(:ref:`sensors-common-output-configuration-rendervar`);
:doc:`Shape an Image Like a Camera Sensor <image_pipeline>` shows the complete
product.

.. _sensors-visual-camera-core-howto-input-image-precision:
.. _sensors-camera-core-hdr-precision:

Choose the precision
^^^^^^^^^^^^^^^^^^^^

The rendered image arrives in one of two floating-point precisions. Which one is
chosen on the RenderProduct, not on the camera, so two products that render the
same camera can differ in it, and the choice applies in both path-tracing
modes.

.. list-table::
   :header-rows: 1
   :widths: 20 16 24 40

   * - Precision
     - Components
     - Representable range
     - How it is selected
   * - 16-bit HDR
     - RGBA
     - ``0.0`` to ``65504.0``
     - The default.
   * - 32-bit HDR
     - RGBA
     - ``0.0`` to the largest finite IEEE-754 ``float32``
     - The RenderProduct attribute ``omni:rtx:rt:fp32Target``, type ``bool``,
       default ``false``; set it to ``true``.

Both are linearly mappable to physical luminance units such as cd/m², which is
what lets a color correction matrix and a full-well level mean something: the
:ref:`color correction attributes <sensors-visual-camera-core-attributes-color-correction>`
scale and normalize these values.

``omni:rtx:rt:fp32Target`` is a render setting: an attribute in the
``omni:rtx:`` namespace on the RenderProduct prim, authored like any other
attribute (:ref:`sensors-common-output-configuration-render-settings`). In USDA
it is one line on the product:

.. code-block:: usda

   bool omni:rtx:rt:fp32Target = true

The precision is a property of the product's ``HdrColor``, so every consumer of
that output on the product receives the format you chose. A product that feeds
the model keeps the default: the model's first stage takes ``HdrColor`` as
16-bit float, as the
:ref:`per-stage formats <sensors-visual-camera-core-outputs-formats>` on Outputs
show. Select 32-bit on a product whose other consumers of ``HdrColor`` need the
wider range and that does not feed the model. The
:ref:`camera output tables <sensors-cameras-outputs-tables>` describe the
``HdrColor`` output itself, per render mode.

.. _sensors-visual-camera-core-howto-input-image-render-mode:
.. _sensors-camera-core-render-mode:

Select a render mode that produces ``HdrColor``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The render mode determines the lighting represented in ``HdrColor``. Set the
RenderProduct's ``omni:rtx:rendermode`` to one of the two path-tracing modes
described in :doc:`Render Modes <../../../cameras/render_modes>`.
``MinimalRendering`` produces no ``HdrColor`` and cannot provide the model's
input; :doc:`Minimal <../../../cameras/render_modes/minimal>` lists that
mode's available outputs.

.. _sensors-visual-camera-core-howto-input-image-not-ldr:
.. _sensors-camera-core-not-ldr:

``LdrColor`` is not an input
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 8-bit ``LdrColor`` output is not an input to this model. It is the
tone-mapped sRGB image (its format and shape are in its row of the
:ref:`camera output tables <sensors-cameras-outputs-tables>`), and tone mapping
and the 8-bit quantization have already discarded the linear relation to scene
luminance that the model's stages depend on. Among the sensor models it feeds the
:doc:`Camera single-view stereo depth model <../../depth_camera/index>`.
Requesting ``LdrColor`` alongside an output of this model is harmless; it
simply does not participate.

.. _sensors-visual-camera-core-howto-input-image-verify:

Verify it worked
----------------

Request one of the two :ref:`primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` beside ``HdrColor`` on the
product, then read the outputs back as you would any output:
:doc:`Sensor Outputs <../../../common/sensor_outputs>` covers mapping an output,
:doc:`Decoding camera outputs <../../../cameras/decoding_outputs>` the image
outputs in particular. Two things show that the input reached the pipeline.

1. **The primary output is produced.** ``OmniCameraSensorPreIsp`` or
   ``OmniCameraSensorPostIsp``, whichever you requested, arrives for the
   product. Without ``HdrColor`` on the same product the model skips the
   product: its other outputs still arrive, but none of the model's do, and the
   reason is logged as an error.

2. **The element format matches the precision you chose.** ``HdrColor`` itself
   arrives as four-component 16-bit float on a product that keeps the default,
   and as 32-bit float on one where ``omni:rtx:rt:fp32Target`` is ``true``, as
   the precision table above and the :ref:`camera output tables
   <sensors-cameras-outputs-tables>` state. On a product that feeds the model,
   add the ``OmniCameraSensorInputSource`` tap, the read-back input: it is RGBA
   float16 with shape ``(H, W, 4)`` on both pipelines, the format the model's
   first stage takes ``HdrColor`` in (:ref:`per-stage formats
   <sensors-visual-camera-core-outputs-formats>`).

When it goes wrong
------------------

Each entry names the mechanism and the section that states it in full; the
:doc:`Symptom Index <../../../troubleshooting/symptoms>` holds the full symptom
text.

- **None of the model's outputs arrive, while the product's other outputs do.**
  ``HdrColor`` is not requested on the same product as the model's outputs, so
  the model skips the product and the reason is logged as an error. Refer to
  :ref:`Request HdrColor on the same product
  <sensors-visual-camera-core-howto-input-image-hdrcolor>` and, on the Symptom
  Index, the entry on a camera product missing its input or its primary output under
  :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **The product requests the input and still delivers none of the model's
  outputs.** Neither primary output is requested: one of ``OmniCameraSensorPreIsp``
  and ``OmniCameraSensorPostIsp`` has to be present as well, and a tap on its
  own does not build a pipeline for the tap to sit on. Refer to :ref:`the
  primary outputs <sensors-visual-camera-core-outputs-primary-outputs>` and the same entry
  under :ref:`Missing output <sensors-troubleshooting-symptoms-nothing>`.
- **Minimal rendering does not provide the required input.**
  ``MinimalRendering`` produces no ``HdrColor``. Select one of the two
  path-tracing modes. Refer to :ref:`Select a render mode that produces
  HdrColor <sensors-visual-camera-core-howto-input-image-render-mode>`,
  :doc:`Minimal <../../../cameras/render_modes/minimal>` and, on the
  Symptom Index, the entry on warm-up frames and the render mode used by a
  camera sensor under :ref:`Performance problems <sensors-troubleshooting-symptoms-slow>`.
- **The 8-bit output was used as the input.** ``LdrColor`` is not an input to
  this model: tone mapping and the 8-bit quantization have discarded the linear
  relation to scene luminance that the model's stages depend on, so it simply
  does not participate, and the product still needs ``HdrColor``. Refer to
  :ref:`LdrColor is not an input
  <sensors-visual-camera-core-howto-input-image-not-ldr>` and the model's
  :ref:`Limitations <sensors-troubleshooting-limitations-camera-core>`.

Related
-------

- :doc:`Camera generic core model <../index>` — what the model does with the image, and when to choose it.
- :doc:`USD Attributes <../attributes>` — the color correction and full-well attributes that scale the input values.
- :doc:`Outputs <../outputs>` — the seven output names, the primary output requirement and the per-stage formats.
- :doc:`Cameras: Outputs <../../../cameras/outputs>` — the ``HdrColor`` and ``LdrColor`` rows, formats and shapes.
