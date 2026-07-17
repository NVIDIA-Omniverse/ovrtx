/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef PATH_DICTIONARY_UTILS_H
#define PATH_DICTIONARY_UTILS_H

#include "path_dictionary_types.h"

#ifdef __cplusplus
extern "C"
{
#endif

    static inline ovx_api_result_t path_dictionary_create_tokens_from_strings(
        path_dictionary_instance_t* instance,
        const ovx_string_t* strings,
        size_t num_strings,
        ovx_token_t* out_tokens)
    {
        return instance->vtable->create_tokens_from_strings(
            instance->context, strings, num_strings, out_tokens);
    }

    static inline ovx_api_result_t path_dictionary_create_paths_from_tokens(
        path_dictionary_instance_t* instance,
        const ovx_token_t* tokens_per_path,
        const size_t* num_tokens_per_path,
        size_t num_paths,
        ovx_primpath_t* out_prim_paths)
    {
        return instance->vtable->create_paths_from_tokens(
            instance->context, tokens_per_path, num_tokens_per_path, num_paths, out_prim_paths);
    }

    static inline ovx_api_result_t path_dictionary_create_paths_from_strings(
        path_dictionary_instance_t* instance,
        const ovx_string_t* path_strings,
        size_t num_paths,
        ovx_primpath_t* out_prim_paths)
    {
        return instance->vtable->create_paths_from_strings(
            instance->context, path_strings, num_paths, out_prim_paths);
    }

    static inline ovx_api_result_t path_dictionary_create_path_list_from_paths(
        path_dictionary_instance_t* instance,
        const ovx_primpath_t* paths,
        size_t num_paths,
        ovx_primpath_list_t* out_path_list)
    {
        return instance->vtable->create_path_list_from_paths(
            instance->context, paths, num_paths, out_path_list);
    }

    static inline ovx_api_result_t path_dictionary_create_path_list_from_strings(
        path_dictionary_instance_t* instance,
        const ovx_string_t* path_strings,
        size_t num_paths,
        ovx_primpath_list_t* out_path_list)
    {
        return instance->vtable->create_path_list_from_strings(
            instance->context, path_strings, num_paths, out_path_list);
    }

    /* Increments the path-list refcount. See path_dictionary.h for the
       refcount contract. OVX_INVALID_PRIMPATH_LIST is a no-op success;
       unknown handle is OVX_API_ERROR. */
    static inline ovx_api_result_t path_dictionary_add_path_list_reference(
        path_dictionary_instance_t* instance,
        ovx_primpath_list_t path_list)
    {
        return instance->vtable->add_path_list_reference(
            instance->context, path_list);
    }

    /* Decrements the path-list refcount; erases storage and invalidates the
       handle at zero. See path_dictionary.h for the refcount contract.
       OVX_INVALID_PRIMPATH_LIST is a no-op success; unknown handle is
       OVX_API_ERROR. */
    static inline ovx_api_result_t path_dictionary_release_path_list_reference(
        path_dictionary_instance_t* instance,
        ovx_primpath_list_t path_list)
    {
        return instance->vtable->release_path_list_reference(
            instance->context, path_list);
    }

    static inline ovx_api_result_t path_dictionary_get_strings_from_tokens(
        path_dictionary_instance_t* instance,
        const ovx_token_t* tokens,
        size_t num_tokens,
        ovx_string_t* out_strings)
    {
        return instance->vtable->get_strings_from_tokens(
            instance->context, tokens, num_tokens, out_strings);
    }

    static inline ovx_api_result_t path_dictionary_get_tokens_from_paths(
        path_dictionary_instance_t* instance,
        const ovx_primpath_t* prim_paths,
        size_t num_paths,
        ovx_token_t* token_buffer,
        size_t token_buffer_size,
        ovx_token_t** out_tokens_per_path,
        size_t* out_num_tokens_per_path,
        size_t* out_num_paths_processed)
    {
        return instance->vtable->get_tokens_from_paths(
            instance->context, prim_paths, num_paths, token_buffer, token_buffer_size,
            out_tokens_per_path, out_num_tokens_per_path, out_num_paths_processed);
    }

    static inline ovx_api_result_t path_dictionary_get_num_paths_from_path_list(
        path_dictionary_instance_t* instance,
        ovx_primpath_list_t path_list,
        size_t* out_num_paths)
    {
        return instance->vtable->get_num_paths_from_path_list(
            instance->context, path_list, out_num_paths);
    }

    static inline ovx_api_result_t path_dictionary_get_paths_from_path_list(
        path_dictionary_instance_t* instance,
        ovx_primpath_list_t path_list,
        size_t start_offset,
        size_t max_paths,
        ovx_primpath_t* out_paths,
        size_t* out_num_paths)
    {
        return instance->vtable->get_paths_from_path_list(
            instance->context, path_list, start_offset, max_paths, out_paths, out_num_paths);
    }

    static inline void path_dictionary_release_error(
        path_dictionary_instance_t* instance,
        ovx_string_t error)
    {
        instance->vtable->release_error(
            instance->context, error);
    }

#ifdef __cplusplus
}
#endif

#endif /* PATH_DICTIONARY_UTILS_H */

