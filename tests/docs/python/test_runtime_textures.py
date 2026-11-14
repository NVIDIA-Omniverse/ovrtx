# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Exercise the shipped public example with CUDA texel producers."""
import os
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import pytest
import numpy as np
from PIL import Image
import ovrtx
import ovstage
import warp as wp


# [snippet:doc-runtime-texture-python-producer]
@wp.kernel
def fill_texture(pixels: wp.array(dtype=wp.uint8), channel: int):
    component = wp.tid() % 4
    # Interleaved RGBA8: one primary color and opaque alpha.
    pixels[wp.tid()] = wp.uint8(255 if component == channel or component == 3 else 0)
# [/snippet:doc-runtime-texture-python-producer]


@pytest.fixture
def renderer(output_dir):
    """Runtime textures require a single renderer GPU, including on multi-GPU hosts."""
    renderer = ovrtx.Renderer(ovrtx.RendererConfig(
        active_cuda_gpus="0",
        log_file_path=str(output_dir / "runtime-texture-authoring.log"),
    ))
    try:
        yield renderer
    finally:
        renderer.destroy()


def _runtime_texture_state(stage, ordinal):
    """Read the authored values and connections through the public data plane."""
    attributes = {
        "/Texture": ["usd-prim-type", "texture:uri", "texture:dimension", "texture:extent",
                     "texture:format", "texture:colorSpace", "texture:data"],
        "/RuntimeMaterial": ["usd-prim-type", "outputs:surface"],
        "/RuntimeMaterial/Surface": ["usd-prim-type", "info:id", "inputs:roughness", "inputs:diffuseColor"],
        "/RuntimeMaterial/Tex": ["usd-prim-type", "info:id", "inputs:file", "inputs:st"],
        "/RuntimeMaterial/UV": ["usd-prim-type", "info:id", "inputs:varname"],
    }
    result = {}
    with ovstage.PathDictionary(stage) as paths:
        for path, names in attributes.items():
            path_list = paths.create_path_list_from_strings([path])
            try:
                with stage.query_from_path_list(path_list) as query:
                    for name in names:
                        with stage.read_attributes(
                            query, [paths.intern_token(name)], ovstage.OrdinalRange.latest(ordinal)
                        ) as read:
                            group = read.fetch_next()
                            assert group is not None, (path, name)
                            try:
                                column = group.columns[0]
                                result[path, name] = (column.semantic, column.is_array,
                                                      np.asarray(column.array(0)).tolist())
                            finally:
                                stage.release_group(group)
            finally:
                paths.destroy_path_list(path_list)
    return result


