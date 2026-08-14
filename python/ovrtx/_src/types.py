# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import sys
import warnings
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, TypeVar

from .bindings import (  # noqa: F401 — re-exported public API
    AttributeFilterMode,
    BindingFlag,
    DataAccess,
    Device,
    EventStatus,
    FilterKind,
    MotionBvh,
    PrimMode,
    SelectionFillMode,
    Semantic,
    TextureStreamingMode,
)
from .dlpack import DLPACK_MAJOR_VERSION, DLDataType, DLTensor, ManagedDLTensor, _to_dlpack_capsule
from .helpers import _deprecation_warnings_suppressed, deprecated

if TYPE_CHECKING:
    from .renderer import Renderer

T = TypeVar("T")
_BindingTensorT = TypeVar("_BindingTensorT")

_VOID_RESULT = True
"""Value returned by :meth:`Operation.wait` on success for void operations
(operations with no payload, such as ``remove_usd_async`` or ``reset_stage_async``).
``None`` still indicates timeout."""


_OVSTAGE_WRITE_REPLACEMENT = "Use ovstage.Stage.write_attribute() with a reusable ovstage query instead."
_OVSTAGE_MAP_REPLACEMENT = "Use ovstage.Stage.map_attribute() with a reusable ovstage query instead."
_OVSTAGE_UNMAP_REPLACEMENT = "Use ovstage.Map.unmap() or ovstage.Stage.unmap_attribute() instead."
_OVSTAGE_RELEASE_QUERY_REPLACEMENT = "Release the reusable ovstage query with Query.release() instead."


class Operation(Generic[T]):
    """Represents an enqueued async operation.

    ``None`` return means timeout; errors raise :class:`RuntimeError`.
    Void operations (no payload) return ``True`` on success.

    For simple operations (add_usd_reference, reset_stage), :meth:`wait` returns the
    result directly::

        op = renderer.add_usd_reference_async(path, "/World/Props")
        handle = op.wait()                           # infinite wait
        handle = op.wait(timeout_ns=0)               # poll, None = not ready
        handle = op.wait(timeout_ns=5_000_000_000)   # 5s, None = timed out

    For void operations (``Operation[bool]``), :meth:`wait` returns ``True``
    on success, ``None`` on timeout::

        op = renderer.reset_stage_async()
        if op.wait(timeout_ns=0):                    # True when complete
            print("reset done")
        else:
            print("still running (or timed out)")

    Fetchable operations (step, query, read) have a two-phase lifecycle:

    1. **Operation wait** — :meth:`wait` blocks until the enqueued GPU/CPU
       work completes (or times out). Returns a :class:`PendingFetch` on
       success, ``None`` on timeout.
    2. **Fetch** — :meth:`PendingFetch.fetch` retrieves the computed data
       (or times out). Returns the final result on success
       (:class:`QueryResult`, :class:`ReadResult`, etc.), ``None`` on timeout.

    Each phase has independent timeout control::

        op = renderer.step_async(...)
        pending = op.wait(timeout_ns=5_000_000_000)   # None = timed out
        result = pending.fetch(timeout_ns=100_000_000) # None = timed out
    """

    @dataclass
    class _Result:
        """Internal C wait result. Inferred status: errors imply failed, value None implies timeout, else completed."""

        value: Optional[Any]
        errors: list[str]

        @property
        def is_resolved(self) -> bool:
            return self.value is not None or bool(self.errors)

    @dataclass
    class _Ctx:
        """Phase context held during the C wait. Cleared after :meth:`wait` produces a value."""

        renderer: Any  # Renderer (avoids circular import)
        result: Optional["Operation._Result"] = None
        fetch_fn: Optional[Callable[[Optional[int]], Any]] = None
        cleanup_fn: Optional[Callable[[], None]] = None

    def __init__(
        self,
        renderer: "Renderer",
        op_id: int,
        handle: Any = None,
        operation_name: str = "",
        fetch_fn: Optional[Callable[[Any], T]] = None,
        cleanup_fn: Optional[Callable[[], None]] = None,
    ):
        self._op_id = op_id
        self._operation_name = operation_name
        self._ctx = Operation._Ctx(renderer=renderer, fetch_fn=fetch_fn, cleanup_fn=cleanup_fn)
        self._handle = handle
        self._pending_fetch: Optional[T] = None

    @property
    def op_id(self) -> int:
        """The operation ID."""
        return self._op_id

    def wait(self, timeout_ns: Optional[int] = None) -> Optional[T]:
        """Wait for operation to complete.

        Args:
            timeout_ns: Timeout in nanoseconds.
                None (default) = infinite wait,
                0 = non-blocking poll,
                >0 = wait for specified duration.

        Returns:
            :class:`PendingFetch` for fetchable operations (step, query, read),
            the operation's result value for simple operations (e.g. a USD
            handle from add_usd_reference), ``True`` for void operations (no payload),
            or ``None`` on timeout.

        Raises:
            RuntimeError: If operation failed.

        Note:
            ``None`` always indicates timeout — success always returns a non-``None`` value.
            Void operations return ``True`` on success so callers can distinguish
            completion from timeout with a simple truthiness check.

        Examples::

            # Fetchable operation (step, query, read) — wait returns PendingFetch
            op = renderer.step_async(...)
            pending = op.wait()           # PendingFetch[RenderProductSetOutputs]
            result = pending.fetch()      # RenderProductSetOutputs

            # Simple operation (add_usd_reference) — wait returns handle directly
            op = renderer.add_usd_reference_async(path, "/World/Props")
            handle = op.wait()            # USD handle (no fetch phase)

            # Void operation (reset_stage, write_attribute, ...) — wait returns True
            op = renderer.reset_stage_async()
            assert op.wait() is True

            # Polling with timeout
            pending = op.wait(timeout_ns=0)
            if pending is None:
                print("Not ready yet")
        """
        if self._pending_fetch is not None:
            return self._pending_fetch

        ctx = self._ctx
        if ctx.result is None or not ctx.result.is_resolved:
            ctx.result = ctx.renderer._wait_operation(self, timeout_ns)

        if ctx.result.errors:
            error_msg = "\n  ".join(ctx.result.errors)
            raise RuntimeError(f"Operation '{self._operation_name}' failed:\n  {error_msg}")

        if ctx.result.value is None:
            return None

        self._pending_fetch = PendingFetch(ctx.fetch_fn) if ctx.fetch_fn else ctx.result.value
        self._ctx = None  # phase complete — release all wait-phase context
        return self._pending_fetch

    def query_status(self) -> "OperationStatus":
        """Query the current progress of this operation.

        Returns a point-in-time snapshot. The returned :class:`OperationStatus`
        is a plain dataclass with no C resources attached.
        """
        if self._ctx is None:
            raise RuntimeError("Operation already completed — query_status is no longer available")
        return self._ctx.renderer._query_op_status(self._op_id)

    def __del__(self):
        """Warn and block if operation was never waited on."""
        # Already consumed (wait succeeded) or already cleaned up — nothing to do
        if self._pending_fetch is not None or self._ctx is None:
            return
        warnings.warn(
            f"Operation '{self._operation_name}' (op_id={self._op_id}) was garbage-collected "
            f"without wait(). Blocking until completion to prevent use-after-free.",
            ResourceWarning,
            stacklevel=1,
        )
        ctx = self._ctx
        # Block until the C operation completes (keeps _storage_refs alive)
        try:
            ctx.result = ctx.renderer._wait_operation(self, None)
        except Exception:
            pass
        # Release the C result handle (step/query/read) to prevent leaks
        if ctx.cleanup_fn is not None:
            try:
                ctx.cleanup_fn()
            except Exception:
                pass

    def __repr__(self) -> str:
        if self._pending_fetch is not None:
            return f"Operation({self._operation_name}, op_id={self._op_id}, completed)"
        if self._ctx is None:
            return f"Operation({self._operation_name}, op_id={self._op_id}, consumed)"
        r = self._ctx.result
        if r is None:
            label = "pending"
        elif r.errors:
            label = "failed"
        else:
            label = "pending" if r.value is None else "completed"
        return f"Operation({self._operation_name}, op_id={self._op_id}, {label})"


