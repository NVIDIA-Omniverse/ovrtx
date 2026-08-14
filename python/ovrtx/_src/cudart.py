# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Minimal libcudart bindings used by :class:`MappedRenderVar` sync helpers.

Lazy-loads libcudart on first use, so importing ovrtx on a system without
CUDA does not fail. The two runtime calls exposed here are cross-device
safe — the user's stream may live on any device, and the recorded event may
live on yet another; the runtime handles cross-context bookkeeping.
"""

import ctypes
import sys
import threading
from pathlib import Path
from typing import Optional

# CUDA 12 is the lower bound (matches the version ovrtx has shipped with since initial release).
# The upper bound is a forward-compat search window — bump if needed in the future.
_CUDART_MIN_MAJOR = 12
_CUDART_MAX_MAJOR = 20

_prefix, _suffix = ("cudart64_", ".dll") if sys.platform.startswith("win") else ("libcudart.so.", "")
_LIB_NAMES = tuple(f"{_prefix}{v}{_suffix}" for v in reversed(range(_CUDART_MIN_MAJOR, _CUDART_MAX_MAJOR + 1)))

# The build stages the runtime beside the renderer plugins rather than next to
# ovrtx-dynamic, so each loader directory is probed with these suffixes too.
_PLUGIN_SUBDIRS = (Path(), Path("plugins") / "rtx", Path("plugins") / "gpu.foundation")

_lock = threading.Lock()
_lib: Optional[ctypes.CDLL] = None


def _library_candidates() -> tuple[str, ...]:
    """Bundled CUDA runtimes as full paths, then the bare sonames for the system loader.

    Directories come from :func:`ovrtx_loader_candidate_dirs` — the same resolver that
    finds ovrtx-dynamic — so a layout in which the renderer loads can never be one in
    which the runtime does not. The wheel, the deploy tree and in-tree builds each place
    the runtime somewhere different, and only that resolver knows about all three.
    """
    # Imported lazily, as types.py does for this module, so importing ovrtx stays cheap.
    from .bindings import _resolve_existing_dirs, ovrtx_loader_candidate_dirs

    bundled: list[str] = []
    seen: set[Path] = set()
    # The resolver returns raw entries; _resolve_existing_dirs is how every other caller
    # survives a PATH holding %LocalAppData%\Microsoft\WindowsApps, which raises
    # PermissionError from is_dir(). The inner probes stay guarded for the same reason.
    for base in _resolve_existing_dirs(ovrtx_loader_candidate_dirs()):
        for directory in (base / sub for sub in _PLUGIN_SUBDIRS):
            if directory in seen:
                continue
            seen.add(directory)
            try:
                if not directory.is_dir():
                    continue
                bundled.extend(str(path) for name in _LIB_NAMES if (path := directory / name).is_file())
            except OSError:
                continue
    return (*bundled, *_LIB_NAMES)


def _load() -> ctypes.CDLL:
    global _lib
    if _lib is not None:
        return _lib
    with _lock:
        if _lib is None:
            # Keep only the message: retaining an exception retains its traceback,
            # which would form a cycle through callers of the first sync operation.
            last_err: Optional[str] = None
            candidates = _library_candidates()
            for candidate in candidates:
                try:
                    lib = ctypes.CDLL(candidate)
                    break
                except OSError as err:
                    last_err = str(err)
            else:
                raise RuntimeError(f"Could not load CUDA runtime (tried {candidates}): {last_err}")

            lib.cudaEventSynchronize.argtypes = [ctypes.c_void_p]
            lib.cudaEventSynchronize.restype = ctypes.c_int

            lib.cudaStreamWaitEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
            lib.cudaStreamWaitEvent.restype = ctypes.c_int

            lib.cudaGetErrorString.argtypes = [ctypes.c_int]
            lib.cudaGetErrorString.restype = ctypes.c_char_p

            _lib = lib
    return _lib


def _check(lib: ctypes.CDLL, rc: int, fn: str) -> None:
    if rc != 0:
        msg = lib.cudaGetErrorString(rc)
        raise RuntimeError(f"{fn} failed (rc={rc}): {msg.decode() if msg else 'unknown'}")


def event_synchronize(event: int) -> None:
    """Block the calling thread until ``event`` has fired."""
    lib = _load()
    _check(lib, lib.cudaEventSynchronize(event), "cudaEventSynchronize")


def stream_wait_event(stream: int, event: int) -> None:
    """Insert a wait barrier into ``stream`` against ``event`` (no CPU block)."""
    lib = _load()
    _check(lib, lib.cudaStreamWaitEvent(stream, event, 0), "cudaStreamWaitEvent")
