// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovstage/ovstage.h>
#include <ovx/path_dictionary/path_dictionary.h>
#include <ovx/path_dictionary/path_dictionary_utils.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

static std::string_view view(ovx_string_t s) {
    return {s.ptr ? s.ptr : "", s.length};
}
static ovx_string_t text(const std::string& s) { return {s.data(), s.size()}; }

static void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <class Result> static void check(Result result) {
    require(result.status == OVRTX_API_SUCCESS,
            std::string(view(ovrtx_get_last_error())));
}

static void check_stage(ovstage_api_status_t status) {
    require(status == OVSTAGE_OK,
            "ovstage error " + std::to_string(status) + ": " +
                std::string(view(ovstage_get_last_error())));
}

static void wait_stage(ovstage_instance_t* stage,
                       ovstage_enqueue_result_t enqueue) {
    check_stage(enqueue.status);
    ovstage_op_wait_result_t done{};
    const auto status = ovstage_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &done);
    const bool failed = status != OVSTAGE_OK || done.error_op_id_count != 0;
    const std::string error =
        done.error_op_id_count
            ? std::string(
                  view(ovstage_get_last_op_error(stage, done.error_op_ids[0])))
            : std::string(view(ovstage_get_last_error()));
    ovstage_release_op(stage, enqueue.op_index);
    require(!failed, "ovstage operation failed: " + error);
}

template <typename T>
static std::vector<T>
copy_tensor(const DLTensor& tensor, uint8_t code, int components = 1) {
    require(tensor.device.device_type == kDLCPU && tensor.dtype.code == code &&
                tensor.dtype.bits == sizeof(T) * 8 && tensor.dtype.lanes == 1 &&
                tensor.shape && tensor.ndim == (components == 1 ? 1 : 2),
            "Unexpected output tensor type");
    require(tensor.shape[0] >= 0 &&
                (components == 1 || tensor.shape[1] == components),
            "Unexpected output tensor shape");
    int64_t stride = 1;
    for (int d = tensor.ndim - 1; d >= 0; --d) {
        require(!tensor.strides || tensor.strides[d] == stride,
                "Expected a contiguous output tensor");
        stride *= tensor.shape[d];
    }
    std::vector<T> copy(static_cast<size_t>(stride));
    if (!copy.empty()) {
        require(tensor.data != nullptr, "Missing output tensor data");
        std::memcpy(copy.data(),
                    static_cast<const uint8_t*>(tensor.data) +
                        tensor.byte_offset,
                    copy.size() * sizeof(T));
    }
    return copy;
}

struct Capture {
    std::array<uint32_t, 5> shape{};
    std::array<uint32_t, 3> selectors{};
    std::vector<uint32_t> valid;
    std::vector<float> distance, hit_world;
};

