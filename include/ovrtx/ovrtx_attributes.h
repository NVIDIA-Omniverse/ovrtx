/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVRTX_ATTRIBUTES_H
#define OVRTX_ATTRIBUTES_H

#include "ovrtx.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/** @defgroup ovrtx_attribute_helpers Attribute helper functions
 *  @{
 */

/*----------------------------------------------------------------------
* Transform attribute writes
*/

/*
* Sets transform attribute values from row-major matrix 4x4 double values
*/
static inline ovrtx_enqueue_result_t ovrtx_set_xform_mat(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_matrix44d_t* transforms);

/*
* Sets transform attribute values from position in double and a 3x3 row-major rotation matrix
*/
static inline ovrtx_enqueue_result_t ovrtx_set_xform_pos_rot3x3(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_pos3d_rot3x3f_t* transforms);

/*
* Sets transform attribute values from position in double, a 4 float quaternion rotation and 3 float scale
*/
static inline ovrtx_enqueue_result_t ovrtx_set_xform_pos_rot_scale(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_pos3d_rot4f_scale3f_t* transforms);

/*
* Sets the resetXformStack attribute for the given prims (one bool per prim).
* When true: the prim's transform is treated as world-space; parent transforms are ignored when computing the prim's final transform.
* When false (default): the prim's transform is in local space and is composed with the parent's world transform.
* */
static inline ovrtx_enqueue_result_t ovrtx_set_reset_xform_stack(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const bool* values);

/* ----------------------------------------------------------------------
* Path and token attribute writes
*/

/**
 * Write path string values as relationship arrays to an attribute on the specified prims.
 * @see The implementation section below for full parameter documentation.
 */
static inline ovrtx_enqueue_result_t ovrtx_set_path_attributes(
    ovrtx_renderer_t* instance,
    const ovx_string_t* prim_paths,
    size_t path_count,
    ovx_string_t attribute_name,
    const ovx_string_t* path_values);

/**
 * Write token string values to an attribute on the specified prims.
 * @see The implementation section below for full parameter documentation.
 */
static inline ovrtx_enqueue_result_t ovrtx_set_token_attributes(
    ovrtx_renderer_t* instance,
    const ovx_string_t* prim_paths,
    size_t path_count,
    ovx_string_t attribute_name,
    const ovx_string_t* token_values);

/** @} */ // end of ovrtx_attribute_helpers

/* ----------------------------------------------------------------------
* Implementation
*/

/* C11 static_assert compatibility */
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
    #define OVRTX_STATIC_ASSERT(cond, msg) _Static_assert(cond, msg)
#else
    #ifdef _MSC_VER
        #define OVRTX_UNUSED
    #else
        #define OVRTX_UNUSED __attribute__((unused))
    #endif

    #define OVRTX_CONCAT_(a, b) a##b
    #define OVRTX_CONCAT(a, b) OVRTX_CONCAT_(a, b)
    #define OVRTX_STATIC_ASSERT(cond, msg) \
        typedef char OVRTX_CONCAT(ovrtx_static_assert_, __LINE__)[(cond) ? 1 : -1] OVRTX_UNUSED
#endif

/** Make a 1-D CPU DLTensor for C attribute writes.
 *
 * The C API uses @c DLDataType::lanes for multi-component attribute elements.
 * For example, pass @c size=10 and @c dtype={kDLFloat,32,3} for a point3f[]
 * array with 10 points, or @c size=N and @c dtype={kDLFloat,64,16} for N
 * 4x4 double matrices.
 */
static inline DLTensor ovrtx_make_write_cpu_tensor(const void* ptr, const size_t* size, DLDataType dtype)
{
    static int64_t s_stride1 = 1;
    DLTensor tensor;
    tensor.data = (void*)ptr; /* dltensor is non-const even for read-only */
    tensor.device.device_type = kDLCPU;
    tensor.device.device_id = 0;
    tensor.ndim = 1;
    tensor.dtype = dtype;
    tensor.shape = (int64_t*)size;
    tensor.strides = &s_stride1;
    tensor.byte_offset = 0;
    return tensor;
}

static inline ovrtx_binding_desc_or_handle_t ovrtx_make_binding_desc(
    const ovx_string_t* paths,
    size_t path_count,
    ovx_string_t attribute_name,
    ovrtx_attribute_semantic_t semantic,
    DLDataType dtype)
{
    ovrtx_binding_desc_or_handle_t bindingDesc;
    ovrtx_attribute_type_t attr_type;
    ovx_string_or_token_t attr_lookup;

    memset(&bindingDesc, 0, sizeof(bindingDesc));
    memset(&attr_lookup, 0, sizeof(attr_lookup));

    attr_lookup.string = attribute_name;

    attr_type.dtype = dtype;
    attr_type.is_array = false;
    attr_type.semantic = semantic;

    bindingDesc.binding_desc.prim_list.prim_paths = paths;
    bindingDesc.binding_desc.prim_list.num_paths = path_count;
    bindingDesc.binding_desc.attribute_name = attr_lookup;
    bindingDesc.binding_desc.attribute_type = attr_type;
    bindingDesc.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_EXISTING_ONLY;
    bindingDesc.binding_desc.flags = OVRTX_BINDING_FLAG_NONE;

    return bindingDesc;
}

OVRTX_STATIC_ASSERT(sizeof(ovrtx_xform_matrix44d_t) == 8 * 16, "ovrtx_xform_matrix44d_t size mismatch");

static inline ovrtx_enqueue_result_t ovrtx_set_xform_mat(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_matrix44d_t* transforms)
{
    DLDataType type;
    DLTensor tensor;
    ovrtx_input_buffer_t buffer;
    ovrtx_binding_desc_or_handle_t binding_desc;

    type.code = kDLFloat;
    type.bits = 64;
    type.lanes = 16;

    tensor = ovrtx_make_write_cpu_tensor(transforms, &path_count, type);

    memset(&buffer, 0, sizeof(buffer));
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;
    buffer.dirty_bits = NULL;

    ovx_string_t localMatrix = literal_to_ovx_string("omni:xform");
    binding_desc = ovrtx_make_binding_desc(paths, path_count, localMatrix, OVRTX_SEMANTIC_XFORM_MAT4x4, type);

    return ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);
}

