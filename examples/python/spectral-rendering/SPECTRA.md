# Spectrum sources

The mercury example copies published wavelength/value pairs from Colour Science.
Sodium augments Colour Science’s LPS data with the synthetic doublet described below.
`PhotometricAreaLightAPI` normalizes each spectrum to the same 6,400-lumen target.
The tabulated amplitudes are therefore not an absolute radiometric calibration.
All profiles illuminate the same rect light; they do not reproduce the original
fixtures' geometry or beam distribution.

- **Low-pressure sodium (`sodium`):** based on Colour Science v0.4.6,
  [`DATA_LIGHT_SOURCES_NIST_TRADITIONAL`](https://github.com/colour-science/colour/blob/v0.4.6/colour/colorimetry/datasets/light_sources/sds.py),
  entry `LPS`. Colour attributes this table to Ohno, Yoshiro and Davis, W.
  (2008), *NIST CQS simulation 7.4.xls*. Copyright 2013 Colour Developers;
  distributed under BSD-3-Clause. The complete notice is in `COLOUR-LICENSE`.
  Linearly interpolate the 81 source samples (380–780 nm, 5 nm spacing) onto
  a 1 nm grid. Add two synthetic Gaussian lobes centered at **588.9950 nm**
  and **589.5924 nm**, each with **2 nm FWHM**, with peak heights equal to
  **1.0** and **0.5** times the original LPS maximum. Scale the entire sum
  so its largest 1 nm sample equals that original maximum. The resulting
  401 samples span **380–780 nm**.
  The centers and 2:1 relative strengths follow the
  [NIST Na I line table](https://physics.nist.gov/PhysRefData/Handbook/Tables/sodiumtable2.htm).
  Gaussian width and added amplitude are illustrative choices, not measured
  lamp properties. This is an augmented spectrum, not a higher-resolution measurement.
  For reproduction, each lobe is `A * exp(-0.5 * ((wavelength - center) / sigma)**2)`,
  with `sigma = 2 / (2 * sqrt(2 * ln(2)))` nm.
- **Clear mercury vapor (`mercury`):** Colour Science v0.4.6,
  [`DATA_LIGHT_SOURCES_NIST_PHILIPS`](https://github.com/colour-science/colour/blob/v0.4.6/colour/colorimetry/datasets/light_sources/sds.py),
  entry `H38HT-100 (Mercury)`. Colour attributes this table to Ohno, Yoshiro
  and Davis, W. (2008), *NIST CQS simulation 7.4.xls*.
  Copyright 2013 Colour Developers; distributed under BSD-3-Clause.
  The complete notice and license are preserved in `COLOUR-LICENSE`.
  The source module has SHA-256
  `6f9a7790a843adafd93311ff886b81e3728103d6231fe635b4f1c9c71c5c2d26`.
  Mercury retains its 81 samples spanning 380–780 nm at 5 nm intervals.
  `H38HT-100 (Mercury)` represents a clear 100 W mercury-vapor lamp.

The renderer resamples custom illuminants onto a uniform 1 nm grid by default,
using the existing ASTM E2022 interpolation. The augmented Colour-based sodium table
has 1 nm spacing; mercury has 5 nm source spacing. Resampling
does not add measured spectral detail. The scene's RGB material colors are
reconstructed into spectra; they are not measured reflectance data.

The camera-responsivity example also uses `daylight`: the renderer’s CIE daylight
model at 6504 K (D65), at the same 6,400-lumen target. This differs from the
`white` preset. See `CAMERA_RESPONSIVITY.md` for the Canon EOS 5D and Sony α7 IV
curves and their fixed D65 display calibrations.

## Diamond geometry and material

The shared scene references `tests/docs/data/diamond.usd`, with
`simple_surface_materials.mdl` beside it. The isolated diamond mesh's material
was restored from its source scene and its bindings made local to the asset.
It uses `SimpleDispersiveGlossy`, IOR 2.4187 and Abbe number 55.3, in both RGB
and spectral PathTracing. The scene scales the diamond by three and places it
on a pavilion facet in front of the spheres, with the crown turned 65 degrees
camera-left; the source mesh remains unchanged.
