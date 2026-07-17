#!/usr/bin/env python3
"""Inline tested snippet references in ovrtx skill files.

The source-of-truth skills under ``skills/`` reference snippets that live in
``tests/`` and ``examples/``. Release artifacts can use this script to replace
those references with fenced code blocks so the distributed skills stand alone.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path("/tmp/ovrtx-skills")

SNIPPET_START_RE = re.compile(r"\[\s*snippet:(?P<name>[A-Za-z0-9_.:-]+)\s*\]")
SNIPPET_END_RE = re.compile(r"\[\s*/snippet:(?P<name>[A-Za-z0-9_.:-]+)\s*\]")
SKILL_REFERENCE_RE = re.compile(
    r"^(?P<indent>\s*)>\s*(?P<label>\*\*Source:\*\*|Followed by:)\s+"
    r"`(?P<path>[^`]+)`\s+snippets?\s+(?P<tail>.*)$"
)
BACKTICK_CONTENT_RE = re.compile(r"`([^`]+)`")
FENCE_RE = re.compile(r"`{3,}")

SKIP_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "_deps",
    "__pycache__",
    "build",
    "build-dev",
    "dist",
}

LANGUAGE_BY_SUFFIX = {
    ".bat": "batch",
    ".c": "c",
    ".cc": "cpp",
    ".cmake": "cmake",
    ".cpp": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".lua": "lua",
    ".md": "markdown",
    ".py": "python",
    ".rst": "rst",
    ".sh": "bash",
    ".toml": "toml",
    ".usd": "usda",
    ".usda": "usda",
    ".frag": "glsl",
    ".glsl": "glsl",
    ".vert": "glsl",
}

SOURCE_FILE_SUFFIXES = {
    ".bat",
    ".c",
    ".cc",
    ".cmake",
    ".cpp",
    ".cu",
    ".cuh",
    ".cxx",
    ".frag",
    ".glsl",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".lua",
    ".py",
    ".sh",
    ".toml",
    ".usd",
    ".usda",
    ".vert",
}
SOURCE_FILE_NAMES = {
    "CMakeLists.txt",
}


class InlineSkillSnippetError(RuntimeError):
    """Raised when skill snippet expansion cannot complete."""


@dataclass(frozen=True)
class Snippet:
    source_path: str
    name: str
    content: str
    language: str


@dataclass
class TransformStats:
    indexed_snippets: int = 0
    indexed_files: int = 0
    expanded_references: int = 0
    transformed_files: int = 0
    unresolved_references: int = 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replace ovrtx skill snippet references with code copied from "
            "the referenced tests/examples snippets."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help=f"Repository root to scan. Defaults to {REPO_ROOT}.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=None,
        help="Skills directory to transform. Defaults to <repo-root>/skills.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Dry-run output directory. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Write the transformed skills tree to --output-dir. This is the default.",
    )
    mode.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite SKILL.md files in the skills directory.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Leave unresolved snippet references unchanged instead of failing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    skills_dir = (args.skills_dir or repo_root / "skills").resolve()
    output_dir = args.output_dir.resolve()

    try:
        stats = inline_skill_snippets(
            repo_root=repo_root,
            skills_dir=skills_dir,
            output_dir=output_dir,
            in_place=args.in_place,
            allow_missing=args.allow_missing,
        )
    except InlineSkillSnippetError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Indexed {stats.indexed_snippets} snippets from "
        f"{stats.indexed_files} tests/examples files."
    )
    print(
        f"Expanded {stats.expanded_references} snippet references in "
        f"{stats.transformed_files} skill files."
    )
    if stats.unresolved_references:
        print(
            f"Left {stats.unresolved_references} unresolved references unchanged "
            "because --allow-missing was set."
        )
    if args.in_place:
        print(f"Updated skills in place: {skills_dir}")
    else:
        print(f"Wrote dry-run skills tree: {output_dir}")
    return 0


def inline_skill_snippets(
    *,
    repo_root: Path,
    skills_dir: Path,
    output_dir: Path,
    in_place: bool,
    allow_missing: bool,
) -> TransformStats:
    repo_root = repo_root.resolve()
    skills_dir = skills_dir.resolve()

    if not skills_dir.is_dir():
        raise InlineSkillSnippetError(f"skills directory does not exist: {skills_dir}")

    snippets, indexed_file_count = collect_snippets(repo_root)
    stats = TransformStats(
        indexed_snippets=len(snippets),
        indexed_files=indexed_file_count,
    )

    transformed = transform_skill_tree(
        skills_dir=skills_dir,
        snippets=snippets,
        allow_missing=allow_missing,
        stats=stats,
    )

    if in_place:
        for path, content in transformed.items():
            path.write_text(content, encoding="utf-8")
    else:
        output_dir = output_dir.resolve()
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(skills_dir, output_dir)
        for source_path, content in transformed.items():
            relative_path = source_path.relative_to(skills_dir)
            target_path = output_dir / relative_path
            target_path.write_text(content, encoding="utf-8")

    return stats


def collect_snippets(repo_root: Path) -> tuple[dict[tuple[str, str], Snippet], int]:
    snippets: dict[tuple[str, str], Snippet] = {}
    indexed_files: set[str] = set()

    for source_dir_name in ("tests", "examples"):
        source_dir = repo_root / source_dir_name
        if not source_dir.is_dir():
            continue

        for path in iter_text_files(source_dir):
            relative_path = normalize_ref_path(path.relative_to(repo_root).as_posix())
            file_snippets = extract_snippets(path, relative_path)
            if not file_snippets:
                continue

            indexed_files.add(relative_path)
            for snippet in file_snippets:
                key = (snippet.source_path, snippet.name)
                if key in snippets:
                    raise InlineSkillSnippetError(
                        f"duplicate snippet `{snippet.name}` in {snippet.source_path}"
                    )
                snippets[key] = snippet

    return snippets, len(indexed_files)


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_NAMES for part in relative_parts):
            continue
        if path.is_file() and is_source_file(path):
            yield path


def is_source_file(path: Path) -> bool:
    return path.name in SOURCE_FILE_NAMES or path.suffix.lower() in SOURCE_FILE_SUFFIXES


def extract_snippets(path: Path, relative_path: str) -> list[Snippet]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return []

    snippets: list[Snippet] = []
    active_name: str | None = None
    active_lines: list[str] = []
    seen_names: set[str] = set()

    for line_number, line in enumerate(lines, start=1):
        start_match = SNIPPET_START_RE.search(line)
        end_match = SNIPPET_END_RE.search(line)

        if start_match:
            if active_name is not None:
                raise InlineSkillSnippetError(
                    f"nested snippet `{start_match.group('name')}` at "
                    f"{relative_path}:{line_number}"
                )
            active_name = start_match.group("name")
            if active_name in seen_names:
                raise InlineSkillSnippetError(
                    f"duplicate snippet `{active_name}` in {relative_path}"
                )
            active_lines = []
            seen_names.add(active_name)
            continue

        if end_match:
            end_name = end_match.group("name")
            if active_name is None:
                raise InlineSkillSnippetError(
                    f"unexpected snippet end `{end_name}` at {relative_path}:{line_number}"
                )
            if end_name != active_name:
                raise InlineSkillSnippetError(
                    f"snippet `{active_name}` closed by `{end_name}` at "
                    f"{relative_path}:{line_number}"
                )
            snippets.append(
                Snippet(
                    source_path=relative_path,
                    name=active_name,
                    content=normalize_snippet_content(active_lines),
                    language=language_for_path(Path(relative_path)),
                )
            )
            active_name = None
            active_lines = []
            continue

        if active_name is not None:
            active_lines.append(line)

    if active_name is not None:
        raise InlineSkillSnippetError(
            f"snippet `{active_name}` in {relative_path} is missing an end marker"
        )

    return snippets


def normalize_snippet_content(lines: list[str]) -> str:
    content = "".join(lines)
    return textwrap.dedent(content).strip("\n")


def transform_skill_tree(
    *,
    skills_dir: Path,
    snippets: dict[tuple[str, str], Snippet],
    allow_missing: bool,
    stats: TransformStats,
) -> dict[Path, str]:
    transformed: dict[Path, str] = {}
    missing: list[str] = []

    for skill_path in sorted(skills_dir.rglob("SKILL.md")):
        original = skill_path.read_text(encoding="utf-8")
        replacement, expanded_count, unresolved_count, file_missing = transform_skill_file(
            original,
            skill_path=skill_path,
            skills_dir=skills_dir,
            snippets=snippets,
            allow_missing=allow_missing,
        )
        missing.extend(file_missing)
        stats.expanded_references += expanded_count
        stats.unresolved_references += unresolved_count
        if replacement != original:
            transformed[skill_path] = replacement
            stats.transformed_files += 1

    if missing and not allow_missing:
        raise InlineSkillSnippetError(
            "unresolved skill snippet references:\n" + "\n".join(missing)
        )

    return transformed


def transform_skill_file(
    text: str,
    *,
    skill_path: Path,
    skills_dir: Path,
    snippets: dict[tuple[str, str], Snippet],
    allow_missing: bool,
) -> tuple[str, int, int, list[str]]:
    lines = text.splitlines()
    output_lines: list[str] = []
    expanded_count = 0
    unresolved_count = 0
    missing: list[str] = []
    inside_fence = False
    skip_quote_separator = False

    for line_number, line in enumerate(lines, start=1):
        if skip_quote_separator and re.match(r"^\s*>\s*$", line):
            output_lines.append("")
            skip_quote_separator = False
            continue
        skip_quote_separator = False

        if line.lstrip().startswith("```"):
            inside_fence = not inside_fence
            output_lines.append(line)
            continue

        match = SKILL_REFERENCE_RE.match(line)
        if inside_fence or not match:
            output_lines.append(line)
            continue

        source_path = normalize_ref_path(match.group("path"))
        snippet_names = BACKTICK_CONTENT_RE.findall(match.group("tail"))
        if not snippet_names:
            output_lines.append(line)
            continue

        snippet_blocks: list[str] = []
        missing_for_line: list[str] = []
        for snippet_name in snippet_names:
            snippet = snippets.get((source_path, snippet_name))
            if snippet is None:
                missing_for_line.append(
                    f"{skill_path.relative_to(skills_dir).as_posix()}:{line_number}: "
                    f"{source_path} snippet `{snippet_name}`"
                )
                continue
            snippet_blocks.append(format_snippet_block(snippet))

        if missing_for_line:
            missing.extend(missing_for_line)
            unresolved_count += len(missing_for_line)
            if allow_missing:
                output_lines.append(line)
                continue
            output_lines.append(line)
            continue

        output_lines.extend("\n\n".join(snippet_blocks).splitlines())
        expanded_count += len(snippet_blocks)
        skip_quote_separator = True

    trailing_newline = "\n" if text.endswith("\n") else ""
    return "\n".join(output_lines) + trailing_newline, expanded_count, unresolved_count, missing


def format_snippet_block(snippet: Snippet) -> str:
    fence = fence_for_content(snippet.content)
    language = snippet.language
    opening = f"{fence}{language}" if language else fence
    return f"{opening}\n{snippet.content}\n{fence}"


def fence_for_content(content: str) -> str:
    max_existing = max((len(match.group(0)) for match in FENCE_RE.finditer(content)), default=0)
    return "`" * max(3, max_existing + 1)


def language_for_path(path: Path) -> str:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "")


def normalize_ref_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


if __name__ == "__main__":
    sys.exit(main())
