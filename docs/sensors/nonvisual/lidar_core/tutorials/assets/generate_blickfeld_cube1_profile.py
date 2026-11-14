#!/usr/bin/env python3
"""Generate the documentation-derived Blickfeld Cube 1 analytic profile."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Callable, Iterable, Sequence

HORIZONTAL_FOV_DEG = 70.0
VERTICAL_FOV_DEG = 30.0
NUM_LINES = 50
HORIZONTAL_SPACING_DEG = 0.6
RAYS_PER_LINE = 117
FRAME_RATE_NUMERATOR = 10
FRAME_RATE_DENOMINATOR = 1
FRAME_DURATION_S = FRAME_RATE_DENOMINATOR / FRAME_RATE_NUMERATOR
MIRROR_FREQUENCY_HZ = NUM_LINES / (2.0 * FRAME_DURATION_S)

DEFAULT_OUTPUT = Path(__file__).with_name("Blickfeld_Cube1_Analytic.usda")


def _ramp(time_s: float, frame_duration_s: float) -> float:
    """Return the exemplary 3:1 linear ramp published by Blickfeld."""
    if time_s <= 0.75 * frame_duration_s:
        return 4.0 * time_s / (3.0 * frame_duration_s)
    return 4.0 - 4.0 * time_s / frame_duration_s


def _round_ns(time_s: float) -> int:
    return int(math.floor(time_s * 1_000_000_000.0 + 0.5))


def build_schedule() -> dict[str, list[float] | list[int]]:
    """Build one chronological frame from the published mirror equations."""
    frame_duration_s = FRAME_DURATION_S
    angular_frequency = 2.0 * math.pi * MIRROR_FREQUENCY_HZ
    horizontal_amplitude = HORIZONTAL_FOV_DEG / 2.0
    vertical_amplitude = VERTICAL_FOV_DEG / 2.0

    # Center a 0.6-degree grid inside the nominal 70-degree horizontal FoV.
    # This avoids duplicate timestamps at the mirror turnarounds.
    grid_start = -0.5 * HORIZONTAL_SPACING_DEG * (RAYS_PER_LINE - 1)
    horizontal_grid = [grid_start + index * HORIZONTAL_SPACING_DEG for index in range(RAYS_PER_LINE)]

    azimuth_deg: list[float] = []
    elevation_deg: list[float] = []
    fire_time_ns: list[int] = []
    channel_id: list[int] = []
    range_id: list[int] = []
    bank: list[int] = []

    for line in range(NUM_LINES):
        # cos() moves from +amplitude to -amplitude on even half-periods
        # and reverses on odd half-periods.
        physical_horizontal_angles: Iterable[float]
        if line % 2 == 0:
            physical_horizontal_angles = reversed(horizontal_grid)
        else:
            physical_horizontal_angles = horizontal_grid

        half_period_sign = 1.0 if line % 2 == 0 else -1.0
        for physical_azimuth_deg in physical_horizontal_angles:
            phase_in_line = math.acos(half_period_sign * physical_azimuth_deg / horizontal_amplitude)
            phase = line * math.pi + phase_in_line
            time_s = phase / angular_frequency

            # Core solid-state azimuth is converted to 360 - authored azimuth.
            # Positive physical elevation is up; the published first line moves
            # downward, so negate its vertical mirror equation.
            authored_azimuth_deg = -physical_azimuth_deg
            authored_elevation_deg = -_ramp(time_s, frame_duration_s) * vertical_amplitude * math.sin(phase)

            azimuth_deg.append(authored_azimuth_deg)
            elevation_deg.append(authored_elevation_deg)
            fire_time_ns.append(_round_ns(time_s))
            channel_id.append(len(channel_id) + 1)
            range_id.append(0)
            bank.append(line)

    schedule: dict[str, list[float] | list[int]] = {
        "azimuth_deg": azimuth_deg,
        "elevation_deg": elevation_deg,
        "fire_time_ns": fire_time_ns,
        "channel_id": channel_id,
        "range_id": range_id,
        "bank": bank,
    }
    _validate_schedule(schedule)
    return schedule


def _validate_schedule(
    schedule: dict[str, list[float] | list[int]],
) -> None:
    emitter_count = NUM_LINES * RAYS_PER_LINE
    for name, values in schedule.items():
        if len(values) != emitter_count:
            raise ValueError(f"{name} has {len(values)} values, expected {emitter_count}")

    fire_times = schedule["fire_time_ns"]
    assert all(isinstance(value, int) for value in fire_times)
    if any(first >= second for first, second in zip(fire_times, fire_times[1:])):
        raise ValueError("fireTimeNs must be strictly increasing")

    frame_duration_ns = _round_ns(FRAME_DURATION_S)
    if fire_times[0] < 0 or fire_times[-1] >= frame_duration_ns:
        raise ValueError("fireTimeNs must remain inside one frame")

    if fire_times[0] != 68_090 or fire_times[-1] != 99_931_910:
        raise ValueError("unexpected schedule endpoints")

    # The recipe documents one channel ID per emitter slot, numbered from 1 in
    # array order. The model itself accepts any uint32 IDs whose distinct count
    # does not exceed numberOfChannels, which one ID per slot always satisfies.
    if schedule["channel_id"] != list(range(1, emitter_count + 1)):
        raise ValueError("channelId must number the emitter slots from 1, as the recipe documents")


def _format_float(value: float) -> str:
    if abs(value) < 0.5e-6:
        value = 0.0
    return f"{value:.6f}"


def _format_int(value: int) -> str:
    return str(value)


def _format_array(
    declaration: str,
    values: Sequence[float] | Sequence[int],
    formatter: Callable[[float | int], str],
    values_per_line: int,
) -> str:
    lines = [f"    {declaration} = ["]
    for start in range(0, len(values), values_per_line):
        chunk = values[start : start + values_per_line]
        suffix = "," if start + values_per_line < len(values) else ""
        lines.append("        " + ", ".join(formatter(value) for value in chunk) + suffix)
    lines.append("    ]")
    return "\n".join(lines)


def render_usda(schedule: dict[str, list[float] | list[int]]) -> str:
    emitter_count = NUM_LINES * RAYS_PER_LINE
    rays_per_line = [RAYS_PER_LINE] * NUM_LINES

    sections = [
        """#usda 1.0
