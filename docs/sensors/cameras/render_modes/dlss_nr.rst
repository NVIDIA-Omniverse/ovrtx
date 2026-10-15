.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

.. _dlss-nr:

DLSS 5 3D-Guided Neural Rendering
=================================

.. warning::

   This feature is **experimental** and currently supported only on **Windows**.
   It requires an NVIDIA Blackwell GPU and
   a driver that supports DLSS Neural Rendering. The current integration requires
   driver 615.64 or newer.

   The required driver has **not been validated for use with Omniverse**.
   There may be unknown compatibility, rendering, or stability issues.
   This guidance will be updated once a suitable **Production Branch driver**
   has been validated.

DLSS 5 3D-Guided Neural Rendering (DLSS-NR) uses a neural model to enhance
lighting and material appearance in a rendered image. It uses the image,
depth, motion vectors, and temporal history to guide the result.

.. figure:: ../../../img/dlss-nr-banner.avif
   :alt: Portrait and robot lineup comparisons with DLSS-NR off on the left and on on the right
   :width: 100%

   *DLSS-NR Off (left) and On (right), shown on a portrait and a robot lineup.*

DLSS-NR generates appearance detail. Its output should not be treated as a
physically accurate reference image. It is separate from DLSS Super Resolution
(upscaling) and DLSS Ray Reconstruction (denoising).

Enable Neural Rendering
-----------------------

DLSS-NR is off by default and is supported only in
:doc:`real_time_path_tracing`. It does not run in :doc:`path_tracing` or
:doc:`minimal`.

Configure the camera's ``RenderProduct`` as follows:

#. Select ``RealTimePathTracing`` with ``omni:rtx:rendermode``.
#. Request :ref:`LdrColor <camera-output-tables>` in ``orderedVars``.
#. Set ``omni:rtx:dlssnr:enabled`` to ``true``.

``OmniRtxPostDlssNrAPI_1`` is automatically applied to ``RenderProduct`` prims.
You can author its attributes directly on the RenderProduct. DLSS-NR runs
only when NGX reports support for the GPU and driver. Enabling the attribute
on an unsupported system leaves the image without the neural rendering effect.

The following snippets configure an existing scene camera for neural rendering.
The resolution sets the output size; the scene must provide ``/World/Camera``.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../../tests/docs/usd/data/dlss_nr.usda
         :language: usda
         :start-after: # [snippet:doc-dlss-nr-render-product]
         :end-before: # [/snippet:doc-dlss-nr-render-product]

   .. tab-item:: Python

      .. literalinclude:: ../../../../tests/docs/usd/test_dlss_nr.py
         :language: python
         :start-after: # [snippet:doc-dlss-nr-render-product-python]
         :end-before: # [/snippet:doc-dlss-nr-render-product-python]
         :dedent:

Controls
--------

These attributes belong to ``OmniRtxPostDlssNrAPI_1`` on the RenderProduct.
The renderer clamps strength values to the range shown below.

.. csv-table::
   :header: "USD declaration", "Behavior"
   :widths: 50, 50
   :class: compact-table

   "``bool omni:rtx:dlssnr:enabled = false``", "Enables neural rendering when the render mode, output, GPU, and driver support it."
   "``float omni:rtx:dlssnr:intensity = 1``", "Overall effect strength, from 0 to 1. Zero preserves the original image; one applies the full effect."
   "``float omni:rtx:dlssnr:globalToneStrength = 0``", "Whole-image tone adjustment strength, from 0 to 1."
   "``float omni:rtx:dlssnr:localToneStrength = 0``", "Spatially adaptive tone adjustment strength, from 0 to 1."
   "``float omni:rtx:dlssnr:localStructureStrength = 0``", "Local detail and structure enhancement strength, from 0 to 1."
   "``bool omni:rtx:dlssnr:useAutoMask = false``", "Enables the model's automatic influence mask."
   "``float omni:rtx:dlssnr:skinStructureStrength = 0``", "Skin-specific structure enhancement strength, from 0 to 1."
   "``int omni:rtx:dlssnr:style = 0``", "Selects processing style 0, 1, or 2."
   "``int omni:rtx:dlssnr:presetHint = 0``", "Selects the NGX model preset: 0 uses the linked SDK default; 1 through 7 select presets A through G. Values are clamped to this range. Changing the preset recreates the feature and resets its history."
   "``int omni:rtx:dlssnr:iterations = 1``", "Experimental number of chained evaluations, from 1 to 4. Each evaluation processes the preceding result with its own temporal history. Additional iterations increase processing and memory costs."

Strength controls are read for each rendered frame. Changing the input, render,
or output dimensions also recreates the feature and resets its history.

.. note::

   Keep ``iterations`` at 1 when exploring the other controls. The chained
   evaluations are experimental; more iterations do not guarantee a better image.

Outputs
-------

DLSS-NR affects :ref:`LdrColor <camera-output-tables>`. If you request both
:ref:`LdrColor and HdrColor <camera-output-tables>`, the renderer applies the
effect to the separately tone-mapped LDR image and keeps HDR unchanged.
If you request only :ref:`HdrColor <camera-output-tables>`, DLSS-NR is skipped.

Further Reading
---------------

* :doc:`real_time_path_tracing`
* :doc:`../outputs`
* `DLSS 5: Generative Neural Rendering <https://research.nvidia.com/labs/adlr/DLSS5/>`_
