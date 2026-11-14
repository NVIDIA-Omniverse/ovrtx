# AOV Compositing

Render `aov-comp-scene.usda`, add its seven radiance components in linear RGB,
and compare the result with `LdrColor` after ACES Approximation and sRGB encoding.
The scene includes diffuse, reflective, refractive, subsurface, emissive, and
volume materials. The scene and its three local assets are the original files
used for the compositing validation.

## Runtime requirement

Rendering requires an NVIDIA RTX GPU and a supported driver. The example
defaults to `--denoise none`, capturing both raw beauty and raw AOVs.
`--denoise aovs` denoises beauty and all seven components.
Denoising only the beauty (`--denoise color`) does not preserve this comparison.
The compositing script itself uses only NumPy, OpenEXR, and Pillow and needs no GPU.


## Run

From this directory, render the scene, composite its outputs, and report the error:

```bash
uv run render-aovs.py
uv run composite-aovs.py
```

The default render uses 1280 x 720 pixels, 512 samples per pixel, and no denoising.
Linux users can also run `./render-aovs.sh` and
`./composite-aovs.sh`. Both wrappers resolve this project from any
working directory.

To keep generated files outside the example directory, pass the same location
to the two scripts:

```bash
uv run render-aovs.py --output-dir /path/to/aov
uv run composite-aovs.py --aov-dir /path/to/aov
```

Use `--resolution WIDTH HEIGHT` and `--spp N` to change render quality.
`--scene PATH` accepts another copy or variation of this scene with the same
camera, RenderProduct, and RenderVar paths. `--denoise scene` retains its authored
denoising settings. Each render writes an overlay and preserves the source
stage's units, up axis, and time metadata. It explicitly selects ACES
Approximation, linear sRGB output primaries, sRGB display encoding, and no dither.
The original scene and its assets remain unchanged.

## Outputs and acceptance

Render outputs default to `_output/aov/`:

- `LdrColor.png`: the renderer's 8-bit RGBA output, used as the RGB reference.
- `HdrColor.exr` and seven `Pt*.exr` files: unmodified floating-point RGBA outputs.
- `*.preview.png`: display-only Reinhard + sRGB previews; never compositing inputs.
- `render.usda`, `renderer.log`, and `metadata.json`: effective settings, runtime log,
  and render provenance, including the ovrtx build and scene hash.

The compositing script writes `_output/aov/composite/`:

- `sum.exr`: the linear RGB sum, saved as float32.
- `sum.aces-srgb.png`: the displayed RGB composite.
- `aov-catalog.png`: the seven AOVs and final composite, labeled in a two-column grid.
- `sum.aces-srgb.comparison.png`: reference, composite, and absolute difference x4.
- `sum.aces-srgb.difference.png`: absolute 8-bit RGB differences at full resolution.
- `report.json`: input hashes, linear HDR diagnostics, and full-resolution RGB metrics.

`--output-dir PATH` relocates the compositing results. `--png PATH` saves an
additional copy of the displayed composite. Existing output files are overwritten.

The catalog applies the same ACES Approximation and sRGB display transform to
each AOV and the final composite, without normalizing individual panels. It is
for viewing the contributions; the actual sum uses the linear EXR values before
any display transform.

The raw capture is diagnostic: the lighting AOVs accumulate at half precision,
while beauty accumulates at full precision. Their displayed sum can differ by
more than one code value. Inspect `report.json` before choosing a tolerance;
converting the EXRs to float32 cannot recover precision lost during rendering.
On Linux x86-64 with an RTX 5090, the default raw capture
had a maximum RGB error of 3/255. The strict one-code-value check therefore fails
for that capture.

Capture and check the validated denoised configuration explicitly:

```bash
uv run render-aovs.py --output-dir _output/denoised --denoise aovs
uv run composite-aovs.py --aov-dir _output/denoised --check
```

`--check` exits with status 1 if any RGB channel differs by more than
`--tolerance`, whose default is one 8-bit code value (1/255). The validated
denoised render had a maximum error of 1/255 and a mean absolute error of about
0.150/255; every RGB channel passed. This tolerance is specific to this scene,
its display transform, and the tested runtime. It is not a general error bound
for arbitrary scenes, render modes, or post-processing pipelines.

Alpha is preserved in the individual EXRs but is not added or compared.
No additional exposure, per-pass tone mapping, or denoising is applied while
compositing. `PtBackground` would duplicate background radiance already present
in the seven components; `Pt*Filter` outputs are not extra radiance contributions
and must not be multiplied into these final components again.

## Scene assets

