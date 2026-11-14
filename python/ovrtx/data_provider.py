# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution without an express license agreement is prohibited.

"""Process-wide data-provider registration and native callback types.

Callbacks follow ovrtx_data_provider.h, including its asynchronous lifetime rules.
Use the exported ctypes callback constructors for Python or native callbacks. Python
callbacks must catch exceptions and translate them to operation results; exceptions
cannot cross a C callback boundary. Accepted operations complete exactly once.
The final ``user_data`` argument is caller-owned, per-operation context for ``done``;
pass it unchanged as ``done(user_data, status, result, error)``. It is separate from
provider context and resource handles. Providers must not dereference/free it or
use it after calling ``done``. Retain ``done``/``user_data`` for accepted work until
completion, including cancellation; retain neither after returning RETRY/REJECTED.

Registration retains callback objects and ``keepalive`` until successful removal
or native shutdown. Pin metadata and error strings need survive only their completion callback.
Pins, byte leases, read destinations and accessor storage retain their documented
native lifetimes. ``options.contents.pin_flags`` requests optional WATCH_CHANGES or
REQUIRE_CHANGE_TRACKING; a null options pointer requests neither. Report enabled
tracking in ``resource.change_tracking_enabled``. Optional tracking may be declined;
required tracking must fail with UNSUPPORTED when unavailable. Establish monitoring
with snapshot selection and retain it until unpin, without changing pinned bytes.
Pin results may optionally set ``has_modified_time`` and ``modified_time_ns``
(nanoseconds since the Unix epoch). Zero and negative timestamps are valid; false
means unavailable. The value stays fixed for the pin and is descriptive metadata,
not content identity or authorization for timestamp-based cache validation.
Package members report their containing source's timestamp; virtual aggregates
without a meaningful single source leave it unavailable.
Credential rotation is provider-internal, without re-registration.
"""

import ctypes as ct
import operator
import threading
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from ._src import bindings
from ._src.provider_bindings import (
    ACCESSOR_ABI_VERSION,
    DATA_PROVIDER_ABI_VERSION,
    DATA_SIZE_UNKNOWN,
    AccessorCapability,
    AccessorDone,
    Cancel,
    CloseAccessor,
    DataHint,
    DataKind,
    DataPinFlag,
    DataRangeStrategy,
    DataStatus,
    DataSubmit,
    MapAsync,
    MapDone,
    OpenAccessorAsync,
    PinAsync,
    PinDone,
    ReadAsync,
    ReadDone,
    ReleaseMap,
    Unpin,
    ovrtx_attribute_type_t,
    ovrtx_data_accessor_t,
    ovrtx_data_accessor_vtable_t,
    ovrtx_data_attribute_info_t,
    ovrtx_data_byte_view_t,
    ovrtx_data_cpu_array_t,
    ovrtx_data_gpu_access_desc_t,
    ovrtx_data_gpu_array_t,
    ovrtx_data_prim_info_t,
    ovrtx_data_provider_context_t,
    ovrtx_data_provider_desc_t,
    ovrtx_data_provider_t,
    ovrtx_data_provider_vtable_t,
    ovrtx_data_request_options_t,
    ovrtx_data_resource_handle_t,
    ovrtx_data_resource_t,
    ovstage_cuda_sync_t,
    ovx_string_t,
)
from ._src.renderer import Renderer
from ._src.types import RendererConfig
from .handles import DataProviderId

