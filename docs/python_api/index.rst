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

.. _python-handle-types:

Handle Types
^^^^^^^^^^^^

.. automodule:: ovrtx.handles
   :no-members:
   :no-special-members:

.. autoclass:: ovrtx.Token

.. autoclass:: ovrtx.PrimPath

.. autoclass:: ovrtx.PrimPathList

.. autoclass:: ovrtx.UsdHandle

.. autoclass:: ovrtx.EventHandle

.. autoclass:: ovrtx.AttributeBindingHandle

.. autoclass:: ovrtx.MapHandle

.. autoclass:: ovrtx.StepResultHandle

.. autoclass:: ovrtx.RenderVarOutputHandle

.. autoclass:: ovrtx.RenderVarOutputMapHandle

.. autoclass:: ovrtx.OpId

.. autoclass:: ovrtx.QueryHandle

.. autoclass:: ovrtx.ReadHandle

.. autoclass:: ovrtx.DataProviderId

.. autoclass:: ovrtx.DataArrayLeaseId

.. autodata:: ovrtx.INVALID_USD_HANDLE

.. autodata:: ovrtx.INVALID_EVENT_HANDLE

.. autodata:: ovrtx.INVALID_ATTRIBUTE_BINDING_HANDLE

.. autodata:: ovrtx.INVALID_MAP_HANDLE

.. autodata:: ovrtx.INVALID_STEP_RESULT_HANDLE

.. autodata:: ovrtx.INVALID_RENDER_VAR_OUTPUT_HANDLE

.. autodata:: ovrtx.INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE

.. autodata:: ovrtx.INVALID_OP_ID

.. autodata:: ovrtx.INVALID_QUERY_HANDLE

.. autodata:: ovrtx.INVALID_READ_HANDLE

.. autodata:: ovrtx.INVALID_DATA_PROVIDER_ID

Version and Constants
^^^^^^^^^^^^^^^^^^^^^

.. autodata:: ovrtx.__version__

.. autodata:: ovrtx.OVRTX_LIBRARY_PATH_HINT

.. autofunction:: ovrtx.get_build_info

.. autoclass:: ovrtx.BuildInfo
   :members:

.. autodata:: ovrtx.OVRTX_RENDER_VAR_PICK_HIT

.. py:data:: ovrtx.OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO
   :type: int
   :value: 2

   Requests tracked metadata for the first hit of a one-pixel-equivalent pick.
   Without this flag, or for a multi-pixel pick, ``objectType``,
   ``geometryInstanceId``, ``worldPositionM``, and ``worldNormal`` are
   zero-filled.

.. autodata:: ovrtx.OVRTX_PICK_HIT_MAGIC

.. autodata:: ovrtx.OVRTX_PICK_HIT_VERSION

USD Schema Path Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``OVRTX_PXR_SCHEMA_AUTO_REGISTER=1`` is set, ``import ovrtx`` publishes ovrtx's USD
schema/plugin directories to the ovrtx-namespaced plugin-path env var and upstream
``PXR_PLUGINPATH_NAME``. The hook is disabled by default; call
:func:`ovrtx.register_schema_paths` explicitly when you need bundled-OpenUSD registration
without enabling the import hook. Integrations that want to select or filter the paths
for an external OpenUSD runtime can use :func:`ovrtx.usd_plugin_paths`, which enumerates
the directories without mutating plugin-path env vars. Append any desired subset to
``PXR_PLUGINPATH_NAME`` **before** that external runtime opens its first stage.

In an ovrtx + ovstage process, creating ``ovrtx.Renderer`` first registers these
paths automatically before OpenUSD loads. If ``ovstage.Stage`` (or
``ovstage.library_version()``) runs first, call ``ovrtx.register_schema_paths()``
before it. The registration call loads only the ovrtx shared loader; the ovrtx
runtime remains deferred until renderer initialization.

See :doc:`../core/usd_plugin_paths` for complete, tested workflows.

.. autofunction:: ovrtx.register_schema_paths

.. autofunction:: ovrtx.usd_plugin_paths

.. autofunction:: ovrtx.usd_pluginpath_env_keys

Data Collection
^^^^^^^^^^^^^^^

ovrtx sends one anonymous report per process, when it first initializes, which happens when
the first :class:`ovrtx.Renderer` is created. Set
``NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1`` before starting the process, or call
:func:`ovrtx.library_telemetry_opt_out` before creating that renderer, to turn it off.
See `Data Collection & Use <https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/TELEMETRY.md>`_
for every field in the report.

.. autofunction:: ovrtx.library_telemetry_opt_out

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

Performance Profiling
^^^^^^^^^^^^^^^^^^^^^

Collect simplified performance metrics, grouped RTX stages, and grouped memory data.
Use :py:func:`ovrtx.start_profiling()` after renderer creation and
:py:func:`ovrtx.stop_profiling()` before renderer teardown. The update functions
document retained-batch ownership, measurement meanings, and recommended copy intervals
for data collection and live visualization.

.. autofunction:: ovrtx.start_profiling

.. autofunction:: ovrtx.stop_profiling

.. autofunction:: ovrtx.get_performance_data_update

.. autofunction:: ovrtx.get_performance_data_update_as_json

.. autofunction:: ovrtx.release_performance_data_update

.. autoclass:: ovrtx.ovrtx_performance_data_update_t

.. autofunction:: ovrtx.add_performance_metric_value

.. autofunction:: ovrtx.add_performance_metric_value_with_thread_execution_id

.. autofunction:: ovrtx.add_performance_metric_value_with_custom_execution_id

.. autodata:: ovrtx.OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS

.. autodata:: ovrtx.OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME

Configuration
^^^^^^^^^^^^^

.. autoclass:: ovrtx.RendererConfig
   :members:
   :undoc-members:

.. autoclass:: ovrtx.RenderQuality
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

.. _python-api-render-outputs:

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
   :inherited-members:

.. autoclass:: ovrtx.RenderVarTensor
   :members:
   :undoc-members:
   :inherited-members:

.. autoclass:: ovrtx.RenderVarParam
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
   :inherited-members:

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

.. autoclass:: ovrtx.TextureStreamingMode
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

.. autoclass:: ovrtx.DLDevice
   :members:
   :undoc-members:

.. autoclass:: ovrtx.DLDeviceType
   :members:
   :undoc-members:
