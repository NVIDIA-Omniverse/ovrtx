# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""DLPack tensor structures for zero-copy data interchange.

This module provides ctypes wrappers for DLPack tensors, enabling efficient
data sharing between the C library and Python without copying.

Supports:
- DLPack 0.8: DLTensor, DLManagedTensor (legacy capsule layout).
- DLPack 1.0: DLManagedTensorVersioned with flags for read-only/writeable control.
- DLPack 1.3: device/type enums aligned with ovrtx dlpack.h.

NumPy 2.1+ supports the versioned protocol and respects DLPACK_FLAG_BITMASK_READ_ONLY.
Older NumPy versions default to read-only for safety.
"""

import ctypes
import operator
import sys
import threading
from typing import Any, Optional

__all__ = [
    "DLDeviceType",
    "DLDataTypeCode",
    "DLDevice",
    "DLDataType",
    "DLTensor",
    "DLManagedTensor",
    "DLPackVersion",
    "DLManagedTensorVersioned",
    "DLPACK_MAJOR_VERSION",
    "DLPACK_MINOR_VERSION",
    "DLPACK_FLAG_BITMASK_READ_ONLY",
    "DLPACK_FLAG_BITMASK_IS_COPIED",
    "DLPACK_FLAG_BITMASK_IS_SUBBYTE_TYPE_PADDED",
]

# DLPack version numbers (aligned with C header dlpack.h)
DLPACK_MAJOR_VERSION = 1
DLPACK_MINOR_VERSION = 3

# Capsule name strings
_c_str_dltensor = b"dltensor"
_c_str_used_dltensor = b"used_dltensor"
_c_str_dltensor_versioned = b"dltensor_versioned"
_c_str_used_dltensor_versioned = b"used_dltensor_versioned"

# DLPack 1.0+ flag bitmasks
DLPACK_FLAG_BITMASK_READ_ONLY = 1 << 0
DLPACK_FLAG_BITMASK_IS_COPIED = 1 << 1
DLPACK_FLAG_BITMASK_IS_SUBBYTE_TYPE_PADDED = 1 << 2


class DLDeviceType(ctypes.c_int):
    """The enum that encodes the type of the device where
    DLTensor memory is allocated.
    """

    kDLCPU = 1
    kDLCUDA = 2
    kDLCUDAHost = 3
    kDLOpenCL = 4
    kDLVulkan = 7
    kDLMetal = 8
    kDLVPI = 9
    kDLROCM = 10
    kDLROCMHost = 11
    kDLExtDev = 12
    kDLCUDAManaged = 13
    kDLOneAPI = 14
    kDLWebGPU = 15
    kDLHexagon = 16
    kDLMAIA = 17
    kDLTrn = 18

    def __str__(self):
        return {
            self.kDLCPU: "CPU",
            self.kDLCUDA: "CUDA",
            self.kDLCUDAHost: "CUDAHost",
            self.kDLOpenCL: "OpenCL",
            self.kDLVulkan: "Vulkan",
            self.kDLMetal: "Metal",
            self.kDLVPI: "VPI",
            self.kDLROCM: "ROCM",
            self.kDLROCMHost: "ROCMHost",
            self.kDLExtDev: "ExtDev",
            self.kDLCUDAManaged: "CUDAManaged",
            self.kDLOneAPI: "OneAPI",
            self.kDLWebGPU: "WebGPU",
            self.kDLHexagon: "Hexagon",
            self.kDLMAIA: "MAIA",
            self.kDLTrn: "Trn",
        }.get(self.value, f"Device{self.value}")


class DLDataTypeCode(ctypes.c_uint8):
    """An integer that encodes the category of DLTensor elements' data type."""

    kDLInt = 0
    kDLUInt = 1
    kDLFloat = 2
    kDLOpaqueHandle = 3
    kDLBfloat = 4
    kDLComplex = 5
    kDLBool = 6
    kDLFloat8_e3m4 = 7
    kDLFloat8_e4m3 = 8
    kDLFloat8_e4m3b11fnuz = 9
    kDLFloat8_e4m3fn = 10
    kDLFloat8_e4m3fnuz = 11
    kDLFloat8_e5m2 = 12
    kDLFloat8_e5m2fnuz = 13
    kDLFloat8_e8m0fnu = 14
    kDLFloat6_e2m3fn = 15
    kDLFloat6_e3m2fn = 16
    kDLFloat4_e2m1fn = 17

    def __str__(self):
        return {
            self.kDLInt: "int",
            self.kDLUInt: "uint",
            self.kDLFloat: "float",
            self.kDLBfloat: "bfloat",
            self.kDLComplex: "complex",
            self.kDLOpaqueHandle: "void_p",
            self.kDLBool: "bool",
            self.kDLFloat8_e3m4: "float8_e3m4",
            self.kDLFloat8_e4m3: "float8_e4m3",
            self.kDLFloat8_e4m3b11fnuz: "float8_e4m3b11fnuz",
            self.kDLFloat8_e4m3fn: "float8_e4m3fn",
            self.kDLFloat8_e4m3fnuz: "float8_e4m3fnuz",
            self.kDLFloat8_e5m2: "float8_e5m2",
            self.kDLFloat8_e5m2fnuz: "float8_e5m2fnuz",
            self.kDLFloat8_e8m0fnu: "float8_e8m0fnu",
            self.kDLFloat6_e2m3fn: "float6_e2m3fn",
            self.kDLFloat6_e3m2fn: "float6_e3m2fn",
            self.kDLFloat4_e2m1fn: "float4_e2m1fn",
        }.get(self.value, f"type{self.value}")


