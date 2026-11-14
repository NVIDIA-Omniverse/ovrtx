.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Runtime textures
================

Runtime textures allow you to create and fill textures dynamically at runtime
that can then be applied to any material in the scene. Updating the texels in the
stage changes the applied texture on the next rendered frame.

.. figure:: ../img/carter-monitor.avif
   :alt: Carter beside a monitor showing its previous camera frame in greyscale
   :align: center

   |carter-monitor-caption|

.. |carter-monitor-caption| replace::
   *Carter drives in a circle while Warp converts its previous camera frame to
   greyscale and publishes it as the monitor texture. See the*
   :doc:`Python example <../examples/python_runtime_textures>`.

Creating a runtime texture
--------------------------

Author an ``OmniRuntimeTexture`` prim and reference its ``texture:uri`` from a
material. The URI does not have to match the prim path.

The USDA and USD Python examples create a red texture and a ``UsdPreviewSurface``
material that samples it. Bind ``/RuntimeMaterial`` to your mesh. The OVStage
Python example creates only the texture and points the existing ``UsdUVTexture``
shader at its dynamic URI:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/data/ovrtx-test-runtime-textures.usda
         :language: usda
         :start-after: # [snippet:doc-runtime-texture-usda]
         :end-before: # [/snippet:doc-runtime-texture-usda]
         :dedent:

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_runtime_textures.py
         :language: python
         :start-after: # [snippet:doc-runtime-texture-usd-python]
         :end-before: # [/snippet:doc-runtime-texture-usd-python]
         :dedent:

   .. tab-item:: OVStage Python

      This example assumes the material and shader prims already exist in an
      ``ovstage.Stage`` named ``stage``, including the ``UsdUVTexture`` shader at
      ``/RuntimeMaterial/Tex``. The ``/Texture`` prim must be absent. Use an
      application-owned ``ordinal`` above the stage's write floor.

      .. literalinclude:: ../../tests/docs/python/test_runtime_textures.py
         :language: python
         :start-after: # [snippet:doc-runtime-texture-ovstage-python]
         :end-before: # [/snippet:doc-runtime-texture-ovstage-python]
         :dedent:

.. csv-table:: OmniRuntimeTexture attributes
   :header: "Declaration", "Meaning"
   :class: compact-table
   :widths: 45, 55

   "``string texture:uri``", "Nonempty dynamic:// identifier. Canonical identifiers must be unique in the attached stage."
   "``token texture:dimension = ""2d""``", "2d or 3d. A 2D texture requires depth one."
   "``int3 texture:extent = (1, 1, 1)``", "Positive width, height, and depth in texels."
   "``token texture:format = ""rgba8unorm""``", "Interleaved component layout and numeric interpretation; see the formats below."
   "``token texture:colorSpace = ""linear""``", "linear or sRGB. sRGB requires rgba8unorm; RGB is decoded and alpha remains linear. This value takes precedence over material color-space requests."
   "``uchar[] texture:data``", "Packed texel bytes. X varies fastest, followed by Y and Z. The byte count must exactly match extent and format."

Supported formats are ``r8unorm``, ``rg8unorm``, ``rgba8unorm``,
``r16float``, ``rg16float``, ``rgba16float``, ``r32float``, ``rg32float``,
and ``rgba32float``. Their byte sizes per texel are 1, 2, 4, 2, 4, 8, 4, 8,
and 16 respectively. Float payloads must also be supplied as byte views.

Only whole-texture updates and one mip level are supported. Pitched or
transposed input, compressed formats, region updates, mip chains, cube maps,
and texture arrays are not supported.

Updating texels
---------------

Keep dimensions in ``texture:extent``; the tensor shape is not image metadata.
Use a compact ``uint8`` byte tensor for ``texture:data``. Write related metadata
and texels at the same ordinal, wait for every write to succeed, then advance
the write floor before rendering that ordinal.

