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

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C++"
{
#include <functional>
#include <type_traits>
}
#endif

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

/** Interned string identity within one path dictionary, valid for that dictionary's
 *  lifetime. No per-token release is needed. ID 0 denotes the empty string;
 *  UINT64_MAX (OVX_INVALID_TOKEN) is invalid.
 *
 *  This is a distinct type from path and path-list handles even when their IDs
 *  overlap. Access .raw_id for uint64 tensor payloads, legacy numeric APIs, or
 *  diagnostic output. Rebuild all producers and consumers when migrating from
 *  the former uint64 typedef. */
typedef struct ovx_token_t
{
    uint64_t raw_id; /**< Dictionary-local ID; does not identify the owning dictionary. */
} ovx_token_t;

/* C has no == for structs, so C code cannot compare two handles or test a handle
 * against its sentinel with ==. These helpers give C the same-kind equality and
 * validity tests that C++ gets from operator==, and keep the sentinel values in
 * one place. C++ code can use them too. */

/** Return whether `token` is not OVX_INVALID_TOKEN (UINT64_MAX). Token ID 0, the
 *  empty string, is valid. */
static inline bool ovx_token_is_valid(ovx_token_t token)
{
    return token.raw_id != UINT64_MAX;
}

/** Return whether two tokens have the same identity; both must belong to the same dictionary. */
static inline bool ovx_token_equal(ovx_token_t a, ovx_token_t b)
{
    return a.raw_id == b.raw_id;
}

#ifdef __cplusplus
/** Define same-kind equality, raw-ID ordering, and hashing for a handle with a
 *  uint64_t raw_id member. Invoke at global scope, after the struct definition.
 *  Shared by the token here and the path/list handles in ovx/types.h. */
#define OVX_DEFINE_HANDLE_CPP_OPERATORS(Type) \
static_assert(sizeof(Type) == sizeof(uint64_t), #Type " must match uint64_t size"); \
static_assert(std::is_trivially_copyable<Type>::value, #Type " must be trivially copyable"); \
/** Compare identities of the same handle kind; both must belong to the same owning resource. */ \
inline constexpr bool operator==(Type a, Type b) { return a.raw_id == b.raw_id; } \
/** Test whether two same-kind handles have different identities. */ \
inline constexpr bool operator!=(Type a, Type b) { return !(a == b); } \
/** Order raw IDs for sorting and ordered containers; this is not a content or hierarchy order. */ \
inline constexpr bool operator<(Type a, Type b) { return a.raw_id < b.raw_id; } \
inline constexpr bool operator>(Type a, Type b) { return b < a; } \
inline constexpr bool operator<=(Type a, Type b) { return !(b < a); } \
inline constexpr bool operator>=(Type a, Type b) { return !(a < b); } \
 \
namespace std \
{ \
/** Hash the ID for unordered containers, consistently with same-kind equality. */ \
template <> struct hash<Type> \
{ \
    size_t operator()(Type handle) const noexcept { return hash<uint64_t>{}(handle.raw_id); } \
}; \
}

extern "C++"
{
OVX_DEFINE_HANDLE_CPP_OPERATORS(ovx_token_t)
}
#endif

/** Accepts either a raw string or an interned token.
 *  When string.ptr is non-NULL, use string and ignore token, even if string.length
 *  is 0. Otherwise use token: ID 0 represents the empty string and UINT64_MAX
 *  (OVX_INVALID_TOKEN) is invalid. Token-only callers must leave string.ptr NULL. */
typedef struct ovx_token_or_string_t
{
    ovx_token_t  token;
    ovx_string_t string;
} ovx_token_or_string_t;

#endif /* OVX_STRING_TYPES_H */
