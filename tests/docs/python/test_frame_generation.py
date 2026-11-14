# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for DLSS Frame Generation output frame semantics.

The unscheduled camera used here completes one capture per step. With frame
generation active, that capture returns N interpolated frames followed by its
simulated frame. These count-based recipes do not apply to scheduled cameras
that complete several captures per step.

Hardware-gated. Frame generation needs an Ada (RTX 40-series) or newer GPU that is
driving a display, so these tests skip rather than fail everywhere else. There is
no public capability query -- stepping and looking at the frame count IS the
supported way to find out, which is what ``_frame_generation_active`` does.
"""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest

OUTPUT_DIR = Path(__file__).parent / "_output"
RENDER_PRODUCT_PATH = "/Render/Camera"
LDR_COLOR_PATH = "/Render/Camera/LdrColor"

# Frame generation interpolates between the previous and current rendered frame, so
# the first step has no history to work with. Warm up before reading the count.
WARMUP_STEPS = 3
DELTA_TIME = 1.0 / 60.0

# Ada tops out at 1 interpolated frame; Blackwell reaches 3. Requesting more than
# the hardware supports is clamped, not an error, so this asks for the maximum and
# accepts whatever comes back.
REQUESTED_INTERPOLATED_FRAMES = 3

USDA = """#usda 1.0
(
    subLayers = [
        @https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda@
    ]
)

def Scope "Render" {
    def RenderProduct "Camera" {
        # Frame generation requires RealTimePathTracing, a render resolution of at
        # least 126 pixels per side, and LdrColor (or HdrColor) as the ONLY render
        # output. Any additional AOV counts as an incompatible render output and
        # silently disables frame generation for the view.
        int2 resolution = (640, 480)
        rel camera = </World/Camera>
        rel orderedVars = [<LdrColor>]
        token omni:rtx:rendermode = "RealTimePathTracing"

        # Enable frame generation and request an interpolated frame count. A count
        # of 0 or unset requests one frame; explicit larger values are clamped to
        # the hardware maximum (1 on Ada, 3 on Blackwell).
        #
        bool omni:rtx:dlss:frameGeneration = 1
        int omni:rtx:dlss:frameGenerationInterpolatedFrameCount = 3

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
    }
}
"""


def _build_stage(stage, usda=USDA):
    """Populate the attached stage and return the ordinal to step with."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, usda, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    return ordinal


def _step(renderer, ordinal):
    return renderer.step(
        render_products={RENDER_PRODUCT_PATH},
        delta_time=DELTA_TIME,
        ordinal=ordinal,
    )


# [snippet:doc-frame-generation-detect]
def _frame_generation_active(products):
    """Detect interpolation when exactly one camera capture completes per step.

    All returned frames must belong to that capture, as with the unscheduled
    camera in this example. A scheduled
    camera can return several simulated captures without interpolation, so total
    frame count cannot detect frame generation for a multi-capture step.

    There is no public frame-generation capability query. The renderer can decline --
    unsupported GPU, non-display device, incompatible render outputs, resolution
    too small -- and the step still succeeds, returning a single simulated frame. The
    frame count is the signal: more than one frame means interpolation happened.
    """
    product = products["/Render/Camera"]
    return len(product.frames) > 1
# [/snippet:doc-frame-generation-detect]


def _warm_up(renderer, ordinal):
    """Step past the history reset and return the last step's products."""
    products = None
    for _ in range(WARMUP_STEPS):
        products = _step(renderer, ordinal)
    return products


def test_frame_generation_emits_interpolated_frames(renderer, stage):
    """One unscheduled camera capture returns N interpolated frames plus its simulated frame."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ordinal = _build_stage(stage)

    products = _warm_up(renderer, ordinal)
    assert products[RENDER_PRODUCT_PATH].frames, "Expected at least the simulated frame"
    if not _frame_generation_active(products):
        pytest.skip(
            "DLSS Frame Generation did not engage on this system. It requires an "
            "Ada (RTX 40-series) or newer GPU that is driving a display."
        )

    # [snippet:doc-frame-generation-read-frames]
    product = products["/Render/Camera"]

    # All returned frames must belong to one completed capture, as with this
    # unscheduled camera. Multiple scheduled captures invalidate this classification.
    # Derive the interpolated count from the result; never hardcode it. The count is
    # clamped to the hardware maximum and can change at runtime, so a step may
    # return fewer interpolated frames than were requested.
    interpolated_count = len(product.frames) - 1

    # The simulated frame is LAST. The frames before it are interpolated, in
    # presentation order. Nothing on a frame marks it as interpolated -- position in
    # the list is the only signal.
    interpolated_frames = product.frames[:-1]
    simulated_frame = product.frames[-1]
    # [/snippet:doc-frame-generation-read-frames]

    assert 1 <= interpolated_count <= REQUESTED_INTERPOLATED_FRAMES
    assert len(interpolated_frames) == interpolated_count

    # Every frame exposes the same single render var.
    for index, frame in enumerate(product.frames):
        assert list(frame.render_vars) == [LDR_COLOR_PATH], (
            f"frame {index} render vars: {list(frame.render_vars)}"
        )

    # Each frame maps to a well-formed image of the authored resolution.
    for index, frame in enumerate(product.frames):
        var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
        view = np.from_dlpack(var)
        assert view.ndim == 3, f"frame {index} ndim: {view.ndim}"
        assert view.shape[0] == 480, f"frame {index} height: {view.shape[0]}"
        assert view.shape[1] == 640, f"frame {index} width: {view.shape[1]}"
        assert view.shape[2] >= 3, f"frame {index} channels: {view.shape[2]}"
        del view
        del var

    assert simulated_frame is product.frames[-1]


def test_frame_generation_frame_times_are_ordered(renderer, stage):
    """Frames are placed at strictly increasing instants, simulated frame last."""
    ordinal = _build_stage(stage)

    products = _warm_up(renderer, ordinal)
    assert products[RENDER_PRODUCT_PATH].frames, "Expected at least the simulated frame"
    if not _frame_generation_active(products):
        pytest.skip("DLSS Frame Generation did not engage on this system.")

    frames = products[RENDER_PRODUCT_PATH].frames

    # Interpolated frames sit temporally between the previous simulated frame and this
    # step's simulated frame, so the whole set is strictly increasing in time. These
    # timestamps are the input any presentation-pacing scheme needs.
    # [snippet:doc-frame-generation-read-times]
    times = [frame.end_time for frame in frames]
    # [/snippet:doc-frame-generation-read-times]
    assert times == sorted(times), times
    assert len(set(times)) == len(times), f"duplicate frame times: {times}"


def test_frame_generation_disabled_returns_single_frame(renderer, stage):
    """With frame generation off, this unscheduled camera returns one frame per step.

    This is also the shape a step returns when the renderer DECLINES frame
    generation, which is why the count alone cannot distinguish "off" from
    "unsupported".
    """
    usda = USDA.replace(
        "bool omni:rtx:dlss:frameGeneration = 1",
        "bool omni:rtx:dlss:frameGeneration = 0",
    )
    ordinal = _build_stage(stage, usda=usda)

    products = _warm_up(renderer, ordinal)

    product = products[RENDER_PRODUCT_PATH]
    assert len(product.frames) == 1, (
        f"expected a single frame with frame generation disabled, got {len(product.frames)}"
    )
    assert list(product.frames[0].render_vars) == [LDR_COLOR_PATH]
