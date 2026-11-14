#!/usr/bin/env python3
"""Render the figures of the example scenes with the ovrtx and ovstage the pages describe.

Writes animated GIFs and AVIFs next to the generated diagrams:

- ``overview/first_sensor_panels_camera.gif`` and ``overview/first_sensor_panels_lidar.gif``: the
  lidar example's alternative scene (``lidar_example_panels.usda``) seen from a camera circling
  the lidar, and the point cloud of one scan of the same lidar on the same circle, coloured by
  ``Intensity``.
- ``nonvisual/radar_field_camera.gif``, ``nonvisual/radar_field_top_doppler.gif`` and
  ``nonvisual/radar_field_top_rcs.gif``: the radar example's alternative scene
  (``radar_example_field.usda``) over the example's ten steps, from the scene's preview camera and
  as top views of the detections coloured by ``RadialVelocityMs`` and by ``RCS``.
- ``nonvisual/acoustic_echo_envelope.avif``: the acoustic example's echo envelope
  (``acoustic_example.usda``, read with the example's own reader) over a to-scale side view of
  its scene, drawn from the numbers in the scene file, on one range axis.
- ``nonvisual/lidar_core_solid_state_scan.avif``: the lidar example scene scanned by a solid-state
  sensor this script defines on the example's mount, a half-degree grid with the detection floor
  off and one return per firing, from the viewpoint of the hub's rotary figure.
- ``nonvisual/lidar_core_intensity_floor_sweep.avif``: the lidar example's sensor beside a copy of
  it with ``minReflectance`` raised to 0.5, one scan each from the same step.
- ``nonvisual/lidar_sweep_compensated_vs_noncompensated.avif``: the panel scene's lidar moving
  forward at 8 m/s beside a second sensor with the same motion asking for ``COMPENSATED`` output,
  one sweep each from the same step, seen from above and colored by ``TimeOffsetNs``.
- ``nonvisual/lidar_core_tutorial_profiles.avif``: the three tutorial layers referenced onto the
  panel scene's mount with their detection floor off, one scan each, shaded by ``Intensity``
  relative to each scan's maximum.
- ``nonvisual/radar_example_velocity_and_rcs.avif``: the C example's copy of the radar scene (the
  one that requests ``RCS``) on step 5 of the example's run, top views colored by
  ``RadialVelocityMs`` with the Python example's own mapping and by ``RCS``.
- ``nonvisual/lidar_wpm_tiled_subsampling_density.avif``: the lidar example's cube scene swept by a
  rotary Lidar generic wpm model sensor this script defines, at ``tiledSubSampling`` 1 and 4 in one
  step, colored by ``Intensity``.
- ``nonvisual/lidar_wpm_glass_retroreflective_scan.avif``: one scan of the Lidar generic wpm model
  sensor of ``scenes/lidar_wpm_bus_shelter.usda``, a street scene with a glass bus shelter authored
  for this figure, colored by ``Intensity`` on a square-root scale, with a camera inset.
- ``nonvisual/idealized_depth_point_cloud.avif``: one frame of the Idealized depth model sensor of
  ``scenes/idealized_depth_plane_cube.usda``, a ground plane and one cube scanned
  with the schema's default emitter set, every hit a point colored by its distance. The model's
  output buffer is one the shipped host does not deliver; the figure was read through a build of
  this branch with that delivery enabled, and is to be re-rendered from the model's composite
  output when it exists.

- ``visual/camera_core_hdr_raw_isp_comparison.avif``,
  ``visual/camera_core_same_frame_four_taps.avif`` and ``visual/camera_core_aov_strip.avif``: one
  frame of the Camera generic core model's example scene in the source tree, with the Camera
  single-view stereo depth model on a second camera at the same pose, with a product of its own, both
  added by the overlay (a camera carries one sensor model); the floating-point and
  sensor-code images are scaled for display, crops magnified pixel for pixel.
- ``visual/depth_camera_beauty_shot.avif``, ``visual/depth_camera_cornell_outputs.avif`` and
  ``visual/depth_confidence_coverage.avif``: the fisheye depth product of the Cornell box test scene
  as shipped, and under overlays that set ``confidenceThreshold`` 0.5 and 0.99 with mode 6.
- ``nonvisual/radar_field_hero.avif`` (``radar_still``): one step of the same radar scene, mid-run, as two
  panels side by side: the preview camera's frame on the left and a top view of that step's
  detections coloured by ``RadialVelocityMs`` on the right; the radar figure of the Sensors overview's
  non-visual strip, the Non-Visual Sensors hub and the radar overview. The example pages and the
  moving-targets how-to keep ``img/example-sensor-radar.avif``, the viewer screenshot of the
  default two-cube scene.

The sensor's position is marked with a white dot in every view, the camera views included; in a
camera view the dot is left out while an opaque wall of the scene hides the sensor from the camera.

Run from ``rendering/ovrtx/public`` against the build the pages describe, never an older release:
the ovrtx and ovstage Python sources as editable packages over that build's native libraries
(a GPU is required)::

    OVRTX_BIN=../../_build/linux-x86_64/release
    LD_LIBRARY_PATH="$OVRTX_BIN:$OVRTX_BIN/plugins/omni.usd_mdl" OVSTAGE_LIBRARY_PATH_HINT="$OVRTX_BIN" \\
    uv run --no-project --with numpy --with pillow --with matplotlib \\
      --with-editable python --with-editable ../../ovstage/public/python \\
      python docs/img/sensors/_render_example_scenes.py [group ...]

The groups are the keys of ``GROUPS`` at the end of this file; without arguments every group is rendered.

The scenes are opened the way the examples open them; a temporary overlay layer adds what each figure
needs, the camera animation and render resolution of the animated figures and the sensors, RenderProducts
and attribute values the comparison figures are described with above, so the shipped scenes stay the
single source.
"""
import math, os, pathlib, re, struct, subprocess, sys, tempfile, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ovrtx, ovstage

HERE = pathlib.Path(__file__).resolve().parent
PUBLIC = HERE.parents[2]
EXAMPLES = PUBLIC / "examples" / "python"
SIZE = (600, 338)
DT = 0.1
INTENSITY_ANCHORS = np.array(((25, 45, 255), (0, 200, 255), (25, 255, 80), (255, 235, 0), (255, 30, 15)), np.float32)
RCS_ANCHORS = np.array(((40, 40, 160), (220, 60, 30), (255, 230, 60)), np.float32)
RCS_RANGE = (15.0, 55.0)        # dBsm, the fixed scale of the RCS top view
VELOCITY_SCALE = 10.0           # m/s, full blue (closing) or red (receding)


def lookat(eye, target, up=(0, 0, 1)):
    e, t, up = (np.asarray(v, float) for v in (eye, target, up))
    f = t - e; f /= np.linalg.norm(f); r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
    return [(*r, 0.0), (*u, 0.0), (*(-f), 0.0), (*e, 1.0)]


def usd_matrix(rows):
    return "( " + ", ".join("(" + ", ".join(f"{v:.6f}" for v in row) + ")" for row in rows) + " )"


def camera_from_scene(scene_path, prim="PreviewCamera"):
    """The preview camera's pose (USD matrix rows: right, up, back, eye) and horizontal field of view, from the scene text."""
    block = re.search(rf'def Camera "{prim}"\s*\{{(.*?)\n    \}}', scene_path.read_text(), re.S).group(1)
    focal = float(re.search(r"focalLength = ([0-9.]+)", block).group(1)); aperture = float(re.search(r"horizontalAperture = ([0-9.]+)", block).group(1))
    matrix = re.search(r"xformOp:transform = \((.*)\)", block).group(1)
    rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\(([^()]*)\)", matrix)]
    return rows, math.degrees(2 * math.atan(aperture / (2 * focal)))


def occluders_from_scene(scene_path, transparent=("Glass",)):
    """The scene's opaque, vertical Mesh rectangles as (axis, value, (lo, hi) along the other axis, (lo, hi) in z)."""
    out = []
    for m in re.finditer(r'def Mesh "\w+"[^{]*\{(.*?)\n    \}', scene_path.read_text(), re.S):
        body = m.group(1); ext = re.search(r"extent = \[\(([^)]*)\), \(([^)]*)\)\]", body)
        bind = re.search(r"material:binding = </World/Materials/(\w+)>", body)
        if not ext or (bind and bind.group(1) in transparent): continue
        lo = [float(v) for v in ext.group(1).split(",")]; hi = [float(v) for v in ext.group(2).split(",")]
        for axis in (0, 1):
            if lo[axis] == hi[axis]: out.append((axis, lo[axis], (lo[1 - axis], hi[1 - axis]), (lo[2], hi[2])))
    return out


def occluded(eye, point, occluders):
    """Whether one of the rectangles cuts the segment from the camera's eye to the point."""
    eye, point = np.asarray(eye, float), np.asarray(point, float); d = point - eye
    for axis, value, (a0, a1), (z0, z1) in occluders:
        if abs(d[axis]) < 1e-9: continue
        t = (value - eye[axis]) / d[axis]
        if not 0.0 < t < 1.0: continue
        hit = eye + t * d
        if a0 - 1e-6 <= hit[1 - axis] <= a1 + 1e-6 and z0 - 1e-6 <= hit[2] <= z1 + 1e-6: return True
    return False


def mark_sensor(img, rows, fov_deg, world_point, occluders=(), radius=4):
    """Draw a white dot, outlined dark, where a world point falls in the frame of a camera posed by USD matrix rows,
    unless an opaque rectangle of the scene hides the point from the camera."""
    right, up, back = (np.asarray(rows[i][:3], float) for i in range(3)); eye = np.asarray(rows[3][:3], float)
    rel = np.asarray(world_point, float) - eye; depth = -(rel @ back)
    if depth <= 0.1 or occluded(eye, world_point, occluders): return img
    h, w = img.shape[:2]; focal = w / (2 * math.tan(math.radians(fov_deg) / 2))
    x = w / 2 + focal * (rel @ right) / depth; y = h / 2 - focal * (rel @ up) / depth
    if not (0 <= x < w and 0 <= y < h): return img
    im = Image.fromarray(img); draw = ImageDraw.Draw(im)
    draw.ellipse([x - radius - 1.5, y - radius - 1.5, x + radius + 1.5, y + radius + 1.5], fill=(0, 0, 0))
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(255, 255, 255))
    return np.asarray(im)


def session(scene_path):
    renderer = ovrtx.Renderer(ovrtx.RendererConfig(log_level="warn", motion_bvh=ovrtx.MotionBvh.ENABLE))
    stage = ovstage.Stage("render_example_scenes"); renderer.attach_ovstage(stage)
    ovstage.population.open_usd(stage, str(scene_path), ordinal=1); stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    return renderer, stage


def finish(renderer, stage):
    renderer.detach_ovstage(); stage.destroy(); renderer.destroy()


def read_pointcloud(frame, var, names):
    with frame.render_vars[var].map(device=ovrtx.Device.CPU) as pc:
        coords = np.asarray(np.from_dlpack(pc["Coordinates"])); n = int(np.from_dlpack(pc["Counts"])[0])
        valid = (np.asarray(np.from_dlpack(pc["Flags"]))[:n] & 0x40) != 0
        points = coords.T if coords.shape[0] == 3 and coords.shape[1] != 3 else coords     # 3 x N (lidar core, radar) or N x 3 (lidar wpm)
        out = {"points": points[:n][valid].astype(np.float64).copy()}
        for name in names: out[name] = np.asarray(np.from_dlpack(pc[name]))[:n][valid].copy()
        return out


def read_image(frame, var):
    with frame.render_vars[var].map(device=ovrtx.Device.CPU) as m: return np.from_dlpack(m).copy()


