# Custom selection outlines through SPG

![Custom selection outlines and patterned fills on a sphere, torus, and cube](../../../img/example-selection-spg.avif)

This self-contained example presents renders in a Vulkan window using CUDA/Vulkan synchronization.
A Slang SPG node reads `LdrColor` and `SelectionState`, then publishes `CustomSelection`.
SPG owns outline width and shape, colors, dashes, group boundaries, opacity, and fill.
The renderer supplies classified coverage and does not draw its native overlay when
`SelectionState` is requested.

The sphere, torus, and cube start selected, with styles defined entirely in SPG:

| Object | Group | Default style |
|---|---|---|
| Sphere | 1 | Cyan, 6-pixel circular outline, translucent solid fill |
| Torus | 2 | Purple, 3-pixel square outline, no visible fill |
| Cube | 3 | Orange, 6-pixel diamond outline, diagonal striped fill |

Left click or drag replaces the selection while preserving each object's group.
Shift-click adds an object or removes it if already selected; Shift-clicking empty
background leaves the selection unchanged. Shift-drag still replaces the selection.
Drag with the right mouse button to orbit; use the wheel to dolly. Cube sits in front of Sphere.
Select only Sphere to see dashed hidden edges and stippled hidden fill:
when both are selected, only the nearest selected surface is represented.
The mesh assets, textured ground, and studio HDRI are bundled copies from
`tests/docs/data`; runtime asset paths stay inside the example.
Objects in the same group form one mask; different groups have white separators.

## Build and run

Requirements: CMake 3.18+, a C++17 compiler, an NVIDIA RTX-capable GPU with a
supported driver, CUDA Toolkit 12.0+, and Vulkan SDK 1.3.250+ (including `glslc`).
On Linux, install the development packages required by GLFW for your window system.

Configure this directory directly or through the parent C examples project.
The included CMake helpers find installed ovrtx and ovstage SDK packages through
`CMAKE_PREFIX_PATH`, or fetch the SDK packages when absent. CMake also fetches
GLFW when absent, plus GLM, volk, and unordered_dense. Dependency downloads require
internet access. Runtime loaders use the `ovrtx/` and `ovstage/` package links
created beside the executable by CMake.

```sh
cmake -S . -B _build -DCMAKE_BUILD_TYPE=Release
cmake --build _build
./_build/ovrtx-selection-spg
./_build/ovrtx-selection-spg --headless --num-frames 100
./_build/ovrtx-selection-spg --usd "$PWD/selection_pt.usda" --headless --num-frames 100
```

On Windows, build with `cmake --build _build --config Release` and run
`_build/Release/ovrtx-selection-spg.exe`.
Headless mode saves `out.png` with all three group styles.

The default scene is loaded directly from this source directory using a path
recorded by CMake. USD, Lua, and Slang assets are not copied into the build directory;
edits take effect on the next launch without rebuilding the viewer. The scene renders
at 1920×1080 independently of window size. Pass `--usd` to load another scene.

## AOV contract and customization

`SelectionState` is an output-resolution `RGBA16_UINT` image (8 bytes per pixel).
Its four channels are coverage samples, each with this layout:

| Bits | Meaning |
|---|---|
| 0–7 | Selection group (1–255); zero means no selected geometry |
| 8 | Selected sample is visible (1) or occluded (0) |
| 9–15 | Reserved, zero |

A background sample is zero. A hidden group-1 sample is `0x001`; a visible group-1
sample is `0x101`.
When nothing is selected, the renderer clears a valid output image and skips selection ray passes.

The native two-pass selection machinery traces at output resolution. It finds the
nearest selected surface through unselected geometry, then compares its identity
with a full-scene hit along the same unjittered camera ray. This adds a visibility
ray for each selected sample.
Both traces use selection's backface-culling and positive-opacity
surface policy, with camera visibility flags and camera/section clipping respected. Visibility is binary, not accumulated material/volume transmission.
Only the nearest selected surface is represented, including when other selected
surfaces lie behind it.

Uniform areas replicate their center result to all four channels; selected-instance
or visibility changes between neighboring centers trigger the native four sample
positions. This adaptive coverage can miss geometry/occluders thinner than the
center sampling pattern; it is not four independently traced samples at every pixel.
The positions relative to the pixel center are (-0.125, -0.375), (0.375, -0.125),
(-0.375, 0.125), and (0.125, 0.375), in channel order.

The SPG example expands the selection mask by screen distance. Set `inputs:width`
to 0–32 for the maximum radius; group 2 uses half (at least one pixel when enabled).
`inputs:shape` selects the base shape: 0 (circle), 1 (square), or 2 (diamond).
Groups 2 and 3 rotate through that sequence by one and two positions respectively.
`inputs:dashPeriod` controls
hidden strokes and `inputs:fillAlpha` controls visible solid/striped fill.
Edit `groupColor()` for a different palette and the shader's group branches for
other width, shape, and fill profiles.
Hidden interiors use cyan dots for group 1, purple cross-hatching for group 2,
and orange single-direction hatching for group 3.
`inputs:hatchSpacing` sets the pattern period in pixels (default 12);
`inputs:hatchLineWidth` sets the dot radius or hatch thickness (default 1).
`inputs:hiddenFillAlpha` sets opacity
(default 0.35; zero disables hidden fill). Spacing is clamped to 1–4096 and line
width to 0–spacing. The pattern stays fixed in screen space as the camera moves.
Width zero disables edges and separators while retaining both kinds of fill.
The four samples are composited independently and averaged. A shared tile/halo
occupancy check skips empty regions. One neighborhood walk reads all four coverage
channels together, as does the group-separator search; populated regions still have
quadratic search cost in outline width.

Expanded strokes inherit the selected seed's visibility. They do not query depth
under the expanded stroke, so a thin foreground surface covering only the stroke
does not change its visibility. Overlapping strokes choose the nearest screen-space
seed with deterministic ties, rather than the frontmost depth. Objects sharing a
group have no separately identifiable boundary in this AOV.

The `selectionOutline` entry point matches in `SelectionOutline.slang`, its
adjacent `.slang.lua` launch script, and the inline Shader definition in
`selection_scene.usda`. That scene contains the complete SPG definition and graph
wiring; `selection_pt.usda` changes only the mode to PT.
The selection pass runs even when RTPT reuses its beauty image in eco mode.

`SelectionState` does not support XR foveation unwarp. When unwarp is authored,
the renderer clears this AOV and logs a warning; beauty output continues normally.
Disable unwarp to read selection in warped coordinates.

## Licensing

This example includes stb_image_write.h by Sean Barrett, released into the public domain.
