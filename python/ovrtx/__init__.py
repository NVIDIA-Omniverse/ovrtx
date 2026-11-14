# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import logging as _logging
import os as _os
from pathlib import Path as _Path

from ._src.bindings import (
    OVRTX_LIBRARY_PATH_HINT,
    OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS,
    OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME,
    OVRTX_PICK_FLAG_GIZMO,
    OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO,
    OVRTX_PICK_HIT_MAGIC,
    OVRTX_PICK_HIT_VERSION,
    OVRTX_RENDER_VAR_PICK_HIT,
    AftermathMode,
    AttributeFilterMode,
    FilterKind,
    _ovrtx_loader,
    get_build_info,
    ovrtx_performance_data_update_t,
    library_telemetry_opt_out,
)
from ._src.schema_paths import register_schema_paths, usd_plugin_paths, usd_pluginpath_env_keys

# Optionally auto-register ovrtx's USD plugin paths at import time. The registration
# logic lives in the native ovrtx loader (single source of truth); this Python hook is
# a thin ctypes shim over `ovrtx_register_schema_paths`. The C implementation always
# publishes to the renamed key used by ovrtx's bundled OpenUSD and, under this same
# opt-in, also publishes to upstream `PXR_PLUGINPATH_NAME` for a compatible co-loaded
# OpenUSD runtime. Integrators that want to select the upstream entries themselves can
# use `ovrtx.usd_plugin_paths()` without mutating plugin-path environment variables.
#
# Failures are logged at WARNING so misconfigured deployments surface in normal log
# output. Only the exact value OVRTX_PXR_SCHEMA_AUTO_REGISTER=1 enables the hook; by
# default `import ovrtx` leaves the process environment untouched.
if _os.environ.get("OVRTX_PXR_SCHEMA_AUTO_REGISTER", "0") == "1":
    try:
        register_schema_paths()
    except Exception as _exc:
        _logging.getLogger(__name__).warning(
            "ovrtx auto-register of USD schema paths failed: %s. "
            "ovrtx schemas may be missing from the first stage open. "
            "Call ovrtx.register_schema_paths() manually before USD initialization, "
            "or unset OVRTX_PXR_SCHEMA_AUTO_REGISTER to silence this warning.",
            _exc,
        )

from ._src.dlpack import DLDataType, DLDevice, DLDeviceType
from ._src.renderer import Renderer
from ._src.types import (
    AccessorCapability,
    AttributeBinding,
    AttributeInfo,
    AttributeMapping,
    BindingFlag,
    BuildInfo,
    DataAccess,
    DataHint,
    DataKind,
    DataPinFlag,
    DataRangeStrategy,
    DataStatus,
    DataSubmit,
    Device,
    EventStatus,
    FrameOutput,
    MappedRenderVar,
    MotionBvh,
    Operation,
    OperationCounter,
    OperationStatus,
    PendingFetch,
    PrimMode,
    ProductOutput,
    RendererConfig,
    RenderProductSetOutputs,
    RenderQuality,
    RenderVarOutput,
    RenderVarParam,
    RenderVarTensor,
    SelectionFillMode,
    SelectionGroupStyle,
    Semantic,
    TextureStreamingMode,
)
from .data_provider import (
    DataProvider,
    DataProviderDescriptor,
    DataProviderRegistration,
    DataProviderVTable,
    register_data_provider,
)
from .handles import (
    INVALID_ATTRIBUTE_BINDING_HANDLE,
    INVALID_DATA_PROVIDER_ID,
    INVALID_EVENT_HANDLE,
    INVALID_MAP_HANDLE,
    INVALID_OP_ID,
    INVALID_QUERY_HANDLE,
    INVALID_READ_HANDLE,
    INVALID_RENDER_VAR_OUTPUT_HANDLE,
    INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE,
    INVALID_STEP_RESULT_HANDLE,
    INVALID_USD_HANDLE,
    AttributeBindingHandle,
    DataArrayLeaseId,
    DataProviderId,
    EventHandle,
    MapHandle,
    OpId,
    PrimPath,
    PrimPathList,
    QueryHandle,
    ReadHandle,
    RenderVarOutputHandle,
    RenderVarOutputMapHandle,
    StepResultHandle,
    Token,
    UsdHandle,
)

# Packaged wheels contain an auto-generated _version.py whose version is the
# exact distribution version. Source and editable checkouts have no such file,
# so derive their identity from the same canonical VERSION.md as the native API.
try:
    from ._version import version as __version__
except ModuleNotFoundError as _exc:
    if _exc.name != f"{__name__}._version":
        raise
    _version_path = _Path(__file__).resolve().parents[2] / "VERSION.md"
    try:
        __version__ = _version_path.read_text(encoding="utf-8").strip()
    except OSError as _version_error:
        raise ImportError(
            f"ovrtx package is missing both ovrtx._version and its fallback VERSION.md at {_version_path}"
        ) from _version_error