class DLDevice(ctypes.Structure):
    """Represents the device where DLTensor memory is allocated."""

    _fields_ = [
        ("device_type", DLDeviceType),
        ("device_id", ctypes.c_int32),
    ]

    def __str__(self) -> str:
        if self.device_id != 0:
            return f"{self.device_type}:{self.device_id}"
        return str(self.device_type)


class DLDataType(ctypes.Structure):
    """Descriptor of data type for elements of DLTensor."""

    _fields_ = [
        ("code", DLDataTypeCode),
        ("bits", ctypes.c_uint8),
        ("lanes", ctypes.c_uint16),
    ]

    TYPE_MAP = {
        "int8": (DLDataTypeCode.kDLInt, 8, 1),
        "int16": (DLDataTypeCode.kDLInt, 16, 1),
        "int32": (DLDataTypeCode.kDLInt, 32, 1),
        "int64": (DLDataTypeCode.kDLInt, 64, 1),
        "uint8": (DLDataTypeCode.kDLUInt, 8, 1),
        "uint16": (DLDataTypeCode.kDLUInt, 16, 1),
        "uint32": (DLDataTypeCode.kDLUInt, 32, 1),
        "uint64": (DLDataTypeCode.kDLUInt, 64, 1),
        "float16": (DLDataTypeCode.kDLFloat, 16, 1),
        "float32": (DLDataTypeCode.kDLFloat, 32, 1),
        "float64": (DLDataTypeCode.kDLFloat, 64, 1),
        "bfloat16": (DLDataTypeCode.kDLBfloat, 16, 1),
        # Multi-lane vector types
        "uint8x4": (DLDataTypeCode.kDLUInt, 8, 4),
        "float32x4": (DLDataTypeCode.kDLFloat, 32, 4),
    }

    @classmethod
    def from_str(cls, type_name: str, lanes: Optional[int] = None) -> "DLDataType":
        """Create DLDataType from string name with optional lanes override.

        Args:
            type_name: Type name like "int32", "float32", "uint8x4".
            lanes: Optional lanes override for vector types. If provided, overrides
                the default lanes from TYPE_MAP. Must be an integer in [1, 65535]:
                the value lands in the DLPack uint16 lane field, so anything outside
                that range raises instead of silently wrapping to a bogus lane count
                (e.g. -1 becoming 65535).

        Returns:
            DLDataType instance.

        Raises:
            ValueError: If type_name is not recognized, or lanes is outside [1, 65535].
            TypeError: If lanes is not an integer.

        Example:
            >>> DLDataType.from_str("int32")           # int32, lanes=1
            >>> DLDataType.from_str("float32", lanes=3)  # float3 for points
            >>> DLDataType.from_str("float64", lanes=3)  # double3 for points
        """
        if type_name not in cls.TYPE_MAP:
            raise ValueError(f"Unknown type: {type_name}. Valid types: {list(cls.TYPE_MAP.keys())}")
        code, bits, default_lanes = cls.TYPE_MAP[type_name]
        if lanes is not None:
            lanes = operator.index(lanes)
            if not 1 <= lanes <= 0xFFFF:
                raise ValueError(f"DLDataType lanes must be in [1, 65535], got {lanes}")
        return cls(code=code, bits=bits, lanes=lanes if lanes is not None else default_lanes)

    def __str__(self) -> str:
        # Try reverse lookup in TYPE_MAP
        for name, (code_val, bits, lanes) in self.TYPE_MAP.items():
            if self.code == code_val and self.bits == bits and self.lanes == lanes:
                return name
        # Fallback
        if self.lanes > 1:
            return f"{self.code}{self.bits}x{self.lanes}"
        return f"{self.code}{self.bits}"


