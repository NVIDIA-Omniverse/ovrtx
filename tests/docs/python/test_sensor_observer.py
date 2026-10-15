# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Keep a scheduled camera active during interactive, zero-time observer updates."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest
from PIL import Image


@pytest.mark.parametrize("observer_updates", [0, 1, 2])
def test_observer_updates_preserve_sensor_cadence(
    renderer, stage, output_dir, observer_updates
):
    scene = Path(__file__).parents[3] / "examples/c/sensor-observer/conveyor.usda"
    ordinal = 1
    ovstage.population.open_usd(stage, str(scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    captures = []
    observer_images = []
    cube_centers = []
    sensor_sequence = output_dir / f"observer-sensor-{observer_updates}"
    observer_sequence = output_dir / f"observer-views-{observer_updates}"
    sensor_sequence.mkdir(exist_ok=True)
    observer_sequence.mkdir(exist_ok=True)
    with ovstage.PathDictionary(stage) as dictionary:
        sensor_paths = dictionary.create_path_list_from_strings(["/World/Sensor"])
        observer_paths = dictionary.create_path_list_from_strings(["/World/Observer"])
        object_paths = dictionary.create_path_list_from_strings(
            ["/World/Cube/Cube", "/World/Sphere/Sphere", "/World/Cone/Cone"]
        )
        with stage.query_from_path_list(
            sensor_paths
        ) as sensor, stage.query_from_path_list(
            observer_paths
        ) as observer, stage.query_from_path_list(
            object_paths
        ) as objects:
            # [snippet:doc-observer-output-policy-python]
            # Request only completed inspection images before the first step.
            ordinal += 1
            stage.write_attribute(
                sensor,
                "omni:sensor:Core:partialOutputs",
                ordinal=ordinal,
                tensors=np.array([False]),
                is_array=False,
            ).wait()
            stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
            # [/snippet:doc-observer-output-policy-python]

            for step_index in range(1, 31):
                # Move the meshes relative to their fixed placement prims.
                # Only simulation steps change object poses, independently of UI updates.
                ordinal += 1
                transforms = np.tile(np.eye(4, dtype=np.float64), (3, 1, 1))
                placement_x = np.array([-300, 0, 300])
                transforms[:, 3, 0] = (
                    placement_x + (step_index / 30) * 180 + 450
                ) % 900 - 450 - placement_x
                transforms[:, 3, 1] = 50
                stage.write_attribute(
                    objects,
                    "omni:xform",
                    ordinal=ordinal,
                    tensors=transforms.reshape(3, 16),
                    is_array=False,
                    semantic=ovstage.AttributeSemantic.MATRIX,
                ).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                # [snippet:doc-observer-simulation-step-python]
                # Step simulation at 30 Hz and keep both products active.
                # The sensor follows its authored 30 Hz capture rate.
                products = renderer.step(
                    render_products={"/Render/Sensor", "/Render/Observer"},
                    delta_time=1 / 30,
                    ordinal=ordinal,
                )
                # [/snippet:doc-observer-simulation-step-python]
                assert products.simulation_end_time == pytest.approx(step_index / 30)
                sensor_product = (
                    products["/Render/Sensor"] if "/Render/Sensor" in products else None
                )
                for frame in sensor_product.frames if sensor_product else []:
                    captures.append((step_index, frame.start_time, frame.end_time))
                    # Retain the whole sequence for temporal image-quality review.
                    with frame.render_vars["/Render/Sensor/LdrColor"].map(
                        device=ovrtx.Device.CPU
                    ) as mapped:
                        pixels = np.from_dlpack(mapped)[..., :3].copy()
                    # Advancing timestamps must also produce the current scene pose.
                    # The orange cube moves right throughout this one-second run.
                    rgb = pixels.astype(np.int16)
                    cube = (rgb[..., 0] - rgb[..., 1] > 40) & (
                        rgb[..., 0] - rgb[..., 2] > 80
                    )
                    _, cube_x = np.nonzero(cube)
                    assert cube_x.size > 100, "The moving cube must remain visible"
                    cube_centers.append(float(cube_x.mean()))
                    sensor_image = Image.fromarray(pixels)
                    sensor_image.save(sensor_sequence / f"{step_index:02d}.png")
                    if step_index == 30:
                        sensor_image.save(
                            output_dir / f"observer-sensor-{observer_updates}.png"
                        )
                del products

                # Include a longer paused interval in the middle of the run.
                update_count = observer_updates + (
                    6 if observer_updates and step_index == 15 else 0
                )
                for update_index in range(update_count):
                    # [snippet:doc-observer-view-step-python]
                    # Publishing a camera edit advances the ordinal, not simulation time.
                    ordinal += 1
                    transform = np.eye(4, dtype=np.float64)
                    angle = np.deg2rad(-28)
                    transform[1:3, 1:3] = [
                        [np.cos(angle), np.sin(angle)],
                        [-np.sin(angle), np.cos(angle)],
                    ]
                    transform[3, :3] = (100 * (update_index % 2), 700, 1200)
                    stage.write_attribute(
                        observer,
                        "omni:xform",
                        ordinal=ordinal,
                        tensors=transform.reshape(1, 16),
                        is_array=False,
                        semantic=ovstage.AttributeSemantic.MATRIX,
                    ).wait()
                    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                    products = renderer.step(
                        render_products={"/Render/Sensor", "/Render/Observer"},
                        delta_time=0,
                        ordinal=ordinal,
                    )
                    # [/snippet:doc-observer-view-step-python]
                    assert products.simulation_start_time == pytest.approx(
                        step_index / 30
                    )
                    assert products.simulation_end_time == pytest.approx(
                        step_index / 30
                    )
                    assert (
                        "/Render/Sensor" not in products
                        or not products["/Render/Sensor"].frames
                    )
                    frames = products["/Render/Observer"].frames
                    assert len(frames) == 1
                    assert frames[0].start_time == pytest.approx(step_index / 30)
                    with frames[0].render_vars["/Render/Observer/LdrColor"].map(
                        device=ovrtx.Device.CPU
                    ) as mapped:
                        image = np.from_dlpack(mapped)[..., :3].copy()
                    Image.fromarray(image).save(
                        observer_sequence / f"{step_index:02d}-{update_index:02d}.png"
                    )
                    if step_index == 15 and update_index < 2:
                        observer_images.append(image)
                        Image.fromarray(image).save(
                            output_dir / f"observer-paused-{update_index}.png"
                        )
                    del products
        for paths in (sensor_paths, observer_paths, object_paths):
            dictionary.destroy_path_list(paths)

    assert len(captures) == 30
    np.testing.assert_array_equal([row[0] for row in captures], np.arange(1, 31))
    np.testing.assert_allclose(
        [row[1] for row in captures], np.arange(1, 31) / 30, atol=1e-6
    )
    np.testing.assert_allclose(
        [row[2] for row in captures], np.arange(1, 31) / 30, atol=1e-6
    )
    assert np.all(np.diff(cube_centers) > 1), (
        "The cube must move in every completed inspection image", cube_centers
    )
    if observer_updates:
        assert (
            np.mean(np.abs(observer_images[0].astype(float) - observer_images[1])) > 1
        )
