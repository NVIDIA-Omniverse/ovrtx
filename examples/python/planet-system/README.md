# Planet System

Animated planetary system demo using ovrtx Python bindings. Demonstrates loading a USD scene into an attached ovstage, injecting additional geometry via `ovstage.population.add_usd_reference_from_string`, reusing one ovstage query for ordinal-keyed per-frame transform writes, and GPU-accelerated animation with Warp kernels. Planets orbit a central cube with hierarchical animation (orbit parent rotation + planet self-spin).

By default, rendered frames are streamed to [rerun.io](https://rerun.io/) for live visualization. Frames can also be saved to disk as PNGs.

> _“Create a Python animation example that loads a base scene, injects generated runtime geometry, creates one reusable stage query, updates many transforms efficiently each simulation step using CPU or GPU compute, renders frames, optionally streams or saves them, and releases the query explicitly.”_

![output](../../../img/example-planet-system.jpg)

## Prerequisites

- Python 3.10–3.13
- [uv](https://docs.astral.sh/uv/)

## Running

```bash
uv run main.py
```

### Options

| Flag | Description |
|------|-------------|
| `--gpu` | Device on which to copy animated transforms <cpu\|gpu> Default: cpu |
| `--num-planets N` | Number of planets, 1–1000 (default: 36) |
| `--png` | Save rendered frames as PNGs to `_output/` |
| `--no-rr` | Disable rerun.io streaming |
| `--log` | Enable carb log file in `_output/` |

The first time the example is run, driver shader compilation will be performed and cached. Subsequent runs will be much faster.
