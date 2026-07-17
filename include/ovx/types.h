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

#include <stdint.h>
#include <stddef.h>

/* ovx_string_t, ovx_token_t and ovx_string_or_token_t live in the shared header
 * so the ovrtx and ovstage public headers can coexist in one translation unit. */
#include <ovx/string_types.h>

/* Macro for creating ovx_string_t from string literals. Concatenating with an
 * empty literal makes non-literal arguments fail to compile. */
#define literal_to_ovx_string(str) ovx_string_t{ (str), sizeof("" str) - 1 }

static inline bool is_ovx_string_empty(const ovx_string_t* str)
{
    return !str || str->ptr == NULL || str->length == 0;
}

typedef uint64_t ovx_primpath_t;
typedef uint64_t ovx_primpath_list_t;

/* Sentinels for the three opaque path-dictionary handle types. Zero is the
 * invalid value for each; minting calls (`create_tokens_from_strings`,
 * `create_paths_from_strings`, `create_path_list_from_*`) never return zero
 * on success. The ovx_token_t typedef itself lives in <ovx/string_types.h>.
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
#define OVX_INVALID_TOKEN         ((ovx_token_t)0)
#define OVX_INVALID_PRIMPATH      ((ovx_primpath_t)0)
#define OVX_INVALID_PRIMPATH_LIST ((ovx_primpath_list_t)0)

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
