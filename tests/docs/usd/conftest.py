# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Shared helpers and schema registration for USDA validation tests."""

import os
from pathlib import Path

from pxr import Plug, Sdf


_PACKAGED_SCHEMA_ROOT_ENV = "OVRTX_DOCS_USD_PLUGIN_ROOT"


def _schema_plugin_dir(schema_name: str) -> Path:
    """Resolve a schema family from the package under test or the source tree."""
    if packaged_root := os.environ.get(_PACKAGED_SCHEMA_ROOT_ENV):
        return Path(packaged_root) / schema_name

    # Source checkouts may keep schema descriptors outside this directory.
    # Search ancestors only when no packaged SDK was selected.
    for parent in Path(__file__).resolve().parents:
        plugin_dir = parent / "schemas" / schema_name / "usd_plugins"
        if (plugin_dir / "plugInfo.json").is_file():
            return plugin_dir
    raise RuntimeError(
        f"USD schema {schema_name!r} was not found. "
        f"Set {_PACKAGED_SCHEMA_ROOT_ENV} to the SDK's bin/usd_plugins directory."
    )


# Register codeless product schemas before any test constructs Usd.SchemaRegistry.
for _schema in ("omni_lens_distortion", "omni_light_shaping", "physical_lighting", "omni_dome_light", "rtx_settings"):
    _plugin_dir = _schema_plugin_dir(_schema)
    _plugin_descriptor = _plugin_dir / "plugInfo.json"
    if not _plugin_descriptor.is_file():
        raise RuntimeError(f"USD schema plugin descriptor not found: {_plugin_descriptor}")
    Plug.Registry().RegisterPlugins(str(_plugin_dir))


def validate_usda(usda_text: str) -> Sdf.Layer:
    """Parse a USDA string and return the layer, failing if invalid."""
    layer = Sdf.Layer.CreateAnonymous(".usda")
    assert layer.ImportFromString(usda_text), "Failed to parse USDA"
    return layer
