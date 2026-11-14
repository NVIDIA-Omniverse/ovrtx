.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-limitations:

Limitations
===========

SPG is under active development. The API surface, Lua bindings and supported workflows can
evolve across releases. This is what it does not do today.

- GPU sources are limited to CUDA (``.cu``, or precompiled ``.ptx``, ``.cubin``, ``.fatbin``)
  and Slang (``.slang``, or precompiled ``.slang-module`` or ``.spv``), each with its ``.lua``
  launch script and a ``.usda`` shader definition. They are loaded from the local filesystem, from
  a ``.usdz`` package, or from a URI the Omniverse client can fetch.
- A CUDA node is one translation unit, compiled against a single include directory, and the
  directory holding the ``.cu`` is not it, so a header beside the source does not resolve. Slang
  has no such limit: a shader imports modules beside itself.
- SPG Shader nodes must not be nested under a ``Material`` prim, and shaders under an instance
  prototype are ignored.
- Standard library nodes operate on 2D textures only. Integer texture formats (``SINT``,
  ``UINT``) and buffer-backed resources are not supported by them.
- Slang shaders need the renderer to be running on Vulkan, and cannot use 64-bit integer types
  because the ``shaderInt64`` feature is not enabled.
- A ray-generation node cannot use a ``.spv`` binary.
- No node is given geometry. There are no vertex or index buffers and no material data; a
  ray-generation node gets hit distance and surface identity from a trace and nothing more.
- A launch script reads the scene as the renderer has it. Custom attributes are there only when
  the load names their prim, and a ``string`` attribute published that way reads as a number, so
  custom text is authored as a ``token``. Refer to :doc:`../do/scene_queries`.
- A launch script cannot write the scene. Prim tables are read-only.
- A product bound to more than one camera is rendered in tiles, one camera per tile. The layout
  comes from ``rtx.product.tiling``; nothing in the image itself says which tile a pixel is in.
- A node cannot reach the CPU mid-frame. No pixel data is readable from the launch script, and
  the GPU code cannot call back to the host.
- A node cannot reach other frames, beyond what a stateful output or a previous-frame read
  carries.
- A launch script cannot reach the filesystem or the OS.
- A launch script cannot catch errors or use the string pattern functions. Refer to
  :ref:`the sandbox <spg-lua-sandbox>`.
- A ``.spv`` runs its compute entry point ``main``; another of its entry points cannot be run by
  naming it. Compile the function to run so that it is exported as ``main``. Refer to
  :doc:`../do/precompiled`.
- A shader output can be bound to one RenderVar at a time.
- A node cannot read an AOV and publish under that same name within one RenderProduct.
- A previous-frame read reaches as far back as ``/rtx/spg/state/maxPreviousFrameOffset`` allows, 8
  frames by default.
- An earlier frame of a sensor composite is kept only when every channel is a GPU buffer of an
  element type SPG binds, stored compactly, with no ``/`` in its name. A ``:-N`` read of a composite
  with any other channel, such as a CPU channel, a CUDA array or a channel that has no buffer when SPG
  records the frame, stops the node's graph with an error naming the channel and why.
- A node input cannot take a ``token[]``. An input that holds one, or is connected to one, keeps
  the node's graph from being built, with an error naming the node and the input.
- A launch script cannot read a composite param of a 64-bit element type, such as a lidar's
  ``timestamp`` or ``frameId``: the param is listed in ``paramNames``, and reading it stops the
  node's graph.
- A CUDA or built-in node that fails while its work runs on the GPU stops the CUDA and built-in
  nodes after it in that frame, but not the Slang nodes after it, which run on its unwritten
  output. The graph's outputs of that frame are still published; the graph stops from the next
  frame. The log has an error naming the node and saying so.
- Cross-product reads can be one frame stale when the consuming product renders before the
  producing one, and converge once the dependency has rendered.
