# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = Path(__file__).resolve().parent


def child(code, *, stderr_contains=()):
    # Keep each registration experiment isolated from cached USD definitions
    # and from a user's automatic plugin registration.
    env = os.environ.copy()
    for key in tuple(env):
        if key == "PXR_PLUGINPATH_NAME" or key.startswith("OV_PXR_PLUGINPATH_"):
            env.pop(key)
    env["OVRTX_PXR_SCHEMA_AUTO_REGISTER"] = "0"
    with tempfile.TemporaryDirectory(prefix="ovplug-") as folder:
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=folder, env=env,
            capture_output=True, text=True, timeout=120,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    for message in stderr_contains:
        assert message in result.stderr, result.stderr
    return result.stdout


def test_enumerated_paths_preserve_environment_and_register_light_schema():
    child("""
import os
from pathlib import Path
import ovrtx
before = dict(os.environ)
paths = ovrtx.usd_plugin_paths()
assert len(paths) >= 1 and len(paths) == len(set(paths))
physical_lighting = [Path(p) for p in paths if Path(p).name == 'physical_lighting']
assert len(physical_lighting) == 1
assert (physical_lighting[0] / 'plugInfo.json').is_file()
assert dict(os.environ) == before
assert ovrtx.usd_plugin_paths() == paths
ovrtx.register_schema_paths()
assert ovrtx.usd_plugin_paths() == paths

from pxr import Plug, Sdf, Usd
Plug.Registry().RegisterPlugins(str(physical_lighting[0]))
stage = Usd.Stage.CreateInMemory()
light = stage.DefinePrim('/World/Light', 'RectLight')
assert light.ApplyAPI('PhysicalLightIlluminantAPI')
illuminant = light.GetAttribute('physical:illuminant')
assert illuminant.GetTypeName() == Sdf.ValueTypeNames.Token
assert illuminant.Get() == "white"
assert not illuminant.HasAuthoredValueOpinion()
""")


@pytest.mark.parametrize("timing", ["early", "late", "missing", "environment"])
def test_schema_registration_in_fresh_process(timing):
    code = """
import os
from pathlib import Path
import ovrtx
plugin = next(p for p in ovrtx.usd_plugin_paths() if Path(p).name == 'physical_lighting')
"""
    if timing == "environment":
        code += "os.environ['PXR_PLUGINPATH_NAME'] = plugin\n"
    code += "from pxr import Plug, Usd\n"
    if timing == "late":
        code += "assert not Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('PhysicalLightIlluminantAPI')\n"
    if timing in ("early", "late"):
        code += "Plug.Registry().RegisterPlugins(plugin)\n"
    code += "definition = Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('PhysicalLightIlluminantAPI')\n"
    code += f"assert bool(definition) == {timing in ('early', 'environment')}\n"
    if timing in ("early", "environment"):
        code += """
stage = Usd.Stage.CreateInMemory()
light = stage.DefinePrim('/World/Light', 'RectLight')
assert light.ApplyAPI('PhysicalLightIlluminantAPI')
illuminant = light.GetAttribute('physical:illuminant')
assert illuminant.Get() == "white"
assert not illuminant.HasAuthoredValueOpinion()
"""
    child(code)


def test_console_example():
    output = child(f"import runpy; runpy.run_path({str(HERE / 'main.py')!r}, run_name='__main__')")
    assert "Schema loaded: PhysicalLightIlluminantAPI" in output
    assert "Schema provider: physicalLighting (" in output
    assert "Default illuminant:" in output


def test_console_example_rejects_another_schema_location():
    child(f"""
from pathlib import Path
import runpy
import shutil
import ovrtx
import pytest
from pxr import Plug, Usd

# Reuse the installed schema at another location, preserving its name and fallback.
source = next(p for p in ovrtx.usd_plugin_paths() if Path(p).name == 'physical_lighting')
other = shutil.copytree(source, Path.cwd() / 'physical_lighting')
Plug.Registry().RegisterPlugins(str(other))
stage = Usd.Stage.CreateInMemory()
light = stage.DefinePrim('/World/Light', 'RectLight')
assert light.ApplyAPI('PhysicalLightIlluminantAPI')
illuminant = light.GetAttribute('physical:illuminant')
assert illuminant.Get() == "white"
assert not illuminant.HasAuthoredValueOpinion()

# The example must reject the other location even though the fallback works.
with pytest.raises(AssertionError, match='Unexpected schema resource path'):
    runpy.run_path({str(HERE / 'main.py')!r}, run_name='__main__')
""")