The following examples publish a 256 × 256 RGBA8 texture, first red and then
green. Both snippets produce texels on CUDA device 0. Its producer completes
before ovstage reads the buffer; the buffer stays alive and unchanged until
the write completes:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_runtime_textures.py
         :language: python
         :start-after: # [snippet:doc-runtime-texture-python-update]
         :end-before: # [/snippet:doc-runtime-texture-python-update]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/runtime-textures/main.cpp
         :language: cpp
         :start-after: // [snippet:doc-runtime-texture-c-update]
         :end-before: // [/snippet:doc-runtime-texture-c-update]
         :dedent:

The Python snippet uses this Warp kernel to fill the texture:

.. literalinclude:: ../../tests/docs/python/test_runtime_textures.py
   :language: python
   :start-after: # [snippet:doc-runtime-texture-python-producer]
   :end-before: # [/snippet:doc-runtime-texture-python-producer]
   :dedent:

Render the updated texture by passing its ordinal to
:py:meth:`~ovrtx.Renderer.step()` in Python. In C, call
:c:func:`ovrtx_step_with_stage()` with that ordinal and wait for the operation
to complete.

You can update the pixels without changing the material or reattaching the stage.
The renderer uploads the texture again only when it changes.

Devices and buffer reuse
------------------------

Use one GPU for rendering, and create your CUDA texture buffers on that same
GPU. For example, if the renderer uses CUDA device 0, your Warp kernel must also
produce its pixels on device 0. Buffers from another GPU are rejected.

Wait for the kernel to finish before writing its pixels to ovstage. Then wait
for the ovstage write to complete before changing or freeing the source buffer.
You do not need to keep that buffer alive until rendering finishes: the renderer
uses its own copy and manages its lifetime.

The renderer uses the latest published texture data. Rendering an earlier ordinal
does not restore an older version of the texture. To display older content again,
publish those pixels as a new update.

Texture updates copy data into ovstage and then into a texture the renderer can
sample; the renderer does not sample your source buffer directly. With a borrowed
stage attachment, CUDA pixels stay on the GPU during these copies. CPU buffers
must be uploaded to the GPU, and replicated stage attachments may also copy data
through CPU memory.

Memory Limits
-------------

Each ovrtx renderer can use up to **1 GiB** for runtime textures from its
attached ovstage stage, including temporary replacement textures.

The limit counts the pixel data of existing textures, their replacements while
an update is in progress, and temporary CPU upload buffers. It does not count
your source buffers or ovstage's storage.

For example, replacing 600 MiB of existing textures with another 600 MiB requires
1,200 MiB during the update. The renderer rejects that update under the default
limit, even if the GPU has enough free memory. To stay within the limit, use
smaller textures or replace fewer textures at once.

When an update exceeds the limit, the renderer reports the failure and keeps
displaying the previous texture. If none exists, it displays a missing-texture
placeholder.

Names and references
--------------------

Each runtime texture URI must be unique within its stage. On Windows, names that
differ only by case are treated as the same name. Separate renderer attachments
can use the same URI for different textures.

Deleting or renaming a texture leaves materials using its old URI with a
missing-texture placeholder of the appropriate dimension (2D or 3D). Creating a
texture with that URI reconnects those materials to it.

Detaching the stage or destroying the renderer releases the attachment's texture
resources once they are no longer in use.

Handling errors
---------------

Invalid texture metadata or texels, duplicate URIs, and recoverable allocation or
upload failures produce a diagnostic without stopping the render step. The
renderer keeps the last published texture, or shows a missing-texture placeholder
if no valid texture has been published. Correct the problem and update the
texture to retry.

Examples
--------

See :doc:`../examples/python_runtime_textures` and
:doc:`../examples/c_runtime_textures` for complete runnable programs and output.

For the standard material nodes used above, see the
`UsdPreviewSurface specification <https://openusd.org/release/spec_usdpreviewsurface.html>`_.
