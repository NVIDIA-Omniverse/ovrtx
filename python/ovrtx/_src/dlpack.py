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
from typing import Any, Callable, Optional

__all__ = [
    "DLDeviceType",
    "DLDataTypeCode",
    "DLDevice",
    "DLDataType",
    "DLTensor",
    "DLManagedTensor",
    "DLPackVersion",
    "DLManagedTensorVersioned",
    "ManagedDLTensor",
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
                the default lanes from TYPE_MAP.

        Returns:
            DLDataType instance.

        Raises:
            ValueError: If type_name is not recognized.

        Example:
            >>> DLDataType.from_str("int32")           # int32, lanes=1
            >>> DLDataType.from_str("float32", lanes=3)  # float3 for points
            >>> DLDataType.from_str("float64", lanes=3)  # double3 for points
        """
        if type_name not in cls.TYPE_MAP:
            raise ValueError(f"Unknown type: {type_name}. Valid types: {list(cls.TYPE_MAP.keys())}")
        code, bits, default_lanes = cls.TYPE_MAP[type_name]
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

    @classmethod
    def from_dlpack(cls, obj: Any, stream: Optional[int] = None) -> "DLTensor":
        """Extract DLTensor from an object implementing the DLPack protocol.

        This is useful for passing numpy arrays or other DLPack-compatible objects
        to ovrtx APIs that expect DLTensor.

        Args:
            obj: Object with __dlpack__() method (e.g., numpy array).
            stream: CUDA stream handle to pass to the DLPack producer for synchronization.
                When supplied and ``obj`` reports a CUDA device via ``__dlpack_device__``, the
                producer is instructed to make this stream wait for any pending work on ``obj``
                so the consumer can safely read the tensor on that stream. Ignored for CPU
                tensors and for producers that don't advertise ``__dlpack_device__``.

        Returns:
            DLTensor with copied shape/strides (safe to use after capsule is freed).

        Raises:
            TypeError: If object does not support DLPack protocol.
            RuntimeError: If capsule extraction fails.

        Note:
            The returned DLTensor's data pointer references memory owned by the
            original object. Keep the original object alive while using the DLTensor.
            The shape and strides arrays are deep-copied for safety.
        """
        if not hasattr(obj, "__dlpack__"):
            raise TypeError(f"Object of type {type(obj).__name__} does not support DLPack protocol")

        # Forward the consumer stream only for CUDA tensors (CPU __dlpack__ rejects stream args).
        pass_stream = False
        if stream is not None and hasattr(obj, "__dlpack_device__"):
            device_type, _ = obj.__dlpack_device__()
            pass_stream = device_type in (DLDeviceType.kDLCUDA, DLDeviceType.kDLCUDAManaged)

        capsule = obj.__dlpack__(stream=stream) if pass_stream else obj.__dlpack__()

        # Extract pointer to DLManagedTensor from capsule
        ptr = PyCapsule_GetPointer(capsule, b"dltensor")
        if not ptr:
            raise RuntimeError("Failed to get DLManagedTensor pointer from capsule")

        # Cast to DLManagedTensor and extract dl_tensor
        managed = ctypes.cast(ptr, ctypes.POINTER(DLManagedTensor)).contents
        src = managed.dl_tensor

        # Create new DLTensor with copied shape/strides (capsule memory may be freed)
        result = cls()
        result.data = src.data
        result.device = src.device
        result.ndim = src.ndim
        result.dtype = src.dtype
        result.byte_offset = src.byte_offset

        # Deep-copy shape/strides arrays and keep source object alive as instance
        # attributes so their lifetime is tied to this DLTensor.
        result._source_obj = obj
        if src.ndim > 0 and src.shape:
            result._shape_storage = (ctypes.c_int64 * src.ndim)()
            for i in range(src.ndim):
                result._shape_storage[i] = src.shape[i]
            result.shape = ctypes.cast(result._shape_storage, ctypes.POINTER(ctypes.c_int64))
        else:
            result.shape = None

        if src.ndim > 0 and src.strides:
            result._strides_storage = (ctypes.c_int64 * src.ndim)()
            for i in range(src.ndim):
                result._strides_storage[i] = src.strides[i]
            result.strides = ctypes.cast(result._strides_storage, ctypes.POINTER(ctypes.c_int64))
        else:
            result.strides = None

        # Mark capsule as consumed per DLPack protocol (prevents double-consumption)
        PyCapsule_SetName(capsule, b"used_dltensor")

        # Release the managed tensor descriptor. capsule_destructor will no-op via name check
        # when the consumed capsule is later GC'd (name is now "used_dltensor*").
        if managed.deleter:
            managed.deleter(ptr)

        return result


class DLManagedTensor(ctypes.Structure):
    """C structure for managed DLPack 0.x tensor.

    Layout: dl_tensor is FIRST (offset 0).
    """

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


# Python C API bindings for capsule protocol
PyMem_Malloc = ctypes.pythonapi.PyMem_Malloc
PyMem_Malloc.argtypes = [ctypes.c_size_t]
PyMem_Malloc.restype = ctypes.c_void_p

PyMem_Free = ctypes.pythonapi.PyMem_Free
PyMem_Free.argtypes = [ctypes.c_void_p]
PyMem_Free.restype = None

Py_IncRef = ctypes.pythonapi.Py_IncRef
Py_IncRef.argtypes = [ctypes.py_object]
Py_IncRef.restype = None

Py_DecRef = ctypes.pythonapi.Py_DecRef
Py_DecRef.argtypes = [ctypes.py_object]
Py_DecRef.restype = None

PyCapsule_Destructor = ctypes.CFUNCTYPE(None, ctypes.c_void_p)

PyCapsule_New = ctypes.pythonapi.PyCapsule_New
PyCapsule_New.argtypes = [ctypes.c_void_p, ctypes.c_char_p, PyCapsule_Destructor]
PyCapsule_New.restype = ctypes.py_object

PyCapsule_IsValid = ctypes.pythonapi.PyCapsule_IsValid
PyCapsule_IsValid.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_IsValid.restype = ctypes.c_int

PyCapsule_GetPointer = ctypes.pythonapi.PyCapsule_GetPointer
PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_GetPointer.restype = ctypes.c_void_p

PyCapsule_SetName = ctypes.pythonapi.PyCapsule_SetName
PyCapsule_SetName.argtypes = [ctypes.py_object, ctypes.c_char_p]
PyCapsule_SetName.restype = ctypes.c_int

# Separate bindings that accept capsule as c_void_p (raw pointer) rather than py_object,
# for use inside capsule_destructor where the capsule refcount is already zero.
_PyCapsule_IsValid_raw = ctypes.pythonapi["PyCapsule_IsValid"]
_PyCapsule_IsValid_raw.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
_PyCapsule_IsValid_raw.restype = ctypes.c_int

_PyCapsule_GetPointer_raw = ctypes.pythonapi["PyCapsule_GetPointer"]
_PyCapsule_GetPointer_raw.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
_PyCapsule_GetPointer_raw.restype = ctypes.c_void_p

PyCapsule_SetContext = ctypes.pythonapi.PyCapsule_SetContext
PyCapsule_SetContext.argtypes = [ctypes.py_object, ctypes.c_void_p]
PyCapsule_SetContext.restype = ctypes.c_int

_PyCapsule_GetContext_raw = ctypes.pythonapi["PyCapsule_GetContext"]
_PyCapsule_GetContext_raw.argtypes = [ctypes.c_void_p]
_PyCapsule_GetContext_raw.restype = ctypes.c_void_p


class _CapsuleCtx:
    """Internal keepalive for DLPack capsule callbacks and the caller's manager_ctx."""

    __slots__ = ("manager_ctx", "deleter_callback", "c_deleter", "capsule_destructor")

    def __init__(self, manager_ctx: Any, deleter_callback: Optional[Callable]) -> None:
        self.manager_ctx = manager_ctx
        self.deleter_callback = deleter_callback
        self.c_deleter = None
        self.capsule_destructor = None


def _to_dlpack_capsule(
    dl_tensor: DLTensor,
    manager_ctx: Any,
    deleter_callback: Optional[Callable] = None,
    *,
    versioned: bool = False,
    readonly: bool = True,
) -> Any:
    """Create DLPack capsule from DLTensor.

    Args:
        dl_tensor: The tensor to wrap
        manager_ctx: Python object to keep alive (prevents GC of underlying data)
        deleter_callback: Optional callback when tensor is released
        versioned: If True, create DLPack 1.0 DLManagedTensorVersioned capsule
        readonly: If True and versioned, set DLPACK_FLAG_BITMASK_READ_ONLY flag

    Returns:
        PyCapsule for the DLPack tensor.

    Note:
        Per DLPack spec: Consumer renames capsule to "used_*" after extraction.
        Capsule destructor checks name and calls deleter only if unconsumed.
        manager_ctx is kept alive for the lifetime of the capsule.
    """
    # Handle vectorized dtypes (lanes > 1) by expanding to an extra shape dimension
    actual_ndim = dl_tensor.ndim + (1 if dl_tensor.dtype.lanes > 1 else 0)

    # Choose struct type and capsule name based on version
    if versioned:
        ManagedTensor = DLManagedTensorVersioned
        capsule_name = _c_str_dltensor_versioned
    else:
        ManagedTensor = DLManagedTensor
        capsule_name = _c_str_dltensor

    # Allocate managed tensor + shape array in one block
    managed_size = ctypes.sizeof(ManagedTensor)
    shape_size = actual_ndim * ctypes.sizeof(ctypes.c_int64)
    total_size = managed_size + shape_size

    mem_ptr = PyMem_Malloc(total_size)
    if not mem_ptr:
        raise MemoryError("Failed to allocate DLManagedTensor")

    managed_tensor = ManagedTensor.from_address(mem_ptr)

    # Set version and flags for versioned struct
    if versioned:
        managed_tensor.version.major = DLPACK_MAJOR_VERSION
        managed_tensor.version.minor = DLPACK_MINOR_VERSION
        managed_tensor.flags = DLPACK_FLAG_BITMASK_READ_ONLY if readonly else 0

    # Copy DLTensor fields (shallow copy - pointers reference C memory)
    managed_tensor.dl_tensor.data = dl_tensor.data
    managed_tensor.dl_tensor.device = dl_tensor.device
    managed_tensor.dl_tensor.ndim = actual_ndim
    managed_tensor.dl_tensor.byte_offset = dl_tensor.byte_offset

    # Copy dtype, adjusting lanes if expanded
    managed_tensor.dl_tensor.dtype.code = dl_tensor.dtype.code
    managed_tensor.dl_tensor.dtype.bits = dl_tensor.dtype.bits
    managed_tensor.dl_tensor.dtype.lanes = 1 if dl_tensor.dtype.lanes > 1 else dl_tensor.dtype.lanes

    # Set up shape array after the managed tensor struct
    shape_ptr = ctypes.cast(mem_ptr + managed_size, ctypes.POINTER(ctypes.c_int64))
    for i in range(dl_tensor.ndim):
        shape_ptr[i] = dl_tensor.shape[i]
    if dl_tensor.dtype.lanes > 1:
        shape_ptr[dl_tensor.ndim] = dl_tensor.dtype.lanes
    managed_tensor.dl_tensor.shape = shape_ptr
    managed_tensor.dl_tensor.strides = None

    # Two manual refs keep _capsule_ctx (and its CFUNCTYPEs) alive: one for c_deleter,
    # one for capsule_destructor stored in the capsule context.
    _capsule_ctx = _CapsuleCtx(manager_ctx, deleter_callback)
    Py_IncRef(_capsule_ctx)  # held by c_deleter
    managed_tensor.manager_ctx = id(_capsule_ctx)

    @DLPACK_DELETER
    def c_deleter(managed_ptr):
        mt = ManagedTensor.from_address(managed_ptr)
        ctx = ctypes.cast(mt.manager_ctx, ctypes.py_object).value
        try:
            if ctx.deleter_callback is not None:
                ctx.deleter_callback(ctx.manager_ctx)
        finally:
            Py_DecRef(ctx)
            PyMem_Free(managed_ptr)

    @PyCapsule_Destructor
    def capsule_destructor(capsule_ptr):
        ctx_id = _PyCapsule_GetContext_raw(capsule_ptr)
        if ctx_id:
            ctx = ctypes.cast(ctx_id, ctypes.py_object).value
            Py_DecRef(ctx)

        # Use raw c_void_p bindings to avoid incrementing refcount on an object under deallocation.
        # IsValid check skips the deleter when the capsule was already consumed (renamed by consumer).
        if not _PyCapsule_IsValid_raw(capsule_ptr, capsule_name):
            return
        managed_ptr = _PyCapsule_GetPointer_raw(capsule_ptr, capsule_name)
        if managed_ptr:
            mt = ManagedTensor.from_address(managed_ptr)
            if mt.deleter:
                mt.deleter(managed_ptr)

    _capsule_ctx.c_deleter = c_deleter
    _capsule_ctx.capsule_destructor = capsule_destructor
    managed_tensor.deleter = c_deleter

    capsule = PyCapsule_New(mem_ptr, capsule_name, capsule_destructor)
    Py_IncRef(_capsule_ctx)  # held by capsule_destructor
    PyCapsule_SetContext(capsule, id(_capsule_ctx))
    return capsule


class ManagedDLTensor:
    """Managed DLPack tensor wrapper with protocol version support.

    Obtained from :attr:`AttributeMapping.tensor` (for attribute maps).
    Pass the instance to ``np.from_dlpack()`` / ``wp.from_dlpack()`` /
    ``torch.from_dlpack()`` for zero-copy array access, or call
    :meth:`numpy` / :meth:`to_bytes` directly.

    Supports both DLPack 0.x and 1.0 protocols. When a consumer (e.g. NumPy 2.1+)
    requests a versioned capsule via ``__dlpack__(max_version=...)``, this returns a
    ``DLManagedTensorVersioned`` with proper read-only/writeable flags.
    """

    def __init__(
        self,
        dl_tensor: DLTensor,
        manager_ctx: Any,
        deleter_callback: Optional[Callable] = None,
        readonly: bool = True,
    ):
        self._dl_tensor = dl_tensor
        self._manager_ctx = manager_ctx
        self._deleter_callback = deleter_callback
        self._cleanup_done = False
        self._readonly = readonly

    @property
    def shape(self) -> tuple[int, ...]:
        """Shape as Python tuple."""
        return tuple(self._dl_tensor.shape[i] for i in range(self._dl_tensor.ndim))

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return self._dl_tensor.ndim

    @property
    def dtype(self):
        """Data type descriptor."""
        return self._dl_tensor.dtype

    @property
    def data(self) -> int:
        """Data pointer address."""
        return self._dl_tensor.data

    @property
    def device(self):
        """Device info."""
        return self._dl_tensor.device

    @property
    def raw_dltensor(self) -> DLTensor:
        """Access underlying DLTensor (advanced use)."""
        return self._dl_tensor

    def to_bytes(self) -> bytes:
        """Get pixel data as bytes (creates copy)."""
        size = self._calculate_byte_size()
        buffer = (ctypes.c_uint8 * size).from_address(self.data)
        return bytes(buffer)

    def _calculate_byte_size(self) -> int:
        """Calculate total buffer size in bytes."""
        total_elements = 1
        for dim in self.shape:
            total_elements *= dim
        bytes_per_element = (self.dtype.bits // 8) * self.dtype.lanes
        return total_elements * bytes_per_element

    def numpy(self) -> "numpy.ndarray":
        """Get NumPy array view of this tensor.

        Returns:
            NumPy ndarray view of the tensor data (zero-copy).

        Note:
            Writeability is controlled by the ``readonly`` flag passed to the
            ``ManagedDLTensor`` constructor, which sets the DLPack 1.0
            ``DLPACK_FLAG_BITMASK_READ_ONLY`` flag in the versioned capsule.

            **NumPy 2.1+ behavior:** Calls ``__dlpack__(max_version=(1, 0))``,
            receives versioned capsule with flags, and respects
            ``DLPACK_FLAG_BITMASK_READ_ONLY`` — the returned array is writeable
            only when the flag is not set.

            **NumPy <2.1 behavior:** Calls ``__dlpack__()`` without ``max_version``,
            receives legacy (unversioned) capsule, and always marks external
            buffers as read-only regardless of flags.
        """
        import numpy as np

        return np.from_dlpack(self)

    def __dlpack_device__(self) -> tuple[int, int]:
        """Return (device_type, device_id) tuple."""
        return (self._dl_tensor.device.device_type.value, self._dl_tensor.device.device_id)

    def __dlpack__(
        self,
        *,
        stream: Optional[int] = None,
        max_version: Optional[tuple[int, int]] = None,
        dl_device: Optional[tuple[int, int]] = None,
        copy: Optional[bool] = None,
    ) -> Any:
        """Create DLPack capsule for tensor exchange.

        Args:
            stream: CUDA stream hint from consumer. Accepted but ignored - caller
                is responsible for synchronization before accessing the data.
                Per DLPack: None=legacy, -1=no sync needed, 1=null stream,
                positive=actual stream handle.
            max_version: Maximum DLPack version supported by consumer, e.g. (1, 0)
            dl_device: Target device (not supported, must match tensor device)
            copy: Whether to copy data (not supported, must be None or False)

        Returns:
            PyCapsule containing DLManagedTensor or DLManagedTensorVersioned
        """
        # Note: stream parameter is accepted but ignored - we don't track which
        # stream produced the data. Caller must ensure proper synchronization.
        _ = stream

        if copy is True:
            raise BufferError("copy=True not supported")

        # Return versioned capsule when consumer supports same major and at least (1, 0). DLPack
        # minor version changes are ABI-compatible (same DLManagedTensorVersioned layout); only
        # major version changes the layout. Same major ensures the consumer can use our struct;
        # (1, 0) minimum ensures they support the versioned protocol. NumPy 2.1+ requests
        # max_version=(1, 0) and then respects the read-only flag; legacy capsules are read-only.
        use_versioned = max_version is not None and max_version[0] == DLPACK_MAJOR_VERSION and max_version >= (1, 0)

        # Wrap deleter_callback so that c_deleter's invocation marks _cleanup_done on this
        # ManagedDLTensor, preventing __del__ from re-invoking the callback.
        if self._deleter_callback is not None:
            original_cb = self._deleter_callback

            def wrapped_cb(ctx, _self=self, _cb=original_cb):
                _cb(ctx)
                _self._cleanup_done = True

        else:
            wrapped_cb = None

        return _to_dlpack_capsule(
            self._dl_tensor,
            self._manager_ctx,
            wrapped_cb,
            versioned=use_versioned,
            readonly=self._readonly,
        )

    def __del__(self):
        """Call cleanup callback on destruction."""
        if not self._cleanup_done and self._deleter_callback is not None:
            try:
                self._deleter_callback(self._manager_ctx)
                self._cleanup_done = True
            except Exception:
                pass

    def __repr__(self) -> str:
        return f"ManagedDLTensor(shape={self.shape}, dtype={self.dtype}, device={self.device})"