def test_bundled_registration_publishes_paths_without_registering_external_usd():
    child(f"""
import os
import runpy
from pathlib import Path
import ovrtx
example = runpy.run_path({str(HERE / 'main.py')!r})
paths = {{Path(p).resolve() for p in ovrtx.usd_plugin_paths()}}
example['register_for_bundled_usd']()
keys = [key for key in os.environ if key.startswith('OV_PXR_PLUGINPATH_')]
assert keys
assert any(paths <= {{Path(p).resolve() for p in os.environ[key].split(os.pathsep) if p}} for key in keys)
assert 'PXR_PLUGINPATH_NAME' not in os.environ
from pxr import Usd
assert not Usd.SchemaRegistry().FindAppliedAPIPrimDefinition('PhysicalLightIlluminantAPI')
""")


def test_console_example_rejects_missing_schema_root():
    child(f"""
import os
from pathlib import Path
import runpy
import pytest
missing = Path.cwd() / 'nonexistent-schema-root'
assert not missing.exists()
os.environ['OMNI_USD_PLUGINS_BASE_PATH'] = str(missing)
with pytest.raises(AssertionError, match='Schema plugin descriptor missing'):
    runpy.run_path({str(HERE / 'main.py')!r}, run_name='__main__')
""")


@pytest.mark.parametrize("first_call", ["enumeration", "registration"])
def test_first_schema_root_wins(first_call, tmp_path):
    # Discover the installed resources in another process so the test starts unpinned.
    sources = json.loads(child("import json, ovrtx; print(json.dumps(ovrtx.usd_plugin_paths()))"))
    assert sources
    root_a, root_b = tmp_path / "root-a", tmp_path / "root-b"
    for root in (root_a, root_b):
        for source in sources:
            source = Path(source)
            assert (source / "plugInfo.json").is_file()
            shutil.copytree(source, root / "usd_plugins" / source.name)

    child(f"""
import os
from pathlib import Path
import ovrtx
root_a = Path({str(root_a)!r})
root_b = Path({str(root_b)!r})
os.environ.pop('OMNI_USD_RTX_SETTINGS_PATH', None)
os.environ['OMNI_USD_PLUGINS_BASE_PATH'] = str(root_a)
if {first_call!r} == 'registration':
    ovrtx.register_schema_paths()

# [snippet:plugin-paths-first-root-wins-python]
# The first call selects A for this process.
os.environ['OMNI_USD_PLUGINS_BASE_PATH'] = str(root_a)
paths_a = ovrtx.usd_plugin_paths()
assert paths_a and all(Path(p).is_relative_to(root_a) for p in paths_a)
assert all((Path(p) / 'plugInfo.json').is_file() for p in paths_a)

# B also contains the schemas, but changing the root cannot replace A.
assert all((root_b / Path(p).relative_to(root_a) / 'plugInfo.json').is_file()
           for p in paths_a)
os.environ['OMNI_USD_PLUGINS_BASE_PATH'] = str(root_b)
assert ovrtx.usd_plugin_paths() == paths_a  # Warns and keeps A.
ovrtx.register_schema_paths()              # Also warns and publishes A.
assert ovrtx.usd_plugin_paths() == paths_a
# [/snippet:plugin-paths-first-root-wins-python]

keys = [key for key in os.environ if key.startswith('OV_PXR_PLUGINPATH_')]
assert keys
published = [Path(p) for key in keys for p in os.environ[key].split(os.pathsep) if p]
assert all(Path(p) in published for p in paths_a)
assert not any(p.is_relative_to(root_b) for p in published)
""", stderr_contains=(
        "[ovrtx] WARNING: USD plugin paths already registered against",
        "root-a'; ignoring new request for",
        "root-b'. USD plugin-path registration is one-shot per process.",
    ))