__all__ = [
    "ACCESSOR_ABI_VERSION",
    "AccessorCapability",
    "AccessorDone",
    "Cancel",
    "CloseAccessor",
    "DATA_PROVIDER_ABI_VERSION",
    "DATA_SIZE_UNKNOWN",
    "DataHint",
    "DataPinFlag",
    "DataKind",
    "DataProvider",
    "DataProviderDescriptor",
    "DataProviderRegistration",
    "DataProviderVTable",
    "DataRangeStrategy",
    "DataStatus",
    "DataSubmit",
    "MapAsync",
    "MapDone",
    "OpenAccessorAsync",
    "PinAsync",
    "PinDone",
    "ReadAsync",
    "ReadDone",
    "ReleaseMap",
    "Unpin",
    "ovrtx_attribute_type_t",
    "ovrtx_data_accessor_t",
    "ovrtx_data_accessor_vtable_t",
    "ovrtx_data_attribute_info_t",
    "ovrtx_data_byte_view_t",
    "ovrtx_data_cpu_array_t",
    "ovrtx_data_gpu_access_desc_t",
    "ovrtx_data_gpu_array_t",
    "ovrtx_data_prim_info_t",
    "ovrtx_data_provider_context_t",
    "ovrtx_data_provider_desc_t",
    "ovrtx_data_provider_t",
    "ovrtx_data_provider_vtable_t",
    "ovrtx_data_request_options_t",
    "ovrtx_data_resource_handle_t",
    "ovrtx_data_resource_t",
    "ovstage_cuda_sync_t",
    "ovx_string_t",
    "register_data_provider",
]


@dataclass(frozen=True)
class DataProviderDescriptor:
    """Registration identity and routing, separate from implementation callbacks.

    ``namespace_key`` separates cache and authorization domains. ``uri_scheme``
    routes root references (without a colon); empty accepts any root. Matching
    explicit schemes precede catch-alls; priority applies within each group.
    CPU_ARRAYS and GPU_ARRAYS are independently optional: each advertised capability
    requires its acquire/release pair on every accessor, and unadvertised pairs
    must be null. Zero capabilities also supports scalar-only structured accessors.
    """

    namespace_key: str
    uri_scheme: str = ""
    priority: int = 0
    accessor_capabilities: AccessorCapability = AccessorCapability(0)


@dataclass(frozen=True)
class DataProviderVTable:
    """Provider callback definitions, reusable across instances.

    Provide read_async for bytes and both accessor callbacks for structured data.
    open_accessor_async takes provider-defined offset/size selectors after the
    resource handle; they need not describe bytes. Each call independently loads
    or prepares selected data and returns its own accessor, allowing concurrent
    opens on one pin. Accessor methods traverse prepared data without I/O, and
    each accessor owns its leases and close. Accessor methods and close return
    DataStatus; close returns BUSY while leases exist. Supply map_async/release_map together.
    Callbacks receive an ovrtx_data_provider_context_t pointer as their first argument.
    Use the exported ctypes callback constructors; never throw across the C boundary.
    """

    pin_async: Any
    unpin: Any
    cancel: Any
    read_async: Any = None
    open_accessor_async: Any = None
    close_accessor: Any = None
    map_async: Any = None
    release_map: Any = None


@dataclass(frozen=True)
class DataProvider:
    """Provider implementation and typed context, retained until removal or shutdown.

    ``context`` is a ctypes pointer to ovrtx_data_provider_context_t, or None for a
    stateless provider. ``keepalive`` retains its owner, native library or other state
    not owned by the callback objects. Each registration retains its native vtable.
    Do not call registration, unregister, or renderer teardown from a callback.
    """

    vtable: DataProviderVTable
    context: Optional[ct.POINTER(ovrtx_data_provider_context_t)] = None
    keepalive: Any = None


_registrations: dict[DataProviderId, "DataProviderRegistration"] = {}
_registration_lock = threading.RLock()


