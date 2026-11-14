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

Start from what you see and work down the list.

.. _spg-symptom-nothing:

Nothing Appears
---------------

An output that stays empty or black.

**The node never ran.** Execution is driven backwards from the outputs that are requested, so a
node whose output nothing consumes and which publishes no RenderVar is not executed at all.
Check the output is connected to a RenderVar and that the RenderVar is in ``orderedVars``.
Refer to :ref:`how execution order is decided <spg-execution-order>`.

**The RenderVar is not published.** It needs a ``sourceName`` as well as the connection.

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
is missing and its graph stops. Refer to
:ref:`with a group size from neither place <spg-slang-no-group-size>`.

**A composite channel or parameter was asked for by a name it does not carry.** The node's graph
stops, and the message names the port, the name used and the nearest match.

**A ``:-N`` read of a sensor composite stopped its graph.**
SPG keeps earlier frames of a composite whose channels are all GPU buffers of an element type SPG
binds, stored compactly, with no ``/`` in their names,
so a ``:-N`` read of another composite stops the node's graph, and the message names the channel and
why. Refer to :doc:`../do/previous_frame`.

**A node input holds a token[].** SPG node inputs do not take a ``token[]``, so the node's graph is
not built, and the log names the node and the input. Refer to :doc:`../ref/usd`.

**The launch script does not parse.** The node's graph stops, and the log has a
``Lua load error`` line naming the script and the line of the error. The renderer keeps running.

**The launch script was rejected.** Scripts run in a sandbox and the source is scanned before
it runs. The scan is a plain substring match over the whole file, **including comments**, so a
comment mentioning a forbidden construct is enough. A rejected script produces no GPU work.

.. _spg-symptom-graph-stopped:

**A graph stopped after one failure.** A node that fails stops its whole graph, not only itself:
the graph's outputs are not written, and the log has an error naming the node and the
reason. The node can fail at two points:

- **Before its GPU work starts**: a launch script that does not parse, raises an error or reaches
  a :ref:`sandbox limit <spg-lua-sandbox>`, a value that cannot be converted, or a ``:-N`` read
  SPG does not serve.
- **While its GPU work runs**: a CUDA kernel that does not compile or launch, the upload of an
  array value that fails, or a built-in node that rejects its input. The graph then stops from
  the next frame, and the outputs of the frame in which the work failed may be incomplete.

A graph that reads the output of a graph that failed fails in that frame too, but does not stop.
Until the failed graph runs again, the nodes that read its output, and the nodes that need
theirs, do not run; then they read its new output.

A stopped graph runs again, on its schedule, once one of these happens:

- A value-input of one of its nodes changes, such as a corrected ``inputs:swizzle``. While the
  values that stopped it stay the same, it does not run again.
- It is rebuilt. An edit to ``info:spg:sourceAsset`` or to the connections of one of its nodes
  rebuilds it, and so do an edit to the ``sourceName`` of a RenderVar it reads or publishes and
  opening the stage again.

A launch script that has loaded is not read again while the stage stays open, so after fixing
one, open the stage again.

**A graph was not built because an asset input cannot be loaded.** A node input that names an
asset, such as a lookup table, that cannot be loaded keeps the node's whole graph from being built.
The log has an error naming the prim, the input and the asset. Once the input names an asset that
loads, the graph is built.

**An output was never described.** Every declared output must be assigned a descriptor before
the launch script returns.

**A scene read came back** ``nil`` **and the script indexed it.** The tell is
``attempt to index a nil value`` in the log. ``rtx.stage.prim`` is ``nil`` for a path with no prim
on the stage, and a prim table reads ``nil`` for an attribute the prim does not carry. A custom
attribute is there only when the load named its prim. Refer to :doc:`../do/scene_queries`.

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
one camera per tile, and pixel coordinates alone do not say which view a pixel belongs to. The
grid is ``rtx.product.tiling``; refer to :doc:`../ref/lua_rtx`.

.. _spg-symptom-stale:

Something Is Stale or Late
--------------------------

**A cross-product read is one frame behind.** Expected when the consuming product renders
first. Refer to :ref:`cross-product staleness <spg-cross-product-stale>`.

**The first frame of a stateful node reads zeros.** Defined behaviour. Refer to
:ref:`stateful zero-initialisation <spg-stateful-zeroed>`.

**A scene edit had no effect.** The write did not land before the step: advance the write floor
before stepping. Refer to :doc:`../do/runtime_changes`.

Reading the Log
---------------

SPG reports through the renderer's log, which the renderer writes to standard output: node
loading, shader compilation and binding diagnostics, most of them naming the port concerned. When
a node produces nothing and the scene looks right, the log is the fastest way to tell a rejected
script from a node that was never asked to run.

Messages a launch script writes with ``warning`` appear there too, prefixed ``Lua:``. Those written
with ``info`` or ``print`` do not, at the default log level. Refer to :doc:`../ref/lua_contract`.
