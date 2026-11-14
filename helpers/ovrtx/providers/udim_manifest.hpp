// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <ovrtx/ovrtx_data_provider.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_set>
#include <mutex>
#include <unordered_map>

namespace ovrtx::data
{

/** One entry in an ovrtx.texture.udim version-1 manifest. */
struct UdimTile
{
    uint32_t id; /**< Unique tile ID in [1001, 9999]. */
    std::string reference; /**< Nonempty resource reference resolved relative to the manifest pin. */
};
/** Header-only manifest accessor implementing the public scalar/CPU-array contract.
 * Initialize before publication. Keep this object and its dictionary alive until all
 * leases are released and the provider closes the accessor. Concurrent accessor calls
 * are supported after initialization; initialization/destruction must not race them.
 * The provider owns destruction and must check canClose() before deleting this object. */
class UdimManifestAccessor
{
public:
    /** Prepare dictionary paths/tokens and copy tile IDs; no payload I/O occurs.
     * @param dictionary Non-NULL caller-owned dictionary, retained through accessor lifetime.
     * @param members Iterable of entries with id and reference fields; borrowed for this call.
     * @return True on success, including an empty manifest. False for a null dictionary,
     * repeated initialization, invalid/duplicate IDs, empty references, or dictionary errors.
     * After dictionary population starts, failure is terminal: discard the object, do not
     * publish view() or retry. Allocation exceptions propagate to the caller; catch them
     * before returning across a provider C callback. */
    template <class Tiles>
    bool initialize(path_dictionary_instance_t* dictionary, const Tiles& members)
    {
        if (!dictionary || m_initialized)
            return false;
        std::unordered_set<uint32_t> ids;
        for (const auto& member : members)
            if (member.id < 1001 || member.id > 9999 || member.reference.empty() || !ids.insert(member.id).second)
                return false;
        // Failed dictionary population is terminal for this helper instance.
        m_initialized = true;
        const ovx_string_t names[]{ { "tile_ids", 8 }, { "asset", 5 } };
        if (path_dictionary_create_tokens_from_strings(dictionary, names, 2, m_attributes).status != OVX_API_SUCCESS)
            return false;
        const ovx_string_t root{ "/udim", 5 };
        if (path_dictionary_create_paths_from_strings(dictionary, &root, 1, &m_root).status != OVX_API_SUCCESS)
            return false;
        for (const auto& member : members)
        {
            // Fabric prim names cannot begin with a digit.
            const auto path = "/tiles/tile_" + std::to_string(member.id);
            const ovx_string_t pathString{ path.data(), path.size() };
            const ovx_string_t reference{ member.reference.data(), member.reference.size() };
            ovx_primpath_t prim{};
            ovx_token_t token{};
            if (path_dictionary_create_paths_from_strings(dictionary, &pathString, 1, &prim).status != OVX_API_SUCCESS ||
                path_dictionary_create_tokens_from_strings(dictionary, &reference, 1, &token).status != OVX_API_SUCCESS)
                return false;
            m_tiles.emplace(prim, token);
            m_ids.push_back(member.id);
        }
        return true;
    }

    /** Return a borrowed view after successful initialize().
     * @return Copyable accessor record; copying does not transfer or extend ownership.
     * The context points to this object, which must outlive every use of the view. */
    ovrtx_data_accessor_t view()
    {
        return { table(), reinterpret_cast<ovrtx_data_accessor_context_t*>(this) };
    }

    /** Check whether all successful CPU-array acquisitions have been released.
     * @return True if there are no leases, false otherwise. This is only a snapshot;
     * stop concurrent accessor calls before using it to authorize destruction. */
    bool canClose()
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_leases.empty();
    }

private:
    static UdimManifestAccessor& self(ovrtx_data_accessor_context_t* context)
    {
        return *reinterpret_cast<UdimManifestAccessor*>(context);
    }

