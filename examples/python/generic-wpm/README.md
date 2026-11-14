# Generic WPM configurations

Run small depth, scan, beam, multistatic, acoustic and stored-pattern recipes.
The example saves raw contributions to NPZ and optionally displays derived hit
samples in Rerun. These samples are not detector-generated points.

The sensor is at the centre of a steel enclosure. The X/Z walls are 11 m from
the origin; the Y walls are 12 m away.
`scene.usda` reuses the documentation cube mesh. No visual lighting is needed.
Configurations live in [`tests/docs/usd/data`](../../../tests/docs/usd/data/)
and have tested `usd-core` Python equivalents in
[`test_generic_wpm_usda.py`](../../../tests/docs/usd/test_generic_wpm_usda.py).
See the [Generic WPM guide](../../../docs/sensors/nonvisual/generic_wpm/index.rst) for the inputs.

## Run

Requires Python 3.10–3.14, an RTX GPU and a supported driver.


From this directory:

```bash
uv run main.py --recipe depth
uv run main.py --recipe lidar --rrd _output/lidar.rrd
uv run main.py --recipe acoustic --no-rr --output _output/acoustic.npz
uv run main.py --recipe mixed --live-edits --no-rr
```

`--recipe` accepts `depth`, `planar`, `cylindrical`, `lidar`, `gaussian`,
`gaussian_bloom`, `multistatic`, `multistatic_map`, `acoustic`, or `mixed`.
`--png PATH` saves a labelled 3×5 range grid for the first three recipes.
`--rrd PATH` saves a headless recording; do not combine it with `--no-rr`.
`--live-edits` runs the mixed recipe's selector transitions and saves the final
recovered capture. Without it, `mixed` renders only the initial selection.
The first run may spend several minutes compiling shaders.

## Configuration and output

The depth recipe pairs matching angular Tx/Rx grids and reuses one identity ray
at every transmitter. Its complete composed configuration is
[`generic_wpm_depth.usda`](../../../tests/docs/usd/data/generic_wpm_depth.usda),
including the shared base layer. The guide explains the USDA configuration and
why its geometry, ray bundle and receiver mapping were chosen.

For example, this complete override layer adds a one-cell receiver neighborhood
to the Gaussian recipe. It is the marked snippet from
[`generic_wpm_gaussian_bloom.usda`](../../../tests/docs/usd/data/generic_wpm_gaussian_bloom.usda):

```usda
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 10
    subLayers = [@generic_wpm_gaussian.usda@]
)

over "World"
{
    over "Sensor"
    {
        # Radius one allocates nine receiver slots per ray; edge slots can be invalid.
        uint[] omni:sensor:GenericWpm:tx:mappingBloomFactors = [1]
    }
}
```

This increases capacity from 135 to 1,215 slots without increasing the ray count.
The full USDA recipe is in the guide.

A successful depth run prints `shape=(1, 15, 1, 1, 1), valid=15/15`.
The centre cell has 11 m range; off-axis ranges are longer. The NPZ contains
channel names as keys and CPU parameters under `param_`-prefixed keys. Filter
every payload by `Valid != 0`; unused slots are not meaningful. Range is half
`RoundTripDistanceM` only for a direct return with co-located ray-emission and
receiver origins, as in these three grid recipes.

The consumer reconstructs logical slot coordinates from accepted CPU metadata,
then compacts only valid records. This excerpt is `doc-generic-wpm-read-output`
from `main.py`:

```python
import numpy as np

# These are owned copies from capture(), not borrowed GPU or mapped CPU data.
shape = tuple(int(params[name].item()) for name in ("numTiles", "numTx", "raysPerTx", "maxBounces", "groupSize"))
valid = tensors["Valid"].reshape(shape) != 0
# Keep logical slot coordinates before compacting the valid payloads.
slot_indices = np.argwhere(valid)
hit_samples = tensors["HitPosWorld"].reshape(*shape, 3)[valid]
path_lengths = tensors["RoundTripDistanceM"].reshape(shape)[valid]
```

`capture()` maps to CPU and copies the named tensors and parameters before
leaving the mapping. These copies remain usable after renderer destruction.
The example's world positions use its origin-centred, metre-unit scene; prefer
the explicitly metre-valued sensor/receiver channels when interpreting other
scene coordinate systems.

With `--live-edits`, the requested Tx/Rx/page triplets are `(0,0,0)`, `(1,1,1)`,
`(2,1,1)`, `(0,1,0)` and `(0,0,0)`. They allocate 2, 6, 18, 18 and 2 slots.
The fourth request is invalid and retains accepted selectors `(2,1,1)`;
the last request recovers. Each update writes all three scalars at one ordinal,
waits for the writes, seals that ordinal, and only then steps the renderer.
This retains the accepted configuration, not a frozen previous frame.
See the [example documentation](../../../docs/examples/python_generic_wpm.rst)
for paired Python/C readback and selector-update snippets.

## Limits

Gaussian sampling is seeded and scalar; blooming adds receiver slots, not rays.
The multistatic recipe is a path-transport layout, not an FMCW/IQ radar simulator.
Mechanical propagation uses the reference-air acoustic material model, not a
general elastic-wave solver. `DeltaTimeNs` is a firing offset, not arrival time.
