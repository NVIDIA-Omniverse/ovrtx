# usd-plugin-paths (C/C++)

List ovrtx's schema directories, check their plugin descriptors, and publish
them for the bundled USD runtime.
This program takes no arguments and does not create a renderer or output files.

Follow the [C/C++ setup](../../../docs/c_api/getting_started.rst) first.
Start in the public ovrtx root, `rendering/ovrtx/public` in a Kit checkout.

Windows PowerShell:

```powershell
cd examples/c/usd-plugin-paths
cmake -B build
cmake --build build --config Release
.\build\static\Release\usd-plugin-paths.exe
.\build\shared\Release\usd-plugin-paths-dynamic.exe
```

Linux:

```bash
cd examples/c/usd-plugin-paths
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/static/usd-plugin-paths
./build/shared/usd-plugin-paths-dynamic
```

Both loaders print the directories and a confirmation that the paths were
published. Successful registration does not prove an external OpenUSD client
loaded the schemas. The [Python example](../../python/usd-plugin-paths/) performs
that check. An external C++ OpenUSD client needs its own headers and libraries.

## Enumerate paths

The returned strings are owned by ovrtx:

```cpp
// Returned strings belong to ovrtx and remain valid for this process.
const size_t count = ovrtx_get_usd_plugin_path_count(&config);
std::vector<ovx_string_t> paths(count);
const size_t total = ovrtx_get_usd_plugin_paths(&config, paths.data(), paths.size());
if (total != count || count == 0) return 1;
for (auto path : paths) std::cout << std::string_view(path.ptr, path.length) << "\n";
```

## Check the directories

Enumeration does not check the filesystem. The example exits with code 1 and
`Schema plugin descriptor missing: ...` for a missing descriptor, including when
`OMNI_USD_PLUGINS_BASE_PATH` points to a nonexistent root. CI checks this negative
case in a new process for both loaders.

```cpp
// Enumeration and registration do not check the filesystem.
for (auto path : paths) {
    const auto descriptor = std::filesystem::path(std::string(path.ptr, path.length)) / "plugInfo.json";
    std::error_code error;
    if (!std::filesystem::is_regular_file(descriptor, error)) {
        std::cerr << "Schema plugin descriptor missing: " << descriptor.string() << "\n";
        return 1;
    }
}
```

## Register paths

Publish paths before initializing ovstage in a stage-first application:

```cpp
// Publish paths before the bundled USD runtime first reads its registry.
const ovrtx_result_t result = ovrtx_register_schema_paths(&config);
if (result.status != OVRTX_API_SUCCESS) {
    std::cerr << "Could not register ovrtx schema paths.\n";
    return 1;
}
```
