# Camera Lens Calibration

Renders the robot-lineup scene through OpenCV pinhole, OpenCV fisheye, and
omni-directional stereo cameras and logs all three images to Rerun. `--png`
writes a contact sheet plus one PNG for each camera.

![OpenCV pinhole and fisheye views above an omni-directional stereo panorama](../../../docs/img/camera-lens-calibration.avif)

```bash
uv run main.py
uv run main.py --rrd _output/camera-lens-calibration.rrd
uv run main.py --no-rr --png _output/camera-lens-calibration.png
```
