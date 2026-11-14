# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution without an express license agreement is prohibited.

"""Native data-provider and structured-accessor ABI. Callbacks use the C calling convention."""

import ctypes as ct
from enum import IntEnum, IntFlag

from .bindings import (
    ovrtx_attribute_type_t,
    ovrtx_data_array_lease_id_t,
    ovrtx_data_provider_id_t,
    ovx_primpath_t,
    ovx_string_t,
    ovx_token_t,
    path_dictionary_instance_t,
)
from .dlpack import DLDevice, DLTensor


class DataStatus(IntEnum):
    """Shared provider/accessor results; BUSY leaves registration or accessor ownership intact."""

    OK = 0
    NOT_HANDLED = 1
    NOT_FOUND = 2
    UNSUPPORTED = 3
    INVALID_ARGUMENT = 4
    ACCESS_DENIED = 5
    IO_ERROR = 6
    STALE = 7
    CANCELLED = 8
    BUSY = 9
    INVALID_STATE = 10
    INVALID_HANDLE = 11
    OUT_OF_RANGE = 12


class DataSubmit(IntEnum):
    """ACCEPTED owes one completion; RETRY and REJECTED owe none."""

    ACCEPTED = 0
    RETRY = 1
    REJECTED = 2


class DataKind(IntEnum):
    """Representation requested from a provider."""

    BYTES = 1
    STRUCTURED = 2


class DataRangeStrategy(IntEnum):
    """Range-read cost advertised at pin completion, before payload I/O."""

    UNKNOWN = 0
    NATIVE = 1
    CACHED_READ_THROUGH = 2
    MATERIALIZE_ONLY = 3
    UNSUPPORTED = 4


class DataHint(IntFlag):
    """Advisory access intent; never authorizes payload reads during pinning."""

    WHOLE_OBJECT = 1


class DataPinFlag(IntFlag):
    """Mutually exclusive pin tracking requests; zero requests no tracking."""

    WATCH_CHANGES = 1
    REQUIRE_CHANGE_TRACKING = 2


class ovrtx_data_request_options_t(ct.Structure):
    """Request hints, timeout, priority and pin-only change-tracking flags."""

    _fields_ = [
        ("struct_size", ct.c_size_t),
        ("hints", ct.c_uint64),
        ("timeout_ns", ct.c_uint64),
        ("priority", ct.c_int32),
        ("pin_flags", ct.c_uint64),
    ]


class ovrtx_data_byte_view_t(ct.Structure):
    """Immutable CPU bytes retained by a non-null lease, including empty views."""

    _fields_ = [("struct_size", ct.c_size_t), ("data", ct.c_void_p), ("size", ct.c_uint64), ("lease", ct.c_void_p)]


class AccessorCapability(IntFlag):
    """Array access supported by a structured provider."""

    CPU_ARRAYS = 1
    GPU_ARRAYS = 2


DATA_SIZE_UNKNOWN = (1 << 64) - 1
DATA_PROVIDER_ABI_VERSION = 5
ACCESSOR_ABI_VERSION = 4


class ovrtx_data_prim_info_t(ct.Structure):
    """Prim metadata; type_name is a token in the supplied dictionary."""

    _fields_ = [("type_name", ovx_token_t)]


class ovrtx_data_attribute_info_t(ct.Structure):
    """Packed scalar/array layout, restricted to the footprint in ovrtx_data_provider.h.

    NONE supports uint8/32/64, int64 and float32/64 with positive dtype.lanes.
    TOKEN_ID uses uint64 with one lane. Other types/semantics return UNSUPPORTED.
    """

    _fields_ = [
        ("type", ovrtx_attribute_type_t),
        ("count", ct.c_uint64),
    ]


class ovrtx_data_cpu_array_t(ct.Structure):
    """Immutable CPU storage borrowed until its lease is released."""

    _fields_ = [
        ("lease", ovrtx_data_array_lease_id_t),
        ("data", ct.c_void_p),
        ("byte_size", ct.c_uint64),
        ("layout", ovrtx_data_attribute_info_t),
    ]


class ovrtx_data_gpu_access_desc_t(ct.Structure):
    """Requested CUDA device; acquisition never migrates data."""

    _fields_ = [("device", DLDevice)]


class ovstage_cuda_sync_t(ct.Structure):
    """OVStage producer readiness: stream 0=none, 1=default, >1=CUDA stream; wait_event 0=none.

    Consumers synchronize both nonzero fields before accessing the borrowed tensor.
    Provider-owned stream/event objects remain valid through lease release.
    """

    _fields_ = [("stream", ct.c_size_t), ("wait_event", ct.c_size_t)]


