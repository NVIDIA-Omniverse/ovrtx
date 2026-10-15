# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Register an explicit ovrtx light schema with external OpenUSD and verify its provider and fallback."""
from pathlib import Path

import ovrtx
from pxr import Plug, Sdf, Usd


def register_for_bundled_usd():
    # [snippet:plugin-paths-register-python]
    # Publish paths before initializing ovstage in a stage-first application.
    ovrtx.register_schema_paths()
    # [/snippet:plugin-paths-register-python]


def main():
    # [snippet:plugin-paths-external-python]
    # Select only the schema family this application needs.
    paths = ovrtx.usd_plugin_paths()
    schema_path = next(p for p in paths if Path(p).name == "physical_lighting")
    assert (Path(schema_path) / "plugInfo.json").is_file(), "Schema plugin descriptor missing"
    # Register before creating a stage or using Usd.SchemaRegistry.
    Plug.Registry().RegisterPlugins(schema_path)
    # [/snippet:plugin-paths-external-python]

    # [snippet:plugin-paths-verify-python]
    # A fallback alone does not identify which plugin supplied the schema.
    schema_type = Usd.SchemaRegistry.GetTypeFromSchemaTypeName("PhysicalLightIlluminantAPI")
    assert schema_type, "Schema type not found"
    provider = Plug.Registry().GetPluginForType(schema_type)
    assert provider and provider.name == "physicalLighting", "Unexpected schema provider"
    assert Path(provider.resourcePath).samefile(schema_path), (
        f"Unexpected schema resource path: {provider.resourcePath} (expected {schema_path})"
    )

    stage = Usd.Stage.CreateInMemory()
    light = stage.DefinePrim("/World/Light", "RectLight")
    assert not light.GetAttribute("physical:illuminant"), "Schema must be applied explicitly"
    assert light.ApplyAPI("PhysicalLightIlluminantAPI")

    # Read a schema fallback without authoring a value ourselves.
    illuminant = light.GetAttribute("physical:illuminant")
    assert illuminant.GetTypeName() == Sdf.ValueTypeNames.Token
    assert illuminant.Get() == "white"
    assert not illuminant.HasAuthoredValueOpinion()
    # [/snippet:plugin-paths-verify-python]

    print("Schema loaded: PhysicalLightIlluminantAPI")
    print(f"Schema provider: {provider.name} ({provider.resourcePath})")
    print(f"Default illuminant: {illuminant.Get()}")


if __name__ == "__main__":
    main()
