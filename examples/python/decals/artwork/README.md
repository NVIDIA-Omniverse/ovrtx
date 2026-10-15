# Decal source artwork

These PNGs are inputs to `../generate_masks.py`, not documentation figures.

- `nvidia.png`: existing NVIDIA artwork, copied unchanged from
  `rendering/data/usd/tests/SceneTemplates/NVIDIA_Logo_V_ForScreen_ForDarkBG.png`.
  Its alpha channel preserves both the eye and wordmark.
- `rtx.png`: the RTX reference supplied for this example. The generator removes
  its dark background and preserves the original letter shapes and proportions.

The generated grayscale masks live in `tests/docs/data/`. The renderer supplies
the red and silver materials; no lighting or metallic appearance is baked into
the masks.
