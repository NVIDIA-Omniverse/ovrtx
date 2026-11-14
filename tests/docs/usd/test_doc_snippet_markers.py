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


# --------------------------------------------------------------------------------------------
# The snippet inventory in tests/docs/AGENTS.md
#
# The inventory table is the index agents and reviewers use to find where a snippet is quoted.
# It only helps while it is true, so each row is checked against the tree: the source file
# exists and carries the marker, every page the row names exists and literalincludes the
# marker, every page that literalincludes a marker is listed on that marker's row, every
# marker in the sources has a row, and the usd/data listing in the directory layout names
# every data file.

TESTS_DOCS = REPO_ROOT / "tests" / "docs"
INVENTORY = TESTS_DOCS / "AGENTS.md"
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")
MARKER = re.compile(r"^\s*(?:#|//|/\*|--)\s*\[snippet:([a-z0-9-]+)\]", re.MULTILINE)
PAGE = re.compile(r"`([^`]+\.rst)`")
SOURCE_SUFFIXES = {".py", ".usda", ".cpp", ".c", ".h", ".txt", ".lua", ".cu", ".slang"}


def _inventory_rows():
    """(line number, snippet, source path, used-in cell) for every table row of the inventory."""
    rows = []
    for lineno, line in enumerate(INVENTORY.read_text().splitlines(), 1):
        match = ROW.match(line)
        if match:
            rows.append((lineno, match.group(1), match.group(2), match.group(3)))
    return rows


def _resolve_source(path):
    """Inventory source paths are relative to tests/docs, or to the public root for examples/."""
    for base in (TESTS_DOCS, REPO_ROOT):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return None


def _page_uses():
    """marker -> set of pages (relative to docs/) that literalinclude it."""
    uses = {}
    for rst in sorted(DOCS.rglob("*.rst")):
        if "_build" in rst.parts:
            continue
        for match in re.finditer(r":start-after:[^\n]*\[snippet:([a-z0-9-]+)\]", rst.read_text()):
            uses.setdefault(match.group(1), set()).add(rst.relative_to(DOCS).as_posix())
    return uses


def _source_markers():
    """marker -> first source file (relative to tests/docs or the public root) that defines it."""
    markers = {}
    for root in (TESTS_DOCS, REPO_ROOT / "examples"):
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES or any(part in path.parts for part in ("__pycache__", ".venv", "_build", "build", "build-dev", "_deps")):
                continue
            rel = path.relative_to(TESTS_DOCS) if root == TESTS_DOCS else path.relative_to(REPO_ROOT)
            for match in MARKER.finditer(path.read_text(errors="replace")):
                markers.setdefault(match.group(1), rel.as_posix())
    return markers


ROWS = _inventory_rows()
assert ROWS, "no inventory rows found; the table in tests/docs/AGENTS.md moved"
USES = _page_uses()
SOURCES = _source_markers()
LISTED = {snippet: set(PAGE.findall(used)) for _, snippet, _, used in ROWS}


@pytest.mark.parametrize("lineno, snippet, source, used", ROWS, ids=[r[1] for r in ROWS])
def test_inventory_row_is_true(lineno, snippet, source, used):
    where = f"AGENTS.md:{lineno} ({snippet})"
    resolved = _resolve_source(source)
    assert resolved is not None, f"{where}: source file not found: {source}"
    assert f"[snippet:{snippet}]" in resolved.read_text(errors="replace"), (
        f"{where}: {source} has no marker [snippet:{snippet}]"
    )
    for page in PAGE.findall(used):
        rst = DOCS / page
        assert rst.is_file(), f"{where}: page not in the tree: {page}"
        assert page in USES.get(snippet, ()), f"{where}: {page} does not literalinclude [snippet:{snippet}]"


USE_CASES = sorted((snippet, page) for snippet, pages in USES.items() for page in pages)


@pytest.mark.parametrize("snippet, page", USE_CASES, ids=[f"{s}@{p}" for s, p in USE_CASES])
def test_every_page_use_is_listed(snippet, page):
    assert snippet in LISTED, f"[snippet:{snippet}] is quoted by {page} but has no inventory row"
    assert page in LISTED[snippet], f"the inventory row of {snippet} does not list {page}"


@pytest.mark.parametrize("snippet", sorted(SOURCES), ids=sorted(SOURCES))
def test_every_marker_has_a_row(snippet):
    assert snippet in LISTED, f"[snippet:{snippet}] in {SOURCES[snippet]} has no inventory row"


def test_data_listing_names_every_data_file():
    inventory = INVENTORY.read_text()
    data = TESTS_DOCS / "usd" / "data"
    missing = [p.relative_to(data).as_posix() for p in sorted(data.rglob("*.usda"))
               if f"── {p.relative_to(data).as_posix()}" not in inventory]
    assert not missing, f"usd/data files absent from the directory layout in AGENTS.md: {missing}"
