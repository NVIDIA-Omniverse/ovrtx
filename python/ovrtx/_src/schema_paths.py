# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Thin Python wrapper around the C ``ovrtx_register_schema_paths`` API.

USD schema/plugin path registration is implemented in a single place:
``rendering/source/sharedlibs/ovrtx/CRenderApiLibLoader.cpp`` (the
``registerUsdPluginPathsBody`` / ``registerSchemaPathsIfNeeded`` pair). This
module loads the ovrtx loader shared library and calls the exported
``ovrtx_register_schema_paths`` C entry point, so the same code path runs
whether the registration originates from Python (auto-import hook in
``ovrtx/__init__.py``), from a C/C++ host's ``ovrtx_register_schema_paths``
call, or implicitly from ``ovrtx_initialize`` / ``ovrtx_create_renderer``.

This module previously duplicated the path-resolution and env-var-update
logic in pure Python. The duplicate has been removed because USD's plug
registry contract (one-shot per process during ``Plug_InitConfig``) made
keeping two implementations in sync error-prone — when the C side picked up
the renamed ``OV_PXR_PLUGINPATH_2511`` env-var via the ``OV_OPENUSD_PLUGINPATH``
build macro, the Python copy silently diverged and broke schema discovery
in co-load scenarios with peer subsystems. A single source of truth in C
avoids that class of drift entirely.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from . import bindings as _bindings
from .bindings import (
    OVRTX_LOADER_LIB_NAME,
    ovrtx_config_t,
    ovrtx_loader_candidate_dirs,
    ovrtx_result_t,
)

# Highest-precedence root override env-var. The C resolver in
# ``CRenderApiLibLoader::registerSchemaPathsIfNeeded`` consults this before
# falling back to the loader's own location (``GetModuleFileName`` / ``dladdr``);
# we forward ``binary_package_root`` through it because ovrtx_config_t doesn't
# yet have a string-key for the binary package root.
_BASE_PATH_ENV_KEY: str = "OMNI_USD_PLUGINS_BASE_PATH"

# Optional override for the RTX settings plugin directory name (consumed by the
# ``OMNI_USD_RTX_SETTINGS_PATH`` lookup in ``registerUsdPluginPathsBody``).
_RTX_SETTINGS_ENV_KEY: str = "OMNI_USD_RTX_SETTINGS_PATH"

# Env-var keys USD's plug registry consults during ``Plug_InitConfig``. The
# C-side body writes to ``OV_OPENUSD_PLUGINPATH`` (build-time-configured —
# currently ``OV_PXR_PLUGINPATH_2511`` for the bundled OpenUSD 25.11; see
# ``OV_OPENUSD_PLUGINPATH`` in ``rendering/premake5.lua`` and ``_BUNDLED_USD_VERSION``
# in ``bindings.py``) and, only when ``OVRTX_PXR_SCHEMA_AUTO_REGISTER=1`` is
# set, also to the OpenUSD upstream default ``PXR_PLUGINPATH_NAME`` for any
# non-renamed peer USD that may also be co-loaded into the process.
# Surfaced here so tests / integrators that want to snapshot env state don't
# have to know which renamed key the C macro currently points at.
#
# Drift guard: the test
# ``test.ovrtx.python/test_schema_auto_register.py::test_every_advertised_key_is_actually_written``
# asserts (with the ``OVRTX_PXR_SCHEMA_AUTO_REGISTER=1`` opt-in set) that
# every key in this tuple gets populated by the C body, so a USD version
# bump that changes ``OV_OPENUSD_PLUGINPATH`` (or otherwise stops the C side
# from writing to one of these keys) without updating this list will fail
# in CI.
_PXR_PLUGINPATH_ENV_KEYS: Tuple[str, ...] = (
    "OV_PXR_PLUGINPATH_2511",
    "PXR_PLUGINPATH_NAME",
)


