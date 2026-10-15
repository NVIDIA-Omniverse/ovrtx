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
)
from ._src.schema_paths import register_schema_paths, usd_plugin_paths, usd_pluginpath_env_keys

# Optionally auto-register ovrtx's USD plugin paths at import time. The registration
# logic lives in CRenderApiLibLoader.cpp (single source of truth); this Python hook is
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
    AttributeBinding,
    AttributeInfo,
    AttributeMapping,
    BindingFlag,
    BuildInfo,
    DataAccess,
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
    RenderVarOutput,
    RenderVarParam,
    RenderVarTensor,
    SelectionFillMode,
    SelectionGroupStyle,
    Semantic,
    TextureStreamingMode,
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

__all__ = [
    "__version__",
    "get_build_info",
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
    # renderer types
    "Renderer",
    "RendererConfig",
    "PendingFetch",
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
]
