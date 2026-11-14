#!/usr/bin/env python3
"""Output Configuration: USD relationships and returned tensors."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl


def generate(out_dir):
    c = dl.Canvas(1080, 650, "Requesting sensor outputs",
        "Camera and lidar RenderProducts target their sensor with camera and their "
        "RenderVars with orderedVars. Dashed arrows show returned image and point-cloud tensors.")
    for x, label in [(24, "Sensor prim"), (330, "RenderProduct"), (710, "RenderVar and returned output")]:
        dl.text(c, x, 30, label, 18, "bold")
    rows = [
        (60, "Camera", "/World/Camera", "/Render/Camera", "/Render/Camera/", "LdrColor", ["image tensor"]),
        (320, "OmniLidar", "/World/Lidar", "LidarProduct", "/World/Render/Vars/", "PointCloud", ["Coordinates, Intensity", "Counts, TimeOffsetNs, Flags"]),
    ]
    for y, sensor, sensor_path, product, var_parent, var, channels in rows:
        dl.box(c, 24, y, 210, 105, sensor, sublabel=sensor_path, label_size=18, sublabel_size=17)
        dl.box(c, 330, y, 230, 105, fill="#eef7dd", stroke=dl.GREEN)
        if var == "PointCloud":
            dl.text(c, 347, y + 26, "/World/Render/", 17, family=dl.M)
            dl.text(c, 347, y + 51, "Products/", 17, family=dl.M)
            dl.text(c, 347, y + 79, product, 18, "bold", family=dl.M)
        else:
            dl.text(c, 347, y + 58, product, 18, "bold", family=dl.M)
        dl.box(c, 710, y, 346, 105, fill="#eaf3ff", stroke=dl.BLUE)
        dl.text(c, 727, y + 27, var_parent, 17, family=dl.M)
        dl.text(c, 727, y + 52, var, 18, "bold", family=dl.M)
        dl.text(c, 727, y + 82, f'sourceName = "{var}"', 17, family=dl.M)
        dl.arrow(c, 324, y + 70, 240, y + 70)
        dl.text(c, 282, y + 49, "camera", 17, anchor="middle", family=dl.M)
        dl.arrow(c, 566, y + 70, 704, y + 70)
        dl.text(c, 635, y + 49, "orderedVars", 17, anchor="middle", family=dl.M)
        dl.arrow(c, 883, y + 111, 883, y + 144, dashed=True)
        dl.box(c, 710, y + 150, 346, 85, fill=dl.PANEL)
        for i, channel in enumerate(channels):
            dl.text(c, 727, y + 179 + i * 27, channel, 18)
        if var == "PointCloud":
            dl.text(c, 24, y + 155, 'Requested channels:', 18, "bold")
            dl.text(c, 24, y + 185, 'Coordinates, Intensity,', 18)
            dl.text(c, 24, y + 212, 'Counts, TimeOffsetNs', 18)
    dl.text(c, 24, 598, "Solid arrows: USD relationships. Dashed arrows: outputs returned by a step.", 18)
    dl.text(c, 24, 628, "Look up outputs by the full RenderVar prim path, not sourceName.", 18, "bold")
    dl.validate(c)
    dl.write_svg(out_dir / "output_configuration.svg", c.render())


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
