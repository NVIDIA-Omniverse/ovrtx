# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Pytest configuration for ovrtx documentation tests."""

import re
import warnings
from pathlib import Path

import pytest

import ovrtx
import ovstage

_OVRTX_DEPRECATION_MESSAGE = re.compile(r".* deprecated (since|in) ovrtx 0\.4\..*")
_OVRTX_DEPRECATION_FILTER = f"ignore:{_OVRTX_DEPRECATION_MESSAGE.pattern}:DeprecationWarning"
_UNAPPROVED_DEPRECATION_NODEIDS: set[str] = set()
_FAILED_NODEIDS: set[str] = set()


def pytest_configure(config):
    """Register documentation-test markers."""
    config.addinivalue_line(
        "markers",
        "allow_deprecated_ovrtx_api: mark a test of the deprecated renderer-owned API contract",
    )


def pytest_sessionstart(session):
    """Clear the deprecation summary state before test collection."""
    _UNAPPROVED_DEPRECATION_NODEIDS.clear()
    _FAILED_NODEIDS.clear()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session):
    """Reserve known OVRTX deprecations for the ovstage migration summary."""
    terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter is None:
        return

    warning_reports = terminalreporter.stats.get("warnings")
    if warning_reports:
        terminalreporter.stats["warnings"] = [
            report for report in warning_reports if not _OVRTX_DEPRECATION_MESSAGE.search(report.message)
        ]


def pytest_warning_recorded(warning_message: warnings.WarningMessage, when: str, nodeid: str):
    """Record recognized OVRTX deprecations not suppressed by a compatibility opt-in."""
    if issubclass(warning_message.category, DeprecationWarning) and _OVRTX_DEPRECATION_MESSAGE.search(
        str(warning_message.message)
    ):
        _UNAPPROVED_DEPRECATION_NODEIDS.add(nodeid or f"<{when}>")


def pytest_runtest_logreport(report):
    """Track failures already represented by pytest's ordinary failure report."""
    if report.failed:
        _FAILED_NODEIDS.add(report.nodeid)


def pytest_terminal_summary(terminalreporter):
    """List tests whose deprecated API use requires migration to ovstage."""
    nodeids = sorted(_UNAPPROVED_DEPRECATION_NODEIDS - _FAILED_NODEIDS)
    if not nodeids:
        return

    terminalreporter.write_sep("=", f"tests requiring migration to ovstage ({len(nodeids)})")
    for nodeid in nodeids:
        terminalreporter.write_line(f"  - {nodeid}")


def pytest_collection_modifyitems(items):
    """Apply the centralized warning filter to explicitly marked compatibility tests."""
    for item in items:
        marker_nodes = list(item.iter_markers_with_node(name="allow_deprecated_ovrtx_api"))
        if not marker_nodes:
            continue
        if any(marker_node is not item for marker_node, _marker in marker_nodes):
            raise pytest.UsageError("allow_deprecated_ovrtx_api must be applied to individual tests")
        item.add_marker(pytest.mark.filterwarnings(_OVRTX_DEPRECATION_FILTER))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield

    # Pytest retains fixture return values in ``item.funcargs`` after fixture
    # finalization. Clearing them releases each renderer before the next test.
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
        # Explicit destruction provides deterministic native teardown despite
        # the renderer's reference cycle. A later __del__ is a no-op.
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
