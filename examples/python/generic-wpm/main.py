# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import argparse
from pathlib import Path

import numpy as np

import ovrtx
import ovstage


def capture(renderer, *, ordinal=1, steps=10):
    """Warm up the pipelines and return an independent copy of one capture."""
    # [snippet:doc-generic-wpm-step]
    for _ in range(steps):
        products = renderer.step(render_products={"/Render/GenericWpm"}, delta_time=0.1, ordinal=ordinal)
    frame = products["/Render/GenericWpm"].frames[0]
    # [/snippet:doc-generic-wpm-step]
    # [snippet:doc-generic-wpm-copy-contributions]
    import numpy as np
    import ovrtx

    with frame.render_vars["/Render/GenericWpm/Contributions"].map(device=ovrtx.Device.CPU) as output:
        # Copy inside the mapping: the returned arrays own their memory.
        tensors = {name: np.from_dlpack(output[name]).copy() for name in output}
        params = {name: np.from_dlpack(output.params[name]).copy() for name in output.params}
    # [/snippet:doc-generic-wpm-copy-contributions]
    return tensors, params


def select_patterns(stage, ordinal, tx, rx, page):
    """Publish one coordinated selector update before the next renderer step."""
    # [snippet:doc-generic-wpm-select-patterns]
    import numpy as np
    import ovstage

    with ovstage.PathDictionary(stage) as paths:
        prims = paths.create_path_list_from_strings(["/World/Sensor"])
        try:
            with stage.query_from_path_list(prims) as query:
                for name, value in (
                    ("activeTxPatternIndex", tx),
                    ("activeRxPatternIndex", rx),
                    ("activeMappingPageIndex", page),
                ):
                    stage.write_attribute(
                        query,
                        paths.intern_token("omni:sensor:GenericWpm:" + name),
                        ordinal=ordinal,
                        tensors=np.array([value], dtype=np.uint32),
                        is_array=False,
                    ).wait()
        finally:
            paths.destroy_path_list(prims)
    # Seal only after all three writes; do not step the renderer between them.
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:doc-generic-wpm-select-patterns]


def live_edits(renderer, stage):
    """Exercise the mixed recipe's accepted, rejected and recovered selections."""
    for ordinal, (requested, expected, slots) in enumerate(
        (
            ((0, 0, 0), (0, 0, 0), 2),
            ((1, 1, 1), (1, 1, 1), 6),
            ((2, 1, 1), (2, 1, 1), 18),
            ((0, 1, 0), (2, 1, 1), 18),  # Page 0 has Rx ID 2; Rx pattern 1 has only two receivers.
            ((0, 0, 0), (0, 0, 0), 2),
        ),
        start=2,
    ):
        select_patterns(stage, ordinal, *requested)
        tensors, params = capture(renderer, ordinal=ordinal, steps=10 if ordinal == 2 else 3)
        accepted = tuple(
            int(params[name].item())
            for name in ("activeTxPatternIndex", "activeRxPatternIndex", "activeMappingPageIndex")
        )
        if accepted != expected or tensors["Valid"].size != slots or not tensors["Valid"].all():
            raise RuntimeError(f"Unexpected state after selector edit {requested}: accepted={accepted}")
        print(f"requested={requested}, accepted={accepted}, slots={slots}")
    return tensors, params


