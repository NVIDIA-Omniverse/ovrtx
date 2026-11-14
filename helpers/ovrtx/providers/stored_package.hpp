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

#include <cstdint>
#include <cstring>
#include <string>

namespace ovrtx::data
{

// USDZ members are stored, not compressed. Return a view into the retained
// archive snapshot; no filesystem extraction or USD resolver is involved.
// The caller retains the archive allocation for the lifetime of every returned
// view. Compressed/encrypted entries are rejected; this is not a decompressor.
class StoredPackage
{
public:
    struct View
    {
        const uint8_t* data = nullptr;
        uint64_t size = 0;
    };

    static bool member(View archive, const std::string& name, View& output)
    {
        output = {};
        bool found = false;
        return visit(archive,
                     [&](const std::string& candidate, View bytes) {
                         if (candidate == name)
                         {
                             output = bytes;
                             found = true;
                         }
                     }) &&
               found;
    }

    template <typename Visitor>
    static bool visit(View archive, Visitor visitor)
    {
        if (archive.size < 22 || !archive.data)
            return false;
        const uint64_t first = archive.size > 65557 ? archive.size - 65557 : 0;
        uint64_t end = archive.size - 22;
        for (;;)
        {
            if (u32(archive.data + end) == 0x06054b50 && u16(archive.data + end + 20) == archive.size - end - 22)
                break;
            if (end == first)
                return false;
            --end;
        }
        const auto* footer = archive.data + end;
        if (u16(footer + 4) || u16(footer + 6) || u16(footer + 8) != u16(footer + 10))
            return false;
        uint64_t count = u16(footer + 10), directorySize = u32(footer + 12), directory = u32(footer + 16);
        if (count == UINT16_MAX || directorySize == UINT32_MAX || directory == UINT32_MAX)
        {
            if (end < 20 || u32(archive.data + end - 20) != 0x07064b50 || u32(archive.data + end - 16) ||
                u32(archive.data + end - 4) != 1)
                return false;
            const auto offset = u64(archive.data + end - 12);
            if (!range(offset, 56, end - 20))
                return false;
            const auto* zip64 = archive.data + offset;
            if (u32(zip64) != 0x06064b50 || u64(zip64 + 4) < 44 || u32(zip64 + 16) || u32(zip64 + 20) ||
                u64(zip64 + 24) != u64(zip64 + 32))
                return false;
            count = u64(zip64 + 32);
            directorySize = u64(zip64 + 40);
            directory = u64(zip64 + 48);
        }
        if (!range(directory, directorySize, end) || count > directorySize / 46)
            return false;
        const uint64_t directoryEnd = directory + directorySize;
        for (uint64_t i = 0; i < count; ++i)
        {
            if (!range(directory, 46, directoryEnd))
                return false;
            const auto* entry = archive.data + directory;
            if (u32(entry) != 0x02014b50)
                return false;
            const uint64_t nameSize = u16(entry + 28), extraSize = u16(entry + 30), commentSize = u16(entry + 32);
            const uint64_t recordSize = 46 + nameSize + extraSize + commentSize;
            if (!range(directory, recordSize, directoryEnd))
                return false;
            directory += recordSize;
            if ((u16(entry + 8) & 1) || u16(entry + 10) || u16(entry + 34))
                return false;
            uint64_t packed = u32(entry + 20), size = u32(entry + 24), offset = u32(entry + 42);
            if (packed == UINT32_MAX || size == UINT32_MAX || offset == UINT32_MAX)
            {
                bool found = false;
                uint64_t extra = 0;
                const auto* fields = entry + 46 + nameSize;
                while (range(extra, 4, extraSize))
                {
                    const uint16_t tag = u16(fields + extra), length = u16(fields + extra + 2);
                    extra += 4;
                    if (!range(extra, length, extraSize))
                        return false;
                    if (tag == 1)
                    {
                        uint64_t cursor = 0;
                        for (uint64_t* value : { &size, &packed, &offset })
                        {
                            if (*value == UINT32_MAX)
                            {
                                if (!range(cursor, 8, length))
                                    return false;
                                *value = u64(fields + extra + cursor);
                                cursor += 8;
                            }
                        }
                        found = true;
                        break;
                    }
                    extra += length;
                }
                if (!found)
                    return false;
            }
            if (packed != size || !range(offset, 30, archive.size))
                return false;
            const auto* local = archive.data + offset;
            if (u32(local) != 0x04034b50 || (u16(local + 6) & 1) || u16(local + 8))
                return false;
            const uint64_t headerSize = 30 + uint64_t(u16(local + 26)) + u16(local + 28);
            if (!range(offset, headerSize, archive.size) || !range(offset + headerSize, size, archive.size))
                return false;
            visitor(std::string(reinterpret_cast<const char*>(entry + 46), nameSize),
                    View{ archive.data + offset + headerSize, size });
        }
        return true;
    }

private:
    static bool range(uint64_t offset, uint64_t size, uint64_t limit)
    {
        return offset <= limit && size <= limit - offset;
    }
    static uint16_t u16(const uint8_t* p)
    {
        return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
    }
    static uint32_t u32(const uint8_t* p)
    {
        return uint32_t(u16(p)) | (uint32_t(u16(p + 2)) << 16);
    }
    static uint64_t u64(const uint8_t* p)
    {
        return uint64_t(u32(p)) | (uint64_t(u32(p + 4)) << 32);
    }
};

} // namespace ovrtx::data
