/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

/* Canonical ovx string view types, shared by the ovrtx and ovstage public
 * headers so the two can coexist in a single translation unit. */

#ifndef OVX_STRING_TYPES_H
#define OVX_STRING_TYPES_H

#include <stdint.h>
#include <stddef.h>

/** Non-owning UTF-8 string view; `length` is the byte count. The pointed-to
 *  storage is owned by whoever produced the view (a callee copies an input it
 *  needs to retain past the call).
 *
 *  Null-termination is asymmetric:
 *   - As an input, treat it as a length-prefixed view: `ptr[length]` is not
 *     assumed to be '\0', and substring views into a larger buffer are valid.
 *   - As a value produced by the library (return value, out-param, or callback
 *     argument), a non-empty view is null-terminated — `ptr[length] == '\0'` —
 *     so `ptr` may be passed directly to libc functions that require a C string.
 *     A `{ NULL, 0 }` view denotes "no value". A null pointer with non-zero
 *     length is invalid.
 *
 *  Compare by (length, bytes): `a.length == b.length && memcmp(a.ptr, b.ptr,
 *  a.length) == 0`. `strncmp` is unsafe — a shorter string prefix-matches. */
typedef struct ovx_string_t
{
    const char* ptr;  /**< Pointer to UTF-8 data. */
    size_t      length;  /**< Length in bytes. */
} ovx_string_t;

typedef uint64_t ovx_token_t;

/** Accepts either a pre-resolved token (when token != 0) or a raw string. */
typedef struct ovx_string_or_token_t
{
    ovx_token_t  token;
    ovx_string_t string;
} ovx_string_or_token_t;

#endif /* OVX_STRING_TYPES_H */
