# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Test the startup-mode example without inheriting another test's graphics resources."""

import subprocess
import sys
from pathlib import Path

import ovrtx


def _create_minimal_only_renderer():
    # [snippet:doc-create-minimal-only-renderer]
    config = ovrtx.RendererConfig(
        enable_minimal=True,
        enable_realtimepathtracing=False,
        enable_pathtracing=False,
        # Retain shared graphics resources even after this instance is destroyed.
        keep_system_alive=True,
    )
    renderer = ovrtx.Renderer(config=config)
    # [/snippet:doc-create-minimal-only-renderer]
    try:
        assert renderer.config.enable_minimal is True
        assert renderer.config.enable_realtimepathtracing is False
        assert renderer.config.enable_pathtracing is False
        # [snippet:doc-reset-render-mode-availability]
        # Omit enable_* so this instance inherits Minimal-only availability.
        # Creating it clears retention left by keep_system_alive=True.
        release_retention = ovrtx.Renderer(config=ovrtx.RendererConfig(keep_system_alive=False))
        renderer.destroy()
        # Destroy any other ovrtx renderer instances before this final destroy.
        release_retention.destroy()

        # No instance or keep-alive reference remains: initialize graphics again.
        renderer = ovrtx.Renderer(
            config=ovrtx.RendererConfig(
                enable_minimal=True,
                enable_realtimepathtracing=True,
                enable_pathtracing=True,
                keep_system_alive=False,
            )
        )
        # [/snippet:doc-reset-render-mode-availability]
        assert renderer.config.enable_realtimepathtracing is True
        assert renderer.config.enable_pathtracing is True
    finally:
        renderer.destroy()


def test_create_minimal_only_renderer():
    # Other docs tests retain an all-modes backend. This example must be the first
    # renderer in its process; the native startup test checks actual GPU allocations.
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    _create_minimal_only_renderer()