# ---------------------------------------------------------------- drawing ----------------------
def project(points, eye, target, fov_deg, size):
    w, h = size; eye = np.asarray(eye, float); f = np.asarray(target, float) - eye; f /= np.linalg.norm(f)
    r = np.cross(f, (0, 0, 1.0)); r /= np.linalg.norm(r); u = np.cross(r, f)
    rel = np.asarray(points, float) - eye; d = rel @ f; focal = w / (2 * math.tan(math.radians(fov_deg) / 2)); sd = np.maximum(d, 0.01)
    x = w / 2 + focal * (rel @ r) / sd; y = h / 2 - focal * (rel @ u) / sd
    return x, y, d, (d > 0.15) & (x >= 0) & (x < w - 1) & (y >= 0) & (y < h - 1)


def splat(img, zbuf, x, y, d, colors, radius):
    h, w = img.shape[:2]; x = np.round(x).astype(int); y = np.round(y).astype(int); pix = img.reshape(-1, 3)
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius + 0.5: continue
            xx, yy = x + dx, y + dy; ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h); idx = yy[ok] * w + xx[ok]; dd = d[ok]
            np.minimum.at(zbuf, idx, dd); near = dd <= zbuf[idx] + 1e-4; pix[idx[near]] = colors[ok][near]


def ramp(values, anchors):
    v = np.clip(np.asarray(values, np.float32), 0, 1) * (len(anchors) - 1); lo = np.minimum(v.astype(int), len(anchors) - 2); w = (v - lo)[:, None]
    return (anchors[lo] * (1 - w) + anchors[lo + 1] * w).astype(np.uint8)


def velocity_colors(v):
    v = np.asarray(v, np.float32); t = np.clip(np.abs(v) / VELOCITY_SCALE, 0, 1)[:, None]; still = np.array([[40, 220, 60]], np.float32)
    closing = still * (1 - t) + np.array([[30, 90, 255]], np.float32) * t; receding = still * (1 - t) + np.array([[255, 40, 30]], np.float32) * t
    return np.where(v[:, None] < -0.5, closing, np.where(v[:, None] > 0.5, receding, still)).astype(np.uint8)


def ground_grid(x_range, y_range, step, z):
    pts = []
    for xv in np.arange(x_range[0], x_range[1] + 1e-6, step): pts.append(np.stack([np.full(400, xv), np.linspace(*y_range, 400), np.full(400, z)], 1))
    for yv in np.arange(y_range[0], y_range[1] + 1e-6, step): pts.append(np.stack([np.linspace(*x_range, 400), np.full(400, yv), np.full(400, z)], 1))
    return np.concatenate(pts)


def perspective_view(points, colors, eye, target, fov, grid, grid_z, marker, radius=1, size=SIZE):
    w, h = size; img = np.zeros((h, w, 3), np.uint8); zbuf = np.full(w * h, np.inf, np.float32)
    x, y, d, ok = project(grid, eye, target, fov, size); splat(img, zbuf, x[ok], y[ok], d[ok] + 0.5, np.full((int(ok.sum()), 3), 38, np.uint8), 0)
    x, y, d, ok = project(points, eye, target, fov, size); splat(img, zbuf, x[ok], y[ok], d[ok], colors[ok], radius)
    x, y, d, ok = project(np.asarray([marker]), eye, target, fov, size)
    if ok[0]: splat(img, zbuf, x, y, d - 0.3, np.array([[255, 255, 255]], np.uint8), 3)
    return img


def top_view_mapping(size, extent_forward, half_width):
    """Scale and image origin of the top view: x forward is up the image, y left is left of the sensor at the bottom centre."""
    w, h = size; return min((h - 50) / extent_forward, (w - 30) / (2 * half_width)), w / 2, h - 26


def top_view(points, colors, extent_forward=85.0, half_width=45.0, ring=10.0, dot=3, size=SIZE, ring_labels=False):
    w, h = size; img = np.zeros((h, w, 3), np.uint8); s, cx, cy = top_view_mapping(size, extent_forward, half_width)
    for r in np.arange(ring, extent_forward + 1e-6, ring):
        a = np.linspace(0, math.pi, 900); u = (cx - r * s * np.cos(a)).astype(int); v = (cy - r * s * np.sin(a)).astype(int)
        ok = (u >= 0) & (u < w) & (v >= 0) & (v < h); img[v[ok], u[ok]] = 48
    img[int(cy), :] = np.maximum(img[int(cy), :], 70); img[: int(cy), int(cx)] = np.maximum(img[: int(cy), int(cx)], 70)
    if len(points):
        u = np.round(cx - points[:, 1] * s).astype(int); v = np.round(cy - points[:, 0] * s).astype(int)
        for du in range(-dot, dot + 1):
            for dv in range(-dot, dot + 1):
                if du * du + dv * dv > dot * dot + 0.5: continue
                uu, vv = u + du, v + dv; ok = (uu >= 0) & (uu < w) & (vv >= 0) & (vv < h); img[vv[ok], uu[ok]] = colors[ok]
    img[int(cy) - 3: int(cy) + 4, int(cx) - 3: int(cx) + 4] = 255
    if ring_labels:
        im = Image.fromarray(img); draw = ImageDraw.Draw(im); f = font(14)
        for r in np.arange(ring, extent_forward + 1e-6, ring): draw.text((cx - draw.textlength(f"{r:g} m", font=f) - 6, cy - r * s - 16), f"{r:g} m", fill=(150, 150, 150), font=f)
        img = np.asarray(im)
    return img


def font(size):
    try: return ImageFont.load_default(size=size)
    except TypeError: return ImageFont.load_default()


def annotate(img, text, corner="bl", scale=None):
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); f = font(14); tw = draw.textlength(text, font=f)
    x, y = (8, im.height - 24) if corner == "bl" else (im.width - tw - 8, im.height - 24)
    draw.rectangle([x - 4, y - 2, x + tw + 4, y + 18], fill=(0, 0, 0)); draw.text((x, y), text, fill=(230, 230, 230), font=f)
    if scale is not None:  # a colour bar with its end labels, top right
        anchors, lo, hi, unit = scale; bar = ramp(np.linspace(0, 1, 120), anchors); bx, by = im.width - 136, 10
        for i, c in enumerate(bar): draw.line([(bx + i, by), (bx + i, by + 8)], fill=tuple(int(v) for v in c))
        draw.text((bx, by + 10), lo, fill=(200, 200, 200), font=font(12)); draw.text((bx + 120 - draw.textlength(hi, font=font(12)), by + 10), hi, fill=(200, 200, 200), font=font(12))
        draw.text((bx + 60 - draw.textlength(unit, font=font(12)) / 2, by + 24), unit, fill=(200, 200, 200), font=font(12))
    return np.asarray(im)


def save_gif(path, frames, durations):
    ims = [Image.fromarray(f).quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) for f in frames]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=durations, loop=0, optimize=False)
    print(f"{path.relative_to(HERE)}: {len(frames)} frames, {path.stat().st_size // 1024} KB")


def overlay(scene, body, time_codes=None, metadata=('defaultPrim = "World"', "metersPerUnit = 1", 'upAxis = "Z"')):
    """A temporary root layer that sublayers the shipped scene and adds the figure's own prims and animation.

    ``metadata`` is the stage metadata the root layer repeats; a scene that is not authored in meters passes its own."""
    header = "" if time_codes is None else f"    startTimeCode = 0\n    endTimeCode = {time_codes}\n    timeCodesPerSecond = 10\n"
    meta = "".join(f"    {line}\n" for line in metadata)
    text = f'#usda 1.0\n(\n{meta}{header}    subLayers = [ @{scene.resolve()}@ ]\n)\n{body}'
    path = pathlib.Path(tempfile.mkdtemp(prefix="render_example_scenes_")) / f"{scene.stem}_render.usda"; path.write_text(text); return path


# ---------------------------------------------------------------- lidar ------------------------
def lidar_figures():
    scene = EXAMPLES / "lidar" / "lidar_example_panels.usda"; sensor_world = np.array([0.0, 0.0, 1.5]); frames_n = 40
    target_w, radius, height, fov = np.array([0.8, 0.0, 0.7]), 8.6, 3.4, 72.0
    eyes = [np.array([radius * math.cos(a), radius * math.sin(a), height]) for a in (math.radians(-145 + 360 * k / frames_n) for k in range(frames_n))]
    samples = "\n".join(f"            {k}: {usd_matrix(lookat(e, target_w))}," for k, e in enumerate(eyes))
    body = f'''over "World"
{{
    over "PreviewCamera"
    {{
        matrix4d xformOp:transform.timeSamples = {{
{samples}
        }}
    }}
    over "Render"
    {{
        over "Products"
        {{
            over "CameraProduct"
            {{
                int2 resolution = ({SIZE[0]}, {SIZE[1]})
            }}
        }}
    }}
}}
'''
    _, cam_fov = camera_from_scene(scene); walls = occluders_from_scene(scene)
    renderer, stage = session(overlay(scene, body, time_codes=frames_n))
    lidar_prod, lidar_var = "/World/Render/Products/LidarProduct", "/World/Render/Vars/PointCloud"
    cam_prod, cam_var = "/World/Render/Products/CameraProduct", "/World/Render/Vars/LdrColor"
    ordinal = 2; ovstage.population.update_from_usd_time(stage, ordinal, 0.0); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(5): renderer.step(render_products={lidar_prod}, delta_time=DT, ordinal=ordinal)
    products = renderer.step(render_products={lidar_prod}, delta_time=DT, ordinal=ordinal)
    scan = read_pointcloud(products[lidar_prod].frames[0], lidar_var, ["Intensity"]); del products
    camera_frames = []
    for k in range(frames_n):
        ordinal += 1; ovstage.population.update_from_usd_time(stage, ordinal, k * DT); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        for _ in range(2): products = renderer.step(render_products={cam_prod}, delta_time=DT / 2, ordinal=ordinal)
        image = read_image(products[cam_prod].frames[-1], cam_var)[..., :3].copy(); del products
        camera_frames.append(mark_sensor(image, lookat(eyes[k], target_w), cam_fov, sensor_world, walls))
    finish(renderer, stage)
    # the point cloud is in the sensor frame (+X forward, +Z up, origin at the lidar): move the circle with it
    pts = scan["points"]; colors = ramp(np.sqrt(np.clip(scan["Intensity"], 0, 1)), INTENSITY_ANCHORS); grid = ground_grid((-10, 10), (-10, 10), 1.0, -sensor_world[2])
    cloud_frames = [perspective_view(pts, colors, e - sensor_world, target_w - sensor_world, fov, grid, -sensor_world[2], (0, 0, 0)) for e in eyes]
    save_gif(HERE / "overview" / "first_sensor_panels_camera.gif", camera_frames, 100)
    save_gif(HERE / "overview" / "first_sensor_panels_lidar.gif", cloud_frames, 100)
    print(f"lidar scan: {len(pts)} valid points")