@pytest.mark.skipif(
    os.environ.get("OVRTX_SOURCE", "prebuilt") != "current",
    reason="Runtime textures require the matching current OVRTX/OVStage SDKs",
)
def test_runtime_texture_ovstage_authoring(renderer, stage, output_dir):
    """Recreate the texture and retarget an existing shader, then compare state and rendering."""
    import numpy as np
    import ovstage

    scene = Path(__file__).resolve().parents[1] / "data/ovrtx-test-runtime-textures.usda"
    ovstage.population.open_usd(stage, str(scene), ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    expected = _runtime_texture_state(stage, 1)

    def capture(ordinal):
        for _ in range(41):
            products = renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)
        output = products["/Render/Camera"].frames[-1].render_vars["/Render/Camera/LdrColor"]
        with output.map(device=ovrtx.Device.CPU) as mapped:
            return np.from_dlpack(mapped).copy()

    baseline = capture(1)
    # Keep the shader network; require the snippet to recreate the texture and repair its URI.
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Texture"])
        try:
            with stage.query_from_path_list(path_list) as query:
                stage.delete_attributes(query, [], ordinal=2).wait()
        finally:
            paths.destroy_path_list(path_list)
        shader_paths = paths.create_path_list_from_strings(["/RuntimeMaterial/Tex"])
        try:
            with stage.query_from_path_list(shader_paths) as query:
                pair_type = ovstage.DLDataType(ovstage.DLDataTypeCode.kDLUInt, 64, 2)
                missing_asset = np.array([paths.intern_token("dynamic://missingTexture").raw_id, 0], dtype=np.uint64)
                stage.write_attribute(
                    query, "inputs:file", ordinal=2, is_array=False,
                    tensors=ovstage.make_dltensor(missing_asset, dtype=pair_type, shape=[1]),
                    semantic=ovstage.AttributeSemantic.ASSET_PATH_ID,
                ).wait()
        finally:
            paths.destroy_path_list(shader_paths)
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    missing = capture(2)
    assert np.abs(baseline.astype(np.int16) - missing.astype(np.int16)).mean() > 5
    ordinal = 3

    # [snippet:doc-runtime-texture-ovstage-python]
    import numpy as np
    import ovstage

    with ovstage.PathDictionary(stage) as paths:
        texture_paths = paths.create_path_list_from_strings(["/Texture"])
        shader_paths = paths.create_path_list_from_strings(["/RuntimeMaterial/Tex"])
        try:
            with stage.query_from_path_list(texture_paths) as query:
                # INSERT creates the texture prim and rejects an existing prim at this path.
                stage.write_attribute(
                    query, "usd-prim-type", ordinal=ordinal, is_array=False,
                    tensors=np.array([paths.intern_token("OmniRuntimeTexture").raw_id], dtype=np.uint64),
                    prim_mode=ovstage.PrimMode.INSERT,
                ).wait()
                stage.write_attribute(
                    query, "texture:uri", ordinal=ordinal, is_array=True,
                    tensors=np.frombuffer(b"dynamic://runtimeTextureExample", dtype=np.uint8),
                    semantic=ovstage.AttributeSemantic.STRING,
                ).wait()
                for attribute, value in (("texture:dimension", "2d"),
                                         ("texture:format", "rgba8unorm"),
                                         ("texture:colorSpace", "linear")):
                    stage.write_attribute(
                        query, attribute, ordinal=ordinal, is_array=False,
                        tensors=np.array([paths.intern_token(value).raw_id], dtype=np.uint64),
                        semantic=ovstage.AttributeSemantic.TOKEN_ID,
                    ).wait()
                stage.write_attribute(
                    query, "texture:extent", ordinal=ordinal, is_array=False,
                    tensors=np.array([[1, 1, 1]], dtype=np.int32),
                ).wait()
                stage.write_attribute(
                    query, "texture:data", ordinal=ordinal, is_array=True,
                    tensors=np.array([255, 0, 0, 255], dtype=np.uint8),
                ).wait()

            # Assets carry authored/resolved token IDs. Dynamic URIs need no file resolution.
            pair_type = ovstage.DLDataType(ovstage.DLDataTypeCode.kDLUInt, 64, 2)
            asset = np.array([paths.intern_token("dynamic://runtimeTextureExample").raw_id, 0], dtype=np.uint64)
            with stage.query_from_path_list(shader_paths) as query:
                stage.write_attribute(
                    query, "inputs:file", ordinal=ordinal, is_array=False,
                    tensors=ovstage.make_dltensor(asset, dtype=pair_type, shape=[1]),
                    semantic=ovstage.AttributeSemantic.ASSET_PATH_ID,
                ).wait()

            # Publish only after every write succeeds, then render this ordinal.
            stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        finally:
            for path_list in (texture_paths, shader_paths):
                paths.destroy_path_list(path_list)
    # [/snippet:doc-runtime-texture-ovstage-python]

    assert _runtime_texture_state(stage, ordinal) == expected
    authored = capture(ordinal)
    assert np.abs(baseline.astype(np.int16) - authored.astype(np.int16)).mean() < 1
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Texture"])
        try:
            with stage.query_from_path_list(path_list) as query:
                stage.write_attribute(query, "texture:data", ordinal=4, is_array=True,
                                      tensors=np.array([0, 255, 0, 255], dtype=np.uint8)).wait()
        finally:
            paths.destroy_path_list(path_list)
    stage.advance_write_floor(4, ovstage.Scope.ALL).wait()
    updated = capture(4)
    for name, image, channel in (("authored", authored, 0), ("updated", updated, 1)):
        mean = image[64:-64, 64:-64, :3].astype(np.float32).mean(axis=(0, 1))
        assert mean[channel] > max(np.delete(mean, channel)) + 60, mean
        Image.fromarray(image).save(output_dir / f"runtime-texture-ovstage-{name}.png")


