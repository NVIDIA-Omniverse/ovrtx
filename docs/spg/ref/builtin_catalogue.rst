.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-stdlib-nodes:

Built-In Node Catalogue
=======================

Nodes that ship with SPG, usable with no GPU source and no launch script. Author them with
``info:implementationSource = "id"`` and one of the ``info:id`` values listed here. These four are
the whole of the supported set. An ID outside this table may still resolve, and is not an
authoring surface you can rely on.

Available Nodes
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 15 35

   * - ``info:id``
     - Inputs
     - Output
     - Operation
   * - ``spg:rtx.spg.stdlib/Add``
     - ``A``, ``B`` (opaque)
     - ``Result``
     - Element-wise addition. uint8: saturating (``min(a+b, 255)``).
   * - ``spg:rtx.spg.stdlib/Multiply``
     - ``A``, ``B`` (opaque)
     - ``Result``
     - Element-wise multiplication. uint8: normalized (``(a*b)/255``).
   * - ``spg:rtx.spg.stdlib/Scale``
     - ``Input`` (opaque), ``scaleX`` (float, default 0.5), ``scaleY`` (float, default 0.5)
     - ``Output``
     - Nearest-neighbor resize. Output: ``width*scaleX`` x ``height*scaleY``, min 1px.
   * - ``spg:rtx.spg.stdlib/Swizzle``
     - ``Input`` (opaque), ``swizzle`` (token, default ``"xyzw"``)
     - ``Output``
     - Per-channel routing.

Binary nodes (Add, Multiply) require both inputs to have the same dimensions
and format. Scale is the only node whose output dimensions differ from its
input.

**Swizzle selectors**: ``x`` ``y`` ``z`` ``w`` select source channels 0-3. ``0``
inserts zero. ``1`` inserts one (``1.0`` for float, ``255`` for uint8).
Case-insensitive. String length must equal the input channel count.

Standard library nodes operate on 2D textures only. Integer texture formats (``SINT``,
``UINT``) and buffer-backed resources are not supported.
