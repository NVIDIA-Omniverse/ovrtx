# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for Python ovRTX error-handling snippets."""

from pathlib import Path

import pytest
import ovstage

MISSING_USD_PATH = str((Path(__file__).parent / "../data/this-file-does-not-exist.usda").resolve())


def test_sync_method_raises_runtime_error(stage):
    """Synchronous population APIs surface operation failures as OvstageError."""
    # [snippet:doc-python-sync-runtime-error]
    with pytest.raises(ovstage.OvstageError):
        ovstage.population.open_usd(stage, MISSING_USD_PATH, ordinal=1)
    # [/snippet:doc-python-sync-runtime-error]


def test_async_wait_raises_runtime_error(stage):
    """Async Python APIs surface operation failures when wait() is called."""
    # [snippet:doc-python-async-operation-error]
    op = ovstage.population.open_usd_async(stage, MISSING_USD_PATH, ordinal=1)
    with pytest.raises(ovstage.OvstageError):
        op.wait()
    # [/snippet:doc-python-async-operation-error]