class DLTensor(ctypes.Structure):
    """Plain C Tensor object, does not manage memory."""

    _fields_ = [
        ("data", ctypes.c_void_p),
        ("device", DLDevice),
        ("ndim", ctypes.c_int32),
        ("dtype", DLDataType),
        ("shape", ctypes.POINTER(ctypes.c_int64)),
        ("strides", ctypes.POINTER(ctypes.c_int64)),
        ("byte_offset", ctypes.c_uint64),
    ]


class DLManagedTensor(ctypes.Structure):
    """C structure for managed DLPack 0.x tensor."""

    _fields_ = [
        ("dl_tensor", DLTensor),
        ("manager_ctx", ctypes.c_void_p),
        ("deleter", ctypes.CFUNCTYPE(None, ctypes.c_void_p)),
    ]


# DLPack deleter function type: void (*)(void*)
DLPACK_DELETER = ctypes.CFUNCTYPE(None, ctypes.c_void_p)


class DLPackVersion(ctypes.Structure):
    """DLPack version struct for versioned protocol."""

    _fields_ = [
        ("major", ctypes.c_uint32),
        ("minor", ctypes.c_uint32),
    ]


class DLManagedTensorVersioned(ctypes.Structure):
    """DLPack 1.0 versioned managed tensor."""

    _fields_ = [
        ("version", DLPackVersion),  # offset 0, size 8
        ("manager_ctx", ctypes.c_void_p),  # offset 8, size 8
        ("deleter", DLPACK_DELETER),  # offset 16, size 8
        ("flags", ctypes.c_uint64),  # offset 24, size 8
        ("dl_tensor", DLTensor),  # offset 32, size 48
    ]


PyCapsule_IsValid = ctypes.pythonapi.PyCapsule_IsValid
PyCapsule_IsValid.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_IsValid.restype = ctypes.c_int

PyCapsule_GetPointer = ctypes.pythonapi.PyCapsule_GetPointer
PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_GetPointer.restype = ctypes.c_void_p

PyCapsule_SetName = ctypes.pythonapi.PyCapsule_SetName
PyCapsule_SetName.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_SetName.restype = ctypes.c_int


class _ManagedTensorLease:
    """Keep a consumed foreign managed tensor alive."""

    __slots__ = ("_deleter", "_managed_ptr", "_tensor")

    def __init__(self, managed_ptr: int, deleter: Any) -> None:
        self._managed_ptr = managed_ptr
        self._deleter = deleter
        self._tensor = None

    @property
    def tensor(self) -> DLTensor:
        """The foreign tensor, valid while this lease is alive."""
        if self._tensor is None:
            raise RuntimeError("DLPack tensor has been released")
        return self._tensor

    def __del__(self) -> None:
        # Clear this lease before a foreign deleter can re-enter Python.
        managed_ptr = self._managed_ptr
        deleter = self._deleter
        self._managed_ptr = 0
        self._deleter = None
        self._tensor = None

        try:
            if managed_ptr and deleter:
                deleter(managed_ptr)
        except BaseException:
            # Destructors have no error channel. The producer must still obey
            # DLPack's noexcept deleter contract; never replace an outer error.
            pass


