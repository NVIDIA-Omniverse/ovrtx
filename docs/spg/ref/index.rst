.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-reference:

Reference
=========

Lookup, not teaching. Every surface a node touches, stated once and in full.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Page
     - Contents
   * - :doc:`lua_contract`
     - What a launch script is handed, what it must describe, and what it may call, in either language.
   * - :doc:`lua_cuda`
     - Every function, dtype and wrapper on the ``cuda`` table, and what each one produces.
   * - :doc:`lua_slang`
     - Every function, binder and layout control on the ``slang`` table.
   * - :doc:`usd`
     - What a shader definition, a RenderVar and a RenderProduct may declare.
   * - :doc:`builtin_catalogue`
     - The pre-built nodes, their IDs, and the ports each one carries.
   * - :doc:`glossary`
     - SPG's own vocabulary, defined once.

.. toctree::
   :hidden:

   lua_contract
   lua_cuda
   lua_slang
   usd
   builtin_catalogue
   glossary