class PendingFetch(Generic[T]):
    """Phase 2 of a fetchable operation's lifecycle (see :class:`Operation`).

    Returned by :meth:`Operation.wait` after the enqueued work completes.
    Call :meth:`fetch` to retrieve the final result (e.g. :class:`QueryResult`,
    :class:`ReadResult`, :class:`RenderProductSetOutputs`).

    The fetch is stream-ordered — it may block waiting for prior GPU work
    in the stream to drain, independently of the operation wait timeout.

    If garbage-collected without :meth:`fetch`, forces a blocking fetch
    with a :class:`ResourceWarning` to prevent C resource leaks.
    """

    def __init__(self, fetch_fn: Callable[[Optional[int]], Optional[T]]):
        self._fetch_fn = fetch_fn
        self._result: Optional[T] = None
        self._fetched = False

    def fetch(self, timeout_ns: Optional[int] = None) -> Optional[T]:
        """Fetch the result data.

        Idempotent — subsequent calls return the cached result.

        Args:
            timeout_ns: Fetch timeout in nanoseconds. None = infinite (default).

        Returns:
            The final result, or None on timeout.
        """
        if self._fetched:
            return self._result
        self._result = self._fetch_fn(timeout_ns)
        if self._result is not None:
            self._fetched = True
            self._fetch_fn = None  # phase complete — release fetch context
        return self._result

    def __del__(self):
        if not self._fetched:
            warnings.warn(
                "PendingFetch was garbage-collected without fetch(). Blocking to free C resources.",
                ResourceWarning,
                stacklevel=1,
            )
            try:
                self.fetch()
            except Exception:
                pass

    def __repr__(self) -> str:
        if self._fetched:
            return f"PendingFetch(fetched={type(self._result).__name__})"
        return "PendingFetch(pending)"


class _UnmapState:
    """Shared unmap bookkeeping, held by both ``MappedRenderVar`` and ``Renderer._live_mappings``.

    Holds only plain data and deliberately keeps **no** reference to the ``Renderer``
    (not even a bound method): this state lives in ``Renderer._live_mappings``, so any
    renderer reference stored here would close a ``Renderer -> registry -> state ->
    Renderer`` cycle and, because ``Renderer`` defines ``__del__``, defer its teardown to
    a cyclic GC pass. ``Renderer._force_unmap_all`` performs the C unmap using the renderer
    it is already a method of.

    Coordinates two concerns between ``MappedRenderVar.__del__`` and
    ``Renderer._force_unmap_all`` (whichever fires first):
    1. Double-unmap prevention — ``unmapped`` flag; the second one to run sees it set and skips.
    2. CUDA sync hint passing — ``unmap(stream=...)`` records the sync params here so a
       later force-unmap on renderer teardown honors them.
    """

    __slots__ = ("unmapped", "cuda_sync")

    def __init__(self):
        self.unmapped = False
        self.cuda_sync = None


