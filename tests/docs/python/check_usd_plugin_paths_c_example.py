# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Run both packaged C schema-registration examples and keep their output."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run_examples(binary_root: Path, output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for model, name in (("static", "usd-plugin-paths"), ("shared", "usd-plugin-paths-dynamic")):
        binary_dir = binary_root / model
        if sys.platform == "win32":
            binary_dir /= "Release"
            name += ".exe"
        binary = (binary_dir / name).resolve()
        if not binary.is_file():
            raise FileNotFoundError(f"Packaged C Plugin Paths example is missing: {binary}")
        if sys.platform != "win32":
            binary.chmod(0o755)
        log = output_dir / f"c-usd-plugin-paths-{model}.log"
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run(
                [str(binary)], cwd=output_dir, stdout=stream, stderr=subprocess.STDOUT,
                timeout=60, check=True,
            )
        output = log.read_text(encoding="utf-8", errors="replace")
        if "rtx_settings" not in output or not re.search(
            r"Published [1-9][0-9]* schema directories for the bundled USD runtime\.", output
        ):
            raise RuntimeError(f"Missing schema paths or registration confirmation; see {log}")
        # The C API publishes strings even when the selected root does not exist.
        # Each loader must reject that root rather than report a successful check.
        with tempfile.TemporaryDirectory(prefix="schema-root-", dir=output_dir) as folder:
            missing = Path(folder) / "does-not-exist"
            env = os.environ.copy()
            env["OMNI_USD_PLUGINS_BASE_PATH"] = str(missing)
            env["OVRTX_PXR_SCHEMA_AUTO_REGISTER"] = "0"
            negative_log = output_dir / f"c-usd-plugin-paths-{model}-missing-root.log"
            with negative_log.open("w", encoding="utf-8") as stream:
                result = subprocess.run(
                    [str(binary)], cwd=output_dir, env=env, stdout=stream,
                    stderr=subprocess.STDOUT, timeout=60,
                )
            negative = negative_log.read_text(encoding="utf-8", errors="replace")
            if (result.returncode != 1 or "Schema plugin descriptor missing:" not in negative
                    or "Published " in negative or str(missing) not in negative):
                raise RuntimeError(f"Nonexistent schema root was not rejected correctly; see {negative_log}")
        print(f"Validated {binary.name}, including missing-root rejection; output: {log}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_examples(args.binary_root, args.output_dir)
