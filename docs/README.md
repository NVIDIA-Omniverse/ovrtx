# Building the Documentation

This directory contains the Sphinx source for the ovrtx documentation published at
<https://nvidia-omniverse.github.io/ovrtx>.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (Linux/macOS) or `winget install astral-sh.uv` (Windows) |
| [Doxygen](https://www.doxygen.nl/download.html) | ≥ 1.9 | `sudo apt-get install doxygen` (Ubuntu) or `winget install -e --id DimitriVanHeesch.Doxygen` (Windows) |
| Python | ≥ 3.11 | provisioned automatically by `uv` |

Sphinx and all Python documentation dependencies (Breathe, the NVIDIA theme, etc.) are
declared in `requirements.txt` in this directory and are installed automatically by
`uv` — you do not need to install them separately.

They are deliberately *not* part of `pyproject.toml`. The docs need Sphinx ≥ 8.2 (see
the comments in `requirements.txt`), which requires Python ≥ 3.11, while ovrtx itself
supports Python ≥ 3.10. Keeping the toolchain in a standalone file lets the docs
require a newer Python than the package does. The build commands below therefore ask
`uv` for a Python ≥ 3.11 interpreter, downloading one if your default is older.

## Building on Linux

```bash
cd docs
make html
```

`make html` runs Doxygen first (to generate the C API XML consumed by Breathe), then
invokes Sphinx via `uv run`.

## Building on Windows

With `uv` on your `PATH` (see Prerequisites), `make.bat` automatically provisions
Sphinx and the rest of `requirements.txt` into a managed environment — no separate
Sphinx install required:

```bat
cd docs
make.bat html
```

`make.bat html` runs Doxygen first, matching `make html` on Linux, and then invokes
Sphinx. You can also run `make.bat doxygen` to generate only the C API XML.

If you do not want to install Doxygen system-wide, download a pinned, project-local
copy instead:

```bat
get-doxygen.bat
make.bat html
```

The downloader verifies the archive's published SHA-256 checksum and extracts it to
the ignored `docs\_tools` directory. `make.bat` discovers this copy automatically.
You can also point `make.bat` at another executable by setting `%DOXYGEN%`.

`make.bat` picks its Sphinx in this order:

1. `%SPHINXBUILD%` if you've set it explicitly.
2. `..\repo.bat` (NVIDIA-internal builds) — routes `uv` through it.
3. `uv` on `PATH`.
4. A bare `sphinx-build` on `PATH` (only useful if you've installed Sphinx
   yourself).

Options 2 and 3 both provision the toolchain from `requirements.txt`.

If you'd rather drive Sphinx directly:

```bat
cd docs
uv run --no-project --python ">=3.11" --with-requirements requirements.txt sphinx-build -M html . _build
```

If `make.bat` reports that `sphinx-build` was not found, your shell does not have
`uv` (or any other Sphinx) on `PATH`. Install it with `winget install astral-sh.uv`,
open a new terminal, and re-run.

## Viewing the output

After a successful build, serve the result locally:

```bash
# Linux / macOS
uv run python -m http.server 8000 -d _build/html
```

```bat
REM Windows
uv run python -m http.server 8000 -d _build/html
```

Then open <http://localhost:8000/> in a browser.

## Cleaning build artifacts

```bash
# Linux
make clean
```

```bat
REM Windows
make.bat clean
```
