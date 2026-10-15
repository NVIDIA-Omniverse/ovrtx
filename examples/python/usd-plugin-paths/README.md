# usd-plugin-paths

Register the physical-lighting schema from ovrtx with external OpenUSD, apply it
to a RectLight, and verify its provider and an unauthored fallback value.

Follow the [Python setup](../../../docs/python_api/getting_started.rst) first.
From the public ovrtx root, `rendering/ovrtx/public` in a Kit checkout:

```console
cd examples/python/usd-plugin-paths
uv run main.py
uv run --group dev pytest -q
```

A successful run prints `Schema loaded: PhysicalLightIlluminantAPI`, the provider's
name and resource directory, and the default illuminant `white`. It creates no files
and does not render.

## Register the schema

Register the required family before creating a stage or using Usd.SchemaRegistry:

```python
# Select only the schema family this application needs.
paths = ovrtx.usd_plugin_paths()
schema_path = next(p for p in paths if Path(p).name == "physical_lighting")
assert (Path(schema_path) / "plugInfo.json").is_file(), "Schema plugin descriptor missing"
# Register before creating a stage or using Usd.SchemaRegistry.
Plug.Registry().RegisterPlugins(schema_path)
```

## Verify the provider and fallback

Check that the schema comes from the expected ovrtx plugin, then read its
fallback. A fallback alone cannot distinguish providers with the same default:

```python
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
```

The tests exercise early, late, missing, and environment-based registration in
separate processes, using `usd-core==26.3`. They also verify that the example
rejects a copy of the schema registered from another directory, even though
its fallback resolves. They also reject a nonexistent schema root and verify
that explicit bundled registration publishes paths without registering the
schema with external OpenUSD. They do not create ovstage.
See the
[registration guide](../../../docs/core/usd_plugin_paths.rst) for ordering and
the distinction between external OpenUSD and the bundled USD runtime.