class DataProviderRegistration:
    """An explicit registration, retained even if the caller drops this object.

    Call unregister after consumers retire. BUSY leaves registration and its
    Python references intact; garbage collection never implicitly unregisters.
    """

    def __init__(
        self,
        provider_id: DataProviderId,
        descriptor: DataProviderDescriptor,
        provider: DataProvider,
        native: ovrtx_data_provider_t,
        lib,
    ):
        self._id = DataProviderId._require(provider_id, "provider_id")
        self._descriptor = descriptor
        self._provider = provider
        self._native = native
        self._lib = lib
        self._active = True

    @property
    def provider_id(self) -> DataProviderId:
        """Nonzero native registration identifier; never reused in the process."""
        return self._id

    @property
    def active(self) -> bool:
        """Whether this registration has not yet been removed or shut down."""
        with _registration_lock:
            return self._active

    def notify_changed(self, identifiers: Sequence[str]) -> DataStatus:
        """Notify a batch of canonical resources after publishing replacement revisions.

        Duplicate identifiers and members covered by an outer package are coalesced
        only for well-formed USDZ bracket paths, including nested packages. Other
        brackets in opaque identifiers do not imply containment.
        An empty sequence is a no-op for a live registration. The entire batch is
        validated before delivery; it does not establish a cross-resource snapshot.
        Existing pins stay immutable. Currently only MDL listens; its reloads are
        asynchronous. Subscriber callbacks run synchronously on the calling thread;
        return does not wait for reloads. Call outside provider locks/operation callbacks,
        do not call recursively from a change callback, and do not race shutdown.
        Tracking interest is expressed by pin flags; this method does not establish a watch.

        Args:
            identifiers: Canonical resource identifiers, each a nonempty string without NUL.
                A bare string/bytes object is not a batch. Values are copied for the native call.

        Returns:
            OK after delivery (including no listeners or an empty batch); INVALID_ARGUMENT
            for an inactive registration, or INVALID_STATE if the native service is unavailable.

        Raises:
            TypeError: The batch is not iterable, is a bare string/bytes, or contains non-strings.
            ValueError: An identifier is empty or contains NUL. No events are delivered.
        """
        if isinstance(identifiers, (str, bytes)):
            raise TypeError("identifiers must be a sequence of strings, not a single string")
        identifiers = tuple(identifiers)
        for identifier in identifiers:
            if not isinstance(identifier, str):
                raise TypeError("each identifier must be a string")
            if not identifier or "\0" in identifier:
                raise ValueError("each identifier must be nonempty and contain no NUL")
        # Retain each owning string wrapper as well as the pointer array through the call.
        strings = [bindings.ovx_string_t(identifier) for identifier in identifiers]
        array = (bindings.ovx_string_t * len(strings))(*strings)
        with _registration_lock:
            if not self._active:
                return DataStatus.INVALID_ARGUMENT
            lib, provider_id = self._lib, self._id
        return DataStatus(lib.ovrtx_data_notify_changed(provider_id, array, len(strings)))

    def unregister(self) -> DataStatus:
        """Remove an idle provider, returning BUSY without side effects if in use.

        Repeated removal of an inactive registration returns INVALID_ARGUMENT.
        Native shutdown also marks this object inactive. Successful removal releases this
        registration's strong references to the provider, callbacks and keepalive objects.
        Retire consumers and all outstanding pins, leases and requests before retrying BUSY.
        Do not call from a provider operation callback or race native shutdown.

        Returns:
            OK on removal; BUSY while referenced; INVALID_ARGUMENT if already inactive;
            INVALID_STATE if the native service is unavailable. Failures retain ownership.
        """
        with _registration_lock:
            if not self._active:
                return DataStatus.INVALID_ARGUMENT
            status = DataStatus(self._lib.ovrtx_unregister_data_provider(self._id))
            if status == DataStatus.OK:
                self._active = False
                del _registrations[self._id]
                self._native = None
                self._descriptor = None
                self._provider = None
                self._lib = None
            return status


