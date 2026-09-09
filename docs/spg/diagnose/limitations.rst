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
- A launch script cannot read the scene. A prim's attributes, a camera's transform and how a
  render product is laid out are all unreachable from it; a node is given what its ports carry
  and its authored value-inputs, and nothing else.
- A product bound to more than one camera is rendered in tiles, one camera per tile, and a node
  reading that image sees all of them at once with nothing to tell it the layout.
- A node cannot reach the CPU mid-frame. No pixel data is readable from the launch script, and
  the GPU code cannot call back to the host.
- A node cannot reach other frames, beyond what a stateful output or a previous-frame read
  carries.
- A launch script cannot reach the filesystem or the OS; its sandbox has neither.
- A shader output can be bound to one RenderVar at a time.
- A node cannot read an AOV and publish under that same name within one RenderProduct.
- A previous-frame read reaches at most 8 frames back.
- Cross-product reads can be one frame stale when the consuming product renders before the
  producing one, and converge once the dependency has rendered.