# ---------------------------------------------------------------- radar ------------------------
def radar_figures():
    scene = EXAMPLES / "radar" / "radar_example_field.usda"; radar_world = np.array([0.0, 0.0, 1.0])
    cam_rows, cam_fov = camera_from_scene(scene); walls = occluders_from_scene(scene)
    body = f'''over "World"
{{
    over "Render"
    {{
        over "Products"
        {{
            over "CameraProduct"
            {{
                int2 resolution = ({SIZE[0]}, {SIZE[1]})
            }}
        }}
    }}
}}
'''
    renderer, stage = session(overlay(scene, body, time_codes=10))
    radar_prod, radar_var = "/World/Render/Products/RadarProduct", "/World/Render/Vars/PointCloud"
    cam_prod, cam_var = "/World/Render/Products/CameraProduct", "/World/Render/Vars/LdrColor"
    ordinal = 2; ovstage.population.update_from_usd_time(stage, ordinal, 0.0); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(3): renderer.step(render_products={radar_prod, cam_prod}, delta_time=DT, ordinal=ordinal)
    cam, dop, rcs, counts = [], [], [], []
    for step in range(1, 11):
        ordinal += 1; ovstage.population.update_from_usd_time(stage, ordinal, step * DT); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        products = renderer.step(render_products={radar_prod, cam_prod}, delta_time=DT, ordinal=ordinal)
        det = read_pointcloud(products[radar_prod].frames[0], radar_var, ["RadialVelocityMs", "RCS"]); image = read_image(products[cam_prod].frames[-1], cam_var)[..., :3].copy(); del products
        label = f"step {step} of 10, t = {step * DT:.1f} s"; counts.append(len(det["points"]))
        cam.append(annotate(mark_sensor(image, cam_rows, cam_fov, radar_world, walls), label))
        dop.append(annotate(top_view(det["points"], velocity_colors(det["RadialVelocityMs"])), label, scale=(np.array(((30, 90, 255), (40, 220, 60), (255, 40, 30)), np.float32), f"-{VELOCITY_SCALE:.0f}", f"+{VELOCITY_SCALE:.0f}", "RadialVelocityMs, m/s")))
        norm = (det["RCS"] - RCS_RANGE[0]) / (RCS_RANGE[1] - RCS_RANGE[0])
        rcs.append(annotate(top_view(det["points"], ramp(norm, RCS_ANCHORS)), label, scale=(RCS_ANCHORS, f"{RCS_RANGE[0]:.0f}", f"{RCS_RANGE[1]:.0f}", "RCS, dBsm")))
    finish(renderer, stage)
    durations = [350] * 9 + [1400]
    save_gif(HERE / "nonvisual" / "radar_field_camera.gif", cam, durations)
    save_gif(HERE / "nonvisual" / "radar_field_top_doppler.gif", dop, durations)
    save_gif(HERE / "nonvisual" / "radar_field_top_rcs.gif", rcs, durations)
    print(f"radar detections per step: {counts}")


# ---------------------------------------------------------------- lidar core -------------------
GRAY_ANCHORS = np.array(((70, 70, 70), (255, 255, 255)), np.float32)   # the hub figure's shading: weak returns dark, strong ones white
TUTORIAL_ASSETS = PUBLIC / "docs" / "sensors" / "nonvisual" / "lidar_core" / "tutorials" / "assets"
HUB_VIEW = (np.array([-9.0, -3.5, 5.0]), np.array([3.0, 0.0, 0.0]), 60.0)   # above and behind the sensor, the cube ahead to the right


def mounted_profile(name, layer, extra="", z=1.0):
    """A sensor for the overlay: a shipped profile layer referenced onto a lidar example's mount, with the example's output settings."""
    return f'''    def OmniLidar "{name}" (
        prepend references = @{layer.resolve()}@
    )
    {{
        token omni:sensor:Core:elementsCoordsType = "CARTESIAN"
        bool omni:sensor:Core:includeInvalidPoints = false
{extra}        double3 xformOp:translate = (0, 0, {z:g})
        float3 xformOp:rotateXYZ = (90, 0, -90)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}
'''


def products_block(*pairs):
    """The overlay's Render block: one RenderProduct per (name, sensor prim name), all on the scene's PointCloud var."""
    products = "".join(f'''            def RenderProduct "{name}"
            {{
                rel camera = </World/{sensor}>
                rel orderedVars = [</World/Render/Vars/PointCloud>]
            }}
''' for name, sensor in pairs)
    return "    over \"Render\"\n    {\n        over \"Products\"\n        {\n" + products + "        }\n    }\n"


def scan_once(renderer, product, var, names=("Intensity",), warmup=5):
    """Step until the sensor has settled, then read one complete scan of it."""
    for _ in range(warmup): renderer.step(render_products={product}, delta_time=DT, ordinal=2)
    products = renderer.step(render_products={product}, delta_time=DT, ordinal=2)
    scan = read_pointcloud(products[product].frames[-1], var, list(names)); del products
    return scan


def solid_state_grid(az=(-60.0, 60.0), el=(-25.0, 5.0), step=1.0, spread_ns=90_000_000):
    """A forward-facing solid-state pattern laid out in lines: one line per elevation, fired line after line over ``spread_ns`` of the scan period."""
    azimuths = np.arange(az[0], az[1] + 1e-6, step); elevations = np.arange(el[0], el[1] + 1e-6, step)
    cols, rows = len(azimuths), len(elevations); n = cols * rows
    fire = np.round(np.linspace(0, spread_ns, n)).astype(int)
    arrays = {"azimuthDeg": np.tile(azimuths, rows), "elevationDeg": np.repeat(elevations, cols), "fireTimeNs": fire,
              "channelId": np.arange(1, n + 1), "rangeId": np.zeros(n, int), "bank": np.repeat(np.arange(rows), cols)}
    fmt = lambda v: ", ".join(f"{x:g}" for x in v)
    lines = [f'        token omni:sensor:Core:scanType = "SOLID_STATE"', f"        uint omni:sensor:Core:numberOfEmitters = {n}",
             f"        uint omni:sensor:Core:numberOfChannels = {n}", f"        uint omni:sensor:Core:numLines = {rows}",
             f"        uint[] omni:sensor:Core:numRaysPerLine = [{fmt([cols] * rows)}]"]
    for name, values in arrays.items():
        kind = "float[]" if name.endswith("Deg") else "uint[]"
        lines.append(f"        {kind} omni:sensor:Core:emitterState:s001:{name} = [{fmt(values)}]")
    return "\n".join(lines) + "\n", (cols, rows, n)


def lidar_solid_state_figure():
    """F4: the lidar example scene scanned by the same model as a solid-state sensor, from the hub figure's viewpoint.

    The sensor is the script's own: a forward-facing half-degree grid fired line after line once per scan, the
    detection floor off (``minReflectance`` 0) and one return per firing (``maxReturns`` 1); the shading is Intensity
    relative to the scan's maximum."""
    scene = EXAMPLES / "lidar" / "lidar_example.usda"; sensor_world = np.array([0.0, 0.0, 1.0]); size = (1265, 713)
    pattern, (cols, rows, n) = solid_state_grid(step=0.5)
    body = f'''over "World"
{{
    def OmniLidar "LidarSolidState" (
        prepend apiSchemas = ["OmniSensorGenericLidarCoreAPI"]
    )
    {{
        token omni:sensor:Core:elementsCoordsType = "CARTESIAN"
        bool omni:sensor:Core:includeInvalidPoints = false
        double2 omni:sensor:frameRate = (10, 1)
        float omni:sensor:Core:minReflectance = 0.0
        uint omni:sensor:Core:maxReturns = 1
{pattern}        double3 xformOp:translate = (0, 0, 1)
        float3 xformOp:rotateXYZ = (90, 0, -90)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}
''' + products_block(("SolidStateProduct", "LidarSolidState")) + "}\n"
    renderer, stage = session(overlay(scene, body))
    ovstage.population.update_from_usd_time(stage, 2, 0.0); stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    scan = scan_once(renderer, "/World/Render/Products/SolidStateProduct", "/World/Render/Vars/PointCloud")
    finish(renderer, stage)
    eye, target, fov = HUB_VIEW; pts = scan["points"]; strength = scan["Intensity"] / max(float(scan["Intensity"].max()), 1e-9)
    colors = ramp(np.sqrt(strength), GRAY_ANCHORS); grid = ground_grid((-12, 26), (-16, 16), 1.0, -sensor_world[2])
    img = perspective_view(pts, colors, eye - sensor_world, target - sensor_world, fov, grid, -sensor_world[2], (0, 0, 0), size=size)
    save_avif(HERE / "nonvisual" / "lidar_core_solid_state_scan.avif", img)
    print(f"solid-state scan: {cols} x {rows} = {n} emitters, {len(pts)} valid points, intensity {float(scan['Intensity'].min()):.4f} to {float(scan['Intensity'].max()):.4f}")


TIME_ANCHORS = np.array(((25, 55, 150), (60, 130, 230), (170, 225, 255)), np.float32)   # TimeOffsetNs: one hue, early dark, late light
RAISED_FLOOR = 0.5                                                                       # F6: the raised minReflectance the caption states
PANEL_MOUNT = np.array([0.0, 0.0, 1.5])                                                  # the panel scene's sensor position


def label_panel(img, text, size=22):
    """A caption-like label in the top-left corner of a panel."""
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); f = font(size); tw = draw.textlength(text, font=f)
    draw.rectangle([8, 8, 8 + tw + 16, 8 + size + 14], fill=(0, 0, 0)); draw.text((16, 14), text, fill=(235, 235, 235), font=f)
    return np.asarray(im)


def color_bar(img, anchors, lo, hi, unit, size=16):
    """A colour bar with end labels and a unit, top right, sized for a wide panel."""
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); length, thick = 200, 12; bx, by = im.width - length - 16, 14
    for i, c in enumerate(ramp(np.linspace(0, 1, length), anchors)): draw.line([(bx + i, by), (bx + i, by + thick)], fill=tuple(int(v) for v in c))
    f = font(size); draw.text((bx, by + thick + 4), lo, fill=(210, 210, 210), font=f)
    draw.text((bx + length - draw.textlength(hi, font=f), by + thick + 4), hi, fill=(210, 210, 210), font=f)
    draw.text((bx + length / 2 - draw.textlength(unit, font=f) / 2, by + thick + 4 + size + 4), unit, fill=(210, 210, 210), font=f)
    return np.asarray(im)


def side_by_side(images, gutter=8):
    h = max(i.shape[0] for i in images); w = sum(i.shape[1] for i in images) + gutter * (len(images) - 1)
    out = np.full((h, w, 3), 255, np.uint8); x = 0
    for i in images: out[:i.shape[0], x:x + i.shape[1]] = i; x += i.shape[1] + gutter
    return out


def stacked(images, gutter=8):
    w = max(i.shape[1] for i in images); h = sum(i.shape[0] for i in images) + gutter * (len(images) - 1)
    out = np.full((h, w, 3), 255, np.uint8); y = 0
    for i in images: out[y:y + i.shape[0], :i.shape[1]] = i; y += i.shape[0] + gutter
    return out


def example_sensor(name, extra="", z=1.0, api="OmniSensorGenericLidarCoreAPI"):
    """A second sensor with the lidar examples' own settings, for a comparison on one scene."""
    return f'''    def OmniLidar "{name}" (
        prepend apiSchemas = ["{api}"]
    )
    {{
        token omni:sensor:Core:elementsCoordsType = "CARTESIAN"
        bool omni:sensor:Core:includeInvalidPoints = false
        double2 omni:sensor:frameRate = (10, 1)
{extra}        double3 xformOp:translate = (0, 0, {z:g})
        float3 xformOp:rotateXYZ = (90, 0, -90)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}
'''


def floor_sweep_scans(values, warmup=5):
    """F6 data: the lidar example's sensor beside copies of it with a raised minReflectance, one scan each, in one session."""
    scene = EXAMPLES / "lidar" / "lidar_example.usda"
    body = 'over "World"\n{\n' + "".join(example_sensor(f"LidarFloor{i}", f"        float omni:sensor:Core:minReflectance = {v:g}\n") for i, v in enumerate(values))
    body += products_block(*[(f"FloorProduct{i}", f"LidarFloor{i}") for i in range(len(values))]) + "}\n"
    renderer, stage = session(overlay(scene, body))
    ovstage.population.update_from_usd_time(stage, 2, 0.0); stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    products = ["/World/Render/Products/LidarProduct"] + [f"/World/Render/Products/FloorProduct{i}" for i in range(len(values))]
    for _ in range(warmup): renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    delivered = renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    scans = [read_pointcloud(delivered[prod].frames[-1], "/World/Render/Vars/PointCloud", ["Intensity"]) for prod in products]; del delivered
    finish(renderer, stage)
    return scans


