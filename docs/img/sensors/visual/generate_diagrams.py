#!/usr/bin/env python3
"""Write every SVG of this image directory.

The drawings live in the ``_gen_*.py`` modules beside this file, one module per
topic group; each exposes ``generate(out_dir: pathlib.Path) -> None``. This entry
point imports them in name order and runs them, so one command regenerates the
whole directory::

    python3 generate_diagrams.py            # in place
    python3 generate_diagrams.py /tmp/check # elsewhere, to diff against the committed files

Shared helpers (palette, font stack, shapes, overlap and bounds checks) come from
``../_diagram_lib.py``.
"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import _diagram_lib as dl  # noqa: E402


def main() -> None:
    out_dir = dl.output_dir(__file__)
    modules = sorted(HERE.glob("_gen_*.py"))
    if not modules:
        sys.exit(f"{HERE}: no _gen_*.py modules")
    for path in modules:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate(out_dir)


if __name__ == "__main__":
    main()