    static const ovrtx_data_accessor_vtable_t* table()
    {
        static const ovrtx_data_accessor_vtable_t api = [] {
            ovrtx_data_accessor_vtable_t api{};
            api.struct_size = sizeof(api);
            api.abi_version = OVRTX_DATA_ACCESSOR_ABI_VERSION;
            api.get_roots = [](ovrtx_data_accessor_context_t* c, uint64_t start, ovx_primpath_t* storage,
                               uint64_t capacity, uint64_t* total) {
                if (!total)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                *total = 1;
                if (storage && capacity && start == 0)
                    storage[0] = self(c).m_root;
                return OVRTX_DATA_OK;
            };
            api.get_children = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, uint64_t,
                                  ovx_primpath_t*, uint64_t, uint64_t* total) {
                if (!total)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                auto& s = self(c);
                if (!(prim == s.m_root || s.m_tiles.count(prim)))
                    return OVRTX_DATA_NOT_FOUND;
                *total = 0;
                return OVRTX_DATA_OK;
            };
            api.get_attributes = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, uint64_t start,
                                    ovx_token_t* storage, uint64_t capacity, uint64_t* total) {
                if (!total)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                auto& s = self(c);
                if (!(prim == s.m_root || s.m_tiles.count(prim)))
                    return OVRTX_DATA_NOT_FOUND;
                *total = 1;
                if (storage && capacity && start == 0)
                    storage[0] = prim == s.m_root ? s.m_attributes[0] : s.m_attributes[1];
                return OVRTX_DATA_OK;
            };
            api.get_prim_info = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, ovrtx_data_prim_info_t* info) {
                if (!info)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                if (prim != self(c).m_root && !self(c).m_tiles.count(prim))
                    return OVRTX_DATA_NOT_FOUND;
                *info = {};
                return OVRTX_DATA_OK;
            };
            api.get_attribute_info = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, ovx_token_t name,
                                        ovrtx_data_attribute_info_t* info) {
                if (!info)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                auto& s = self(c);
                if (prim == s.m_root && name == s.m_attributes[0])
                    *info = { { { kDLUInt, 32, 1 }, true, OVRTX_SEMANTIC_NONE }, s.m_ids.size() };
                else if (s.m_tiles.count(prim) && name == s.m_attributes[1])
                    *info = { { { kDLUInt, 64, 1 }, false, OVRTX_SEMANTIC_TOKEN_ID }, 1 };
                else
                    return OVRTX_DATA_NOT_FOUND;
                return OVRTX_DATA_OK;
            };
            api.get_scalar_attribute = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, ovx_token_t name,
                                          void* buffer, uint64_t capacity, uint64_t* required) {
                if (!required)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                auto& s = self(c);
                if (prim == s.m_root && name == s.m_attributes[0])
                    return OVRTX_DATA_INVALID_ARGUMENT;
                const auto found = s.m_tiles.find(prim);
                if (found == s.m_tiles.end() || name != s.m_attributes[1])
                    return OVRTX_DATA_NOT_FOUND;
                *required = sizeof(ovx_token_t);
                if (!buffer || capacity < *required)
                    return OVRTX_DATA_OUT_OF_RANGE;
                std::memcpy(buffer, &found->second, *required);
                return OVRTX_DATA_OK;
            };
            api.acquire_array_cpu = [](ovrtx_data_accessor_context_t* c, ovx_primpath_t prim, ovx_token_t name,
                                       ovrtx_data_cpu_array_t* array) {
                if (!array)
                    return OVRTX_DATA_INVALID_ARGUMENT;
                auto& s = self(c);
                if (s.m_tiles.count(prim) && name == s.m_attributes[1])
                    return OVRTX_DATA_INVALID_ARGUMENT;
                if (prim != s.m_root || name != s.m_attributes[0])
                    return OVRTX_DATA_NOT_FOUND;
                std::lock_guard<std::mutex> lock(s.m_mutex);
                const ovrtx_data_array_lease_id_t lease{s.m_nextLease++};
                s.m_leases.insert(lease);
                *array = { lease,
                           s.m_ids.data(),
                           s.m_ids.size() * sizeof(uint32_t),
                           { { { kDLUInt, 32, 1 }, true, OVRTX_SEMANTIC_NONE }, s.m_ids.size() } };
                return OVRTX_DATA_OK;
            };
            api.release_array_cpu = [](ovrtx_data_accessor_context_t* c, ovrtx_data_array_lease_id_t lease) {
                auto& s = self(c);
                std::lock_guard<std::mutex> lock(s.m_mutex);
                return s.m_leases.erase(lease) ? OVRTX_DATA_OK : OVRTX_DATA_INVALID_HANDLE;
            };
            return api;
        }();
        return &api;
    }

    bool m_initialized = false;
    ovx_primpath_t m_root{};
    ovx_token_t m_attributes[2]{};
    std::vector<uint32_t> m_ids;
    std::unordered_map<ovx_primpath_t, ovx_token_t> m_tiles;
    std::mutex m_mutex;
    uint64_t m_nextLease = 1;
    std::unordered_set<ovrtx_data_array_lease_id_t> m_leases;
};

} // namespace ovrtx::data
