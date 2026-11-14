# Acoustic SignalWays Composite Tensor Example

This example populates an attached ovstage from `acoustic_example.usda`, renders
one acoustic (ultrasonic) `SignalWays` frame, maps the composite render variable to
CPU memory, and plots the echo envelopes in [rerun.io](https://rerun.io/).

> _"Create a Python sensor example that loads a scene containing a configured ultrasonic sensor facing a wall, warms up the sensor pipeline, renders one frame, reads the echo envelopes from the composite output, converts the strongest sample to a range, and optionally plots the envelopes."_

## Scene

The scene is Z-up and contains:

- an acoustic sensor at `(0, 0, 0.5)` oriented to fire along world +X
- an asphalt ground plane spanning `X=-50..50` and `Y=-50..50`
- a concrete wall whose near face stands at exactly `X = 3.0`

Both surfaces are bound to materials that carry only *nonvisual* attributes
(`omni:simready:nonvisual:*`). The acoustic return comes from those, not from a
visual shader, so the materials deliberately have no output terminals.

## Render Output

The acoustic model reports a per-signal-way echo envelope rather than per-point
returns, so the USD requests one composite render variable, `SignalWays`, instead
of one var per channel. It carries these channels:

- `Amplitudes`
- `TimeOffsetNs`
- `Flags`
- `TransmitterIds`, `ReceiverIds`, `ChannelIds`

The frame's extent arrives as composite *parameters* rather than as a channel,
which is the role `Counts` plays for a point cloud: `frameId`, `numSignalWays`,
`numSamplesPerSignalWay`, `numElements`, `cycleIndex`, `centerFrequencyHz` and
`sampleDurationUs`.

The executable maps the output to CPU, reshapes the per-sample channels to one
row per signal way, converts the strongest sample to a range, and prints the
median peak range and amplitude. Channel types and the full parameter contract
are documented in `docs/sensors/nonvisual/acoustic_wpm/outputs.rst`.

## Reading a Range

In basic mode, bin `index` covers round-trip times from
`(index + 1) * sampleDuration` up to `(index + 2) * sampleDuration`.
The example plots the lower range bound of each bin:

```text
range = (index + 1) * sampleDuration * speed_of_sound / 2
```

The example reads the sample duration from the published parameter rather than
hardcoding it.

## Renderer Config

Motion BVH is required, not preferred: the acoustic model runs the multi-tick
trace path, and every envelope comes back empty without it. The example enables
it via `RendererConfig` at renderer creation time:

```python
renderer = ovrtx.Renderer(ovrtx.RendererConfig(motion_bvh=ovrtx.MotionBvh.ENABLE))
```

The model also publishes nothing on its first frames, so the example takes three
warm-up steps before the one it reads.

## Running

From this directory:

```bash
uv run main.py
```

Write a rerun recording instead of spawning a viewer:

```bash
uv run main.py --rrd acoustic_envelope.rrd
```

Disable rerun and print only the frame summary:

```bash
uv run main.py --no-rr
```

Write a carb log file:

```bash
uv run main.py --no-rr --log
```

By default, `--log` writes to `_output/acoustic_example.log` from `OUTPUT_DIR`.
You can also pass a custom path:

```bash
uv run main.py --no-rr --log /tmp/acoustic_example.log
```

The log reports the number of signal ways and responding ways, the median peak
range and the median peak amplitude. Amplitudes vary with detector noise. Peak
ranges are envelope-bin lower bounds, not exact target distances; see the range
conversion above.