OVRTX_STATIC_ASSERT(sizeof(ovrtx_xform_pos3d_rot4f_scale3f_t) == 56, "ovrtx_xform_pos3d_rot4f_scale3f_t size mismatch");

static inline ovrtx_enqueue_result_t ovrtx_set_xform_pos_rot_scale(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_pos3d_rot4f_scale3f_t* transforms)
{
    DLDataType type;
    DLTensor tensor;
    ovrtx_input_buffer_t buffer;
    ovrtx_binding_desc_or_handle_t binding_desc;

    type.code = kDLUInt;
    type.bits = 8;
    type.lanes = 56; /* just use the bytes as the types are non-uniform */

    tensor = ovrtx_make_write_cpu_tensor(transforms, &path_count, type);

    memset(&buffer, 0, sizeof(buffer));
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;
    buffer.dirty_bits = NULL;

    ovx_string_t localMatrix = literal_to_ovx_string("omni:xform");
    binding_desc = ovrtx_make_binding_desc(paths, path_count, localMatrix, OVRTX_SEMANTIC_XFORM_POS3d_ROT4f_SCALE3f, type);

    return ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);
}

OVRTX_STATIC_ASSERT(sizeof(ovrtx_xform_pos3d_rot3x3f_t) == 64, "ovrtx_xform_pos3d_rot3x3f_t size mismatch");

static inline ovrtx_enqueue_result_t ovrtx_set_xform_pos_rot3x3(
    ovrtx_renderer_t* instance,
    const ovx_string_t* paths,
    size_t path_count,
    const ovrtx_xform_pos3d_rot3x3f_t* transforms)
{
    DLDataType type;
    DLTensor tensor;
    ovrtx_input_buffer_t buffer;
    ovrtx_binding_desc_or_handle_t binding_desc;

    type.code = kDLUInt;
    type.bits = 8;
    type.lanes = 64; /* just use the bytes as the types are non-uniform */

    tensor = ovrtx_make_write_cpu_tensor(transforms, &path_count, type);

    memset(&buffer, 0, sizeof(buffer));
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;
    buffer.dirty_bits = NULL;

    ovx_string_t localMatrix = literal_to_ovx_string("omni:xform");
    binding_desc = ovrtx_make_binding_desc(paths, path_count, localMatrix, OVRTX_SEMANTIC_XFORM_POS3d_ROT3x3f, type);

    return ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);
}

static inline ovrtx_enqueue_result_t ovrtx_set_reset_xform_stack(ovrtx_renderer_t* instance, const ovx_string_t* paths, size_t path_count, const bool* values)
{
    DLDataType type{ kDLUInt, 8, 1 };
    DLTensor tensor = ovrtx_make_write_cpu_tensor(values, &path_count, type);
    ovrtx_input_buffer_t buffer = { &tensor, 1, nullptr, {} };
    ovrtx_binding_desc_or_handle_t binding_desc =
        ovrtx_make_binding_desc(paths, path_count, literal_to_ovx_string("omni:resetXformStack"), OVRTX_SEMANTIC_NONE, type);
    return ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);
}

/* ============================================================================
 * Path and Token String Attribute Writers
 * ============================================================================
 * These functions write path or token string attributes to prims. The strings
 * are converted to internal path/token IDs synchronously during the call.
 * The input strings only need to be valid for the duration of the call.
 */

/*
Maximum number of prims for stack - allocated tensor storage
*/
#define OVRTX_PATH_ATTR_STACK_TENSOR_COUNT 16

