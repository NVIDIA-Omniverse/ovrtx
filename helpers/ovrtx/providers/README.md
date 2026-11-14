# C++ helpers for data-provider authors

These optional, header-only C++17 utilities let custom ovrtx data providers reuse
UDIM manifest construction and stored-package parsing. They are useful when a
provider supplies texture tile sets or USDZ members from its own storage backend.
Ordinary rendering applications do not need them.

The C interface and provider ABI live in
[`include/ovrtx/ovrtx_data_provider.h`](../../../include/ovrtx/ovrtx_data_provider.h).
The helpers implement parts of that contract in your provider's process; they do
not add exported runtime symbols or a new binary interface. They are public
source utilities, so use headers from the same SDK version as the provider C
headers and rebuild your provider when upgrading. They do not register a
provider, fetch resources, resolve storage URLs, or own your provider's lifetime.

## Add them to your build

The SDK ships these utilities under `helpers/ovrtx/providers/`, with `helpers/`
and `include/` at the package root. After
`find_package(ovrtx REQUIRED)`, add `ovrtx::provider_helpers` to your target's
`target_link_libraries` dependencies. This interface target adds both include
roots and requests C++17; it does not link an ovrtx runtime library. Link your
chosen ovrtx loader separately if your application calls exported ovrtx functions.

For a build without CMake, add both the SDK's `helpers/` and `include/` directories
to the compiler's include search path and enable C++17. Include
`<ovrtx/providers/udim_manifest.hpp>` or
`<ovrtx/providers/stored_package.hpp>` as needed. All helper types are in
`ovrtx::data`.

## Build a UDIM manifest accessor

[`udim_manifest.hpp`](udim_manifest.hpp) provides `UdimTile` and
`UdimManifestAccessor`. Use it when responding to an `OVRTX_DATA_STRUCTURED`
request for the `ovrtx.texture.udim` version-1 schema.

1. Collect `UdimTile` entries, each with a unique ID in `[1001, 9999]` and a
   nonempty resource reference. References resolve relative to the manifest pin.
   An empty tile list is valid.
2. Create an accessor at a stable address and call `initialize(dictionary, tiles)`
   with your caller-owned path dictionary. Initialization copies the entries and
   creates the dictionary paths and tokens. Check its boolean result; discard the
   object on failure. Initialization can allocate, so catch exceptions before
   returning through a C callback.
3. Advertise `OVRTX_DATA_ACCESSOR_CAP_CPU_ARRAYS` in your provider descriptor and
   implement the provider's accessor open/close callbacks. Accept the manifest's
   whole-object open request `(0, OVRTX_DATA_SIZE_UNKNOWN)`. Publish `view()` as
   the accessor returned by your open callback. The helper supplies the scalar,
   enumeration and CPU-array accessor operations.
4. Retain the accessor and its dictionary until all array leases are released.
   In the close callback, check `canClose()` before destroying the accessor;
   return `OVRTX_DATA_BUSY` while leases remain. Do not destroy the dictionary
   while an accessor still uses it.

Initialize before publication. Concurrent accessor calls are supported after
initialization; initialization and destruction must not race those calls. The
helper exposes `/udim.tile_ids` as a u32 CPU array and
`/tiles/tile_<id>.asset` as a scalar token. The provider header documents the
schema and its surrounding pin/accessor contract.

## Read stored package members

[`stored_package.hpp`](stored_package.hpp) provides
`StoredPackage` and its non-owning `View` (`data`, `size`). Use it when your
provider already holds the complete bytes of a stored ZIP/ZIP64 archive, such as
USDZ, and wants to return member bytes without extracting or copying them.

1. Retain the outer archive's byte allocation or map lease and construct a `View`
   over those bytes.
2. Call `StoredPackage::member(archive, memberName, output)` and check the boolean
   result. On success, `output` points into the original archive allocation. A
   zero-length member is valid. For nested packages, pass the returned member
   view into another `member` call.
3. To enumerate entries, call `StoredPackage::visit(archive, visitor)`. The visitor
   receives each member name and borrowed byte view. Check the final boolean
   result before accepting the archive: callbacks may have run before a later
   invalid entry causes validation to fail.
4. Keep the outer allocation or map lease alive for every returned member view,
   including views into nested packages. Release it only when consumers no
   longer use those views.

Compressed and encrypted entries are unsupported. This helper validates archive
structure and locates stored bytes; it is not a decompressor, filesystem
extractor, or resource resolver. Your provider remains responsible for parsing
`outer[member]` references, resolving dependencies, enforcing path policy, and
translating failures into provider status codes. Its `false` result does not
supply a detailed provider diagnostic.