def usd_pluginpath_env_keys() -> Tuple[str, ...]:
    """Env-var keys that :func:`register_schema_paths` reads or writes.

    Output keys (USD's plug registry reads these — see
    ``_PXR_PLUGINPATH_ENV_KEYS``) followed by the input overrides the C
    resolver consults. Tests use this to snapshot/restore env state without
    hard-coding the list of keys.
    """
    return (
        *_PXR_PLUGINPATH_ENV_KEYS,
        _BASE_PATH_ENV_KEY,
        _RTX_SETTINGS_ENV_KEY,
    )


_loaded_lib: Optional[ctypes.CDLL] = None


def _load_loader_lib() -> ctypes.CDLL:
    """Locate and ``dlopen`` ``ovrtx-dynamic`` once; cache the handle.

    Search precedence mirrors ``_LibraryLoader._load_library``:
    ``OVRTX_LIBRARY_PATH_HINT`` (if set) first, then
    :func:`bindings.ovrtx_loader_candidate_dirs`. Honouring the hint here is
    important — without it, the import-time schema sync would happily load a
    DLL from the standard candidate dirs while the later renderer init loaded
    a different one from the hint, with potentially different schema-path
    behaviour bound into the same process.

    Subsequent calls return the cached handle. The same DLL refcount-bumps
    cleanly when ``_LibraryLoader`` later opens it for the renderer init,
    so calling here at import time and again from ``create_bindings`` does
    not load two copies (Windows ``LoadLibraryA`` and Linux ``dlopen`` both
    return the existing in-memory image when asked for the same path).

    Raises:
        OSError: When the DLL cannot be found on the candidate search path
            or every candidate ``ctypes.CDLL`` load fails. Caller is
            expected to translate this into a graceful warning so a
            missing-binary install (e.g. a source checkout without a built
            DLL) doesn't wedge ``import ovrtx`` for callers that don't need
            the cross-subsystem coexistence path.
    """
    global _loaded_lib
    if _loaded_lib is not None:
        return _loaded_lib

    # Read the hint via the module attribute (not a `from .bindings import HINT`
    # capture) so an integrator that leaves `OVRTX_PXR_SCHEMA_AUTO_REGISTER`
    # unset (the default — no import-time registration), mutates
    # `bindings.OVRTX_LIBRARY_PATH_HINT`, and then calls
    # `register_schema_paths()` manually picks up the new value — matching how
    # `_LibraryLoader.create_bindings` reads it for the renderer init load.
    #
    # Hint preprocessing intentionally diverges from `_LibraryLoader._load_library`:
    # we skip its `_resolve_existing_dirs` pass (which `.resolve()`-s and drops
    # non-dirs) because the per-candidate `is_file()` check below already falls
    # through cleanly on a missing hint, and `.resolve()` only affects the path
    # string passed to `CDLL` (typically same loaded image in normal layouts).
    hint = _bindings.OVRTX_LIBRARY_PATH_HINT
    candidate_dirs = ovrtx_loader_candidate_dirs()
    if hint:
        candidate_dirs = [Path(hint), *candidate_dirs]

    last_error: Optional[Exception] = None
    for directory in candidate_dirs:
        candidate = directory / OVRTX_LOADER_LIB_NAME
        try:
            if candidate.is_file():
                _loaded_lib = ctypes.CDLL(str(candidate))
                return _loaded_lib
        except OSError as exc:
            last_error = exc
            continue

    msg = f"Could not load {OVRTX_LOADER_LIB_NAME} from any of the standard ovrtx search paths"
    if last_error is not None:
        msg += f" (last error: {last_error})"
    raise OSError(msg)


