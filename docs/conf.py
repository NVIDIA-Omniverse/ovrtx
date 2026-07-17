# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the package to the path for autodoc
sys.path.insert(0, os.path.abspath("../python"))
# Add local extensions
sys.path.insert(0, os.path.abspath("_ext"))

# -- Project information -----------------------------------------------------
project = "ovrtx"
copyright = "2025, NVIDIA Corporation"
author = "NVIDIA Corporation"

# The version info
from ovrtx import __version__

version = __version__
release = __version__

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_mdinclude",
    "breathe",
    "filtered_literalinclude",
]

# -- Options for Breathe (C API documentation) -------------------------------
breathe_projects = {"ovrtx": "_doxygen/xml"}
breathe_default_project = "ovrtx"
breathe_default_members = ("members", "undoc-members")
breathe_domain_by_extension = {"h": "c"}

# -- Options for sphinx-mdinclude (Markdown in docstrings) -------------------
# Enable Markdown-to-RST conversion for docstrings
mdinclude_transform = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Suppress warnings for known issues
suppress_warnings = [
    "autodoc.duplicate_object",  # Dataclass fields documented twice by autodoc
    "duplicate_declaration.cpp",  # Breathe generates duplicate typedef/enum declarations for C typedef patterns
    "duplicate_declaration.c",  # Same, for C domain (breathe_domain_by_extension maps .h to C)
]
# Note: The "Error in declarator" warning for ovrtx_renderer_config_value_t is due to
# Sphinx's C++ domain not supporting anonymous unions. This is a cosmetic warning only;
# the documentation still generates correctly.

# -- Options for autodoc -----------------------------------------------------
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

autodoc_typehints = "description"
autodoc_class_signature = "separated"

# -- Options for Napoleon (Google/NumPy docstrings) --------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for HTML output -------------------------------------------------
html_theme = "nvidia_sphinx_theme"

html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "pygments_light_style": "sas",  # for light mode
    "pygments_dark_style": "github-dark",  # for dark mode
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/NVIDIA-Omniverse/ovrtx",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
}

html_static_path = ["_static"]
# Paths are relative to html_static_path
html_css_files = [
    "css/custom.css",
]
html_js_files = [
    ("js/aov-images.js", {"defer": "defer"}),
]

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "ovstage": ("https://nvidia-omniverse.github.io/ovstage", None),
}

# -- Autosummary settings ----------------------------------------------------
autosummary_generate = True


# -- Convert Markdown code blocks in docstrings to RST -----------------------
import re


def convert_markdown_codeblocks(app, what, name, obj, options, lines):
    """Convert Markdown fenced code blocks to RST code-block directives.

    Also handles Example/Examples sections with plain Python code.
    """
    text = "\n".join(lines)

    # Pattern for ```lang ... ``` code blocks
    pattern = r"```(\w*)\n(.*?)```"

    def replace_codeblock(match):
        lang = match.group(1) or "python"
        code = match.group(2).rstrip()
        # Indent the code for RST
        indented = "\n".join("    " + line if line else "" for line in code.split("\n"))
        return f".. code-block:: {lang}\n\n{indented}\n"

    text = re.sub(pattern, replace_codeblock, text, flags=re.DOTALL)

    # Handle Example/Examples sections with plain Python code
    # Pattern: "Example:" or "Examples:" followed by indented code (not >>> style)
    lines_list = text.split("\n")
    result = []
    i = 0
    in_example = False
    example_indent = 0
    code_block_lines = []

    while i < len(lines_list):
        line = lines_list[i]
        stripped = line.strip()

        # Check for Example: or Examples: section start
        if stripped in ("Example:", "Examples:"):
            in_example = True
            result.append(line)
            result.append("")  # Blank line after Example:
            result.append(".. code-block:: python")
            result.append("")
            i += 1
            # Skip blank lines after Example:
            while i < len(lines_list) and not lines_list[i].strip():
                i += 1
            # Determine indentation of first code line
            if i < len(lines_list):
                first_code = lines_list[i]
                example_indent = len(first_code) - len(first_code.lstrip())
            continue

        if in_example:
            # Check if still in example section (indented or blank)
            if not stripped:
                # Blank line - could be end or continuation
                # Look ahead to see if more code follows
                j = i + 1
                while j < len(lines_list) and not lines_list[j].strip():
                    j += 1
                if j < len(lines_list):
                    next_line = lines_list[j]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    next_stripped = next_line.strip()
                    # Check if next non-blank is still code (indented) and not a new section
                    if next_indent >= example_indent and not next_stripped.endswith(
                        ":"
                    ):
                        result.append("")  # Keep blank line in code block
                        i += 1
                        continue
                # End of example section
                in_example = False
                result.append(line)
            elif stripped.endswith(":") and not stripped.startswith("#"):
                # New section starting (Args:, Returns:, etc.)
                in_example = False
                result.append(line)
            else:
                # Code line - ensure proper indentation (4 spaces for RST code block)
                code_content = (
                    line[example_indent:]
                    if len(line) > example_indent
                    else line.lstrip()
                )
                result.append("    " + code_content)
        else:
            result.append(line)
        i += 1

    # Update lines in-place
    lines.clear()
    lines.extend(result)


def setup(app):
    app.connect("autodoc-process-docstring", convert_markdown_codeblocks)
