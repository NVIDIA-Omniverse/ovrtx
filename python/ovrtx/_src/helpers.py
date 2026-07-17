# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import contextvars
import functools
import warnings
from typing import Callable

_DEPRECATION_DEPTH = contextvars.ContextVar("ovrtx_deprecation_depth", default=0)


def deprecated(replacement: str):
    """Mark a public Python API deprecated while suppressing nested delegation warnings."""

    def decorate(function: Callable):
        message = f"{function.__qualname__} is deprecated in ovrtx 0.4. {replacement}"

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            depth = _DEPRECATION_DEPTH.get()
            token = _DEPRECATION_DEPTH.set(depth + 1)
            try:
                if depth == 0:
                    warnings.warn(message, DeprecationWarning, stacklevel=2)
                return function(*args, **kwargs)
            finally:
                _DEPRECATION_DEPTH.reset(token)

        wrapped.__doc__ = f"Deprecated since ovrtx 0.4. {replacement}\n\n{function.__doc__ or ''}"
        setattr(wrapped, "__ovrtx_deprecated__", message)
        return wrapped

    return decorate
