# Sensor documentation images

Figures for the ovrtx sensor documentation, one subdirectory per documentation
area (`overview/`, `common/`, `camera/`, `visual/`, `nonvisual/`, `lidar/`;
the first five follow the doc tree, `lidar/` holds the data-sheet and manual scans the
lidar tutorials use; `scenes/` holds the scene files authored for figures alone, which
`_render_example_scenes.py` opens like the shipped examples). Two kinds of file live here:

- **Raster images** (renders, screenshots, scans of data sheets) are committed
  as AVIF at quality 80. Convert with
  `node -e "require('sharp')('x.png').avif({quality:80}).toFile('x.avif')"`.
  Animated content stays GIF. `camera/camera_outputs_hero.avif` is a two-by-two
  composite of `img/aovs/rt2/{LdrColor,NormalSD,DistanceToCameraSD,SemanticSegmentation}.avif`
  (each tile 640 x 360, 8 px white gutter), assembled with sharp's `composite()`.
  `overview/hero_four_sensors.avif` is a two-by-two composite (each tile 960 x 540, 8 px
  white gutter, a label in the corner of each tile) of four sensor views captured at one
  moment from one robot of a robotics-lab demonstration scene that is not among the examples:
  a camera's `LdrColor`, a 200-degree F-theta fisheye camera's `LdrColor`, the
  `DepthSensorDistance` image of a Camera single-view stereo depth model on a fixed 0.3 m
  (blue) to 10 m (red) scale, and the `PointCloud` of a 128-channel rotary Lidar generic core
  model shaded by `Intensity` with the color ramp of `_render_example_scenes.py`, projected
  from behind and above the sensor. The tiles are the demonstration's own rendered
  1920 x 1080 views downscaled by two; the composite and its labels were assembled with sharp.
- **Diagrams** are SVG, and are never hand-edited: every SVG is written by the
  generator of its area.

The Output Configuration diagram is `common/output_configuration.svg`, generated
by `common/_gen_output_configuration.py`. It shows camera and lidar requests,
USD relationship directions, and returned tensors keyed by RenderVar paths.

## One generator per area

Each area directory holds one `generate_diagrams.py`, the entry point that
writes *every* SVG in that directory and nothing else. The drawings themselves
live in `_gen_<group>.py` modules beside it, one per topic group (for example
`_gen_lidar_core_a.py`, `_gen_radar_b.py`), each exposing
`generate(out_dir)` and runnable on its own (`python3 -B _gen_<group>.py`)
while the rest of the directory is untouched. The entry point imports the
modules in name order and runs them. All of them import the shared helper
module `_diagram_lib.py` from this directory (palette, font stack, `Canvas`,
`box`/`arrow`/`curve`/`lane`/`legend`, the overlap and canvas-edge checks), so all sensor figures share one look. Stdlib only; no
plotting library, no build step. Run Python with `-B` here so no
`__pycache__` is written next to the images (the directory's `.gitignore`
covers it anyway).

Regenerate in place:

```bash
cd rendering/ovrtx/public/docs/img/sensors/<area>
python3 -B generate_diagrams.py
```

Generation is byte-for-byte reproducible (no timestamps, no randomness, fixed
number formatting). Verify after a change:

```bash
python3 -B generate_diagrams.py /tmp/check && diff -q . /tmp/check --exclude='*.py' --exclude='*.avif' --exclude='*.gif' --exclude='*.md' --exclude='.gitignore'
```

Every figure function calls `dl.validate(c)` before `dl.write_svg(...)`: it
raises if two labels overlap (or touch) or if any text comes within 8 px of the
canvas edge. Looking at the rasterized result is still required.

## Look at the result

An SVG cannot be reviewed by reading it. Rasterize it with the `sharp`
package (`npm install sharp`, then point `NODE_PATH` at that `node_modules`)
and open the PNG:

```bash
NODE_PATH=/path/to/node_modules node -e "require('sharp')('x.svg',{density:150}).png().toFile('x.png')"
```

(`density` is relative to 72 dpi, so 150 gives a PNG about twice the SVG's
nominal pixel size.)

`python3 -B -c "import _diagram_lib as dl; print(dl.rasterize_hint('x.svg', 'x.png'))"`
prints that command with the install location filled in: `$DIAGRAM_SHARP_NODE_MODULES`
if set, else the first of a `node_modules` in the current directory and the global
`npm root -g` that holds `sharp`. If none does, it prints the `npm install sharp` step
instead.

