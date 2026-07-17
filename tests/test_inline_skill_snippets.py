import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve().with_name("inline_skill_snippets.py")
SPEC = importlib.util.spec_from_file_location("inline_skill_snippets", SCRIPT_PATH)
inline_skill_snippets = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["inline_skill_snippets"] = inline_skill_snippets
SPEC.loader.exec_module(inline_skill_snippets)


class InlineSkillSnippetsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.skills_dir = self.repo_root / "skills"
        self.output_dir = self.repo_root / "out-skills"

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, relative_path, content):
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_dry_run_inlines_single_plural_and_followed_by_references(self):
        self.write(
            "tests/docs/python/test_sample.py",
            """
def test_step(renderer):
    # [snippet:doc-step]
    renderer.step()
    renderer.step()
    # [/snippet:doc-step]
""",
        )
        self.write(
            "examples/c/minimal/main.cpp",
            """
int main() {
    // [snippet:create-renderer]
    ovrtx_renderer_t renderer = nullptr;
    check(ovrtx_create_renderer(nullptr, &renderer));
    // [/snippet:create-renderer]

    // [snippet:destroy-renderer]
    ovrtx_destroy_renderer(renderer);
    // [/snippet:destroy-renderer]
}
""",
        )
        self.write(
            "skills/sample/SKILL.md",
            """
# Sample

## Python

> **Source:** `tests/docs/python/test_sample.py` snippet `doc-step`

## C

> **Source:** `examples/c/minimal/main.cpp` snippets `create-renderer`, `destroy-renderer`
>
> Followed by: `tests/docs/python/test_sample.py` snippet `doc-step`
""",
        )
        self.write("skills/README.md", "This should be copied but not transformed.\n")

        stats = inline_skill_snippets.inline_skill_snippets(
            repo_root=self.repo_root,
            skills_dir=self.skills_dir,
            output_dir=self.output_dir,
            in_place=False,
            allow_missing=False,
        )

        transformed = (self.output_dir / "sample" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("> **Source:**", transformed)
        self.assertNotIn("> Followed by:", transformed)
        self.assertNotIn("\n>\n", transformed)
        self.assertIn("```python\nrenderer.step()\nrenderer.step()\n```", transformed)
        self.assertIn(
            "```cpp\novrtx_renderer_t renderer = nullptr;\n"
            "check(ovrtx_create_renderer(nullptr, &renderer));\n```",
            transformed,
        )
        self.assertIn("```cpp\novrtx_destroy_renderer(renderer);\n```", transformed)
        self.assertEqual(
            "This should be copied but not transformed.\n",
            (self.output_dir / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(4, stats.expanded_references)
        self.assertEqual(1, stats.transformed_files)
        self.assertEqual(0, stats.unresolved_references)

    def test_missing_reference_fails_by_default(self):
        self.write(
            "skills/sample/SKILL.md",
            "> **Source:** `tests/docs/python/test_missing.py` snippet `doc-missing`\n",
        )

        with self.assertRaises(inline_skill_snippets.InlineSkillSnippetError):
            inline_skill_snippets.inline_skill_snippets(
                repo_root=self.repo_root,
                skills_dir=self.skills_dir,
                output_dir=self.output_dir,
                in_place=False,
                allow_missing=False,
            )

    def test_allow_missing_leaves_reference_unchanged(self):
        self.write(
            "skills/sample/SKILL.md",
            "> **Source:** `tests/docs/python/test_missing.py` snippet `doc-missing`\n",
        )

        stats = inline_skill_snippets.inline_skill_snippets(
            repo_root=self.repo_root,
            skills_dir=self.skills_dir,
            output_dir=self.output_dir,
            in_place=False,
            allow_missing=True,
        )

        transformed = (self.output_dir / "sample" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(
            "> **Source:** `tests/docs/python/test_missing.py` snippet `doc-missing`\n",
            transformed,
        )
        self.assertEqual(1, stats.unresolved_references)

    def test_repository_skill_references_resolve(self):
        with tempfile.TemporaryDirectory() as output_dir:
            try:
                inline_skill_snippets.inline_skill_snippets(
                    repo_root=REPO_ROOT,
                    skills_dir=REPO_ROOT / "skills",
                    output_dir=Path(output_dir) / "ovrtx-skills",
                    in_place=False,
                    allow_missing=False,
                )
            except inline_skill_snippets.InlineSkillSnippetError as error:
                self.fail(str(error))


if __name__ == "__main__":
    unittest.main()