`assets/studio.exr` and `assets/lookdev_grid_10k.png` are unchanged copies of the
assets already used by the public documentation test scenes. The volume density
is supplied by `assets/wdas_cloud_sixteenth.vdb`. All three files and
`aov-comp-scene.usda` are preserved byte-for-byte from the validated scene.


## Implementation

The render script waits for one converged frame and copies every output before
releasing the map. `PRODUCT` identifies the scene's RenderProduct, and `AOVS`
contains `LdrColor`, `HdrColor`, and the seven names below.

```python
# All components and the reference must come from the same converged frame.
for attempt in range(8):
    products = renderer.step(render_products={PRODUCT}, delta_time=1 / 60, ordinal=1)
    if PRODUCT not in products or not products[PRODUCT].frames:
        raise RuntimeError(f"Renderer returned no frame for {PRODUCT}")
    frame = products[PRODUCT].frames[-1]
    convergence.append(bool(frame.converged))
    print(f"Render request {attempt + 1}: converged={frame.converged}", flush=True)
    if frame.converged:
        break
    frame = products = None
else:
    raise RuntimeError("Path tracing did not converge after 8 render requests; see renderer.log")
# Copy while mapped: the NumPy view otherwise borrows the renderer output.
for name in AOVS:
    with frame.render_vars[f"/Render/Vars/{name}"].map(device=ovrtx.Device.CPU) as mapped:
        images[name] = np.from_dlpack(mapped).copy()
```

The compositor explicitly selects the seven radiance outputs, so other EXRs in
the directory cannot silently change the sum.

```python
# Select radiance components explicitly: PtBackground and Pt*Filter are not additive inputs.
COMPONENTS = (
    "PtDirectIllumation",  # This spelling is the renderer's actual sourceName.
    "PtGlobalIllumination",
    "PtReflections",
    "PtRefractions",
    "PtSubsurfaceScattering",
    "PtSelfIllumination",
    "PtVolumes",
)
```

It reads linear RGB values and checks that every input has the same dimensions
and EXR data window before adding them.

```python
# Read unmodified EXR RGB values. Preview PNGs have already been transformed.
total = None
inputs = []
for path in paths:
    rgb, data_window = read_rgb(path)
    if total is None:
        total = np.zeros_like(rgb)
        expected_window = data_window
    if rgb.shape != total.shape or data_window != expected_window:
        raise ValueError(f"{path}: EXR dimensions/dataWindow differ from the other inputs")
    total += rgb
    inputs.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
if total.shape != reference.shape:
    raise ValueError(f"EXR/PNG size mismatch: {total.shape} vs {reference.shape}")
if not np.isfinite(total).all():
    raise ValueError("The AOV sum contains non-finite values")
```

For this scene, `srgb8(aces_approximation(total))` reproduces the renderer's
display transform. The input already has the renderer's exposure applied.

```python
def srgb8(linear: np.ndarray) -> np.ndarray:
    # Encode only after summing and tone mapping; round once for the final 8-bit image.
    linear = np.clip(linear, 0.0, 1.0)
    encoded = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1.0 / 2.4) - 0.055)
    return np.rint(encoded * 255.0).astype(np.uint8)


def aces_approximation(linear: np.ndarray) -> np.ndarray:
    # Match this scene's ACES Approximation operator, with no second exposure multiplier.
    linear = np.maximum(linear, 0.0)
    return np.minimum(linear * (2.51 * linear + 0.03) / (linear * (2.43 * linear + 0.59) + 0.14), 1.0)
```

The comparison checks all RGB channels, while also reporting the average error
and exact equality separately.

```python
def compare(actual: np.ndarray, reference: np.ndarray, tolerance: float) -> dict:
    if actual.shape != reference.shape:
        raise ValueError(f"Image size mismatch: {actual.shape} vs {reference.shape}")
    # The threshold applies to every RGB channel, not just the average error.
    difference = actual.astype(np.float64) - reference.astype(np.float64)
    absolute = np.abs(difference)
    per_pixel = absolute.max(axis=-1)
    return {
        "exact_match": bool(np.all(absolute == 0)),
        "tolerance": tolerance,
        "within_tolerance": bool(np.all(absolute <= tolerance)),
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.mean(difference**2))),
        "max_absolute_error": float(absolute.max()),
        "p99_absolute_error": float(np.percentile(absolute, 99)),
        "exact_pixels_percent": float(100 * np.mean(per_pixel == 0)),
        "pixels_within_tolerance_percent": float(100 * np.mean(per_pixel <= tolerance)),
    }
```
