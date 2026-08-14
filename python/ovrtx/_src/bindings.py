# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import ctypes
import os
import sys
from enum import IntEnum, IntFlag
from pathlib import Path
from typing import Any, Iterable, List, Optional

from .dlpack import DLDataType, DLTensor


def _resolve_existing_dirs(paths: Iterable[Path]) -> List[Path]:
    """Return ``[p.resolve()]`` for each existing-and-directory entry, OSError-tolerant.

    Used by both ``_LibraryLoader.__init__`` (filtering ``PATH``) and
    ``_load_library`` (filtering caller-supplied hints). Centralized here because
    on Windows the ``PATH`` entry ``%LocalAppData%\\Microsoft\\WindowsApps``
    (the Microsoft Store app-execution-aliases directory) raises
    ``PermissionError`` from ``Path.exists`` / ``is_dir`` / ``resolve``;
    swallowing that per-entry keeps a broken-PATH host from killing every
    ``import ovrtx`` on a default Windows install.
    """
    out: List[Path] = []
    for candidate in paths:
        try:
            if candidate.exists() and candidate.is_dir():
                out.append(candidate.resolve())
        except OSError:
            continue
    return out


class ovx_string_t(ctypes.Structure):
    """ovx_string_t binding class"""

    _fields_ = [  # these must match the ovx_string_t struct in ovx_types.h
        ("ptr", ctypes.c_char_p),
        ("length", ctypes.c_size_t),
    ]

    def __init__(self, value=None):
        """Constructor that accepts any value convertible to string.

        Args:
            value: Any value that can be converted to string using str().
                  If None, creates an empty string structure.
        """
        super().__init__()

        encoded = str(value if value is not None else "").encode("utf-8")
        self._bytes = ctypes.create_string_buffer(encoded)
        self.ptr = ctypes.cast(self._bytes, ctypes.c_char_p)
        self.length = len(encoded)

    def __bool__(self) -> bool:
        """Return True if string is non-null and non-empty."""
        return self.ptr is not None and self.length > 0

    def __len__(self) -> int:
        """Return byte length (excluding null terminator)."""
        return int(self.length)

    def __str__(self) -> str:
        """Convert to Python string. Treats string as null-terminated."""
        return ctypes.string_at(self.ptr).decode("utf-8", errors="replace") if self.ptr is not None else ""

    def __repr__(self):
        value_repr = repr(str(self)) if self.ptr is not None else "None"
        return f"ovx_string_t({value_repr}, ptr={self.ptr}, length={self.length})"


# ovrtx_config_key_type_t
class ConfigKeyType(IntEnum):
    """Config entry value type tag."""

    BOOL = 0
    INT64 = 1
    UINT64 = 2
    DOUBLE = 3
    STRING = 4
    BLOB = 5


# ovrtx_config_bool_t
class ConfigBoolKey(IntEnum):
    """Bool-valued renderer configuration keys."""

    SYNC_MODE = 0
    ENABLE_PROFILING = 1
    READ_GPU_TRANSFORMS = 2
    KEEP_SYSTEM_ALIVE = 3
    USE_VULKAN = 4
    SELECTION_OUTLINE_ENABLED = 5
    ENABLE_GEOMETRY_STREAMING = 6
    ENABLE_GEOMETRY_STREAMING_LOD = 7
    ENABLE_SPG = 8
    SUPPRESS_DEPRECATION_WARNINGS = 9


# ovrtx_config_string_t
class ConfigStringKey(IntEnum):
    """String-valued renderer configuration keys."""

    LOG_FILE_PATH = 1
    LOG_LEVEL = 2
    ACTIVE_CUDA_GPUS = 3
    DATASTORE_CACHE = 4


# ovrtx_config_int64_t
class ConfigInt64Key(IntEnum):
    """Int64-valued renderer configuration keys."""

    SELECTION_OUTLINE_WIDTH = 0
    SELECTION_FILL_MODE = 1
    MOTION_BVH = 2
    _ATTACH_MODE = 3
    DOME_BAKING_RESOLUTION = 4
    TEXTURE_STREAMING_MODE = 5


# ovrtx_config_double_t
class ConfigDoubleKey(IntEnum):
    """Double-valued renderer configuration keys."""

    pass


# ovrtx_selection_fill_mode_t
class SelectionFillMode(IntEnum):
    """Selection-outline interior (fill) mode.

    Controls how the interior of selection-outlined prims is filled, parallel to
    the underlying RTX shader's ``OutlineMode``. Set globally at renderer
    creation via :attr:`RendererConfig.selection_fill_mode` (which maps to
    ``OVRTX_CONFIG_SELECTION_FILL_MODE``); changing it requires recreating the
    renderer.
    """

    EDGE_ONLY = 0
    """No interior fill — only the outline edge is drawn."""
    GLOBAL = 1
    """Interior is filled with a single global intersection color shared across all groups."""
    GROUP_OUTLINE_COLOR = 2
    """Interior is filled with each group's outline color."""
    GROUP_FILL_COLOR = 3
    """Interior is filled with each group's dedicated fill/shade color."""


# ovrtx_motion_bvh_t
class MotionBvh(IntEnum):
    """Motion BVH (ray-traced motion) mode for sensor pipelines.

    Set at renderer creation via :attr:`RendererConfig.motion_bvh` (maps to
    ``OVRTX_CONFIG_MOTION_BVH``); changing it requires recreating the renderer.
    """

    DISABLE = 0
    """Motion BVH off (default when unset)."""
    ENABLE = 1
    """Motion BVH enabled from renderer creation."""
    AUTO = 2
    """Motion BVH enabled at runtime when a non-visual sensor is rendered."""


# ovrtx_texture_streaming_mode_t
class TextureStreamingMode(IntEnum):
    """Texture streaming behavior selected when the renderer is created.

    ``SYNCHRONOUS`` controls texture-feedback processing; it does not make all
    texture loading operations synchronous. The mode is process-global and
    applies to all active renderer instances.
    """

    DISABLE = 0
    """Texture streaming is disabled."""
    SYNCHRONOUS = 1
    """Texture streaming is enabled and texture feedback is processed synchronously."""
    ASYNCHRONOUS = 2
    """Texture streaming is enabled and texture feedback is processed asynchronously (default)."""


# ovrtx_attach_mode_t
class _AttachMode(IntEnum):
    """How an attached ovstage instance feeds data into the renderer.

    Internal development option fixed for a renderer's lifetime.
    """

    BORROW = 0
    """Zero-copy: the renderer renders directly out of ovstage's Fabric (default)."""
    REPLICATE = 1
    """The renderer keeps its own UsdStage / Fabric; update_from_stage pulls committed ovstage state into it."""


class ovrtx_config_key_type_t(ctypes.c_int):
    pass


class ovrtx_config_blob_value_t(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
    ]


class ovrtx_config_entry_t(ctypes.Structure):
    """Single config entry. key_type selects which key and value union members are valid."""

    class _KeyUnion(ctypes.Union):
        _fields_ = [
            ("bool_key", ctypes.c_int),
            ("int64_key", ctypes.c_int),
            ("uint64_key", ctypes.c_int),
            ("double_key", ctypes.c_int),
            ("string_key", ctypes.c_int),
            ("blob_key", ctypes.c_int),
        ]

    class _ValueUnion(ctypes.Union):
        _fields_ = [
            ("bool_value", ctypes.c_bool),
            ("int_value", ctypes.c_int64),
            ("uint_value", ctypes.c_uint64),
            ("double_value", ctypes.c_double),
            ("string_value", ovx_string_t),
            ("blob_value", ovrtx_config_blob_value_t),
        ]

    _fields_ = [
        ("key_type", ovrtx_config_key_type_t),
        ("key", _KeyUnion),
        ("value", _ValueUnion),
    ]


def ovrtx_config_entry_bool(key: int, value: bool) -> ovrtx_config_entry_t:
    """Build a config entry for a boolean setting."""
    entry = ovrtx_config_entry_t()
    entry.key_type = ConfigKeyType.BOOL
    entry.key.bool_key = key
    entry.value.bool_value = value
    return entry


def ovrtx_config_entry_int(key: int, value: int) -> ovrtx_config_entry_t:
    """Build a config entry for an int64 setting."""
    entry = ovrtx_config_entry_t()
    entry.key_type = ConfigKeyType.INT64
    entry.key.int64_key = key
    entry.value.int_value = value
    return entry


def ovrtx_config_entry_string(key: int, value: str) -> ovrtx_config_entry_t:
    """Build a config entry for a string setting.

    Constructs an ovx_string_t internally and attaches it as entry._string_ref
    to prevent GC of the underlying buffer.  ctypes only copies the C-level
    ptr/length into the union -- the Python _bytes attribute that owns the
    buffer memory is NOT copied.  All shallow copies (union field, C array)
    share the same ptr; the single buffer is owned by _string_ref._bytes.
    The companion ovrtx_config_t stores _entries to keep entries (and therefore
    their _string_ref) alive for the entire config lifetime.
    """
    entry = ovrtx_config_entry_t()
    entry.key_type = ConfigKeyType.STRING
    entry.key.string_key = key
    entry._string_ref = ovx_string_t(value)
    entry.value.string_value = entry._string_ref
    return entry


def ovrtx_config_entry_blob(key: int, value: bytes) -> ovrtx_config_entry_t:
    """Build a config entry for a blob setting.

    Creates a ctypes buffer internally and attaches it as entry._blob_ref
    to prevent GC of the underlying data.  Same lifetime pattern as
    ovrtx_config_entry_string -- see its docstring for details.
    """
    entry = ovrtx_config_entry_t()
    entry.key_type = ConfigKeyType.BLOB
    entry.key.blob_key = key
    entry._blob_ref = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    entry.value.blob_value.data = ctypes.addressof(entry._blob_ref)
    entry.value.blob_value.size = len(value)
    return entry


class ovrtx_config_t(ctypes.Structure):
    """Config container passed to ovrtx_initialize() and ovrtx_create_renderer()."""

    _fields_ = [
        ("entries", ctypes.POINTER(ovrtx_config_entry_t)),
        ("entry_count", ctypes.c_size_t),
    ]

    def __init__(self, entries: list[ovrtx_config_entry_t]):
        if entries:
            self._array = (ovrtx_config_entry_t * len(entries))(*entries)
            # Keep the original Python entry objects alive.  The C array (_array)
            # only contains byte copies, but each entry may hold _string_ref (or
            # _blob_ref) attributes whose underlying buffers are still referenced
            # by the copied C-level pointers.  Dropping _entries would allow GC to
            # collect those buffers while the C array still points to them.
            self._entries = entries
            super().__init__(entries=self._array, entry_count=len(entries))
        else:
            super().__init__(entries=None, entry_count=0)
            self._array = None
            self._entries = []


