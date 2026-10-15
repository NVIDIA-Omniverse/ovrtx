# Projector Light Calibration

Generates a square OpenEXR direction texture from an OpenCV pinhole
calibration, then renders pinhole and calibrated projector lights against the
same scene used by the Rect Light documentation.

![Pinhole and OpenCV-calibrated projector output](../../../docs/img/light-projector-direction-texture.avif)

## Calibration

Replace this example camera matrix and distortion vector with values from your
OpenCV calibration:

```python
IMAGE_SIZE = (3840, 2160)
CAMERA_MATRIX = np.array(
    [
        [2400.0, 0.0, 1900.0],
        [0.0, 2421.0, 1200.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float64,
)
# OpenCV order: k1, k2, p1, p2, k3, k4, k5, k6,
# s1, s2, s3, s4, tau_x, tau_y.
DISTORTION = np.array(
    [
        -0.32734,
        0.07468,
        -0.00046,
        0.00106,
        0.0,
        0.0,
        0.0,
        0.0,
        -0.0008216463,
        0.0,
        -0.01727441,
        0.0,
        -0.03459962,
        0.001508283,
    ],
    dtype=np.float64,
)
```

## Octahedral Directions

Build the direction represented by every texel in the square lookup:

```python
texel_centers = (np.arange(texture_size, dtype=np.float64) + 0.5) / texture_size
oct_x, oct_y = np.meshgrid(
    texel_centers * 2.0 - 1.0,
    texel_centers * 2.0 - 1.0,
)
direction_z = 1.0 - np.abs(oct_x) - np.abs(oct_y)

folded_x = (1.0 - np.abs(oct_y)) * np.where(oct_x >= 0.0, 1.0, -1.0)
folded_y = (1.0 - np.abs(oct_x)) * np.where(oct_y >= 0.0, 1.0, -1.0)
direction_x = np.where(direction_z <= 0.0, folded_x, oct_x)
direction_y = np.where(direction_z <= 0.0, folded_y, oct_y)

directions = np.stack((direction_x, direction_y, direction_z), axis=-1)
directions /= np.linalg.norm(directions, axis=-1, keepdims=True)
```

## OpenCV Projection

Project the front-facing directions and mark directions outside the image:

```python
flat_directions = directions.reshape(-1, 3)
uv = np.full((flat_directions.shape[0], 2), -1.0, dtype=np.float32)

# The renderer flips local -Z before indexing the lookup, so valid decoded
# directions face +Z in the coordinate system passed to OpenCV.
front_facing = flat_directions[:, 2] > 1.0e-8
image_points, _ = cv2.projectPoints(
    flat_directions[front_facing],
    np.zeros(3),
    np.zeros(3),
    camera_matrix,
    distortion,
)
projected_uv = image_points[:, 0, :] / np.asarray(image_size)

# Projector lights emit only for UVs strictly inside (0, 1). Mark every
# direction that projects outside the calibrated image with -1.
inside_image = np.all((projected_uv > 0.0) & (projected_uv < 1.0), axis=1)
front_indices = np.flatnonzero(front_facing)
uv[front_indices[inside_image]] = projected_uv[inside_image]
uv = uv.reshape(directions.shape[:2] + (2,))
```

## OpenEXR Output

Write the projected UV values into float32 R and G channels:

```python
height, width, channels = uv.shape
if width != height or channels != 2:
    raise ValueError("direction textures must be square float RG images")

path.parent.mkdir(parents=True, exist_ok=True)
float_channel = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
header = OpenEXR.Header(width, height)
header["channels"] = {"R": float_channel, "G": float_channel}
header["compression"] = Imath.Compression(Imath.Compression.ZIP_COMPRESSION)

output = OpenEXR.OutputFile(str(path), header)
output.writePixels(
    {
        "R": np.ascontiguousarray(uv[:, :, 0], dtype=np.float32).tobytes(),
        "G": np.ascontiguousarray(uv[:, :, 1], dtype=np.float32).tobytes(),
    }
)
output.close()
```

The renderer samples the lookup with linear filtering. Use sufficient lookup
resolution for a smooth valid/invalid boundary; add an invalid guard band when
you need a hard calibrated aperture edge.

The example generates the direction texture before rendering both mappings:

```python
generate_direction_texture(direction_texture, args.texture_size)
pinhole = render_panel("pinhole", None, args.warmup_frames)
calibrated = render_panel(
    "opencv-calibrated", direction_texture, args.warmup_frames
)
```

## Running

```bash
uv run main.py
uv run main.py --rrd _output/projector-light-calibration.rrd
uv run main.py --no-rr --png _output/projector-light-calibration.png
```

You can generate only the lookup texture with:

```bash
uv run generate_direction_texture.py \
  --output _output/projector-opencv-direction.exr \
  --texture-size 1024
```

The projected image is “Chelsea the cat,” photographed by Stefan van der Walt
and dedicated to the public domain under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). It is
distributed with
[`skimage.data.chelsea`](https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.chelsea).