def lidar_floor_sweep_figure():
    """F6: the lidar example's sweep at the shipped detection floor and after raising minReflectance, same scene and viewpoint."""
    sensor_world = np.array([0.0, 0.0, 1.0]); size = (800, 450); eye, target, fov = HUB_VIEW
    default, raised = floor_sweep_scans([RAISED_FLOOR])
    grid = ground_grid((-12, 26), (-16, 16), 1.0, -sensor_world[2]); panels = []
    for scan, text in ((default, "minReflectance 0.1 (the default)"), (raised, f"minReflectance {RAISED_FLOOR:g}")):
        colors = ramp(np.sqrt(np.clip(scan["Intensity"], 0, 1)), INTENSITY_ANCHORS)
        img = perspective_view(scan["points"], colors, eye - sensor_world, target - sensor_world, fov, grid, -sensor_world[2], (0, 0, 0), size=size)
        panels.append(label_panel(img, text))
    save_avif(HERE / "nonvisual" / "lidar_core_intensity_floor_sweep.avif", side_by_side(panels))
    print(f"floor sweep: {len(default['points'])} valid points at the default floor, {len(raised['points'])} at {RAISED_FLOOR:g}")


def lidar_motion_figure():
    """F7: one sweep of the panel scene's lidar while it moves forward, delivered NONCOMPENSATED and COMPENSATED, colored by TimeOffsetNs.

    The sensor moves along +X at 8 m/s (time-sampled translation, USD time advanced every step); a second sensor with the same
    motion and settings asks for COMPENSATED output, so both halves come from the same step of the same scene."""
    scene = EXAMPLES / "lidar" / "lidar_example_panels.usda"; size = (800, 450); speed, start_x = 8.0, -3.0
    samples = "\n".join(f"            {k}: ({start_x + speed * k * DT:g}, 0, {PANEL_MOUNT[2]:g})," for k in range(11))
    body = f'''over "World"
{{
    over "Lidar"
    {{
        double3 xformOp:translate.timeSamples = {{
{samples}
        }}
    }}
    def OmniLidar "LidarCompensated" (
        prepend apiSchemas = ["OmniSensorGenericLidarCoreAPI"]
    )
    {{
        token omni:sensor:Core:elementsCoordsType = "CARTESIAN"
        bool omni:sensor:Core:includeInvalidPoints = false
        double2 omni:sensor:frameRate = (10, 1)
        float omni:sensor:Core:reflectionPowerFraction = 1.0
        token omni:sensor:Core:outputMotionCompensationState = "COMPENSATED"
        double3 xformOp:translate.timeSamples = {{
{samples}
        }}
        float3 xformOp:rotateXYZ = (90, 0, -90)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}
''' + products_block(("CompensatedProduct", "LidarCompensated")) + "}\n"
    renderer, stage = session(overlay(scene, body, time_codes=10))
    products = {"/World/Render/Products/LidarProduct", "/World/Render/Products/CompensatedProduct"}
    for k in range(5):
        ordinal = 2 + k; ovstage.population.update_from_usd_time(stage, ordinal, k * DT); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        delivered = renderer.step(render_products=products, delta_time=DT, ordinal=ordinal)
    scans = {prod.rsplit("/", 1)[1]: read_pointcloud(delivered[prod].frames[-1], "/World/Render/Vars/PointCloud", ["TimeOffsetNs"]) for prod in products}; del delivered
    finish(renderer, stage)
    eye, target, fov = np.array([-5.0, 0.0, 19.0]), np.array([0.5, 0.0, 0.0]), 66.0; grid = ground_grid((-12, 12), (-12, 12), 1.0, -PANEL_MOUNT[2]); panels = []
    for prod, text in (("LidarProduct", "NONCOMPENSATED (the default)"), ("CompensatedProduct", "COMPENSATED")):
        scan = scans[prod]; t = np.asarray(scan["TimeOffsetNs"], np.float64) / 1e8     # the scan period, 100 ms
        img = perspective_view(scan["points"], ramp(t, TIME_ANCHORS), eye, target, fov, grid, -PANEL_MOUNT[2], (0, 0, 0), size=size)
        panels.append(color_bar(label_panel(img, text), TIME_ANCHORS, "0", "100 ms", "TimeOffsetNs"))
    save_avif(HERE / "nonvisual" / "lidar_sweep_compensated_vs_noncompensated.avif", side_by_side(panels))
    print("motion: " + ", ".join(f"{k} {len(v['points'])} points, time offsets {v['TimeOffsetNs'].min()} to {v['TimeOffsetNs'].max()} ns" for k, v in scans.items()))


def lidar_profiles_figure():
    """F8: the three shipped tutorial profiles referenced onto the panel scene's mount, one scan each, shaded by Intensity relative to each scan's maximum."""
    scene = EXAMPLES / "lidar" / "lidar_example_panels.usda"; size = (1000, 360)
    layers = ("Velodyne_Alpha_Prime_Rev4.usda", "Blickfeld_Cube1_Analytic.usda", "SICK_TiM781.usda")
    floor_off = "        float omni:sensor:Core:minReflectance = 0.0\n"     # the shipped floors are data-sheet values; here every return of each pattern shows
    body = 'over "World"\n{\n' + "".join(mounted_profile(f"Profile{i}", TUTORIAL_ASSETS / name, extra=floor_off, z=PANEL_MOUNT[2]) for i, name in enumerate(layers))
    body += products_block(*[(f"ProfileProduct{i}", f"Profile{i}") for i in range(len(layers))]) + "}\n"
    renderer, stage = session(overlay(scene, body))
    ovstage.population.update_from_usd_time(stage, 2, 0.0); stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    products = [f"/World/Render/Products/ProfileProduct{i}" for i in range(len(layers))]
    for _ in range(5): renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    delivered = renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    scans = [read_pointcloud(delivered[prod].frames[-1], "/World/Render/Vars/PointCloud", ["Intensity"]) for prod in products]; del delivered
    finish(renderer, stage)
    eye, target, fov = np.array([-8.0, -6.5, 7.0]), np.array([1.0, 0.0, 0.8]), 64.0; grid = ground_grid((-10, 12), (-10, 10), 1.0, -PANEL_MOUNT[2]); panels = []
    for scan, name in zip(scans, layers):
        strength = scan["Intensity"] / max(float(scan["Intensity"].max()), 1e-9) if len(scan["points"]) else scan["Intensity"]
        radius = 1 if len(scan["points"]) > 20000 else 2          # a sparse scan gets a larger point footprint
        img = perspective_view(scan["points"], ramp(np.sqrt(np.clip(strength, 0, 1)), INTENSITY_ANCHORS), eye, target, fov, grid, -PANEL_MOUNT[2], (0, 0, 0), radius=radius, size=size)
        panels.append(label_panel(img, name))
        print(f"profile {name}: {len(scan['points'])} valid points, intensity max {float(scan['Intensity'].max()) if len(scan['points']) else None}")
    save_avif(HERE / "nonvisual" / "lidar_core_tutorial_profiles.avif", stacked(panels))


# ---------------------------------------------------------------- radar detections (F9) -------
def top_label(img, text, x, y, extent_forward, half_width, size=20, dy=-28):
    """A label above a world position in a top view, with a short leader down to it."""
    s, cx, cy = top_view_mapping((img.shape[1], img.shape[0]), extent_forward, half_width); u, v = cx - y * s, cy - x * s
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); f = font(size); tw = draw.textlength(text, font=f)
    draw.line([(u, v - 6), (u, v + dy + size + 4)], fill=(200, 200, 200), width=1)
    draw.text((u - tw / 2, v + dy), text, fill=(235, 235, 235), font=f)
    return np.asarray(im)


def radar_detections_figure():
    """F9: the radar example scene's detections on step 5 of the example's run, from above, colored by RadialVelocityMs and by RCS.

    The scene is the C example's copy, the one that requests RCS; the velocity colours are the Python example's own mapping."""
    import importlib.util
    scene = PUBLIC / "examples" / "c" / "radar" / "radar_example.usda"; size = (800, 450); extent, half = 36.0, 18.0; step_shown = 5
    spec = importlib.util.spec_from_file_location("radar_example_main", EXAMPLES / "radar" / "main.py")
    radar = importlib.util.module_from_spec(spec); spec.loader.exec_module(radar)
    renderer, stage = session(scene); prod, var = radar.RENDER_PRODUCT, radar.POINTCLOUD_RENDER_VAR
    ordinal = 2; ovstage.population.update_from_usd_time(stage, ordinal, 0.0); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(radar.WARMUP_STEPS): renderer.step(render_products={prod}, delta_time=radar.STEP_DT_SECONDS, ordinal=ordinal)
    for step in range(1, step_shown + 1):
        ordinal += 1; ovstage.population.update_from_usd_time(stage, ordinal, step * radar.STEP_DT_SECONDS); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        products = renderer.step(render_products={prod}, delta_time=radar.STEP_DT_SECONDS, ordinal=ordinal)
    det = read_pointcloud(products[prod].frames[0], var, ["RadialVelocityMs", "RCS"]); del products
    finish(renderer, stage)
    text = scene.read_text(); steel_x = float(re.search(rf"\n\s*{step_shown}: \(([-0-9.]+), ([-0-9.]+), [-0-9.]+\)", text).group(1)); steel_y = float(re.search(rf"\n\s*{step_shown}: \(([-0-9.]+), ([-0-9.]+), [-0-9.]+\)", text).group(2))
    cx, cy = (float(v) for v in re.search(r'def Cube "LeftConcreteCube".*?xformOp:translate = \(([-0-9.]+), ([-0-9.]+),', text, re.S).groups())
    v = det["RadialVelocityMs"]; vmax = max(float(np.max(np.abs(v))), 1e-6); rcs = det["RCS"]; lo, hi = float(rcs.min()), float(rcs.max())
    velocity = top_view(det["points"], radar.radial_velocity_colors(v), extent, half, dot=6, size=size, ring_labels=True)
    velocity = color_bar(label_panel(velocity, "RadialVelocityMs, the example's colors"), np.array(((0, 0, 255), (0, 180, 0), (255, 0, 0)), np.float32), f"-{vmax:.1f}", f"+{vmax:.1f}", "m/s, blue approaching")
    by_rcs = top_view(det["points"], ramp((rcs - lo) / max(hi - lo, 1e-6), RCS_ANCHORS), extent, half, dot=6, size=size, ring_labels=True)
    by_rcs = color_bar(label_panel(by_rcs, "RCS"), RCS_ANCHORS, f"{lo:.0f}", f"{hi:.0f}", "dBsm, this frame's range")
    panels = [top_label(top_label(img, "steel cube, approaching", steel_x, steel_y, extent, half), "concrete cube", cx, cy, extent, half) for img in (velocity, by_rcs)]
    save_avif(HERE / "nonvisual" / "radar_example_velocity_and_rcs.avif", side_by_side(panels))
    print(f"radar step {step_shown}: {len(v)} detections, radial velocity {v.min():.2f} to {v.max():.2f} m/s, RCS {lo:.1f} to {hi:.1f} dBsm, steel cube at ({steel_x:g}, {steel_y:g}), concrete at ({cx:g}, {cy:g})")


