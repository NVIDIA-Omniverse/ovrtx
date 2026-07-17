.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python API Reference
====================

The Python API provides a high-level interface to the ovrtx rendering library.

.. contents:: Contents
   :local:
   :depth: 2

ovrtx
-----

Version and Constants
^^^^^^^^^^^^^^^^^^^^^

.. autodata:: ovrtx.__version__

.. autodata:: ovrtx.OVRTX_LIBRARY_PATH_HINT

.. autodata:: ovrtx.OVRTX_RENDER_VAR_PICK_HIT

.. autodata:: ovrtx.OVRTX_PICK_FLAG_GIZMO

.. autodata:: ovrtx.OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO

.. autodata:: ovrtx.OVRTX_PICK_HIT_MAGIC

.. autodata:: ovrtx.OVRTX_PICK_HIT_VERSION

USD Schema Path Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: ovrtx.register_schema_paths

.. autofunction:: ovrtx.usd_pluginpath_env_keys

Renderer
^^^^^^^^

.. autoclass:: ovrtx.Renderer
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: Semantic, PrimMode, DataAccess, Device

   .. note::
      Enums are also available as class attributes for convenience
      (for example, ``Renderer.Semantic.NONE``). Refer to :ref:`enums` below for details.

Configuration
^^^^^^^^^^^^^

.. autoclass:: ovrtx.RendererConfig
   :members:
   :undoc-members:

.. autoclass:: ovrtx.SelectionGroupStyle
   :members:
   :undoc-members:

Async Operations
^^^^^^^^^^^^^^^^

.. autoclass:: ovrtx.Operation
   :members:
   :undoc-members:

.. autoclass:: ovrtx.PendingFetch
   :members:
   :undoc-members:

.. autoclass:: ovrtx.OperationStatus
   :members:
   :undoc-members:

.. autoclass:: ovrtx.OperationCounter
   :members:
   :undoc-members:

Render Outputs
^^^^^^^^^^^^^^

.. autoclass:: ovrtx.RenderProductSetOutputs
   :members:
   :undoc-members:

.. autoclass:: ovrtx.ProductOutput
   :members:
   :undoc-members:

.. autoclass:: ovrtx.FrameOutput
   :members:
   :undoc-members:

.. autoclass:: ovrtx.RenderVarOutput
   :members:
   :undoc-members:

.. autoclass:: ovrtx.MappedRenderVar
   :members:
   :undoc-members:

.. autoclass:: ovrtx.RenderVarTensor
   :members:
   :undoc-members:

.. autoclass:: ovrtx.RenderVarParam
   :members:
   :undoc-members:

.. autoclass:: ovrtx.ManagedDLTensor
   :members:
   :undoc-members:

Attribute Bindings and Mappings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: ovrtx.AttributeBinding
   :members:
   :undoc-members:

.. autoclass:: ovrtx.AttributeMapping
   :members:
   :undoc-members:

.. autoclass:: ovrtx.AttributeInfo
   :members:
   :undoc-members:

.. _enums:

Enums
^^^^^

.. autoclass:: ovrtx.Semantic
   :members:
   :undoc-members:

.. autoclass:: ovrtx.PrimMode
   :members:
   :undoc-members:

.. autoclass:: ovrtx.DataAccess
   :members:
   :undoc-members:

.. autoclass:: ovrtx.Device
   :members:
   :undoc-members:

.. autoclass:: ovrtx.BindingFlag
   :members:
   :undoc-members:

.. autoclass:: ovrtx.EventStatus
   :members:
   :undoc-members:

.. autoclass:: ovrtx.SelectionFillMode
   :members:
   :undoc-members:

.. autoclass:: ovrtx.AttributeFilterMode
   :members:
   :undoc-members:

.. autoclass:: ovrtx.FilterKind
   :members:
   :undoc-members:

.. autoclass:: ovrtx.DLDataType
   :members:
   :undoc-members:
