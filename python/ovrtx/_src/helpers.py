# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import contextvars
import functools
import inspect
import warnings
import weakref
from typing import Callable

_DEPRECATION_DEPTH = contextvars.ContextVar("ovrtx_deprecation_depth", default=0)


def _deprecation_warnings_suppressed(owner) -> bool:
    """Return whether the owner or its renderer suppresses deprecation warnings."""
    config = getattr(owner, "_config", None)
    if config is None:
        renderer = getattr(owner, "_renderer", None)
        if isinstance(renderer, weakref.ReferenceType):
            renderer = renderer()
        config = getattr(renderer, "_config", None)
    return bool(getattr(config, "suppress_deprecation_warnings", False))


def deprecated(replacement: str):
    """Mark a public Python API deprecated while suppressing nested delegation warnings."""

    def decorate(function: Callable):
        message = f"{function.__qualname__} has been deprecated since ovrtx 0.4. {replacement}"

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            depth = _DEPRECATION_DEPTH.get()
            token = _DEPRECATION_DEPTH.set(depth + 1)
            try:
                suppress_warnings = bool(args and _deprecation_warnings_suppressed(args[0]))
                if depth == 0 and not suppress_warnings:
                    warnings.warn(message, DeprecationWarning, stacklevel=2)
                return function(*args, **kwargs)
            finally:
                _DEPRECATION_DEPTH.reset(token)

        # cleandoc() before prepending: the notice is unindented, so on Python < 3.13
        # (which does not dedent docstrings at compile time) a raw concatenation leaves
        # an unindented line above an indented body. Every consumer that infers the
        # block indent from the docstring -- help(), IDE tooltips, and Sphinx's
        # prepare_docstring -- then computes a margin of zero and dedents nothing,
        # which stops Napoleon from recognizing the "Args:"/"Returns:" sections.
        body = inspect.cleandoc(function.__doc__ or "")
        wrapped.__doc__ = f"Deprecated since ovrtx 0.4. {replacement}\n\n{body}"
        setattr(wrapped, "__ovrtx_deprecated__", message)
        return wrapped

    return decorate