class ovrtx_renderer_t(ctypes.Structure):
    """ovrtx_renderer_t binding class (fully opaque)"""

    pass


# Opaque ovstage types used only at the OVRTX C ABI boundary.
ovstage_instance_p = ctypes.c_void_p
ovstage_ordinal_t = ctypes.c_uint64


# OVRTX API Status Constants
OVRTX_API_SUCCESS: int = 0
OVRTX_API_ERROR: int = 1
OVRTX_API_TIMEOUT: int = 2


class ovrtx_api_status_t(ctypes.c_int32):
    """ovrtx_api_status_t binding class"""

    def __eq__(self, other):
        return self.value == int(other) if isinstance(other, (int, ovrtx_api_status_t)) else NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        return not result if result is not NotImplemented else NotImplemented


class ovrtx_result_t(ctypes.Structure):
    """ovrtx_result_t binding class."""

    _fields_ = [
        ("status", ovrtx_api_status_t),
    ]


class ovrtx_timeout_t(ctypes.Structure):
    """ovrtx_timeout_t binding class"""

    _fields_ = [
        ("time_out_ns", ctypes.c_uint64),
    ]


OVRTX_TIMEOUT_INFINITE = ovrtx_timeout_t(time_out_ns=0xFFFFFFFFFFFFFFFF)


class ovrtx_op_id_t(ctypes.c_uint64):
    """ovrtx_op_id_t binding class for operation IDs"""

    pass


class ovrtx_op_wait_result_t(ctypes.Structure):
    """ovrtx_op_wait_result_t binding class.

    Note: error_op_ids contains op IDs that errored. Use get_last_op_error(op_id)
    to get the error string for each failed operation.
    """

    _fields_ = [
        ("error_op_ids", ctypes.POINTER(ovrtx_op_id_t)),
        ("num_error_ops", ctypes.c_size_t),
        ("lowest_pending_op_id", ovrtx_op_id_t),
    ]


class ovrtx_op_counter_t(ctypes.Structure):
    """ovrtx_op_counter_t — named resource counter from a progress query."""

    _fields_ = [
        ("name", ovx_string_t),
        ("current", ctypes.c_uint64),
        ("total", ctypes.c_uint64),
    ]


class ovrtx_op_status_t(ctypes.Structure):
    """ovrtx_op_status_t — operation progress snapshot."""

    _fields_ = [
        ("op_id", ovrtx_op_id_t),
        ("state", ctypes.c_int),  # ovrtx_event_status_t
        ("progress", ctypes.c_double),
        ("counters", ctypes.POINTER(ovrtx_op_counter_t)),
        ("counter_count", ctypes.c_size_t),
    ]


class ovrtx_usd_handle_t(ctypes.c_uint64):
    """ovrtx_usd_handle_t binding class for USD file handles"""

    pass


class ovrtx_enqueue_result_t(ctypes.Structure):
    """Result from an asynchronous API call.

    ``status`` is the API call status, not necessarily the final operation execution result.
    ``op_index`` is non-zero when an operation was enqueued, or zero otherwise.
    In sync mode, execution errors can return ``OVRTX_API_ERROR`` while still providing a non-zero ``op_index``.
    """

    _fields_ = [
        ("status", ovrtx_api_status_t),
        ("op_index", ovrtx_op_id_t),
    ]


class ovrtx_render_product_set_t(ctypes.Structure):
    """ovrtx_render_product_set_t binding class"""

    _fields_ = [
        ("render_products", ctypes.POINTER(ovx_string_t)),
        ("num_render_products", ctypes.c_size_t),
    ]


# Pick query / pick-hit (multi-tensor render variable ``ovrtx_pick_hit``)
OVRTX_RENDER_VAR_PICK_HIT = "ovrtx_pick_hit"
OVRTX_PICK_FLAG_GIZMO = 1 << 0
OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO = 1 << 1
# Schema-identity / schema-version handshake. Surfaced as ``uint32`` params named
# ``magic`` and ``version`` on the mapped render variable; consumers must validate
# both before reading the v1 tensor schema (``primPath`` / ``objectType`` /
# ``geometryInstanceId`` / ``worldPositionM`` / ``worldNormal``).
OVRTX_PICK_HIT_MAGIC = 0x56505448
OVRTX_PICK_HIT_VERSION = 1


class ovrtx_pick_query_desc_t(ctypes.Structure):
    """Pick rectangle in normalized RenderProduct coordinates; see ``ovrtx_enqueue_pick_query``."""

    _fields_ = [
        ("render_product_path", ovx_string_t),
        ("left_ndc", ctypes.c_float),
        ("top_ndc", ctypes.c_float),
        ("right_ndc", ctypes.c_float),
        ("bottom_ndc", ctypes.c_float),
        ("flags", ctypes.c_uint32),
    ]


class ovrtx_selection_group_style_t(ctypes.Structure):
    """Per-group selection-outline / fill colors. RGBA components in [0, 1].

    Pairs with :func:`ovrtx_set_selection_group_styles` (group_id is supplied
    in a parallel uint8 array).
    """

    _fields_ = [
        ("outline_color", ctypes.c_float * 4),
        ("fill_color", ctypes.c_float * 4),
    ]


class ovrtx_step_result_handle_t(ctypes.c_uint64):
    """ovrtx_step_result_handle_t binding class for step result handles"""

    pass


# ovrtx_event_status_t
class EventStatus(IntEnum):
    """Operation event status.

    Indicates whether an asynchronous operation is still running,
    has completed successfully, or has failed.
    """

    PENDING = 0
    COMPLETED = 1
    FAILURE = 2


# ovrtx_map_device_type_t
class Device(IntEnum):
    """Device type for attribute mapping and render output mapping.

    Controls where mapped tensor data resides. ``DEFAULT`` lets the
    runtime pick the most efficient format; ``CPU`` forces a synchronous
    copy to host memory; ``CUDA`` returns raw device pointers; and
    ``CUDA_ARRAY`` returns a CUDA array handle (zero-copy for images).
    """

    DEFAULT = 0
    CPU = 1
    CUDA = 2
    CUDA_ARRAY = 3


# Simple type alias - render variable output handles are just uint64 values
# We don't derive from ctypes types to avoid instance creation issues
ovrtx_render_var_output_handle_t = ctypes.c_uint64


# Render output description structures
class ovrtx_render_product_render_var_output_t(ctypes.Structure):
    """Single render variable output (e.g., 'rgb', 'depth')."""

    _fields_ = [
        ("render_var_name", ovx_string_t),
        ("output_handle", ctypes.c_uint64),  # Plain c_uint64, not type alias
    ]


class ovrtx_accumulation_status_t(ctypes.Structure):
    """Path-tracing accumulation status for a rendered frame.

    Matches ovrtx_accumulation_status_t from ovrtx_types.h.
    """

    _fields_ = [
        ("progression", ctypes.c_uint32),
        ("converged", ctypes.c_bool),
    ]


class ovrtx_render_product_frame_output_t(ctypes.Structure):
    """Single frame output with multiple render variables."""

    _fields_ = [
        ("frame_start_time", ctypes.c_double),
        ("frame_end_time", ctypes.c_double),
        ("output_render_vars", ctypes.POINTER(ovrtx_render_product_render_var_output_t)),
        ("render_var_count", ctypes.c_size_t),
        ("accumulation_status", ovrtx_accumulation_status_t),
    ]


class ovrtx_render_product_output_t(ctypes.Structure):
    """Single render product output with multiple frames."""

    _fields_ = [
        ("render_product_path", ovx_string_t),
        ("output_frames_produced", ctypes.c_float),
        ("output_frames", ctypes.POINTER(ovrtx_render_product_frame_output_t)),
        ("output_frame_count", ctypes.c_size_t),
    ]


class ovrtx_render_product_set_outputs_t(ctypes.Structure):
    """Complete output description from a step operation."""

    _fields_ = [
        ("status", ctypes.c_int),
        ("error_message", ovx_string_t),
        ("simulation_start_time", ctypes.c_double),
        ("simulation_end_time", ctypes.c_double),
        ("outputs", ctypes.POINTER(ovrtx_render_product_output_t)),
        ("output_count", ctypes.c_size_t),
        ("start_time", ctypes.c_double),
        ("end_time", ctypes.c_double),
    ]


class ovrtx_cuda_sync_t(ctypes.Structure):
    """CUDA synchronization hints.

    Matches ovrtx_cuda_sync_t from ovrtx_types.h.

    Fields:
        stream: CUDA stream to synchronize to. 0 = no sync, 1 = default stream, >1 = specific stream
        wait_event: Event to wait on before operation (0 = none)
    """

    _fields_ = [
        ("stream", ctypes.c_size_t),  # uintptr_t
        ("wait_event", ctypes.c_size_t),  # uintptr_t
    ]


class ovrtx_output_buffer_t(ctypes.Structure):
    """Output buffer wrapping a DLTensor with optional CUDA synchronization.

    This is an ovrtx-specific extension wrapping the standard DLTensor.
    """

    _fields_ = [
        ("dl", DLTensor),  # DLPack tensor
        ("cuda_sync", ovrtx_cuda_sync_t),  # CUDA sync info (stream + event)
    ]


# Type alias for map handles (uint64)
ovrtx_render_var_output_map_handle_t = ctypes.c_uint64


class ovrtx_map_output_description_t(ctypes.Structure):
    """Description for mapping rendered output to specific device.

    Fields:
        device_type: ovrtx_map_device_type_t (DEFAULT=0, CPU=1, CUDA=2, CUDA_ARRAY=3)
        sync_stream: uintptr_t for CUDA stream (0=no sync, 1=default stream, >1=specific stream)
    """

    _fields_ = [
        ("device_type", ctypes.c_int),
        ("sync_stream", ctypes.c_void_p),
    ]