class MappedRenderVar:
    """One mapped render variable: named tensors, named params, and the render variable's
    description fields (:attr:`name`, :attr:`type`, :attr:`doc`, :attr:`version`).

    Returned by :meth:`RenderVarOutput.map`. A render variable that carries a
    single tensor exposes it via the DLPack protocol on the mapping itself
    (``np.from_dlpack(rv)``); one with multiple tensors exposes them via a
    dict protocol (``rv["tensor_name"]``). Param values are reached via
    :attr:`params`.

    **Lifetime.** Use either the context-manager form or a direct
    :meth:`unmap` call to signal that you are done. The underlying buffer
    stays valid for as long as anything you derived from it is still in
    use — a NumPy or Warp array, a DLPack capsule, a tensor or param
    obtained from this mapping. You do not need to manage that explicitly.

    After :meth:`unmap` (or ``__exit__``) has run, requesting a *new*
    tensor or param from this mapping raises :class:`RuntimeError`.
    Tensors and params obtained earlier — and any arrays already minted
    from them — remain readable.

    **GPU mappings.** The producer's CUDA work may still be in flight when
    :meth:`map` returns. Reading tensor data before :attr:`wait_event` has
    fired is a race — the access sees uninitialized or stale memory. Use
    exactly one of the patterns below to enforce ordering:

    1. **Auto-barrier on a stream you'll use** — pass
       ``sync_stream=your_stream`` to :meth:`map` and then queue your
       downstream kernel on ``your_stream``. ovrtx inserts
       ``cudaStreamWaitEvent(your_stream, wait_event)`` for you, so the
       kernel observes the barrier; the data is *not* valid for any access
       on a different stream or on the CPU under this pattern.
    2. **Explicit stream-ordered wait** — call
       :meth:`wait_on` ``(your_stream)`` and then queue your downstream
       kernel on ``your_stream``. Same effect as (1); use this when the
       consumer stream is chosen after :meth:`map` time, or when no
       ``sync_stream`` was passed.
    3. **Explicit CPU-block** — call :meth:`wait`. The calling thread
       blocks until ``wait_event`` fires; after it returns, the data is
       valid for any subsequent access (CPU read, fresh kernel launch on
       any stream, etc.).

    CPU mappings (``device=Device.CPU``) are always valid on map return;
    :meth:`wait` and :meth:`wait_on` are silent no-ops in that case
    (:attr:`wait_event` is ``None``).

    Usage::

        # Context-manager form.
        with render_var.map(device=Device.CUDA) as rv:
            arr = wp.from_dlpack(rv)            # single-tensor render variable
        do_work(arr)                            # consumer view still valid

        # Multi-tensor render variable: dict access by tensor name.
        with render_var.map(device=Device.CPU) as rv:
            coords = np.from_dlpack(rv["Coordinates"])
            frame_id = int(np.from_dlpack(rv.params["frameId"]))

        # Direct map / unmap.
        rv = render_var.map(device=Device.CUDA)
        arr = wp.from_dlpack(rv)
        rv.unmap(stream=cuda_stream)            # release with a sync hint
        do_work(arr)
    """

    class _DLPackable:
        """Internal mix-in: provides the DLPack protocol methods to view classes.

        Subclasses must expose ``_dl`` (the underlying ``DLTensor``) and
        ``_parent`` (the :class:`MappedRenderVar` that owns the buffer).
        Adds no slots and no ``__init__``.
        """

        __slots__ = ()

        def __dlpack_device__(self) -> tuple[int, int]:
            device = self._dl.device
            return (device.device_type.value, device.device_id)

        def __dlpack__(
            self,
            *,
            stream: Optional[int] = None,
            max_version: Optional[tuple[int, int]] = None,
            dl_device: Optional[tuple[int, int]] = None,
            copy: Optional[bool] = None,
        ) -> Any:
            _ = stream  # synchronization is the caller's responsibility
            if copy is True:
                raise BufferError("copy=True not supported")
            use_versioned = max_version is not None and max_version[0] == DLPACK_MAJOR_VERSION and max_version >= (1, 0)
            return _to_dlpack_capsule(
                self._dl,
                self._parent,
                None,
                versioned=use_versioned,
                readonly=True,
            )

    @dataclass(slots=True, frozen=True)
    class _RenderVarRecord:
        """Internal: per-tensor or per-param record on a :class:`MappedRenderVar`.

        Holds the decoded ``name`` / ``doc`` strings (Python ``str``) and the
        by-value ``DLTensor`` snapshot. The ``DLTensor`` pointer fields reference
        C-side memory whose lifetime is tied to the parent mapping's ``map_handle``.
        """

        name: str
        doc: str
        dl: DLTensor

    def __init__(
        self,
        *,
        renderer: "Renderer",
        map_handle: int,
        device: Device,
        name: str,
        type: str,
        doc: str,
        version: int,
        tensors: list,
        params: list,
        wait_event: Optional[int] = None,
    ):
        """Internal: constructed by :meth:`Renderer._map_output` after decoding the C struct.

        ``tensors`` and ``params`` are lists of ``(name: str, doc: str, dl: DLTensor)``
        triples — the C-side ``ovx_string_t`` fields decoded to Python ``str`` and the
        ``DLTensor`` structs copied by value (their inner pointers still reference
        C-side memory tied to ``map_handle``).

        ``wait_event`` is the producer-done CUDA event handle for GPU mappings, or
        ``None`` for CPU mappings (and any GPU mapping where every tensor is CPU-
        resident — the C side already CPU-blocked + copied).
        """
        self._renderer = renderer
        self._map_handle = map_handle
        self._device = device
        self._cuda_sync = None
        self._wait_event = wait_event
        self._unmapped = False  # set once the user has called unmap() / __exit__
        self._render_var: Optional["RenderVarOutput"] = None  # set by RenderVarOutput.map() post-construction

        # Cycle-free registry entry shared with Renderer._live_mappings (keyed by
        # ``map_handle``); see :class:`_UnmapState` for why it stores no renderer reference.
        # ``self._renderer`` above is an intentional one-way pin (keeps the buffer valid while
        # any derived view is alive); it does not close a cycle because the renderer registers
        # this plain state, not this MappedRenderVar.
        self._unmap_state = _UnmapState()
        renderer._register_mapping(map_handle, self._unmap_state)

        # Render variable description fields (plain instance attributes — opaque strings + int).
        self.name = name
        self.type = type
        self.doc = doc
        self.version = version

        # Records keyed by name. Records do not reference the parent, so storing
        # them on `self` is cycle-free. Insertion order matches declaration order
        # (Python 3.7+ dict guarantee), which is what the iter / values / items
        # protocols below rely on. Both RenderVarTensor and RenderVarParam
        # wrappers are minted on demand (by __getitem__ / the params property);
        # those wrappers hold the parent strongly, which keeps the reference
        # graph cycle-free as long as the parent does not hold the wrappers.
        self._tensors: dict[str, MappedRenderVar._RenderVarRecord] = {
            n: MappedRenderVar._RenderVarRecord(n, d, dl) for (n, d, dl) in tensors
        }
        self._params: dict[str, MappedRenderVar._RenderVarRecord] = {
            n: MappedRenderVar._RenderVarRecord(n, d, dl) for (n, d, dl) in params
        }

    @property
    def device(self) -> Device:
        """Device this render variable's tensors are mapped to (params are always CPU)."""
        return self._device

    @property
    def params(self) -> dict[str, "RenderVarParam"]:
        """``{name: RenderVarParam}`` dict for this render variable's params (always CPU).

        Each access returns a new dict of new :class:`RenderVarParam`
        instances over the same underlying data — no copy of the param
        buffers is performed (the data itself is shared).

        Raises:
            RuntimeError: If accessed after :meth:`unmap`.
        """
        self._require_mapped()
        return {name: RenderVarParam(parent=self, record=rec) for name, rec in self._params.items()}

    @property
    def tensor(self) -> ManagedDLTensor:
        """Deprecated. Returns the sole tensor of a single-tensor render variable as a :class:`ManagedDLTensor`.

        Emits :class:`DeprecationWarning`. Raises if this render variable
        carries multiple tensors or none.

        Prefer ``np.from_dlpack(rv)`` for a single-tensor render variable and
        ``rv["<name>"]`` when there are multiple tensors. The returned
        :class:`ManagedDLTensor` preserves the historical signature of this
        accessor — its ``.numpy()``, ``.to_bytes()``, ``.data``, ``.shape``,
        ``.dtype``, etc. continue to work as before, and the underlying
        buffer's lifetime is tied to this mapping for as long as any view
        you minted from it is alive.
        """
        self._require_mapped()
        n = len(self._tensors)
        if n == 0:
            raise RuntimeError(
                f"Render variable '{self.name}' has no tensors; use rv.params for params-only render variables"
            )
        if n > 1:
            raise RuntimeError(
                f"Render variable '{self.name}' has multiple tensors ({n}: {list(self._tensors)}); "
                f"use rv['<tensor_name>'] (or np.from_dlpack(rv['<tensor_name>']))."
            )
        if not _deprecation_warnings_suppressed(self):
            warnings.warn(
                ".tensor is deprecated for single-tensor render variables; use the mapping directly: "
                "np.from_dlpack(rv). Will be removed in a later release.",
                DeprecationWarning,
                stacklevel=2,
            )
        rec = next(iter(self._tensors.values()))
        return ManagedDLTensor(rec.dl, manager_ctx=self, deleter_callback=None, readonly=True)

    def __dlpack_device__(self) -> tuple[int, int]:
        """Return ``(device_type, device_id)`` for the sole tensor.

        Only valid on a single-tensor render variable; raises if the render
        variable carries multiple tensors or none.
        """
        device = self._require_uniform("__dlpack_device__").dl.device
        return (device.device_type.value, device.device_id)

    def __dlpack__(
        self,
        *,
        stream: Optional[int] = None,
        max_version: Optional[tuple[int, int]] = None,
        dl_device: Optional[tuple[int, int]] = None,
        copy: Optional[bool] = None,
    ) -> Any:
        """Mint a DLPack capsule for the sole tensor.

        Only valid on a single-tensor render variable; raises if the render
        variable carries multiple tensors or none. For multi-tensor render
        variables, use ``rv["<tensor_name>"]``; for a render variable with
        only params, use ``rv.params``.
        """
        rec = self._require_uniform("__dlpack__")
        _ = stream
        if copy is True:
            raise BufferError("copy=True not supported")
        use_versioned = max_version is not None and max_version[0] == DLPACK_MAJOR_VERSION and max_version >= (1, 0)
        return _to_dlpack_capsule(
            rec.dl,
            self,
            None,
            versioned=use_versioned,
            readonly=True,
        )

    def __getitem__(self, key: str) -> "RenderVarTensor":
        """Return the :class:`RenderVarTensor` for the named tensor.

        Each call returns a new :class:`RenderVarTensor` over the same
        underlying data — accessing a name twice does not copy or duplicate
        the buffer (no identity guarantee across calls; the data itself is
        shared).

        Raises:
            KeyError: If this render variable has no tensor with this name.
            RuntimeError: If accessed after :meth:`unmap`.
        """
        self._require_mapped()
        rec = self._tensors.get(key)
        if rec is None:
            raise KeyError(
                f"Render variable '{self.name}' has no tensor named {key!r}; " f"available: {list(self._tensors)}"
            )
        return RenderVarTensor(parent=self, record=rec)

    def __contains__(self, key: object) -> bool:
        return key in self._tensors

    def __iter__(self):
        """Iterate tensor names in declaration order."""
        return iter(self._tensors)

    def __len__(self) -> int:
        """Number of tensors in this render variable."""
        return len(self._tensors)

    def keys(self):
        """Tensor names."""
        return self._tensors.keys()

    def values(self):
        """Iterator of :class:`RenderVarTensor` in declaration order."""
        return (RenderVarTensor(parent=self, record=rec) for rec in self._tensors.values())

    def items(self):
        """Iterator of ``(name, RenderVarTensor)`` pairs in declaration order."""
        return ((name, RenderVarTensor(parent=self, record=rec)) for name, rec in self._tensors.items())

    @property
    def wait_event(self) -> Optional[int]:
        """Producer-done CUDA event handle, or ``None`` if no wait is needed.

        ``None`` for CPU mappings and for any GPU mapping whose tensors all
        landed on the CPU (the C side already CPU-blocked + copied). For
        GPU-resident tensors, this is the event the consumer must observe
        before reading — see the class docstring for the three usage patterns.
        """
        return self._wait_event

    def wait(self) -> None:
        """Block the calling thread until :attr:`wait_event` has fired.

        Silent no-op when :attr:`wait_event` is ``None``. After this returns,
        the data is valid for any subsequent access.
        """
        if self._wait_event is None:
            return
        from . import cudart

        cudart.event_synchronize(self._wait_event)

    def wait_on(self, stream: int) -> None:
        """Insert a wait barrier into ``stream`` against :attr:`wait_event`.

        Silent no-op when :attr:`wait_event` is ``None``. Does not CPU-block.
        Any kernel queued on ``stream`` after this call observes the producer
        as done.

        Args:
            stream: CUDA stream handle (integer). May be on any device — the
                runtime handles cross-context bookkeeping.
        """
        if self._wait_event is None:
            return
        from . import cudart

        cudart.stream_wait_event(stream, self._wait_event)

    def unmap(self, event: Optional[int] = None, stream: Optional[int] = None) -> None:
        """Release interest in this mapping. Idempotent.

        Subsequent attempts to mint *new* views on this mapping (``rv["X"]``,
        ``np.from_dlpack(rv)``) raise :class:`RuntimeError`. Views minted
        earlier remain readable, and the buffer stays alive while any of them
        are still referenced. The originating :class:`RenderVarOutput` is
        immediately remappable.

        Args:
            event: Optional CUDA event handle to wait on before the buffer is
                eventually released. Mutually exclusive with ``stream``.
                Not accepted for CPU-mapped outputs.
            stream: Optional CUDA stream handle to synchronize before the
                buffer is eventually released. Mutually exclusive with
                ``event``. Not accepted for CPU-mapped outputs.

        Raises:
            ValueError: If ``event`` or ``stream`` is provided for a
                CPU-mapped output, or if both are provided together.

        Note:
            First call wins — subsequent calls are no-ops, and any sync hint
            recorded by the first call is preserved. ``__exit__`` of a ``with``
            block is equivalent to calling :meth:`unmap` with no sync args.
        """
        if self._unmapped:
            return  # idempotent — first call wins

        if self._device == Device.CPU and (event is not None or stream is not None):
            raise ValueError("CUDA sync parameters (event/stream) not applicable for CPU-mapped outputs")

        if event is not None and stream is not None:
            raise ValueError("Cannot specify both event and stream; use one or the other")

        if event is not None or stream is not None:
            from . import bindings

            cuda_sync = bindings.ovrtx_cuda_sync_t()
            if stream is not None:
                cuda_sync.stream = stream
            if event is not None:
                cuda_sync.wait_event = event
            self._cuda_sync = cuda_sync
            # Mirror onto the registered _UnmapState so _force_unmap_all sees the same
            # sync hint if it ends up firing the C unmap on renderer teardown.
            self._unmap_state.cuda_sync = cuda_sync

        self._unmapped = True

        # Clear the originating output's re-map gate at the user-release point.
        # The C unmap is still deferred until the last consumer capsule drops, but
        # the user has signaled "done with active interest", so a fresh map() on the
        # same RenderVarOutput is allowed even while old buffers stay alive in
        # capsules. __del__ only re-clears the gate on the never-released path.
        if self._render_var is not None:
            self._render_var._map_handle = None

    def __enter__(self) -> "MappedRenderVar":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.unmap()
        return False

    def __del__(self) -> None:
        """Release the underlying buffer when the last reference is dropped.

        Idempotent: if cleanup already ran (e.g. the renderer was torn down
        and force-released this mapping first), this is a no-op. Skips the
        underlying C call when the renderer has already been destroyed, so
        a mapping outliving its renderer collects cleanly. As a fallback for
        instances dropped without an explicit :meth:`unmap` or ``__exit__``,
        also resets the originating output's re-map gate so the same
        :class:`RenderVarOutput` can be mapped again.
        """
        state = self._unmap_state
        if state.unmapped:
            return
        state.unmapped = True
        # Fallback gate-clear for the never-released path. If unmap() ran earlier
        # the gate was already cleared (and possibly already re-set by a fresh
        # map() on the same RenderVarOutput), so don't touch it.
        if not self._unmapped and self._render_var is not None:
            try:
                self._render_var._map_handle = None
            except Exception:
                pass
        renderer = self._renderer
        if renderer is not None and renderer._handle is not None:
            try:
                from . import bindings

                cuda_sync = self._cuda_sync if self._cuda_sync is not None else bindings.ovrtx_cuda_sync_t()
                renderer._unmap_output(self._map_handle, cuda_sync)
            except Exception:
                pass
            try:
                renderer._deregister_mapping(self._map_handle)
            except Exception:
                pass

    # --- helpers -----------------------------------------------------------------------

    def _require_mapped(self) -> None:
        if self._unmapped:
            raise RuntimeError(f"Mapping for '{self.name}' already released")

    def _require_uniform(self, op: str) -> "MappedRenderVar._RenderVarRecord":
        """Validate that this render variable carries exactly one tensor and return its record.

        Shared by ``__dlpack__`` / ``__dlpack_device__`` / ``tensor``.
        """
        self._require_mapped()
        n = len(self._tensors)
        if n == 0:
            raise RuntimeError(
                f"Render variable '{self.name}' has no tensors; {op} requires a single-tensor render variable "
                f"(use rv.params for params-only render variables)"
            )
        if n > 1:
            raise RuntimeError(
                f"Render variable '{self.name}' has multiple tensors ({n}: {list(self._tensors)}); "
                f"{op} requires a single-tensor render variable (use rv['<tensor_name>'] to access a specific tensor)"
            )
        return next(iter(self._tensors.values()))

    def __repr__(self) -> str:
        state = "unmapped" if self._unmapped else "mapped"
        return (
            f"MappedRenderVar(name={self.name!r}, type={self.type!r}, "
            f"num_tensors={len(self._tensors)}, num_params={len(self._params)}, "
            f"device={self._device.name}, {state})"
        )


