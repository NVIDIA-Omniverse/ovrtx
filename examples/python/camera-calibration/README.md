# Camera calibration

Fit an OpenCV camera model to checkerboard photographs and write a USD Camera.
The eight supplied fisheye photographs are already in `input_images/`.
No renderer or GPU is required.

```bash
uv run main.py --fisheye --pattern 20x14
```

The command writes `_out/calibrated_camera.usda` and reports reprojection RMS.
Use `--images DIR` and `--pattern COLSxROWS` for your own photographs. The pattern
counts inner corners, not squares. Omit `--fisheye` for a pinhole lens; add
`--rational` for an eight-coefficient pinhole fit.

![Checkerboard calibration photographs](../../../docs/img/sensors/camera/calibration-inputs.avif)

See [Python: Camera calibration](../../../docs/examples/python_camera_calibration.rst)
for the walkthrough and output checks. Dependencies are managed by `uv` using
`pyproject.toml` and `uv.lock`.

Reference the generated Camera into your scene. The asset sets
`defaultPrim = "CalibratedCamera"`, so the reference only needs the file path.
Set its pose in the scene and point your RenderProduct at the referenced camera.