def _from_dlpack(obj: Any, stream: Optional[int] = None, *, writable: bool = False) -> _ManagedTensorLease:
    """Consume a foreign DLPack export and retain its managed tensor."""
    if not hasattr(obj, "__dlpack__"):
        raise TypeError(f"Object of type {type(obj).__name__} does not support DLPack protocol")

    kwargs = {"max_version": (DLPACK_MAJOR_VERSION, DLPACK_MINOR_VERSION)}
    if stream is not None and hasattr(obj, "__dlpack_device__"):
        device_type, _ = obj.__dlpack_device__()
        if device_type in (DLDeviceType.kDLCUDA, DLDeviceType.kDLROCM, DLDeviceType.kDLCUDAManaged):
            kwargs["stream"] = stream

    try:
        capsule = obj.__dlpack__(**kwargs)
    except TypeError:
        kwargs.pop("max_version")
        capsule = obj.__dlpack__(**kwargs)

    if PyCapsule_IsValid(capsule, _c_str_dltensor):
        capsule_name = _c_str_dltensor
        used_name = _c_str_used_dltensor
        managed_type = DLManagedTensor
    elif PyCapsule_IsValid(capsule, _c_str_dltensor_versioned):
        capsule_name = _c_str_dltensor_versioned
        used_name = _c_str_used_dltensor_versioned
        managed_type = DLManagedTensorVersioned
    else:
        raise RuntimeError("DLPack producer returned an invalid or already-consumed capsule")

    ptr = PyCapsule_GetPointer(capsule, capsule_name)
    if not ptr:
        raise RuntimeError("Failed to get managed DLPack tensor pointer from capsule")

    managed = ctypes.cast(ptr, ctypes.POINTER(managed_type)).contents
    deleter = managed.deleter
    if PyCapsule_SetName(capsule, used_name) != 0:
        raise RuntimeError("Failed to mark DLPack capsule as consumed")

    try:
        lease = _ManagedTensorLease(ptr, deleter)
    except BaseException:
        # Ownership transferred when the capsule was renamed, so allocation
        # failure has no object whose destructor could release the descriptor.
        try:
            if deleter:
                deleter(ptr)
        except BaseException:
            pass
        raise

    if managed_type is DLManagedTensorVersioned:
        if managed.version.major != DLPACK_MAJOR_VERSION:
            producer_major = managed.version.major
            del lease
            raise RuntimeError(
                f"DLPack producer major version {producer_major} is incompatible with {DLPACK_MAJOR_VERSION}"
            )
        if writable and managed.flags & DLPACK_FLAG_BITMASK_READ_ONLY:
            del lease
            raise BufferError("DLPack destination is read-only")
        if writable and managed.flags & DLPACK_FLAG_BITMASK_IS_COPIED:
            del lease
            raise BufferError("DLPack destination export is a copy")

    lease._tensor = managed.dl_tensor
    return lease


class _NativePythonApiV1(ctypes.Structure):
    _fields_ = [
        ("struct_size", ctypes.c_uint32),
        ("abi_version", ctypes.c_uint32),
        ("python_hexversion", ctypes.c_uint32),
        ("py_gil_state_ensure", ctypes.c_void_p),
        ("py_gil_state_release", ctypes.c_void_p),
        ("py_inc_ref", ctypes.c_void_p),
        ("py_dec_ref", ctypes.c_void_p),
        ("py_capsule_new", ctypes.c_void_p),
        ("py_capsule_is_valid", ctypes.c_void_p),
        ("py_capsule_get_pointer", ctypes.c_void_p),
        ("py_capsule_set_name", ctypes.c_void_p),
        ("py_err_fetch", ctypes.c_void_p),
        ("py_err_restore", ctypes.c_void_p),
        ("py_err_clear", ctypes.c_void_p),
        ("py_err_occurred", ctypes.c_void_p),
        ("py_err_set_string", ctypes.c_void_p),
        ("py_err_no_memory", ctypes.c_void_p),
        ("py_exc_runtime_error", ctypes.py_object),
        ("py_exc_value_error", ctypes.py_object),
    ]


class _NativeCreateV1(ctypes.Structure):
    _fields_ = [
        ("struct_size", ctypes.c_uint32),
        ("max_version", DLPackVersion),
        ("dlpack_flags", ctypes.c_uint64),
        ("tensor", ctypes.POINTER(DLTensor)),
        ("owner", ctypes.py_object),
    ]


class _NativeExtensionV1(ctypes.Structure):
    _fields_ = [
        ("struct_size", ctypes.c_uint32),
        ("abi_version", ctypes.c_uint32),
        ("create_bridge", ctypes.c_void_p),
        ("close_bridge", ctypes.c_void_p),
        ("create_capsule", ctypes.c_void_p),
    ]


def _python_api_address(name: str) -> int:
    return ctypes.cast(getattr(ctypes.pythonapi, name), ctypes.c_void_p).value


