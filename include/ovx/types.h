/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVX_TYPES_H
#define OVX_TYPES_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* ovx_string_t, ovx_token_t and ovx_token_or_string_t live in the shared header
 * so the ovrtx and ovstage public headers can coexist in one translation unit. */
#include <ovx/string_types.h>

/* Macro for creating ovx_string_t from string literals. Concatenating with an
 * empty literal makes non-literal arguments fail to compile. */
#ifdef __cplusplus
    #define literal_to_ovx_string(str) ovx_string_t{ (str), sizeof("" str) - 1 }
#else
    #define literal_to_ovx_string(str) ((ovx_string_t){ (str), sizeof("" str) - 1 })
#endif

static inline bool is_ovx_string_empty(const ovx_string_t* str)
{
    return !str || str->ptr == NULL || str->length == 0;
}

/** Interned prim-path identity within one path dictionary, valid for that
 *  dictionary's lifetime. No per-path release is needed. ID 0 is invalid.
 *  A path handle is distinct from tokens and path-list handles with equal IDs. */
typedef struct ovx_primpath_t
{
    /** Dictionary-local ID, exposed for uint64 tensor payloads, legacy numeric APIs,
     *  and diagnostic output. */
    uint64_t raw_id;
} ovx_primpath_t;

/** Identity of a reference-counted path list within one path dictionary.
 *  Creating a list or adding a reference requires a matching explicit release.
 *  Copying this struct does not add a reference; it is not an owning C++ wrapper.
 *  ID 0 is invalid. Equality compares list identities, not their path contents. */
typedef struct ovx_primpath_list_t
{
    /** Dictionary-local ID, exposed for C equality checks, numeric cache keys,
     *  and diagnostic output. */
    uint64_t raw_id;
} ovx_primpath_list_t;

#ifdef __cplusplus
extern "C++"
{
OVX_DEFINE_HANDLE_CPP_OPERATORS(ovx_primpath_t)
OVX_DEFINE_HANDLE_CPP_OPERATORS(ovx_primpath_list_t)
}
#endif

/* Sentinels for the three opaque path-dictionary handle types. Token id 0
 * represents the empty string; UINT64_MAX is reserved for an invalid token.
 * Prim paths and path lists retain 0 as their invalid value. Minting calls
 * never return the corresponding invalid sentinel on success.
 * The ovx_token_t typedef itself lives in <ovx/string_types.h>.
 *
 * Handle lifetime regimes (see <ovx/path_dictionary/path_dictionary.h>):
 *   - ovx_token_t / ovx_primpath_t are dict-lifetime: they have NO
 *     per-handle release call and remain valid for as long as the path
 *     dictionary itself is alive.
 *   - ovx_primpath_list_t is refcounted: each `create_path_list_from_*`
 *     and each `path_dictionary_add_path_list_reference` produces one
 *     reference that must be matched by exactly one
 *     `path_dictionary_release_path_list_reference`. The
 *     `OVX_INVALID_PRIMPATH_LIST` sentinel is a no-op on both add/release.
 */
#ifdef __cplusplus
#define OVX_INVALID_TOKEN         ovx_token_t{UINT64_MAX}
#define OVX_INVALID_PRIMPATH      ovx_primpath_t{0}
#define OVX_INVALID_PRIMPATH_LIST ovx_primpath_list_t{0}
#else
#define OVX_INVALID_TOKEN         ((ovx_token_t){UINT64_MAX})
#define OVX_INVALID_PRIMPATH      ((ovx_primpath_t){0})
#define OVX_INVALID_PRIMPATH_LIST ((ovx_primpath_list_t){0})
#endif

/* C has no == for structs, so C code cannot compare two handles or test a handle
 * against its sentinel with ==. These helpers give C the same-kind equality and
 * validity tests that C++ gets from operator==, and keep the sentinel values in
 * one place. C++ code can use them too. The token helpers live in
 * <ovx/string_types.h>. */

/** Return whether `path` is not OVX_INVALID_PRIMPATH. */
static inline bool ovx_primpath_is_valid(ovx_primpath_t path)
{
    return path.raw_id != OVX_INVALID_PRIMPATH.raw_id;
}

/** Return whether two prim paths have the same identity; both must belong to the same dictionary. */
static inline bool ovx_primpath_equal(ovx_primpath_t a, ovx_primpath_t b)
{
    return a.raw_id == b.raw_id;
}

/** Return whether `list` is not OVX_INVALID_PRIMPATH_LIST. */
static inline bool ovx_primpath_list_is_valid(ovx_primpath_list_t list)
{
    return list.raw_id != OVX_INVALID_PRIMPATH_LIST.raw_id;
}

/** Return whether two path-list handles have the same list identity. This does not
 *  compare list contents; both must belong to the same dictionary. */
static inline bool ovx_primpath_list_equal(ovx_primpath_list_t a, ovx_primpath_list_t b)
{
    return a.raw_id == b.raw_id;
}

typedef enum
{
    OVX_API_SUCCESS = 0,
    OVX_API_ERROR = 1,
} ovx_api_status_t;

typedef struct
{
    ovx_api_status_t status;
    ovx_string_t error;
} ovx_api_result_t;

typedef struct ovx_string_or_prim_path_t
{
    ovx_primpath_t path; /* Optional prim path handle within the path_dictionary_interface */
    ovx_string_t string;
} ovx_string_or_prim_path_t;

#endif /* OVX_TYPES_H */