class RenderVarTensor(MappedRenderVar._DLPackable):
    """One named tensor from a mapped render variable.

    Returned by ``rv["<name>"]``. Implements the DLPack protocol so consumers
    can do ``np.from_dlpack(rv["Coordinates"])`` directly. Exposes the
    tensor's :attr:`name`, :attr:`doc`, :attr:`shape`, :attr:`dtype`,
    :attr:`device`, and :attr:`ndim`.

    Safe to keep around past the originating ``with`` block or a
    :meth:`MappedRenderVar.unmap` call — the underlying buffer remains valid
    until both this object and any arrays minted from it have been dropped.
    """

    __slots__ = ("_parent", "_record")

    def __init__(self, parent: "MappedRenderVar", record: "MappedRenderVar._RenderVarRecord"):
        """Internal: constructed by :meth:`MappedRenderVar.__getitem__`."""
        self._parent = parent
        self._record = record

    @property
    def _dl(self) -> DLTensor:
        return self._record.dl

    @property
    def name(self) -> str:
        """Tensor name, e.g. ``"Coordinates"``, ``"Intensity"``."""
        return self._record.name

    @property
    def doc(self) -> str:
        """Human-readable description of the tensor (may be empty)."""
        return self._record.doc

    @property
    def shape(self) -> tuple:
        """Tensor shape as a tuple of ints (read from the live DLTensor)."""
        dl = self._record.dl
        return tuple(dl.shape[i] for i in range(dl.ndim))

    @property
    def dtype(self) -> DLDataType:
        """DLPack data type descriptor."""
        return self._record.dl.dtype

    @property
    def device(self):
        """DLPack device descriptor."""
        return self._record.dl.device

    @property
    def ndim(self) -> int:
        """Tensor rank."""
        return self._record.dl.ndim

    def __repr__(self) -> str:
        return f"RenderVarTensor(name={self._record.name!r}, shape={self.shape}, dtype={self.dtype})"