static Capture
capture(ovrtx_renderer_t* renderer, ovstage_ordinal_t ordinal, int steps = 10) {
    Capture captured;
    for (int step = 0; step < steps; ++step) {
        ovrtx_step_result_handle_t result_handle =
            OVRTX_INVALID_STEP_RESULT_HANDLE;
        ovrtx_render_var_output_t output{};
        try {
            // [snippet:doc-generic-wpm-step-c]
            const ovx_string_t product =
                literal_to_ovx_string("/Render/GenericWpm");
            ovrtx_render_product_set_t products{};
            products.render_products = &product;
            products.num_render_products = 1;
            const auto enqueue = ovrtx_step_with_stage(
                renderer, products, 0.1, ordinal, &result_handle);
            check(enqueue);
            ovrtx_op_wait_result_t done{};
            check(ovrtx_wait_op(
                renderer, enqueue.op_index, ovrtx_timeout_infinite, &done));
            require(done.num_error_ops == 0,
                    "Rendering failed; inspect the renderer log");
            ovrtx_render_product_set_outputs_t results{};
            check(ovrtx_fetch_results(
                renderer, result_handle, ovrtx_timeout_infinite, &results));
            // [/snippet:doc-generic-wpm-step-c]
            if (step == steps - 1) {
                ovrtx_render_var_output_handle_t handle =
                    OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE;
                for (size_t p = 0; p < results.output_count; ++p) {
                    const auto& product_output = results.outputs[p];
                    for (size_t f = 0; f < product_output.output_frame_count;
                         ++f) {
                        const auto& frame = product_output.output_frames[f];
                        for (size_t v = 0; v < frame.render_var_count; ++v) {
                            const auto& var = frame.output_render_vars[v];
                            if (view(var.render_var_path) ==
                                "/Render/GenericWpm/Contributions") {
                                handle = var.output_handle;
                            }
                        }
                    }
                }
                require(handle != OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE,
                        "No Contributions frame was produced");
                // [snippet:doc-generic-wpm-read-output-c]
                ovrtx_map_output_description_t map{};
                map.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
                check(ovrtx_map_render_var_output(
                    renderer, handle, &map, ovrtx_timeout_infinite, &output));

                // Channel and parameter order is not part of the contract; find
                // each by name.
                auto channel = [&](std::string_view name) -> const DLTensor& {
                    for (size_t i = 0; i < output.num_tensors; ++i) {
                        if (view(*output.tensors[i].name) == name) {
                            return *output.tensors[i].dl;
                        }
                    }
                    throw std::runtime_error("Missing channel: " +
                                             std::string(name));
                };
                auto parameter = [&](std::string_view name) {
                    for (size_t i = 0; i < output.num_params; ++i) {
                        if (view(output.params[i].name) != name) {
                            continue;
                        }
                        const auto copy =
                            copy_tensor<uint32_t>(output.params[i].dl, kDLUInt);
                        require(copy.size() == 1,
                                "Expected a scalar CPU parameter");
                        return copy[0];
                    }
                    throw std::runtime_error("Missing parameter: " +
                                             std::string(name));
                };
                captured.shape = {parameter("numTiles"),
                                  parameter("numTx"),
                                  parameter("raysPerTx"),
                                  parameter("maxBounces"),
                                  parameter("groupSize")};
                captured.selectors = {parameter("activeTxPatternIndex"),
                                      parameter("activeRxPatternIndex"),
                                      parameter("activeMappingPageIndex")};
                // These vectors and metadata copies remain valid after
                // unmapping.
                captured.valid =
                    copy_tensor<uint32_t>(channel("Valid"), kDLUInt);
                captured.distance =
                    copy_tensor<float>(channel("RoundTripDistanceM"), kDLFloat);
                captured.hit_world =
                    copy_tensor<float>(channel("HitPosWorld"), kDLFloat, 3);
                const size_t slots = std::accumulate(captured.shape.begin(),
                                                     captured.shape.end(),
                                                     size_t{1},
                                                     std::multiplies<size_t>());
                require(slots == captured.valid.size() &&
                            slots == parameter("maxContributions") &&
                            slots == captured.distance.size() &&
                            3 * slots == captured.hit_world.size(),
                        "Contribution dimensions do not match their channels");
                check(ovrtx_unmap_render_var_output(
                    renderer, output.map_handle, {}));
                output.map_handle = OVRTX_INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE;
                // [/snippet:doc-generic-wpm-read-output-c]
            }
            check(ovrtx_destroy_results(renderer, result_handle));
        } catch (...) {
            if (output.map_handle != OVRTX_INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE) {
                ovrtx_unmap_render_var_output(renderer, output.map_handle, {});
            }
            if (result_handle != OVRTX_INVALID_STEP_RESULT_HANDLE) {
                ovrtx_destroy_results(renderer, result_handle);
            }
            throw;
        }
    }
    return captured;
}

static void select_patterns(ovstage_instance_t* stage,
                            ovstage_query_handle_t sensor,
                            ovstage_ordinal_t ordinal,
                            std::array<uint32_t, 3> requested) {
    // [snippet:doc-generic-wpm-select-patterns-c]
    const ovx_string_t names[] = {
        literal_to_ovx_string("omni:sensor:GenericWpm:activeTxPatternIndex"),
        literal_to_ovx_string("omni:sensor:GenericWpm:activeRxPatternIndex"),
        literal_to_ovx_string("omni:sensor:GenericWpm:activeMappingPageIndex"),
    };
    int64_t shape[] = {1};
    for (size_t i = 0; i < requested.size(); ++i) {
        DLTensor tensor{};
        tensor.data = &requested[i];
        tensor.device = {kDLCPU, 0};
        tensor.ndim = 1;
        tensor.dtype = {kDLUInt, 32, 1};
        tensor.shape = shape;
        ovstage_write_data_t write{};
        write.tensors = &tensor;
        write.tensor_count = 1;
        write.is_array = false;
        // All three selectors belong to the same application-owned ordinal.
        wait_stage(stage,
                   ovstage_write_attribute(stage,
                                           sensor,
                                           {0, names[i]},
                                           ordinal,
                                           write,
                                           OVSTAGE_PRIM_MODE_UPSERT));
    }
    ovstage_write_floor_desc_t floor{};
    floor.ordinal = ordinal;
    floor.scope = OVSTAGE_SCOPE_ALL;
    wait_stage(stage, ovstage_advance_write_floor(stage, &floor));
    // Step the attached renderer with this same ordinal after publishing all
    // writes.
    // [/snippet:doc-generic-wpm-select-patterns-c]
}

