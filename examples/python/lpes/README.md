# Light Path Expressions

This example sublayers `ovrtx-robot-lineup.usda`, renders `HdrColor` plus
diffuse-reflection, glossy-reflection, glossy-transmission, and caustics Light
Path Expression outputs, and converts the linear Rec.709 images to sRGB
`uint8` for Rerun or PNG output.

![Beauty, diffuse reflection, glossy reflection, glossy transmission, and caustics outputs](../../../docs/img/light-path-expressions.avif)

## Prerequisites

- Python 3.10-3.13
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU and supported driver
- Internet access for payloads referenced by `ovrtx-robot-lineup.usda`

## Running

```bash
uv run main.py
uv run main.py --rrd _output/lpes.rrd
uv run main.py --no-rr --png _output/light-path-expressions.png
```

Useful options:

```bash
uv run main.py --resolution 1280 720
uv run main.py --spp 32
uv run main.py --usd path/to/scene.usd
```

The example maps every returned RenderVar and copies it before unmapping. It
then converts floating-point LPE and `HdrColor` images to sRGB:

```python
def read_lpe_outputs(frame) -> dict[str, np.ndarray]:
    images = {}
    for render_var_path, render_var in frame.render_vars.items():
        # Copy before unmapping so each image remains valid after this iteration.
        pixels = _map_render_var(render_var)
        if pixels.dtype == np.uint8:
            image = np.ascontiguousarray(pixels[..., :3])
        elif np.issubdtype(pixels.dtype, np.floating):
            # HdrColor and LPE outputs are linear Rec.709 floating-point images.
            image = _linear_rec709_to_srgb_uint8(pixels)
        else:
            raise TypeError(
                f"Unsupported image dtype for {render_var_path}: {pixels.dtype}"
            )

        print(
            f"  {render_var_path}: shape={pixels.shape}, dtype={pixels.dtype}",
            file=sys.stderr,
        )
        images[render_var_path] = image
    return images
```

Logged outputs:

- `HdrColor`
- `DiffuseReflection` (`E<RD>.*L`)
- `GlossyReflection` (`E<RG>.*L`)
- `GlossyTransmission` (`E<TG>.*L`)
- `Caustics` (`EDG.*L`)