def register_data_provider(
    descriptor: DataProviderDescriptor, provider: DataProvider, *, config: Optional[RendererConfig] = None
) -> DataProviderRegistration:
    """Register before submitting scene references; no Renderer instance is required.

    ``config`` supplies library initialization settings if OVRTX is not initialized
    yet, just as with Renderer construction. Callbacks must be instances of the
    corresponding ctypes callback types exported by this module.

    The returned registration and its callback/context keepalive objects remain strongly
    retained by the module even if the caller drops the result. Explicitly unregister when
    idle, or allow native shutdown to drain and release the registration. Do not call from
    provider operation callbacks or race shutdown. An unsuccessful call retains no provider state.

    Args:
        descriptor: Routing identity, priority and accessor capabilities; strings are copied.
        provider: Typed callbacks, optional context and objects kept alive for the registration.
        config: Optional initialization settings, used only when initializing OVRTX.

    Returns:
        An active DataProviderRegistration with a nonzero process-local ID.

    Raises:
        TypeError: An argument or callback has the wrong Python/ctypes type.
        ValueError: Numeric fields or capability bits are invalid.
        RuntimeError: Native initialization or registration failed, including duplicate namespace,
            invalid scheme, missing callback pairs or unavailable service.
    """
    if not isinstance(descriptor, DataProviderDescriptor):
        raise TypeError("descriptor must be a DataProviderDescriptor")
    for name in ("namespace_key", "uri_scheme"):
        if not isinstance(getattr(descriptor, name), str):
            raise TypeError(f"{name} must be a string")
    if isinstance(descriptor.priority, bool):
        raise TypeError("priority must be an integer, not bool")
    priority = operator.index(descriptor.priority)
    if not -(1 << 31) <= priority < (1 << 31):
        raise ValueError("priority must fit int32_t")
    if isinstance(descriptor.accessor_capabilities, bool):
        raise TypeError("accessor_capabilities must be an integer bitmask, not bool")
    capabilities = operator.index(descriptor.accessor_capabilities)
    supported = int(AccessorCapability.CPU_ARRAYS | AccessorCapability.GPU_ARRAYS)
    if capabilities < 0 or capabilities & ~supported:
        raise ValueError("accessor_capabilities contains unsupported bits")
    if not isinstance(provider, DataProvider):
        raise TypeError("provider must be a DataProvider")
    if not isinstance(provider.vtable, DataProviderVTable):
        raise TypeError("provider.vtable must be a DataProviderVTable")
    if provider.context is not None and not isinstance(provider.context, ct.POINTER(ovrtx_data_provider_context_t)):
        raise TypeError("provider.context must point to ovrtx_data_provider_context_t")
    native = ovrtx_data_provider_desc_t()
    native.struct_size = ct.sizeof(native)
    native.abi_version = DATA_PROVIDER_ABI_VERSION
    native.namespace_key = bindings.ovx_string_t(descriptor.namespace_key)
    native.uri_scheme = bindings.ovx_string_t(descriptor.uri_scheme)
    native.priority = priority
    native.accessor_capabilities = capabilities
    vtable = ovrtx_data_provider_vtable_t()
    vtable.struct_size = ct.sizeof(vtable)
    vtable.abi_version = DATA_PROVIDER_ABI_VERSION
    for name, callback_type in (
        ("pin_async", PinAsync),
        ("unpin", Unpin),
        ("read_async", ReadAsync),
        ("open_accessor_async", OpenAccessorAsync),
        ("close_accessor", CloseAccessor),
        ("cancel", Cancel),
        ("map_async", MapAsync),
        ("release_map", ReleaseMap),
    ):
        callback = getattr(provider.vtable, name)
        if callback is not None and not isinstance(callback, callback_type):
            raise TypeError(f"{name} must be an instance of its ctypes callback type")
        setattr(vtable, name, callback if callback is not None else callback_type())
    instance = ovrtx_data_provider_t(ct.pointer(vtable), provider.context)
    # Construct all callback storage before native admission. Registration itself
    # invokes no provider callbacks, so the strong-reference publication is atomic.
    with _registration_lock:
        bound = bindings._ovrtx_loader.create_bindings(Renderer._to_c_config(config or RendererConfig()))
        provider_id = DataProviderId()
        status = DataStatus(
            bound._lib.ovrtx_register_data_provider(ct.byref(native), ct.byref(instance), ct.byref(provider_id))
        )
        if status != DataStatus.OK:
            error = bound._lib.ovrtx_get_last_error()
            detail = f": {error}" if error.ptr else ""
            raise RuntimeError(f"Data provider registration failed: {status.name}{detail}")
        registration = DataProviderRegistration(provider_id, descriptor, provider, instance, bound._lib)
        _registrations[provider_id] = registration
        return registration


def _release_provider_registrations(lib) -> None:
    """Release Python ownership only after this native library has drained providers."""
    with _registration_lock:
        for provider_id, registration in list(_registrations.items()):
            if registration._lib is lib:
                registration._active = False
                registration._native = None
                registration._descriptor = None
                registration._provider = None
                registration._lib = None
                del _registrations[provider_id]