class ovrtx_render_var_tensor_t(ctypes.Structure):
    """One named DLPack tensor slot in a mapped render variable output.

    Matches the C struct in ovrtx_types.h: all fields are pointers into
    C-side memory whose lifetime is tied to the parent map_handle.
    """

    _fields_ = [
        ("dl", ctypes.POINTER(DLTensor)),  # const DLTensor*
        ("name", ctypes.POINTER(ovx_string_t)),  # const ovx_string_t*
        ("doc", ctypes.POINTER(ovx_string_t)),  # const ovx_string_t*
    ]


class ovrtx_render_var_param_t(ctypes.Structure):
    """One named CPU-resident param value in a mapped render variable output.

    Matches the C struct in ovrtx_types.h: dl is by value (DLTensor inline),
    name and doc are by value (ovx_string_t inline). The DLTensor's data /
    shape / strides pointers reference C-side memory tied to the parent
    map_handle.
    """

    _fields_ = [
        ("dl", DLTensor),  # DLTensor (by value, always CPU)
        ("name", ovx_string_t),
        ("doc", ovx_string_t),
    ]


class ovrtx_render_var_output_t(ctypes.Structure):
    """Mapped render variable output: bundle of named tensors, named params, and description fields.

    Lifetime: all pointer fields and inner DLTensor data/shape/strides remain valid
    from ovrtx_map_render_var_output until ovrtx_unmap_render_var_output.
    """

    _fields_ = [
        ("status", ctypes.c_int),  # ovrtx_event_status_t
        ("error_message", ovx_string_t),
        ("map_handle", ctypes.c_uint64),  # ovrtx_render_var_output_map_handle_t
        ("cuda_sync", ovrtx_cuda_sync_t),  # ONE shared sync, covers all tensors
        ("name", ovx_string_t),  # Render variable name (e.g. "PointCloud", "HdrColor")
        ("type", ovx_string_t),  # Semantic type identifier
        ("doc", ovx_string_t),  # Human-readable description
        ("version", ctypes.c_int),  # Output schema version (signed int per C)
        ("num_tensors", ctypes.c_size_t),
        ("tensors", ctypes.POINTER(ovrtx_render_var_tensor_t)),  # const ovrtx_render_var_tensor_t*
        ("num_params", ctypes.c_size_t),
        ("params", ctypes.POINTER(ovrtx_render_var_param_t)),  # const ovrtx_render_var_param_t*
    ]


# ============================================================================
# Phase 1.1: Attribute write structures and enums
# ============================================================================


# ovrtx_attribute_semantic_t
class Semantic(IntEnum):
    """Attribute semantic type for write, bind, and map operations.

    Specifies the interpretation of attribute data. For write methods, the
    semantic can often be omitted — the element type is inferred from the
    input data. For bind/map methods, ``dtype``/``shape`` is the recommended
    alternative for standard tensor types.

    The C API defines two additional packed-struct transform semantics
    (``XFORM_POS3d_ROT4f_SCALE3f = 2``, ``XFORM_POS3d_ROT3x3f = 3``)
    that are intentionally omitted here. Their heterogeneous layouts
    (mixed float32/float64 fields) have no natural NumPy or Warp
    representation, so they cannot be used without manual byte packing.
    """

    NONE = 0
    XFORM_MAT4x4 = 1  # Row-major 4x4 double matrix (kDLFloat, 64, 16)
    PATH_STRING = 4  # Prim paths as ovx_string_t (kDLUInt, 128, 1). Sync data access only.
    TOKEN_STRING = 5  # String tokens as ovx_string_t (kDLUInt, 128, 1). Sync data access only.
    TOKEN_ID = 6  # Raw token ID (kDLUInt, 64, 1). Resolve via path dictionary.
    PATH_ID = 7  # Raw path ID (kDLUInt, 64, 1). Resolve via path dictionary.
    TAG = 8  # Name-only attribute with no value or storage. Do not read data.


class ovrtx_attribute_semantic_t(ctypes.c_int):
    """Attribute semantic type enum."""

    pass


# ovrtx_binding_prim_mode_t
class PrimMode(IntEnum):
    """Prim binding mode controlling how prim paths are resolved.

    ``EXISTING_ONLY`` matches only prims that already exist on the stage.
    ``MUST_EXIST`` raises an error if the prim is not found.
    ``CREATE_NEW`` creates the prim if it does not exist.
    """

    EXISTING_ONLY = 0
    MUST_EXIST = 1
    CREATE_NEW = 2


class ovrtx_binding_prim_mode_t(ctypes.c_int):
    """Prim binding mode enum."""

    pass


# ovrtx_binding_flag_t
class BindingFlag(IntFlag):
    """Binding optimization hint flags (bitmask).

    Flags can be combined with ``|``:  ``BindingFlag.OPTIMIZE | future_flag``.
    """

    NONE = 0
    OPTIMIZE = 1 << 0


class ovrtx_binding_flag_t(ctypes.c_int):
    """Binding flag enum."""

    pass


# ovrtx_data_access_t
class DataAccess(IntEnum):
    """Data access mode for attribute write operations.

    ``SYNC`` copies input data immediately so the caller's buffer can be
    reused right away. ``ASYNC`` references the caller's buffer until the
    operation completes (zero-copy).
    """

    ASYNC = 0
    SYNC = 1


class ovrtx_data_access_t(ctypes.c_int):
    """Data access mode enum."""

    pass


# Type aliases
ovrtx_attribute_binding_handle_t = ctypes.c_uint64
ovrtx_map_handle_t = ctypes.c_uint64


class ovx_string_or_token_t(ctypes.Structure):
    """String or token union for attribute names."""

    _fields_ = [
        ("token", ctypes.c_uint64),  # ovx_token_t
        ("string", ovx_string_t),
    ]


class ovrtx_prim_list_t(ctypes.Structure):
    """List of prim paths."""

    _fields_ = [
        ("prim_paths", ctypes.POINTER(ovx_string_t)),  # const ovx_string_t*
        ("num_paths", ctypes.c_size_t),
    ]


class ovrtx_attribute_type_t(ctypes.Structure):
    """Attribute type descriptor."""

    _fields_ = [
        ("dtype", DLDataType),
        ("is_array", ctypes.c_bool),
        ("semantic", ovrtx_attribute_semantic_t),
    ]


class ovrtx_binding_desc_t(ctypes.Structure):
    """Attribute binding descriptor."""

    _fields_ = [
        ("prim_list", ovrtx_prim_list_t),
        ("prims_list_handle", ctypes.c_uint64),  # ovx_primpath_list_t
        ("attribute_name", ovx_string_or_token_t),
        ("attribute_type", ovrtx_attribute_type_t),
        ("prim_mode", ovrtx_binding_prim_mode_t),
        ("flags", ovrtx_binding_flag_t),
    ]


class ovrtx_binding_desc_or_handle_t(ctypes.Structure):
    """Binding descriptor or handle union."""

    _fields_ = [
        ("binding_desc", ovrtx_binding_desc_t),
        ("binding_handle", ovrtx_attribute_binding_handle_t),
    ]


class ovrtx_input_buffer_t(ctypes.Structure):
    """Input buffer for attribute writes."""

    _fields_ = [
        ("tensors", ctypes.POINTER(DLTensor)),
        ("tensor_count", ctypes.c_uint64),
        ("dirty_bits", ctypes.POINTER(ctypes.c_uint8)),
        ("dirty_bits_size", ctypes.c_size_t),
        ("access_cuda_sync", ovrtx_cuda_sync_t),
        ("done_cuda_sync", ovrtx_cuda_sync_t),
    ]


class ovrtx_read_dest_t(ctypes.Structure):
    """Optional destination tensor for scalar reads."""

    _fields_ = [
        ("tensor", ctypes.POINTER(DLTensor)),
        ("access_cuda_sync", ovrtx_cuda_sync_t),
        ("done_cuda_sync", ovrtx_cuda_sync_t),
    ]


class ovrtx_mapping_desc_t(ctypes.Structure):
    """Descriptor for attribute mapping."""

    _fields_ = [
        ("device_type", ctypes.c_int32),  # DLDevice device_type
        ("device_id", ctypes.c_int32),  # DLDevice device_id
    ]


class ovrtx_attribute_mapping_t(ctypes.Structure):
    """Result from map_attribute."""

    _fields_ = [
        ("map_handle", ovrtx_map_handle_t),  # Handle for unmap operation
        ("dl", DLTensor),  # Mapped memory as tensor, valid until unmap
    ]


# ============================================================================
# Stage query and attribute read structures
# ============================================================================

# Type aliases for query/read handles
ovrtx_query_handle_t = ctypes.c_uint64
ovrtx_read_handle_t = ctypes.c_uint64


class FilterKind(IntEnum):
    """Kind of prim filter criterion for query_prims.

    Each filter matches prims by a single criterion (type name or attribute
    existence). Combine multiple filters via ``require_all``, ``require_any``,
    and ``exclude`` lists.
    """

    PRIM_TYPE = 0  # Match by USD prim type name (e.g. "Mesh", "SphereLight")
    HAS_ATTRIBUTE = 1  # Match by attribute existence (e.g. "points", "radius")


class ovrtx_filter_kind_t(ctypes.c_int):
    """Filter kind enum (ctypes)."""

    pass


class ovrtx_filter_t(ctypes.Structure):
    """Single prim filter criterion."""

    _fields_ = [
        ("kind", ovrtx_filter_kind_t),
        ("name", ovx_string_or_token_t),
    ]


class AttributeFilterMode(IntEnum):
    """Controls which attributes are reported per prim group in query results.

    ``NONE`` returns only prim grouping (lightweight prim counting).
    ``ALL`` returns every attribute descriptor on each group.
    ``SPECIFIC`` returns only a named subset (pass names via ``attribute_names``).
    """

    NONE = 0
    ALL = 1
    SPECIFIC = 2


class ovrtx_attribute_filter_mode_t(ctypes.c_int):
    """Attribute filter mode enum (ctypes)."""

    pass


class ovrtx_attribute_filter_t(ctypes.Structure):
    """Attribute filter specifying which attributes to report per group."""

    _fields_ = [
        ("mode", ovrtx_attribute_filter_mode_t),
        ("attribute_names", ctypes.POINTER(ovx_string_or_token_t)),
        ("attribute_name_count", ctypes.c_size_t),
    ]


