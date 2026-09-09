# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Check that every ``literalinclude`` in the docs still resolves.

Snippet markers are a contract between the docs and the files they quote. A
renamed marker, a moved file or a snippet that grew or shrank all leave the
build green while the page quietly shows the wrong thing, so each directive is
re-resolved here the way Sphinx would:

- the included file exists,
- its ``start-after`` and ``end-before`` markers are both present,
- every ``emphasize-lines`` entry falls inside the region it highlights, and
  lands on a line with content rather than on a blank.

Pure standard library, so it runs wherever the USDA suite runs.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs"

DIRECTIVE = re.compile(r"^(\s*)\.\.\s+(?:filtered-)?literalinclude::\s*(\S+)\s*$")
OPTION = re.compile(r"^\s*:([a-z-]+):\s*(.*?)\s*$")


def _directives():
    """Yield (rst, line number, target path, options) for every literalinclude."""
    for rst in sorted(DOCS.rglob("*.rst")):
        if "_build" in rst.parts:
            continue
        lines = rst.read_text().splitlines()
        for i, line in enumerate(lines):
            match = DIRECTIVE.match(line)
            if not match:
                continue
            indent, target = match.group(1), match.group(2)
            options = {}
            for follow in lines[i + 1:]:
                if not follow.strip():
                    break
                if len(follow) - len(follow.lstrip()) <= len(indent):
                    break
                option = OPTION.match(follow)
                if not option:
                    break
                options[option.group(1)] = option.group(2)
            yield rst, i + 1, target, options


def _emphasized(spec):
    """Expand an emphasize-lines spec such as "7, 17-18" into line numbers."""
    numbers = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            first, last = part.split("-", 1)
            numbers.extend(range(int(first), int(last) + 1))
        elif part:
            numbers.append(int(part))
    return numbers


CASES = list(_directives())
assert CASES, "no literalinclude directives found; the docs tree moved"


@pytest.mark.parametrize(
    "rst, lineno, target, options",
    CASES,
    ids=[f"{r.relative_to(DOCS)}:{n}" for r, n, _, _ in CASES],
)
def test_literalinclude_resolves(rst, lineno, target, options):
    where = f"{rst.relative_to(REPO_ROOT)}:{lineno}"

    included = (rst.parent / target).resolve()
    assert included.is_file(), f"{where}: included file not found: {target}"

    body = included.read_text(errors="replace").splitlines()
    start, end = options.get("start-after"), options.get("end-before")

    first, last = 0, len(body)
    if start is not None:
        opens = [i for i, l in enumerate(body) if start in l]
        assert opens, f"{where}: {included.name} has no line containing {start!r}"
        first = opens[0] + 1
    if end is not None:
        closes = [i for i, l in enumerate(body) if end in l and i >= first]
        assert closes, f"{where}: {included.name} has no line containing {end!r}"
        last = closes[0]
    region = body[first:last]

    assert region, f"{where}: the region between the markers is empty"

    for number in _emphasized(options.get("emphasize-lines", "")):
        assert 1 <= number <= len(region), (
            f"{where}: emphasize-lines {number} is outside the {len(region)}-line "
            f"region taken from {included.name}"
        )
        assert region[number - 1].strip(), (
            f"{where}: emphasize-lines {number} lands on a blank line in "
            f"{included.name}, which usually means the snippet moved"
        )