(
    doc = \"\"\"Documentation-derived analytic Blickfeld Cube 1 profile.
The firing pattern is generated from the public scan-pattern equations, not
from a captured device frame or an undocumented factory preset.\"\"\"
    metersPerUnit = 1
    upAxis = "Z"
    defaultPrim = "Blickfeld_Cube1_Analytic"
)

def OmniLidar "Blickfeld_Cube1_Analytic" (
    doc = \"\"\"Blickfeld Cube 1 source-based analytic example.
It uses the datasheet's 70 x 30 degree, 50-scanline example, selects its
published minimum 10 Hz frame rate, applies 0.6 degree horizontal spacing,
and derives a 250 Hz mirror frequency. The firing pattern follows Blickfeld's
published exemplary continuous 3:1 linear ramp. Validate it against a captured
frame before treating it as a device-specific scan preset.\"\"\"
    prepend apiSchemas = ["OmniSensorGenericLidarCoreAPI"]
)
{
    string omni:sensor:modelName = "LidarCore"
    string omni:sensor:modelVersion = "0"
    string omni:sensor:modelVendor = "NVIDIA"
    string omni:sensor:marketName = "Blickfeld Cube 1"
    double2 omni:sensor:frameRate = (10, 1)

    token omni:sensor:Core:scanType = "SOLID_STATE"
    token omni:sensor:Core:rayType = "IDEALIZED"
    bool omni:sensor:Core:partialOutputs = false
    bool omni:sensor:Core:instantLidar = false

    # The datasheet calls 1.5-75 m a typical application range and separately
    # publishes a 250 m detection envelope. The generic model needs hard
    # near/far limits, so 1.5 m is an operational approximation.
    float omni:sensor:Core:nearRangeM = 1.5
    float omni:sensor:Core:farRangeM = 250.0
    # Published values are upper bounds under stated conditions. The generic
    # model parameters do not reproduce those conditions one-to-one.
    float omni:sensor:Core:rangeResolutionM = 0.01
    float omni:sensor:Core:rangeAccuracyM = 0.02
    # A conservative anchor for the conditional ">30 m at 10%" claim.
    float omni:sensor:Core:minReflectance = 0.10
    float omni:sensor:Core:minReflectionRangeM = 30.0

    float omni:sensor:Core:waveLengthNm = 905.0
    float omni:sensor:Core:divergenceHorDeg = 0.4
    float omni:sensor:Core:divergenceVerDeg = 0.4

    # No public radiometric transfer curve is available. These modes provide
    # generic normalized output and require calibration for intensity fidelity.
    token omni:sensor:Core:intensityProcessing = "NORMALIZATION"
    token omni:sensor:Core:intensityMappingType = "LINEAR"

    # Cube 1 publishes up to three returns. Its single-return behavior below
    # 5 m is not expressible through this global capacity.
    uint omni:sensor:Core:maxReturns = 3

    # The analytic profile assigns one channel ID to each emitter slot.
    # This is a modeling convention, not a claim about physical detectors.
    uint omni:sensor:Core:numberOfEmitters = 5850
    uint omni:sensor:Core:numberOfChannels = 5850
    uint omni:sensor:Core:numLines = 50""",
        _format_array(
            "uint[] omni:sensor:Core:numRaysPerLine",
            rays_per_line,
            _format_int,
            20,
        ),
        """    uint omni:sensor:Core:rangeCount = 1
    float[] omni:sensor:Core:rangesMinM = [1.5]
    float[] omni:sensor:Core:rangesMaxM = [250.0]
    uint omni:sensor:Core:stateResolutionStep = 1

    # Public sources do not provide a random angular-error distribution.
    float omni:sensor:Core:azimuthErrorMean = 0.0
    float omni:sensor:Core:azimuthErrorStd = 0.0
    float omni:sensor:Core:elevationErrorMean = 0.0
    float omni:sensor:Core:elevationErrorStd = 0.0

    # Each line samples the same centered -34.8..+34.8 degree grid.
    # Alternating array order follows the mirror in chronological order.""",
        _format_array(
            "float[] omni:sensor:Core:emitterState:s001:azimuthDeg",
            schedule["azimuth_deg"],
            _format_float,
            12,
        ),
        _format_array(
            "float[] omni:sensor:Core:emitterState:s001:elevationDeg",
            schedule["elevation_deg"],
            _format_float,
            12,
        ),
        _format_array(
            "uint[] omni:sensor:Core:emitterState:s001:fireTimeNs",
            schedule["fire_time_ns"],
            _format_int,
            12,
        ),
        """    # Authored channel IDs cover 1..numberOfChannels, one per emitter slot.
    # PointCloud ChannelId reports them unchanged: 1..5850.""",
        _format_array(
            "uint[] omni:sensor:Core:emitterState:s001:channelId",
            schedule["channel_id"],
            _format_int,
            24,
        ),
        _format_array(
            "uint[] omni:sensor:Core:emitterState:s001:rangeId",
            schedule["range_id"],
            _format_int,
            24,
        ),
        _format_array(
            "uint[] omni:sensor:Core:emitterState:s001:bank",
            schedule["bank"],
            _format_int,
            24,
        ),
        """    def RenderProduct "RenderedOutputs"
    {
        uniform int2 resolution = (1280, 720)
        rel camera = <../../Blickfeld_Cube1_Analytic>
        rel orderedVars = [
            <SupportedOutputs/PointCloud>
        ]

        def Scope "SupportedOutputs"
        {
            def RenderVar "PointCloud"
            {
                string sourceName = "PointCloud"
                token[] channels = ["Coordinates", "Intensity", "TimeOffsetNs", "EmitterId", "ChannelId", "EchoId"]
            }
        }
    }
}""",
    ]
    result = "\n".join(sections) + "\n"
    if f"uint omni:sensor:Core:numberOfEmitters = {emitter_count}" not in result:
        raise ValueError("rendered emitter count does not match schedule")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output USDA path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    schedule = build_schedule()
    args.output.write_text(render_usda(schedule), encoding="utf-8")

    fire_times = schedule["fire_time_ns"]
    elevations = schedule["elevation_deg"]
    print(f"Wrote {args.output}")
    print(f"Emitters: {len(fire_times)}")
    print(f"Fire-time range: {fire_times[0]}..{fire_times[-1]} ns")
    print(f"Sampled elevation range: {min(elevations):.6f}..{max(elevations):.6f} deg")


if __name__ == "__main__":
    main()