class ovrtx_query_desc_t(ctypes.Structure):
    """Query descriptor for ovrtx_query_prims."""

    _fields_ = [
        ("require_all", ctypes.POINTER(ovrtx_filter_t)),
        ("require_all_count", ctypes.c_size_t),
        ("require_any", ctypes.POINTER(ovrtx_filter_t)),
        ("require_any_count", ctypes.c_size_t),
        ("exclude", ctypes.POINTER(ovrtx_filter_t)),
        ("exclude_count", ctypes.c_size_t),
        ("attribute_filter", ovrtx_attribute_filter_t),
    ]


class ovrtx_attribute_desc_t(ctypes.Structure):
    """Attribute descriptor returned in query results."""

    _fields_ = [
        ("name", ctypes.c_uint64),  # ovx_token_t
        ("type", ovrtx_attribute_type_t),
    ]


class ovrtx_query_prim_group_t(ctypes.Structure):
    """A group of prims sharing the same attribute schema."""

    _fields_ = [
        ("prim_count", ctypes.c_size_t),
        ("prim_list_handle", ctypes.c_uint64),  # ovx_primpath_list_t
        ("attributes", ctypes.POINTER(ovrtx_attribute_desc_t)),
        ("attribute_count", ctypes.c_size_t),
    ]


class ovrtx_query_result_t(ctypes.Structure):
    """Result of a query operation."""

    _fields_ = [
        ("groups", ctypes.POINTER(ovrtx_query_prim_group_t)),
        ("group_count", ctypes.c_size_t),
        ("total_prim_count", ctypes.c_size_t),
    ]


class ovrtx_read_output_t(ctypes.Structure):
    """Attribute read output returned by :func:`fetch_read_result`."""

    _fields_ = [
        ("buffers", ctypes.POINTER(ovrtx_output_buffer_t)),
        ("buffer_count", ctypes.c_size_t),
        ("prim_count", ctypes.c_size_t),
        ("is_array", ctypes.c_bool),
    ]


# Path dictionary types


class ovx_api_result_t(ctypes.Structure):
    """Result from an ovx API call (status + error string)."""

    _fields_ = [
        ("status", ctypes.c_int),
        ("error", ovx_string_t),
    ]


_PD_CTX = ctypes.c_void_p
_TOKEN = ctypes.c_uint64
_PRIMPATH = ctypes.c_uint64
_PATHLIST = ctypes.c_uint64

# Function pointer types for path_dictionary_vtable_t, matching path_dictionary.h
_FN_create_tokens_from_strings = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, ctypes.POINTER(ovx_string_t), ctypes.c_size_t, ctypes.POINTER(_TOKEN)
)
_FN_create_paths_from_tokens = ctypes.CFUNCTYPE(
    ovx_api_result_t,
    _PD_CTX,
    ctypes.POINTER(_TOKEN),
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.c_size_t,
    ctypes.POINTER(_PRIMPATH),
)
_FN_create_paths_from_strings = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, ctypes.POINTER(ovx_string_t), ctypes.c_size_t, ctypes.POINTER(_PRIMPATH)
)
_FN_create_path_list_from_paths = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, ctypes.POINTER(_PRIMPATH), ctypes.c_size_t, ctypes.POINTER(_PATHLIST)
)
_FN_create_path_list_from_strings = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, ctypes.POINTER(ovx_string_t), ctypes.c_size_t, ctypes.POINTER(_PATHLIST)
)
_FN_add_path_list_reference = ctypes.CFUNCTYPE(ovx_api_result_t, _PD_CTX, _PATHLIST)
_FN_release_path_list_reference = ctypes.CFUNCTYPE(ovx_api_result_t, _PD_CTX, _PATHLIST)
_FN_get_strings_from_tokens = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, ctypes.POINTER(_TOKEN), ctypes.c_size_t, ctypes.POINTER(ovx_string_t)
)
_FN_get_tokens_from_paths = ctypes.CFUNCTYPE(
    ovx_api_result_t,
    _PD_CTX,
    ctypes.POINTER(_PRIMPATH),
    ctypes.c_size_t,
    ctypes.POINTER(_TOKEN),
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.POINTER(_TOKEN)),
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(ctypes.c_size_t),
)
_FN_get_num_paths_from_path_list = ctypes.CFUNCTYPE(
    ovx_api_result_t, _PD_CTX, _PATHLIST, ctypes.POINTER(ctypes.c_size_t)
)
_FN_get_paths_from_path_list = ctypes.CFUNCTYPE(
    ovx_api_result_t,
    _PD_CTX,
    _PATHLIST,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.POINTER(_PRIMPATH),
    ctypes.POINTER(ctypes.c_size_t),
)
_FN_release_error = ctypes.CFUNCTYPE(None, _PD_CTX, ovx_string_t)


class path_dictionary_vtable_t(ctypes.Structure):
    """Path dictionary vtable — function pointers for token/path resolution."""

    _fields_ = [
        ("create_tokens_from_strings", _FN_create_tokens_from_strings),
        ("create_paths_from_tokens", _FN_create_paths_from_tokens),
        ("create_paths_from_strings", _FN_create_paths_from_strings),
        ("create_path_list_from_paths", _FN_create_path_list_from_paths),
        ("create_path_list_from_strings", _FN_create_path_list_from_strings),
        ("add_path_list_reference", _FN_add_path_list_reference),
        ("release_path_list_reference", _FN_release_path_list_reference),
        ("get_strings_from_tokens", _FN_get_strings_from_tokens),
        ("get_tokens_from_paths", _FN_get_tokens_from_paths),
        ("get_num_paths_from_path_list", _FN_get_num_paths_from_path_list),
        ("get_paths_from_path_list", _FN_get_paths_from_path_list),
        ("release_error", _FN_release_error),
    ]


class path_dictionary_instance_t(ctypes.Structure):
    """Path dictionary instance."""

    _fields_ = [
        ("vtable", ctypes.POINTER(path_dictionary_vtable_t)),
        ("context", ctypes.c_void_p),
    ]

    def token_to_string(self, token: int) -> str:
        """Resolve a single token handle to a string."""
        t = _TOKEN(token)
        out = ovx_string_t()
        self.vtable.contents.get_strings_from_tokens(self.context, ctypes.byref(t), 1, ctypes.byref(out))
        return str(out) if out.ptr else ""

    def prim_path_to_string(self, prim_path: int) -> str:
        """Resolve a single prim path handle to a string like '/World/Cube'."""
        p = _PRIMPATH(prim_path)
        token_buf = (_TOKEN * 64)()
        tokens_out = ctypes.POINTER(_TOKEN)()
        num_tokens = ctypes.c_size_t(0)
        num_processed = ctypes.c_size_t(0)
        self.vtable.contents.get_tokens_from_paths(
            self.context,
            ctypes.byref(p),
            1,
            token_buf,
            64,
            ctypes.byref(tokens_out),
            ctypes.byref(num_tokens),
            ctypes.byref(num_processed),
        )
        if num_processed.value == 0 or num_tokens.value == 0:
            return ""
        parts = []
        for i in range(num_tokens.value):
            parts.append("/" + self.token_to_string(tokens_out[i]))
        return "".join(parts)

    def get_path_list_paths(self, path_list_handle: int) -> list[str]:
        """Resolve all prim paths in a path list handle to strings."""
        num = ctypes.c_size_t(0)
        self.vtable.contents.get_num_paths_from_path_list(self.context, path_list_handle, ctypes.byref(num))
        if num.value == 0:
            return []
        paths = (_PRIMPATH * num.value)()
        retrieved = ctypes.c_size_t(0)
        self.vtable.contents.get_paths_from_path_list(
            self.context, path_list_handle, 0, num.value, paths, ctypes.byref(retrieved)
        )
        return [self.prim_path_to_string(paths[i]) for i in range(retrieved.value)]