# ---------------------------------------------------------------- wpm subsampling (F5) --------
def wpm_rotary_sensor(name, factor, rows=32, z=1.0):
    """A rotary Lidar generic wpm model sensor for the overlay: one firing pattern of ``rows`` emitter rows fanned out in elevation."""
    elevations = np.linspace(-20.0, 10.0, rows); fmt = lambda v: ", ".join(f"{x:g}" for x in v)
    return f'''    def OmniLidar "{name}" (
        prepend apiSchemas = ["OmniSensorGenericLidarWpmAPI"]
    )
    {{
        token visibility = "invisible"
        double2 omni:sensor:frameRate = (10, 1)
        token omni:sensor:LidarWpm:elementsCoordsType = "CARTESIAN"
        token omni:sensor:LidarWpm:scanType = "rotary"
        float omni:sensor:LidarWpm:rotPatternFiringResDeg = 0.5
        uint omni:sensor:LidarWpm:maxReturns = 2
        uint omni:sensor:LidarWpm:tiledSubSampling = {factor}
        float[] omni:sensor:LidarWpm:firingPattern:p001:azimuthDeg = [{fmt([0] * rows)}]
        float[] omni:sensor:LidarWpm:firingPattern:p001:elevationDeg = [{fmt(elevations)}]
        uint[] omni:sensor:LidarWpm:firingPattern:p001:fireTimeNs = [{fmt(range(0, rows * 1000, 1000))}]
        uint[] omni:sensor:LidarWpm:firingPattern:p001:channelId = [{fmt(range(1, rows + 1))}]
        uint[] omni:sensor:LidarWpm:firingPattern:p001:rangeId = []
        double3 xformOp:translate = (0, 0, {z:g})
        float3 xformOp:rotateXYZ = (90, 0, -90)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }}
'''


def wpm_subsampling_figure():
    """F5: the lidar example scene swept by one rotary Lidar generic wpm model sensor at tiledSubSampling 1 and 4, same sweep, colored by Intensity."""
    scene = EXAMPLES / "lidar" / "lidar_example.usda"; sensor_world = np.array([0.0, 0.0, 1.0]); size = (800, 450); factors = (1, 4)
    body = 'over "World"\n{\n' + "".join(wpm_rotary_sensor(f"LidarWpm{f}", f) for f in factors) + products_block(*[(f"WpmProduct{f}", f"LidarWpm{f}") for f in factors]) + "}\n"
    renderer, stage = session(overlay(scene, body))
    ovstage.population.update_from_usd_time(stage, 2, 0.0); stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    products = [f"/World/Render/Products/WpmProduct{f}" for f in factors]
    for _ in range(5): renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    delivered = renderer.step(render_products=set(products), delta_time=DT, ordinal=2)
    scans = [read_pointcloud(delivered[prod].frames[-1], "/World/Render/Vars/PointCloud", ["Intensity"]) for prod in products]; del delivered
    finish(renderer, stage)
    eye, target, fov = HUB_VIEW; grid = ground_grid((-12, 26), (-16, 16), 1.0, -sensor_world[2]); panels = []
    top = max(float(scan["Intensity"].max()) for scan in scans if len(scan["points"])) or 1.0
    for scan, f in zip(scans, factors):
        colors = ramp(np.sqrt(np.clip(scan["Intensity"] / top, 0, 1)), INTENSITY_ANCHORS)
        img = perspective_view(scan["points"], colors, eye - sensor_world, target - sensor_world, fov, grid, -sensor_world[2], (0, 0, 0), size=size)
        panels.append(label_panel(img, f"tiledSubSampling {f}: {len(scan['points']):,} valid points"))
        print(f"wpm factor {f}: {len(scan['points'])} valid points, intensity max {float(scan['Intensity'].max()) if len(scan['points']) else None}")
    save_avif(HERE / "nonvisual" / "lidar_wpm_tiled_subsampling_density.avif", side_by_side(panels))


# ---------------------------------------------------------------- wpm model: the glass bus shelter (F17) ---
SHELTER_SCENE = HERE / "scenes" / "lidar_wpm_bus_shelter.usda"
SHELTER_LIDAR = np.array([0.0, 0.0, 1.8])                                                # the scene's sensor position
SHELTER_VIEW = (np.array([-4.5, -8.0, 4.5]), np.array([8.0, 0.5, 1.0]), 58.0)
SHELTER_CALLOUTS = (((7.0, 1.0, 2.2), "glass pane", -150, -70), ((9.5, 0.5, 1.6), "wall behind the pane: second returns", 60, -60),
                    ((8.2, -0.5, 0.6), "bench inside the shelter", -150, 50), ((5.0, -3.5, 2.3), "sign", 30, -10), ((0.0, 0.0, 1.8), "lidar", 30, -40))
INTENSITY_FULL_SCALE = 2.55                                                              # the model's default intensityScale, the caption's full scale


def sqrt_color_bar(img, anchors, full, ticks, unit, size=14):
    """A colour bar for values shown on a square-root scale, tick labels at their true positions, top right on a black backing."""
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); length, thick = 200, 10; bx, by = im.width - length - 30, 14; f = font(size)
    draw.rectangle([bx - 30, by - 6, bx + length + 30, by + thick + size * 2 + 14], fill=(0, 0, 0))
    for i, c in enumerate(ramp(np.linspace(0, 1, length), anchors)): draw.line([(bx + i, by), (bx + i, by + thick)], fill=tuple(int(v) for v in c))
    for t in ticks:
        x = bx + length * math.sqrt(t / full); label = f"{t:g}"; draw.line([(x, by + thick), (x, by + thick + 3)], fill=(220, 220, 220))
        draw.text((x - draw.textlength(label, font=f) / 2, by + thick + 4), label, fill=(220, 220, 220), font=f)
    draw.text((bx + length / 2 - draw.textlength(unit, font=f) / 2, by + thick + size + 8), unit, fill=(220, 220, 220), font=f)
    return np.asarray(im)


def callouts(img, items, eye, target, fov, size=14):
    """Labels on black boxes with one-pixel leader lines to the image positions of world points."""
    im = Image.fromarray(img); draw = ImageDraw.Draw(im); f = font(size); w, h = im.size
    for world_pt, text, dx, dy in items:
        x, y, d, ok = project(np.asarray([world_pt]), eye, target, fov, (w, h))
        if not ok[0]: continue
        tx, ty = x[0] + dx, y[0] + dy; tw = draw.textlength(text, font=f)
        draw.line([(x[0], y[0]), (tx, ty)], fill=(235, 235, 235), width=1)
        draw.rectangle([tx - 3, ty - 2, tx + tw + 3, ty + size + 3], fill=(0, 0, 0)); draw.text((tx, ty), text, fill=(235, 235, 235), font=f)
    return np.asarray(im)


def lidar_wpm_figure():
    """F17: one scan of the Lidar generic wpm model sensor in the glass bus shelter scene, colored by Intensity, with a camera inset of the same view."""
    eye, target, fov = SHELTER_VIEW; size, inset = (1000, 562), (320, 180)
    lidar_prod, cam_prod = "/World/Render/Products/LidarProduct", "/World/Render/Products/CameraProduct"
    body = f'''over "World"
{{
    over "PreviewCamera"
    {{
        matrix4d xformOp:transform = {usd_matrix(lookat(eye, target))}
    }}
    over "Render"
    {{
        over "Products"
        {{
            over "CameraProduct"
            {{
                int2 resolution = ({inset[0] * 2}, {inset[1] * 2})
            }}
        }}
    }}
}}
'''
    renderer, stage = session(overlay(SHELTER_SCENE, body))
    for _ in range(2): products = renderer.step(render_products={lidar_prod, cam_prod}, delta_time=DT, ordinal=1)
    scan = read_pointcloud(products[lidar_prod].frames[-1], "/World/Render/Vars/PointCloud", ["Intensity", "EchoId"])
    for _ in range(6): products = renderer.step(render_products={cam_prod}, delta_time=DT / 2, ordinal=1)
    image = read_image(products[cam_prod].frames[-1], "/World/Render/Vars/LdrColor")[..., :3].copy(); del products
    finish(renderer, stage)
    pts, inten = scan["points"], scan["Intensity"]
    colors = ramp(np.sqrt(np.clip(inten / INTENSITY_FULL_SCALE, 0, 1)), INTENSITY_ANCHORS)
    img = perspective_view(pts, colors, eye, target, fov, ground_grid((-6, 14), (-10, 10), 1.0, 0.0), 0.0, SHELTER_LIDAR, size=size)
    img = sqrt_color_bar(img, INTENSITY_ANCHORS, INTENSITY_FULL_SCALE, (0, 0.16, 0.64, 1.4, 2.55), "Intensity, square-root scale")
    img = callouts(img, SHELTER_CALLOUTS, eye, target, fov)
    cam = np.asarray(Image.fromarray(image).resize(inset, Image.LANCZOS))
    cam = mark_sensor(cam, lookat(eye, target), camera_from_scene(SHELTER_SCENE)[1], SHELTER_LIDAR, occluders_from_scene(SHELTER_SCENE), radius=3)
    im = Image.fromarray(img); x0, y0 = size[0] - inset[0] - 10, size[1] - inset[1] - 10
    im.paste(Image.fromarray(cam), (x0, y0)); ImageDraw.Draw(im).rectangle([x0 - 1, y0 - 1, x0 + inset[0], y0 + inset[1]], outline=(200, 200, 200))
    save_avif(HERE / "nonvisual" / "lidar_wpm_glass_retroreflective_scan.avif", np.asarray(im))
    print(f"wpm shelter scan: {len(pts)} valid points, {int((scan['EchoId'] == 1).sum())} with EchoId 1, Intensity {float(inten.min()):.4f} to {float(inten.max()):.2f}")


# -------------------------------------------------------- idealized depth ----------------------
IDS_SCENE = HERE / "scenes" / "idealized_depth_plane_cube.usda"
IDS_SENSOR = np.array([0.0, 0.0, 1.0])                                                     # the scene's sensor position
IDS_PRODUCT, IDS_VAR, IDS_META = ("/World/Render/Products/DepthProduct", "/World/Render/Vars/GenericModelOutput",
                                  "/World/Render/Vars/RtxSensorMetadata")
IDS_VIEW = (np.array([-16.0, -13.0, 10.0]), np.array([3.0, 0.0, 0.0]), 58.0)
DISTANCE_ANCHORS = np.array(((255, 240, 90), (255, 140, 40), (225, 60, 120), (110, 70, 230), (60, 150, 255)), np.float32)   # near warm, far cool
DISTANCE_RANGE = (0.0, 45.0)                                                                # meters, the color bar's span: the plane's far corners
OUTPUT_HEADER = "<4IQI2H2Q2I16f" + "Q7f4x" * 2 + "2I7Q"                                     # the output buffer's packed header
OUTPUT_MAGIC = 0x4E474D4F
OUTPUT_AUX = "<2I7fi2fI4x6Q"                                                                 # the emitter shape's auxiliary struct
METADATA = "<5Q"                                                                             # dataSize, numElements, start, end, pointer


def read_depth_entries(frame, var, meta_var):
    """The Idealized depth model's entries of one frame: azimuth, elevation (degrees), distance (m), origin (m), VALID.

    The buffer is a packed header followed by one array per component (time offset, azimuth, elevation, distance,
    a scalar, flags), then, 8-byte aligned, the shape's auxiliary struct and the origin arrays; the metadata output
    cross-checks the element count. The offsets follow the model's test reader."""
    with frame.render_vars[var].map(device=ovrtx.Device.CPU) as m: raw = np.asarray(np.from_dlpack(m)).tobytes()
    with frame.render_vars[meta_var].map(device=ovrtx.Device.CPU) as m: meta = struct.unpack_from(METADATA, np.asarray(np.from_dlpack(m)).tobytes(), 0)
    magic, = struct.unpack_from("<I", raw, 0); n, = struct.unpack_from("<I", raw, struct.calcsize("<4IQ"))
    frame_of_reference, = struct.unpack_from("<H", raw, struct.calcsize("<4IQI")); coords, = struct.unpack_from("<I", raw, struct.calcsize("<4IQI2H2Q"))
    assert magic == OUTPUT_MAGIC and n == meta[1] and coords == 1, (hex(magic), n, meta[1], coords)   # 1: the three components are angles and distance
    off = struct.calcsize(OUTPUT_HEADER)
    def array(dtype):
        nonlocal off
        a = np.frombuffer(raw, dtype=dtype, count=n, offset=off); off += a.nbytes; return a
    _time, az, el, dist, _scalar, flags = array(np.int32), array(np.float32), array(np.float32), array(np.float32), array(np.float32), array(np.uint8)
    off += (-off) % 8 + struct.calcsize(OUTPUT_AUX); origin = np.stack([array(np.float32), array(np.float32), array(np.float32)], 1)
    assert meta[0] == off + 20 * n, (meta[0], off + 20 * n)                                  # objectId (16 bytes) and materialId (4) end the buffer
    return {"azimuth": az.copy(), "elevation": el.copy(), "distance": dist.copy(), "origin": origin.copy(), "valid": (flags & 0x40) != 0,
            "frame_of_reference": frame_of_reference, "count": n}