class ovrtx_data_gpu_array_t(ct.Structure):
    """Borrowed CUDA tensor plus producer readiness, following OVStage's handoff contract.

    The tensor is packed, ndim=1, shape=[count], dtype matching get_attribute_info.
    Synchronize cuda_sync before access and finish device work before release.
    Data, shape, strides and sync objects remain provider-owned through the lease.
    """

    _fields_ = [("lease", ovrtx_data_array_lease_id_t), ("tensor", DLTensor), ("cuda_sync", ovstage_cuda_sync_t)]


class ovrtx_data_accessor_vtable_t(ct.Structure):
    """No-I/O accessor methods returning DataStatus; CPU/GPU callback pairs are independently optional."""

    _fields_ = [
        ("struct_size", ct.c_uint32),
        ("abi_version", ct.c_uint32),
        (
            "get_roots",
            ct.CFUNCTYPE(
                ct.c_int, ct.c_void_p, ct.c_uint64, ct.POINTER(ovx_primpath_t), ct.c_uint64, ct.POINTER(ct.c_uint64)
            ),
        ),
        (
            "get_children",
            ct.CFUNCTYPE(
                ct.c_int,
                ct.c_void_p,
                ovx_primpath_t,
                ct.c_uint64,
                ct.POINTER(ovx_primpath_t),
                ct.c_uint64,
                ct.POINTER(ct.c_uint64),
            ),
        ),
        (
            "get_attributes",
            ct.CFUNCTYPE(
                ct.c_int,
                ct.c_void_p,
                ovx_primpath_t,
                ct.c_uint64,
                ct.POINTER(ovx_token_t),
                ct.c_uint64,
                ct.POINTER(ct.c_uint64),
            ),
        ),
        ("get_prim_info", ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ovx_primpath_t, ct.POINTER(ovrtx_data_prim_info_t))),
        (
            "get_attribute_info",
            ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ovx_primpath_t, ovx_token_t, ct.POINTER(ovrtx_data_attribute_info_t)),
        ),
        (
            "get_scalar_attribute",
            ct.CFUNCTYPE(
                ct.c_int, ct.c_void_p, ovx_primpath_t, ovx_token_t, ct.c_void_p, ct.c_uint64, ct.POINTER(ct.c_uint64)
            ),
        ),
        (
            "acquire_array_cpu",
            ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ovx_primpath_t, ovx_token_t, ct.POINTER(ovrtx_data_cpu_array_t)),
        ),
        ("release_array_cpu", ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ovrtx_data_array_lease_id_t)),
        (
            "acquire_array_gpu",
            ct.CFUNCTYPE(
                ct.c_int,
                ct.c_void_p,
                ovx_primpath_t,
                ovx_token_t,
                ct.POINTER(ovrtx_data_gpu_access_desc_t),
                ct.POINTER(ovrtx_data_gpu_array_t),
            ),
        ),
        ("release_array_gpu", ct.CFUNCTYPE(ct.c_int, ct.c_void_p, ovrtx_data_array_lease_id_t)),
    ]


class ovrtx_data_accessor_t(ct.Structure):
    """Provider-owned vtable and context; valid until successful close_accessor."""

    _fields_ = [("vtable", ct.POINTER(ovrtx_data_accessor_vtable_t)), ("context", ct.c_void_p)]


class ovrtx_data_resource_handle_t(ct.Structure):
    """Opaque provider-owned pin state; valid until unpin."""

    pass


class ovrtx_data_resource_t(ct.Structure):
    """Pin result. Strings are callback-scoped; retain the handle until unpin."""

    _fields_ = [
        ("struct_size", ct.c_size_t),
        ("handle", ct.POINTER(ovrtx_data_resource_handle_t)),
        ("identifier", ovx_string_t),
        ("revision", ovx_string_t),
        ("content_hash", ovx_string_t),
        ("kind", ct.c_int),
        ("byte_size", ct.c_uint64),
        ("schema", ovx_string_t),
        ("schema_version", ct.c_uint32),
        ("range_strategy", ct.c_int),
        ("change_tracking_enabled", ct.c_bool),
        ("modified_time_ns", ct.c_int64),
        ("has_modified_time", ct.c_bool),
    ]


class ovrtx_data_provider_context_t(ct.Structure):
    """Opaque provider implementation state; cast an owned native pointer to this type."""

    pass


