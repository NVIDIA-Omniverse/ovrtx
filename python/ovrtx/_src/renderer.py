# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import ctypes
import math
import operator
import sys
import threading
import warnings
from dataclasses import dataclass, field
from typing import Any, List, Optional

from . import bindings
from .dlpack import DLDataType, DLDataTypeCode, DLDevice, DLDeviceType, DLTensor, ManagedDLTensor
from .helpers import deprecated
from .types import (
    _VOID_RESULT,
    AttributeBinding,
    AttributeInfo,
    AttributeMapping,
    BindingFlag,
    DataAccess,
    Device,
    EventStatus,
    FrameOutput,
    Operation,
    OperationCounter,
    OperationStatus,
    PendingFetch,
    PrimMode,
    ProductOutput,
    RendererConfig,
    RenderProductSetOutputs,
    RenderVarOutput,
    SelectionGroupStyle,
    Semantic,
)

_OVSTAGE_POPULATION_REPLACEMENT = (
    "Use ovstage.population with an ovstage.Stage, attach it with Renderer.attach_ovstage(), "
    "and render with Renderer.step(..., ordinal=...)."
)
_OVSTAGE_CLONE_REPLACEMENT = "Use ovstage.Stage.clone() or clone_async(), then advance the write floor."
_OVSTAGE_QUERY_REPLACEMENT = "Use ovstage.Stage.query() or query_from_path_list() instead."
_OVSTAGE_READ_REPLACEMENT = "Use ovstage.Stage.read_attributes() and fetch read groups from ovstage instead."
_OVSTAGE_WRITE_REPLACEMENT = "Use ovstage.Stage.write_attribute() with an ordinal and reusable query instead."
_OVSTAGE_BINDING_REPLACEMENT = "Use a reusable ovstage query with ovstage.Stage read, write, or map operations instead."
_OVSTAGE_MAP_REPLACEMENT = "Use ovstage.Stage.map_attribute() with an ordinal and reusable query instead."
_OVSTAGE_UNMAP_REPLACEMENT = "Use ovstage.Map.unmap() or ovstage.Stage.unmap_attribute() instead."


@dataclass
class _PrimGroup:
    """A group of prims sharing the same attribute schema.

    Built during the query fetch closure. Each group carries both
    resolved Python-facing data (attribute names, prim paths) and the
    original handles for efficient bulk reads.
    """

    prim_count: int
    """Number of prims in this group."""

    prim_list_handle: int
    """Handle for efficient bulk reads."""

    attributes: dict[str, AttributeInfo]
    """Resolved attribute names mapped to their descriptors."""

    _path_dict: "bindings.path_dictionary_instance_t" = field(repr=False)
    """Path dictionary for resolving prim path handles to strings."""

    _prim_paths_cache: Optional[list[str]] = field(repr=False, default=None)

    @property
    def prim_paths(self) -> list[str]:
        """Resolved USD prim path strings for this group (cached on first access)."""
        if self._prim_paths_cache is None:
            self._prim_paths_cache = self._path_dict.get_path_list_paths(self.prim_list_handle)
        return self._prim_paths_cache


class _AttributeBindingDescStorage:
    """Helper class to keep binding descriptor and string arrays alive (private implementation detail)."""

    def __init__(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: DLDataType,
        semantic: int,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        flags: int = bindings.BindingFlag.NONE,
        is_array: bool = False,
    ):
        # Keep string objects alive
        self._prim_strings = [bindings.ovx_string_t(path) for path in prim_paths]
        self._attr_string = bindings.ovx_string_t(attribute_name)

        # Create ctypes array - MUST keep reference to prevent GC
        self._prim_array = (bindings.ovx_string_t * len(self._prim_strings))(*self._prim_strings)

        # Build prim_list pointing to array
        self.prim_list = bindings.ovrtx_prim_list_t(
            prim_paths=self._prim_array, num_paths=len(self._prim_strings)  # Array reference kept in self
        )

        # Build attribute_name (string mode)
        self.attribute_name = bindings.ovx_string_or_token_t(
            string=self._attr_string, token=0  # String reference kept in self
        )

        # Build attribute_type
        self.attribute_type = bindings.ovrtx_attribute_type_t(
            dtype=dtype,
            is_array=is_array,
            semantic=bindings.ovrtx_attribute_semantic_t(semantic),
        )

        # Build full binding_desc
        self.binding_desc = bindings.ovrtx_binding_desc_t(
            prim_list=self.prim_list,
            prims_list_handle=0,  # Not using persistent handles
            attribute_name=self.attribute_name,
            attribute_type=self.attribute_type,
            prim_mode=bindings.ovrtx_binding_prim_mode_t(prim_mode),
            flags=bindings.ovrtx_binding_flag_t(flags),
        )

        # Build binding_desc_or_handle (always use binding_desc, handle=0)
        self.binding_desc_or_handle = bindings.ovrtx_binding_desc_or_handle_t(
            binding_desc=self.binding_desc, binding_handle=0
        )


class _InputBufferStorage:
    """Helper class to keep input buffer and DLTensor arrays alive (private implementation detail)."""

    def __init__(
        self,
        dl_tensors: List[DLTensor],
        dirty_bits: Optional[bytes] = None,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ):
        """Initialize input buffer storage.

        Args:
            dl_tensors: List of DLTensor objects (will be copied to array)
            dirty_bits: Optional dirty bit array (copied if provided)
            cuda_stream: Optional CUDA stream handle (int). Sets both access and done sync stream fields.
            cuda_event: Optional CUDA event handle (int). Sets access sync wait_event field.
        """
        # Keep Python data references alive (for ASYNC access)
        self._tensor_refs = dl_tensors

        # Create DLTensor objects array
        self._tensor_storage = list(dl_tensors)  # Keep references

        # Create ctypes array and populate with stable shape/strides pointers.
        # We store the backing arrays in _shape_storage/_strides_storage to keep them alive.
        tensor_count = len(self._tensor_storage)
        self._tensor_array = (DLTensor * tensor_count)()
        self._shape_storage = []
        self._strides_storage = []

        for i, src_tensor in enumerate(self._tensor_storage):
            dest = self._tensor_array[i]
            # Copy scalar fields
            dest.data = src_tensor.data
            dest.device = src_tensor.device
            dest.ndim = src_tensor.ndim
            dest.dtype = src_tensor.dtype
            dest.byte_offset = src_tensor.byte_offset

            # Deep-copy shape array and set pointer
            if src_tensor.ndim > 0 and src_tensor.shape:
                shape_array = (ctypes.c_int64 * src_tensor.ndim)()
                for j in range(src_tensor.ndim):
                    shape_array[j] = src_tensor.shape[j]
                self._shape_storage.append(shape_array)
                dest.shape = ctypes.cast(shape_array, ctypes.POINTER(ctypes.c_int64))
            else:
                self._shape_storage.append(None)
                dest.shape = None

            # Deep-copy strides array if present
            if src_tensor.ndim > 0 and src_tensor.strides:
                strides_array = (ctypes.c_int64 * src_tensor.ndim)()
                for j in range(src_tensor.ndim):
                    strides_array[j] = src_tensor.strides[j]
                self._strides_storage.append(strides_array)
                dest.strides = ctypes.cast(strides_array, ctypes.POINTER(ctypes.c_int64))
            else:
                self._strides_storage.append(None)
                dest.strides = None

        # Build dirty_bits array if provided
        self._dirty_bits_array = None
        dirty_bits_ptr = None
        dirty_bits_size = 0
        if dirty_bits is not None:
            dirty_bits_size = len(dirty_bits)
            self._dirty_bits_array = (ctypes.c_uint8 * dirty_bits_size).from_buffer_copy(dirty_bits)
            dirty_bits_ptr = ctypes.cast(self._dirty_bits_array, ctypes.POINTER(ctypes.c_uint8))

        # Build CUDA sync structs (fields default to 0)
        access_sync = bindings.ovrtx_cuda_sync_t()
        done_sync = bindings.ovrtx_cuda_sync_t()
        if cuda_stream is not None:
            access_sync.stream = cuda_stream
            done_sync.stream = cuda_stream
        if cuda_event is not None:
            access_sync.wait_event = cuda_event

        # Build input_buffer pointing to array
        self.input_buffer = bindings.ovrtx_input_buffer_t(
            tensors=self._tensor_array,  # Array reference kept in self
            tensor_count=len(self._tensor_storage),
            dirty_bits=dirty_bits_ptr,
            dirty_bits_size=dirty_bits_size,
            access_cuda_sync=access_sync,
            done_cuda_sync=done_sync,
        )