def idealized_depth_figure():
    """F19: one frame of the Idealized depth model over a ground plane and one cube, the default emitter set.

    The hits are placed from each entry's own origin along its azimuth and elevation at the reported distance, in the
    sensor frame, and colored by that distance; the cube sits ahead of the sensor, the plane shows the grid's rings."""
    eye, target, fov = IDS_VIEW; size = (1000, 562)
    renderer, stage = session(IDS_SCENE)
    for _ in range(3): products = renderer.step(render_products={IDS_PRODUCT}, delta_time=DT, ordinal=1)
    entries = read_depth_entries(products[IDS_PRODUCT].frames[-1], IDS_VAR, IDS_META); del products
    finish(renderer, stage)
    az, el = np.radians(entries["azimuth"].astype(np.float64)), np.radians(entries["elevation"].astype(np.float64))
    direction = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], 1)
    local = entries["origin"].astype(np.float64) + entries["distance"][:, None].astype(np.float64) * direction
    valid = entries["valid"]; pts = IDS_SENSOR + local[valid]; dist = entries["distance"][valid]
    ground = pts[(el[valid] < 0) & (np.abs(pts[:, 0] - 7) > 2.5)]                               # ground hits away from the cube's footprint
    print(f"idealized depth: {entries['count']} entries, {int(valid.sum())} valid, distance {dist.min():.2f} to {dist.max():.2f} m, "
          f"frame of reference {entries['frame_of_reference']}, ground height median {np.median(ground[:, 2]):.3f} m")
    colors = ramp((dist - DISTANCE_RANGE[0]) / (DISTANCE_RANGE[1] - DISTANCE_RANGE[0]), DISTANCE_ANCHORS)
    img = perspective_view(pts, colors, eye, target, fov, np.zeros((0, 3)), 0.0, IDS_SENSOR, size=size)
    img = color_bar(img, DISTANCE_ANCHORS, f"{DISTANCE_RANGE[0]:g}", f"{DISTANCE_RANGE[1]:g}", "Distance (m)")
    save_avif(HERE / "nonvisual" / "idealized_depth_point_cloud.avif", img)


# ---------------------------------------------------------------- visual models: one Cornell box frame (F10 to F13) ---
RENDERING = PUBLIC.parents[1]
CAMERA_CORE_SCENE = RENDERING / "source" / "examples" / "example.ovrtx.python" / "camera_core" / "CornellBoxCameraCoreExample.usda"
CAMERA_CORE_PRODUCT = "/Render/CameraIspExampleRP"
CAMERA_CORE_DEPTH_PRODUCT = "/Render/CameraDepthExampleRP"      # the depth model's own product, through a second camera at the same pose
CAMERA_CORE_AOVS = ("InputSource", "PostColorCorrection", "PostCfa", "PostNoise", "PreIsp", "PostYuvIsp", "PostIsp")
DEPTH_ON_CAMERA_CORE = {"baselineMM": 55.0, "focalLengthPixel": 897.0, "sensorSizePixel": 1280.0, "maxDisparityPixel": 250.0,
                        "confidenceThreshold": 1.0, "minDistance": 0.1, "maxDistance": 12.0, "noiseMean": 0.0, "noiseSigma": 0.0,
                        "noiseDownscaleFactorPixel": 1.0, "rgbDepthOutputMode": 3}
DEPTH_VARS = ("DistanceToImagePlaneSD", "Camera3dPositionSD", "DepthSensorDistance", "DepthSensorImager", "DepthSensorPointCloudPosition",
              "DepthSensorPointCloudColor", "DepthSensorOutputVisualization")
INK, PAPER = (49, 49, 49), (255, 255, 255)


def srgb_u8(linear):
    """Linear light in [0, 1] to 8-bit sRGB."""
    x = np.clip(np.asarray(linear, np.float32), 0, 1)
    return np.round(255 * np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)).astype(np.uint8)


def gray3(values):
    g = np.asarray(values, np.uint8); return np.repeat(g.reshape(g.shape[0], g.shape[1], 1), 3, axis=2)


def fit(img, w, h):
    return np.asarray(Image.fromarray(np.ascontiguousarray(img)).resize((w, h), Image.BOX))


def magnify(img, w, h):
    return np.asarray(Image.fromarray(np.ascontiguousarray(img)).resize((w, h), Image.NEAREST))


def captioned_strip(panels, labels, font_px=13, gutter=8, line_px=None, lines=1):
    """Panels side by side on white, each with its label (one or two lines of dark text) in a band below."""
    line_px = line_px or font_px + 5; band = 6 + lines * line_px
    h = max(p.shape[0] for p in panels); w = sum(p.shape[1] for p in panels) + gutter * (len(panels) - 1)
    out = Image.new("RGB", (w, h + band), PAPER); draw = ImageDraw.Draw(out); f = font(font_px); x = 0
    for panel, label in zip(panels, labels):
        out.paste(Image.fromarray(np.ascontiguousarray(panel)), (x, 0))
        for i, line in enumerate(label if isinstance(label, (list, tuple)) else [label]):
            draw.text((x + 2, h + 4 + i * line_px), line, fill=INK, font=f)
        x += panel.shape[1] + gutter
    return np.asarray(out)


def box_outline(img, x, y, w, h, color=(255, 230, 0), width=2):
    im = Image.fromarray(np.ascontiguousarray(img)); ImageDraw.Draw(im).rectangle([x, y, x + w, y + h], outline=color, width=width); return np.asarray(im)


def camera_core_frame():
    """Open the Camera generic core model's example scene with the depth model on a second camera at the same pose, warm up and read every output of one frame of both products."""
    attrs = "".join(f"    {'int' if isinstance(v, int) else 'float'} omni:sensor:depthSensor:{k} = {v}\n" for k, v in DEPTH_ON_CAMERA_CORE.items())
    extra = ("ldrColor",) + DEPTH_VARS
    defs = "".join(f'''        def RenderVar "{n}"
        {{
            uniform string sourceName = "{'LdrColor' if n == 'ldrColor' else n}"
        }}
''' for n in extra)
    # A camera carries one sensor model, so the depth model gets a second camera at the same pose (a reference to
    # the example's camera with the depth schema in place of the camera-core schema) and a product of its own.
    depth_targets = ", ".join(f"<{CAMERA_CORE_DEPTH_PRODUCT}/{n}>" for n in extra)
    body = f'''def Camera "camPersp2Depth" (
    references = </camPersp2>
    apiSchemas = ["OmniSensorGenericDepthSensorSingleViewAPI"]
)
{{
    string omni:sensor:modelName = "DepthSensorSingleView"
{attrs}}}
over "Render"
{{
    over "CameraIspExampleRP"
    {{
        append rel orderedVars = [<{CAMERA_CORE_PRODUCT}/ldrColor>]
        def RenderVar "ldrColor"
        {{
            uniform string sourceName = "LdrColor"
        }}
    }}
    def RenderProduct "{CAMERA_CORE_DEPTH_PRODUCT.rsplit("/", 1)[1]}"
    {{
        rel camera = </camPersp2Depth>
        uniform int2 resolution = (1920, 1080)
        rel orderedVars = [{depth_targets}]
{defs}    }}
}}
'''
    renderer, stage = session(overlay(CAMERA_CORE_SCENE, body, metadata=()))
    both = {CAMERA_CORE_PRODUCT, CAMERA_CORE_DEPTH_PRODUCT}
    for _ in range(10): renderer.step(render_products=both, delta_time=DT, ordinal=1)
    products = renderer.step(render_products=both, delta_time=DT, ordinal=1)
    core, depth = products[CAMERA_CORE_PRODUCT].frames[-1], products[CAMERA_CORE_DEPTH_PRODUCT].frames[-1]
    names = ("hdrColor", "ldrColor") + tuple("OmniCameraSensor" + a for a in CAMERA_CORE_AOVS)
    out = {n: read_image(core, f"{CAMERA_CORE_PRODUCT}/{n}") for n in names}
    out.update({n: read_image(depth, f"{CAMERA_CORE_DEPTH_PRODUCT}/{n}") for n in DEPTH_VARS}); del core, depth, products
    finish(renderer, stage); return out




def camera_core_figures():
    """F11 to F13 from one frame of the Camera generic core model's example scene."""
    f = camera_core_frame(); H, W = f["hdrColor"].shape[:2]
    hdr = f["hdrColor"][..., :3].astype(np.float32); lum = 0.2126 * hdr[..., 0] + 0.7152 * hdr[..., 1] + 0.0722 * hdr[..., 2]
    white = float(np.percentile(lum, 99.5)); show_hdr = lambda img: srgb_u8(img[..., :3].astype(np.float32) / white)
    cfa_scale = float(np.percentile(f["OmniCameraSensorPostCfa"], 99.5)); show_code = lambda img: gray3(srgb_u8(img[..., 0].astype(np.float32) / cfa_scale))
    pre_isp = gray3(np.round(255 * f["OmniCameraSensorPreIsp"][..., 0].astype(np.float32) / 65520).astype(np.uint8))
    luma = gray3(np.round(255 * f["OmniCameraSensorPostYuvIsp"][..., 2].astype(np.float32) / 65535).astype(np.uint8))
    post_isp = f["OmniCameraSensorPostIsp"][..., :3]; ldr = f["ldrColor"][..., :3]
    depth_vis = f["DepthSensorOutputVisualization"][..., :3]; depth = f["DepthSensorDistance"][..., 0]
    print(f"camera core frame {W} x {H}: HdrColor white {white:.3f}, mosaic scale {cfa_scale:.3g}, depth measured on {100 * np.mean(depth > 0):.1f}% of pixels, "
          f"PostNoise differs from PostCfa at {100 * np.mean(f['OmniCameraSensorPostNoise'] != f['OmniCameraSensorPostCfa']):.1f}% of pixels")
    pw, ph = 328, 184
    # F11: HdrColor input, the RAW mosaic crop, the processed image
    cx, cy, cw, ch = 1548, 742, 64, 36
    hdr_panel = box_outline(fit(box_outline(show_hdr(f["hdrColor"]), cx, cy, cw, ch, width=4), pw, ph), 0, 0, 0, 0, width=0) if False else fit(box_outline(show_hdr(f["hdrColor"]), cx, cy, cw, ch, width=4), pw, ph)
    raw_crop = magnify(pre_isp[cy:cy + ch, cx:cx + cw], pw, ph)
    strip = captioned_strip([hdr_panel, raw_crop, fit(post_isp, pw, ph)],
                            [("HdrColor input, scaled for display;", "the box marks the crop"), ("RAW mosaic before the ISP,", "OmniCameraSensorPreIsp, crop magnified"), ("Processed image,", "OmniCameraSensorPostIsp")],
                            font_px=13, lines=2)
    save_avif(HERE / "visual" / "camera_core_hdr_raw_isp_comparison.avif", strip)
    # F12: four taps of one frame; the noise tap carries the amplified difference to the previous tap
    pw4, ph4 = 244, 137
    noise = show_code(f["OmniCameraSensorPostNoise"]); cfa = f["OmniCameraSensorPostCfa"][..., 0].astype(np.float32)
    rel = (f["OmniCameraSensorPostNoise"][..., 0].astype(np.float32) - cfa) / np.maximum(cfa, 1); inset = gray3(np.round(255 * np.clip((rel[cy:cy + ch, cx:cx + cw] + 0.02) / 0.04, 0, 1)).astype(np.uint8))
    noise_panel = fit(noise, pw4, ph4); ins = magnify(inset, 80, 45); im = Image.fromarray(noise_panel.copy()); im.paste(Image.fromarray(ins), (pw4 - 84, ph4 - 49))
    ImageDraw.Draw(im).rectangle([pw4 - 85, ph4 - 50, pw4 - 4, ph4 - 4], outline=(255, 255, 255), width=1); noise_panel = np.asarray(im)
    strip = captioned_strip([fit(show_hdr(f["hdrColor"]), pw4, ph4), fit(show_code(f["OmniCameraSensorPostCfa"]), pw4, ph4), noise_panel, fit(post_isp, pw4, ph4)],
                            [("HdrColor", ""), ("OmniCameraSensorPostCfa", ""), ("OmniCameraSensorPostNoise;", "inset: difference to PostCfa, amplified"), ("OmniCameraSensorPostIsp", "")],
                            font_px=12, lines=2)
    save_avif(HERE / "visual" / "camera_core_same_frame_four_taps.avif", strip)
    # F13: the seven AOVs in pipeline order, each above a magnified crop of one window
    tw, th = 148, 83; kx, ky, kw = 1576, 748, 18
    pictures = [show_hdr(f["OmniCameraSensorInputSource"]), show_hdr(f["OmniCameraSensorPostColorCorrection"]), show_code(f["OmniCameraSensorPostCfa"]),
                show_code(f["OmniCameraSensorPostNoise"]), pre_isp, luma, post_isp]
    row1 = [fit(img, tw, th) for img in pictures]; row2 = [magnify(img[ky:ky + kw, kx:kx + kw], tw, tw) for img in pictures]
    labels = [("OmniCameraSensor-", a) for a in CAMERA_CORE_AOVS]
    top = side_by_side(row1); bottom = captioned_strip(row2, labels, font_px=11, lines=2)
    strip = stacked([top, bottom]); strip = np.pad(strip, ((8, 0), (8, 8), (0, 0)), constant_values=255)
    save_avif(HERE / "visual" / "camera_core_aov_strip.avif", strip)


