# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Pytest configuration for ovrtx documentation tests."""

from pathlib import Path

import ovrtx
import ovstage
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield

    # Fix: pytest caches every fixture's return value in ``item.funcargs`` and keeps the Function
    # item in ``session.items`` for the whole run, so ``item.funcargs["renderer"]`` pins each
    # ovrtx.Renderer alive until session end. Because Renderer's only teardown path is __del__
    # (refcount-triggered), destroy_renderer + streaming-status unregister never run between
    # tests and the busy clients accumulate. All fixtures for this item are finalized by now, so
    # dropping funcargs lets the renderer's refcount reach zero and __del__ fire promptly.
    funcargs = getattr(item, "funcargs", None)
    if funcargs:
        funcargs.clear()


@pytest.fixture(scope="session")
def output_dir():
    """Return the _output directory, creating it if needed."""
    d = Path(__file__).parent / "_output"
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture
def renderer(output_dir):
    """Create a Renderer for an individual test."""
    config = ovrtx.RendererConfig(
        log_file_path=str(output_dir / "python-doc-tests-ovrtx.log"),
    )
    r = ovrtx.Renderer(config=config)
    try:
        yield r
    finally:
        # Deterministic teardown: the renderer participates in a reference cycle, so relying on
        # __del__ (refcount) would defer native teardown to a GC pass. 
        # destroy() is idempotent, so a later __del__ is a no-op.
        r.destroy()


@pytest.fixture
def stage(renderer, request):
    """Attach a fresh ovstage instance to the test renderer."""
    s = ovstage.Stage(f"ovrtx.docs.{request.node.name}")
    renderer.attach_ovstage(s)
    try:
        yield s
    finally:
        renderer.detach_ovstage()
        s.destroy()
