# Selection SPG example

This example owns its viewer sources, shaders, CMake helpers, and scene assets.
Build `ovrtx-selection-spg` from this directory; do not include sources or build
files from another example. It presents only `/Render/Camera/CustomSelection`.
The viewer maps CUDA arrays, copies them to exported Vulkan images, and uses
timeline semaphores to synchronize presentation. Preserve that interop lifecycle.

Keep the `selectionOutline` entry point identical in the Slang source, adjacent Lua
launch script, and inline USD shader definition in `selection_scene.usda`. Keep
the SPG node definition and graph wiring together in that scene, without a separate
referenced shader USDA. Assets load directly from the source tree;
CMake records the default scene path in `OVRTX_SELECTION_SCENE`.
Do not stage editable assets in the build directory. The scene renders at 1920×1080.

`SelectionState` is RGBA16_UINT at output resolution. Channels are coverage samples;
bits 0–7 are group (zero is background), bit 8 means visible, and bits 9–15 are zero.
The renderer performs selection/visibility classification only. Every styling choice,
including width and shape, belongs to SPG. Same-group objects form one mask.
Visibility is traced along output-resolution selection rays.
The native overlay is suppressed for a RenderProduct requesting SelectionState.
Empty selections clear the output without tracing. The SPG shader skips empty tiles
using a shared occupancy check over the tile plus outline halo; all threads must
reach both barriers before out-of-image threads return. Its neighborhood search
loads four coverage channels together, preserving independent nearest seeds.

Keep README's coverage, visibility, and morphology limitations explicit. Runtime
validation should inspect visible/hidden edges, group colors, empty selections,
SPG width/shape changes, upscaling, and selection changes after the eco-mode idle limit.