def start_profiling(output_path: str | None = None, file_name: str | None = None) -> None:
    """Start process-wide CPU/GPU/RTX profiling after creating a renderer.

    With both arguments None, collect live data without saving files.
    Providing either argument enables file capture; an empty string selects its default.

    Args:
        output_path: Existing writable directory, or None for the persistent user directory.
        file_name: Basename without an extension, or None for a timestamp-based name.
            Existing recordings are not overwritten; collisions add a timestamp suffix.

    Raises RuntimeError if profiling is already active or capture cannot start. Serialize capture
    controls with renderer teardown. Stop before destroying the last renderer.
    """
    from ._src.bindings import OVRTX_API_SUCCESS, ovrtx_config_t

    native = _ovrtx_loader.create_bindings(ovrtx_config_t([]))
    result = native.start_profiling(output_path, file_name)
    if result.status != OVRTX_API_SUCCESS:
        raise RuntimeError(native.get_last_error() or "Failed to start profiling")


def stop_profiling() -> None:
    """Stop profiling and flush and close file capture before renderer teardown; may block on output work.

    A no-op when no capture is active. Raises RuntimeError on native failure.
    """
    from ._src.bindings import OVRTX_API_SUCCESS, ovrtx_config_t

    native = _ovrtx_loader.create_bindings(ovrtx_config_t([]))
    result = native.stop_profiling()
    if result.status != OVRTX_API_SUCCESS:
        raise RuntimeError(native.get_last_error() or "Failed to stop profiling")


def add_performance_metric_value(metric_uid: int, value: float) -> None:
    """Append an unattributed value to predefined FPS or Render Thread.

    Args:
        metric_uid: OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
            OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
        value: Sample in the metric's declared units (FPS or milliseconds).

    The sample has execution_id zero. This does not open or close a timed scope.
    """
    from ._src.bindings import ovrtx_config_t

    _ovrtx_loader.create_bindings(ovrtx_config_t([])).add_performance_metric_value(metric_uid, value)


def add_performance_metric_value_with_thread_execution_id(metric_uid: int, value: float) -> None:
    """Append a value to predefined FPS or Render Thread, attributed to the calling thread.

    Args:
        metric_uid: OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
            OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
        value: Sample in the metric's declared units (FPS or milliseconds).

    The nonzero execution_id identifies the calling thread within this process.
    """
    from ._src.bindings import ovrtx_config_t

    _ovrtx_loader.create_bindings(ovrtx_config_t([])).add_performance_metric_value_with_thread_execution_id(metric_uid, value)


def add_performance_metric_value_with_custom_execution_id(metric_uid: int, value: float, execution_id: int) -> None:
    """Append a value to predefined FPS or Render Thread with an explicit execution identity.

    Args:
        metric_uid: OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
            OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
        value: Sample in the metric's declared units (FPS or milliseconds).
        execution_id: Unsigned 32-bit identity stored unchanged; zero means unspecified.
    """
    from ._src.bindings import ovrtx_config_t

    _ovrtx_loader.create_bindings(ovrtx_config_t([])).add_performance_metric_value_with_custom_execution_id(metric_uid, value, execution_id)


def release_performance_data_update(data: ovrtx_performance_data_update_t) -> None:
    """Release a retained batch before renderer teardown and reset it to an empty struct.

    Args:
        data: Retained batch or a zero-initialized struct. Empty release is valid.
            Previous Python-owned copies remain valid, but borrowed native views expire.
    """
    from ._src.bindings import ovrtx_config_t

    _ovrtx_loader.create_bindings(ovrtx_config_t([])).release_performance_data_update(data)


def get_performance_data_update(data: ovrtx_performance_data_update_t) -> tuple[int, list[dict]]:
    """Return (collection_time_ns, metrics) for public metrics only.

    Args:
        data: Zero-initialized batch on the first call. Retain and reuse it for new samples;
            each batch has independent progress, reset automatically on profiling restart.
            Release with release_performance_data_update in finally before renderer teardown.
            Do not copy its handle, use it concurrently or overlap reads with restart/teardown.

    The first call returns retained history. Later calls return newly available samples in
    per-metric collection order, not timestamp order. Sample timestamps can precede an earlier
    returned sample or a previous collection time.
    Collection time is informational, not a cursor or a bound on sample timestamps.
    JSON and structured reads share progress.
    Each metric contains uid, parent_uid, name, units, info, group_name and a values array of
    timestamp_ns/value/parent_uid/execution_id records. Metric parent_uid describes the default
    hierarchy; sample parent_uid identifies that invocation's parent. Returned data is owned by Python.

    RTX stages are grouped by GPU/render graph and viewport. RTX Memory categories are Geometry
    (with subcategories), Textures, Volumes, Gaussians, SPG, Output Buffers and Internal. Values use
    MiB in separate GPU, host and virtual-reservation scopes. Tracked host allocations are not
    process physical memory. Do not sum inclusive parents with children or reservations with
    allocations. Grouped RTX durations can combine separate intervals, not contiguous GPU occupancy.

    Prefer copying every 500 ms-1 s (1-2 Hz), or 200-250 ms (4-5 Hz) for live visualization.
    At no more than 120 samples/s per metric, 4 s accumulates 480 samples per metric and fits
    retained history if bursts, scheduling and copying stay within its margin. Longer intervals
    make larger, slower batches, especially with many RTX and memory metrics. Copying does not
    change sampling cadence or recover overwritten history.
    """
    from ._src.bindings import ovrtx_config_t

    return _ovrtx_loader.create_bindings(ovrtx_config_t([])).get_performance_data_update(data)