## Rendering the example-scene figures

`_render_example_scenes.py` renders the figures that come from the shipped example scenes, with
the ovrtx and ovstage the pages describe:

- the animated figures of the two alternative example scenes
  (`examples/python/lidar/lidar_example_panels.usda` and
  `examples/python/radar/radar_example_field.usda`): the circling camera and point-cloud views on
  Your First Lidar Sensor (`overview/first_sensor_panels_*.gif`) and the radar field's camera and top
  views (`nonvisual/radar_field_*.gif`);
- `nonvisual/acoustic_echo_envelope.avif`: the acoustic example's echo envelope over a to-scale
  side view of its scene (`examples/python/acoustic/acoustic_example.usda`) on one range axis. The
  scene is opened as the example opens it and read with the example's own reader; the side view
  is drawn from the numbers in the scene file;
- `nonvisual/lidar_core_solid_state_scan.avif`: the lidar example scene
  (`examples/python/lidar/lidar_example.usda`) scanned by a solid-state sensor the script defines
  on the example's mount, a forward-facing half-degree grid with the detection floor off and one
  return per firing, from the viewpoint of the hub's rotary figure;
- `nonvisual/lidar_core_intensity_floor_sweep.avif`: the lidar example's own sensor beside a copy
  of it with `minReflectance` raised to 0.5, one scan each from the same step, from the hub
  figure's viewpoint;
- `nonvisual/lidar_sweep_compensated_vs_noncompensated.avif`: the panel scene's lidar moving
  forward at 8 m/s (a time-sampled translation the overlay adds, USD time advanced every step)
  beside a second sensor with the same motion asking for `COMPENSATED` output, one sweep each from
  the same step, seen from above and colored by `TimeOffsetNs`;
- `nonvisual/lidar_core_tutorial_profiles.avif`: the three tutorial layers under
  `docs/sensors/nonvisual/lidar_core/tutorials/assets/` referenced onto the panel scene's mount
  with their detection floor off, one scan each, shaded by `Intensity` relative to each scan's
  maximum, one panel below the other;
- `nonvisual/radar_example_velocity_and_rcs.avif`: the radar example scene as the C example ships
  it (`examples/c/radar/radar_example.usda`, the copy that requests `RCS`) on step 5 of the
  example's run, top views colored by `RadialVelocityMs` with the Python example's own mapping and
  by `RCS` over the frame's range;
- `nonvisual/lidar_wpm_tiled_subsampling_density.avif`: the lidar example's cube scene swept by a
  rotary Lidar generic wpm model sensor the script defines, at `tiledSubSampling` 1 and 4 in one
  step, colored by `Intensity`, from the hub figure's viewpoint;
- `visual/visual_sensors_strip.avif`: retained camera-output comparison. This image is
  an explicit exception to the shipped-example/test reproduction requirement.
  Keep its existing pixels and panel descriptions; no reproduction example is shipped.
- `visual/camera_core_hdr_raw_isp_comparison.avif`,
  `visual/camera_core_same_frame_four_taps.avif` and `visual/camera_core_aov_strip.avif`: one frame
  of the Camera generic core model's example scene
  (a Cornell box scene that is not among the shipped examples) with the Camera single-view stereo depth model
  on a second camera at the same pose with a product of its own, both added by the overlay since a
  camera carries one sensor model, read after ten warm-up steps. The floating-point and
  sensor-code images are scaled for display (white at the frame's 99.5th-percentile luminance, the
  two mosaics on one gray scale, the companded RAW codes linear in their 16-bit integer format, the AYUV
  result as its luma); crops are magnified pixel for pixel;
- `visual/depth_camera_beauty_shot.avif`, `visual/depth_camera_cornell_outputs.avif` and
  `visual/depth_confidence_coverage.avif`: the fisheye depth product of the Cornell box test scene
  (not among the shipped examples),
  read after the depth example's 64 warm-up steps; the coverage figure reruns it under overlays that
  set `confidenceThreshold` 0.5 and 0.99 with `rgbDepthOutputMode` 6. Every panel is the lens's
  image area cut from the frame; the distance images use one gray scale, near bright, zero black;