static void save_csv(std::ofstream& csv,
                     ovstage_ordinal_t ordinal,
                     const Capture& captured,
                     bool depth) {
    // [snippet:doc-generic-wpm-valid-slots-c]
    for (size_t slot = 0; slot < captured.valid.size(); ++slot) {
        if (!captured.valid[slot]) {
            continue; // Dense holes are not returns.
        }
        size_t index = slot;
        std::array<size_t, 5> coordinates{};
        for (int axis = 4; axis >= 0; --axis) {
            coordinates[axis] = index % captured.shape[axis];
            index /= captured.shape[axis];
        }
        // Coordinates are tile, transmitter, ray, bounce, receiver slot
        // (fastest).
        csv << ordinal << ',' << slot;
        for (auto coordinate : coordinates) {
            csv << ',' << coordinate;
        }
        csv << ',' << captured.distance[slot];
        for (int axis = 0; axis < 3; ++axis) {
            csv << ',' << captured.hit_world[3 * slot + axis];
        }
        csv << ',';
        // Only the colocated, one-bounce depth recipe has range = round-trip
        // / 2.
        if (depth) {
            csv << captured.distance[slot] / 2;
        }
        csv << '\n';
    }
    // [/snippet:doc-generic-wpm-valid-slots-c]
    csv.flush();
    require(csv.good(), "Failed to write contribution CSV");
}

