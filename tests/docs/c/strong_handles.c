/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved. */
#include <ovrtx/ovrtx_data_provider.h>

/* Duplicate compatible associations are invalid C, so aliases fail compilation. */
#define HANDLE_KIND(value) _Generic((value), \
    ovrtx_data_array_lease_id_t: 1, \
    ovrtx_data_provider_id_t: 2, \
    ovrtx_usd_handle_t: 3, \
    ovrtx_event_handle_t: 4, \
    ovrtx_attribute_binding_handle_t: 5, \
    ovrtx_map_handle_t: 6, \
    ovrtx_step_result_handle_t: 7, \
    ovrtx_render_var_output_handle_t: 8, \
    ovrtx_render_var_output_map_handle_t: 9, \
    ovrtx_op_id_t: 10, \
    ovrtx_query_handle_t: 11, \
    ovrtx_read_handle_t: 12)

_Static_assert(sizeof(ovrtx_data_array_lease_id_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_data_array_lease_id_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_data_array_lease_id_t){0})) == 1, "handle identity");
_Static_assert(sizeof(ovrtx_data_provider_id_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_data_provider_id_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_data_provider_id_t){0})) == 2, "handle identity");
_Static_assert(sizeof(ovrtx_usd_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_usd_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_usd_handle_t){0})) == 3, "handle identity");
_Static_assert(sizeof(ovrtx_event_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_event_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_event_handle_t){0})) == 4, "handle identity");
_Static_assert(sizeof(ovrtx_attribute_binding_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_attribute_binding_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_attribute_binding_handle_t){0})) == 5, "handle identity");
_Static_assert(sizeof(ovrtx_map_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_map_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_map_handle_t){0})) == 6, "handle identity");
_Static_assert(sizeof(ovrtx_step_result_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_step_result_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_step_result_handle_t){0})) == 7, "handle identity");
_Static_assert(sizeof(ovrtx_render_var_output_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_render_var_output_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_render_var_output_handle_t){0})) == 8, "handle identity");
_Static_assert(sizeof(ovrtx_render_var_output_map_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_render_var_output_map_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_render_var_output_map_handle_t){0})) == 9, "handle identity");
_Static_assert(sizeof(ovrtx_op_id_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_op_id_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_op_id_t){0})) == 10, "handle identity");
_Static_assert(sizeof(ovrtx_query_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_query_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_query_handle_t){0})) == 11, "handle identity");
_Static_assert(sizeof(ovrtx_read_handle_t) == sizeof(uint64_t), "handle layout");
_Static_assert(_Alignof(ovrtx_read_handle_t) == _Alignof(uint64_t), "handle alignment");
_Static_assert(HANDLE_KIND(((ovrtx_read_handle_t){0})) == 12, "handle identity");
