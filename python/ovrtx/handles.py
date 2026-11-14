# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Dictionary and resource identities for the ovrtx bindings.

Keep handles typed through API calls, arrays, callbacks, and results. Handle
arguments require the matching type; plain integers and other handle kinds are
rejected with ``TypeError``. Construct the matching type from a raw uint64 only
at an explicit storage or interchange boundary. Use ``raw_id`` to extract that
number; ``int(handle)`` is not supported.

Handles identify objects within the scope defined by their API. Their kind and
raw ID do not prove ownership, liveness, or membership in a particular owner.
Copying a handle does not retain its resource or extend its lifetime.

Equality and hashing use the handle kind and raw ID. An invalid ``QueryHandle()``
differs from integer zero; compare it with ``ovrtx.INVALID_QUERY_HANDLE``.
For types with an invalid sentinel, ``bool(handle)`` checks only whether the
value differs from that sentinel. It does not establish resource liveness.
Resource and operation IDs also support same-kind ordering with ``<``.

``DataArrayLeaseId`` has no invalid sentinel: zero is a valid accessor-local
lease ID, and its truth value is always true.

Named invalid handles are shared ctypes objects for comparisons and value copies.
Never pass them as writable native output buffers, including via ``ctypes.byref()``:
native writes can mutate their storage despite Python attribute assignment guards.
Allocate a fresh ``QueryHandle()`` or copy the sentinel with
``QueryHandle(ovrtx.INVALID_QUERY_HANDLE)`` for an output argument.
"""

import ctypes
import operator


def _public_name(t):
    package = t.__module__.partition(".")[0]
    return t.__qualname__ if package == "builtins" else f"{package}.{t.__qualname__}"


class _Handle(ctypes.Structure):
    _fields_ = [("_value", ctypes.c_uint64)]
    _invalid = 0

    def __init__(self, value=0):
        if isinstance(value, _Handle):
            value = self._kind._require(value).raw_id
        if isinstance(value, bool):
            raise TypeError("a handle value must be an integer, not bool")
        value = operator.index(value)
        if not 0 <= value < 2**64:
            raise ValueError("a handle value must fit uint64")
        super().__init__()
        super().__setattr__("_value", value)

    @classmethod
    def _require(cls, value, name="handle"):
        if not isinstance(value, cls):
            raise TypeError(f"{name} must be {_public_name(cls)}, got {_public_name(type(value))}")
        return value

    @property
    def raw_id(self):
        """The raw uint64, for explicit storage/interchange conversions."""
        return self._value

    def __setattr__(self, name, value):
        if name in ("raw_id", "_value"):
            raise AttributeError("handle values cannot be assigned from Python")
        super().__setattr__(name, value)

    def __int__(self):
        # Without this guard, int() can parse the ctypes buffer as ASCII digits.
        raise TypeError("use .raw_id for explicit numeric conversion")

    def __bool__(self):
        return self.raw_id != self._invalid

    def __eq__(self, other):
        if not isinstance(other, _Handle) or self._kind is not other._kind:
            return NotImplemented
        return self.raw_id == other.raw_id

    def __hash__(self):
        return hash((self._kind, self.raw_id))

    def __repr__(self):
        return f"{self._kind.__name__}({self.raw_id})"

    def __copy__(self):
        return self._kind(self.raw_id)

    def __deepcopy__(self, memo):
        return self.__copy__()

    def __reduce__(self):
        return (self._kind, (self.raw_id,))


class Token(_Handle):
    """An interned string (ovx_token_t); zero is the valid empty token."""

    _invalid = 2**64 - 1


class PrimPath(_Handle):
    """An interned prim path (ovx_primpath_t); zero is invalid."""


class PrimPathList(_Handle):
    """A non-owning path-list handle (ovx_primpath_list_t); zero is invalid."""


Token._kind = Token
PrimPath._kind = PrimPath
PrimPathList._kind = PrimPathList


class _ResourceHandle(_Handle):
    """Typed resource identity; does not establish ownership or liveness."""

    def __lt__(self, other):
        if not isinstance(other, _ResourceHandle) or self._kind is not other._kind:
            return NotImplemented
        return self.raw_id < other.raw_id


class UsdHandle(_ResourceHandle):
    """Binding class for ``ovrtx_usd_handle_t``, identifying a USD reference added to a renderer, used to remove that
    reference.
    """


UsdHandle._kind = UsdHandle


class EventHandle(_ResourceHandle):
    """Binding class for ``ovrtx_event_handle_t``, identifying an event associated with a renderer."""


EventHandle._kind = EventHandle


class AttributeBindingHandle(_ResourceHandle):
    """Binding class for ``ovrtx_attribute_binding_handle_t``, identifying a persistent attribute binding created by a
    renderer.
    """


AttributeBindingHandle._kind = AttributeBindingHandle


class MapHandle(_ResourceHandle):
    """Binding class for ``ovrtx_map_handle_t``, identifying an attribute mapping on a renderer, used to unmap the
    mapped resource.
    """


MapHandle._kind = MapHandle


class StepResultHandle(_ResourceHandle):
    """Binding class for ``ovrtx_step_result_handle_t``, identifying the result of a renderer step, used to access that
    step's outputs.
    """


StepResultHandle._kind = StepResultHandle


class RenderVarOutputHandle(_ResourceHandle):
    """Binding class for ``ovrtx_render_var_output_handle_t``, identifying a rendered output of a renderer step, used to
    map its data.
    """


RenderVarOutputHandle._kind = RenderVarOutputHandle


class RenderVarOutputMapHandle(_ResourceHandle):
    """Binding class for ``ovrtx_render_var_output_map_handle_t``, identifying a mapping of a rendered output, used to
    unmap its data.
    """


RenderVarOutputMapHandle._kind = RenderVarOutputMapHandle


class OpId(_ResourceHandle):
    """Binding class for ``ovrtx_op_id_t``, identifying an asynchronous operation submitted to a renderer, used to poll
    or wait.
    """


OpId._kind = OpId


class QueryHandle(_ResourceHandle):
    """Binding class for ``ovrtx_query_handle_t``, identifying a prim query created by a renderer."""


QueryHandle._kind = QueryHandle


class ReadHandle(_ResourceHandle):
    """Binding class for ``ovrtx_read_handle_t``, identifying an attribute read on a renderer, used to fetch and release
    its result.
    """


ReadHandle._kind = ReadHandle


class DataProviderId(_ResourceHandle):
    """Binding class for ``ovrtx_data_provider_id_t``, identifying a process-local data-provider registration; copying
    it does not retain the provider.
    """


DataProviderId._kind = DataProviderId


class DataArrayLeaseId(_ResourceHandle):
    """Binding class for ``ovrtx_data_array_lease_id_t``, identifying an array borrow scoped to the accessor that
    granted it.

    Every uint64 value, including zero, can identify a lease; there is no invalid
    sentinel. ``bool(lease_id)`` is always true and does not establish that a lease
    was acquired or is live. Release each successful acquisition on its owning
    accessor; copying the ID does not acquire another borrow.
    """

    _invalid = None


DataArrayLeaseId._kind = DataArrayLeaseId


# Named sentinels retain the identity kind at checks and reset boundaries.
INVALID_USD_HANDLE = UsdHandle()
INVALID_EVENT_HANDLE = EventHandle()
INVALID_ATTRIBUTE_BINDING_HANDLE = AttributeBindingHandle()
INVALID_MAP_HANDLE = MapHandle()
INVALID_STEP_RESULT_HANDLE = StepResultHandle()
INVALID_RENDER_VAR_OUTPUT_HANDLE = RenderVarOutputHandle()
INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE = RenderVarOutputMapHandle()
INVALID_OP_ID = OpId()
INVALID_QUERY_HANDLE = QueryHandle()
INVALID_READ_HANDLE = ReadHandle()
INVALID_DATA_PROVIDER_ID = DataProviderId()