- `nonvisual/lidar_wpm_glass_retroreflective_scan.avif`: one scan of the Lidar generic wpm model
  sensor of `scenes/lidar_wpm_bus_shelter.usda`, a street scene with a glass bus shelter authored for
  this figure, since no shipped example carries a sensor of this model, colored by `Intensity` on a
  square-root scale, with a camera inset of the same view.
- `nonvisual/idealized_depth_point_cloud.avif`: one frame of the Idealized depth model sensor of
  `scenes/idealized_depth_plane_cube.usda`, a ground plane and one cube scanned
  with the schema's default emitter set, every hit a point colored by its distance. The model's
  output buffer is one the shipped host does not deliver; the figure was read through a build of
  this branch with that delivery enabled, and is to be re-rendered from the model's composite
  output when it exists;
- `nonvisual/radar_field_hero.avif`: step 6 of the radar example's run on its alternative scene
  (`radar_example_field.usda`), the preview camera's frame with the radar marked white beside a top
  view of that step's detections colored by `RadialVelocityMs` over 10 m rings; the radar figure of
  the Sensors overview's non-visual strip, the Non-Visual Sensors hub and the radar
  overview;

It opens the shipped scenes, and the scene under `scenes/`, the way the examples do and adds a temporary overlay with what each
figure needs: the camera animation and render resolution of the animated figures, and the sensors, RenderProducts and attribute
values the bullets above name for the comparison figures. The scene files stay the single source. Render
with the ovrtx build the pages describe, never an older release: the Python sources of ovrtx
(`python/` under `rendering/ovrtx/public`) and ovstage (`public/python` in the ovstage tree) as
editable packages over the native libraries of that same build, the directory holding
`libovrtx-dynamic.so` and `libovstage.so`. It needs a GPU; run it from `rendering/ovrtx/public`
after a change to a scene or to the build:

```bash
OVRTX_BIN=../../_build/linux-x86_64/release
LD_LIBRARY_PATH="$OVRTX_BIN:$OVRTX_BIN/plugins/omni.usd_mdl" OVSTAGE_LIBRARY_PATH_HINT="$OVRTX_BIN" \
uv run --no-project --with numpy --with pillow --with matplotlib \
  --with-editable python --with-editable ../../ovstage/public/python \
  python docs/img/sensors/_render_example_scenes.py [group ...]
```

The groups are `lidar`, `radar`, `acoustic`, `solid_state`, `floor`, `motion`, `profiles`,
`radar_detections`, `wpm_subsampling`, `lidar_wpm`, `idealized_depth`, `camera_core`, `depth` and `radar_still`; without
arguments the script renders them all.

These are renders, not diagrams: the reproducibility diff above excludes them.

The output gallery of the camera Outputs page, `docs/img/aovs/{rt2,pt,minimal}/`, is not written by
this script: it holds the semantic-segmentation example's own headless captures
(`examples/python/semantic-segmentation/README.md`, run with `--no-spawn`: Real-Time Path Tracing
after 50 warm-up frames, Path Tracing at 960 × 540 and 128 samples per pixel, Minimal at 960 × 540).
The two `StableIdMap` illustrations of the Real-Time Path Tracing and Path Tracing tabs come from
those commands run against this branch's build (`_output/StableIdMap.png` and
`_output/pt/StableIdMap.png`), encoded as AVIF like every raster figure here. Three more images
were re-captured from this branch's build on the author's ruling: `aovs/pt/PtPreDenoisedResult.avif`
(the example as shipped), `debug-views/depth.avif` (the debug-views example with
`float omni:rtx:debug:view:scaling = 0.005` authored on the depth product) and
`debug-views/stableId.avif` (the same example with a `StableIdSegmentation` RenderVar added to the
product), as their rows say.

## Calibration input contact sheet

`camera/calibration-inputs.avif` shows the shipped camera-calibration photographs.
From the repository root, hydrate the input images and run the standalone builder:

```sh
git lfs pull -I "rendering/ovrtx/public/examples/python/camera-calibration/input_images/**"
uv run --script rendering/ovrtx/public/docs/img/sensors/camera/build_calibration_contact_sheet.py
```

The script uses its PEP 723 Pillow dependency and writes AVIF at quality 80,
4:4:4 chroma. It is independent of the standard-library SVG generators.
