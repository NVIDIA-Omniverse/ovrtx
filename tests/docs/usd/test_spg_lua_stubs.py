# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Keep the SPG Lua editor stubs and the SPG docs describing the same surface.

``docs/spg/.luarc/`` is what the docs tell a reader to point their Lua Language
Server at, so a symbol the docs describe and the stubs omit is flagged as
undefined in the reader's editor, and a symbol the stubs carry and the docs never
mention is undocumented API. Both drifted before this check existed.

The two sides are compared by name in both directions:

- every ``cuda.X``, ``slang.X`` and ``rtx.X`` named in ``docs/spg`` is declared in
  the stubs, and
- every symbol the stubs declare is named somewhere in ``docs/spg``.

Pure standard library, so it runs wherever the USDA suite runs.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPG_DOCS = REPO_ROOT / "docs" / "spg"
LUARC = SPG_DOCS / ".luarc"

MODULES = ("cuda", "slang", "rtx")

# ``slang.lua``, ``cuda.lua`` and ``slang.usda`` are file names, not symbols, and
# they read as ``<module>.<name>`` to any regex. Every suffix a doc page can name
# a file with belongs here.
FILE_SUFFIXES = frozenset(
    {"lua", "usda", "usd", "usdz", "cu", "slang", "spv", "ptx", "cubin", "fatbin", "py", "rst", "json", "bin", "md"}
)

REFERENCE = re.compile(r"\b(cuda|slang|rtx)\.([A-Za-z_][A-Za-z0-9_]*)")
# ``rtx.spg.stdlib/Add`` is a built-in node ID, not a Lua global.
NOT_A_SYMBOL = frozenset({("rtx", "spg")})
STUB_CLASS = re.compile(r"^---@class\s+(cuda|slang|rtx)\s*$")
STUB_FIELD = re.compile(r"^---@field\s+([A-Za-z_][A-Za-z0-9_]*)\s")
STUB_FUNCTION = re.compile(r"^function\s+(cuda|slang|rtx)\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# A ``---@class`` block ends at the first line that is not a stub annotation.
STUB_ANNOTATION = re.compile(r"^---@")


def _documented():
    """Return {module: {name: [where it was written]}} for every symbol the docs name."""
    found = {module: {} for module in MODULES}
    for rst in sorted(SPG_DOCS.rglob("*.rst")):
        if "_build" in rst.parts:
            continue
        for number, line in enumerate(rst.read_text().splitlines(), start=1):
            for module, name in REFERENCE.findall(line):
                if name in FILE_SUFFIXES or (module, name) in NOT_A_SYMBOL:
                    continue
                found[module].setdefault(name, []).append(f"{rst.relative_to(REPO_ROOT)}:{number}")
    return found


def _declared():
    """Return {module: {name}} for every symbol the stubs declare."""
    found = {module: set() for module in MODULES}
    for stub in sorted(LUARC.glob("*.lua")):
        module_of_class = None
        for line in stub.read_text().splitlines():
            function = STUB_FUNCTION.match(line)
            if function:
                found[function.group(1)].add(function.group(2))
                module_of_class = None
                continue
            opened = STUB_CLASS.match(line)
            if opened:
                module_of_class = opened.group(1)
                continue
            if module_of_class is None:
                continue
            field = STUB_FIELD.match(line)
            if field:
                found[module_of_class].add(field.group(1))
            elif not STUB_ANNOTATION.match(line):
                module_of_class = None
    return found


DOCUMENTED = _documented()
DECLARED = _declared()


def test_stubs_were_parsed():
    """Guard the parser itself: an empty side would make every check below pass."""
    for module in MODULES:
        assert DECLARED[module], f"no symbols parsed out of the {module} stub; the parser or the stub changed shape"
        assert DOCUMENTED[module], f"no {module}.X references found in {SPG_DOCS}; the doc scan found nothing"


@pytest.mark.parametrize("module", MODULES)
def test_every_documented_symbol_is_in_the_stubs(module):
    """A documented symbol the stubs omit is flagged as undefined in the reader's editor."""
    missing = {
        name: where for name, where in sorted(DOCUMENTED[module].items()) if name not in DECLARED[module]
    }
    assert not missing, (
        f"{module}.X documented but absent from docs/spg/.luarc/: "
        + "; ".join(f"{name} ({where[0]})" for name, where in missing.items())
    )


@pytest.mark.parametrize("module", MODULES)
def test_every_stub_symbol_is_documented(module):
    """A symbol the stubs carry and no page names is API the reader cannot find."""
    undocumented = sorted(name for name in DECLARED[module] if name not in DOCUMENTED[module])
    assert not undocumented, (
        f"declared in docs/spg/.luarc/ but named on no page under docs/spg/: "
        + ", ".join(f"{module}.{name}" for name in undocumented)
    )
