.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-symptoms:

Symptom Index
=============

Start from what you see. Each cause has its own tell, so work down the list rather than
guessing.

.. _spg-symptom-nothing:

Nothing Appears
---------------

An output that stays empty or black.

**The node never ran.** Execution is driven backwards from the outputs that are requested, so a
node whose output nothing consumes and which publishes no RenderVar is not executed at all.
Check the output is connected to a RenderVar and that the RenderVar is in ``orderedVars``.
Refer to :ref:`how execution order is decided <spg-execution-order>`.

**The RenderVar is not published.** It needs a ``sourceName`` as well as the connection.

**The name collides with a built-in AOV.** The renderer's own output shadows the node's. Refer
to :ref:`name collisions <spg-aov-collision>`.

**A node is wired to another product's node instead of to a published AOV.** A shader-to-shader
connection only works inside one product. Reaching across a product boundary needs the producing
node's output published as a RenderVar and listed in that product's ``orderedVars``. The tell is
one warning per frame naming the upstream port, with the output AOV never written::

    resolveInputShape: Upstream output GrayscaleKernel.LdrGrayscale not resolved yet

Refer to :doc:`../do/products`.

**The shader is under a Material prim.** Those are ignored. Author it under a plain scope or
the RenderProduct.

**The shader is under an instance prototype.** A prim marked instanceable, and everything beneath
it, is skipped before the kernel is ever compiled. Move the shader out, or drop the
``instanceable`` flag on the ancestor.

**A Slang node had no thread group size to work from.** A ``.spv`` whose launch script states
neither ``numthreads`` nor ``grid`` leaves nothing to derive a grid from, so the node reports what
is missing and does not run. Refer to
:ref:`with a group size from neither place <spg-slang-no-group-size>`.

**A composite channel or parameter was asked for by a name it does not carry.** The node fails
without publishing, and the message names the port, the name used and the nearest match.

**The launch script was rejected.** Scripts run in a sandbox and the source is scanned before
it runs. The scan is a plain substring match over the whole file, **including comments**, so a
comment mentioning a forbidden construct is enough. A rejected script produces no GPU work.

**An output was never described.** Every declared output must be assigned a descriptor before
the launch script returns.

**The shader failed to compile.** Check the log. A Slang compile failure reports that it will
use the existing shader and the run continues with an empty AOV **and a zero exit code**, so
assert on content rather than on the process exiting cleanly.

**The sensor returned nothing.** For a composite, ``Counts`` of zero means the sweep produced
no points, not that the node is wrong. Refer to :ref:`bounding by the count channel <spg-composite-counts>`.
The composite's :ref:`status <spg-composite-status>` does not answer this and should not be used
for it.

.. _spg-symptom-wrong-pixels:

Wrong Pixels Rather Than No Pixels
----------------------------------

Something is produced, but it is not what you expected. Almost always a mismatch between the
launch script and the GPU code, because both are matched by position.

**The argument or bind order does not match.** In CUDA, ``args`` is matched against the C
signature by position and a mismatch is not diagnosed: the kernel reads whatever occupies that
slot. In Slang, the Nth ``bind`` entry is matched against the Nth declared resource per
descriptor kind.

**The shape order is reversed.** Shapes are height-first while the ``image`` functions take
width first.

**A value is in the wrong field.** For a Slang parameter block, a wrong count is an error but a
wrong order is only a warning, and a value carrying no name cannot be cross-checked.

**A value-input was used as a number.** It is a wrapper; arithmetic on it fails. Refer to
:ref:`value-inputs are wrappers <spg-value-wrapper>`.

**A tiled product was treated as one image.** A product bound to more than one camera renders
one camera per tile, and pixel coordinates alone do not say which view a pixel belongs to.

.. _spg-symptom-stale:

Something Is Stale or Late
--------------------------

**A cross-product read is one frame behind.** Expected when the consuming product renders
first. Refer to :ref:`cross-product staleness <spg-cross-product-stale>`.

**The first frame of a stateful node reads zeros.** Defined behaviour. Refer to
:ref:`stateful zero-initialisation <spg-stateful-zeroed>`.

**A scene edit had no effect.** The write did not land before the step.

Reading the Log
---------------

SPG reports through the renderer's log, which the renderer writes to standard output: node
loading, shader compilation and binding diagnostics, most of them naming the port concerned. When
a node produces nothing and the scene looks right, the log is the fastest way to tell a rejected
script from a node that was never asked to run.

Messages a launch script writes with ``warning`` appear there too, prefixed ``Lua:``. Those written
with ``info`` or ``print`` do not, at the default log level. Refer to :doc:`../ref/lua_contract`.