# ---------------------------------------------------------------- depth model: the Cornell box fisheye product (F14 to F16) ---
DEPTH_SCENE = RENDERING / "data" / "usd" / "tests" / "ovrtx" / "CornellBoxCameraCore.usda"
DEPTH_PRODUCT = "/Render/DepthSensorFisheye"
DEPTH_METADATA = ("metersPerUnit = 0.0009999999776482582", 'upAxis = "Z"')         # the scene's own stage metadata, repeated by the overlay
DEPTH_CROP = (92, 0, 1020, 696)                                                       # the lens's image area of the 1280 x 720 frame, plus a margin
DEPTH_GRAY = (0.19, 0.86)                                                             # meters mapped to gray 255 (near) .. 64 (far); zero stays black


def depth_frame(body=None, warmup=64):
    """One frame of the fisheye depth product of the Cornell box test scene, as shipped or under an overlay, after the example's warm-up."""
    scene = DEPTH_SCENE if body is None else overlay(DEPTH_SCENE, body, metadata=DEPTH_METADATA)
    renderer, stage = session(scene)
    for _ in range(warmup): renderer.step(render_products={DEPTH_PRODUCT}, delta_time=DT, ordinal=1)
    products = renderer.step(render_products={DEPTH_PRODUCT}, delta_time=DT, ordinal=1); frame = products[DEPTH_PRODUCT].frames[-1]
    names = ("ldrColor", "DistanceToImagePlaneSD", "DepthSensorDistance", "DepthSensorImager", "DepthSensorPointCloudPosition", "DepthSensorPointCloudColor", "DepthSensorOutputVisualization")
    out = {n: read_image(frame, f"{DEPTH_PRODUCT}/{n}") for n in names}; del frame, products
    finish(renderer, stage); return out


def crop(img):
    x0, y0, x1, y1 = DEPTH_CROP; return np.ascontiguousarray(img[y0:y1, x0:x1])


def mode3_rainbow(distance, lo, hi):
    """The depth model's own mode-3 color scale over the gates, so the renderer's distance can be painted like the model's visualization."""
    d = np.asarray(distance, np.float32); ok = np.isfinite(d) & (d >= lo) & (d <= hi)
    norm = np.clip((np.where(ok, d, lo) - lo) / (hi - lo), 0, 1); hue = np.sqrt(norm) - 0.2; hue = np.where(hue < 0, hue + 1, hue)
    h6 = hue * 6; i = np.floor(h6).astype(int) % 6; f = h6 - np.floor(h6)
    q, t = 1 - f, f; r = np.choose(i, [1, q, 0, 0, t, 1]); g = np.choose(i, [t, 1, 1, q, 0, 0]); b = np.choose(i, [0, 0, t, 1, 1, q])
    rgb = (np.stack([r, g, b], -1) * 255).astype(np.uint8); rgb[~ok] = 0; return rgb


def depth_gray(distance):
    d = np.asarray(distance, np.float32); lo, hi = DEPTH_GRAY
    g = np.where(d > 0, 255 - np.round(np.clip((d - lo) / (hi - lo), 0, 1) * 191), 0).astype(np.uint8); return gray3(g)


def point_cloud_view(positions, colors_rgba, size):
    """DepthSensorPointCloudPosition seen from beside and above the camera: camera frame x right, y up, -z forward, in the scene's millimeters."""
    pos = positions.reshape(-1, 4); col = colors_rgba.reshape(-1, 4)[:, :3]; ok = pos[:, 3] > 0.5
    pts = np.stack([-pos[ok, 2], -pos[ok, 0], pos[ok, 1]], 1)                  # forward = -z, left = -x, up = y
    w, h = size; img = np.zeros((h, w, 3), np.uint8); zbuf = np.full(w * h, np.inf, np.float32)
    eye, target, fov = np.array([-250.0, -650.0, 520.0]), np.array([520.0, 0.0, -40.0]), 62.0
    x, y, d, vis = project(pts, eye, target, fov, size); splat(img, zbuf, x[vis], y[vis], d[vis], np.ascontiguousarray(col[ok][vis]), 1)
    x, y, d, vis = project(np.zeros((1, 3)), eye, target, fov, size)
    if vis[0]: splat(img, zbuf, x, y, d - 1, np.array([[255, 255, 255]], np.uint8), 4)
    return img


def depth_figures():
    """F14 to F16: the Camera single-view stereo depth model on the Cornell box fisheye product, as shipped and at two confidence thresholds."""
    f = depth_frame(); gates = (0.1, 5.0)
    depth = f["DepthSensorDistance"][..., 0]; truth = f["DistanceToImagePlaneSD"][..., 0]
    print(f"depth frame: measured on {100 * np.mean(depth > 0):.1f}% of pixels, {depth[depth > 0].min():.3f} to {depth.max():.3f} m; renderer distance {truth[np.isfinite(truth)].min():.3f} to {truth[np.isfinite(truth)].max():.3f} m")
    half = lambda img: fit(crop(img), 464, 348)
    # F14: input, the renderer's distance in the model's color scale, the model's visualization
    panels = [half(f["ldrColor"][..., :3]), half(mode3_rainbow(truth, *gates)), half(f["DepthSensorOutputVisualization"][..., :3])]
    strip = captioned_strip(panels, [("LdrColor", "the rendered input"), ("DistanceToImagePlaneSD", "the renderer's distance, in the model's color scale"), ("DepthSensorOutputVisualization, mode 3", "near magenta to far yellow, black = no measurement")], font_px=14, lines=2)
    save_avif(HERE / "visual" / "depth_camera_beauty_shot.avif", strip)
    # F15: the five outputs, with a projected point cloud and a legend
    pw, ph = 356, 267; small = lambda img: fit(crop(img), pw, ph)
    cloud = fit(point_cloud_view(f["DepthSensorPointCloudPosition"], f["DepthSensorPointCloudColor"], (pw * 2, ph * 2)), pw, ph)
    legend = Image.new("RGB", (pw, ph), PAPER); draw = ImageDraw.Draw(legend); fl = font(14)
    draw.text((10, 18), "DepthSensorDistance: gray, near bright", fill=INK, font=fl)
    for i in range(200): v = 255 - round(191 * i / 199); draw.line([(10 + i, 44), (10 + i, 58)], fill=(v, v, v))
    hi_gray = f"{DEPTH_GRAY[1]:.2f} m"; draw.text((10, 62), f"{DEPTH_GRAY[0]:.2f} m", fill=INK, font=fl); draw.text((210 - draw.textlength(hi_gray, font=fl), 62), hi_gray, fill=INK, font=fl)
    draw.text((10, 100), "DepthSensorOutputVisualization: mode 3", fill=INK, font=fl)
    bar = mode3_rainbow(np.linspace(gates[0], gates[1], 200)[None, :], *gates)[0]
    for i, c in enumerate(bar): draw.line([(10 + i, 126), (10 + i, 140)], fill=tuple(int(v) for v in c))
    draw.text((10, 144), f"left end: minDistance {gates[0]:g} m", fill=INK, font=fl); draw.text((10, 162), f"right end: maxDistance {gates[1]:g} m", fill=INK, font=fl)
    draw.text((10, 200), "Black: no measurement (zero, empty entry)", fill=INK, font=fl); draw.text((10, 222), "White dot in the point cloud: the camera", fill=INK, font=fl)
    row1 = captioned_strip([small(depth_gray(depth)), small(gray3(np.round(255 * np.clip(f["DepthSensorImager"][..., 0], 0, 1)).astype(np.uint8))), small(f["DepthSensorPointCloudColor"][..., :3])],
                           ["DepthSensorDistance", "DepthSensorImager", "DepthSensorPointCloudColor"], font_px=14)
    row2 = captioned_strip([small(f["DepthSensorOutputVisualization"][..., :3]), cloud, np.asarray(legend)],
                           ["DepthSensorOutputVisualization, mode 3", "DepthSensorPointCloudPosition, projected", ""], font_px=14)
    grid = stacked([row1, row2]); grid = np.pad(grid, ((0, 0), (8, 8), (0, 0)), constant_values=255)
    save_avif(HERE / "visual" / "depth_camera_cornell_outputs.avif", grid)
    # F16: the confidence map (mode 6) and the distance image at two thresholds
    runs = {}
    for threshold in (0.5, 0.99):
        body = f'''over "DepthCamGroup"
{{
    over "depthCam_12" (
        prepend apiSchemas = ["OmniSensorGenericDepthSensorSingleViewAPI"]
    )
    {{
        float omni:sensor:depthSensor:confidenceThreshold = {threshold}
        int omni:sensor:depthSensor:rgbDepthOutputMode = 6
    }}
}}
'''
        runs[threshold] = depth_frame(body); d = runs[threshold]["DepthSensorDistance"][..., 0]
        print(f"confidenceThreshold {threshold}: measured on {100 * np.mean(d > 0):.1f}% of pixels")
    cw, chh = 496, 372; col = lambda img: fit(crop(img), cw, chh)
    columns = []
    for threshold in (0.5, 0.99):
        column = captioned_strip([col(runs[threshold]["DepthSensorOutputVisualization"][..., :3])], [("DepthSensorOutputVisualization, mode 6", "white: passed; gray: a failed pixel's texture gradient")], font_px=14, lines=2)
        column = stacked([column, captioned_strip([col(depth_gray(runs[threshold]["DepthSensorDistance"][..., 0]))], [("DepthSensorDistance", "near bright, far dark, black = no measurement")], font_px=14, lines=2)])
        head = Image.new("RGB", (cw, 34), PAPER); ImageDraw.Draw(head).text((2, 6), f"confidenceThreshold {threshold:g}", fill=INK, font=font(20))
        columns.append(stacked([np.asarray(head), column], gutter=0))
    save_avif(HERE / "visual" / "depth_confidence_coverage.avif", side_by_side(columns))