class RenderVarParam(MappedRenderVar._DLPackable):
    """One named param value from a mapped render variable. Always CPU-resident.

    Returned by ``rv.params["<name>"]``. Implements the DLPack protocol so
    consumers can do ``np.from_dlpack(rv.params["frameId"])`` directly.
    Exposes the param's :attr:`name`, :attr:`doc`, :attr:`shape`,
    :attr:`dtype`, :attr:`device`, and :attr:`ndim`.

    Safe to keep around past the originating ``with`` block or a
    :meth:`MappedRenderVar.unmap` call — same lifetime contract as
    :class:`RenderVarTensor`.
    """

    __slots__ = ("_parent", "_record")

    def __init__(self, parent: "MappedRenderVar", record: "MappedRenderVar._RenderVarRecord"):
        """Internal: constructed by :attr:`MappedRenderVar.params`."""
        self._parent = parent
        self._record = record

    @property
    def _dl(self) -> DLTensor:
        return self._record.dl

    @property
    def name(self) -> str:
        """Param name, e.g. ``"frameId"``, ``"timestampNs"``."""
        return self._record.name

    @property
    def doc(self) -> str:
        """Human-readable description of the param (may be empty)."""
        return self._record.doc

    @property
    def shape(self) -> tuple:
        """Param shape as a tuple of ints (scalar params have shape ``()``)."""
        dl = self._record.dl
        return tuple(dl.shape[i] for i in range(dl.ndim))

    @property
    def dtype(self) -> DLDataType:
        """DLPack data type descriptor."""
        return self._record.dl.dtype

    @property
    def device(self):
        """DLPack device descriptor (always CPU for params)."""
        return self._record.dl.device

    @property
    def ndim(self) -> int:
        """Param rank."""
        return self._record.dl.ndim

    def __repr__(self) -> str:
        return f"RenderVarParam(name={self._record.name!r}, shape={self.shape}, dtype={self.dtype})"


class RenderVarOutput(Generic[T]):
    """Single render variable output, fetched as part of a :class:`RenderProductSetOutputs`.

    Use :meth:`map` to obtain a :class:`MappedRenderVar` exposing the render
    variable's tensors and params via DLPack.

    Example::

        with render_var.map(device=Device.CUDA) as rv:
            arr = wp.from_dlpack(rv)            # single-tensor render variable
            wp.launch(my_kernel, inputs=[arr])
    """

    def __init__(
        self,
        name: str,
        handle: T,
        renderer: "Renderer",
    ):
        """Internal: created by :meth:`Renderer._fetch_results`."""
        self.name = name
        self.handle = handle
        self._renderer = renderer
        self._map_handle: Any = None  # set while a mapping is outstanding; gates re-map

    def map(self, device: Device = Device.CPU, sync_stream: Optional[int] = None) -> "MappedRenderVar":
        """Map this render variable output and return a :class:`MappedRenderVar`.

        Use either the context-manager form (``with ... as rv:``) or the
        direct form (``rv = ...; rv.unmap()``); they are equivalent. See
        :class:`MappedRenderVar` for the full usage surface.

        Args:
            device: Target device (:attr:`Device.CPU` or :attr:`Device.CUDA`).
            sync_stream: Optional CUDA stream handle. When provided, the
                stream waits for render completion before subsequent work
                runs on it. Default: 1 for CUDA (default stream), 0 for CPU.

        Returns:
            A :class:`MappedRenderVar` exposing the render variable's tensors,
            params, and description fields.

        Raises:
            RuntimeError: If mapping fails or this output is already mapped
                (call :meth:`MappedRenderVar.unmap` on the prior mapping
                first).
        """
        if self._map_handle is not None:
            raise RuntimeError(f"Render var '{self.name}' already mapped")

        rv = self._renderer._map_output(self.handle, device_type=device, sync_stream=sync_stream)
        self._map_handle = rv._map_handle
        # Back-reference so MappedRenderVar.__del__ can re-open this output for
        # re-mapping after its C unmap fires (clears self._map_handle).
        rv._render_var = self
        return rv

    def __repr__(self) -> str:
        status = "mapped" if self._map_handle else "unmapped"
        return f"RenderVarOutput(name='{self.name}', {status})"


@dataclass
class FrameOutput(Generic[T]):
    """Single frame with multiple render variables."""

    start_time: float
    """Sensor simulation time at frame start, in seconds.

    Accumulated from ``delta_time`` values passed to :meth:`Renderer.step`.
    Epoch is 0.0 at renderer creation and after :meth:`reset_stage`;
    set to *time* after :meth:`reset(time=...) <Renderer.reset>`.
    """
    end_time: float
    """Sensor simulation time at frame end, in seconds (``start_time + delta_time``)."""
    render_vars: dict[str, RenderVarOutput[T]]
    progression: int = 0
    """Path-tracing sample accumulation progress for this render product frame.

    Increases with each time an output is rendered to in a call to :meth:`Renderer.step`.
    Resets after :meth:`Renderer.reset`, or when internal conditions invalidate the current 
    accumulation state (ex: scene changes, camera movement, etc.)
    """
    converged: bool = False
    """True when the path tracer has reached the ``omni:rtx:pt:samplesPerPixel`` stop criterion.

    Once ``True``, additional :meth:`Renderer.step` calls will not result in additional
    sample accumulation until :meth:`Renderer.reset` is called or the scene changes. Always ``False`` 
    for non-PT render modes.
    """


@dataclass
class ProductOutput(Generic[T]):
    """Single render product with multiple frames."""

    name: str
    frames: list[FrameOutput[T]]


class RenderProductSetOutputs(Generic[T]):
    """Dict-like container for rendering results from a step operation.

    Acts as a dictionary mapping render product paths to ProductOutput instances.

    Example::

        # Dict-like iteration
        products = renderer.step(...)
        for product_name, product in products.items():
            for frame in product.frames:
                for var_name, render_var in frame.render_vars.items():
                    mapping = render_var.map()
                    # Process mapping.tensor...

        # Dict-like indexing
        product = products["/Render/Product0"]

        # Membership test
        if "/Render/Product0" in products:
            ...
    """

    def __init__(
        self,
        destroy_fn: Callable[[], None],
        products: dict[str, ProductOutput[T]],
    ):
        """Internal: Created by Renderer._fetch_results().

        Args:
            destroy_fn: Callable that releases C step result resources.
            products: Parsed product outputs keyed by render product name
        """
        self._destroy_fn = destroy_fn
        self._outputs = products

    # Dict-like protocol
    def __getitem__(self, key: str) -> ProductOutput[T]:
        """Get product by render product path."""
        try:
            return self._outputs[key]
        except KeyError:
            available = "\n  ".join(sorted(self._outputs.keys()))
            raise KeyError(f"No product '{key}'. Available products:\n  {available}") from None

    def __iter__(self):
        """Iterate over render product paths."""
        return iter(self._outputs)

    def __len__(self) -> int:
        """Number of render products."""
        return len(self._outputs)

    def __contains__(self, key: str) -> bool:
        """Check if render product path exists."""
        return key in self._outputs

    def keys(self):
        """Get all render product paths."""
        return self._outputs.keys()

    def values(self):
        """Get all ProductOutput instances."""
        return self._outputs.values()

    def items(self):
        """Get all (path, ProductOutput) pairs."""
        return self._outputs.items()

    def __del__(self):
        """Auto-cleanup on garbage collection.

        Releases the step result handle. The lifetime of render variable
        mappings and any DLPack views derived from them is independent of
        this call — they are released when their own ``unmap`` fires (via
        the mapping's own deleter chain).
        """
        try:
            self._destroy_fn()
        except Exception as e:
            print(f"Warning: Exception during RenderProductSetOutputs cleanup in __del__: {e}", file=sys.stderr)

    def __repr__(self) -> str:
        return f"RenderProductSetOutputs({list(self._outputs.keys())})"