/**
 * Write path string values as relationship arrays to an attribute on the specified prims.
 * Each prim receives a single-element array containing its path value, since USD
 * relationship attributes are always arrays.
 * @param instance Renderer instance
 * @param prim_paths Array of prim paths to write the attribute to
 * @param path_count Number of prims
 * @param attribute_name Name of the attribute to write
 * @param path_values Array of path strings to write (one per prim)
 * @return Result of the enqueue operation
 */
static inline ovrtx_enqueue_result_t ovrtx_set_path_attributes(
    ovrtx_renderer_t* instance,
    const ovx_string_t* prim_paths,
    size_t path_count,
    ovx_string_t attribute_name,
    const ovx_string_t* path_values)
{
    OVRTX_STATIC_ASSERT(sizeof(ovx_string_t) == 16, "ovx_string_t must be 16 bytes (128 bits)");
    DLDataType type{ kDLUInt, 128, 1 };  /* ovx_string_t = ptr(8 bytes) + length(8 bytes) = 16 bytes = 128 bits */

    /*
    *   Path attributes are USD relationships, which must be arrays.
    *   Each prim gets a single-element array containing its path value.
    *   Use stack storage for small counts, heap for larger.
    */
    DLTensor stackTensors[OVRTX_PATH_ATTR_STACK_TENSOR_COUNT];
    int64_t stackShapes[OVRTX_PATH_ATTR_STACK_TENSOR_COUNT];
    DLTensor* tensors = stackTensors;
    int64_t* shapes = stackShapes;
    
    /* Allocate heap storage if needed */
    DLTensor* heapTensors = nullptr;
    int64_t* heapShapes = nullptr;
    if (path_count > OVRTX_PATH_ATTR_STACK_TENSOR_COUNT)
    {
        heapTensors = new DLTensor[path_count];
        heapShapes = new int64_t[path_count];
        tensors = heapTensors;
        shapes = heapShapes;
    }

    /*Initialize each tensor as a single-element array pointing to its path value*/
    for (size_t i = 0; i < path_count; ++i)
    {
        shapes[i] = 1;  /*Each array has 1 element*/
        tensors[i] = {};
        tensors[i].data = const_cast<ovx_string_t*>(&path_values[i]);
        tensors[i].device = { kDLCPU, 0 };
        tensors[i].ndim = 1;
        tensors[i].dtype = type;
        tensors[i].shape = &shapes[i];
        tensors[i].strides = nullptr;
        tensors[i].byte_offset = 0;
    }

    ovrtx_input_buffer_t buffer = { tensors, path_count, nullptr, {} };

    /*Build binding descriptor with is_array=true for relationship attribute*/
    ovrtx_binding_desc_or_handle_t binding_desc{};
    binding_desc.binding_desc.prim_list = { prim_paths, path_count };
    binding_desc.binding_desc.attribute_name = { {}, attribute_name };
    binding_desc.binding_desc.attribute_type = { type, true, OVRTX_SEMANTIC_PATH_STRING };  /*is_array=true*/
    binding_desc.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_EXISTING_ONLY;
    binding_desc.binding_desc.flags = OVRTX_BINDING_FLAG_NONE;

    ovrtx_enqueue_result_t result = ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);

    /*Clean up heap storage if allocated*/
    if (heapTensors)
    {
        delete[] heapTensors;
        delete[] heapShapes;
    }

    return result;
}

/**
 * Write token string values to an attribute on the specified prims.
 * @param instance Renderer instance
 * @param prim_paths Array of prim paths to write the attribute to
 * @param path_count Number of prims
 * @param attribute_name Name of the attribute to write
 * @param token_values Array of token strings to write (one per prim)
 * @return Result of the enqueue operation
 */
static inline ovrtx_enqueue_result_t ovrtx_set_token_attributes(
    ovrtx_renderer_t* instance,
    const ovx_string_t* prim_paths,
    size_t path_count,
    ovx_string_t attribute_name,
    const ovx_string_t* token_values)
{
    DLDataType type;
    DLTensor tensor;
    ovrtx_input_buffer_t buffer;
    ovrtx_binding_desc_or_handle_t binding_desc;

    OVRTX_STATIC_ASSERT(sizeof(ovx_string_t) == 16, "ovx_string_t must be 16 bytes (128 bits)");

    type.code = kDLUInt;
    type.bits = 128;  /* ovx_string_t = ptr (8 bytes) + length (8 bytes) = 16 bytes = 128 bits */
    type.lanes = 1;

    tensor = ovrtx_make_write_cpu_tensor(token_values, &path_count, type);

    memset(&buffer, 0, sizeof(buffer));
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;
    buffer.dirty_bits = NULL;

    binding_desc = ovrtx_make_binding_desc(prim_paths, path_count, attribute_name, OVRTX_SEMANTIC_TOKEN_STRING, type);

    return ovrtx_write_attribute(instance, &binding_desc, &buffer, OVRTX_DATA_ACCESS_SYNC);
}

#endif /* OVRTX_ATTRIBUTES_H */
