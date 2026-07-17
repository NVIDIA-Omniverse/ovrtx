# ovrtx Examples

This directory contains example projects demonstrating various features of ovrtx.

## Example Projects


<table>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-minimal.jpg" alt="Minimal Example" width="100%">
      <br>
      <b>Minimal</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create the smallest useful ovrtx example that loads an existing USD scene, renders one camera frame, maps the color output, and saves or displays the result while cleaning up resources appropriately.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/minimal/">C →</a>, <a href="python/minimal/">Python →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-minimal.jpg" alt="Status Queries Example" width="100%">
      <br>
      <b>Status Queries</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create a rendering example that demonstrates operation status queries, including logging, asynchronous scene loading, progress and counter polling while waiting, shader warmup feedback, final frame rendering, output handling, and error checks.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/status-queries/">C →</a>, <a href="python/status-queries/">Python →</a></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-vulkan-interop.gif" alt="Vulkan Interop Example" width="100%">
      <br>
      <b>Vulkan Interop</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create a C++ interactive viewer that renders ovrtx camera output directly into a Vulkan presentation path through CUDA interop, with GPU selection, GPU image mapping, exported-image copies, explicit synchronization, double buffering, orbit camera controls, finite-frame capture, and click or marquee picking with selection outlines.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/vulkan-interop/">C →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-planet-system.jpg" alt="Planet System Example" width="100%">
      <br>
      <b>Planet System</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create an animation example that loads a base scene, injects generated runtime geometry, creates persistent transform bindings, updates many transforms efficiently each simulation step using CPU or GPU compute, renders frames, optionally streams or saves them, and cleans up bindings explicitly.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/planet-system/">Python →</a></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-tiled-rendering.avif" alt="Tiled Rendering Example" width="100%">
      <br>
      <b>Tiled Rendering</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create an example that composes multiple referenced scene instances into a grid, assigns per-instance visual variation at runtime, renders all cameras through one tiled output, warms up for image quality, and saves or displays the final tiled image.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/tiled-rendering/">Python →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-semantic-segmentation.avif" alt="Semantic Segmentation Example" width="100%">
      <br>
      <b>Semantic Segmentation</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create an example that composes an existing scene with semantic label overrides and camera annotation outputs, renders several camera AOVs including semantic segmentation and its ID map, decodes metadata into human-readable labels, logs a useful visual layout to a viewer, and supports headless image export.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/semantic-segmentation/">Python →</a></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-sensor-lidar.avif" alt="Lidar Sensor Example" width="100%">
      <br>
      <b>Lidar Sensor</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create a lidar sensor example that applies required sensor runtime settings as needed, loads a configured lidar scene, warms up the sensor pipeline, renders one point-cloud output, reads valid point data safely through the count channel, prints summary statistics, and cleans up resources appropriately.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/sensors/lidar/">C →</a>, <a href="python/sensors/lidar/">Python →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-sensor-radar.avif" alt="Radar Sensor Example" width="100%">
      <br>
      <b>Radar Sensor</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create a radar sensor example that applies required runtime settings as needed, loads an animated radar scene, advances scene time across several simulation steps, reads valid detections including signal strength and signed radial velocity, prints per-step summaries, and cleans up resources appropriately.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/sensors/radar/">C →</a>, <a href="python/sensors/radar/">Python →</a></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-material-editor.avif" alt="Material Editor Example" width="100%">
      <br>
      <b>Material Editor</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create a C++ Qt desktop application that combines live ovrtx rendering with read-only USD material introspection, showing materials, a rendered viewport, a shader graph, and editable shader properties, while keeping runtime material edits and rendering resets separate from introspection.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="c/material-editor/">C →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-spg-grayscale.png" alt="SPG Grayscale Example" width="100%">
      <br>
      <b>SPG: Grayscale</b>
      <br>
      <blockquote>
        <p align="left"><em>“Create the smallest useful SPG example: a CUDA kernel that converts the LdrColor render output to grayscale, wired into a RenderProduct and read back from Python as a new AOV.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/spg-grayscale/">Python →</a></sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%">
      <img src="../img/example-spg-pipeline.png" alt="SPG Pipeline Example" width="100%">
      <br>
      <b>SPG: Pipeline</b>
      <br>
      <blockquote>
        <p align="left"><em>“Chain two SPG shaders so the renderer's color output is converted to grayscale and then inverted in a single RenderProduct, reading back only the final result.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/spg-pipeline/">Python →</a></sub>
    </td>
    <td align="center" width="50%">
      <img src="../img/example-spg-builtin-nodes.png" alt="SPG Built-in Nodes Example" width="100%">
      <br>
      <b>SPG: Built-in Nodes</b>
      <br>
      <blockquote>
        <p align="left"><em>“Chain two built-in SPG nodes (no custom CUDA) that brighten the color output and downscale it to half resolution, wired into a RenderProduct via info:id.”</em></p>
      </blockquote>
      <sub>Build &amp; run in: <a href="python/spg-builtin-nodes/">Python →</a></sub>
    </td>
  </tr>
</table>