class AttributeBinding(Generic[_BindingTensorT]):
    """Persistent attribute binding for efficient repeated writes or maps.

    Created by ``Renderer.bind_attribute()`` or
    ``Renderer.bind_array_attribute()``. Reuse for multiple write operations
    to avoid recreating the binding descriptor.

    ``write()`` accepts NumPy arrays, Warp arrays, or any
    ``__dlpack__``-compatible object. For string bindings, pass ``list[str]``
    (scalar) or ``list[list[str]]`` (array).

    Example (scalar):
        ```python
        import numpy as np

        binding = renderer.bind_attribute(
            ["/World/Cube"], "xformOp:transform",
            dtype="float64", shape=(4, 4))
        binding.write(np.eye(4, dtype=np.float64).reshape(1, 4, 4))
        binding.unbind()
        ```

    Example (array):
        ```python
        import numpy as np

        binding = renderer.bind_array_attribute(
            ["/World/Mesh1", "/World/Mesh2"], "faceVertexCounts",
            dtype="int32")
        binding.write([np.array([4, 4], dtype=np.int32), np.array([3, 3, 3], dtype=np.int32)])
        binding.unbind()
        ```
    """

    def __init__(
        self,
        handle: int,
        semantic: int,
        dtype: DLDataType,
        renderer: "Renderer",
        is_array: bool = False,
        shape: "Optional[tuple]" = None,
    ):
        """Initialize attribute binding (internal use - created by Renderer.bind_attribute).

        Args:
            handle: Raw C binding handle value
            semantic: Semantic constant (OVRTX_SEMANTIC_*)
            dtype: Expected DLDataType for tensors used with this binding
            renderer: Renderer instance that created this binding
            is_array: True if this binding is for array attributes
            shape: Optional element shape from the dtype/shape API, stored for map output reshaping
        """
        import weakref

        self._handle = handle
        self._semantic = semantic
        self._dtype = dtype
        self._renderer = weakref.ref(renderer)
        self._is_array = is_array
        self._shape = shape

    def _get_renderer(self) -> "Renderer":
        """Get renderer, raising if it has been destroyed."""
        renderer = self._renderer()
        if renderer is None:
            raise RuntimeError("Renderer has been destroyed")
        return renderer

    @property
    def handle(self) -> int:
        """Raw C binding handle value."""
        return self._handle

    @property
    def semantic(self) -> int:
        """Semantic constant (OVRTX_SEMANTIC_*) for tensor reshaping."""
        return self._semantic

    @property
    def dtype(self) -> DLDataType:
        """Expected DLDataType for tensors used with this binding."""
        return self._dtype

    @property
    def is_array(self) -> bool:
        """True if this binding is for array attributes."""
        return self._is_array

    @property
    def shape(self) -> "Optional[tuple]":
        """Element shape from the dtype/shape API, or None if not specified."""
        return self._shape

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write(
        self,
        data: _BindingTensorT,
        dirty_bits: Optional[bytes] = None,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> None:
        """Write attribute data using this binding (synchronous).

        Args:
            data: Data to write. Accepts NumPy arrays, Warp arrays, or any
                ``__dlpack__``-compatible object. For scalar bindings
                (``bind_attribute``): a single tensor. For array bindings
                (``bind_array_attribute``): a list of tensors, one per prim.
                For string bindings: a ``list[str]`` (scalar) or
                ``list[list[str]]`` (array).
            dirty_bits: Optional dirty bit array for selective updates.
            data_access: Data access mode. ``DataAccess.SYNC`` (default) copies
                input data immediately so the caller's buffer can be reused
                after this call returns. ``DataAccess.ASYNC`` references the
                caller's buffer until the operation completes (zero-copy). Not
                allowed with string bindings.
            cuda_stream: Optional CUDA stream handle (``int``) on which the input
                tensor's data is (or will be) ready. ovrtx synchronizes its read of
                the tensor against this stream and forwards it to the DLPack producer
                (e.g. Warp) so any pending work on a different stream is bridged
                automatically. If omitted, the caller must ensure the tensor's state
                is fully settled before calling.
            cuda_event: CUDA event handle (``int``) for GPU synchronization.

        Raises:
            RuntimeError: If called after unbind().
        """
        if self._handle is None:
            raise RuntimeError(
                "AttributeBinding.write() called after unbind(). Create a new binding with bind_attribute()."
            )
        tensors = data if self._is_array else [data]
        self._get_renderer()._write_attribute_by_binding(
            self,
            tensors,
            dirty_bits,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        )

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write_async(
        self,
        data: _BindingTensorT,
        dirty_bits: Optional[bytes] = None,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> "Operation[bool]":
        """Write attribute data using this binding (asynchronous).

        Args:
            data: Data to write. Accepts NumPy arrays, Warp arrays, or any
                ``__dlpack__``-compatible object. For scalar bindings
                (``bind_attribute``): a single tensor. For array bindings
                (``bind_array_attribute``): a list of tensors, one per prim.
                For string bindings: a ``list[str]`` (scalar) or
                ``list[list[str]]`` (array).
            dirty_bits: Optional dirty bit array for selective updates.
            data_access: Data access mode. ``DataAccess.SYNC`` (default) copies
                input data immediately; ``DataAccess.ASYNC`` references the
                caller's buffer until the operation completes (zero-copy). Not
                allowed with string bindings.
            cuda_stream: Optional CUDA stream handle (``int``) on which the input
                tensor's data is (or will be) ready. ovrtx synchronizes its read of
                the tensor against this stream and forwards it to the DLPack producer
                (e.g. Warp) so any pending work on a different stream is bridged
                automatically. If omitted, the caller must ensure the tensor's state
                is fully settled before calling.
            cuda_event: Optional CUDA event handle (int) for GPU sync.

        Returns:
            Operation for async control (yields None on completion).

        Raises:
            RuntimeError: If called after unbind().
        """
        if self._handle is None:
            raise RuntimeError(
                "AttributeBinding.write_async() called after unbind(). Create a new binding with bind_attribute()."
            )
        tensors = data if self._is_array else [data]
        return self._get_renderer()._write_attribute_by_binding_async(
            self, tensors, dirty_bits, data_access=data_access, cuda_stream=cuda_stream, cuda_event=cuda_event
        )

    @deprecated(_OVSTAGE_MAP_REPLACEMENT)
    def map(self, device: Device = Device.CPU, device_id: int = 0) -> "AttributeMapping":
        """Map attribute buffer for direct memory access using this binding.

        Convenience wrapper: delegates to Renderer._map_attribute_by_binding().

        Args:
            device: Device type (Device.CPU or Device.CUDA).
            device_id: Device ID (default 0).

        Returns:
            AttributeMapping for direct buffer access.

        Raises:
            RuntimeError: If called after unbind().
        """
        if self._handle is None:
            raise RuntimeError(
                "AttributeBinding.map() called after unbind(). Create a new binding with bind_attribute()."
            )
        return self._get_renderer()._map_attribute_by_binding(self, device, device_id)

    @deprecated(_OVSTAGE_RELEASE_QUERY_REPLACEMENT)
    def unbind(self) -> None:
        """Release this binding.

        Convenience wrapper: delegates to Renderer._unbind_attribute().
        """
        if self._handle is None:
            return  # Already unbound
        self._get_renderer()._unbind_attribute(self)
        self._handle = None

    def __del__(self):
        """Auto-unbind on garbage collection if not already unbound."""
        if self._handle is None:
            return  # Already unbound
        renderer = self._renderer()  # weakref - may be None if renderer destroyed
        if renderer is None:
            return  # Renderer already gone, can't unbind
        if self._handle not in renderer._live_binding_handles:
            return  # Already force-unbound by renderer destruction
        try:
            renderer._unbind_attribute(self)
        except Exception as e:
            print(f"Warning: Exception during AttributeBinding cleanup: {e}", file=sys.stderr)
        self._handle = None

    def __repr__(self) -> str:
        return f"AttributeBinding(handle={self._handle}, semantic={self._semantic})"


class _AttrMappingCtx:
    """Lightweight proxy used as manager_ctx for AttributeMapping's ManagedDLTensor.

    Avoids a Py_IncRef reference cycle between AttributeMapping and ManagedDLTensor
    so that AttributeMapping.__del__ fires via refcount for deterministic cleanup.
    """


class AttributeMapping:
    """High-level wrapper for mapped attribute buffer.

    Provides access to an internal buffer for direct writes using NumPy, Warp,
    or any ``__dlpack__``-compatible library. ``unmap()`` and ``__exit__``
    commit data to the stage synchronously. If the mapping is dropped without
    ``unmap()`` or a context manager, ``__del__`` commits and frees the buffer
    as a safety-net fallback.

    Usage:
        ```python
        import numpy as np

        mapping = renderer.map_attribute(
            ["/World/Cube"], "xformOp:transform",
            dtype=np.float64, shape=(4, 4))

        # Write data via NumPy, Warp, etc.
        array = np.from_dlpack(mapping.tensor)
        array[:] = source_matrix_data

        # Unmap to apply changes
        mapping.unmap()
        ```

    Or use as context manager:
        ```python
        with renderer.map_attribute(...) as mapping:
            np.from_dlpack(mapping.tensor)[:] = source_data
        # Automatically unmapped on exit
        ```
    """

    def __init__(
        self,
        mapping: Any,  # ovrtx_attribute_mapping_t from C API
        renderer: "Renderer",
        dltensor: DLTensor,  # Reshaped DLTensor view (provided by renderer)
        binding_desc: Optional[Any] = None,  # Optional ovrtx_binding_desc_t for write_attribute
        device: Device = Device.CPU,
    ):
        """Initialize attribute mapping (internal use - created by Renderer.map_attribute).

        Args:
            mapping: C structure ovrtx_attribute_mapping_t containing map_handle and tensor data.
            renderer: Renderer instance (needed for unmap).
            dltensor: Reshaped tensor view (provided by renderer, shaped per dtype/shape).
            binding_desc: Optional binding descriptor (for write_attribute calls).
            device: Device type (Device.CPU or Device.CUDA).
        """
        self._mapping = mapping
        self._renderer = renderer
        self._dltensor = dltensor
        self._binding_desc = binding_desc
        self._device = device
        self._unmapped = False
        self._managed_tensor: Optional[ManagedDLTensor] = None

    @property
    def tensor(self) -> ManagedDLTensor:
        """Access the mapped buffer as a tensor for NumPy, Warp, etc.

        When the mapping was created with ``shape=``, the tensor dimensions
        match ``(N, *shape)`` with a scalar element dtype. For
        ``Semantic.XFORM_MAT4x4`` bindings, the tensor is reshaped to
        ``(N, 4, 4)`` for direct matrix operations.

        Use ``np.from_dlpack(mapping.tensor)`` or equivalent to obtain a
        writable array view.

        Returns:
            ManagedDLTensor ready for consumption by array libraries.

        Raises:
            RuntimeError: If accessed after unmap().
        """
        if self._unmapped:
            raise RuntimeError(
                "Mapping already released — access tensor before calling unmap() or exiting the with block."
            )
        if self._managed_tensor is None:
            ctx = _AttrMappingCtx()
            self._managed_tensor = ManagedDLTensor(self._dltensor, ctx, None, readonly=False)
        return self._managed_tensor

    @property
    def map_handle(self) -> int:
        """Get the map handle for unmap operation.

        Returns:
            Map handle value (uint64)
        """
        return int(self._mapping.map_handle)

    @property
    def binding_desc(self) -> Optional[Any]:
        """Get the binding descriptor used for map_attribute (if available).

        This can be used for write_attribute calls if needed.

        Returns:
            ovrtx_binding_desc_t or None
        """
        return self._binding_desc

    @property
    def device(self) -> Device:
        """Get the device type this attribute is mapped to."""
        return self._device

    def _do_unmap(self, event: Optional[int] = None, stream: Optional[int] = None) -> "Operation[bool]":
        """Validate, enqueue C unmap, mark unmapped, return Operation.

        Single gatekeeper for sync and async unmap paths. Sets
        ``_unmapped = True`` before returning so ``__del__`` cannot race
        with an in-flight operation.

        Args:
            event: CUDA event handle to wait on before committing.
            stream: CUDA stream handle to synchronize before committing.

        Returns:
            Operation that completes when data is committed to stage.

        Raises:
            RuntimeError: If mapping already unmapped.
            ValueError: If event/stream provided for CPU-mapped attribute.
            ValueError: If both event and stream provided (mutually exclusive).
        """
        if self._unmapped:
            raise RuntimeError("Mapping already unmapped")

        if self._device == Device.CPU and (event is not None or stream is not None):
            raise ValueError("CUDA sync parameters (event/stream) not applicable for CPU-mapped attributes")

        if event is not None and stream is not None:
            raise ValueError("Cannot specify both event and stream; use one or the other")

        op = self._renderer._enqueue_attribute_unmap(
            int(self._mapping.map_handle), self._build_cuda_sync(event, stream)
        )
        self._managed_tensor = None
        self._unmapped = True
        return op

    @deprecated(_OVSTAGE_UNMAP_REPLACEMENT)
    def unmap(self, event: Optional[int] = None, stream: Optional[int] = None) -> None:
        """Commit written data to stage and free the C buffer.

        Enqueues the C unmap and waits for completion. Data is visible
        on the stage when this method returns.

        Args:
            event: CUDA event handle to wait on before C unmap.
            stream: CUDA stream handle to synchronize before C unmap.

        Raises:
            ValueError: If event/stream provided for CPU-mapped attribute.
            ValueError: If both event and stream provided (mutually exclusive).
        """
        if self._unmapped:
            return
        self._do_unmap(event, stream).wait()

    @deprecated(_OVSTAGE_UNMAP_REPLACEMENT)
    def unmap_async(self, event: Optional[int] = None, stream: Optional[int] = None) -> "Operation[bool]":
        """Enqueue attribute unmap and return an Operation for caller-managed wait.

        The mapping is marked as unmapped immediately — ``__del__``
        becomes a no-op. Call ``.wait()`` on the returned Operation to
        block until data is committed to the stage.

        Args:
            event: CUDA event handle to wait on before committing.
            stream: CUDA stream handle to synchronize before committing.

        Returns:
            Operation[bool] for async control.

        Raises:
            RuntimeError: If mapping already unmapped.
            ValueError: If event/stream provided for CPU-mapped attribute.
            ValueError: If both event and stream provided (mutually exclusive).
        """
        return self._do_unmap(event, stream)

    def _build_cuda_sync(self, event: Optional[int] = None, stream: Optional[int] = None):
        """Build ovrtx_cuda_sync_t from event/stream params."""
        from . import bindings

        cuda_sync = bindings.ovrtx_cuda_sync_t()
        if stream is not None:
            cuda_sync.stream = stream
        if event is not None:
            cuda_sync.wait_event = event
        return cuda_sync

    def __enter__(self) -> "AttributeMapping":
        """Context manager entry — returns self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — commits data and frees buffer."""
        if not self._unmapped:
            self._do_unmap().wait()
        return False

    def __del__(self):
        """Safety fallback — enqueue C unmap if not already done.

        Uses fire-and-forget (no ``op.wait()``) because blocking C calls
        can deadlock inside finalizers. The enqueued operation completes
        when the renderer processes its next operation.
        """
        if not self._unmapped:
            try:
                self._renderer._enqueue_attribute_unmap(int(self._mapping.map_handle))
            except Exception:
                pass
            self._managed_tensor = None
            self._unmapped = True

    def __repr__(self) -> str:
        status = "unmapped" if self._unmapped else "mapped"
        return f"AttributeMapping(map_handle={self.map_handle}, {status})"


@dataclass
class RendererConfig:
    """ovrtx renderer configuration."""

    sync_mode: Optional[bool] = None
    """Enables synchronous rendering mode for debugging purposes."""

    log_file_path: Optional[str] = None
    """Set the path to the log file for logging output."""

    log_level: Optional[str] = None
    """Set the log level for logging output: "verbose", "info", "warn", "error"."""

    enable_profiling: Optional[bool] = None
    """Enable internal profiling. Adds overhead when enabled."""

    read_gpu_transforms: Optional[bool] = None
    """Use GPU world transform propagation during rendering."""

    keep_system_alive: Optional[bool] = None
    """Keep the renderer system alive after all instances are destroyed so the next create reuses it.

    When omitted (``None``), the native layer defaults to enabled.
    """

    active_cuda_gpus: Optional[str] = None
    """Comma-separated CUDA device indices to use for rendering (e.g., "0,1,2")."""

    datastore_cache: Optional[str] = None
    """Protocol-prefixed datastore cache configuration used by UJITSO. Supported values include
    ``grpcdns://host:port``, ``grpcdns_notls://host:port``, and ``local://path``. When omitted,
    existing defaults and environment-variable behavior are preserved."""

    use_vulkan: Optional[bool] = None
    """Select Vulkan rendering backend. On Linux Vulkan is always used.
    On Windows, set True to force Vulkan instead of the default DX12."""

    selection_outline_enabled: Optional[bool] = None
    """Enable the selection-outline post-process pass. Defaults to ``False`` when unset.
    Init-time only; toggling requires recreating the renderer."""

    selection_outline_width: Optional[int] = None
    """Selection outline width in pixels. Valid range is ``0..15`` (the underlying RTX
    outline pipeline cap); out-of-range values are clamped by the renderer.
    Init-time only; changing requires recreating the renderer. Default: 2."""

    selection_fill_mode: Optional[SelectionFillMode] = None
    """Selection-outline fill (interior) mode. Accepts a :class:`SelectionFillMode`
    member or the equivalent ``int`` value (``0..3``). Out-of-range values are
    clamped by the renderer.

    Init-time only; changing requires recreating the renderer.
    Default: :attr:`SelectionFillMode.GLOBAL`."""

    dome_baking_resolution: Optional[int] = None
    """DomeLight baking resolution in texels, used when an MDL material drives a
    DomeLight's image source. Applies renderer-wide to all dome lights. Valid
    range is ``1..8192``; out-of-range values are clamped by the renderer.

    Init-time only; changing requires recreating the renderer. When ``None``,
    ovrtx does not write the setting: the value is ``4096`` for the first
    renderer in a fresh process, but a value set by a prior in-process renderer
    (or via dev settings) is left in place rather than reset."""

    enable_geometry_streaming: Optional[bool] = None
    """Geometry streaming opt-in config entry."""

    enable_geometry_streaming_lod: Optional[bool] = None
    """Geometry streaming LOD opt-in config entry."""

    enable_spg: Optional[bool] = None
    """Set to False to disable Sensor Processing Graphs (SPG), enabled by default.
       This is a global setting, applying to all active renderer instances."""

    suppress_deprecation_warnings: Optional[bool] = None
    """Suppress Python and native runtime warnings emitted by deprecated OVRTX APIs.

    Compile-time deprecation diagnostics for C and C++ consumers are unaffected. When ``None`` or
    ``False``, runtime deprecation warnings remain enabled.
    """

    motion_bvh: Optional[MotionBvh] = None
    """Motion BVH mode for sensor pipelines (lidar, radar, acoustic).

    Accepts a :class:`MotionBvh` member, the equivalent ``int`` value (``0..2``),
    or the strings ``"disable"``, ``"enable"``, or ``"auto"``.

    When ``None`` (default), motion BVH is disabled and no config entry is sent.
    Sensor workflows should pass :attr:`MotionBvh.AUTO` or :attr:`MotionBvh.ENABLE`.
    Init-time only; changing requires recreating the renderer."""

    texture_streaming_mode: Optional[TextureStreamingMode] = None
    """Texture streaming mode.

    Accepts a :class:`TextureStreamingMode` member, the equivalent ``int`` value
    (``0..2``), or the strings ``"disable"``, ``"synchronous"``, or
    ``"asynchronous"``. When ``None``, asynchronous mode is used.

    Synchronous mode controls texture-feedback processing; it does not make all
    texture loading operations synchronous. This setting is process-global and
    applies to all active renderer instances."""

    def __repr__(self) -> str:
        set_fields = ", ".join(
            f"{f.name}={getattr(self, f.name)!r}" for f in fields(self) if getattr(self, f.name) is not None
        )
        return f"RendererConfig({set_fields})"


@dataclass
class SelectionGroupStyle:
    """Per-group visual styling for the selection-outline pass.

    Used as the value side of the dict passed to
    :meth:`Renderer.set_selection_group_styles`. RGBA components are floats
    in ``[0, 1]``.

    Group ids (the dict keys) are uint8 (``0..255``) and match the per-prim
    group id assigned through the renderer selection-outline group API.

    Note:
        Outline thickness and the fill/interior mode are global init-time
        settings — see :attr:`RendererConfig.selection_outline_width` and
        :attr:`RendererConfig.selection_fill_mode`. Outline dashing is not
        supported by the underlying renderer.
    """

    outline_color: tuple[float, float, float, float]
    """Outline edge color (RGBA, ``[0, 1]``)."""

    fill_color: tuple[float, float, float, float]
    """Interior fill color (RGBA, ``[0, 1]``). Used when the global fill
    mode selects per-group fill modes (``2`` or ``3``)."""


@dataclass
class OperationCounter:
    """Named resource counter from an operation progress query."""

    name: str
    """Counter name (e.g. ``"systems"``). Assigned by the C runtime."""

    current: int
    """Current value. Monotonically increases toward *total*."""

    total: int
    """Target value. ``0`` means the total is unknown."""


@dataclass
class OperationStatus:
    """Snapshot of an operation's progress.

    Returned by :meth:`Operation.query_status`. Fields are copied from
    the C ``ovrtx_op_status_t`` struct and the C resources are released
    immediately, so this object has no special lifecycle requirements.
    """

    state: EventStatus
    """``PENDING``, ``COMPLETED``, or ``FAILURE``."""

    progress: float
    """Fraction complete in ``[0.0, 1.0]``. Negative means indeterminate."""

    counters: list[OperationCounter]
    """Per-resource counters (may be empty)."""


@dataclass
class AttributeInfo:
    """Descriptor for an attribute discovered by :meth:`Renderer.query_prims`.

    Carries the resolved attribute name, element data type, and semantic.
    Returned inside :class:`QueryResult` dict values.
    """

    name: str
    """Resolved attribute name (e.g. ``"radius"``, ``"points"``)."""

    dtype: DLDataType
    """Element data type (code, bits, lanes)."""

    is_array: bool
    """True if the attribute is variable-length per prim."""

    semantic: Semantic
    """Interpretation hint (NONE, TOKEN_ID, PATH_ID, TAG, etc.)."""