# ---------------------------------------------------------------- acoustic ---------------------
def scene_numbers(text, pattern, count):
    values = tuple(float(v) for v in re.search(pattern, text, re.S).group(1).split(","))
    assert len(values) == count, (pattern, values)
    return values


def acoustic_figure():
    """The acoustic example's echo envelope over a to-scale side view of its scene, on one range axis.

    One AVIF for the three pages that embed it. The scene is opened exactly as the example opens it,
    the envelope is read with the example's own reader, and the side view is drawn from the numbers in
    the scene file, so the wall stands where the scene puts it."""
    import importlib.util, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
    scene = EXAMPLES / "acoustic" / "acoustic_example.usda"; text = scene.read_text()
    spec = importlib.util.spec_from_file_location("acoustic_example_main", EXAMPLES / "acoustic" / "main.py")
    acoustic = importlib.util.module_from_spec(spec); spec.loader.exec_module(acoustic)
    # the geometry, from the scene: the sensor's height, the wall's near face and its top edge
    sensor = re.search(r'def OmniAcoustic "Acoustic".*?\n    \}', text, re.S).group(0)
    rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\(([^()]*)\)", re.search(r"xformOp:transform = \((.*)\)", sensor).group(1))]
    sensor_z = rows[3][2]                                                 # the translation row of the sensor's matrix
    wall = re.search(r'def Cube "ConcreteWall".*?\n    \}', text, re.S).group(0)
    size = float(re.search(r"double size = ([0-9.]+)", wall).group(1)) / 2
    sx, sy, sz = scene_numbers(wall, r"xformOp:scale = \((.*?)\)", 3); tx, ty, tz = scene_numbers(wall, r"xformOp:translate = \((.*?)\)", 3)
    wall_x0, wall_x1, wall_top = tx - size * sx, tx + size * sx, tz + size * sz
    # the envelope, read the way the example reads it: three warm-up steps, then the frame
    renderer, stage = session(scene); product = acoustic.RENDER_PRODUCT
    for _ in range(acoustic.WARMUP_STEPS): renderer.step(render_products={product}, delta_time=acoustic.STEP_DT_SECONDS, ordinal=1)
    products = renderer.step(render_products={product}, delta_time=acoustic.STEP_DT_SECONDS, ordinal=1)
    data = acoustic.read_acoustic_signal_ways(products[product].frames[0]); del products
    finish(renderer, stage)
    ranges = acoustic.sample_ranges_m(data); envelope = data["envelopes"][0]; peak = int(np.argmax(envelope)); x_max = float(ranges[-1])
    tx_id, rx_id, ch_id = (int(data[k][0]) for k in ("transmitter_ids", "receiver_ids", "channel_ids"))
    DK, GREY, MUTED, FAINT, PANEL, BLUE, GREEN = "#313131", "#757575", "#9A9A9A", "#C0C0C0", "#F2F2F2", "#0074DF", "#76B900"
    W, H = 1200, 760; left, width = 0.075, 0.905; z_lo, z_hi = -0.3, 1.36
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    view_h = (z_hi - z_lo) * (width * W / x_max) / H                      # the side view keeps meters square
    view = fig.add_axes((left, 0.085, width, view_h)); plot = fig.add_axes((left, 0.085 + view_h + 0.07, width, 0.925 - (0.085 + view_h + 0.07)))
    # the plot: one series, so no legend; the amplitude axis carries no numbers, the docs quote none
    plot.plot(ranges, envelope, color=BLUE, linewidth=2.0)
    plot.annotate(f"peak at {ranges[peak]:.2f} m", (ranges[peak], envelope[peak]), xytext=(12, -2), textcoords="offset points", fontsize=16, color=DK, va="top")
    plot.set_xlim(0, x_max); plot.set_ylim(0, envelope[peak] * 1.12); plot.set_yticks([]); plot.tick_params(axis="x", labelbottom=False, length=0)
    plot.set_ylabel("Amplitudes", fontsize=17, color=DK)
    plot.set_title(f"Echo envelope of the example's one signal way: transmitter {tx_id} to receiver {rx_id}, channel id {ch_id}", fontsize=17, color=DK, loc="left", pad=12)
    # the side view, on the same range axis
    view.set_xlim(0, x_max); view.set_ylim(z_lo, z_hi); view.set_aspect("equal", adjustable="box")
    view.add_patch(Rectangle((0, z_lo), x_max, -z_lo, facecolor=PANEL, edgecolor="none")); view.axhline(0, color=MUTED, linewidth=1.2)
    view.text(0.12, z_lo / 2, "asphalt ground plane", fontsize=15, color=GREY, va="center")
    view.add_patch(Rectangle((wall_x0, 0), wall_x1 - wall_x0, wall_top, facecolor=FAINT, edgecolor=DK, linewidth=1.2))
    view.text(wall_x1 + 0.12, wall_top - 0.12, "concrete wall", fontsize=15, color=DK, va="top")
    view.text(wall_x1 + 0.12, wall_top - 0.38, f"near face at {wall_x0:.1f} m", fontsize=15, color=GREY, va="top")
    view.text(wall_x1 + 0.12, wall_top - 0.62, f"{wall_top:.2f} m above the ground", fontsize=15, color=GREY, va="top")
    view.add_patch(Circle((0, sensor_z), 0.07, facecolor=GREEN, edgecolor=DK, linewidth=1.0, zorder=5, clip_on=False))
    view.text(0.14, sensor_z + 0.3, f"acoustic sensor, {sensor_z:.1f} m up, firing along +X", fontsize=15, color=DK, va="bottom")
    view.add_patch(FancyArrowPatch((0.1, sensor_z + 0.05), (wall_x0 - 0.03, sensor_z + 0.05), arrowstyle="-|>", mutation_scale=16, color=GREY, linewidth=1.5))
    view.add_patch(FancyArrowPatch((wall_x0 - 0.03, sensor_z - 0.09), (0.1, sensor_z - 0.09), arrowstyle="-|>", mutation_scale=16, color=GREY, linewidth=1.5, linestyle=(0, (4, 3))))
    view.text(wall_x0 / 2, sensor_z + 0.1, "pulse", fontsize=14, color=GREY, ha="center", va="bottom"); view.text(wall_x0 / 2, sensor_z - 0.14, "echo", fontsize=14, color=GREY, ha="center", va="top")
    view.set_xlabel("Range (m): each sample's round-trip time as a distance", fontsize=17, color=DK); view.set_ylabel("Height (m)", fontsize=17, color=DK)
    view.set_yticks([0, 0.5, 1.0]); view.tick_params(labelsize=15, colors=DK)
    for ax in (plot, view):
        ax.axvline(ranges[peak], color=MUTED, linewidth=1.2, zorder=0); ax.grid(axis="x", color="#E6E6E6", linewidth=0.8)
        for side in ("top", "right"): ax.spines[side].set_visible(False)
        for side in ("left", "bottom"): ax.spines[side].set_color(FAINT)
    fig.canvas.draw(); image = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(); plt.close(fig)
    save_avif(HERE / "nonvisual" / "acoustic_echo_envelope.avif", image)
    print(f"acoustic: {data['num_signal_ways']} signal way(s), {data['num_samples']} samples of {data['sample_duration_s'] * 1e6:.1f} us, "
          f"range axis to {x_max:.2f} m, peak sample {peak} at {ranges[peak]:.3f} m; wall face at {wall_x0:.2f} m, top {wall_top:.2f} m, sensor {sensor_z:.2f} m up")


def save_avif(path, image):
    Image.fromarray(image).save(path, quality=80, subsampling="4:4:4")
    print(f"{path.relative_to(HERE)}: {image.shape[1]} x {image.shape[0]}, {path.stat().st_size // 1024} KB")



# ---------------------------------------------------------------- radar hero still -----------
STILL_PANEL = (596, 400)        # each of the two panels; 8 px of white between them make 1200 px
STILL_GUTTER = 8
STILL_STEP = 6                  # the cube mid-field, at 24 m


def radar_still():
    """The hero still: the radar field scene's camera frame beside a top view of that step's detections."""
    scene = EXAMPLES / "radar" / "radar_example_field.usda"; radar_world = np.array([0.0, 0.0, 1.0])
    cam_rows, cam_fov = camera_from_scene(scene); walls = occluders_from_scene(scene)
    body = f'''over "World"
{{
    over "Render"
    {{
        over "Products"
        {{
            over "CameraProduct"
            {{
                int2 resolution = ({STILL_PANEL[0]}, {STILL_PANEL[1]})
            }}
        }}
    }}
}}
'''
    renderer, stage = session(overlay(scene, body, time_codes=10))
    radar_prod, radar_var = "/World/Render/Products/RadarProduct", "/World/Render/Vars/PointCloud"
    cam_prod, cam_var = "/World/Render/Products/CameraProduct", "/World/Render/Vars/LdrColor"
    ordinal = 2; ovstage.population.update_from_usd_time(stage, ordinal, 0.0); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(3): renderer.step(render_products={radar_prod, cam_prod}, delta_time=DT, ordinal=ordinal)
    for step in range(1, STILL_STEP + 1):
        ordinal += 1; ovstage.population.update_from_usd_time(stage, ordinal, step * DT); stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        products = renderer.step(render_products={radar_prod, cam_prod}, delta_time=DT, ordinal=ordinal)
        det = read_pointcloud(products[radar_prod].frames[0], radar_var, ["RadialVelocityMs"]); image = read_image(products[cam_prod].frames[-1], cam_var)[..., :3].copy(); del products
    finish(renderer, stage)
    v = det["RadialVelocityMs"]; closing = v[v < -0.5]
    label = f"step {STILL_STEP} of 10, t = {STILL_STEP * DT:.1f} s"
    left = annotate(mark_sensor(image, cam_rows, cam_fov, radar_world, walls, radius=5), label + ": camera view, the radar marked white")
    right = annotate(top_view(det["points"], velocity_colors(v), half_width=85.0, dot=4, size=STILL_PANEL), f"{len(v)} detections, top view, 10 m rings",
                     scale=(np.array(((30, 90, 255), (40, 220, 60), (255, 40, 30)), np.float32), f"-{VELOCITY_SCALE:.0f}", f"+{VELOCITY_SCALE:.0f}", "RadialVelocityMs, m/s"))
    w, h = STILL_PANEL; canvas = np.full((h, 2 * w + STILL_GUTTER, 3), 255, np.uint8); canvas[:, :w] = left; canvas[:, w + STILL_GUTTER:] = right
    save_avif(HERE / "nonvisual" / "radar_field_hero.avif", canvas); print(f"radar still: {len(v)} detections, {len(closing)} closing at {closing.min():.1f} m/s")


GROUPS = {"lidar": lidar_figures, "radar": radar_figures, "acoustic": acoustic_figure, "solid_state": lidar_solid_state_figure,
          "floor": lidar_floor_sweep_figure, "motion": lidar_motion_figure, "profiles": lidar_profiles_figure,
          "radar_detections": radar_detections_figure, "wpm_subsampling": wpm_subsampling_figure, "lidar_wpm": lidar_wpm_figure, "idealized_depth": idealized_depth_figure,
          "camera_core": camera_core_figures, "depth": depth_figures, "radar_still": radar_still}

if __name__ == "__main__":
    which = sys.argv[1:] or list(GROUPS)
    unknown = [w for w in which if w not in GROUPS]
    if unknown: raise SystemExit(f"unknown figure group(s) {unknown}; choose from {list(GROUPS)}")
    for name in which: GROUPS[name]()
