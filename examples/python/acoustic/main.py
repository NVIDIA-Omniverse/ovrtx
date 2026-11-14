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

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "acoustic_example.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/World/Render/Products/AcousticProduct"
SIGNAL_WAYS_RENDER_VAR = "/World/Render/Vars/SignalWays"
WARMUP_STEPS = 3
STEP_DT_SECONDS = 0.1


# [snippet:read-acoustic-signal-ways]
def read_acoustic_signal_ways(frame) -> dict:
    """Map the SignalWays composite tensor to CPU and return one frame of echoes."""
    with frame.render_vars[SIGNAL_WAYS_RENDER_VAR].map(device=ovrtx.Device.CPU) as signal_ways:

        def param(name: str) -> float:
            return float(np.from_dlpack(signal_ways.params[name])[0])

        num_signal_ways = int(param("numSignalWays"))
        num_samples = int(param("numSamplesPerSignalWay"))

        if num_signal_ways == 0 or num_samples == 0:
            return {"num_signal_ways": 0, "num_samples": 0}

        num_elements = num_signal_ways * num_samples

        def channel(name: str) -> np.ndarray:
            return np.from_dlpack(signal_ways[name])[:num_elements]

        return {
            "num_signal_ways": num_signal_ways,
            "num_samples": num_samples,
            "sample_duration_s": param("sampleDurationUs") * 1.0e-6,
            "center_frequency_hz": param("centerFrequencyHz"),
            "cycle_index": int(param("cycleIndex")),
            "envelopes": channel("Amplitudes").reshape(num_signal_ways, num_samples).copy(),
            # The identifier channels carry one entry per signal way rather than one per
            # element, so only the first num_signal_ways entries are meaningful.
            "transmitter_ids": channel("TransmitterIds")[:num_signal_ways].astype(int),
            "receiver_ids": channel("ReceiverIds")[:num_signal_ways].astype(int),
            "channel_ids": channel("ChannelIds")[:num_signal_ways].astype(int),
        }


# [/snippet:read-acoustic-signal-ways]


# [snippet:acoustic-sample-index-to-range]
import numpy as np


def sample_ranges_m(frame_data: dict) -> np.ndarray:
    """Return the lower range bound, in meters, of each envelope bin."""
    sample_index = np.arange(frame_data["num_samples"], dtype=np.float64)
    # Bin s holds round-trip times [(s + 1) dt, (s + 2) dt).
    return (sample_index + 1) * frame_data["sample_duration_s"] * 343.21 / 2.0


# [/snippet:acoustic-sample-index-to-range]


# [snippet:log-acoustic-signal-ways]
def log_acoustic_signal_ways(rr, frame_data: dict) -> None:
    """Log the frame to rerun: one amplitude-over-range curve per signal way."""
    ranges_m = sample_ranges_m(frame_data)

    for sgw in range(frame_data["num_signal_ways"]):
        envelope = frame_data["envelopes"][sgw]
        if not np.any(envelope):
            continue

        tx = frame_data["transmitter_ids"][sgw]
        rx = frame_data["receiver_ids"][sgw]

        rr.log(
            f"acoustic/envelope/tx{tx}_rx{rx}",
            rr.LineStrips2D([np.column_stack((ranges_m, envelope))], colors=[[80, 180, 255]]),
        )

        peak = int(np.argmax(envelope))
        # The peak echo placed along the sensor boresight (world +X).
        rr.log(
            f"acoustic/peak_point/tx{tx}_rx{rx}",
            rr.Points3D([[float(ranges_m[peak]), 0.0, 0.5]], colors=[[255, 200, 0]], radii=0.08),
        )


# [/snippet:log-acoustic-signal-ways]


def main(argv: list[str] | None = None) -> None:
    # [snippet:parse-acoustic-cli-args]
    parser = argparse.ArgumentParser(
        description="Acoustic SignalWays ovrtx example with rerun visualization"
    )
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    parser.add_argument("--no-rr", action="store_true", help="Disable rerun visualization")
    parser.add_argument(
        "--rrd",
        type=Path,
        default=None,
        help="Write a rerun .rrd recording instead of spawning",
    )
    parser.add_argument(
        "--log",
        nargs="?",
        type=Path,
        const=OUTPUT_DIR / "acoustic_example.log",
        default=None,
        metavar="PATH",
        help="Write a carb log file (default: _output/acoustic_example.log)",
    )
    args = parser.parse_args(argv)
    # [/snippet:parse-acoustic-cli-args]

    # [snippet:initialize-rerun]
    # Rerun is optional: the same example can run headless with --no-rr.
    rr = None
    if not args.no_rr:
        import rerun as rr

        rr.init("ovrtx_acoustic", spawn=args.rrd is None)
        if args.rrd is not None:
            rr.save(str(args.rrd))
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    # [/snippet:initialize-rerun]

    # [snippet:create-renderer]
    # Enable motion BVH: the acoustic model runs the multi-tick trace path, and
    # every envelope comes back empty without it.
    log_file_path = None
    if args.log is not None:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = str(args.log)
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            log_file_path=log_file_path,
            log_level="info",
            motion_bvh=ovrtx.MotionBvh.ENABLE,
        )
    )
    stage = ovstage.Stage("ovrtx.example.acoustic")
    renderer.attach_ovstage(stage)
    # [/snippet:create-renderer]

    # [snippet:load-acoustic-scene]
    # The USDA scene defines the sensor, the nonvisual materials it returns from,
    # the render product, and a concrete wall 3.0 m along the sensor boresight.
    print(f"Loading acoustic scene from {args.scene}...")
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:load-acoustic-scene]

    # [snippet:warm-up-acoustic]
    # Warm up the sensor before reading an envelope: the model publishes nothing
    # on its first frame.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS, ordinal=ordinal)
    # [/snippet:warm-up-acoustic]

    # [snippet:step-and-visualize-acoustic]
    # Render one acoustic frame and report the strongest echo, which locates the
    # wall the scene places 3.0 m ahead of the sensor.
    products = renderer.step(
        render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS, ordinal=ordinal
    )
    frame = products[RENDER_PRODUCT].frames[0]
    frame_data = read_acoustic_signal_ways(frame)

    if frame_data["num_signal_ways"] == 0:
        print("no signal ways reported")
    else:
        ranges_m = sample_ranges_m(frame_data)
        peaks = frame_data["envelopes"].max(axis=1)
        responding = peaks > 0.0
        peak_sample = np.argmax(frame_data["envelopes"][responding], axis=1)
        print(
            f"signal ways={frame_data['num_signal_ways']}, "
            f"responding={int(np.count_nonzero(responding))}, "
            f"median peak range={float(np.median(ranges_m[peak_sample])):.3f} m, "
            f"median peak amplitude={float(np.median(peaks[responding])):.4g}"
        )
        if rr is not None:
            log_acoustic_signal_ways(rr, frame_data)
    # [/snippet:step-and-visualize-acoustic]

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
