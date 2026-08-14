# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import logging as _logging
import os as _os

from ._src.bindings import (
    OVRTX_LIBRARY_PATH_HINT,
    OVRTX_PICK_FLAG_GIZMO,
    OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO,
    OVRTX_PICK_HIT_MAGIC,
    OVRTX_PICK_HIT_VERSION,
    OVRTX_RENDER_VAR_PICK_HIT,
    AttributeFilterMode,
    FilterKind,
    _ovrtx_loader,
)
from ._src.schema_paths import register_schema_paths, usd_pluginpath_env_keys

# Optionally auto-register ovrtx's USD plugin paths at import time so that
#   import ovrtx
#   import ovphysx
# publishes both subsystems' paths before USD loads. The registration logic
# itself lives in CRenderApiLibLoader.cpp (single source of truth); the Python
# call here is a thin ctypes shim that loads the ovrtx loader DLL and invokes
# the exported `ovrtx_register_schema_paths` C entry point. The C body
# publishes to the env-vars USD's plug registry consults (the bundled-USD-
# renamed `OV_PXR_PLUGINPATH_2511` always, and the OpenUSD upstream default
# `PXR_PLUGINPATH_NAME` under the same opt-in) so a non-renamed peer USD
# co-loaded into the same process picks up our plugin/schema contributions
# too. Failures are logged at WARNING (no silent except: pass) so
# misconfigured deployments — e.g. a source checkout where ovrtx-dynamic was
# never built — surface in normal log output. The hook is opt-in: it only
# runs when OVRTX_PXR_SCHEMA_AUTO_REGISTER=1 is set. By default (unset)
# `import ovrtx` leaves the process env untouched; integrators that want the
# paths published call register_schema_paths() themselves before USD
# initialization.
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

from ._src.dlpack import DLDataType, ManagedDLTensor
from ._src.renderer import Renderer
from ._src.types import (
    AttributeBinding,
    AttributeInfo,
    AttributeMapping,
    BindingFlag,
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

__version__ = "0.4.1"

__all__ = [
    "__version__",
    # global config
    "OVRTX_LIBRARY_PATH_HINT",
    "OVRTX_RENDER_VAR_PICK_HIT",
    "OVRTX_PICK_FLAG_GIZMO",
    "OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO",
    "OVRTX_PICK_HIT_MAGIC",
    "OVRTX_PICK_HIT_VERSION",
    # USD schema/plugin path registration
    "register_schema_paths",
    "usd_pluginpath_env_keys",
    # enums
    "BindingFlag",
    "DataAccess",
    "Device",
    "DLDataType",
    "EventStatus",
    "PrimMode",
    "SelectionFillMode",
    "MotionBvh",
    "TextureStreamingMode",
    "Semantic",
    "AttributeFilterMode",
    "FilterKind",
    # dataclasses
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
    "ManagedDLTensor",
    "MappedRenderVar",
    "Operation",
    "ProductOutput",
    "RenderProductSetOutputs",
    "RenderVarOutput",
    "RenderVarParam",
    "RenderVarTensor",
]
