# AGENTS.md - AI Agent Guide for ovrtx

This file gives AI coding agents the minimum context needed to work effectively in this repository. Use it as a starting map, then go to `skills/` for task-level implementation guidance.

## What This Repo Is

`ovrtx` is a pre-release NVIDIA SDK that exposes Omniverse RTX through:
- a Python package (`python/ovrtx/`)
- a C API (documented in `docs/c_api/`)
- runnable examples in both Python and C (`examples/`)

Primary use case: OpenUSD-based sensor simulation and rendering workflows (camera, lidar, radar, etc.).

## Relationship to ovstage

Starting with **ovrtx 0.4**, ovrtx can integrate with **ovstage** — an optional
NVIDIA library that owns the runtime scene, ordinal-keyed writes, and change
detection. When both libraries are used together:

- **ovstage** is authoritative for: scene data, path dictionary, prim attributes,
  cloning, stage queries, ordinals, and write-floor gates.
- **ovrtx** is authoritative for: rendering, sensor simulation, GPU resources,
  RenderProducts, and sensor outputs.

ovrtx can operate in **standalone compatibility mode** (the renderer-owned scene
APIs are deprecated in 0.4) or **attached mode** (renders scene state from an
external ovstage instance). Scene ownership transitions entirely to ovstage in a
future release.

Skills that touch ovstage concepts (cloning, attributes, queries, stage loading)
should cross-reference ovstage as authoritative for scene-data behavior. When
working in an attached-mode context, also pull ovstage's agent context — its
`AGENTS.md`.

Key docs: `docs/core/ovstage_integration.rst` (attachment, ordinals, update
loop), `CHANGELOG.md` §0.4.