# The released pair pinned by the public docs predates stage-owned textures.
# Current-mode failures must stay failures, including missing schema support.
@pytest.mark.skipif(
    os.environ.get("OVRTX_SOURCE", "prebuilt") != "current",
    reason="Runtime textures require the matching current OVRTX/OVStage SDKs",
)
def test_runtime_texture_cuda_updates(renderer, stage, output_dir):
    """CUDA texels turn the material red, then green after one update step."""
    scene = Path(__file__).resolve().parents[1] / "data/ovrtx-test-runtime-textures.usda"
    ovstage.population.open_usd(stage, scene, ordinal=1)
    images = []
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Texture"])
        query = stage.query_from_path_list(path_list)
        try:
            # [snippet:doc-runtime-texture-python-update]
            # Keep the dimensions explicit; the payload is a packed byte array.
            extent = np.array([[256, 256, 1]], dtype=np.int32)
            pixels = wp.empty(256 * 256 * 4, dtype=wp.uint8, device="cuda:0")
            for channel, ordinal in ((0, 1), (1, 2)):
                wp.launch(fill_texture, dim=256 * 256 * 4,
                          inputs=[pixels, channel], device="cuda:0")
                # Finish the producer before ovstage reads its storage.
                wp.synchronize_device("cuda:0")

                stage.write_attribute(query, "texture:extent", tensors=extent,
                                      is_array=False, ordinal=ordinal).wait()
                stage.write_attribute(query, "texture:data", tensors=pixels,
                                      is_array=True, ordinal=ordinal).wait()
                # Seal only after both writes succeed. The producer may now reuse pixels.
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                products = renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)
                # [/snippet:doc-runtime-texture-python-update]
                # Initial shader loading needs warm-up; the green update gets one step.
                if ordinal == 1:
                    for _ in range(40):
                        products = renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)
                output = products["/Render/Camera"].frames[-1].render_vars["/Render/Camera/LdrColor"]
                with output.map(device=ovrtx.Device.CPU) as mapped:
                    images.append(np.from_dlpack(mapped).copy())
                del mapped, output
                del products
        finally:
            query.release().wait()
            paths.destroy_path_list(path_list)
    for channel, image in enumerate(images):
        assert image.shape[:2] == (512, 512)
        mean = image[64:-64, 64:-64, :3].mean(axis=(0, 1))
        assert mean[channel] > max(np.delete(mean, channel)) + 60
        Image.fromarray(image).save(output_dir / f"runtime-texture-cuda-{channel}.png")


def test_camera_luminance_kernel():
    """Known linear-light luminances catch channel order, gamma, alpha and row inversion errors."""
    import warp as wp

    example = Path(__file__).resolve().parents[3] / "examples/python/runtime-textures/main.py"
    spec = importlib.util.spec_from_file_location("carter_monitor_example", example)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    source = np.array([
        [[255, 0, 0, 0], [0, 255, 0, 64], [0, 0, 255, 128]],
        [[0, 0, 0, 0], [255, 255, 255, 0], [128, 128, 128, 0]],
    ], dtype=np.uint8)
    gpu_source = wp.array(source, dtype=wp.uint8, device="cuda:0")
    output = wp.empty(2 * 3 * 4, dtype=wp.uint8, device="cuda:0")
    wp.launch(module.camera_luminance, dim=(2, 3), inputs=[gpu_source, output], device="cuda:0")
    wp.synchronize_device("cuda:0")
    actual = output.numpy().reshape(2, 3, 4)
    expected_gray = np.array([[127, 220, 76], [0, 255, 128]], dtype=np.int16)
    assert np.max(np.abs(actual[:, :, :3].astype(np.int16) - expected_gray[:, :, None])) <= 1
    assert np.all(actual[:, :, 3] == 255)


@pytest.mark.skipif(
    os.environ.get("OVRTX_SOURCE", "prebuilt") != "current",
    reason="Runtime textures require the matching current OVRTX/OVStage SDKs",
)
def test_carter_camera_monitor(output_dir):
    """Render a short circle; validate actual monitor sampling against the previous camera frame."""
    example = Path(__file__).resolve().parents[3] / "examples/python/runtime-textures/main.py"
    result = subprocess.run(
        [sys.executable, str(example), "--frames", "8", "--fps", "4", "--period", "2",
         "--check", "--png", str(output_dir / "carter.png")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600,
    )
    (output_dir / "carter-monitor-run.log").write_text(result.stdout)
    assert result.returncode == 0, result.stdout
    checks = json.loads((output_dir / "carter-monitor-checks.json").read_text())
    assert checks["frames"] == 8
    assert checks["kernel_max_error"] <= 1
    assert len(checks["monitor_correlations"]) == 7
    assert min(checks["monitor_correlations"]) >= 0.9
    with Image.open(output_dir / "carter.png") as image:
        assert image.size == (960, 720)
        assert np.asarray(image)[:, :, :3].std() > 5
    with Image.open(output_dir / "carter_monitor.png") as image:
        assert image.size == (320, 240)
