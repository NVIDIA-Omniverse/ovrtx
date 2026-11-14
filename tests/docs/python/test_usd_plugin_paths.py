# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Check external-USD interop and bundled-USD registration in fresh processes."""
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

import ovrtx
import pytest


@pytest.mark.skipif(platform.machine().lower() in ("aarch64", "arm64"),
                    reason="The pinned usd-core distribution has no aarch64 wheel")
def test_usd_plugin_paths_example():
    """Exercise USD plugin registration with the suite's OVRTX in an isolated example process."""
    # Use the version installed with this suite, independent of the shell PATH.
    uv = [sys.executable, "-m", "uv"]
    example = Path(__file__).parents[3] / "examples/python/usd-plugin-paths"
    env = os.environ.copy()
    # Use the exact ovrtx under test; keep usd-core out of this parent process.
    root = str(Path(ovrtx.__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join([root, env.get("PYTHONPATH", "")])
    # Public checkouts omit lockfiles; let uv create one from the pinned dependencies.
    sync = subprocess.run(
        [*uv, "sync", "--project", str(example), "--group", "dev",
         "--no-install-package", "ovrtx"],
        cwd=tempfile.gettempdir(), env=env, capture_output=True, text=True, timeout=300,
    )
    assert sync.returncode == 0, sync.stdout + sync.stderr
    result = subprocess.run(
        [*uv, "run", "--project", str(example), "--no-sync",
         "pytest", str(example / "test_example.py"), "-q", "--tb=short"],
        cwd=tempfile.gettempdir(), env=env, capture_output=True, text=True, timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("timing", ["before", "after", "missing", "late"])
def test_bundled_schema_registration_order(timing):
    """Check actual ovstage fallback consumption in a fresh USD runtime."""
    # Avoid inherited registration and renderer fixtures masking a missing call.
    env = os.environ.copy()
    for key in tuple(env):
        if key == "PXR_PLUGINPATH_NAME" or key.startswith("OV_PXR_PLUGINPATH_"):
            env.pop(key)
    env["OVRTX_PXR_SCHEMA_AUTO_REGISTER"] = "0"
    code = r'''
import sys
import numpy as np
import ovrtx

timing = sys.argv[1]

# Register before loading ovstage, or explicitly exercise its loaded-runtime path.
if timing == "before":
    ovrtx.register_schema_paths()

import ovstage
from ovstage import population

with ovstage.Stage("schema-registration-order") as stage:
    if timing == "after":
        ovrtx.register_schema_paths()
    elif timing == "late":
        # Force USD to cache definitions before registering the missing family.
        population.open_usd_from_string(stage, '#usda 1.0\ndef Xform "Warmup" {}', ordinal=1)
        ovrtx.register_schema_paths()

    # No authored illuminant: only the registered schema can supply "white".
    scene = '\n'.join([
        '#usda 1.0',
        'def RectLight "Light" (prepend apiSchemas = ["PhysicalLightIlluminantAPI"])',
        '{',
        '}',
    ])
    selector = population.Selector(
        prim_predicate=population.PrimPredicate.has_type("RectLight"),
        property_predicate=population.PropertyPredicate.declared_by_schema("PhysicalLightIlluminantAPI"),
    )
    population.open_usd_from_string_with_desc(
        stage, scene, ordinal=2, time=population.DEFAULT_TIME,
        descs=[population.Desc(selectors=[selector])],
    )
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

    with ovstage.PathDictionary(stage) as paths:
        attribute = paths.intern_token("physical:illuminant")
        query = stage.query(filter=ovstage.Filter([
            ovstage.Predicate("usd-path", ovstage.FilterOp.PREFIX, ["/Light"])
        ]))
        try:
            query.wait()
            result = stage.fetch_query_result(query)
            assert attribute in result.attributes, "schema fallback was not populated"
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                assert group is not None, "schema fallback read returned no data"
                try:
                    column = group.columns[0]
                    values = np.from_dlpack(column.dlpack(0)).reshape(-1)
                    assert [paths.token_to_string(ovstage.Token(value)) for value in values] == ["white"]
                finally:
                    stage.release_group(group)
        finally:
            stage.release_query(query).wait()
'''
    # The same success assertion must fail for missing and too-late registration.
    with tempfile.TemporaryDirectory(prefix="bundled-schema-") as folder:
        result = subprocess.run(
            [sys.executable, "-c", code, timing], cwd=folder, env=env,
            capture_output=True, text=True, timeout=120,
        )
    output = result.stdout + result.stderr
    if timing in ("missing", "late"):
        assert result.returncode == 1, output
        assert "AssertionError: schema fallback was not populated" in result.stderr, output
    else:
        assert result.returncode == 0, output