def get_performance_data_update_as_json(data: ovrtx_performance_data_update_t) -> tuple[int, str]:
    """Return (collection_time_ns, JSON) with the same public data and retained progress.

    Args:
        data: Retained batch; ownership and progress follow get_performance_data_update.

    Follow get_performance_data_update for grouped-data meanings and polling guidance.
    JSON contains collection_time_ns and metrics. Non-finite sample values are null.
    Raises RuntimeError on native failure; the returned string is Python-owned.
    """
    from ._src.bindings import ovrtx_config_t

    return _ovrtx_loader.create_bindings(ovrtx_config_t([])).get_performance_data_update(data, as_json=True)


__all__ = [
    "INVALID_USD_HANDLE",
    "INVALID_EVENT_HANDLE",
    "INVALID_ATTRIBUTE_BINDING_HANDLE",
    "INVALID_MAP_HANDLE",
    "INVALID_STEP_RESULT_HANDLE",
    "INVALID_RENDER_VAR_OUTPUT_HANDLE",
    "INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE",
    "INVALID_OP_ID",
    "INVALID_QUERY_HANDLE",
    "INVALID_READ_HANDLE",
    "INVALID_DATA_PROVIDER_ID",
    "UsdHandle",
    "EventHandle",
    "AttributeBindingHandle",
    "MapHandle",
    "StepResultHandle",
    "RenderVarOutputHandle",
    "RenderVarOutputMapHandle",
    "OpId",
    "QueryHandle",
    "ReadHandle",
    "DataProviderId",
    "DataArrayLeaseId",
    "__version__",
    "get_build_info",
    "library_telemetry_opt_out",
    "register_data_provider",
    "AccessorCapability",
    "DataProvider",
    "DataProviderDescriptor",
    "DataProviderVTable",
    "DataProviderRegistration",
    "DataStatus",
    "DataSubmit",
    "DataHint",
    "DataPinFlag",
    "DataKind",
    "DataRangeStrategy",
    # global config
    "OVRTX_LIBRARY_PATH_HINT",
    "OVRTX_RENDER_VAR_PICK_HIT",
    "OVRTX_PICK_FLAG_GIZMO",
    "OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO",
    "OVRTX_PICK_HIT_MAGIC",
    "OVRTX_PICK_HIT_VERSION",
    # USD schema/plugin path registration
    "register_schema_paths",
    "usd_plugin_paths",
    "usd_pluginpath_env_keys",
    # enums
    "BindingFlag",
    "DataAccess",
    "Device",
    "DLDataType",
    "DLDevice",
    "DLDeviceType",
    "EventStatus",
    "PrimMode",
    "SelectionFillMode",
    "MotionBvh",
    "TextureStreamingMode",
    "Semantic",
    "AttributeFilterMode",
    "AftermathMode",
    "FilterKind",
    # dataclasses
    "BuildInfo",
    "AttributeInfo",
    "OperationCounter",
    "OperationStatus",
    # dictionary handles
    "Token",
    "PrimPath",
    "PrimPathList",
    # renderer types
    "Renderer",
    "RendererConfig",
    "PendingFetch",
    "RenderQuality",
    "SelectionGroupStyle",
    # return types
    "AttributeBinding",
    "AttributeMapping",
    "FrameOutput",
    "MappedRenderVar",
    "Operation",
    "ProductOutput",
    "RenderProductSetOutputs",
    "RenderVarOutput",
    "RenderVarParam",
    "RenderVarTensor",
    # rtx profiling
    "start_profiling",
    "stop_profiling",
    "add_performance_metric_value",
    "add_performance_metric_value_with_thread_execution_id",
    "add_performance_metric_value_with_custom_execution_id",
    "OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS",
    "OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME",
    "get_performance_data_update",
    "get_performance_data_update_as_json",
    "ovrtx_performance_data_update_t",
    "release_performance_data_update",
]