The public C examples consume ovstage as its own independent package, symmetric
with ovrtx. Both packages expose a static loader (model #1) and a shared loader
(model #2). The operating system loads only the shared forwarding loader in
model #2; both models open the OpenUSD-dependent runtime on the first
initialization call. `examples/c/minimal/` builds both combinations from the same
source and calls `ovrtx_register_schema_paths()` before either runtime can load
OpenUSD. Keep ovrtx and ovstage on the same release train, and keep
`examples/c/cmake/{ovrtx,ovstage}.cmake` synchronized with package layout changes.

For codebases still on ovrtx 0.3 that need to move to ovrtx 0.4 + ovstage 0.1
(the first release where attached mode became the primary user-facing
workflow), use [`update-0_3-0_4-c`](skills/update-0_3-0_4-c/SKILL.md) for C/C++
codebase and [`update-0_3-0_4-python`](skills/update-0_3-0_4-python/SKILL.md) for Python codebases.

For existing Python or C/C++ applications moving from ovrtx 0.4.x to 0.5.x,
use [`update-0-4-to-0-5`](skills/update-0-4-to-0-5/SKILL.md). It covers the 0.5
RenderVar/DLPack/API migrations, sensor asset changes, and the paired ovstage
0.1 to 0.2 data-contract changes that can affect an attached application.

## Start Here

- Read `README.md` for top-level product context and quick starts.
- Read `examples/README.md` to choose a runnable reference project.
- Read `skills/README.md` to understand the skill format and maintenance expectations.

## Repo Layout (High-Level)

- `python/ovrtx/` - Python package source
- `tests/` - Python test suite (pytest)
- `examples/python/` - Python example projects (see `examples/README.md` for the full list)
- `examples/c/` - C/C++ example projects (see `examples/README.md` for the full list)
- `skills/` - Task-oriented agent skills (`*/SKILL.md`)
- `docs/` - Sphinx docs, including Python/C getting started and API reference scaffolding

## Common Workflows

### Runtime Validation

OVRTX runtime validation requires an NVIDIA RTX-capable GPU, a supported NVIDIA driver listed in `docs/driver_requirements.rst`, internet access for examples that load remote S3 assets, and execution outside sandboxed environments. Do not claim runtime validation from parse-only checks, docs-only checks, or execution on a host without those prerequisites. If a prerequisite is missing, report the missing prerequisite instead of editing around it. If remote USD/S3 loading fails, treat it as an environment/network blocker unless the same URL is reachable outside ovrtx; report internet, proxy, firewall, or asset-access issues explicitly.

Use this validation scope when reporting results:

| Check | RTX GPU + supported driver | Unsandboxed execution | Internet access | Proves ovrtx runtime |
|-------|----------------------------|-----------------------|-----------------|----------------------|
| Sphinx/docs build | No | No | Maybe, for dependency install | No |
| Static USD/docs checks | No | No | Maybe, for dependency install | No |
| Python minimal example with `--png` | Yes | Yes | Yes, for remote S3 assets | Yes |
| C minimal example | Yes | Yes | Yes, for package and remote assets | Yes |
| Python/C runtime docs tests | Yes | Yes | Depends on assets under test | Yes |

Start with the Python minimal example:

```bash
cd examples/python/minimal
uv run main.py --png
```

Success means `_output/render.png` exists and matches the documented minimal reference image. The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.

Then validate the C minimal example when C coverage is relevant.

Linux:

```bash
cd examples/c/minimal
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/static/minimal
```

Windows:

```powershell
cd examples/c/minimal
cmake -B build
cmake --build build --config Release
.\build\static\Release\minimal.exe
```

Success means `out.png` exists and matches the documented minimal reference image.

### Python (recommended via uv)

- Use Python 3.10-3.13.
- Run example:
  - `cd examples/python/minimal`
  - `uv run main.py --png`

### C/C++ (CMake)

- Build example:
  - `cd examples/c/minimal`
  - `cmake -B build -DCMAKE_BUILD_TYPE=Release`
  - `cmake --build build`
- Run binary on Linux:
  - `./build/static/minimal`

### Tests

- Python tests live under `tests/`.
- If working on Python bindings/API behavior, run targeted tests first, then broader suites as needed.


## Use Skills for Task-Specific Work

When a request maps to a known ovrtx workflow, go directly to the relevant skill in `skills/`:

- Renderer setup/init -> `skills/renderer-creation/SKILL.md`
- Scene/stage loading (USD) -> `skills/loading-usd/SKILL.md`
- Step loop and frame rendering -> `skills/stepping-and-rendering/SKILL.md`
- Reading rendered outputs -> `skills/reading-render-output/SKILL.md`
- Reading prim attributes -> `skills/reading-attributes/SKILL.md`
- RenderProduct GPU device selection -> `skills/render-product-device-pinning/SKILL.md`
- Viewport picking and selection outlines -> `skills/picking-selection/SKILL.md`
- Configuring lidar sensors -> `skills/configuring-lidar-sensors/SKILL.md`
- Configuring radar sensors -> `skills/configuring-radar-sensors/SKILL.md`
- Nonvisual materials -> `skills/nonvisual-materials/SKILL.md`
- Reading sensor pointclouds -> `skills/reading-sensor-pointclouds/SKILL.md`
- Interpreting lidar pointclouds -> `skills/interpreting-lidar-pointclouds/SKILL.md`
- Interpreting radar pointclouds -> `skills/interpreting-radar-pointclouds/SKILL.md`
- Available camera outputs (RT2) -> `skills/camera-outputs-rt2/SKILL.md`
- Writing attributes -> `skills/writing-attributes/SKILL.md`
- Writing transforms -> `skills/writing-transforms/SKILL.md`
- Semantic labels -> `skills/semantic-labels/SKILL.md`
- Binding materials -> `skills/binding-materials/SKILL.md`
- Render settings -> `skills/render-settings/SKILL.md`
- Mapping attributes/bindings -> `skills/mapping-attributes/SKILL.md`, `skills/attribute-bindings/SKILL.md`
- Async operations -> `skills/async-operations/SKILL.md`
- Status/progress queries -> `skills/status-queries/SKILL.md`
- Runtime stage queries -> `skills/stage-queries/SKILL.md`
- Cloning prims -> `skills/cloning-prims/SKILL.md`
- Warmup/image quality -> `skills/warmup/SKILL.md`
- Sequential crop rendering and stitching -> `skills/sliced-rendering/SKILL.md`
- C project bootstrapping -> `skills/project-setup-c/SKILL.md`
- Python project bootstrapping -> `skills/project-setup-python/SKILL.md`
- CUDA interop -> `skills/cuda-interop/SKILL.md`
- Sensor Processing Graphs (SPG): running your own CUDA or Slang code over render outputs -> `skills/spg/SKILL.md`
- App-level lifecycle and ordering -> `skills/application-flow/SKILL.md`
- Error/reporting patterns -> `skills/error-handling/SKILL.md`
- String handling (ovx_string_t) -> `skills/string-handling/SKILL.md`
- 0.2 to 0.3 project upgrades -> `skills/update-0_2-0_3/SKILL.md`
- 0.3 to 0.4 (+ ovstage 0.1) migration for C codebases -> `skills/update-0_3-0_4-c/SKILL.md`
- 0.3 to 0.4 (+ ovstage 0.1) migration for Python codebases -> `skills/update-0_3-0_4-python/SKILL.md`
- 0.4 to 0.5 migration for Python and C/C++ codebases -> `skills/update-0-4-to-0-5/SKILL.md`

If multiple skills seem relevant, start with `skills/application-flow/SKILL.md`, then layer in specialized skills.

## Agent Expectations

- Prefer small, targeted edits over broad refactors unless requested.
- Keep examples and skills in sync with API behavior changes.
- If you change conventions or introduce a new repeated workflow, add/update the corresponding skill under `skills/`.
- Preserve licensing headers and proprietary notices where present.
- When a `SKILL.md` references code via `> **Source:** ...`, read the snippet markers in the referenced file to get the current code. Do not rely on stale inline examples.

### Snippet and skill rules

These rules are mandatory. Test/example code is the single source of truth; skills and docs reference it — never the other way around.

- **Adding tests or examples:** Wrap every illustrative code path in `# [snippet:name]` / `# [/snippet:name]` markers (Python) or `// [snippet:...]` (C/C++). Names are kebab-case and unique within the file. If the new code demonstrates a workflow that maps to an existing skill, add a `> **Source:**` reference in that skill. If no matching skill exists, consider creating one under `skills/`.
- **Modifying tests or examples:** Preserve existing snippet markers. If you move or restructure marked code, update the markers to stay around the illustrative section. Do not remove markers without also removing or updating every reference to them in `skills/` and `docs/`.
- **Adding skills:** Every code example in a `SKILL.md` must come from a snippet marker in a test or example file — never write inline code blocks for API usage. If no suitable snippet exists, first add a focused test function (in `tests/test_ovrtx.py`) or example code with markers, then reference it from the skill. See `skills/README.md` for the full format.

## Notes

- The project is pre-release; behavior, APIs, and packaging details may evolve.
