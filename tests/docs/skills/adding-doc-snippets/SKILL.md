---
name: adding-doc-snippets
description: Adding new tested code snippets for documentation pages. Use when adding code examples to RST docs, creating new doc pages, or migrating inline code blocks to tested snippets.
---

# Adding Doc Snippets

## Overview

Every substantial code example in the ovrtx docs must be backed by a tested snippet. This skill walks through the full workflow from writing the test to wiring up the RST.

## Step 1: Decide where the test goes

| Code type | Test file location | Why |
|-----------|-------------------|-----|
| ovrtx Python API | `tests/docs/python/test_<doc_page>.py` | Needs `ovrtx` package, GPU to run |
| USDA examples | `tests/docs/usd/data/<name>.usda` (data) + `tests/docs/usd/test_*_usda.py` (validation) | Needs `usd-core` to validate |
| USD Python API | `tests/docs/usd/test_usd_python_examples.py` | Needs `usd-core`, no GPU |
| ovrtx C API | `tests/docs/c/test_<doc_page>.cpp` | Needs ovrtx C API, CMake, GoogleTest, GPU |

Keep `usd-core` imports in `tests/docs/usd/` unless a snippet explicitly needs to demonstrate OpenUSD interop with ovrtx; this keeps the ovrtx runtime tests from picking up docs-only USD dependencies.

## Step 2: Write the test with snippet markers

### For ovrtx Python snippets

Create or edit a test file in `tests/docs/python/`. The test function handles setup (loading scenes, warm-up steps), and the snippet markers wrap only the code the reader should see:

```python
@pytest.mark.usd_scene("simple_camera.usda")
def test_my_feature(renderer, stage, usd_scene):
    """Test description matching the doc section."""
    # Setup -- not in snippet
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, _make_scene(str(usd_scene)), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(5):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1/60, ordinal=ordinal)

    # [snippet:doc-my-feature]
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    for product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
            pixels = np.from_dlpack(var)
            assert pixels.shape[2] == 4
    # [/snippet:doc-my-feature]
```

Key points:
- Snippet markers wrap **only the doc-visible code** -- setup and assertions stay outside.
- Use `ovrtx.Device.CPU` (not `Device.CPU` or `"cpu"`) so the snippet is self-explanatory without a visible import.
- Scene loading uses the sublayer pattern (see `skills/sublayer-test-scenes/SKILL.md`).

### Deprecated API transition

New tests and snippets always use attached ovstage. The
`@pytest.mark.allow_deprecated_ovrtx_api` marker is reserved for retained tests
whose subject is the deprecated renderer-owned API contract. Never add
`filterwarnings`; unsuppressed deprecations remain visible in the suite's
ovstage migration summary.

### For USDA data files

Create a `.usda` file in `tests/docs/usd/data/` with snippet markers using `#` comments:

```usda
#usda 1.0

# [snippet:doc-my-render-product]
def "Render" {
    def RenderProduct "Camera" {
        rel camera = </World/Camera>
        rel orderedVars = [<LdrColor>]

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
    }
}
# [/snippet:doc-my-render-product]
```

Then add a validation test in `tests/docs/usd/test_*_usda.py`:

```python
def test_my_render_product():
    usda_text = (DATA_DIR / "my_file.usda").read_text()
    layer = validate_usda(usda_text)
    assert layer.GetPrimAtPath("/Render/Camera")
```

### For USD Python API tabs

Add a test to `tests/docs/usd/test_usd_python_examples.py`. The `CreateInMemory()` call stays **outside** the snippet markers -- it's setup:

```python
def test_my_render_product():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-my-render-product-python]
    render_scope = stage.DefinePrim("/Render")
    camera_product = UsdRender.Product.Define(stage, "/Render/Camera")
    camera_product.GetCameraRel().SetTargets(["/World/Camera"])
    # ... etc
    # [/snippet:doc-my-render-product-python]

    assert stage.GetPrimAtPath("/Render/Camera").IsValid()
```

## Step 3: Wire up the RST

### USDA blocks become tab-sets with USDA + Python tabs

```rst
.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../tests/docs/usd/data/my_file.usda
         :language: usda
         :start-after: # [snippet:doc-my-render-product]
         :end-before: # [/snippet:doc-my-render-product]

   .. tab-item:: Python

      .. literalinclude:: ../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-my-render-product-python]
         :end-before: # [/snippet:doc-my-render-product-python]
         :dedent:
```

### Python/C runtime code uses existing tab-sets

```rst
.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../tests/docs/python/test_something.py
         :language: python
         :start-after: # [snippet:doc-my-feature]
         :end-before: # [/snippet:doc-my-feature]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../tests/docs/c/test_something.cpp
         :language: cpp
         :start-after: // [snippet:doc-my-feature-c]
         :end-before: // [/snippet:doc-my-feature-c]
         :dedent:
```

## Step 4: Run the tests

```bash
cd tests/docs/usd && uv run pytest -v        # USDA + USD Python API
cd tests/docs/python && uv run pytest -v      # ovrtx (needs GPU)
cd tests/docs/c && cmake -B build-dev -DCMAKE_PREFIX_PATH=/path/to/ovrtx && cmake --build build-dev && ctest --test-dir build-dev --output-on-failure
```

## Step 5: Update the snippet inventory

Add new snippets to the table in `tests/docs/AGENTS.md` so others can find them.

## Style Rules for Prose

### Function names always get parentheses

When mentioning a function or method in prose, always include trailing parentheses so it reads as a callable:

- Good: ``write_array_attribute()``
- Bad: ``write_array_attribute``

### Link function names to API docs

When referencing ovrtx functions in RST prose, use Sphinx cross-reference roles so the reader can click through to the full API documentation:

**Python** -- use `:py:meth:` for Renderer methods, `:py:func:` for free functions, `:py:class:` for classes:

```rst
Use :py:meth:`~ovrtx.Renderer.write_array_attribute()` to write array data.
```

The `~` prefix displays only the method name (``write_array_attribute()``) rather than the fully qualified path. Without it you get ``ovrtx.Renderer.write_array_attribute()``.

**C** -- use `:c:func:` for C API functions:

```rst
Use :c:func:`ovrtx_set_path_attributes()` to write path attributes.
```

These roles will generate hyperlinks when the target exists in the autodoc/breathe output. If the target doesn't exist (e.g., a static inline helper not in a doxygen group), the text still renders as styled monospace, so there's no downside to using them.

## Common Pitfalls

- **Don't forget `:dedent:` on Python literalincludes.** Without it the code renders with test-level indentation.
- **Snippet names must be globally unique** across all files in `tests/docs/`.
- **Don't include setup in snippets.** `CreateInMemory()`, warm-up loops, scene loading -- these are test infrastructure, not doc content.
- **Always use the `doc-` prefix** for snippet names in this tree so doc-tested snippets are easy to identify in skills and RST.
- **Always include parentheses on function names** in prose text -- ``write_array_attribute()`` not ``write_array_attribute``.
- **Always use cross-reference roles** (`:py:meth:`, `:c:func:`, etc.) for ovrtx API functions in RST prose, not bare double-backtick literals.
