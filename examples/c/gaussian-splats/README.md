# gaussian-splats (C/C++)

Compare smoother Gaussians with non-stochastic RTPT rendering and relight the
cactus with `ParticleFieldSHDiffuse.mdl`.

The scene references [cactus-100.usdc](https://huggingface.co/buckets/nvidia/ovrtx-storage/resolve/cactus-100.usdc)
(a ParticleField containing 139,410 Gaussians), rotated 180 degrees around X and placed upright on the ground.
Internet access is required on first load.
Capture: [Steam Studio](https://www.steam-studio.jp), CC0-1.0;
[source dataset](https://note.com/steam_studio/n/ne9736d94f162).

Build this project with `cmake -B build` and `cmake --build build --config Release`.
The static-loader executable is in `build/static/Release/` on Windows and
`build/static/` on Linux. The shared-loader target adds `-dynamic` to the name.

Pass `../../python/gaussian-splats/gaussian_splats.usda` and an optional output PNG path.
Both loaders save the first frame without preceding warmup frames.

## Comparison images

Camera_close, RTPT first frame: non-stochastic off (left), on (right).
Matching crops enlarged 3× without smoothing.

![Non-stochastic comparison](../../../docs/img/gaussian-splats-non-stochastic.avif)

Camera, RTPT after 32 frames: default emissive (left), SH diffuse with normal tone mapping (right).

![Diffuse lighting comparison](../../../docs/img/gaussian-splats-sh-diffuse.avif)

## Scene variants

`non_stochastic.usda` and `stochastic.usda` use `Camera_close` for an on/off
comparison of non-stochastic compositing. `sh_diffuse.usda` uses `Camera`
to show scene lighting with `ParticleFieldSHDiffuse`. All share the same scene.

Pass `../../python/gaussian-splats/non_stochastic.usda` or
`../../python/gaussian-splats/sh_diffuse.usda` as the scene argument to either loader.
Both keep the existing output paths and default to RTPT.

Enable non-stochastic primary-ray compositing for emissive Gaussians. This reduces
transparency noise at a performance cost. It requires RTPT inline tracing and
disables adaptive disocclusion sampling.

```usda
over "Render" {
    over "Camera" {
        rel camera = </World/Camera_close>
        token omni:rtx:rendermode = "RealTimePathTracing"
        bool omni:rtx:rtpt:gaussian:nonStochastic:enabled = true
        # Adaptive disocclusion sampling would force stochastic rendering.
        bool omni:rtx:rtpt:adaptiveSampling:disocclusion:enabled = false
    }
}
```

ovrtx supplies `ParticleFieldSHDiffuse.mdl` with its runtime materials, at
`bin/mdl/ParticleFieldSHDiffuse.mdl` in the extracted SDK package. You do not need
to write an MDL material. See the [supplied source](../../../docs/_static/mdl/ParticleFieldSHDiffuse.mdl). The snippet below references and binds that supplied
material to the ParticleField so scene lights illuminate its Gaussians. Diffuse
albedo is derived from SH0. Captured lighting remains baked into SH0; transparency
remains stochastic.

```usda
over "World" {
    def Material "SHDiffuse" {
        token outputs:mdl:surface.connect = </World/SHDiffuse/Shader.outputs:out>
        def Shader "Shader" {
            uniform token info:implementationSource = "sourceAsset"
            uniform asset info:mdl:sourceAsset = @ParticleFieldSHDiffuse.mdl@
            uniform token info:mdl:sourceAsset:subIdentifier = "ParticleFieldSHDiffuse"
            token outputs:out (renderType = "material")
        }
    }
    over "Splats" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    ) {
        rel material:binding = </World/SHDiffuse>
    }
}
over "Render" {
    over "Camera" {
        # Render scene-lit color through the normal color pipeline.
        bool omni:rtx:gaussian:skipTonemapping:enabled = false
        bool omni:rtx:rtpt:gaussian:nonStochastic:enabled = false
    }
}
```
