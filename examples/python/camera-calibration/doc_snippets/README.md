# USDA documentation excerpts

These excerpts show the USDA equivalent of the Python authoring snippets.
The attribute values in `camera_attributes.usda` come from the bundled photographs.
After changing the authoring code, regenerate the outputs and update these excerpts.

`reference_camera.py` creates `_out/scene.usda` when run from the example folder
after calibration. Its USDA counterpart shows that layer's contents; the reference
path is relative to `_out/scene.usda`.

The CPU docs suite (`test_camera_calibration_example.py`) runs the locked calibration
project, compares its lens attributes with the displayed excerpt, and verifies
both reference examples compose the generated default Camera prim.
