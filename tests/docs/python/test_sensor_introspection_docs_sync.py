# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Keep the generated copy of the sensor introspection utility doc in sync with its source.

docs/sensors/common/_generated/sensor_introspection_utility.txt is produced by
tools/ci/populate_sensor_introspection_docs.py from the sensor-introspection
package's own doc. Neither the tool nor that doc ships in the public GitHub
mirror, where the copy is all there is, so these tests skip there.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PUBLIC_ROOT = Path(__file__).resolve().parents[3]
TOOL = PUBLIC_ROOT / "tools" / "ci" / "populate_sensor_introspection_docs.py"


@pytest.fixture(scope="module")
def populate_tool():
    """Import the populate tool; it leaves the public mirror with the rest of tools/."""
    if not TOOL.is_file():
        pytest.skip(f"{TOOL.relative_to(PUBLIC_ROOT)} is not shipped in the public mirror")
    spec = importlib.util.spec_from_file_location("populate_sensor_introspection_docs", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def source(populate_tool):
    """The canonical document, absent in the public mirror."""
    source, _ = populate_tool.default_paths()
    if not source.is_file():
        pytest.skip(f"canonical document is absent (public mirror): {source}")
    return source


def test_generated_copy_is_in_sync(populate_tool, source):
    """The checked-in copy must be exactly what the tool generates from the source."""
    _, destination = populate_tool.default_paths()
    errors = populate_tool.check_generated_copy(source, destination)
    assert not errors, "\n".join(errors)


def test_check_detects_stale_copy(populate_tool, source, tmp_path):
    """A single extra character in the copy is reported as out of sync."""
    destination = tmp_path / "sensor_introspection_utility.txt"
    populate_tool.populate(source, destination)
    assert populate_tool.check_generated_copy(source, destination) == []
    destination.write_text(destination.read_text(encoding="utf-8") + "x", encoding="utf-8")
    errors = populate_tool.check_generated_copy(source, destination)
    assert len(errors) == 1 and errors[0].startswith("out of sync:"), errors


def test_check_passes_quietly_without_source(populate_tool, tmp_path):
    """Without the source, --check neither fails nor prints, so the mirror stays green."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "--check", "--source", str(tmp_path / "missing.rst")],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "" and result.stderr == ""