# Completion callbacks receive the unchanged caller-owned user_data as their first argument.
PinDone = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_int, ct.POINTER(ovrtx_data_resource_t), ovx_string_t)
ReadDone = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_int, ct.c_uint64, ovx_string_t)
AccessorDone = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_int, ct.POINTER(ovrtx_data_accessor_t), ovx_string_t)
MapDone = ct.CFUNCTYPE(None, ct.c_void_p, ct.c_int, ct.POINTER(ovrtx_data_byte_view_t), ovx_string_t)
PinAsync = ct.CFUNCTYPE(
    ct.c_int,
    ct.POINTER(ovrtx_data_provider_context_t),
    ct.c_void_p,
    ct.POINTER(ovrtx_data_resource_handle_t),
    ovx_string_t,
    ct.c_int,
    ct.POINTER(ovrtx_data_request_options_t),
    PinDone,
    ct.c_void_p,  # Caller-owned user_data passed unchanged to done.
)
Unpin = ct.CFUNCTYPE(None, ct.POINTER(ovrtx_data_provider_context_t), ct.POINTER(ovrtx_data_resource_handle_t))
ReadAsync = ct.CFUNCTYPE(
    ct.c_int,
    ct.POINTER(ovrtx_data_provider_context_t),
    ct.c_void_p,
    ct.POINTER(ovrtx_data_resource_handle_t),
    ct.c_uint64,
    ct.c_void_p,
    ct.c_uint64,
    ct.POINTER(ovrtx_data_request_options_t),
    ReadDone,
    ct.c_void_p,  # Caller-owned user_data passed unchanged to done.
)
OpenAccessorAsync = ct.CFUNCTYPE(
    ct.c_int,
    ct.POINTER(ovrtx_data_provider_context_t),
    ct.c_void_p,
    ct.POINTER(ovrtx_data_resource_handle_t),
    ct.c_uint64,  # Provider-defined offset selector; not necessarily bytes.
    ct.c_uint64,  # Provider-defined size selector; forwarded unchanged.
    ct.POINTER(path_dictionary_instance_t),
    ct.POINTER(ovrtx_data_request_options_t),
    AccessorDone,
    ct.c_void_p,  # Caller-owned user_data passed unchanged to done.
)
CloseAccessor = ct.CFUNCTYPE(ct.c_int, ct.POINTER(ovrtx_data_provider_context_t), ct.POINTER(ovrtx_data_accessor_t))
Cancel = ct.CFUNCTYPE(None, ct.POINTER(ovrtx_data_provider_context_t), ct.c_void_p)
MapAsync = ct.CFUNCTYPE(
    ct.c_int,
    ct.POINTER(ovrtx_data_provider_context_t),
    ct.c_void_p,
    ct.POINTER(ovrtx_data_resource_handle_t),
    ct.c_uint64,
    ct.c_uint64,
    ct.POINTER(ovrtx_data_request_options_t),
    MapDone,
    ct.c_void_p,  # Caller-owned user_data passed unchanged to done.
)
ReleaseMap = ct.CFUNCTYPE(
    None, ct.POINTER(ovrtx_data_provider_context_t), ct.POINTER(ovrtx_data_resource_handle_t), ct.c_void_p
)


class ovrtx_data_provider_desc_t(ct.Structure):
    """Registration descriptor matching ovrtx_data_provider.h."""

    _fields_ = [
        ("struct_size", ct.c_size_t),
        ("abi_version", ct.c_uint32),
        ("namespace_key", ovx_string_t),
        ("uri_scheme", ovx_string_t),
        ("priority", ct.c_int32),
        ("accessor_capabilities", ct.c_uint64),
    ]


class ovrtx_data_provider_vtable_t(ct.Structure):
    """Immutable provider operation table, separate from registration metadata."""

    _fields_ = [
        ("struct_size", ct.c_size_t),
        ("abi_version", ct.c_uint32),
        ("pin_async", PinAsync),
        ("unpin", Unpin),
        ("read_async", ReadAsync),
        ("open_accessor_async", OpenAccessorAsync),
        ("close_accessor", CloseAccessor),
        ("cancel", Cancel),
        ("map_async", MapAsync),
        ("release_map", ReleaseMap),
    ]


class ovrtx_data_provider_t(ct.Structure):
    """Provider instance; its vtable and typed context outlive the registration."""

    _fields_ = [
        ("vtable", ct.POINTER(ovrtx_data_provider_vtable_t)),
        ("context", ct.POINTER(ovrtx_data_provider_context_t)),
    ]


def configure_provider_functions(lib: ct.CDLL) -> None:
    """Bind registration functions before publishing an initialized library."""
    lib.ovrtx_register_data_provider.argtypes = [
        ct.POINTER(ovrtx_data_provider_desc_t),
        ct.POINTER(ovrtx_data_provider_t),
        ct.POINTER(ovrtx_data_provider_id_t),
    ]
    lib.ovrtx_register_data_provider.restype = ct.c_int
    lib.ovrtx_unregister_data_provider.argtypes = [ovrtx_data_provider_id_t]
    lib.ovrtx_unregister_data_provider.restype = ct.c_int
    lib.ovrtx_data_notify_changed.argtypes = [ovrtx_data_provider_id_t, ct.POINTER(ovx_string_t), ct.c_uint64]
    lib.ovrtx_data_notify_changed.restype = ct.c_int