def save_range_grid(path, tensors):
    """Show the 3x5 direct-return recipe as labelled range cells, not camera pixels."""
    from PIL import Image, ImageDraw, ImageFont

    valid = tensors["Valid"].reshape(3, 5) != 0
    ranges = tensors["RoundTripDistanceM"].reshape(3, 5) / 2
    image = Image.new("RGB", (750, 350), "#17202b")
    draw = ImageDraw.Draw(image)
    font_path = Path(__file__).resolve().parents[3] / "tests/docs/data/fonts/DejaVuSans-Bold.ttf"
    title_font = ImageFont.truetype(str(font_path), 16)
    value_font = ImageFont.truetype(str(font_path), 20)
    draw.text((20, 15), "Direct range (m) | rows: Z/elevation | columns: Y/azimuth", fill="white", font=title_font)
    for row, col in np.ndindex(3, 5):
        x, y = col * 150, 50 + row * 100
        value = ranges[row, col]
        fraction = float(np.clip((value - 11) / 3, 0, 1)) if valid[row, col] else 0
        color = (int(35 + 160 * fraction), 90, int(190 - 100 * fraction)) if valid[row, col] else (50, 50, 50)
        draw.rectangle((x + 3, y + 3, x + 146, y + 96), fill=color)
        draw.text((x + 35, y + 40), f"{value:.3f}" if valid[row, col] else "miss", fill="white", font=value_font)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main(argv=None):
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Run a small Generic WPM configuration")
    parser.add_argument(
        "--recipe",
        default="depth",
        choices=(
            "depth",
            "planar",
            "cylindrical",
            "lidar",
            "gaussian",
            "gaussian_bloom",
            "multistatic",
            "multistatic_map",
            "acoustic",
            "mixed",
        ),
    )
    parser.add_argument("--no-rr", action="store_true", help="Do not open the Rerun viewer")
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording instead of opening a viewer")
    parser.add_argument("--png", type=Path, help="Save a labelled range grid (depth, planar or cylindrical only)")
    parser.add_argument("--output", type=Path, help="Save raw channels and CPU parameters to an NPZ file")
    parser.add_argument("--live-edits", action="store_true", help="Switch, reject and recover selections (mixed only)")
    args = parser.parse_args(argv)
    if args.no_rr and args.rrd:
        parser.error("--rrd cannot be combined with --no-rr")
    if args.png and args.recipe not in ("depth", "planar", "cylindrical"):
        parser.error("--png requires a depth, planar or cylindrical recipe")
    if args.live_edits and args.recipe != "mixed":
        parser.error("--live-edits requires --recipe mixed")

    destination = args.output or here / "_output" / f"{args.recipe}.npz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            motion_bvh=ovrtx.MotionBvh.ENABLE,
            log_file_path=str(destination.with_suffix(".log")),
        )
    )
    stage = ovstage.Stage("ovrtx.example.generic-wpm")
    renderer.attach_ovstage(stage)
    try:
        # [snippet:doc-generic-wpm-load-recipe]
        # Compose a complete sensor configuration with the shared steel enclosure.
        recipe = here.parents[2] / "tests/docs/usd/data" / f"generic_wpm_{args.recipe}.usda"
        scene = here / "scene.usda"
        root_layer = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 10
    subLayers = [@{recipe.as_posix()}@, @{scene.as_posix()}@]
)
"""
        ovstage.population.open_usd_from_string(stage, root_layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        # [/snippet:doc-generic-wpm-load-recipe]
        tensors, params = live_edits(renderer, stage) if args.live_edits else capture(renderer)
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()

    # [snippet:doc-generic-wpm-read-output]
    import numpy as np

    # These are owned copies from capture(), not borrowed GPU or mapped CPU data.
    shape = tuple(int(params[name].item()) for name in ("numTiles", "numTx", "raysPerTx", "maxBounces", "groupSize"))
    valid = tensors["Valid"].reshape(shape) != 0
    # Keep logical slot coordinates before compacting the valid payloads.
    slot_indices = np.argwhere(valid)
    hit_samples = tensors["HitPosWorld"].reshape(*shape, 3)[valid]
    path_lengths = tensors["RoundTripDistanceM"].reshape(shape)[valid]
    # [/snippet:doc-generic-wpm-read-output]
    if not np.any(valid):
        raise RuntimeError("The configuration produced no valid contributions; inspect the renderer log")
    np.savez(destination, **tensors, **{f"param_{name}": value for name, value in params.items()})
    print(f"{args.recipe}: shape={shape}, valid={np.count_nonzero(valid)}/{valid.size}; saved {destination}")
    print(f"first valid slot={tuple(slot_indices[0])}, path length={path_lengths[0]:.6f} m")
    if args.png:
        save_range_grid(args.png, tensors)
    if not args.no_rr:
        import rerun as rr

        rr.init("ovrtx_generic_wpm", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
        # These are visualized hit samples derived from contributions, not a detector point cloud.
        rr.log("world/hits", rr.Points3D(hit_samples, radii=0.08))
        rr.log("world/sensor", rr.Arrows3D(origins=[[0, 0, 0]], vectors=[[2, 0, 0]]))
        rr.disconnect()


if __name__ == "__main__":
    main()