int main(int argc, char** argv) {
    if (argc < 2 || argc > 5) {
        std::cerr << "Usage: generic-wpm <ovrtx-public-root> "
                     "[depth|mixed|gaussian_bloom] "
                     "[output.csv] [--live-edits]\n";
        return 2;
    }
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    ovstage_query_handle_t sensor = OVSTAGE_INVALID_QUERY_HANDLE;
    path_dictionary_instance_t* dictionary = nullptr;
    ovx_primpath_list_t paths = OVX_INVALID_PRIMPATH_LIST;
    bool attached = false;
    int exit_code = 0;
    try {
        const auto root = std::filesystem::absolute(argv[1]);
        const std::string recipe = argc >= 3 ? argv[2] : "depth";
        const bool live =
            argc == 5 && std::string_view(argv[4]) == "--live-edits";
        require(recipe == "depth" || recipe == "mixed" ||
                    recipe == "gaussian_bloom",
                "Choose depth, mixed or gaussian_bloom");
        require(argc != 5 || (live && recipe == "mixed"),
                "--live-edits requires the mixed recipe");
        const std::filesystem::path destination =
            argc >= 4 ? argv[3] : "_output/contributions.csv";
        if (destination.has_parent_path()) {
            std::filesystem::create_directories(destination.parent_path());
        }
        std::ofstream csv(destination);
        require(csv.good(), "Cannot open output CSV");
        csv.precision(9);
        csv << "ordinal,slot,tile,tx,ray,bounce,rx_slot,round_trip_m,hit_world_"
               "x,hit_world_y,hit_world_z,range_m\n";
        const auto log_path =
            destination.parent_path() / (destination.stem().string() + ".log");
        const auto log = log_path.string();
        ovrtx_config_entry_t entries[] = {
            ovrtx_config_entry_motion_bvh(OVRTX_MOTION_BVH_ENABLE),
            ovrtx_config_entry_log_file_path(text(log))};
        ovrtx_config_t config{};
        config.entries = entries;
        config.entry_count = 2;
        check(ovrtx_register_schema_paths(&config));
        check(ovrtx_create_renderer(&config, &renderer));
        ovstage_config_t stage_config{};
        check_stage(ovstage_initialize(&stage_config));
        ovstage_instance_desc_t stage_desc{};
        stage_desc.name = "generic-wpm";
        check_stage(ovstage_create_instance(&stage_desc, &stage));
        check(ovrtx_attach_ovstage(renderer, stage));
        attached = true;
        const auto layer =
            root / "tests/docs/usd/data" / ("generic_wpm_" + recipe + ".usda");
        const auto scene = root / "examples/python/generic-wpm/scene.usda";
        require(std::filesystem::exists(layer) &&
                    std::filesystem::exists(scene),
                "Missing recipe or scene layer");
        const auto source =
            std::string("#usda 1.0\n(\n defaultPrim = \"World\"\n "
                        "metersPerUnit = 1\n") +
            " upAxis = \"Z\"\n timeCodesPerSecond = 10\n subLayers = [@" +
            layer.generic_string() + "@, @" + scene.generic_string() +
            "@]\n)\n";
        ovstage_ordinal_t ordinal = 1;
        const auto population = ovstage_population_open_usd_from_string(
            stage,
            text(source),
            ordinal,
            0.0,
            OVSTAGE_POPULATION_DOMAIN_RENDERING);
        check_stage(population.status);
        ovstage_population_op_wait_result_t populated{};
        check_stage(ovstage_population_wait_op(
            stage, population.op_index, OVSTAGE_TIMEOUT_INFINITE, &populated));
        require(populated.error_op_id_count == 0,
                "USD population failed; inspect the renderer log");
        ovstage_write_floor_desc_t floor{};
        floor.ordinal = ordinal;
        floor.scope = OVSTAGE_SCOPE_ALL;
        wait_stage(stage, ovstage_advance_write_floor(stage, &floor));

        dictionary = ovstage_get_path_dictionary(stage);
        const auto path = literal_to_ovx_string("/World/Sensor");
        require(path_dictionary_create_path_list_from_strings(
                    dictionary, &path, 1, &paths)
                        .status == OVX_API_SUCCESS,
                "Cannot create sensor path list");
        check_stage(ovstage_query_from_path_list(stage, paths, &sensor));
        const std::array<std::array<uint32_t, 3>, 5> requests = {
            {{0, 0, 0}, {1, 1, 1}, {2, 1, 1}, {0, 1, 0}, {0, 0, 0}}
        };
        const std::array<size_t, 5> slot_counts = {2, 6, 18, 18, 2};
        Capture previous;
        for (size_t edit = 0; edit < (live ? requests.size() : 1); ++edit) {
            if (edit) {
                select_patterns(stage, sensor, ++ordinal, requests[edit]);
            }
            auto current = capture(renderer, ordinal, edit ? 1 : 10);
            const auto accepted = edit == 3 ? requests[2] : requests[edit];
            require(current.selectors == accepted,
                    "Unexpected accepted selectors");
            const size_t expected_slots = recipe == "depth" ? 15
                                          : recipe == "gaussian_bloom"
                                              ? 1215
                                              : slot_counts[edit];
            const size_t valid_count =
                std::count_if(current.valid.begin(),
                              current.valid.end(),
                              [](uint32_t v) { return v != 0; });
            require(current.valid.size() == expected_slots &&
                        valid_count ==
                            (recipe == "gaussian_bloom" ? 819 : expected_slots),
                    "Unexpected contribution count or invalid returns");
            if (recipe == "depth") {
                require(std::abs(current.distance[7] / 2 - 11) < 1e-3,
                        "Expected 11 m centre range");
            }
            if (edit == 3) {
                require(current.shape == previous.shape &&
                            current.valid == previous.valid,
                        "Rejected edit changed contribution dimensions or "
                        "validity");
                // Independently rendered floats need numeric, not bitwise,
                // comparison.
                const auto near = [](float a, float b) {
                    return std::abs(a - b) <= 1e-5f;
                };
                require(std::equal(current.distance.begin(),
                                   current.distance.end(),
                                   previous.distance.begin(),
                                   near),
                        "Rejected edit changed contribution distances");
                require(std::equal(current.hit_world.begin(),
                                   current.hit_world.end(),
                                   previous.hit_world.begin(),
                                   near),
                        "Rejected edit changed contribution world positions");
            }
            std::cout << "ordinal=" << ordinal
                      << " requested=" << requests[edit][0] << '/'
                      << requests[edit][1] << '/' << requests[edit][2]
                      << " accepted=" << current.selectors[0] << '/'
                      << current.selectors[1] << '/' << current.selectors[2]
                      << " shape=(";
            for (size_t axis = 0; axis < current.shape.size(); ++axis) {
                std::cout << (axis ? "," : "") << current.shape[axis];
            }
            std::cout << ") valid=" << valid_count << '/'
                      << current.valid.size() << '\n';
            save_csv(csv, ordinal, current, recipe == "depth");
            previous = std::move(current);
        }
        std::cout << "Saved " << destination << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        exit_code = 1;
    }
    if (sensor != OVSTAGE_INVALID_QUERY_HANDLE) {
        ovstage_release_query(stage, sensor);
    }
    if (dictionary && paths != OVX_INVALID_PRIMPATH_LIST) {
        path_dictionary_release_path_list_reference(dictionary, paths);
    }
    if (attached &&
        ovrtx_detach_ovstage(renderer).status != OVRTX_API_SUCCESS) {
        exit_code = 1;
    }
    if (renderer &&
        ovrtx_destroy_renderer(renderer).status != OVRTX_API_SUCCESS) {
        exit_code = 1;
    }
    if (stage && ovstage_destroy_instance(stage) != OVSTAGE_OK) {
        exit_code = 1;
    }
    ovstage_shutdown();
    return exit_code;
}