class Bindings:
    """Wrapper for configured C library functions.

    Error Handling:
        Methods return ovrtx_result_t with a status field. On failure (status != OVRTX_API_SUCCESS),
        call get_last_error() to retrieve the error message. The error string is thread-local and
        valid until the next API call on the same thread.
    """

    def __init__(self, lib: ctypes.CDLL, lib_version: tuple):
        self._lib: ctypes.CDLL = lib
        self._lib_version: tuple = lib_version

    @property
    def library_path(self) -> Path:
        """Get the path of the loaded library."""
        return Path(self._lib._name)

    @property
    def version(self) -> tuple:
        """Runtime library version as a (major, minor, patch) tuple."""
        return self._lib_version

    def create_renderer(self, config: ovrtx_config_t) -> tuple[ovrtx_result_t, Any]:
        """Create a new renderer instance.

        Args:
            config: Renderer configuration structure.

        Returns:
            Tuple of (result, renderer_handle). Handle is None if creation failed.
        """
        renderer_handle = ctypes.POINTER(ovrtx_renderer_t)()
        result = self._lib.ovrtx_create_renderer(ctypes.byref(config), ctypes.byref(renderer_handle))
        handle = renderer_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def destroy_renderer(self, renderer_handle: Any) -> ovrtx_result_t:
        """Destroy renderer and release resources.

        Args:
            renderer_handle: Renderer handle from create_renderer, or None.

        Returns:
            Result with status.
        """
        return self._lib.ovrtx_destroy_renderer(renderer_handle)

    def attach_ovstage(self, renderer_handle: Any, stage_handle: ovstage_instance_p) -> ovrtx_result_t:
        """Attach an externally owned ovstage instance to a renderer.

        The renderer must not have stepped or already be attached. The caller
        retains ownership of the stage and must detach it before destroying
        either object. The renderer's configured attach mode determines whether
        it borrows the stage directly or uses it as a source for explicit updates.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            stage_handle: Pointer to an initialized ovstage instance. It must
                remain valid until detached.

        Returns:
            Result with status.
        """
        return self._lib.ovrtx_attach_ovstage(renderer_handle, stage_handle)

    def detach_ovstage(self, renderer_handle: Any) -> ovrtx_result_t:
        """Detach the ovstage instance currently attached to a renderer.

        The renderer returns to standalone mode with a fresh internal stage.
        Any data copied in replicate mode is discarded; ownership of the
        detached ovstage instance remains with the caller. Attaching a different
        stage after detaching is not currently supported.

        Args:
            renderer_handle: Renderer handle previously passed to attach_ovstage.

        Returns:
            Result with status.
        """
        return self._lib.ovrtx_detach_ovstage(renderer_handle)

    def update_from_stage(self, renderer_handle: Any, stage_ordinal: int) -> ovrtx_enqueue_result_t:
        """Enqueue an update from the attached ovstage at a committed ordinal.

        In borrow mode it synchronizes the renderer's scene state with committed
        population changes while attribute values remain shared with ovstage. In
        replicate mode it copies committed attribute values at or before
        ``stage_ordinal`` into the renderer's internal stage. In either mode, the
        ordinal must not exceed the attached stage's write floor.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            stage_ordinal: Committed ovstage ordinal to update through.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_update_from_stage(renderer_handle, ovstage_ordinal_t(stage_ordinal))

    def get_last_error(self) -> str:
        """Get the error string from the last failed API call on this thread.

        The error string is valid until the next API call on the same thread.

        Returns:
            Error message string, or empty string if no error.
        """
        error = self._lib.ovrtx_get_last_error()
        return str(error) if error.ptr else ""

    def get_last_op_error(self, op_id: ovrtx_op_id_t) -> str:
        """Get the error string for a specific failed operation.

        The error string is valid until the next call to wait_op on the same thread.

        Args:
            op_id: Operation ID to get error for.

        Returns:
            Error message string, or empty string if no error.
        """
        error = self._lib.ovrtx_get_last_op_error(op_id)
        return str(error) if error.ptr else ""

    def wait_op(
        self, renderer_handle: Any, op_id: ovrtx_op_id_t, timeout: ovrtx_timeout_t
    ) -> tuple[ovrtx_result_t, ovrtx_op_wait_result_t]:
        """Wait for an operation to complete.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            op_id: Non-zero operation ID to wait for.
            timeout: Timeout for the operation.

        Returns:
            Tuple of (result, wait_result).
        """
        c_wait_result = ovrtx_op_wait_result_t()
        result = self._lib.ovrtx_wait_op(renderer_handle, op_id, timeout, ctypes.byref(c_wait_result))
        return result, c_wait_result

    def query_op_status(self, renderer_handle: Any, op_id: ovrtx_op_id_t) -> tuple[ovrtx_result_t, ovrtx_op_status_t]:
        """Query progress of an operation. Must be paired with release_op_status."""
        c_status = ovrtx_op_status_t()
        result = self._lib.ovrtx_query_op_status(renderer_handle, op_id, ctypes.byref(c_status))
        return result, c_status

    def release_op_status(self, renderer_handle: Any, status: ovrtx_op_status_t) -> ovrtx_result_t:
        """Release resources from a previous query_op_status call."""
        return self._lib.ovrtx_release_op_status(renderer_handle, ctypes.byref(status))

    def open_usd_from_file(self, renderer_handle: Any, file_name: str) -> ovrtx_enqueue_result_t:
        """Open a USD file as the root layer (resets stage first).

        Args:
            renderer_handle: Renderer handle from create_renderer.
            file_name: Path to the USD file.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_open_usd_from_file(renderer_handle, ovx_string_t(file_name))

    def open_usd_from_string(self, renderer_handle: Any, root_layer_content: str) -> ovrtx_enqueue_result_t:
        """Open a USD stage from inline USDA content (resets stage first).

        Args:
            renderer_handle: Renderer handle from create_renderer.
            root_layer_content: USDA content string.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_open_usd_from_string(renderer_handle, ovx_string_t(root_layer_content))

    def add_usd_reference_from_file(
        self, renderer_handle: Any, layer_file: str, prefix_path: str
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Add a USD file as a reference at a prim path.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            layer_file: Path to the USD file.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            Tuple of (enqueue_result, usd_handle). usd_handle is returned only if the API call succeeds.
        """
        usd_handle = ovrtx_usd_handle_t()
        result = self._lib.ovrtx_add_usd_reference_from_file(
            renderer_handle, ovx_string_t(layer_file), ovx_string_t(prefix_path), ctypes.byref(usd_handle)
        )
        handle = usd_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def add_usd_reference_from_string(
        self, renderer_handle: Any, layer_content: str, prefix_path: str
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Add inline USDA content as a reference at a prim path.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            layer_content: USDA content string.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            Tuple of (enqueue_result, usd_handle). usd_handle is returned only if the API call succeeds.
        """
        usd_handle = ovrtx_usd_handle_t()
        result = self._lib.ovrtx_add_usd_reference_from_string(
            renderer_handle, ovx_string_t(layer_content), ovx_string_t(prefix_path), ctypes.byref(usd_handle)
        )
        handle = usd_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def clone_usd(
        self, renderer_handle: Any, source_path: ovx_string_t, target_paths_array: Any, num_targets: int
    ) -> ovrtx_enqueue_result_t:
        """Clone a USD subtree to one or more target paths.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            source_path: Path to the source prim to clone.
            target_paths_array: ctypes array of ovx_string_t target paths.
            num_targets: Number of target paths.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_clone_usd(renderer_handle, source_path, target_paths_array, num_targets)

    def remove_usd(self, renderer_handle: Any, usd_handle: ovrtx_usd_handle_t) -> ovrtx_enqueue_result_t:
        """Remove a previously added USD file from the stage.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            usd_handle: Handle returned by add_usd_reference_from_file or add_usd_reference_from_string.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_remove_usd(renderer_handle, usd_handle)

    def update_stage_from_usd_time(self, renderer_handle: Any, usd_time: float) -> ovrtx_enqueue_result_t:
        """Update stage attributes from USD time samples.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            usd_time: USD time code to evaluate.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_update_stage_from_usd_time(renderer_handle, usd_time)

    def reset_stage(self, renderer_handle: Any) -> ovrtx_enqueue_result_t:
        """Reset the runtime stage to empty.

        Args:
            renderer_handle: Renderer handle from create_renderer.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_reset_stage(renderer_handle)

    def step(
        self, renderer_handle: Any, render_product_set: ovrtx_render_product_set_t, delta_time: float
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Enqueue a step operation.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            render_product_set: Render product set to step.
            delta_time: Time step for simulation.

        Returns:
            Tuple of (enqueue_result, step_result_handle). Handle is None if step failed.
        """
        step_result_handle = ovrtx_step_result_handle_t()
        result = self._lib.ovrtx_step(renderer_handle, render_product_set, delta_time, ctypes.byref(step_result_handle))
        handle = step_result_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def step_with_stage(
        self,
        renderer_handle: Any,
        render_product_set: ovrtx_render_product_set_t,
        delta_time: float,
        ordinal: int,
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Enqueue a simulation step while the renderer is attached to an ovstage.

        ``ordinal`` is a committed-publication gate, not a historical snapshot
        selector: it must not exceed the stage's write floor, and the step may
        observe that publication or a later one. This low-level method does not
        update the renderer from ovstage automatically. Enqueue ``update_from_stage``
        first in either attach mode, or use high-level ``Renderer.step``, which
        performs both operations.

        Args:
            renderer_handle: Renderer handle from create_renderer. It must be
                attached to an ovstage.
            render_product_set: Render product set to step.
            delta_time: Time step for simulation.
            ordinal: Minimum committed ovstage publication required by the step.

        Returns:
            Tuple of (enqueue_result, step_result_handle). Handle is None if the
            step failed to enqueue.
        """
        step_result_handle = ovrtx_step_result_handle_t()
        result = self._lib.ovrtx_step_with_stage(
            renderer_handle,
            render_product_set,
            delta_time,
            ovstage_ordinal_t(ordinal),
            ctypes.byref(step_result_handle),
        )
        handle = step_result_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def enqueue_pick_query(self, renderer_handle: Any, desc: ovrtx_pick_query_desc_t) -> ovrtx_enqueue_result_t:
        """Enqueue a pick query for the next step that renders the given RenderProduct."""
        return self._lib.ovrtx_enqueue_pick_query(renderer_handle, ctypes.byref(desc))

    def set_selection_group_styles(
        self,
        renderer_handle: Any,
        group_ids: Any,
        styles: Any,
        count: int,
    ) -> ovrtx_enqueue_result_t:
        """Set per-group outline/fill colors for selection groups.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            group_ids: ctypes ``c_uint8`` array of length ``count``.
            styles: ctypes ``ovrtx_selection_group_style_t`` array of length ``count``,
                parallel to ``group_ids``.
            count: Number of (group_id, style) pairs.
        """
        return self._lib.ovrtx_set_selection_group_styles(renderer_handle, group_ids, styles, count)

    def set_selection_outline_group(
        self,
        renderer_handle: Any,
        prim_path_ids: Any,
        path_count: int,
        group_ids: Any,
    ) -> ovrtx_enqueue_result_t:
        """Set per-prim selection outline group ids."""
        return self._lib.ovrtx_set_selection_outline_group(renderer_handle, prim_path_ids, path_count, group_ids)

    def set_selection_outline_group_strings(
        self,
        renderer_handle: Any,
        prim_paths: Any,
        path_count: int,
        group_ids: Any,
    ) -> ovrtx_enqueue_result_t:
        """Set per-prim selection outline group ids from string prim paths."""
        return self._lib.ovrtx_set_selection_outline_group_strings(renderer_handle, prim_paths, path_count, group_ids)

    def set_pickable(
        self,
        renderer_handle: Any,
        prim_path_ids: Any,
        path_count: int,
        pickable: Any,
    ) -> ovrtx_enqueue_result_t:
        """Set per-prim viewport pickability."""
        return self._lib.ovrtx_set_pickable(renderer_handle, prim_path_ids, path_count, pickable)

    def set_pickable_strings(
        self,
        renderer_handle: Any,
        prim_paths: Any,
        path_count: int,
        pickable: Any,
    ) -> ovrtx_enqueue_result_t:
        """Set per-prim viewport pickability from string prim paths."""
        return self._lib.ovrtx_set_pickable_strings(renderer_handle, prim_paths, path_count, pickable)

    def fetch_results(
        self,
        renderer: Any,
        step_result_handle: ovrtx_step_result_handle_t,
        timeout: ovrtx_timeout_t,
    ) -> tuple[ovrtx_result_t, ovrtx_render_product_set_outputs_t]:
        """Fetch the render product set outputs (handles and render variable descriptors).

        Args:
            renderer: Renderer instance pointer
            step_result_handle: Handle from step operation (ovrtx_step_result_handle_t)
            timeout: Timeout configuration (ovrtx_timeout_t)

        Returns:
            Tuple of (result, outputs)
        """
        outputs = ovrtx_render_product_set_outputs_t()
        result = self._lib.ovrtx_fetch_results(renderer, step_result_handle, timeout, ctypes.byref(outputs))
        return result, outputs

    def destroy_results(
        self,
        renderer: Any,
        step_result_handle: ovrtx_step_result_handle_t,
    ) -> ovrtx_result_t:
        """Destroy step results and free associated resources.

        Args:
            renderer: Renderer instance pointer
            step_result_handle: Step result handle to destroy

        Returns:
            Result status
        """
        return self._lib.ovrtx_destroy_results(renderer, step_result_handle)

    def map_render_var_output(
        self,
        renderer: Any,
        output_handle: ovrtx_render_var_output_handle_t,
        map_output_description: Any,
        timeout: ovrtx_timeout_t,
    ) -> tuple[ovrtx_result_t, ovrtx_render_var_output_t]:
        rendered_output = ovrtx_render_var_output_t()
        result = self._lib.ovrtx_map_render_var_output(
            renderer,
            output_handle,
            map_output_description,
            timeout,
            ctypes.byref(rendered_output),
        )
        return result, rendered_output

    def unmap_render_var_output(
        self,
        renderer: Any,
        map_handle: ovrtx_render_var_output_map_handle_t,
        before_destroy_cuda_sync: Optional[ovrtx_cuda_sync_t] = None,
    ) -> ovrtx_result_t:
        """Unmap render variable output (low-level).

        Args:
            renderer: Renderer instance pointer
            map_handle: Map handle from rendered output (ovrtx_render_var_output_map_handle_t)
            before_destroy_cuda_sync: Optional CUDA sync to wait for before destroying/reusing
                the mapped memory. Pass None for no sync (default).

        Returns:
            Result status (ovrtx_result_t)
        """
        sync = before_destroy_cuda_sync if before_destroy_cuda_sync is not None else ovrtx_cuda_sync_t()
        return self._lib.ovrtx_unmap_render_var_output(renderer, map_handle, sync)

    def write_attribute(
        self,
        renderer: Any,
        binding_handle_or_desc: ovrtx_binding_desc_or_handle_t,
        data_array: ovrtx_input_buffer_t,
        data_access: ovrtx_data_access_t,
    ) -> ovrtx_enqueue_result_t:
        """Write attribute data (low-level).

        Args:
            renderer: Renderer instance pointer
            binding_handle_or_desc: Binding descriptor or handle
            data_array: Input buffer containing DLTensor array
            data_access: Data access mode (SYNC or ASYNC)

        Returns:
            Enqueue result with operation ID
        """
        return self._lib.ovrtx_write_attribute(
            renderer, ctypes.byref(binding_handle_or_desc), ctypes.byref(data_array), data_access
        )

    def create_attribute_binding(
        self,
        renderer: Any,
        description: ovrtx_binding_desc_t,
    ) -> tuple[ovrtx_enqueue_result_t, ovrtx_attribute_binding_handle_t]:
        """Create a persistent attribute binding handle.

        Args:
            renderer: Renderer handle
            description: Binding description

        Returns:
            Tuple of (enqueue result, binding handle)
        """
        handle = ovrtx_attribute_binding_handle_t()
        result = self._lib.ovrtx_create_attribute_binding(renderer, ctypes.byref(description), ctypes.byref(handle))
        return result, handle

    def destroy_attribute_binding(
        self,
        renderer: Any,
        binding_handle: ovrtx_attribute_binding_handle_t,
    ) -> ovrtx_enqueue_result_t:
        """Destroy a persistent attribute binding handle.

        Args:
            renderer: Renderer handle
            binding_handle: Binding handle to destroy

        Returns:
            Enqueue result with operation ID
        """
        return self._lib.ovrtx_destroy_attribute_binding(renderer, binding_handle)

    def map_attribute(
        self,
        renderer: Any,
        binding_handle_or_desc: ovrtx_binding_desc_or_handle_t,
        mapping_desc: ovrtx_mapping_desc_t,
    ) -> tuple[ovrtx_result_t, ovrtx_attribute_mapping_t]:
        """Map attribute to get direct access to RTX-internal buffer.

        Args:
            renderer: Renderer handle
            binding_handle_or_desc: Binding descriptor or handle
            mapping_desc: Mapping descriptor (device type and ID)

        Returns:
            Tuple of (result, attribute_mapping). Mapping contains map_handle and DLTensor.
        """
        mapping = ovrtx_attribute_mapping_t()
        result = self._lib.ovrtx_map_attribute(
            renderer, ctypes.byref(binding_handle_or_desc), mapping_desc, ctypes.byref(mapping)
        )
        return result, mapping

    def unmap_attribute(
        self,
        renderer: Any,
        map_handle: ovrtx_map_handle_t,
        cuda_sync: ovrtx_cuda_sync_t,
    ) -> ovrtx_enqueue_result_t:
        """Unmap attribute and apply written data to stage representation.

        Args:
            renderer: Renderer handle
            map_handle: Map handle from map_attribute
            cuda_sync: CUDA synchronization hints (optional, can be empty)

        Returns:
            Enqueue result with operation ID
        """
        return self._lib.ovrtx_unmap_attribute(renderer, map_handle, cuda_sync)

    def query_prims(
        self,
        renderer: Any,
        query_desc: ovrtx_query_desc_t,
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Enqueue a prim query operation.

        Args:
            renderer: Renderer instance pointer.
            query_desc: Query descriptor with filters and options.

        Returns:
            Tuple of (enqueue_result, query_handle). Handle is None if enqueue failed.
        """
        query_handle = ovrtx_query_handle_t()
        result = self._lib.ovrtx_query_prims(renderer, ctypes.byref(query_desc), ctypes.byref(query_handle))
        handle = query_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def fetch_query_results(
        self,
        renderer: Any,
        query_handle: ovrtx_query_handle_t,
        timeout: ovrtx_timeout_t,
    ) -> tuple[ovrtx_result_t, ovrtx_query_result_t]:
        """Fetch query results.

        Args:
            renderer: Renderer instance pointer.
            query_handle: Handle from query_prims.
            timeout: Timeout for the operation.

        Returns:
            Tuple of (result, query_result).
        """
        query_result = ovrtx_query_result_t()
        result = self._lib.ovrtx_fetch_query_results(renderer, query_handle, timeout, ctypes.byref(query_result))
        return result, query_result

    def release_query_results(
        self,
        renderer: Any,
        query_handle: ovrtx_query_handle_t,
    ) -> ovrtx_result_t:
        """Release query results and free resources.

        Args:
            renderer: Renderer instance pointer.
            query_handle: Handle from query_prims.

        Returns:
            Result status.
        """
        return self._lib.ovrtx_release_query_results(renderer, query_handle)

    def get_path_dictionary(
        self,
        renderer: Any,
    ) -> tuple[ovrtx_result_t, path_dictionary_instance_t]:
        """Get the renderer's path dictionary for handle-to-string conversion.

        Args:
            renderer: Renderer instance pointer.

        Returns:
            Tuple of (result, path_dictionary_instance).
        """
        pd = path_dictionary_instance_t()
        result = self._lib.ovrtx_get_path_dictionary(renderer, ctypes.byref(pd))
        return result, pd

    def read_attribute(
        self,
        renderer: Any,
        binding_handle_or_desc: ovrtx_binding_desc_or_handle_t,
        read_dest: Optional[ovrtx_read_dest_t] = None,
    ) -> tuple[ovrtx_enqueue_result_t, Any]:
        """Enqueue a stream-ordered attribute read.

        Args:
            renderer: Renderer instance pointer.
            binding_handle_or_desc: Binding identifying prims and attribute.
            read_dest: Optional destination tensor for scalar reads.

        Returns:
            Tuple of (enqueue_result, read_handle). Handle is None if enqueue failed.
        """
        read_handle = ovrtx_read_handle_t()
        dest_ptr = ctypes.byref(read_dest) if read_dest is not None else None
        result = self._lib.ovrtx_read_attribute(
            renderer, ctypes.byref(binding_handle_or_desc), dest_ptr, ctypes.byref(read_handle)
        )
        handle = read_handle if result.status == OVRTX_API_SUCCESS else None
        return result, handle

    def fetch_read_result(
        self,
        renderer: Any,
        read_handle: ovrtx_read_handle_t,
        timeout: ovrtx_timeout_t,
    ) -> tuple[ovrtx_result_t, ovrtx_read_output_t]:
        """Fetch results of a prior read_attribute call.

        Args:
            renderer: Renderer instance pointer.
            read_handle: Handle from read_attribute.
            timeout: Timeout for the operation.

        Returns:
            Tuple of (result, read_output).
        """
        read_output = ovrtx_read_output_t()
        result = self._lib.ovrtx_fetch_read_result(renderer, read_handle, timeout, ctypes.byref(read_output))
        return result, read_output

    def release_read_result(
        self,
        renderer: Any,
        read_handle: ovrtx_read_handle_t,
        before_destroy_cuda_sync: Optional[ovrtx_cuda_sync_t] = None,
    ) -> ovrtx_result_t:
        """Release resources associated with a prior read_attribute call.

        Safe to call whether or not ``fetch_read_result`` was invoked first.

        Args:
            renderer: Renderer instance pointer.
            read_handle: Handle returned by ``read_attribute``.
            before_destroy_cuda_sync: Optional CUDA sync.

        Returns:
            Result status.
        """
        sync = before_destroy_cuda_sync if before_destroy_cuda_sync is not None else ovrtx_cuda_sync_t()
        return self._lib.ovrtx_release_read_result(renderer, read_handle, sync)

    def reset(self, renderer_handle: Any, time: float) -> ovrtx_enqueue_result_t:
        """Reset sensor simulation history to a specific time.

        Args:
            renderer_handle: Renderer handle from create_renderer.
            time: Simulation time to reset to.

        Returns:
            Enqueue result with operation status and op_index.
        """
        return self._lib.ovrtx_reset(renderer_handle, time)


OVRTX_LIBRARY_PATH_HINT: Optional[str] = None

# Major.minor of the USD shared libraries bundled with ovrtx. An installed ``usd-core`` with a
# matching major.minor triggers a native-library collision at process initialization; other
# versions coexist safely. Update in lockstep with the bundled USD version.
_BUNDLED_USD_VERSION: tuple[int, int] = (25, 11)

# Basename of the ovrtx loader shared library. Shared with ``schema_paths.py`` so the
# import-time schema-path shim and ``_LibraryLoader`` can never disagree about which
# binary to look for (a divergence would mean schema-path registration ran against a
# different DLL than the one that later powers ``Renderer()``).
OVRTX_LOADER_LIB_NAME: str = "ovrtx-dynamic.dll" if sys.platform.startswith("win") else "libovrtx-dynamic.so"


def ovrtx_loader_candidate_dirs() -> List[Path]:
    """Ordered, unfiltered candidate directories for ``OVRTX_LOADER_LIB_NAME``.

    Used by both ``_LibraryLoader._load_library`` (the lazy path that powers
    ``Renderer()``) and ``schema_paths._load_loader_lib`` (the import-time
    schema-path shim) so the two callers can't diverge on which binary they
    target. Order is highest-precedence first; callers are responsible for
    filtering with ``_resolve_existing_dirs`` if they want the
    PermissionError-tolerant ``Path.resolve`` pass over the raw entries.

    Precedence (preserves the historical ``_LibraryLoader`` ordering, plus a
    last-resort in-tree dev fallback):
      1. ``<package_dir>/bin`` — wheel layout (``<site-packages>/ovrtx/bin``).
      2. ``LD_LIBRARY_PATH`` entries (Linux only).
      3. ``PATH`` entries.
      4. ``<package_dir>/../../bin`` — in-tree dev layout
         (``<deploy>/python/ovrtx`` paired with ``<deploy>/bin``). Last so an
         explicit ``PATH`` override always wins, but present so an
         in-tree build with the DLL only at ``<deploy>/bin`` and that
         directory absent from ``PATH`` still loads from both
         ``schema_paths`` and ``_LibraryLoader`` (preventing one path
         finding the binary while the other doesn't).

    The current working directory is intentionally **not** searched by default:
    loading a native library from a CWD an attacker can influence is a DLL/SO
    hijacking vector (arbitrary native code on import, before any ``Renderer()``
    call). Opt in explicitly by setting ``OVRTX_ALLOW_CWD_LIBRARY_SEARCH=1`` for
    example/test layouts that drop the DLL next to the script.

    Uses raw ``Path(__file__)`` — never ``.resolve()`` — so symlinks from
    a build tree to the source tree don't strand us at the source root.
    """
    package_dir = Path(__file__).parent.parent
    candidates: List[Path] = [package_dir / "bin"]
    if os.environ.get("OVRTX_ALLOW_CWD_LIBRARY_SEARCH", "") not in ("", "0"):
        try:
            candidates.append(Path.cwd())
        except OSError:
            pass

    if not sys.platform.startswith("win"):
        if ld_paths := os.environ.get("LD_LIBRARY_PATH", ""):
            candidates.extend(Path(p) for p in ld_paths.split(os.pathsep) if p)

    if path_paths := os.environ.get("PATH", ""):
        candidates.extend(Path(p) for p in path_paths.split(os.pathsep) if p)

    candidates.append(package_dir.parent.parent / "bin")
    return candidates


class _LibraryLoader:
    """Internal class to lazily load a singleton ovrtx library and create bindings for it."""

    def __init__(self):
        self._lib: Optional[ctypes.CDLL] = None
        self._lib_version: Optional[tuple] = None
        self._lib_search_paths: List[Path] = _resolve_existing_dirs(ovrtx_loader_candidate_dirs())
        self._dll_dir_cookies: List[object] = []

    def _cleanup(self):
        """Cleanup function called at interpreter exit."""
        if self._lib is not None:
            try:
                # Private compatibility hook for the static OVRTX loader. This
                # symbol is intentionally absent from the public C header.
                shutdown = getattr(self._lib, "ovrtx_shutdown_process", self._lib.ovrtx_shutdown)
                result = shutdown()
                if result.status != OVRTX_API_SUCCESS:
                    error = self._lib.ovrtx_get_last_error()
                    error_msg = str(error) if error.ptr else "Unknown error"
                    print(f"Warning: Failed to shutdown ovrtx library: {error_msg}", file=sys.stderr)
            except Exception as e:
                # During shutdown, modules may be partially torn down
                print(f"Warning: Exception during ovrtx library cleanup: {e}", file=sys.stderr)
            finally:
                self._lib = None

    def create_bindings(self, config: ovrtx_config_t) -> Bindings:
        """Get bindings wrapper, loading library lazily on first access.

        Args:
            config: Configuration for library/renderer initialization.

        Returns:
            Bindings wrapper with configured function signatures.

        Raises:
            RuntimeError: If library cannot be found or functions cannot be bound.
        """
        if self._lib is None:
            lib = None  # Initialize for exception handler
            try:
                library_path_hint = [Path(OVRTX_LIBRARY_PATH_HINT)] if OVRTX_LIBRARY_PATH_HINT else None
                lib = self._load_library(library_path_hint)

                # Version check: call ovrtx_get_version() before anything else (it works pre-initialize)
                lib.ovrtx_get_version.argtypes = [
                    ctypes.POINTER(ctypes.c_uint32),
                    ctypes.POINTER(ctypes.c_uint32),
                    ctypes.POINTER(ctypes.c_uint32),
                ]
                lib.ovrtx_get_version.restype = None
                major, minor, patch = ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32()
                lib.ovrtx_get_version(ctypes.byref(major), ctypes.byref(minor), ctypes.byref(patch))
                self._lib_version = (major.value, minor.value, patch.value)

                from .. import __version__ as ovrtx_version

                lib_ver_str = f"{major.value}.{minor.value}.{patch.value}"
                expected_prefix = f"{major.value}.{minor.value}."
                if not ovrtx_version.startswith(expected_prefix):
                    raise RuntimeError(
                        f"ovrtx version mismatch: Python bindings are {ovrtx_version} "
                        f"but loaded library is {lib_ver_str}"
                    )

                # Configure function signatures
                lib.ovrtx_initialize.argtypes = [ctypes.POINTER(ovrtx_config_t)]
                lib.ovrtx_initialize.restype = ovrtx_result_t

                lib.ovrtx_shutdown.argtypes = []
                lib.ovrtx_shutdown.restype = ovrtx_result_t

                if hasattr(lib, "ovrtx_shutdown_process"):
                    lib.ovrtx_shutdown_process.argtypes = []
                    lib.ovrtx_shutdown_process.restype = ovrtx_result_t

                lib.ovrtx_create_renderer.argtypes = [
                    ctypes.POINTER(ovrtx_config_t),
                    ctypes.POINTER(ctypes.POINTER(ovrtx_renderer_t)),
                ]
                lib.ovrtx_create_renderer.restype = ovrtx_result_t

                lib.ovrtx_destroy_renderer.argtypes = [ctypes.POINTER(ovrtx_renderer_t)]
                lib.ovrtx_destroy_renderer.restype = ovrtx_result_t

                lib.ovrtx_attach_ovstage.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovstage_instance_p,
                ]
                lib.ovrtx_attach_ovstage.restype = ovrtx_result_t

                lib.ovrtx_detach_ovstage.argtypes = [ctypes.POINTER(ovrtx_renderer_t)]
                lib.ovrtx_detach_ovstage.restype = ovrtx_result_t

                lib.ovrtx_update_from_stage.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovstage_ordinal_t,
                ]
                lib.ovrtx_update_from_stage.restype = ovrtx_enqueue_result_t

                lib.ovrtx_get_last_error.argtypes = []
                lib.ovrtx_get_last_error.restype = ovx_string_t

                lib.ovrtx_get_last_op_error.argtypes = [ovrtx_op_id_t]
                lib.ovrtx_get_last_op_error.restype = ovx_string_t

                lib.ovrtx_wait_op.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_op_id_t,
                    ovrtx_timeout_t,
                    ctypes.POINTER(ovrtx_op_wait_result_t),
                ]
                lib.ovrtx_wait_op.restype = ovrtx_result_t

                lib.ovrtx_query_op_status.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_op_id_t,
                    ctypes.POINTER(ovrtx_op_status_t),
                ]
                lib.ovrtx_query_op_status.restype = ovrtx_result_t

                lib.ovrtx_release_op_status.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_op_status_t),
                ]
                lib.ovrtx_release_op_status.restype = ovrtx_result_t

                lib.ovrtx_reset.argtypes = [ctypes.POINTER(ovrtx_renderer_t), ctypes.c_double]
                lib.ovrtx_reset.restype = ovrtx_enqueue_result_t

                lib.ovrtx_open_usd_from_file.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovx_string_t,
                ]
                lib.ovrtx_open_usd_from_file.restype = ovrtx_enqueue_result_t

                lib.ovrtx_open_usd_from_string.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovx_string_t,
                ]
                lib.ovrtx_open_usd_from_string.restype = ovrtx_enqueue_result_t

                lib.ovrtx_add_usd_reference_from_file.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovx_string_t,
                    ovx_string_t,
                    ctypes.POINTER(ovrtx_usd_handle_t),
                ]
                lib.ovrtx_add_usd_reference_from_file.restype = ovrtx_enqueue_result_t

                lib.ovrtx_add_usd_reference_from_string.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovx_string_t,
                    ovx_string_t,
                    ctypes.POINTER(ovrtx_usd_handle_t),
                ]
                lib.ovrtx_add_usd_reference_from_string.restype = ovrtx_enqueue_result_t

                lib.ovrtx_reset_stage.argtypes = [ctypes.POINTER(ovrtx_renderer_t)]
                lib.ovrtx_reset_stage.restype = ovrtx_enqueue_result_t

                lib.ovrtx_remove_usd.argtypes = [ctypes.POINTER(ovrtx_renderer_t), ovrtx_usd_handle_t]
                lib.ovrtx_remove_usd.restype = ovrtx_enqueue_result_t

                lib.ovrtx_update_stage_from_usd_time.argtypes = [ctypes.POINTER(ovrtx_renderer_t), ctypes.c_double]
                lib.ovrtx_update_stage_from_usd_time.restype = ovrtx_enqueue_result_t

                lib.ovrtx_clone_usd.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovx_string_t,
                    ctypes.POINTER(ovx_string_t),
                    ctypes.c_size_t,
                ]
                lib.ovrtx_clone_usd.restype = ovrtx_enqueue_result_t

                lib.ovrtx_step.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_render_product_set_t,
                    ctypes.c_double,
                    ctypes.POINTER(ovrtx_step_result_handle_t),
                ]
                lib.ovrtx_step.restype = ovrtx_enqueue_result_t

                lib.ovrtx_step_with_stage.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_render_product_set_t,
                    ctypes.c_double,
                    ovstage_ordinal_t,
                    ctypes.POINTER(ovrtx_step_result_handle_t),
                ]
                lib.ovrtx_step_with_stage.restype = ovrtx_enqueue_result_t

                lib.ovrtx_enqueue_pick_query.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_pick_query_desc_t),
                ]
                lib.ovrtx_enqueue_pick_query.restype = ovrtx_enqueue_result_t

                lib.ovrtx_set_selection_group_styles.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.POINTER(ovrtx_selection_group_style_t),
                    ctypes.c_size_t,
                ]
                lib.ovrtx_set_selection_group_styles.restype = ovrtx_enqueue_result_t

                lib.ovrtx_set_selection_outline_group.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(_PRIMPATH),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_uint8),
                ]
                lib.ovrtx_set_selection_outline_group.restype = ovrtx_enqueue_result_t

                lib.ovrtx_set_selection_outline_group_strings.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovx_string_t),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_uint8),
                ]
                lib.ovrtx_set_selection_outline_group_strings.restype = ovrtx_enqueue_result_t

                lib.ovrtx_set_pickable.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(_PRIMPATH),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_bool),
                ]
                lib.ovrtx_set_pickable.restype = ovrtx_enqueue_result_t

                lib.ovrtx_set_pickable_strings.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovx_string_t),
                    ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_bool),
                ]
                lib.ovrtx_set_pickable_strings.restype = ovrtx_enqueue_result_t

                lib.ovrtx_fetch_results.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_step_result_handle_t,
                    ovrtx_timeout_t,
                    ctypes.POINTER(ovrtx_render_product_set_outputs_t),
                ]
                lib.ovrtx_fetch_results.restype = ovrtx_result_t

                lib.ovrtx_destroy_results.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_step_result_handle_t,
                ]
                lib.ovrtx_destroy_results.restype = ovrtx_result_t

                lib.ovrtx_write_attribute.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_binding_desc_or_handle_t),
                    ctypes.POINTER(ovrtx_input_buffer_t),
                    ovrtx_data_access_t,
                ]
                lib.ovrtx_write_attribute.restype = ovrtx_enqueue_result_t

                lib.ovrtx_create_attribute_binding.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_binding_desc_t),
                    ctypes.POINTER(ovrtx_attribute_binding_handle_t),
                ]
                lib.ovrtx_create_attribute_binding.restype = ovrtx_enqueue_result_t

                lib.ovrtx_destroy_attribute_binding.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_attribute_binding_handle_t,
                ]
                lib.ovrtx_destroy_attribute_binding.restype = ovrtx_enqueue_result_t

                lib.ovrtx_map_attribute.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_binding_desc_or_handle_t),
                    ovrtx_mapping_desc_t,
                    ctypes.POINTER(ovrtx_attribute_mapping_t),
                ]
                lib.ovrtx_map_attribute.restype = ovrtx_result_t

                lib.ovrtx_unmap_attribute.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_map_handle_t,
                    ovrtx_cuda_sync_t,
                ]
                lib.ovrtx_unmap_attribute.restype = ovrtx_enqueue_result_t

                lib.ovrtx_query_prims.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_query_desc_t),
                    ctypes.POINTER(ovrtx_query_handle_t),
                ]
                lib.ovrtx_query_prims.restype = ovrtx_enqueue_result_t

                lib.ovrtx_fetch_query_results.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_query_handle_t,
                    ovrtx_timeout_t,
                    ctypes.POINTER(ovrtx_query_result_t),
                ]
                lib.ovrtx_fetch_query_results.restype = ovrtx_result_t

                lib.ovrtx_release_query_results.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_query_handle_t,
                ]
                lib.ovrtx_release_query_results.restype = ovrtx_result_t

                lib.ovrtx_get_path_dictionary.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(path_dictionary_instance_t),
                ]
                lib.ovrtx_get_path_dictionary.restype = ovrtx_result_t

                lib.ovrtx_read_attribute.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.POINTER(ovrtx_binding_desc_or_handle_t),
                    ctypes.POINTER(ovrtx_read_dest_t),
                    ctypes.POINTER(ovrtx_read_handle_t),
                ]
                lib.ovrtx_read_attribute.restype = ovrtx_enqueue_result_t

                lib.ovrtx_fetch_read_result.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_read_handle_t,
                    ovrtx_timeout_t,
                    ctypes.POINTER(ovrtx_read_output_t),
                ]
                lib.ovrtx_fetch_read_result.restype = ovrtx_result_t

                lib.ovrtx_release_read_result.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ovrtx_read_handle_t,
                    ovrtx_cuda_sync_t,
                ]
                lib.ovrtx_release_read_result.restype = ovrtx_result_t

                lib.ovrtx_map_render_var_output.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.c_uint64,  # ovrtx_render_var_output_handle_t
                    ctypes.c_void_p,  # ovrtx_map_output_description_t* (specifies CPU or CUDA mapping)
                    ovrtx_timeout_t,  # timeout
                    ctypes.POINTER(ovrtx_render_var_output_t),  # out_render_var_output
                ]
                lib.ovrtx_map_render_var_output.restype = ovrtx_result_t

                lib.ovrtx_unmap_render_var_output.argtypes = [
                    ctypes.POINTER(ovrtx_renderer_t),
                    ctypes.c_uint64,  # ovrtx_render_var_output_map_handle_t
                    ovrtx_cuda_sync_t,  # before_destroy_cuda_sync
                ]
                lib.ovrtx_unmap_render_var_output.restype = ovrtx_result_t

                result = lib.ovrtx_initialize(ctypes.byref(config))
                if result.status != OVRTX_API_SUCCESS:
                    error = lib.ovrtx_get_last_error()
                    error_msg = str(error) if error.ptr else "Unknown error"
                    raise RuntimeError(f"Failed to initialize ovrtx library: {error_msg}")

                # Make sure to properly shutdown the library when the interpreter exits (__del__ is unreliable)
                import atexit

                self._lib = lib
                atexit.register(self._cleanup)

            except Exception as exc:
                # Shutdown if initialize succeeded but subsequent setup failed.
                if self._lib is not None:
                    self._lib.ovrtx_shutdown()
                    self._lib = None
                if isinstance(exc, AttributeError):
                    raise RuntimeError(
                        f"Function not found in {lib._name}. Binary version may not match Python bindings."
                    ) from exc
                raise

        return Bindings(self._lib, self._lib_version)

    def _add_dll_directories(self, lib_dir: Path) -> None:
        """Register package DLL directories for Windows dependency resolution."""
        if not sys.platform.startswith("win"):
            return
        for d in (lib_dir, lib_dir / "plugins"):
            try:
                if d.is_dir():
                    self._dll_dir_cookies.append(os.add_dll_directory(str(d)))
            except OSError:
                continue

    def _load_library(self, extra_paths: Optional[List[Path]] = None) -> ctypes.CDLL:
        """Load the library from search paths or raise an exception."""
        search_paths = _resolve_existing_dirs(extra_paths) if extra_paths else []
        search_paths.extend(self._lib_search_paths)

        # Try loading from each path
        lib_paths = [p / OVRTX_LOADER_LIB_NAME for p in search_paths]
        last_error = None
        for lib_path in lib_paths:
            if lib_path.exists() and lib_path.is_file():
                try:
                    # Windows only: set OMNI_PLUGINS_BASE_PATH and OMNI_USD_PLUGINS_BASE_PATH if not
                    # already set. They're used to configure PATH, DLL directories and PXR_PLUGINPATH_NAME
                    # for USD plugin loading. The library's parent directory is the natural base path.
                    # Linux uses LD_LIBRARY_PATH/RPATH and doesn't need this workaround.
                    if sys.platform.startswith("win"):
                        if "OMNI_PLUGINS_BASE_PATH" not in os.environ:
                            os.environ["OMNI_PLUGINS_BASE_PATH"] = str(lib_path.parent)
                        if "OMNI_USD_PLUGINS_BASE_PATH" not in os.environ:
                            os.environ["OMNI_USD_PLUGINS_BASE_PATH"] = str(lib_path.parent)

                    self._add_dll_directories(lib_path.parent)
                    lib = ctypes.CDLL(str(lib_path))
                    return lib
                except Exception as e:
                    last_error = e
                    continue

        # Throw with verbose message if we failed to load from any path
        paths_str = "\n  ".join(str(p) for p in lib_paths)
        error_msg = f"Failed to load {OVRTX_LOADER_LIB_NAME}. Tried:\n  {paths_str}"
        if last_error:
            error_msg += f"\nLast error: {last_error}"
        raise RuntimeError(error_msg)

    def register_schema_paths(self) -> None:
        """Load the loader DLL transiently and call ovrtx_register_schema_paths(NULL).

        Called from ``ovrtx/__init__.py`` so that ``import ovrtx; import ovphysx``
        publishes both subsystems' USD plugin paths to PXR_PLUGINPATH_NAME before USD's
        plug registry is consulted. The C side is idempotent for matching effective
        roots (see ``ovrtx.h``) and Python does not expose a custom binary-package-root
        config key, so the eager root and the lazy ``create_bindings`` root always agree.

        The loaded handle goes out of scope on return; ``create_bindings`` reloads the
        DLL when the user actually constructs a Renderer. ``_load_library`` already
        sets ``OMNI_USD_PLUGINS_BASE_PATH`` on Windows before the load, which the C
        ``resolveEffectivePluginRoot`` reads as the highest-precedence root.
        """
        library_path_hint = [Path(OVRTX_LIBRARY_PATH_HINT)] if OVRTX_LIBRARY_PATH_HINT else None
        lib = self._load_library(library_path_hint)
        lib.ovrtx_register_schema_paths.argtypes = [ctypes.POINTER(ovrtx_config_t)]
        lib.ovrtx_register_schema_paths.restype = ovrtx_result_t
        lib.ovrtx_get_last_error.argtypes = []
        lib.ovrtx_get_last_error.restype = ovx_string_t
        result = lib.ovrtx_register_schema_paths(None)
        if result.status != OVRTX_API_SUCCESS:
            error = lib.ovrtx_get_last_error()
            error_msg = str(error) if error.ptr else "Unknown error"
            raise RuntimeError(f"Failed to register ovrtx USD schema/plugin paths: {error_msg}")

    @property
    def is_loaded(self) -> bool:
        """Check if library is already loaded."""
        return self._lib is not None


_ovrtx_loader = _LibraryLoader()