def register_schema_paths(binary_package_root: Optional[str] = None) -> None:
    """Publish ovrtx's USD schema/plugin paths to USD's plugin search env-vars.

    Thin wrapper that loads ``ovrtx-dynamic`` and invokes the C-side
    :c:func:`ovrtx_register_schema_paths`. All path-resolution and env-var
    update logic lives in ``CRenderApiLibLoader.cpp`` so every entry point
    (Python auto-import hook, ``ovrtx_initialize``, ``ovrtx_create_renderer``,
    explicit ``ovrtx_register_schema_paths`` call from a C/C++ host) runs
    the same code.

    See ``ovrtx.h`` for the full contract — first-call wins, idempotent for
    matching effective roots, calls with a different root log a warning to
    stderr.

    Args:
        binary_package_root: Optional override for the ovrtx binary package
            root. Forwarded by setting ``OMNI_USD_PLUGINS_BASE_PATH`` (the
            highest-precedence input the C resolver consults), so this is
            equivalent to passing the same root in
            ``OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH`` to a subsequent
            ``ovrtx_initialize`` / ``ovrtx_create_renderer``. When ``None``
            the C side resolves the root from ``OMNI_USD_PLUGINS_BASE_PATH``
            (if already set in the env) then from the loader's own location
            (``GetModuleFileName`` / ``dladdr``).

            .. note::
               Passing a non-``None`` value mutates ``OMNI_USD_PLUGINS_BASE_PATH``
               in the process env unconditionally — even on the second call,
               where the C side has already pinned the first-registered root
               and merely emits a stderr warning. The env-var mutation has no
               effect on USD's plug registry (one-shot per process), but it
               will be observed by anything that consults
               ``OMNI_USD_PLUGINS_BASE_PATH`` later. Pass the same root on
               every call (or ``None`` after the first) if you need the env
               to stay consistent with the registered root.

    Side effect on ``os.environ``: each call mirrors the post-C-call CRT
    value of every key in ``_PXR_PLUGINPATH_ENV_KEYS`` into ``os.environ``
    (overwriting any prior Python-side edits to those specific keys, by
    design — the CRT is the source of truth for what USD sees). See the
    inline comment below the C call for rationale and platform notes.
    """
    lib = _load_loader_lib()

    # ovrtx_register_schema_paths(const ovrtx_config_t*) -> ovrtx_result_t.
    # Re-applying argtypes/restype is a cheap setattr; ctypes doesn't memoize
    # the configuration, but the call cost is dominated by the C-side mutex
    # and env-var I/O anyway, so we don't bother caching on first set.
    lib.ovrtx_register_schema_paths.argtypes = [ctypes.POINTER(ovrtx_config_t)]
    lib.ovrtx_register_schema_paths.restype = ovrtx_result_t

    if binary_package_root:
        os.environ[_BASE_PATH_ENV_KEY] = binary_package_root

    # Status is documented as always SUCCESS (mismatched roots surface as a
    # stderr warning from the C side, see ovrtx.h); intentionally ignored.
    lib.ovrtx_register_schema_paths(None)

    # Rehydrate os.environ from the CRT env block. The C body wrote via
    # _putenv_s (Windows) / setenv (Linux) into the CRT env that USD's
    # Plug_InitConfig reads natively; Python's os.environ is a startup
    # snapshot that ignores those C-side writes. Read back through the same
    # CRT (UCRT shared with CPython on Windows; libc resolved via the global
    # namespace on Linux) and mirror the keys via os.fsdecode (matches
    # Python's normal env-decoding convention).
    #
    # Catches Exception (not OSError): the upstream ovrtx/__init__.py logs
    # any escapee from this function as "auto-register failed", which would
    # be misleading after the C registration above already succeeded. The C
    # state is what USD consults, so a sync failure (missing ucrtbase.dll,
    # an FFI quirk, etc.) is a Python-observability degradation, not a
    # functional regression — best-effort and silent.
    try:
        libc = ctypes.CDLL("ucrtbase.dll" if sys.platform.startswith("win") else None)
        libc.getenv.restype = ctypes.c_char_p
        libc.getenv.argtypes = [ctypes.c_char_p]
        for key in _PXR_PLUGINPATH_ENV_KEYS:
            raw = libc.getenv(key.encode())
            if raw is not None:
                os.environ[key] = os.fsdecode(raw)
    except Exception:  # noqa: BLE001 — see comment above
        pass
