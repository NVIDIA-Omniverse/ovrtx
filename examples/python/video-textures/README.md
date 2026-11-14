# Video Textures

This example maps a generated H.265/HEVC video onto geometry, selects four
video source times, and logs every rendered result to one Rerun recording. The
clip contains a visible stream timestamp and moving orange ball against a
dark-blue background, so frame-selection failures are easy to spot.

![Four rendered H.265 video-texture frames at different source times](../../../docs/img/video-textures.avif)

## Prerequisites

- Python 3.10-3.14
- [uv](https://docs.astral.sh/uv/)
- NVIDIA RTX-capable GPU and supported driver with H.265 decode support

GStreamer is only required to regenerate the committed sample clip. Run
`./generate_video.sh` with the `videotestsrc`, `timeoverlay`, `x265enc`,
`h265parse`, and `mp4mux` plugins installed.

## How it works

### 1. Assign the video to an OmniPBR material

The scene connects an OmniPBR shader to a material, assigns the H.265 file to
the shader's diffuse texture input, and adds playback controls for that input:

```usda
        def Material "VideoMaterial_0"
        {
            token outputs:surface.connect = <Shader.outputs:out>

            def Shader "Shader" (
                prepend apiSchemas = ["OmniPlaybackAPI:inputs:diffuse_texture"]
            )
            {
                uniform token info:implementationSource = "sourceAsset"
                uniform asset info:mdl:sourceAsset = @OmniPBR.mdl@
                uniform token info:mdl:sourceAsset:subIdentifier = "OmniPBR"

                asset inputs:diffuse_texture = @./video_texture_h265.mp4@ (
                    colorSpace = "sRGB"
                )
                color3f inputs:diffuse_color_constant = (1, 1, 1)
                float inputs:reflection_roughness_constant = 0.4

                uniform float inputs:omni:playback:inputs:diffuse_texture:rate = 1
                uniform double inputs:omni:playback:inputs:diffuse_texture:sourceStart = 0
                uniform double inputs:omni:playback:inputs:diffuse_texture:sourceEnd = 3.9
                uniform timecode inputs:omni:playback:inputs:diffuse_texture:playbackStart = 0
                uniform token inputs:omni:playback:inputs:diffuse_texture:before = "hold"
                uniform token inputs:omni:playback:inputs:diffuse_texture:after = "hold"

                token outputs:out (
                    renderType = "material"
                )
            }
        }
```

### 2. Bind the material to the screen

The screen mesh supplies UV coordinates for the video frame and binds the
video material with `MaterialBindingAPI`:

```usda
    def Mesh "Screen_0" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform bool doubleSided = false
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1.777778, -1, 0), (1.777778, -1, 0), (1.777778, 1, 0), (-1.777778, 1, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "faceVarying"
        )
        rel material:binding = </World/Looks/VideoMaterial_0>
        uniform token subdivisionScheme = "none"
    }
```

### 3. Select and render video timestamps

The scene has no animation range, so video selection uses the renderer's
simulation clock. The example resets that clock to zero once, then advances it
by the difference between each pair of requested source times. The results are
logged to Rerun:

```python
    # This stage has no animation range, so video selection uses simulation time.
    if not renderer.reset_async(time=0.0).wait(timeout_ns=VIDEO_TIMEOUT_NS):
        raise TimeoutError(f"reset did not complete within {VIDEO_TIMEOUT_SECONDS} s")
    current_time = 0.0
    for index, video_time in enumerate(times):
        # Advance from the preceding requested timestamp to this one.
        render_product = f"/Render/Camera_{index}"
        pending = renderer.step_async(
            render_products={render_product},
            delta_time=video_time - current_time,
            ordinal=ordinal,
        ).wait(timeout_ns=VIDEO_TIMEOUT_NS)
        products = pending.fetch(timeout_ns=VIDEO_TIMEOUT_NS) if pending else None
        if products is None:
            raise TimeoutError(
                f"{render_product} did not render video time {video_time:.1f} s "
                f"within {VIDEO_TIMEOUT_SECONDS} s"
            )
        current_time = video_time

        # Put the mapped LdrColor image at its source time on the Rerun timeline.
        image = _map_ldr_color(products, render_product)
        rendered_frames.append(image)
        if rr:
            rr.set_time("video_time", duration=video_time)
            rr.log("render/video_texture", rr.Image(image))
        del products
```

Each RenderProduct authors `omni:rtx:videostreamer:blocking = true`, so the
corresponding render waits for its requested decoded frame. The example bounds
each wait at 300 seconds, so a frame that never decodes raises `TimeoutError`
instead of hanging. After rendering,
the application checks every image for the background and timestamp, then
compares the moving ball's center with its expected position in the requested
10-FPS source frame. Consecutive requested times must be at least 0.1 seconds
apart so each render advances by at least one source frame.

## Running

```bash
uv run main.py
uv run main.py --rrd _output/video-textures.rrd --png _output/video-textures.png
uv run main.py --no-rr --png _output/video-textures.png
```

One invocation renders and validates every requested source time. Use
`--times` to choose one to four increasing points within the clip's
0.0-3.9 second range, with at least 0.1 seconds between consecutive values.