class Renderer:
    """High-level Pythonic renderer for OVRTX.

    Wraps the C library with automatic resource management. Resources are
    cleaned up automatically when the renderer goes out of scope.

    Enum types for method parameters are accessible as class attributes
    (e.g., ``Renderer.PrimMode.EXISTING_ONLY``) or via top-level imports
    (e.g., ``from ovrtx import PrimMode``).

    Example:
        ```python
        from ovrtx import Renderer, RendererConfig

        # Use defaults
        renderer = Renderer()

        # Or customize
        config = RendererConfig(sync_mode=True, log_file_path="/path/to/app.log")
        renderer = Renderer(config=config)

        # Resources automatically cleaned up when renderer goes out of scope
        ```
    """

    Semantic = Semantic
    PrimMode = PrimMode
    DataAccess = DataAccess
    Device = Device

    def __init__(self, config: Optional[RendererConfig] = None):
        """Create a new renderer instance.

        Args:
            config: Optional renderer configuration. If None, uses default configuration.

        Raises:
            RuntimeError: If the renderer cannot be created.
        """
        self._handle: Any = None
        self._attached_ovstage: Optional[Any] = None

        # Use default config if none provided, otherwise copy to avoid mutating user's object
        if config is None:
            config = RendererConfig()
        else:
            from copy import copy

            config = copy(config)

        # get bindings to ovrtx library (including lazy-loading and initializing the library if necessary)
        ovrtx_config = self._to_c_config(config)
        _bindings = bindings._ovrtx_loader.create_bindings(ovrtx_config)

        # Create a new renderer instance
        result, c_renderer = _bindings.create_renderer(ovrtx_config)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = _bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to create renderer: {error_msg}\nconfig: {config}")

        # Store bindings, renderer handle and config for other methods to use
        self._handle = c_renderer
        self._bindings = _bindings
        self._config = config

        # Live mapping registry: map_handle -> _UnmapState
        # Used to force-unmap all active mappings before destroying the renderer.
        # _force_unmap_all sets state.unmapped=True so deferred deleters become no-ops.
        self._live_mappings: dict[int, Any] = {}
        self._live_mappings_lock = threading.RLock()

        # Live binding handle registry: raw C handle integers.
        # _force_unbind_all destroys them before destroy_renderer.
        self._live_binding_handles: set[int] = set()

        # Cached path dictionary for token/path resolution (valid for renderer lifetime).
        self._path_dict: Optional[bindings.path_dictionary_instance_t] = None

    def destroy(self) -> None:
        """Explicitly release the renderer's native resources.

        Idempotent: safe to call multiple times. Prefer calling this (e.g. in a fixture finalizer
        or ``try/finally``) for deterministic teardown: the Python wrapper can be kept alive past
        its last use by reference cycles, which would otherwise defer native cleanup to a GC pass.

        Raises:
            RuntimeError: If detaching an attached ovstage or destroying the renderer fails.
        """
        if self._handle is None:
            return
        cleanup_errors = []
        try:
            self._force_unbind_all()
            self._force_unmap_all()
            if self._attached_ovstage is not None:
                result = self._bindings.detach_ovstage(self._handle)
                if result.status != bindings.OVRTX_API_SUCCESS:
                    error_msg = self._bindings.get_last_error() or "Unknown error"
                    cleanup_errors.append(f"Failed to detach ovstage: {error_msg}")
            result = self._bindings.destroy_renderer(self._handle)

            if result.status != bindings.OVRTX_API_SUCCESS:
                error_msg = self._bindings.get_last_error() or "Unknown error"
                cleanup_errors.append(f"Failed to destroy renderer: {error_msg}")
            if cleanup_errors:
                raise RuntimeError("; ".join(cleanup_errors))
        finally:
            # Always clear references to prevent double-cleanup attempts
            self._handle = None
            self._bindings = None
            self._config = None
            self._path_dict = None
            self._attached_ovstage = None

    def __del__(self):
        """Automatically clean up renderer resources on destruction."""
        try:
            self.destroy()
        except Exception as e:
            print(f"Warning: Exception during renderer cleanup in __del__: {e}", file=sys.stderr)

    def _register_mapping(self, handle: int, state: Any) -> None:
        """Register an active mapping's shared state for force-unmap on renderer destruction."""
        with self._live_mappings_lock:
            self._live_mappings[handle] = state

    def _deregister_mapping(self, handle: int) -> None:
        """Remove a mapping from the registry (called by deleter after C unmap)."""
        with self._live_mappings_lock:
            self._live_mappings.pop(handle, None)

    def _force_unmap_all(self) -> None:
        """Force-unmap all active mappings before renderer destruction.

        Sets ``state.unmapped = True`` on each mapping so that deferred deleters
        (which fire later when NumPy/Warp arrays are GC'd) become no-ops.
        """
        with self._live_mappings_lock:
            mappings = list(self._live_mappings.items())
            self._live_mappings.clear()
        if mappings:
            warnings.warn(
                f"Renderer destroyed with {len(mappings)} active mapping(s) — force-unmapping. "
                "Ensure all NumPy/Warp arrays from mapped render vars are deleted before the renderer.",
                RuntimeWarning,
                stacklevel=2,
            )
            for handle, state in mappings:
                if not state.unmapped:
                    state.unmapped = True
                    try:
                        self._unmap_output(handle, state.cuda_sync)
                    except Exception:
                        pass

    def _force_unbind_all(self) -> None:
        """Destroy all live attribute binding C handles before renderer destruction."""
        handles = list(self._live_binding_handles)
        self._live_binding_handles.clear()
        if handles:
            warnings.warn(
                f"Renderer destroyed with {len(handles)} active binding(s) — force-unbinding. "
                "Call unbind() on AttributeBinding objects before destroying the renderer.",
                RuntimeWarning,
                stacklevel=2,
            )
            for h in handles:
                try:
                    self._bindings.destroy_attribute_binding(self._handle, bindings.ovrtx_attribute_binding_handle_t(h))
                except Exception:
                    pass

    @property
    def version(self) -> tuple:
        """Runtime library version as a (major, minor, patch) tuple."""
        return self._bindings.version

    def attach_ovstage(self, stage: Any) -> None:
        """Attach an externally owned ``ovstage.Stage`` to this renderer.

        The renderer borrows the Stage's native instance and retains the Python
        object until detach or renderer destruction. Do not explicitly destroy
        the Stage while it is attached.

        Args:
            stage: A live ``ovstage.Stage`` instance.

        Raises:
            RuntimeError: If the renderer is invalid, is already attached, or
                the native attach fails.
            TypeError: If ``stage`` does not expose a compatible native handle.
            ValueError: If the Stage has already been destroyed.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        if self._attached_ovstage is not None:
            raise RuntimeError("Renderer already has an ovstage attached")

        stage_handle = getattr(stage, "_inst", None)
        if stage_handle is None:
            raise TypeError("stage must be a live ovstage.Stage instance")
        try:
            stage_pointer = ctypes.cast(stage_handle, bindings.ovstage_instance_p)
        except (ctypes.ArgumentError, TypeError, ValueError) as e:
            raise TypeError("stage must be a live ovstage.Stage instance") from e
        if not stage_pointer:
            raise ValueError("Cannot attach a destroyed ovstage.Stage")

        result = self._bindings.attach_ovstage(self._handle, stage_pointer)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to attach ovstage: {error_msg}")
        self._attached_ovstage = stage

    def detach_ovstage(self) -> None:
        """Detach the attached ovstage and return the renderer to standalone mode."""
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        if self._attached_ovstage is None:
            raise RuntimeError("Renderer has no ovstage attached")

        result = self._bindings.detach_ovstage(self._handle)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to detach ovstage: {error_msg}")
        self._attached_ovstage = None

    def update_from_stage(self, ordinal: int) -> None:
        """Update from the attached ovstage through at least ``ordinal``.

        In BORROW mode this synchronizes the renderer's scene state with committed
        population changes while attribute values remain shared with ovstage. In
        REPLICATE mode it copies committed Stage data into the renderer-owned stage.
        Normal calls to :meth:`step` perform this update automatically in both modes.
        """
        self.update_from_stage_async(ordinal).wait()

    def update_from_stage_async(self, ordinal: int) -> Operation[bool]:
        """Enqueue an update from the attached ovstage through at least ``ordinal``.

        BORROW synchronizes the renderer's scene state with committed population
        changes without copying shared attribute values. REPLICATE copies committed
        Stage data into the renderer-owned stage. :meth:`step_async` performs this
        update automatically in both modes.

        Args:
            ordinal: Minimum committed ovstage publication to update through.

        Returns:
            Operation that completes when the update has been applied.

        Raises:
            RuntimeError: If the renderer is invalid, no Stage is attached, or the
                update cannot be enqueued.
            TypeError: If ``ordinal`` is not an integer.
            ValueError: If ``ordinal`` is outside the uint64 range.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        if self._attached_ovstage is None:
            raise RuntimeError("Renderer has no ovstage attached")

        ordinal_value = self._normalize_ordinal(ordinal)
        result = self._bindings.update_from_stage(self._handle, ordinal_value)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue update_from_stage: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"update_from_stage(ordinal={ordinal_value})",
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def open_usd(self, usd_file_path: str) -> None:
        """Open a USD file as the root layer (synchronous).

        Resets the current stage and loads the given file as the root sublayer.
        Blocks until the USD file is fully loaded.

        Args:
            usd_file_path: Path to the USD file to open.

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, or loading fails.

        Example:
            ```python
            renderer.open_usd("/path/to/scene.usda")
            ```
        """
        self.open_usd_async(usd_file_path).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def open_usd_async(self, usd_file_path: str) -> Operation[bool]:
        """Open a USD file as the root layer (asynchronous).

        Resets the current stage and loads the given file as the root sublayer.
        Returns immediately with an Operation for manual control.

        Args:
            usd_file_path: Path to the USD file to open.

        Returns:
            Operation that can be polled or waited on with custom timeout.
            ``wait()`` returns ``True`` on success and ``None`` on timeout.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.

        Example:
            ```python
            op = renderer.open_usd_async("/path/to/scene.usda")
            op.wait(timeout_ns=1_000_000_000)
            ```
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.open_usd_from_file(self._handle, usd_file_path)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue open_usd: {error_msg}")

        return Operation(
            renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name=f"open_usd({usd_file_path})"
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def open_usd_from_string(self, root_layer_content: str) -> None:
        """Open a USD stage from inline USDA content (synchronous).

        Resets the current stage and loads the given content as the root sublayer.
        Blocks until the layer is fully loaded.

        Args:
            root_layer_content: USDA content as a Python string.

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, or loading fails.
            ValueError: If root_layer_content is empty.

        Example:
            ```python
            renderer.open_usd_from_string('''
            #usda 1.0
            (defaultPrim = "World")
            def Xform "World" { ... }
            ''')
            ```
        """
        self.open_usd_from_string_async(root_layer_content).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def open_usd_from_string_async(self, root_layer_content: str) -> Operation[bool]:
        """Open a USD stage from inline USDA content (asynchronous).

        Resets the current stage and loads the given content as the root sublayer.
        Returns immediately with an Operation for manual control.

        Args:
            root_layer_content: USDA content as a Python string.

        Returns:
            Operation that can be polled or waited on with custom timeout.
            ``wait()`` returns ``True`` on success and ``None`` on timeout.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If root_layer_content is empty.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if not root_layer_content or not root_layer_content.strip():
            raise ValueError("root_layer_content cannot be empty")

        result = self._bindings.open_usd_from_string(self._handle, root_layer_content)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue open_usd_from_string: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name="open_usd_from_string(<inline>)",
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def add_usd_reference(self, layer_file: str, prefix_path: str) -> Any:
        """Add a USD file as a reference at a prim path (synchronous).

        Blocks until the reference is fully loaded.

        Args:
            layer_file: Path to the USD file to add as a reference.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            USD handle for the added reference (for use with remove_usd).

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, or loading fails.

        Example:
            ```python
            handle = renderer.add_usd_reference("/path/to/props.usda", "/World/Props")
            ```
        """
        return self.add_usd_reference_async(layer_file, prefix_path).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def add_usd_reference_async(self, layer_file: str, prefix_path: str) -> Operation[Any]:
        """Add a USD file as a reference at a prim path (asynchronous).

        Returns immediately with an Operation for manual control.

        Args:
            layer_file: Path to the USD file to add as a reference.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            Operation that can be polled or waited on with custom timeout.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result, usd_handle = self._bindings.add_usd_reference_from_file(self._handle, layer_file, prefix_path)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue add_usd_reference: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=usd_handle,
            operation_name=f"add_usd_reference({layer_file})",
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def add_usd_reference_from_string(self, layer_content: str, prefix_path: str) -> Any:
        """Add inline USDA content as a reference at a prim path (synchronous).

        Blocks until the reference is fully loaded.

        Args:
            layer_content: USDA content as a Python string. Must set defaultPrim
                for reference composition to work correctly.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            USD handle for the added reference (for use with remove_usd).

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, or loading fails.
            ValueError: If layer_content is empty.

        Note:
            A USD reference is namespace-encapsulated: any relationship or path
            target that points outside ``prefix_path`` is dropped during
            composition. Keep targets self-contained within the reference layer,
            for example a ``RenderProduct`` whose ``rel camera`` points at a
            ``Camera`` defined in the same layer.

        Example:
            ```python
            renderer.open_usd("/path/to/scene.usda")
            renderer.add_usd_reference_from_string('''
            #usda 1.0
            (defaultPrim = "Render")
            def Scope "Render" {
                def Camera "Camera" {}
                def RenderProduct "Product" { rel camera = </Render/Camera> }
            }
            ''', prefix_path="/Render")
            ```
        """
        return self.add_usd_reference_from_string_async(layer_content, prefix_path).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def add_usd_reference_from_string_async(self, layer_content: str, prefix_path: str) -> Operation[Any]:
        """Add inline USDA content as a reference at a prim path (asynchronous).

        Returns immediately with an Operation for manual control.

        Args:
            layer_content: USDA content as a Python string. Must set defaultPrim
                for reference composition to work correctly.
            prefix_path: Absolute prim path where the reference will be created.

        Returns:
            Operation that can be polled or waited on with custom timeout.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If layer_content is empty.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if not layer_content or not layer_content.strip():
            raise ValueError("layer_content cannot be empty")

        result, usd_handle = self._bindings.add_usd_reference_from_string(self._handle, layer_content, prefix_path)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue add_usd_reference_from_string: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=usd_handle,
            operation_name="add_usd_reference_from_string(<inline>)",
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def remove_usd(self, usd_handle: Any) -> None:
        """Remove a previously added USD from the runtime stage.

        Args:
            usd_handle: Handle returned from add_usd_reference() or add_usd_reference_from_string().

        Raises:
            RuntimeError: If the removal fails.
        """
        self.remove_usd_async(usd_handle).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def remove_usd_async(self, usd_handle: Any) -> Operation[bool]:
        """Remove a previously added USD (async).

        Args:
            usd_handle: Handle returned from add_usd_reference() or add_usd_reference_from_string().

        Returns:
            Operation that completes when USD is removed.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.remove_usd(self._handle, usd_handle)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue remove_usd: {error_msg}")

        return Operation(renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name="remove_usd")

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def update_from_usd_time(self, usd_time: float) -> None:
        """Update runtime stage to a specific USD time (synchronous).

        Blocks until all time-sampled attributes are re-evaluated.

        Args:
            usd_time: Stage time in **seconds** (not USD timecodes). The runtime
                converts to timecodes via the stage's ``timeCodesPerSecond`` metadata.

        Raises:
            RuntimeError: If the update fails.
        """
        self.update_from_usd_time_async(usd_time).wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def update_from_usd_time_async(self, usd_time: float) -> Operation[bool]:
        """Update runtime stage to a specific USD time (asynchronous).

        Returns immediately with an Operation for manual control.

        Args:
            usd_time: Stage time in **seconds** (not USD timecodes). The runtime
                converts to timecodes via the stage's ``timeCodesPerSecond`` metadata.

        Returns:
            Operation that completes when the update finishes.

        Raises:
            RuntimeError: If the enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.update_stage_from_usd_time(self._handle, usd_time)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue update_from_usd_time: {error_msg}")

        return Operation(
            renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name="update_from_usd_time"
        )

    @deprecated(_OVSTAGE_CLONE_REPLACEMENT)
    def clone_usd(self, source_path: str, target_paths: List[str]) -> None:
        """Clone a USD subtree to one or more target paths.

        Creates copies of the prim at source_path at each target path.

        Args:
            source_path: Path to the source prim to clone.
            target_paths: List of target paths for the clones.

        Raises:
            RuntimeError: If the clone operation fails.
            ValueError: If target_paths is empty.
        """
        self.clone_usd_async(source_path, target_paths).wait()

    @deprecated(_OVSTAGE_CLONE_REPLACEMENT)
    def clone_usd_async(self, source_path: str, target_paths: List[str]) -> Operation[bool]:
        """Clone a USD subtree (async).

        Args:
            source_path: Path to the source prim to clone.
            target_paths: List of target paths for the clones.

        Returns:
            Operation that completes when cloning is done.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If target_paths is empty.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if not target_paths:
            raise ValueError("At least one target path is required")

        source_string = bindings.ovx_string_t(source_path)
        target_strings = [bindings.ovx_string_t(path) for path in target_paths]
        target_array = (bindings.ovx_string_t * len(target_strings))(*target_strings)

        result = self._bindings.clone_usd(self._handle, source_string, target_array, len(target_strings))
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue clone_usd: {error_msg}")

        op = Operation(renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name="clone_usd")
        op._storage_refs = [source_string, target_strings, target_array]
        return op

    def _wait_operation(self, operation: Operation, timeout_ns: Optional[int]) -> Operation._Result:
        """Internal: Wait for an operation to complete.

        Args:
            operation: The operation to wait for.
            timeout_ns: Timeout in nanoseconds. None or negative means infinite timeout.

        Returns:
            Operation._Result with status and any errors.
        """
        # Use infinite timeout if None or negative
        if timeout_ns is None or timeout_ns < 0:
            timeout = bindings.OVRTX_TIMEOUT_INFINITE
        else:
            timeout = bindings.ovrtx_timeout_t(time_out_ns=timeout_ns)

        result, c_wait_result = self._bindings.wait_op(self._handle, bindings.ovrtx_op_id_t(operation.op_id), timeout)

        # Determine result state
        errors = []
        has_errors = False
        is_timeout = False

        if result.status != bindings.OVRTX_API_SUCCESS:
            if result.status == bindings.OVRTX_API_TIMEOUT:
                is_timeout = True
            else:
                has_errors = True
                error_msg = self._bindings.get_last_error() or "Unknown error"
                errors.append(error_msg)

        # Extract per-operation errors from wait_result
        if c_wait_result.num_error_ops > 0:
            has_errors = True
            for i in range(c_wait_result.num_error_ops):
                failed_op_id = c_wait_result.error_op_ids[i]
                error_msg = self._bindings.get_last_op_error(failed_op_id)
                errors.append(f"op {failed_op_id.value}: {error_msg}")

        # Set value and errors based on outcome
        # Status is inferred: errors imply failed, value=None implies timeout, value implies completed
        return Operation._Result(value=None if (has_errors or is_timeout) else operation._handle, errors=errors)

    def _query_op_status(self, op_id: int) -> OperationStatus:
        """Query status of an operation (internal — called by Operation.query_status).

        Calls the C query, copies fields into a Python dataclass, and
        immediately releases the C status struct.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result, c_status = self._bindings.query_op_status(self._handle, bindings.ovrtx_op_id_t(op_id))
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to query operation status: {error_msg}")

        try:
            counters = [
                OperationCounter(
                    name=str(c_status.counters[i].name),
                    current=c_status.counters[i].current,
                    total=c_status.counters[i].total,
                )
                for i in range(c_status.counter_count)
            ]
            status = OperationStatus(
                state=EventStatus(c_status.state),
                progress=c_status.progress,
                counters=counters,
            )
        finally:
            self._bindings.release_op_status(self._handle, c_status)

        return status

    def step(
        self, render_products: set[str], delta_time: float, *, ordinal: Optional[int] = None
    ) -> RenderProductSetOutputs[Any]:
        """Step the renderer (synchronous - blocks until complete).

        Enqueues a step operation, waits for rendering to complete, and returns results.
        Equivalent to ``step_async(...).wait().fetch()`` with infinite
        timeouts for both the operation wait and the result fetch.

        When an ovstage is attached, the step first synchronizes the renderer with
        committed Stage changes through ``ordinal``. BORROW keeps attribute values
        shared; REPLICATE copies committed data into the renderer-owned stage.

        Args:
            render_products: Set of render product paths to step.
            delta_time: Time delta for the simulation step.
            ordinal: Minimum committed publication required from the attached
                ovstage. Execution may observe that publication or a later one.
                Required in attached mode and invalid in standalone mode.

        Returns:
            :class:`RenderProductSetOutputs` with rendering results.

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, step fails,
                fetch fails, or ordinal use does not match attachment state.
            TypeError: If ``ordinal`` is not an integer.
            ValueError: If no valid render products are provided or ``ordinal``
                is outside the uint64 range.
        """
        return self.step_async(render_products, delta_time, ordinal=ordinal).wait().fetch()

    def step_async(
        self,
        render_products: set[str],
        delta_time: float,
        *,
        ordinal: Optional[int] = None,
    ) -> "Operation[PendingFetch[RenderProductSetOutputs]]":
        """Step the renderer (asynchronous - returns immediately).

        Enqueues a step operation and returns an :class:`Operation`. Call
        ``.wait()`` to get a :class:`PendingFetch`, then ``.fetch()``
        to retrieve the :class:`RenderProductSetOutputs`.

        When an ovstage is attached, the step first enqueues synchronization with
        committed Stage changes through ``ordinal``. BORROW keeps attribute values
        shared; REPLICATE copies committed data into the renderer-owned stage.

        Args:
            render_products: Set of render product paths to step.
            delta_time: Time delta for the simulation step.
            ordinal: Minimum committed publication required from the attached
                ovstage. Execution may observe that publication or a later one.
                Required in attached mode and invalid in standalone mode.

        Returns:
            ``Operation[PendingFetch[RenderProductSetOutputs]]``

        Raises:
            RuntimeError: If renderer is invalid, enqueue fails, or ordinal use
                does not match attachment state.
            TypeError: If ``ordinal`` is not an integer.
            ValueError: If no valid render products are provided or ``ordinal``
                is outside the uint64 range.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        attached = self._attached_ovstage is not None
        if attached and ordinal is None:
            raise RuntimeError("ordinal is required while an ovstage is attached")
        if not attached and ordinal is not None:
            raise RuntimeError("ordinal is only valid while an ovstage is attached")
        ordinal_value = self._normalize_ordinal(ordinal) if ordinal is not None else None

        if delta_time < 0:
            raise ValueError(f"delta_time must be non-negative, got {delta_time}")

        render_products_strings = [
            bindings.ovx_string_t(prod) for prod in render_products if prod and str(prod).strip()
        ]

        if not render_products_strings:
            raise ValueError("At least one valid render product is required to step the renderer")

        render_products_array = (bindings.ovx_string_t * len(render_products_strings))(*render_products_strings)
        render_product_set = bindings.ovrtx_render_product_set_t(
            render_products=render_products_array, num_render_products=len(render_products_strings)
        )

        update_op_id = None
        if ordinal_value is None:
            result, step_result_handle = self._bindings.step(self._handle, render_product_set, delta_time)
            operation_name = f"step(dt={delta_time})"
        else:
            update_result = self._bindings.update_from_stage(self._handle, ordinal_value)
            if update_result.status != bindings.OVRTX_API_SUCCESS:
                error_msg = self._bindings.get_last_error() or "Unknown error"
                raise RuntimeError(f"Failed to enqueue update_from_stage: {error_msg}")
            update_op_id = update_result.op_index.value
            result, step_result_handle = self._bindings.step_with_stage(
                self._handle, render_product_set, delta_time, ordinal_value
            )
            operation_name = f"step(dt={delta_time}, ordinal={ordinal_value})"

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            if update_op_id is not None:
                # The Stage update was already accepted; drain it before raising
                # so an enqueue rejection does not leave an unobserved operation.
                try:
                    self._bindings.wait_op(
                        self._handle, bindings.ovrtx_op_id_t(update_op_id), bindings.OVRTX_TIMEOUT_INFINITE
                    )
                except Exception:
                    pass
            raise RuntimeError(f"Failed to enqueue step: {error_msg}")

        def _fetch_step(timeout_ns: Optional[int] = None) -> Optional[RenderProductSetOutputs]:
            # Called by PendingFetch.fetch(). Retrieves the C step outputs,
            # walks the products / frames / render variables, and builds
            # RenderProductSetOutputs. On failure, destroys the C step result
            # handle to prevent leaks.
            try:
                return self._fetch_step_results(step_result_handle, timeout_ns)
            except Exception as e:
                try:
                    self._bindings.destroy_results(self._handle, step_result_handle)
                except Exception:
                    pass
                raise RuntimeError(f"Failed to fetch step results: {e}") from e

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=step_result_handle,
            operation_name=operation_name,
            fetch_fn=_fetch_step,
            cleanup_fn=lambda: self._bindings.destroy_results(self._handle, step_result_handle),
        )

    def reset(self, time: float = 0.0) -> None:
        """Reset sensor simulation history to a specific time.

        Clears accumulated rendering history for all render products and
        sets the simulation start time for future step() calls.

        Args:
            time: Simulation time to reset to (default: 0.0).

        Raises:
            RuntimeError: If the reset fails.
        """
        self.reset_async(time).wait()

    def reset_async(self, time: float = 0.0) -> Operation[bool]:
        """Reset sensor simulation history (async).

        Args:
            time: Simulation time to reset to (default: 0.0).

        Returns:
            Operation that completes when reset is done.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.reset(self._handle, time)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue reset: {error_msg}")

        return Operation(renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name="reset")

    def enqueue_pick_query_async(
        self,
        render_product_path: str,
        left_ndc: float,
        top_ndc: float,
        right_ndc: float,
        bottom_ndc: float,
        *,
        flags: int = 0,
    ) -> Operation[bool]:
        """Enqueue an NDC viewport pick rectangle for the next ``step()`` on this RenderProduct (async).

        Results appear on the next ``step()`` as the multi-tensor render variable
        ``OVRTX_RENDER_VAR_PICK_HIT``. If multiple queries target the same
        RenderProduct before a step, the last one wins.

        Args:
            render_product_path: Target RenderProduct path.
            left_ndc, top_ndc, right_ndc, bottom_ndc: Pick rectangle in normalized RenderProduct
                coordinates. Values use [0, 1] top-left-origin NDC: x increases left-to-right and
                y increases top-to-bottom. The rectangle uses the same convention as the old pixel API:
                right_ndc and bottom_ndc mark the edge just past the last included pixel. For pixel
                (x, y) on a width x height RenderProduct, use [x / width, y / height, (x + 1) / width,
                (y + 1) / height]. Use [0, 0, 1, 1] for the full RenderProduct. Out-of-bounds values are
                rejected; boundary values may be clamped to the valid range to account for floating-point
                roundoff.
            flags: Combination of ``OVRTX_PICK_FLAG_*``.

        Returns:
            Operation that completes once the pick query is registered.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If ``render_product_path`` is empty.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        path = (render_product_path or "").strip()
        if not path:
            raise ValueError("render_product_path must be non-empty")
        rp = bindings.ovx_string_t(path)
        desc = bindings.ovrtx_pick_query_desc_t()
        desc.render_product_path = rp
        desc.left_ndc = float(left_ndc)
        desc.top_ndc = float(top_ndc)
        desc.right_ndc = float(right_ndc)
        desc.bottom_ndc = float(bottom_ndc)
        desc.flags = int(flags)
        result = self._bindings.enqueue_pick_query(self._handle, desc)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue pick query: {error_msg}")
        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"enqueue_pick_query({path!r})",
        )
        op._storage_refs = [rp, desc]
        return op

    def enqueue_pick_query(
        self,
        render_product_path: str,
        left_ndc: float,
        top_ndc: float,
        right_ndc: float,
        bottom_ndc: float,
        *,
        flags: int = 0,
    ) -> None:
        """Enqueue an NDC viewport pick rectangle for the next ``step()`` on this RenderProduct (blocking).

        Equivalent to ``enqueue_pick_query_async(...).wait()``.
        See :meth:`enqueue_pick_query_async` for argument details.
        """
        self.enqueue_pick_query_async(render_product_path, left_ndc, top_ndc, right_ndc, bottom_ndc, flags=flags).wait()

    def set_selection_group_styles(self, styles: dict[int, SelectionGroupStyle]) -> None:
        """Set per-group outline and fill colors for selection groups (blocking).

        Equivalent to ``set_selection_group_styles_async(styles).wait()``.
        See :meth:`set_selection_group_styles_async` for argument details.
        """
        self.set_selection_group_styles_async(styles).wait()

    def set_selection_group_styles_async(self, styles: dict[int, SelectionGroupStyle]) -> Operation[bool]:
        """Set per-group outline and fill colors for selection groups (async).

        Stream-ordered: takes effect on the next ``step()`` after it completes.
        If multiple writes target the same group id, the last writer wins.
        Outline thickness and fill mode are configured at renderer creation
        via :attr:`RendererConfig.selection_outline_width` and
        :attr:`RendererConfig.selection_fill_mode`.

        Args:
            styles: Mapping from group id (``0..255``) to a :class:`SelectionGroupStyle`.
                Group ids match the per-prim id passed to
                :meth:`set_selection_outline_group`. An empty mapping enqueues a no-op.

        Returns:
            Operation that completes once the styling state has been applied.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If any group id is outside ``0..255`` or any color is not
                a 4-element RGBA sequence.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        count = len(styles)
        ids_array = (ctypes.c_uint8 * count)()
        styles_array = (bindings.ovrtx_selection_group_style_t * count)()
        for i, (group_id, style) in enumerate(styles.items()):
            gid = int(group_id)
            if not 0 <= gid <= 255:
                raise ValueError(f"selection group id {gid} out of range; expected 0..255")
            if len(style.outline_color) != 4 or len(style.fill_color) != 4:
                raise ValueError(
                    f"selection group {gid}: outline_color and fill_color must each have 4 RGBA components"
                )
            ids_array[i] = gid
            styles_array[i].outline_color = (ctypes.c_float * 4)(*style.outline_color)
            styles_array[i].fill_color = (ctypes.c_float * 4)(*style.fill_color)

        result = self._bindings.set_selection_group_styles(self._handle, ids_array, styles_array, count)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue set_selection_group_styles: {error_msg}")

        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"set_selection_group_styles({count} group(s))",
        )
        op._storage_refs = [ids_array, styles_array]
        return op

    @staticmethod
    def _normalize_prim_path_ids(prim_path_ids: list[int]) -> list[int]:
        ids = []
        for prim_path_id in prim_path_ids:
            if isinstance(prim_path_id, bool):
                raise ValueError("prim path id must be a non-zero uint64 integer, not bool")
            value = int(prim_path_id)
            if value <= 0 or value > 0xFFFFFFFFFFFFFFFF:
                raise ValueError(f"prim path id {value} out of range; expected non-zero uint64")
            ids.append(value)
        return ids

    @staticmethod
    def _normalize_selection_group_ids(group_ids: int | list[int], count: int) -> list[int]:
        if isinstance(group_ids, bool):
            raise ValueError("selection group id must be an integer in 0..255, not bool")
        if isinstance(group_ids, int):
            groups = [int(group_ids)] * count
        else:
            groups = []
            for group_id in group_ids:
                if isinstance(group_id, bool):
                    raise ValueError("selection group id must be an integer in 0..255, not bool")
                groups.append(int(group_id))
        if len(groups) != count:
            raise ValueError(f"group_ids length ({len(groups)}) must match prim path count ({count})")
        for group_id in groups:
            if not 0 <= group_id <= 255:
                raise ValueError(f"selection group id {group_id} out of range; expected 0..255")
        return groups

    def set_selection_outline_group(self, prim_path_ids: list[int], group_ids: int | list[int]) -> None:
        """Set each prim's selection outline group by path id (blocking).

        Equivalent to ``set_selection_outline_group_async(...).wait()``.
        See :meth:`set_selection_outline_group_async` for argument details.
        """
        self.set_selection_outline_group_async(prim_path_ids, group_ids).wait()

    def set_selection_outline_group_async(self, prim_path_ids: list[int], group_ids: int | list[int]) -> Operation[bool]:
        """Set each prim's selection outline group by path id (async).

        Stream-ordered: takes effect on the next ``step()`` after it completes.
        Pass group ``0`` to clear a prim's selection outline. A scalar group id
        applies to every path; a list must have one group id per path.
        Duplicate path ids are allowed; the last occurrence wins.

        Args:
            prim_path_ids: Path ids from this renderer's pick-hit ``primPath`` tensor or own path dictionary.
            group_ids: Group id or parallel list of group ids, each in ``0..255``.

        Returns:
            Operation that completes once the renderer selection state has been applied.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If any group id is outside ``0..255`` or list lengths differ.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        path_ids = self._normalize_prim_path_ids(prim_path_ids)
        count = len(path_ids)
        groups = self._normalize_selection_group_ids(group_ids, count)

        path_array = (ctypes.c_uint64 * count)(*path_ids)
        group_array = (ctypes.c_uint8 * count)(*groups)
        result = self._bindings.set_selection_outline_group(self._handle, path_array, count, group_array)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue set_selection_outline_group: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"set_selection_outline_group({count} prim(s))",
        )

    def set_selection_outline_group_strings(self, prim_paths: list[str], group_ids: int | list[int]) -> None:
        """Set each prim's selection outline group by string path (blocking).

        Duplicate paths are allowed; the last occurrence wins.
        """
        self.set_selection_outline_group_strings_async(prim_paths, group_ids).wait()

    def set_selection_outline_group_strings_async(
        self, prim_paths: list[str], group_ids: int | list[int]
    ) -> Operation[bool]:
        """Set each prim's selection outline group by string path (async).

        Duplicate paths are allowed; the last occurrence wins.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        if any(not path or not path.strip() for path in prim_paths):
            raise ValueError(f"all prim_paths must not be empty, got: {prim_paths}")

        count = len(prim_paths)
        groups = self._normalize_selection_group_ids(group_ids, count)

        path_strings = [bindings.ovx_string_t(path) for path in prim_paths]
        path_array = (bindings.ovx_string_t * count)(*path_strings)
        group_array = (ctypes.c_uint8 * count)(*groups)
        result = self._bindings.set_selection_outline_group_strings(self._handle, path_array, count, group_array)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue set_selection_outline_group_strings: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"set_selection_outline_group_strings({count} prim(s))",
        )

    def set_pickable(self, prim_path_ids: list[int], pickable: bool | list[bool]) -> None:
        """Set viewport pickability for prims by path id (blocking).

        Equivalent to ``set_pickable_async(...).wait()``.
        See :meth:`set_pickable_async` for argument details.
        """
        self.set_pickable_async(prim_path_ids, pickable).wait()

    def set_pickable_async(self, prim_path_ids: list[int], pickable: bool | list[bool]) -> Operation[bool]:
        """Set viewport pickability for prims by path id (async).

        Stream-ordered: takes effect on the next ``step()`` after it completes.
        A scalar value applies to every path; a list must have one value per path.

        Args:
            prim_path_ids: Path ids from this renderer's pick-hit ``primPath`` tensor or own path dictionary.
            pickable: Pickability value or parallel list of values.

        Returns:
            Operation that completes once the renderer pickability state has been applied.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
            ValueError: If list lengths differ.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        path_ids = self._normalize_prim_path_ids(prim_path_ids)
        count = len(path_ids)
        values = [bool(pickable)] * count if isinstance(pickable, bool) else [bool(value) for value in pickable]
        if len(values) != count:
            raise ValueError(f"pickable length ({len(values)}) must match prim path count ({count})")

        path_array = (ctypes.c_uint64 * count)(*path_ids)
        pickable_array = (ctypes.c_bool * count)(*values)
        result = self._bindings.set_pickable(self._handle, path_array, count, pickable_array)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue set_pickable: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"set_pickable({count} prim(s))",
        )

    def set_pickable_strings(self, prim_paths: list[str], pickable: bool | list[bool]) -> None:
        """Set viewport pickability for prims by string path (blocking)."""
        self.set_pickable_strings_async(prim_paths, pickable).wait()

    def set_pickable_strings_async(self, prim_paths: list[str], pickable: bool | list[bool]) -> Operation[bool]:
        """Set viewport pickability for prims by string path (async)."""
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        if any(not path or not path.strip() for path in prim_paths):
            raise ValueError(f"all prim_paths must not be empty, got: {prim_paths}")

        count = len(prim_paths)
        values = [bool(pickable)] * count if isinstance(pickable, bool) else [bool(value) for value in pickable]
        if len(values) != count:
            raise ValueError(f"pickable length ({len(values)}) must match prim_paths length ({count})")

        path_strings = [bindings.ovx_string_t(path) for path in prim_paths]
        path_array = (bindings.ovx_string_t * count)(*path_strings)
        pickable_array = (ctypes.c_bool * count)(*values)
        result = self._bindings.set_pickable_strings(self._handle, path_array, count, pickable_array)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue set_pickable_strings: {error_msg}")

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"set_pickable_strings({count} prim(s))",
        )

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def reset_stage(self) -> None:
        """Reset stage to empty state.

        Clears all USD content from the runtime stage. After this call,
        the stage will be empty and new USD content can be loaded.

        Raises:
            RuntimeError: If the reset fails.
        """
        self.reset_stage_async().wait()

    @deprecated(_OVSTAGE_POPULATION_REPLACEMENT)
    def reset_stage_async(self) -> Operation[bool]:
        """Reset stage to empty state (async).

        Returns:
            Operation that completes when stage is cleared.

        Raises:
            RuntimeError: If renderer is invalid or enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.reset_stage(self._handle)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue reset_stage: {error_msg}")

        return Operation(renderer=self, op_id=result.op_index.value, handle=_VOID_RESULT, operation_name="reset_stage")

    # ========================================================================
    # Stage query and attribute read operations
    # ========================================================================

    @deprecated(_OVSTAGE_QUERY_REPLACEMENT)
    def query_prims(
        self,
        require_all: Optional[list[tuple[int, str]]] = None,
        require_any: Optional[list[tuple[int, str]]] = None,
        exclude: Optional[list[tuple[int, str]]] = None,
        attribute_filter_mode: int = bindings.AttributeFilterMode.NONE,
        attribute_names: Optional[list[str]] = None,
    ) -> dict[str, dict[str, AttributeInfo]]:
        """Query prims from the runtime stage (synchronous).

        Finds prims matching the specified filters and returns a dict
        mapping prim paths to their :class:`AttributeInfo` descriptors.
        Equivalent to ``query_prims_async(...).wait().fetch()`` with infinite
        timeouts for both the operation wait and the result fetch.

        **Filter logic**: A prim is included when it matches *every* filter in
        ``require_all`` **and** *at least one* filter in ``require_any`` **and**
        *none* of the filters in ``exclude``. Omitted lists impose no constraint
        (i.e. ``require_all=None`` means no mandatory filters). Each filter is
        a ``(kind, name)`` tuple where *kind* selects the match type:

        - :attr:`FilterKind.PRIM_TYPE` — match by USD type name
          (e.g. ``"Mesh"``, ``"SphereLight"``).
        - :attr:`FilterKind.HAS_ATTRIBUTE` — match by attribute existence
          (e.g. ``"points"``, ``"radius"``).

        **Attribute reporting**: ``attribute_filter_mode`` controls how much
        attribute metadata is included per prim in the result:

        - :attr:`AttributeFilterMode.NONE` — no attribute descriptors;
          the per-prim dicts are empty. Use this for lightweight prim
          counting or path discovery.
        - :attr:`~AttributeFilterMode.ALL` — every attribute on each prim
          is reported as an :class:`AttributeInfo`.
        - :attr:`~AttributeFilterMode.SPECIFIC` — only the attributes
          named in ``attribute_names`` are reported.

        Args:
            require_all: AND filters — prim must match all of them.
            require_any: OR filters — prim must match at least one.
            exclude: NOT filters — prim must match none of them.
            attribute_filter_mode: Attribute reporting level.
            attribute_names: Attribute names to report when mode is
                :attr:`~AttributeFilterMode.SPECIFIC`.

        Returns:
            :class:`dict[str, dict[str, AttributeInfo]]` (dict-like, context manager).

        Raises:
            RuntimeError: If query fails.
        """
        return (
            self.query_prims_async(
                require_all=require_all,
                require_any=require_any,
                exclude=exclude,
                attribute_filter_mode=attribute_filter_mode,
                attribute_names=attribute_names,
            )
            .wait()
            .fetch()
        )

    @deprecated(_OVSTAGE_QUERY_REPLACEMENT)
    def query_prims_async(
        self,
        require_all: Optional[list[tuple[int, str]]] = None,
        require_any: Optional[list[tuple[int, str]]] = None,
        exclude: Optional[list[tuple[int, str]]] = None,
        attribute_filter_mode: int = bindings.AttributeFilterMode.NONE,
        attribute_names: Optional[list[str]] = None,
    ) -> "Operation[PendingFetch[dict[str, dict[str, AttributeInfo]]]]":
        """Query prims from the runtime stage (non-blocking).

        Enqueues the query and returns an :class:`Operation`. Call
        ``.wait()`` to get a :class:`PendingFetch`, then ``.fetch()``
        to retrieve the :class:`dict[str, dict[str, AttributeInfo]]`.

        Args:
            require_all: Filters the prim must match (AND). Each tuple is
                ``(FilterKind.PRIM_TYPE, "Mesh")`` or ``(FilterKind.HAS_ATTRIBUTE, "radius")``.
            require_any: Filters the prim must match at least one of (OR).
            exclude: Filters the prim must not match (NOT).
            attribute_filter_mode: Which attributes to report per group
                (:attr:`AttributeFilterMode.NONE`, :attr:`~AttributeFilterMode.ALL`,
                or :attr:`~AttributeFilterMode.SPECIFIC`).
            attribute_names: Attribute names to report when mode is
                :attr:`~AttributeFilterMode.SPECIFIC`.

        Returns:
            ``Operation[PendingFetch[dict[str, dict[str, AttributeInfo]]]]``

        Raises:
            RuntimeError: If enqueue fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        # Build filter arrays
        def build_filters(filter_list):
            if not filter_list:
                return None, 0
            c_filters = (bindings.ovrtx_filter_t * len(filter_list))()
            string_refs = []
            for i, (kind, name) in enumerate(filter_list):
                c_filters[i].kind = kind
                s = bindings.ovx_string_t(name)
                string_refs.append(s)
                c_filters[i].name.string = s
                c_filters[i].name.token = 0
            return c_filters, len(filter_list), string_refs

        all_filters, all_count, _all_refs = build_filters(require_all) if require_all else (None, 0, [])
        any_filters, any_count, _any_refs = build_filters(require_any) if require_any else (None, 0, [])
        exc_filters, exc_count, _exc_refs = build_filters(exclude) if exclude else (None, 0, [])

        # Build attribute filter
        attr_filter = bindings.ovrtx_attribute_filter_t()
        attr_filter.mode = attribute_filter_mode
        _attr_name_refs = []
        if attribute_filter_mode == bindings.AttributeFilterMode.SPECIFIC and attribute_names:
            c_attr_names = (bindings.ovx_string_or_token_t * len(attribute_names))()
            for i, name in enumerate(attribute_names):
                s = bindings.ovx_string_t(name)
                _attr_name_refs.append(s)
                c_attr_names[i].string = s
                c_attr_names[i].token = 0
            attr_filter.attribute_names = c_attr_names
            attr_filter.attribute_name_count = len(attribute_names)

        # Build query desc
        query_desc = bindings.ovrtx_query_desc_t()
        query_desc.require_all = all_filters
        query_desc.require_all_count = all_count
        query_desc.require_any = any_filters
        query_desc.require_any_count = any_count
        query_desc.exclude = exc_filters
        query_desc.exclude_count = exc_count
        query_desc.attribute_filter = attr_filter

        enqueue_result, query_handle = self._bindings.query_prims(self._handle, query_desc)
        if enqueue_result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue query_prims: {error_msg}")

        pd = self._get_path_dict()  # cached; captured by _fetch_query closure for token resolution

        def _fetch_query(timeout_ns: Optional[int] = None) -> Optional[dict[str, dict[str, AttributeInfo]]]:
            # Called by PendingFetch.fetch(). Retrieves C query results,
            # resolves token handles to strings via the path dictionary,
            # and builds the user-facing dict mapping each prim path to its attributes.
            timeout = bindings.OVRTX_TIMEOUT_INFINITE if timeout_ns is None else timeout_ns
            result, c_qr = self._bindings.fetch_query_results(self._handle, query_handle, timeout)
            if result.status == bindings.OVRTX_API_TIMEOUT:
                return None
            if result.status != bindings.OVRTX_API_SUCCESS:
                self._bindings.release_query_results(self._handle, query_handle)
                error_msg = self._bindings.get_last_error() or "Unknown error"
                raise RuntimeError(f"Failed to fetch query results: {error_msg}")
            prim_dict: dict[str, dict[str, AttributeInfo]] = {}
            for gi in range(c_qr.group_count):
                c_group = c_qr.groups[gi]
                attrs: dict[str, AttributeInfo] = {}
                for ai in range(c_group.attribute_count):
                    ad = c_group.attributes[ai]
                    name = pd.token_to_string(ad.name)
                    if name:
                        attrs[name] = AttributeInfo(
                            name=name,
                            dtype=ad.type.dtype,
                            is_array=ad.type.is_array,
                            semantic=Semantic(ad.type.semantic.value),
                        )
                group = _PrimGroup(
                    prim_count=c_group.prim_count,
                    prim_list_handle=c_group.prim_list_handle,
                    attributes=attrs,
                    _path_dict=pd,
                )
                for path in group.prim_paths:
                    prim_dict[path] = group.attributes
            # All C data resolved into Python objects — release C handle immediately
            self._bindings.release_query_results(self._handle, query_handle)
            return prim_dict

        op = Operation(
            renderer=self,
            op_id=enqueue_result.op_index.value,
            handle=query_handle,
            operation_name="query_prims",
            fetch_fn=_fetch_query,
            cleanup_fn=lambda: self._bindings.release_query_results(self._handle, query_handle),
        )
        op._storage_refs = [_all_refs, _any_refs, _exc_refs, _attr_name_refs]
        return op

    def _get_path_dict(self) -> bindings.path_dictionary_instance_t:
        """Return the cached path dictionary, creating it on first call.

        The C path dictionary is valid for the renderer's lifetime, so
        one allocation serves all queries.

        Raises:
            RuntimeError: If retrieval fails.
        """
        if self._path_dict is not None:
            return self._path_dict
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")
        result, pd = self._bindings.get_path_dictionary(self._handle)
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to get path dictionary: {error_msg}")
        self._path_dict = pd
        return pd

    def resolve_prim_path_id(self, prim_path_id: int) -> str:
        """Resolve an ovrtx prim-path id to a USD prim path string.

        Pick-hit records store path-dictionary ids rather than strings. Use
        this helper to turn a hit record's ``prim_path`` field into a path such
        as ``"/World/Cube"``.
        """
        return self._get_path_dict().prim_path_to_string(int(prim_path_id))

    @deprecated(_OVSTAGE_READ_REPLACEMENT)
    def read_attribute(
        self,
        attribute_name: str,
        prim_paths: list[str],
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        dest: Optional[Any] = None,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> ManagedDLTensor:
        """Read a scalar attribute (synchronous, one value per prim).

        Returns a DLPack-compatible tensor for use with NumPy, Warp, PyTorch,
        or any ``from_dlpack()`` consumer::

            tensor = renderer.read_attribute("radius", ["/World/Sphere"])
            arr = np.from_dlpack(tensor)

        When ``dest`` is provided, data is written directly into the caller's
        tensor (supports GPU tensors for zero-copy reads). The return value
        wraps the same memory as ``dest`` — both are usable.

        Equivalent to ``read_attribute_async(...).wait().fetch()``.

        Args:
            attribute_name: Name of the attribute (e.g. ``"radius"``).
            prim_paths: USD prim paths to read from.
            prim_mode: Prim binding mode (default:
                :attr:`PrimMode.EXISTING_ONLY`).
            dest: Optional pre-allocated DLPack-compatible tensor. When
                provided, data is written directly into it. Accepts any
                object with ``__dlpack__()``.
            cuda_stream: Optional CUDA stream handle (``int``) on which you coordinate
                work with ``dest``. ovrtx waits on this stream before writing and
                signals on it when done, and forwards it to the DLPack producer of
                ``dest`` so any prior work on a different stream is synchronized
                automatically. If omitted, the caller must ensure ``dest``'s state is
                fully settled before calling.
            cuda_event: Optional CUDA event handle (``int``). Sets the
                access sync wait event (waited on before writing to ``dest``).

        Returns:
            :class:`ManagedDLTensor`

        Raises:
            RuntimeError: If the read fails.
            TypeError: If ``dest`` does not support the DLPack protocol.
        """
        return (
            self.read_attribute_async(
                attribute_name=attribute_name,
                prim_paths=prim_paths,
                prim_mode=prim_mode,
                dest=dest,
                cuda_stream=cuda_stream,
                cuda_event=cuda_event,
            )
            .wait()
            .fetch()
        )

    @deprecated(_OVSTAGE_READ_REPLACEMENT)
    def read_attribute_async(
        self,
        attribute_name: str,
        prim_paths: list[str],
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        dest: Optional[Any] = None,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> "Operation[PendingFetch[ManagedDLTensor]]":
        """Read a scalar attribute (non-blocking, one value per prim).

        Enqueues the read and returns an :class:`Operation`. Call
        ``.wait()`` then ``.fetch()`` to retrieve the tensor::

            op = renderer.read_attribute_async("radius", ["/World/Sphere"])
            pending = op.wait(timeout_ns=5_000_000_000)    # None on timeout
            tensor = pending.fetch(timeout_ns=100_000_000)  # None on timeout
            arr = np.from_dlpack(tensor)

        When ``dest`` is provided, data is written directly into the caller's
        tensor (supports GPU tensors for zero-copy reads). The fetched tensor
        wraps the same memory as ``dest`` — both are usable.

        Args:
            attribute_name: Name of the attribute (e.g. ``"radius"``).
            prim_paths: USD prim paths to read from.
            prim_mode: Prim binding mode (default:
                :attr:`PrimMode.EXISTING_ONLY`).
            dest: Optional pre-allocated DLPack-compatible tensor. When
                provided, data is written directly into it. Accepts any
                object with ``__dlpack__()``.
            cuda_stream: Optional CUDA stream handle (``int``) on which you coordinate
                work with ``dest``. ovrtx waits on this stream before writing and
                signals on it when done, and forwards it to the DLPack producer of
                ``dest`` so any prior work on a different stream is synchronized
                automatically. If omitted, the caller must ensure ``dest``'s state is
                fully settled before calling.
            cuda_event: Optional CUDA event handle (``int``). Sets the
                access sync wait event (waited on before writing to ``dest``).

        Returns:
            ``Operation[PendingFetch[ManagedDLTensor]]``

        Raises:
            RuntimeError: If enqueue fails.
            TypeError: If ``dest`` does not support the DLPack protocol.
        """
        dest_dl = DLTensor.from_dlpack(dest, stream=cuda_stream) if dest is not None else None

        def _result_fn_scalar(guard, managed_tensors):
            if dest_dl is not None:
                return ManagedDLTensor(dest_dl, manager_ctx=guard, deleter_callback=None, readonly=False)
            return managed_tensors[0]

        return self._read_attribute_internal(
            attribute_name=attribute_name,
            prim_paths=prim_paths,
            prim_mode=prim_mode,
            dest=dest,
            dest_dl=dest_dl,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
            result_fn=_result_fn_scalar,
        )

    @deprecated(_OVSTAGE_READ_REPLACEMENT)
    def read_array_attribute(
        self,
        attribute_name: str,
        prim_paths: list[str],
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
    ) -> dict[str, ManagedDLTensor]:
        """Read an array attribute (synchronous, variable-length per prim).

        Returns a dict mapping prim paths to DLPack-compatible tensors,
        for use with NumPy, Warp, PyTorch, or any ``from_dlpack()``
        consumer. Iteration order matches ``prim_paths``::

            tensors = renderer.read_array_attribute("points", prim_paths)
            for path, tensor in tensors.items():
                arr = np.from_dlpack(tensor)

        Equivalent to ``read_array_attribute_async(...).wait().fetch()``.

        Args:
            attribute_name: Name of the attribute (e.g. ``"points"``).
            prim_paths: USD prim paths to read from.
            prim_mode: Prim binding mode (default:
                :attr:`PrimMode.EXISTING_ONLY`).

        Returns:
            ``dict[str, ManagedDLTensor]``

        Raises:
            RuntimeError: If the read fails.
        """
        return (
            self.read_array_attribute_async(
                attribute_name=attribute_name,
                prim_paths=prim_paths,
                prim_mode=prim_mode,
            )
            .wait()
            .fetch()
        )

    @deprecated(_OVSTAGE_READ_REPLACEMENT)
    def read_array_attribute_async(
        self,
        attribute_name: str,
        prim_paths: list[str],
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
    ) -> "Operation[PendingFetch[dict[str, ManagedDLTensor]]]":
        """Read an array attribute (non-blocking, variable-length per prim).

        Enqueues the read and returns an :class:`Operation`. Call
        ``.wait()`` then ``.fetch()`` to retrieve the tensor dict::

            op = renderer.read_array_attribute_async("points", prim_paths)
            pending = op.wait(timeout_ns=5_000_000_000)    # None on timeout
            tensors = pending.fetch(timeout_ns=100_000_000) # None on timeout
            for path, tensor in tensors.items():
                arr = np.from_dlpack(tensor)

        Args:
            attribute_name: Name of the attribute (e.g. ``"points"``).
            prim_paths: USD prim paths to read from.
            prim_mode: Prim binding mode (default:
                :attr:`PrimMode.EXISTING_ONLY`).

        Returns:
            ``Operation[PendingFetch[dict[str, ManagedDLTensor]]]``

        Raises:
            RuntimeError: If enqueue fails.
        """
        return self._read_attribute_internal(
            attribute_name=attribute_name,
            prim_paths=prim_paths,
            prim_mode=prim_mode,
            dest=None,
            dest_dl=None,
            cuda_stream=None,
            cuda_event=None,
            result_fn=lambda guard, managed_tensors: dict(zip(prim_paths, managed_tensors)),
        )

    def _read_attribute_internal(
        self,
        attribute_name: str,
        prim_paths: list[str],
        prim_mode: PrimMode,
        dest: Optional[Any],
        dest_dl: Optional[DLTensor],
        cuda_stream: Optional[int],
        cuda_event: Optional[int],
        result_fn,  # (_Guard, list[ManagedDLTensor]) -> ManagedDLTensor (scalar) or dict (array)
    ) -> Operation:
        """Internal: enqueue a read operation and return an Operation with a fetch closure."""
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        binding = bindings.ovrtx_binding_desc_or_handle_t()
        binding.binding_handle = 0

        _string_refs = []
        prim_strings = [bindings.ovx_string_t(p) for p in prim_paths]
        _string_refs.extend(prim_strings)
        prim_array = (bindings.ovx_string_t * len(prim_strings))(*prim_strings)
        _string_refs.append(prim_array)
        binding.binding_desc.prim_list = bindings.ovrtx_prim_list_t(prim_paths=prim_array, num_paths=len(prim_strings))

        attr_str = bindings.ovx_string_t(attribute_name)
        _string_refs.append(attr_str)
        binding.binding_desc.attribute_name.string = attr_str
        binding.binding_desc.attribute_name.token = 0

        binding.binding_desc.prim_mode = bindings.ovrtx_binding_prim_mode_t(prim_mode)

        read_dest = None
        if dest is not None and dest_dl is not None:
            _string_refs.append(dest_dl)
            read_dest = bindings.ovrtx_read_dest_t()
            read_dest.tensor = ctypes.pointer(dest_dl)
            access_sync = bindings.ovrtx_cuda_sync_t()
            done_sync = bindings.ovrtx_cuda_sync_t()
            if cuda_stream is not None:
                access_sync.stream = cuda_stream
                done_sync.stream = cuda_stream
            if cuda_event is not None:
                access_sync.wait_event = cuda_event
            read_dest.access_cuda_sync = access_sync
            read_dest.done_cuda_sync = done_sync

        enqueue_result, read_handle = self._bindings.read_attribute(self._handle, binding, read_dest)
        if enqueue_result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue read_attribute: {error_msg}")

        # Idempotent release shared by fetch-error paths, _Guard.__del__ (success), and
        # Operation.cleanup_fn (never-waited). The sentinel prevents PendingFetch.__del__
        # from re-running a failed fetch and calling release_read_result a second time.
        released = False

        def _release_once() -> None:
            nonlocal released
            if released:
                return
            released = True
            self._bindings.release_read_result(self._handle, read_handle)

        def _fetch_read(timeout_ns: Optional[int] = None):
            if released:
                raise RuntimeError("Read result has already been released after a prior fetch failure")

            timeout = bindings.OVRTX_TIMEOUT_INFINITE if timeout_ns is None else timeout_ns
            result, c_output = self._bindings.fetch_read_result(self._handle, read_handle, timeout)
            if result.status == bindings.OVRTX_API_TIMEOUT:
                return None
            if result.status != bindings.OVRTX_API_SUCCESS:
                _release_once()
                error_msg = self._bindings.get_last_error() or "Unknown error"
                raise RuntimeError(f"Failed to fetch read result: {error_msg}")

            if c_output.prim_count == 0:
                _release_once()
                raise RuntimeError(
                    f"Read returned no data for '{attribute_name}' (attribute may not exist on the given prims)"
                )

            dl_tensors = [c_output.buffers[i].dl for i in range(c_output.buffer_count)]

            class _Guard:
                def __init__(self, renderer):
                    self._renderer = renderer
                    self._refs = (c_output, dl_tensors)  # ctypes keepalive

                def __del__(self):
                    if self._renderer._handle is not None:
                        _release_once()

            guard = _Guard(self)

            managed_tensors = [
                ManagedDLTensor(dl, manager_ctx=guard, deleter_callback=None, readonly=True) for dl in dl_tensors
            ]
            return result_fn(guard, managed_tensors)

        op = Operation(
            renderer=self,
            op_id=enqueue_result.op_index.value,
            handle=read_handle,
            operation_name="read_attribute",
            fetch_fn=_fetch_read,
            cleanup_fn=_release_once,
        )
        op._storage_refs = [_string_refs]
        return op

    def _fetch_step_results(
        self,
        step_handle: Any,
        timeout_ns: Optional[int],
    ) -> Optional[RenderProductSetOutputs]:
        """Internal: Fetch rendering results from the C API.

        Args:
            step_handle: Step result handle (ovrtx_step_result_handle_t).
            timeout_ns: Timeout in nanoseconds. None = infinite.

        Returns:
            :class:`RenderProductSetOutputs`, or None on timeout.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if timeout_ns is None or timeout_ns < 0:
            timeout = bindings.OVRTX_TIMEOUT_INFINITE
        else:
            timeout = bindings.ovrtx_timeout_t(time_out_ns=timeout_ns)

        result, c_outputs = self._bindings.fetch_results(self._handle, step_handle, timeout)
        if result.status == bindings.OVRTX_API_TIMEOUT:
            return None
        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to fetch step results: {error_msg}")

        ignored_render_vars = ["LdrColor0", "LdrColor1", "LdrColor2", "HdrColor0", "HdrColor1", "HdrColor2"]
        products = {}
        for c_product in c_outputs.outputs[: c_outputs.output_count]:
            frames = []
            for c_frame in c_product.output_frames[: c_product.output_frame_count]:
                render_vars = []
                for c_var in c_frame.output_render_vars[: c_frame.render_var_count]:
                    if (var_name := str(c_var.render_var_name)) not in ignored_render_vars:
                        render_vars.append(RenderVarOutput(name=var_name, handle=c_var.output_handle, renderer=self))
                frames.append(
                    FrameOutput(
                        start_time=c_frame.frame_start_time,
                        end_time=c_frame.frame_end_time,
                        render_vars={var.name: var for var in render_vars},
                        progression=int(c_frame.accumulation_status.progression),
                        converged=bool(c_frame.accumulation_status.converged),
                    )
                )
            product_name = str(c_product.render_product_path)
            products[product_name] = ProductOutput(name=product_name, frames=frames)

        def _destroy():
            if self._handle is not None:
                self._bindings.destroy_results(self._handle, step_handle)

        return RenderProductSetOutputs(destroy_fn=_destroy, products=products)

    def _map_output(
        self,
        output_handle: bindings.ovrtx_render_var_output_handle_t,
        device_type: int,
        sync_stream: Optional[int] = None,
    ) -> "MappedRenderVar":
        """Internal: Map render variable output and construct a MappedRenderVar.

        Decodes the C struct's strings to Python ``str`` and copies each ``DLTensor`` by
        value into Python-owned instances. The DLTensor pointer fields (data / shape /
        strides) continue to reference C-side memory whose lifetime is tied to the
        ``map_handle`` — the C unmap fires only when the returned ``MappedRenderVar``
        instance's refcount hits zero.

        Args:
            output_handle: Render variable output handle (from a fetched RenderProductSetOutputs).
            device_type: Device type constant (OVRTX_MAP_DEVICE_TYPE_*).
            sync_stream: CUDA stream handle for render completion sync. The stream will wait
                for render to complete before any subsequent work executes. Default: 1 for
                CUDA (default stream), 0 for CPU.

        Returns:
            A populated :class:`MappedRenderVar`, registered with the renderer's
            live-mappings table.

        Raises:
            RuntimeError: If mapping fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        # Default sync_stream: 1 for CUDA types (default stream), 0 for CPU
        if sync_stream is None:
            sync_stream = 0 if device_type == bindings.Device.CPU else 1
        map_desc = bindings.ovrtx_map_output_description_t(device_type=device_type, sync_stream=sync_stream)
        result, c_output = self._bindings.map_render_var_output(
            self._handle, output_handle, ctypes.byref(map_desc), bindings.OVRTX_TIMEOUT_INFINITE
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to map output: {error_msg}")

        # Check if the rendered output itself is valid (not just the API call)
        if c_output.status != bindings.EventStatus.COMPLETED:
            if c_output.status == bindings.EventStatus.FAILURE:
                error_msg = str(c_output.error_message) if c_output.error_message.ptr else "Unknown error"
                raise RuntimeError(f"Render variable output failed: {error_msg}")
            raise RuntimeError(f"Render variable output not ready (status={c_output.status})")

        # Render variable description fields snapshot: decode strings to Python str; version is signed int.
        name = str(c_output.name)
        type_ = str(c_output.type)
        doc = str(c_output.doc)
        version = int(c_output.version)

        # Snapshot per-tensor records: (name, doc, dl). dl is a Python-owned by-value copy
        # of the C-side DLTensor; its inner pointers (data, shape, strides) reference C
        # memory tied to map_handle.
        tensors_list = []
        for i in range(c_output.num_tensors):
            c_tensor = c_output.tensors[i]
            t_name = str(c_tensor.name.contents) if c_tensor.name else ""
            t_doc = str(c_tensor.doc.contents) if c_tensor.doc else ""
            dl_copy = bindings.DLTensor.from_buffer_copy(bytes(c_tensor.dl.contents))
            tensors_list.append((t_name, t_doc, dl_copy))

        # Snapshot per-param records: param.dl is by-value DLTensor inline in the C struct.
        params_list = []
        for i in range(c_output.num_params):
            c_param = c_output.params[i]
            p_name = str(c_param.name)
            p_doc = str(c_param.doc)
            dl_copy = bindings.DLTensor.from_buffer_copy(bytes(c_param.dl))
            params_list.append((p_name, p_doc, dl_copy))

        map_handle = c_output.map_handle
        device = bindings.Device(device_type)

        # 0 from C means "no wait needed" (CPU mapping, or all tensors CPU-resident).
        # Translate to None at the boundary so the Python type is honest.
        wait_event_raw = int(c_output.cuda_sync.wait_event)
        wait_event = wait_event_raw if wait_event_raw != 0 else None

        # Construct the MappedRenderVar; its __init__ registers a small _UnmapState
        # adapter with this renderer's _live_mappings table so that _force_unmap_all
        # can fire C unmap on teardown without forming a reference cycle between this
        # renderer and the mapping (which would prevent __del__ from firing on user
        # release).
        from .types import MappedRenderVar  # local import: types.py imports renderer types lazily.

        return MappedRenderVar(
            renderer=self,
            map_handle=map_handle,
            device=device,
            name=name,
            type=type_,
            doc=doc,
            version=version,
            tensors=tensors_list,
            params=params_list,
            wait_event=wait_event,
        )

    def _unmap_output(
        self,
        map_handle: bindings.ovrtx_render_var_output_map_handle_t,
        before_destroy_cuda_sync: Optional[bindings.ovrtx_cuda_sync_t] = None,
    ) -> None:
        """Internal: Unmap render variable output.

        Args:
            map_handle: Map handle from a prior :meth:`_map_output` call.
            before_destroy_cuda_sync: Optional CUDA sync to wait for before destroying/reusing
                the mapped memory. Pass None for no sync (default).

        Raises:
            RuntimeError: If unmapping fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        result = self._bindings.unmap_render_var_output(self._handle, map_handle, before_destroy_cuda_sync)

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to unmap output: {error_msg}")

    @staticmethod
    def _to_c_config(config: RendererConfig) -> bindings.ovrtx_config_t:
        """Convert RendererConfig to C structure.

        Uses a whitelist of known config fields. Only whitelisted fields are converted
        to C config entries.
        """
        # Whitelist: field_name -> (factory_function, config_key_enum)
        # Field names must match RendererConfig dataclass fields.
        # Config key enums must match their C header counterparts in both name and
        # integer value (see ovrtx_config_bool_t / ovrtx_config_string_t in ovrtx_types.h).
        # Factories accept native Python types (bool / str) and handle lifetime internally.
        WHITELIST = {
            "sync_mode": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.SYNC_MODE),
            "log_file_path": (bindings.ovrtx_config_entry_string, bindings.ConfigStringKey.LOG_FILE_PATH),
            "log_level": (bindings.ovrtx_config_entry_string, bindings.ConfigStringKey.LOG_LEVEL),
            "enable_profiling": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.ENABLE_PROFILING),
            "read_gpu_transforms": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.READ_GPU_TRANSFORMS),
            "keep_system_alive": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.KEEP_SYSTEM_ALIVE),
            "active_cuda_gpus": (bindings.ovrtx_config_entry_string, bindings.ConfigStringKey.ACTIVE_CUDA_GPUS),
            "use_vulkan": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.USE_VULKAN),
            "selection_outline_enabled": (
                bindings.ovrtx_config_entry_bool,
                bindings.ConfigBoolKey.SELECTION_OUTLINE_ENABLED,
            ),
            "selection_outline_width": (
                bindings.ovrtx_config_entry_int,
                bindings.ConfigInt64Key.SELECTION_OUTLINE_WIDTH,
            ),
            "selection_fill_mode": (
                bindings.ovrtx_config_entry_int,
                bindings.ConfigInt64Key.SELECTION_FILL_MODE,
            ),
            "enable_geometry_streaming": (
                bindings.ovrtx_config_entry_bool,
                bindings.ConfigBoolKey.ENABLE_GEOMETRY_STREAMING,
            ),
            "enable_geometry_streaming_lod": (
                bindings.ovrtx_config_entry_bool,
                bindings.ConfigBoolKey.ENABLE_GEOMETRY_STREAMING_LOD,
            ),
            "enable_spg": (bindings.ovrtx_config_entry_bool, bindings.ConfigBoolKey.ENABLE_SPG),
            "motion_bvh": (bindings.ovrtx_config_entry_int, bindings.ConfigInt64Key.MOTION_BVH),
            "_attach_mode": (bindings.ovrtx_config_entry_int, bindings.ConfigInt64Key._ATTACH_MODE),
        }

        entries: List[bindings.ovrtx_config_entry_t] = []
        for field_name, (factory, key) in WHITELIST.items():
            value = getattr(config, field_name, None)
            if value is not None:
                if field_name == "motion_bvh":
                    value = int(Renderer._normalize_motion_bvh(value))
                elif field_name == "_attach_mode":
                    value = int(Renderer._normalize_attach_mode(value))
                entries.append(factory(key, value))

        return bindings.ovrtx_config_t(entries)

    @staticmethod
    def _normalize_motion_bvh(value: bindings.MotionBvh | int | str) -> bindings.MotionBvh:
        if isinstance(value, bindings.MotionBvh):
            return value
        if isinstance(value, int):
            return bindings.MotionBvh(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            try:
                return bindings.MotionBvh[normalized.upper()]
            except KeyError:
                return bindings.MotionBvh(int(normalized))
        raise ValueError(
            f"Invalid motion_bvh value {value!r}; expected MotionBvh, int 0..2, or 'disable'/'enable'/'auto'"
        )

    @staticmethod
    def _normalize_attach_mode(value: bindings._AttachMode | int | str) -> bindings._AttachMode:
        if isinstance(value, bindings._AttachMode):
            return value
        if isinstance(value, int):
            return bindings._AttachMode(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            try:
                return bindings._AttachMode[normalized.upper()]
            except KeyError:
                return bindings._AttachMode(int(normalized))
        raise ValueError(f"Invalid _attach_mode value {value!r}; expected _AttachMode, int 0..1, or 'borrow'/'replicate'")

    @staticmethod
    def _normalize_ordinal(value: Any, *, name: str = "ordinal") -> int:
        if isinstance(value, bool):
            raise TypeError(f"{name} must be an integer ordinal, not bool")
        try:
            ordinal = operator.index(value)
        except TypeError as e:
            raise TypeError(f"{name} must be an integer ordinal, got {type(value).__name__}") from e
        if not 0 <= ordinal <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError(f"{name} must be in the uint64 range, got {ordinal}")
        return ordinal

    @staticmethod
    def _normalize_tensor_for_write(semantic_constant: int, tensor: DLTensor) -> DLTensor:
        """Validate and optionally pass through a DLTensor for write_attribute.

        For semantics that support Python shape-compatible input (e.g. XFORM_MAT4x4),
        tensors with a single component and the expected trailing shape (e.g.
        (N, 4, 4)) are accepted by the Python API. Tensors with the canonical
        multi-component dtype (e.g. 16 components) are also passed through unchanged.
        Binding metadata still uses the C API's lane-based attribute type.

        Args:
            semantic_constant: Parsed semantic constant (OVRTX_SEMANTIC_*).
            tensor: Input DLTensor to validate and optionally pass through.

        Returns:
            The same tensor (pass-through) when shape/dtype are valid for this semantic.

        Raises:
            ValueError: If tensor has one component but shape does not match the
                       expected layout for the given semantic.
        """
        # Layout-compatible rules mapping each semantic to (source_dtype code/bits, trailing_shape_dims, target_lanes).
        _LAYOUT_RULES = {
            bindings.Semantic.XFORM_MAT4x4: (
                DLDataType(code=DLDataTypeCode.kDLFloat, bits=64, lanes=1),
                (4, 4),
                16,
            ),
        }

        if (rule := _LAYOUT_RULES.get(semantic_constant)) is None:
            return tensor  # No rules for NONE or unknown semantics

        source_dtype, trailing_dims, target_lanes = rule
        expected_ndim = 1 + len(trailing_dims)

        # Pass-through: tensor already has the canonical multi-lane dtype (e.g. shape (N,) lanes=16).
        if tensor.dtype.lanes == target_lanes:
            return tensor

        # Pass-through: Python shape-compatible input (lanes=1, shape (N, 4, 4)).
        # The binding descriptor carries the lane-based C attribute type.
        if tensor.dtype.lanes != 1:
            return tensor

        if tensor.dtype.code.value != source_dtype.code.value or tensor.dtype.bits != source_dtype.bits:
            return tensor  # Let _resolve_semantic_and_dtype catch the mismatch

        if tensor.shape is not None and tensor.ndim == expected_ndim:
            actual_trailing = tuple(tensor.shape[1 + i] for i in range(len(trailing_dims)))
            if actual_trailing == trailing_dims:
                return tensor  # Keep the Python-provided tensor metadata.

        _shape_str = "unknown" if tensor.shape is None else str(tuple(tensor.shape[i] for i in range(tensor.ndim)))
        _expected_shape = "(N, " + ", ".join(str(d) for d in trailing_dims) + ")"
        raise ValueError(
            f"write_attribute: tensor shape {_shape_str} does not match expected shape "
            f"{_expected_shape} for this semantic. Provide a tensor with the correct shape."
        )

    @staticmethod
    def _is_string_semantic(semantic: int) -> bool:
        """Return True if the semantic represents a string type (token or path)."""
        return semantic in (Semantic.TOKEN_STRING, Semantic.PATH_STRING)

    @staticmethod
    def _is_layout_compatible_semantic(semantic: int) -> bool:
        """Return True if the semantic allows layout-compatible tensor input (same code/bits, component count may differ)."""
        return semantic == Semantic.XFORM_MAT4x4

    @staticmethod
    def _strings_to_dltensor(strings: list[str]) -> DLTensor:
        """Convert a list of Python strings to a DLTensor of ovx_string_t structs.

        Each string is encoded as UTF-8 and stored in an ovx_string_t (ptr + length).
        The resulting DLTensor has dtype (kDLUInt, 128, 1) matching sizeof(ovx_string_t).

        Args:
            strings: List of Python strings to convert.

        Returns:
            DLTensor wrapping a contiguous array of ovx_string_t. Internal storage
            (byte buffers and shape array) is kept alive via _string_conversion_storage.
        """
        n = len(strings)
        string_array = (bindings.ovx_string_t * n)()
        for i, s in enumerate(strings):
            string_array[i] = bindings.ovx_string_t(s)

        shape_array = (ctypes.c_int64 * 1)(n)

        tensor = DLTensor(
            data=ctypes.cast(string_array, ctypes.c_void_p),
            device=DLDevice(device_type=DLDeviceType.kDLCPU, device_id=0),
            ndim=1,
            dtype=DLDataType(code=DLDataTypeCode.kDLUInt, bits=128, lanes=1),
            shape=ctypes.cast(shape_array, ctypes.POINTER(ctypes.c_int64)),
            strides=None,
            byte_offset=0,
        )
        # Keep ctypes arrays alive for the lifetime of the DLTensor
        tensor._string_conversion_storage = {"string_array": string_array, "shape_array": shape_array}

        return tensor

    def _resolve_semantic_and_dtype(
        self, semantic: Semantic, dtype: Optional[DLDataType], context: str = "operation"
    ) -> tuple[int, DLDataType]:
        """Resolve dtype from semantic, validating any user-provided dtype.

        Semantics imply specific dtype requirements determined by the C library's
        internal representation. When a semantic is provided, the dtype is inferred
        automatically; user-provided dtypes are validated against the expected type.

        Args:
            semantic: Semantic enum value.
            dtype: User-provided dtype (optional if semantic implies dtype).
            context: Context string for error messages.

        Returns:
            Tuple of (semantic_constant, semantic_dtype).

        Raises:
            ValueError: If dtype is required but not provided,
                       or if provided dtype doesn't match semantic.
        """
        if semantic == Semantic.XFORM_MAT4x4:
            inferred_dtype = DLDataType(code=DLDataTypeCode.kDLFloat, bits=64, lanes=16)
            layout_compatible = True  # Python accepts shape-compatible input, e.g. lanes=1 with shape (N,4,4).
        elif semantic in (Semantic.TOKEN_STRING, Semantic.PATH_STRING):
            inferred_dtype = DLDataType(code=DLDataTypeCode.kDLUInt, bits=128, lanes=1)
            layout_compatible = False
        else:
            inferred_dtype = None  # NONE — user must provide dtype
            layout_compatible = False

        if inferred_dtype is not None:
            if dtype is not None:
                code_bits_ok = dtype.code.value == inferred_dtype.code.value and dtype.bits == inferred_dtype.bits
                if layout_compatible:
                    if not code_bits_ok:
                        raise ValueError(
                            f"{context}: provided dtype (code={dtype.code}, bits={dtype.bits}, "
                            f"components={dtype.lanes}) must match scalar type for {semantic!r} "
                            f"(code={inferred_dtype.code}, bits={inferred_dtype.bits}); "
                            f"component count may differ for layout-compatible input "
                            f"(e.g. shape (N, 4, 4) with 1 component)."
                        )
                else:
                    if not (code_bits_ok and dtype.lanes == inferred_dtype.lanes):
                        raise ValueError(
                            f"{context}: provided dtype (code={dtype.code}, bits={dtype.bits}, "
                            f"components={dtype.lanes}) doesn't match required dtype for {semantic!r} "
                            f"(code={inferred_dtype.code}, bits={inferred_dtype.bits}, "
                            f"components={inferred_dtype.lanes})"
                        )
            semantic_dtype = inferred_dtype
        elif dtype is None:
            raise ValueError(f"{context}: dtype is required when semantic is Semantic.NONE")
        else:
            semantic_dtype = dtype

        return (semantic, semantic_dtype)

    _DTYPE_MAP = {
        "float16": (DLDataTypeCode.kDLFloat, 16),
        "float32": (DLDataTypeCode.kDLFloat, 32),
        "float64": (DLDataTypeCode.kDLFloat, 64),
        "int8": (DLDataTypeCode.kDLInt, 8),
        "int16": (DLDataTypeCode.kDLInt, 16),
        "int32": (DLDataTypeCode.kDLInt, 32),
        "int64": (DLDataTypeCode.kDLInt, 64),
        "uint8": (DLDataTypeCode.kDLUInt, 8),
        "uint16": (DLDataTypeCode.kDLUInt, 16),
        "uint32": (DLDataTypeCode.kDLUInt, 32),
        "uint64": (DLDataTypeCode.kDLUInt, 64),
        "bool": (DLDataTypeCode.kDLBool, 8),
    }

    _PYTHON_BUILTIN_DTYPE_MAP = {
        float: "float64",
        int: "int64",
        bool: "bool",
    }

    _KIND_MAP = {
        "f": DLDataTypeCode.kDLFloat,
        "i": DLDataTypeCode.kDLInt,
        "u": DLDataTypeCode.kDLUInt,
        "b": DLDataTypeCode.kDLBool,
    }

    @staticmethod
    def _resolve_new_dtype_and_shape(
        dtype: Any, shape: Optional[tuple], context: str = "operation"
    ) -> tuple[int, DLDataType, Optional[tuple]]:
        """Translate new-style dtype + shape to (semantic_constant, DLDataType, shape).

        Args:
            dtype: Element type. Accepts string names (``"float32"``, ``"token"``, ``"path"``),
                NumPy dtypes (``np.float32``, ``np.dtype("float64")``), any object with
                ``.kind``/``.itemsize`` attributes (CuPy, JAX dtypes), or Python built-ins
                (``float``, ``int``).
            shape: Optional element shape tuple (e.g. (3,) for float3, (4, 4) for matrix4d).
            context: Context string for error messages.

        Returns:
            Tuple of (semantic_constant, resolved_DLDataType, shape).
        """
        if isinstance(dtype, str):
            if dtype == "token":
                return (Semantic.TOKEN_STRING, DLDataType(code=DLDataTypeCode.kDLUInt, bits=128, lanes=1), None)
            if dtype == "path":
                return (Semantic.PATH_STRING, DLDataType(code=DLDataTypeCode.kDLUInt, bits=128, lanes=1), None)
            dtype_str = dtype
        elif dtype in Renderer._PYTHON_BUILTIN_DTYPE_MAP:
            dtype_str = Renderer._PYTHON_BUILTIN_DTYPE_MAP[dtype]
        elif isinstance(dtype, type) and Renderer._DTYPE_MAP.get(getattr(dtype, "__name__", "")) is not None:
            dtype_str = dtype.__name__
        else:
            # Duck-type: np.dtype instance (has .kind + .itemsize directly)
            if hasattr(dtype, "kind") and hasattr(dtype, "itemsize"):
                code = Renderer._KIND_MAP.get(dtype.kind)
                if code is None:
                    raise ValueError(
                        f"{context}: dtype={dtype!r} is not a supported numeric type. "
                        f"Use a float, int, uint, or bool dtype (e.g. np.float32, np.int32, np.uint8, np.bool_)."
                    )
                bits = dtype.itemsize * 8
                lanes = math.prod(shape) if shape else 1
                return (Semantic.NONE, DLDataType(code=code, bits=bits, lanes=lanes), shape if shape else None)
            # Duck-type: objects with a .dtype property (e.g. numpy scalar type instances)
            if hasattr(dtype, "dtype") and hasattr(dtype.dtype, "kind") and hasattr(dtype.dtype, "itemsize"):
                code = Renderer._KIND_MAP.get(dtype.dtype.kind)
                if code is None:
                    raise ValueError(
                        f"{context}: dtype={dtype!r} is not a supported numeric type. "
                        f"Use a float, int, uint, or bool dtype (e.g. np.float32, np.int32, np.uint8, np.bool_)."
                    )
                bits = dtype.dtype.itemsize * 8
                lanes = math.prod(shape) if shape else 1
                return (Semantic.NONE, DLDataType(code=code, bits=bits, lanes=lanes), shape if shape else None)
            dtype_str = str(dtype)

        entry = Renderer._DTYPE_MAP.get(dtype_str)
        if entry is None:
            raise ValueError(
                f"{context}: unrecognized dtype={dtype!r}. Use a numpy dtype, Python built-in (float, int), "
                f"or a string name ('float32', 'int32', 'token', 'path', etc.)."
            )
        code, bits = entry
        lanes = math.prod(shape) if shape else 1
        return (Semantic.NONE, DLDataType(code=code, bits=bits, lanes=lanes), shape if shape else None)

    def _create_semantic_aware_dltensor(
        self, original_dl_tensor: DLTensor, semantic: int, element_shape: Optional[tuple] = None
    ) -> DLTensor:
        """Create reshaped DLTensor view for interop-friendly consumption.

        When ``element_shape`` is provided (new dtype/shape API path), reshapes
        ``(N,)`` with ``K`` components to ``(N, *element_shape)`` with a scalar element.
        When ``element_shape`` is None, applies semantic-specific reshaping
        (XFORM_MAT4x4 reshapes to ``(N, 4, 4)``).

        Args:
            original_dl_tensor: Original DLTensor from C API.
            semantic: Semantic constant (OVRTX_SEMANTIC_*).
            element_shape: Optional element shape from the new dtype/shape API.

        Returns:
            Reshaped DLTensor view (zero-copy metadata change), or the original
            tensor if no reshaping applies.
        """
        if original_dl_tensor.ndim < 1 or original_dl_tensor.shape is None:
            return original_dl_tensor

        N = original_dl_tensor.shape[0]
        lanes = original_dl_tensor.dtype.lanes

        if element_shape is not None and lanes > 1:
            new_dims = (N, *element_shape)
        elif semantic == bindings.Semantic.XFORM_MAT4x4 and lanes == 16:
            new_dims = (N, 4, 4)
        else:
            return original_dl_tensor

        ndim = len(new_dims)
        shape_array = (ctypes.c_int64 * ndim)(*new_dims)
        # Row-major contiguous strides: strides[i] = product(new_dims[i+1:]).
        # DLPack v1.2 requires strides != NULL whenever ndim != 0.
        strides_array = (ctypes.c_int64 * ndim)()
        running = 1
        for i in range(ndim - 1, -1, -1):
            strides_array[i] = running
            running *= int(new_dims[i])

        reshaped = DLTensor()
        reshaped.data = original_dl_tensor.data
        reshaped.device = original_dl_tensor.device
        reshaped.byte_offset = original_dl_tensor.byte_offset
        reshaped.ndim = ndim
        reshaped.shape = ctypes.cast(shape_array, ctypes.POINTER(ctypes.c_int64))
        reshaped.strides = ctypes.cast(strides_array, ctypes.POINTER(ctypes.c_int64))
        reshaped.dtype.code = original_dl_tensor.dtype.code
        reshaped.dtype.bits = original_dl_tensor.dtype.bits
        reshaped.dtype.lanes = 1
        reshaped._shape_storage = shape_array
        reshaped._strides_storage = strides_array
        return reshaped

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write_attribute(
        self,
        prim_paths: List[str],
        attribute_name: str,
        tensor: Any,
        semantic: Semantic = Semantic.NONE,
        dirty_bits: Optional[bytes] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> None:
        """Write scalar attribute data synchronously.

        Pass data directly — the element type and component count are inferred
        automatically from the input:

        - **Tensor input** (NumPy, Warp, or any ``__dlpack__``-compatible
          object): the element type is derived from the array's dtype and
          shape. For example, a ``float32`` array with shape ``(N, 3)``
          is interpreted as a 3-component float attribute.
        - **String input** (``list[str]``): automatically written as a token
          string attribute. One string per prim.

        For repeated writes to the same attribute, consider using
        ``bind_attribute()`` followed by ``binding.write()`` for better
        performance.

        Args:
            prim_paths: List of prim paths to write to.
            attribute_name: Name of the attribute.
            tensor: A NumPy array, Warp array, or any ``__dlpack__``-compatible
                object. One element per prim.
                For token strings, pass a ``list[str]`` instead.
            semantic: Optional attribute semantic (e.g.,
                ``Semantic.XFORM_MAT4x4``). When omitted (default), the
                element type is inferred from the input data.
            dirty_bits: Optional dirty bit array for selective updates.
            prim_mode: Prim binding mode (e.g., ``PrimMode.EXISTING_ONLY``).
            data_access: Data access mode. ``DataAccess.SYNC`` (default) copies
                input data immediately so the caller's buffer can be reused
                after this call returns. ``DataAccess.ASYNC`` references the
                caller's buffer until the operation completes (zero-copy). Not
                allowed with string data.
            cuda_stream: Optional CUDA stream handle (``int``) on which the input
                tensor's data is (or will be) ready. ovrtx synchronizes its read of
                the tensor against this stream and forwards it to the DLPack producer
                (e.g. Warp) so any pending work on a different stream is bridged
                automatically. If omitted, the caller must ensure the tensor's state
                is fully settled before calling.
            cuda_event: CUDA event handle (``int``) for GPU synchronization.

        Raises:
            RuntimeError: If renderer is invalid or write fails.
            ValueError: If invalid parameters.
            TypeError: If tensor type is not supported, or if string data is
                not a ``list[str]``.

        Example:
            ```python
            import numpy as np

            # Tensor writes — just pass the array
            points = np.random.randn(N, 3).astype(np.float32)
            renderer.write_attribute(prim_paths, "points", points)

            matrices = np.tile(np.eye(4, dtype=np.float64), (N, 1, 1))
            renderer.write_attribute(prim_paths, "xformOp:transform", matrices)

            # Token strings — auto-detected from list[str]
            renderer.write_attribute(prim_paths, "displayName", ["Cube", "Sphere"])
            ```
        """
        self.write_attribute_async(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            tensor=tensor,
            semantic=semantic,
            dirty_bits=dirty_bits,
            prim_mode=prim_mode,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        ).wait()

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write_array_attribute(
        self,
        prim_paths: List[str],
        attribute_name: str,
        tensors: List[Any],
        semantic: Semantic = Semantic.NONE,
        is_token: bool = False,
        dirty_bits: Optional[bytes] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> None:
        """Write array attribute data synchronously.

        Pass data directly — the element type and component count are inferred
        automatically from the input:

        - **Tensor input**: Each tensor corresponds to one prim. The element
          type is derived from the array's dtype and shape. Lengths may differ
          per prim.
        - **String input** (``list[list[str]]``): defaults to path/relationship
          arrays. Set ``is_token=True`` for token arrays such as custom label
          or category attributes.

        Args:
            prim_paths: List of prim paths to write to.
            attribute_name: Name of the array attribute.
            tensors: List of tensors (NumPy arrays, Warp arrays, or any
                ``__dlpack__``-compatible object), one per prim. Lengths may
                differ but element dtype must match the USD attribute schema.
                For string arrays, pass ``list[list[str]]`` instead.
            semantic: Optional attribute semantic (e.g.,
                ``Semantic.PATH_STRING``). When omitted (default), the
                element type is inferred from the input data.
            is_token: When passing ``list[list[str]]`` data, set ``True`` to write
                token arrays instead of path/relationship arrays. Ignored for
                tensor data. Default ``False``.
            dirty_bits: Optional dirty bit array for selective updates.
            prim_mode: Prim binding mode (e.g., ``PrimMode.EXISTING_ONLY``).
            data_access: Data access mode. ``DataAccess.SYNC`` (default) copies input
                data immediately. ``DataAccess.ASYNC`` references the caller's buffer
                until the operation completes (zero-copy). Not allowed with string data.
            cuda_stream: Optional CUDA stream handle (``int``) on which the input
                tensor's data is (or will be) ready. ovrtx synchronizes its read of
                the tensor against this stream and forwards it to the DLPack producer
                (e.g. Warp) so any pending work on a different stream is bridged
                automatically. If omitted, the caller must ensure the tensor's state
                is fully settled before calling.
            cuda_event: CUDA event handle (``int``) for GPU synchronization.

        Raises:
            RuntimeError: If renderer is invalid or write fails.
            ValueError: If invalid parameters or dtype mismatch.
            TypeError: If any tensor type is not supported, or if string data
                is not ``list[str]``.

        Note:
            Tensor dtype must exactly match the USD attribute's element type:

            - ``int[]`` becomes ``np.int32``
            - ``float3[]`` becomes ``np.float32`` with shape ``(N, 3)``
            - ``double3[]`` becomes ``np.float64`` with shape ``(N, 3)``

        Example:
            ```python
            import numpy as np

            # Tensor array write
            face_counts = np.array([4, 4, 4], dtype=np.int32)
            renderer.write_array_attribute(["/World/Mesh"], "faceVertexCounts", [face_counts])

            # Relationship arrays — default for list[list[str]]
            renderer.write_array_attribute(["/World/Mesh"], "material:binding",
                [["path1", "path2"]])

            # Token arrays — explicit is_token override
            renderer.write_array_attribute(["/World/Mesh"], "omni:docTokens",
                [["sensor", "validated"]], is_token=True, prim_mode=ovrtx.PrimMode.CREATE_NEW)
            ```
        """
        self.write_array_attribute_async(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            tensors=tensors,
            semantic=semantic,
            is_token=is_token,
            dirty_bits=dirty_bits,
            prim_mode=prim_mode,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        ).wait()

    def _write_attribute_by_binding(
        self,
        binding: AttributeBinding,
        tensors: List[Any],
        dirty_bits: Optional[bytes] = None,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> None:
        """Write attribute data using a binding handle synchronously (internal)."""
        self._write_attribute_by_binding_async(
            binding=binding,
            tensors=tensors,
            dirty_bits=dirty_bits,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        ).wait()

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write_attribute_async(
        self,
        prim_paths: List[str],
        attribute_name: str,
        tensor: Any,
        semantic: Semantic = Semantic.NONE,
        dirty_bits: Optional[bytes] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> Operation[bool]:
        """Write scalar attribute data asynchronously.

        See :meth:`write_attribute` for full documentation and examples.

        Returns:
            Operation for async control (yields None on completion).
        """
        return self._write_attribute_internal(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            tensors=[tensor],
            semantic=semantic,
            dirty_bits=dirty_bits,
            prim_mode=prim_mode,
            is_array=False,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        )

    @deprecated(_OVSTAGE_WRITE_REPLACEMENT)
    def write_array_attribute_async(
        self,
        prim_paths: List[str],
        attribute_name: str,
        tensors: List[Any],
        semantic: Semantic = Semantic.NONE,
        is_token: bool = False,
        dirty_bits: Optional[bytes] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> Operation[bool]:
        """Write array attribute data asynchronously.

        See :meth:`write_array_attribute` for full documentation and examples.

        Returns:
            Operation for async control (yields None on completion).
        """
        return self._write_attribute_internal(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            tensors=tensors,
            semantic=semantic,
            is_token=is_token,
            dirty_bits=dirty_bits,
            prim_mode=prim_mode,
            is_array=True,
            data_access=data_access,
            cuda_stream=cuda_stream,
            cuda_event=cuda_event,
        )

    def _write_attribute_internal(
        self,
        prim_paths: List[str],
        attribute_name: str,
        tensors: List[Any],
        semantic: Semantic,
        dirty_bits: Optional[bytes],
        prim_mode: PrimMode,
        is_array: bool,
        is_token: bool = False,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> Operation[bool]:
        """Internal: Write attribute data (shared implementation for scalar and array)."""
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if not prim_paths or not all(p and p.strip() for p in prim_paths):
            raise ValueError(f"all prim_paths must not be empty, got: {prim_paths}")

        if not tensors:
            raise ValueError("tensors list cannot be empty")

        if semantic != Semantic.NONE:
            # Explicit semantic path: resolve dtype from the semantic constant
            if semantic == Semantic.PATH_STRING and not is_array:
                raise ValueError(
                    "Semantic.PATH_STRING requires write_array_attribute (is_array=True). "
                    "Use write_array_attribute(semantic=Semantic.PATH_STRING, ...) instead of write_attribute."
                )

            if self._is_string_semantic(semantic) and data_access == DataAccess.ASYNC:
                raise ValueError("String attributes (token, path) require DataAccess.SYNC")

            if self._is_string_semantic(semantic):
                dl_tensors = []
                for i, t in enumerate(tensors):
                    if not isinstance(t, list) or not all(isinstance(s, str) for s in t):
                        raise TypeError(
                            f"tensors[{i}]: expected a list of strings for semantic {semantic!r}, "
                            f"got {type(t).__name__}"
                        )
                    dl_tensors.append(self._strings_to_dltensor(t))
                tensors = dl_tensors
            else:
                tensors = [
                    self._normalize_tensor_for_write(
                        semantic, t if isinstance(t, DLTensor) else DLTensor.from_dlpack(t, stream=cuda_stream)
                    )
                    for t in tensors
                ]

            tensor_dtype = tensors[0].dtype
            for i, t in enumerate(tensors[1:], start=1):
                if (
                    t.dtype.code.value != tensor_dtype.code.value
                    or t.dtype.bits != tensor_dtype.bits
                    or t.dtype.lanes != tensor_dtype.lanes
                ):
                    raise ValueError(
                        f"All tensors must have the same element type. "
                        f"tensors[0] has (code={tensor_dtype.code.value}, bits={tensor_dtype.bits}, "
                        f"components={tensor_dtype.lanes}), but tensors[{i}] has "
                        f"(code={t.dtype.code.value}, bits={t.dtype.bits}, components={t.dtype.lanes})"
                    )

            resolved_semantic, semantic_dtype = self._resolve_semantic_and_dtype(
                semantic, tensor_dtype, context="write_attribute"
            )
        else:
            # New path: auto-detect input type
            first = tensors[0]

            if isinstance(first, list) and all(isinstance(s, str) for s in first):
                # String input
                if data_access == DataAccess.ASYNC:
                    raise ValueError("String data requires DataAccess.SYNC")

                if not is_array:
                    resolved_semantic = Semantic.TOKEN_STRING
                else:
                    resolved_semantic = Semantic.TOKEN_STRING if is_token else Semantic.PATH_STRING

                dl_tensors = []
                for i, t in enumerate(tensors):
                    if not isinstance(t, list) or not all(isinstance(s, str) for s in t):
                        raise TypeError(
                            f"tensors[{i}]: expected a list of strings (all elements must be list[str]), "
                            f"got {type(t).__name__}"
                        )
                    dl_tensors.append(self._strings_to_dltensor(t))
                tensors = dl_tensors
                semantic_dtype = DLDataType(code=DLDataTypeCode.kDLUInt, bits=128, lanes=1)
            else:
                # Tensor / __dlpack__ input — infer component count from shape
                dl_tensors = [
                    t if isinstance(t, DLTensor) else DLTensor.from_dlpack(t, stream=cuda_stream) for t in tensors
                ]
                tensors = dl_tensors

                ref_tensor = tensors[0]
                ref_dtype = ref_tensor.dtype

                for i, t in enumerate(tensors[1:], start=1):
                    if (
                        t.dtype.code.value != ref_dtype.code.value
                        or t.dtype.bits != ref_dtype.bits
                        or t.dtype.lanes != ref_dtype.lanes
                    ):
                        raise ValueError(
                            f"All tensors must have the same element type. "
                            f"tensors[0] has (code={ref_dtype.code.value}, bits={ref_dtype.bits}, "
                            f"components={ref_dtype.lanes}), but tensors[{i}] has "
                            f"(code={t.dtype.code.value}, bits={t.dtype.bits}, components={t.dtype.lanes})"
                        )

                # Infer component count from trailing shape dimensions and tensor lanes.
                # NumPy exports lanes=1 with shape encoding (e.g. (N,3) float32 with lanes=1).
                # Warp exports structured types with lanes>1 (e.g. mat44d with lanes=16, shape=(N,)).
                # Multiplying accounts for both: 1*3=3 for NumPy, 16*1=16 for Warp mat44d.
                if ref_tensor.ndim >= 2 and ref_tensor.shape is not None:
                    trailing_dims = math.prod(ref_tensor.shape[i] for i in range(1, ref_tensor.ndim))
                else:
                    trailing_dims = 1

                semantic_dtype = DLDataType(
                    code=ref_dtype.code, bits=ref_dtype.bits, lanes=ref_dtype.lanes * trailing_dims
                )
                resolved_semantic = Semantic.NONE

        input_storage = _InputBufferStorage(
            tensors, dirty_bits=dirty_bits, cuda_stream=cuda_stream, cuda_event=cuda_event
        )

        binding_storage = _AttributeBindingDescStorage(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=semantic_dtype,
            semantic=resolved_semantic,
            prim_mode=prim_mode,
            is_array=is_array,
        )

        result = self._bindings.write_attribute(
            self._handle,
            binding_storage.binding_desc_or_handle,
            input_storage.input_buffer,
            bindings.ovrtx_data_access_t(data_access),
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue attribute write: {error_msg}")

        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"write_attribute({attribute_name})",
        )

        if data_access == DataAccess.ASYNC:
            op._storage_refs = [input_storage, binding_storage]

        return op

    def _write_attribute_by_binding_async(
        self,
        binding: AttributeBinding,
        tensors: List[Any],
        dirty_bits: Optional[bytes] = None,
        data_access: DataAccess = DataAccess.SYNC,
        cuda_stream: Optional[int] = None,
        cuda_event: Optional[int] = None,
    ) -> Operation[bool]:
        """Write attribute data using a binding handle asynchronously (returns Operation).

        Args:
            binding: AttributeBinding from bind_attribute().
            tensors: List of tensors (NumPy arrays, Warp arrays, or any
                ``__dlpack__``-compatible objects).
            dirty_bits: Optional dirty bit array for selective updates.
            data_access: Data access mode (DataAccess.SYNC or DataAccess.ASYNC).
            cuda_stream: Optional CUDA stream handle (``int``) on which the input
                tensor's data is (or will be) ready. ovrtx synchronizes its read of
                the tensor against this stream and forwards it to the DLPack producer
                (e.g. Warp) so any pending work on a different stream is bridged
                automatically. If omitted, the caller must ensure the tensor's state
                is fully settled before calling.
            cuda_event: Optional CUDA event handle for synchronization.

        Returns:
            Operation for async control (yields None on completion).

        Raises:
            RuntimeError: If renderer is invalid or write fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        if not tensors:
            raise ValueError("tensors list cannot be empty")

        if self._is_string_semantic(binding.semantic) and data_access == DataAccess.ASYNC:
            raise ValueError("String attributes (token, path) require DataAccess.SYNC")

        if self._is_string_semantic(binding.semantic):
            dl_tensors = []
            for i, t in enumerate(tensors):
                if not isinstance(t, list) or not all(isinstance(s, str) for s in t):
                    raise TypeError(
                        f"tensors[{i}]: expected a list of strings for this string attribute binding, "
                        f"got {type(t).__name__}"
                    )
                dl_tensors.append(self._strings_to_dltensor(t))
            tensors = dl_tensors
        else:
            tensors = [
                self._normalize_tensor_for_write(
                    binding.semantic,
                    t if isinstance(t, DLTensor) else DLTensor.from_dlpack(t, stream=cuda_stream),
                )
                for t in tensors
            ]

        first_dtype = tensors[0].dtype
        for i, t in enumerate(tensors[1:], start=1):
            if (
                t.dtype.code.value != first_dtype.code.value
                or t.dtype.bits != first_dtype.bits
                or t.dtype.lanes != first_dtype.lanes
            ):
                raise ValueError(
                    f"All tensors must have the same element type. "
                    f"tensors[0] has (code={first_dtype.code.value}, bits={first_dtype.bits}, "
                    f"components={first_dtype.lanes}), but tensors[{i}] has "
                    f"(code={t.dtype.code.value}, bits={t.dtype.bits}, components={t.dtype.lanes})"
                )

        expected_dtype = binding.dtype
        code_bits_ok = first_dtype.code.value == expected_dtype.code.value and first_dtype.bits == expected_dtype.bits
        lanes_ok = first_dtype.lanes == expected_dtype.lanes
        if self._is_layout_compatible_semantic(binding.semantic) or binding.shape is not None:
            if not code_bits_ok:
                raise ValueError(
                    f"Tensor element type (code={first_dtype.code.value}, bits={first_dtype.bits}, "
                    f"components={first_dtype.lanes}) must match binding's scalar type "
                    f"(code={expected_dtype.code.value}, bits={expected_dtype.bits}); "
                    f"component count may differ for layout-compatible input."
                )
        elif not (code_bits_ok and lanes_ok):
            raise ValueError(
                f"Tensor element type (code={first_dtype.code.value}, bits={first_dtype.bits}, "
                f"components={first_dtype.lanes}) doesn't match binding's expected type "
                f"(code={expected_dtype.code.value}, bits={expected_dtype.bits}, "
                f"components={expected_dtype.lanes})"
            )

        input_storage = _InputBufferStorage(
            tensors, dirty_bits=dirty_bits, cuda_stream=cuda_stream, cuda_event=cuda_event
        )

        binding_desc_or_handle = bindings.ovrtx_binding_desc_or_handle_t(
            binding_desc=bindings.ovrtx_binding_desc_t(),
            binding_handle=bindings.ovrtx_attribute_binding_handle_t(binding.handle),
        )

        result = self._bindings.write_attribute(
            self._handle,
            binding_desc_or_handle,
            input_storage.input_buffer,
            bindings.ovrtx_data_access_t(data_access),
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue attribute write: {error_msg}")

        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"write_attribute(handle={binding.handle})",
        )

        if data_access == DataAccess.ASYNC:
            op._storage_refs = [input_storage]

        return op

    @deprecated(_OVSTAGE_BINDING_REPLACEMENT)
    def bind_attribute(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any = None,
        shape: Optional[tuple] = None,
        semantic: Semantic = Semantic.NONE,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        flags: BindingFlag = BindingFlag.NONE,
    ) -> "AttributeBinding[DLTensor]":
        """Create a persistent binding for scalar attribute writes.

        Creates a binding handle that can be reused for multiple write() calls,
        avoiding the overhead of recreating the binding descriptor each time.

        Specify the attribute type using ``dtype`` and optionally ``shape``:

        - **Tensor types**: ``dtype="float32", shape=(3,)`` for ``point3f``,
          ``dtype="float64", shape=(4, 4)`` for ``matrix4d``, etc.
        - **String types**: ``dtype="token"`` or ``dtype="path"``.
        - **Scalars**: ``dtype="int32"`` (no shape needed).

        Args:
            prim_paths: List of prim paths.
            attribute_name: Name of the attribute.
            dtype: Element type. Accepts string names (``"float32"``,
                ``"float64"``, ``"int32"``, ``"token"``, ``"path"``),
                NumPy dtypes (``np.float32``, ``np.dtype("float64")``),
                any dtype object with ``.kind``/``.itemsize`` attributes
                (CuPy, JAX), Python built-ins (``float``, ``int``), or a
                ``DLDataType`` object.
            shape: Element shape tuple (e.g. ``(3,)`` for 3-component vectors,
                ``(4, 4)`` for matrices). Mandatory for multi-component types
                when using numpy dtypes or string names. Omit for scalars.
                Ignored for string types and ``DLDataType``.
            semantic: Optional attribute semantic (e.g.,
                ``Semantic.XFORM_MAT4x4``). Alternative to ``dtype``/``shape``
                for specifying the attribute type.
            prim_mode: Prim binding mode (e.g., ``PrimMode.EXISTING_ONLY``).
            flags: Binding optimization hint. ``BindingFlag.OPTIMIZE`` tells
                the runtime to optimize for frequent high-volume writes through
                this binding. Default: ``BindingFlag.NONE``.

        Returns:
            AttributeBinding[DLTensor] for scalar attribute writes.

        Example:
            ```python
            # String form — no imports needed for dtype specification:
            binding = renderer.bind_attribute(
                ["/World/Cube"], "xformOp:transform",
                dtype="float64", shape=(4, 4))

            # NumPy dtype objects also work:
            import numpy as np
            binding = renderer.bind_attribute(
                ["/World/Cube"], "visibility", dtype=np.int32)
            ```
        """
        return self.bind_attribute_async(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=dtype,
            shape=shape,
            semantic=semantic,
            prim_mode=prim_mode,
            flags=flags,
        ).wait()

    @deprecated(_OVSTAGE_BINDING_REPLACEMENT)
    def bind_attribute_async(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any = None,
        shape: Optional[tuple] = None,
        semantic: Semantic = Semantic.NONE,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        flags: BindingFlag = BindingFlag.NONE,
    ) -> "Operation[AttributeBinding[DLTensor]]":
        """Create a persistent binding for scalar attribute writes (async).

        See :meth:`bind_attribute` for full documentation and examples.
        """
        return self._bind_attribute_internal(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=dtype,
            shape=shape,
            semantic=semantic,
            prim_mode=prim_mode,
            flags=flags,
            is_array=False,
        )

    @deprecated(_OVSTAGE_BINDING_REPLACEMENT)
    def bind_array_attribute(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any = None,
        shape: Optional[tuple] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        flags: BindingFlag = BindingFlag.NONE,
    ) -> "AttributeBinding[List[DLTensor]]":
        """Create a persistent binding for array attribute writes.

        Array attributes (e.g., ``float3[] points``) may have variable lengths
        per prim. The binding locks in the element dtype; subsequent writes can
        have varying tensor lengths but must use the same element type.

        Args:
            prim_paths: List of prim paths.
            attribute_name: Name of the array attribute.
            dtype: Element type. Accepts string names (``"float32"``,
                ``"float64"``, ``"int32"``, ``"token"``, ``"path"``),
                NumPy dtypes (``np.float32``, ``np.dtype("float64")``),
                any dtype object with ``.kind``/``.itemsize`` attributes
                (CuPy, JAX), Python built-ins (``float``, ``int``), or a
                ``DLDataType`` object.
            shape: Element shape tuple (e.g. ``(3,)`` for ``float3[]``).
                Mandatory for multi-component types when using numpy dtypes
                or string names. Ignored for string types and ``DLDataType``.
            prim_mode: Prim binding mode (e.g., ``PrimMode.CREATE_NEW``).
            flags: Binding optimization hint. ``BindingFlag.OPTIMIZE`` tells
                the runtime to optimize for frequent high-volume writes through
                this binding. Default: ``BindingFlag.NONE``.

        Returns:
            AttributeBinding[List[DLTensor]] for array attribute writes.

        Example:
            ```python
            # String form — no imports needed for dtype specification:
            binding = renderer.bind_array_attribute(
                ["/World/Mesh"], "faceVertexCounts", dtype="int32")

            binding = renderer.bind_array_attribute(
                ["/World/Mesh"], "points", dtype="float32", shape=(3,))

            # NumPy dtype objects also work:
            import numpy as np
            binding = renderer.bind_array_attribute(
                ["/World/Mesh"], "normals", dtype=np.float32, shape=(3,))
            ```
        """
        return self.bind_array_attribute_async(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=dtype,
            shape=shape,
            prim_mode=prim_mode,
            flags=flags,
        ).wait()

    @deprecated(_OVSTAGE_BINDING_REPLACEMENT)
    def bind_array_attribute_async(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any = None,
        shape: Optional[tuple] = None,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
        flags: BindingFlag = BindingFlag.NONE,
    ) -> "Operation[AttributeBinding[List[DLTensor]]]":
        """Create a persistent binding for array attribute writes (async).

        See :meth:`bind_array_attribute` for full documentation and examples.
        """
        return self._bind_attribute_internal(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=dtype,
            shape=shape,
            semantic=Semantic.NONE,
            prim_mode=prim_mode,
            flags=flags,
            is_array=True,
        )

    def _bind_attribute_internal(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any,
        shape: Optional[tuple],
        semantic: Semantic,
        prim_mode: PrimMode,
        flags: BindingFlag,
        is_array: bool,
    ) -> Operation[AttributeBinding]:
        """Internal: Create attribute binding (shared implementation for scalar and array)."""
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        _ALL_BINDING_FLAGS = BindingFlag.OPTIMIZE
        if int(flags) & ~int(_ALL_BINDING_FLAGS):
            raise ValueError(
                f"Invalid binding flags: {flags!r}. "
                f"Valid flags are: {BindingFlag.NONE!r}, {BindingFlag.OPTIMIZE!r} (combinable with |)."
            )

        element_shape: Optional[tuple] = None

        if semantic != Semantic.NONE:
            # Explicit semantic: resolve dtype from the semantic constant
            if shape is not None:
                raise ValueError("shape= must not be provided when semantic= is specified")
            resolved_dtype = dtype if isinstance(dtype, DLDataType) else None
            semantic_constant, semantic_dtype = self._resolve_semantic_and_dtype(
                semantic, resolved_dtype, context="bind_attribute"
            )
        elif isinstance(dtype, DLDataType):
            # Explicit DLDataType: pass through directly with SEMANTIC_NONE
            semantic_constant = Semantic.NONE
            semantic_dtype = dtype
        elif dtype is not None:
            # New-style dtype + shape
            semantic_constant, semantic_dtype, element_shape = self._resolve_new_dtype_and_shape(
                dtype, shape, context="bind_attribute"
            )
        else:
            raise ValueError("bind_attribute: dtype is required. Use e.g. dtype='float32', shape=(3,)")

        binding_storage = _AttributeBindingDescStorage(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=semantic_dtype,
            semantic=semantic_constant,
            prim_mode=prim_mode,
            flags=flags,
            is_array=is_array,
        )

        result, handle = self._bindings.create_attribute_binding(self._handle, binding_storage.binding_desc)

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue attribute binding creation: {error_msg}")

        binding_handle = AttributeBinding(
            handle.value, semantic_constant, semantic_dtype, self, is_array=is_array, shape=element_shape
        )
        self._live_binding_handles.add(handle.value)

        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=binding_handle,
            operation_name=f"bind_attribute({attribute_name})",
        )

        op._storage_refs = [binding_storage]

        return op

    def _unbind_attribute(self, binding: AttributeBinding) -> None:
        """Destroy a persistent attribute binding handle (synchronous - waits internally).

        Args:
            binding: AttributeBinding from `bind_attribute`

        Raises:
            RuntimeError: If renderer is invalid or destruction fails
        """
        self._unbind_attribute_async(binding).wait()
        self._live_binding_handles.discard(binding.handle)

    def _unbind_attribute_async(self, binding: AttributeBinding) -> Operation[bool]:
        """Destroy a persistent attribute binding handle asynchronously (returns Operation for manual control).

        Args:
            binding: AttributeBinding from `bind_attribute`

        Returns:
            Operation[bool] for async control

        Raises:
            RuntimeError: If renderer is invalid or destruction fails
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        # Call C API
        result = self._bindings.destroy_attribute_binding(
            self._handle, bindings.ovrtx_attribute_binding_handle_t(binding.handle)
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(f"Failed to enqueue attribute binding destruction: {error_msg}")

        # Create operation
        op = Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"unbind_attribute({binding.handle})",
        )

        return op

    @deprecated(_OVSTAGE_MAP_REPLACEMENT)
    def map_attribute(
        self,
        prim_paths: List[str],
        attribute_name: str,
        dtype: Any = None,
        shape: Optional[tuple] = None,
        semantic: Semantic = Semantic.NONE,
        device: Device = Device.CPU,
        device_id: int = 0,
        prim_mode: PrimMode = PrimMode.EXISTING_ONLY,
    ) -> AttributeMapping:
        """Map attribute buffer for direct writes (synchronous, by-name).

        Returns an AttributeMapping that provides access to an internal buffer.
        Write data using NumPy, Warp, or any ``__dlpack__``-compatible library,
        then call ``unmap_attribute()`` to apply the changes.

        When ``dtype``/``shape`` are provided, the returned tensor is
        automatically shaped to match. For example, ``dtype="float32",
        shape=(3,)`` returns a tensor with shape ``(N, 3)`` and ``float32``
        dtype, ready for direct NumPy/Warp consumption.

        Note:
            Only scalar attributes (one value per prim) are supported at this time.
            Variable-length array attributes (e.g., ``point3f[] points``,
            ``int[] faceVertexCounts``) cannot be mapped because each prim may
            have a different number of elements. Use ``write_array_attribute()``
            for array attributes — it accepts per-prim tensors of varying length.

        Args:
            prim_paths: List of prim paths.
            attribute_name: Name of the attribute.
            dtype: Element type. Accepts string names (``"float32"``,
                ``"float64"``, ``"int32"``, ``"token"``, ``"path"``),
                NumPy dtypes (``np.float32``, ``np.dtype("float64")``),
                any dtype object with ``.kind``/``.itemsize`` attributes
                (CuPy, JAX), Python built-ins (``float``, ``int``), or a
                ``DLDataType`` object.
            shape: Element shape tuple (e.g. ``(3,)`` for 3-component vectors,
                ``(4, 4)`` for matrices). When provided, the mapped tensor is
                reshaped to ``(N, *shape)``. Ignored for ``DLDataType``.
            semantic: Optional attribute semantic (e.g.,
                ``Semantic.XFORM_MAT4x4``). Alternative to ``dtype``/``shape``
                for specifying the attribute type.
            device: Device for mapping (``Device.CPU`` or ``Device.CUDA``).
            device_id: Device ID (default 0, typically GPU index for CUDA).
            prim_mode: Prim binding mode (e.g., ``PrimMode.EXISTING_ONLY``).

        Returns:
            AttributeMapping with access to the internal buffer. When
            ``shape`` was provided, the tensor has dimensions ``(N, *shape)``
            with a scalar element dtype, ready for NumPy/Warp consumption.

        Raises:
            RuntimeError: If renderer is invalid or mapping fails.
            ValueError: If invalid parameters or dtype mismatch.

        Example:
            ```python
            import numpy as np

            # String form — no imports needed for dtype specification:
            mapping = renderer.map_attribute(
                ["/World/Cube"], "xformOp:transform",
                dtype="float64", shape=(4, 4))
            np.from_dlpack(mapping.tensor)[0] = np.eye(4)
            renderer.unmap_attribute(mapping)

            # NumPy dtype objects also work:
            with renderer.map_attribute(["/World/Cube"], "points",
                    dtype=np.float32, shape=(3,)) as mapping:
                np.from_dlpack(mapping.tensor)[:] = new_points
            ```
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        element_shape: Optional[tuple] = None

        if semantic != Semantic.NONE:
            # Explicit semantic: resolve dtype from the semantic constant
            if shape is not None:
                raise ValueError("shape= must not be provided when semantic= is specified")
            resolved_dtype = dtype if isinstance(dtype, DLDataType) else None
            semantic_constant, semantic_dtype = self._resolve_semantic_and_dtype(
                semantic, resolved_dtype, context="map_attribute"
            )
        elif isinstance(dtype, DLDataType):
            # Explicit DLDataType: pass through directly with SEMANTIC_NONE
            semantic_constant = Semantic.NONE
            semantic_dtype = dtype
        elif dtype is not None:
            # New-style dtype + shape
            semantic_constant, semantic_dtype, element_shape = self._resolve_new_dtype_and_shape(
                dtype, shape, context="map_attribute"
            )
        else:
            raise ValueError("map_attribute: dtype is required. Use e.g. dtype='float32', shape=(3,)")

        mapping_desc = bindings.ovrtx_mapping_desc_t(device_type=device, device_id=device_id)

        binding_storage = _AttributeBindingDescStorage(
            prim_paths=prim_paths,
            attribute_name=attribute_name,
            dtype=semantic_dtype,
            semantic=semantic_constant,
            prim_mode=prim_mode,
        )

        result, c_mapping = self._bindings.map_attribute(
            self._handle, binding_storage.binding_desc_or_handle, mapping_desc
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(
                f"Failed to map attribute '{attribute_name}': {error_msg}\n"
                "Note: array attributes (e.g., float3[] points, int[] faceVertexCounts) "
                "cannot be mapped. Use write_array_attribute() instead."
            )

        try:
            reshaped_tensor = self._create_semantic_aware_dltensor(c_mapping.dl, semantic_constant, element_shape)

            mapping = AttributeMapping(
                mapping=c_mapping,
                renderer=self,
                dltensor=reshaped_tensor,
                binding_desc=binding_storage.binding_desc,
                device=device,
            )
        except Exception:
            # C map succeeded but Python wrapper construction failed — release the C buffer
            try:
                self._bindings.unmap_attribute(
                    self._handle, bindings.ovrtx_map_handle_t(c_mapping.map_handle), bindings.ovrtx_cuda_sync_t()
                )
            except Exception:
                pass
            raise

        mapping._binding_storage = binding_storage

        return mapping

    def _map_attribute_by_binding(
        self, binding: AttributeBinding, device: Device = Device.CPU, device_id: int = 0
    ) -> AttributeMapping:
        """Map attribute buffer using a persistent binding handle (synchronous).

        Returns an AttributeMapping with access to the internal buffer.
        Write data using NumPy, Warp, or any ``__dlpack__``-compatible library,
        then call ``unmap_attribute()`` to apply the changes.

        When the binding was created with ``shape=``, the mapped tensor is
        automatically shaped to ``(N, *shape)`` with a scalar element dtype.

        Args:
            binding: AttributeBinding from bind_attribute().
            device: Device for mapping (Device.CPU or Device.CUDA).
            device_id: Device ID (default 0, typically GPU index for CUDA).

        Returns:
            AttributeMapping with access to the internal buffer.

        Raises:
            RuntimeError: If renderer is invalid or mapping fails.

        Example:
            ```python
            import numpy as np

            binding = renderer.bind_attribute(
                ["/World/Cube"], "xformOp:transform",
                dtype="float64", shape=(4, 4))
            mapping = binding.map()
            np.from_dlpack(mapping.tensor)[0] = np.eye(4)
            mapping.unmap()
            ```
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        mapping_desc = bindings.ovrtx_mapping_desc_t(device_type=device, device_id=device_id)

        binding_desc_or_handle = bindings.ovrtx_binding_desc_or_handle_t(
            binding_desc=bindings.ovrtx_binding_desc_t(),
            binding_handle=bindings.ovrtx_attribute_binding_handle_t(binding.handle),
        )

        result, c_mapping = self._bindings.map_attribute(self._handle, binding_desc_or_handle, mapping_desc)

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(
                f"Failed to map attribute: {error_msg}\n"
                "Note: array attributes (e.g., float3[] points, int[] faceVertexCounts) "
                "cannot be mapped. Use write_array_attribute() instead."
            )

        try:
            reshaped_tensor = self._create_semantic_aware_dltensor(c_mapping.dl, binding.semantic, binding.shape)

            mapping = AttributeMapping(
                mapping=c_mapping,
                renderer=self,
                dltensor=reshaped_tensor,
                binding_desc=None,
                device=device,
            )
        except Exception:
            try:
                self._bindings.unmap_attribute(
                    self._handle, bindings.ovrtx_map_handle_t(c_mapping.map_handle), bindings.ovrtx_cuda_sync_t()
                )
            except Exception:
                pass
            raise

        return mapping

    @deprecated(_OVSTAGE_UNMAP_REPLACEMENT)
    def unmap_attribute(
        self, mapping: AttributeMapping, event: Optional[int] = None, stream: Optional[int] = None
    ) -> None:
        """Commit written data to stage and free the C buffer.

        Delegates to ``mapping.unmap()`` — a synchronous blocking call.
        Data is committed to the stage when this method returns.

        Args:
            mapping: AttributeMapping from map_attribute()
            event: CUDA event handle to wait on before committing.
            stream: CUDA stream handle to synchronize before committing.

        Raises:
            ValueError: If event/stream provided for CPU-mapped attribute.
            ValueError: If both event and stream provided (mutually exclusive).
        """
        mapping.unmap(event=event, stream=stream)

    @deprecated(_OVSTAGE_UNMAP_REPLACEMENT)
    def unmap_attribute_async(
        self, mapping: AttributeMapping, event: Optional[int] = None, stream: Optional[int] = None
    ) -> Operation[bool]:
        """Enqueue attribute unmap and return an Operation for caller-managed wait.

        Delegates to ``mapping.unmap_async()``. The mapping is marked as
        unmapped immediately — ``__del__`` becomes a no-op.

        Args:
            mapping: AttributeMapping from map_attribute()
            event: CUDA event handle to wait on before committing.
            stream: CUDA stream handle to synchronize before committing.

        Returns:
            Operation[bool] for async control

        Raises:
            RuntimeError: If renderer is invalid or mapping already unmapped.
            ValueError: If event/stream provided for CPU-mapped attribute.
            ValueError: If both event and stream provided (mutually exclusive).
        """
        return mapping.unmap_async(event=event, stream=stream)

    def _enqueue_attribute_unmap(
        self,
        map_handle: int,
        cuda_sync: Optional[bindings.ovrtx_cuda_sync_t] = None,
    ) -> Operation[bool]:
        """Internal: enqueue attribute C unmap and return the Operation.

        Single internal entry point for all attribute unmap paths (sync,
        async, ``__del__``). Callers decide whether to ``.wait()`` on the
        returned Operation, return it, or discard it.

        Args:
            map_handle: Raw map handle (int) from the C mapping struct.
            cuda_sync: Optional CUDA sync to apply before committing.

        Raises:
            RuntimeError: If renderer is invalid or C call fails.
        """
        if self._handle is None:
            raise RuntimeError("Renderer is not valid")

        sync = cuda_sync or bindings.ovrtx_cuda_sync_t()

        result = self._bindings.unmap_attribute(
            self._handle,
            bindings.ovrtx_map_handle_t(map_handle),
            sync,
        )

        if result.status != bindings.OVRTX_API_SUCCESS:
            error_msg = self._bindings.get_last_error() or "Unknown error"
            raise RuntimeError(
                f"Failed to enqueue attribute unmap: {error_msg}\n"
                "Note: if this attribute is an array type (e.g., float3[] points), "
                "it cannot be mapped/unmapped. Use write_array_attribute() instead."
            )

        return Operation(
            renderer=self,
            op_id=result.op_index.value,
            handle=_VOID_RESULT,
            operation_name=f"unmap_attribute({map_handle})",
        )

    def __bool__(self) -> bool:
        """Return True if renderer is valid, False if destroyed."""
        return self._handle is not None

    @property
    def config(self) -> RendererConfig:
        """Get the configuration used to create this renderer."""
        return self._config