class _NativeDLPackBridge:
    _SUCCESS = 0
    _INCOMPATIBLE_RUNTIME = 4

    def __init__(self, extension_ptr: int) -> None:
        extension = ctypes.cast(extension_ptr, ctypes.POINTER(_NativeExtensionV1)).contents
        if extension.struct_size < ctypes.sizeof(_NativeExtensionV1) or extension.abi_version != 1:
            raise RuntimeError("Unsupported ovrtx native DLPack extension ABI")

        self._extension = extension
        self._create_bridge = ctypes.PYFUNCTYPE(
            ctypes.c_uint32, ctypes.POINTER(_NativePythonApiV1), ctypes.POINTER(ctypes.c_void_p)
        )(extension.create_bridge)
        # Closing drains foreign threads that may be waiting for the GIL,
        # so this outbound call must release the calling Python thread's GIL.
        self._close_bridge = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(extension.close_bridge)
        self._create_capsule = ctypes.PYFUNCTYPE(ctypes.py_object, ctypes.c_void_p, ctypes.POINTER(_NativeCreateV1))(
            extension.create_capsule
        )

        api = _NativePythonApiV1(
            struct_size=ctypes.sizeof(_NativePythonApiV1),
            abi_version=1,
            python_hexversion=sys.hexversion,
            py_gil_state_ensure=_python_api_address("PyGILState_Ensure"),
            py_gil_state_release=_python_api_address("PyGILState_Release"),
            py_inc_ref=_python_api_address("Py_IncRef"),
            py_dec_ref=_python_api_address("Py_DecRef"),
            py_capsule_new=_python_api_address("PyCapsule_New"),
            py_capsule_is_valid=_python_api_address("PyCapsule_IsValid"),
            py_capsule_get_pointer=_python_api_address("PyCapsule_GetPointer"),
            py_capsule_set_name=_python_api_address("PyCapsule_SetName"),
            py_err_fetch=_python_api_address("PyErr_Fetch"),
            py_err_restore=_python_api_address("PyErr_Restore"),
            py_err_clear=_python_api_address("PyErr_Clear"),
            py_err_occurred=_python_api_address("PyErr_Occurred"),
            py_err_set_string=_python_api_address("PyErr_SetString"),
            py_err_no_memory=_python_api_address("PyErr_NoMemory"),
            py_exc_runtime_error=RuntimeError,
            py_exc_value_error=ValueError,
        )
        bridge = ctypes.c_void_p()
        status = self._create_bridge(ctypes.byref(api), ctypes.byref(bridge))
        if status == self._INCOMPATIBLE_RUNTIME:
            raise RuntimeError("ovrtx native DLPack is already bound to a different CPython runtime")
        if status != self._SUCCESS or not bridge.value:
            raise RuntimeError(f"Failed to create the ovrtx DLPack bridge (status={status})")
        self._api = api
        self._lock = threading.Lock()
        self._bridge = bridge
        self._active = True

    def close(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._active = False
            bridge = self._bridge
            self._bridge = ctypes.c_void_p()
        # Draining may enter Python; the retired handle no longer needs the lock.
        self._close_bridge(bridge)

    def create_capsule(
        self, dl_tensor: DLTensor, owner: Any, *, max_version: Optional[tuple[int, int]], readonly: bool
    ) -> Any:
        version = DLPackVersion(0, 0) if max_version is None else DLPackVersion(*max_version)
        create = _NativeCreateV1(
            struct_size=ctypes.sizeof(_NativeCreateV1),
            max_version=version,
            dlpack_flags=DLPACK_FLAG_BITMASK_READ_ONLY if readonly else 0,
            tensor=ctypes.pointer(dl_tensor),
            owner=owner,
        )
        with self._lock:
            if not self._active:
                raise RuntimeError("ovrtx native DLPack bridge is closed")
            return self._create_capsule(self._bridge, ctypes.byref(create))


_native_dlpack_bridge: Optional[_NativeDLPackBridge] = None


def _initialize_native_dlpack_bridge(lib: ctypes.CDLL) -> None:
    """Query and create the private native DLPack bridge."""
    global _native_dlpack_bridge
    if _native_dlpack_bridge is not None:
        return

    extension_ptr = ctypes.c_void_p()
    result = lib.ovrtx_query_extension(b"ovrtx.python.dlpack.v1", ctypes.byref(extension_ptr))
    if result.status != 0 or not extension_ptr.value:
        raise RuntimeError("Loaded ovrtx library does not provide the native DLPack extension")
    _native_dlpack_bridge = _NativeDLPackBridge(extension_ptr.value)


def _close_native_dlpack_bridge() -> None:
    global _native_dlpack_bridge
    bridge = _native_dlpack_bridge
    _native_dlpack_bridge = None
    if bridge is not None:
        bridge.close()


def _to_dlpack_capsule(
    dl_tensor: DLTensor,
    manager_ctx: Any,
    *,
    dl_device: Optional[tuple[int, int]],
    max_version: Optional[tuple[int, int]] = None,
    readonly: bool = True,
) -> Any:
    """Create DLPack capsule from DLTensor.

    Args:
        dl_tensor: The tensor to wrap
        manager_ctx: Python object to keep alive (prevents GC of underlying data)
        dl_device: Requested target device, or None to use the tensor's current device
        max_version: Maximum DLPack version supported by the consumer
        readonly: If True and versioned, set DLPACK_FLAG_BITMASK_READ_ONLY flag

    Returns:
        PyCapsule for the DLPack tensor.

    Note:
        Per DLPack spec: Consumer renames capsule to "used_*" after extraction.
        The Python owner remains alive until the consumer releases the managed
        tensor or an unconsumed capsule is destroyed.
    """
    if dl_device is not None:
        if not isinstance(dl_device, tuple) or len(dl_device) != 2:
            raise TypeError("dl_device must be a (device_type, device_id) tuple of integers")
        try:
            requested_device = (operator.index(dl_device[0]), operator.index(dl_device[1]))
        except TypeError as exc:
            raise TypeError("dl_device must be a (device_type, device_id) tuple of integers") from exc

        current_device = (dl_tensor.device.device_type.value, dl_tensor.device.device_id)
        if requested_device != current_device:
            raise BufferError(
                f"dl_device={requested_device!r} does not match tensor device "
                f"{current_device!r}; cross-device copy is not supported"
            )

    bridge = _native_dlpack_bridge
    if bridge is None:
        raise RuntimeError("The native ovrtx DLPack bridge requires an initialized OVRTX runtime")
    return bridge.create_capsule(
        dl_tensor,
        manager_ctx,
        max_version=max_version,
        readonly=readonly,
    )


class _DLPackable:
    """Shared DLPack protocol implementation for OVRTX tensor views."""

    __slots__ = ("_dltensor", "_dlpack_error", "_owner", "_readonly")

    def __init__(
        self,
        dltensor: Optional[DLTensor],
        error: Optional[str] = None,
        *,
        owner: Any = None,
        readonly: bool = True,
    ):
        if not isinstance(readonly, bool):
            raise TypeError(f"readonly must be bool, got {type(readonly).__name__}")
        self._dltensor = dltensor
        self._dlpack_error = error
        self._owner = owner
        self._readonly = readonly

    @property
    def _dlpack_tensor(self) -> DLTensor:
        if self._dltensor is None:
            raise RuntimeError(self._dlpack_error or "DLPack tensor is unavailable")
        return self._dltensor

    @property
    def shape(self) -> tuple[int, ...]:
        """Tensor shape."""
        tensor = self._dlpack_tensor
        return tuple(tensor.shape[i] for i in range(tensor.ndim))

    @property
    def dtype(self) -> DLDataType:
        """Tensor data type."""
        return self._dlpack_tensor.dtype

    @property
    def ndim(self) -> int:
        """Tensor rank."""
        return self._dlpack_tensor.ndim

    @property
    def data(self) -> int:
        """Tensor data pointer."""
        return self._dlpack_tensor.data

    @property
    def device(self) -> DLDevice:
        """Tensor device."""
        return self._dlpack_tensor.device

    def __dlpack_device__(self) -> tuple[int, int]:
        """Report the tensor device through the DLPack Python protocol."""
        device = self._dlpack_tensor.device
        return (device.device_type.value, device.device_id)

    def __dlpack__(
        self,
        *,
        stream: Optional[int] = None,
        max_version: Optional[tuple[int, int]] = None,
        dl_device: Optional[tuple[int, int]] = None,
        copy: Optional[bool] = None,
    ) -> Any:
        """Export the tensor through the DLPack Python protocol for zero-copy interop."""
        _ = stream  # synchronization is the caller's responsibility
        if copy is True:
            raise BufferError("copy=True not supported")
        return _to_dlpack_capsule(
            self._dlpack_tensor,
            self,
            dl_device=dl_device,
            max_version=max_version,
            readonly=self._readonly,
        )
