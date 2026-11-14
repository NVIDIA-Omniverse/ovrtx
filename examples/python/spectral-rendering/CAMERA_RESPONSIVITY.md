# Camera responsivity comparison

Render six spectral PathTracing images: CIE D65 daylight (6504 K) and low-pressure sodium,
each viewed with the default CIE 1931 observer, Canon EOS 5D, and Sony α7 IV
(ILCE-7M4) responses. All cameras share the rect-light scene's geometry, exposure,
6400-lumen light power, and path-tracing settings.

## Source data

The camera curves are copied unchanged from the Academy Software Foundation's
[rawtoaces-data](https://github.com/AcademySoftwareFoundation/rawtoaces-data) repository,
pinned to commit `e9b8503cf8a0641f40e5345d9757bde60c15f423`:

- [Canon EOS 5D](https://github.com/AcademySoftwareFoundation/rawtoaces-data/blob/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/camera/Canon_EOS_5D_380_780_5.json),
  SHA-256 `cbb73ad5103aeb9a5f182b56c14e665af3036de02ad8493207d94085bb067d1d`.
- [Sony ILCE-7M4](https://github.com/AcademySoftwareFoundation/rawtoaces-data/blob/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/camera/Sony_ILCE-7M4_380_780_5.json),
  SHA-256 `f7a8dc024ef923820c9d26ef4c31dd48deb28f0ea25cf70dd5a1bce3623576f8`.

Each file has 81 samples from 380 to 780 nm at 5 nm intervals, ordered R, G, B.
The headers attribute the measurements to `wetadigital`, equipment `lightsaber`,
and specify relative units and Apache-2.0 licensing. The Canon file describes the
original EOS 5D, not a Mark II/III/IV. `RAWTOACES-LICENSE` preserves the Apache-2.0
license; the original JSON headers are retained in the Python example's `camera-data/`.
These measurements describe the supplied profiles, not every unit of each model.

Calibration also uses the same repository's
[190-patch spectral training data](https://github.com/AcademySoftwareFoundation/rawtoaces-data/blob/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/training/training_spectral.json)
(Academy Science and Technology Council, Apache-2.0), SHA-256
`1b63cc85f7cf521bf80450fc60172a424a551cc690fdb05313b2cfa7aaa66da1`, and
[CIE 1931 color-matching functions](https://github.com/AcademySoftwareFoundation/rawtoaces-data/blob/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/cmf/cmf_1931.json),
SHA-256 `4f289294876d64a96092a1e567bb95a3e6dcd4caa2e5eb26b3be8ace0d9420a8`.
The latter are CIE 2019, DOI [10.25039/CIE.DS.xvudnb9b](https://doi.org/10.25039/CIE.DS.xvudnb9b),
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and are copied
unchanged. See `SPECTRA.md` for the sodium source.

## Color calibration

The camera datasets contain sensitivity curves, not camera-to-XYZ matrices.
`generate_camera_responsivity.py` derives one matrix per camera from the 190
training reflectances under CIE daylight at 6504 K. It linearly interpolates the
input spectra onto a 1 nm grid over 380–780 nm and uses trapezoidal integration.
A least-squares fit minimizes XYZ error, constrained to reproduce the CIE XYZ
of a perfect white reflector. This includes fixed daylight white balance.

The matrix is stored in `physical:responsivity:cameraToXYZ` and remains identical
under sodium. `physical:responsivity:colorTemperature` is set to zero so no extra
whitepoint adaptation is requested. RTX currently does not implement that
attribute's adaptation anyway. The default camera has no responsivity API and
uses the renderer's CIE 1931 observer.

These are example display calibrations, **not manufacturer matrices or rawtoaces
production IDTs**. With white Y normalized to one, training XYZ RMS errors are
about 0.0103 (Canon) and 0.00784 (Sony). A 3×3 matrix cannot remove all camera
metamerism. The original channel curves are retained; only the output transform
is derived. The example's RGB materials are reconstructed into spectra and are
not measured surface reflectances. Display images include the renderer's normal
color conversion and tone mapping; `--hdr` saves the linear result.

Regenerate the USD camera layer and calibration report from the committed inputs:

```bash
cd examples/python/spectral-rendering
uv run --script generate_camera_responsivity.py
```

The generated `camera_responsivity.usda` references `/World/Camera` so the two
custom cameras inherit the baseline camera's geometry and exposure. The
calibration report is `camera-data/calibration.json` in the Python example.

## Renderer automatic calibration

RTX now performs the same fixed-D65 fit in C++ when `cameraToXYZ` is zero,
including when the attribute is omitted. Nonzero matrices, including identity, override the fit;
this example retains its explicit matrices as reproducible reference values.
The result is cached with the camera curves and is independent of scene lighting
and `colorTemperature`. Rank-deficient responses retain identity.

The renderer's compiled reference table is generated from the same pinned
`training_spectral.json`. Camera curves and the renderer's CIE table use
float precision, so C++ results can differ slightly from this double-precision
reference fit.
