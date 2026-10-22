"""Regression guard: create-card's reproduce.py recipe must find goc's project root.

`Skill(create-card)` Step 6 ships a repo-root walk that every bug-class
`reproduce.py` is told to start with. It used to key on `pyproject.toml`,
which is this repo's marker, not goc's. In a consuming repo without one
(JS/TS, Go, Rust) the walk raised, and in a repo nested in a workspace whose
root has one it returned the workspace without error
(`reproduce-py-recipe-crashes-in-repos-without-a-pyproject-toml`).

A recipe is an instruction agents run literally, so these tests run it: the
python block after "parent-walk pattern" is extracted from the template,
written into fixture repos as `.game-of-cards/deck/some-bug/reproduce.py`,
executed, and its answer compared with `_walk_to_deck_root`, the walk every
goc verb uses. The expected root is derived from the engine, not restated
here, so a change on either side turns the build red. The pre-fix recipe is
fed through the same check to prove it can fire.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import _walk_to_deck_root  # noqa: E402

SKILL = Path("skills") / "create-card" / "SKILL.md"
TEMPLATE = ROOT / "goc" / "templates" / SKILL
SHIPPED_COPIES = [
    ROOT / base / SKILL for base in ("claude-plugin", "codex-plugin", "openclaw-plugin", ".claude", ".codex")
]

PRE_FIX_RECIPE = '''import sys
from pathlib import Path

def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")

sys.path.insert(0, str(_repo_root()))
'''

# label -> (project file at the repo root, where a pyproject.toml sits)
FIXTURES = {
    "JS repo": ("package.json", None),
    "Go repo": ("go.mod", None),
    "repo in a pyproject workspace": ("package.json", "workspace"),
    "Python repo": (None, "repo"),
}


def recipe_from(skill_md: Path) -> str:
    """The python block after "parent-walk pattern" in a create-card SKILL.md."""
    text = skill_md.read_text(encoding="utf-8")
    tail = text[text.index("**parent-walk pattern**") :]
    match = re.search(r"```python\n(.*?)```", tail, re.S)
    assert match is not None, f"{skill_md}: no python recipe block after 'parent-walk pattern'"
    return match.group(1)


def recipe_problems(recipe: str) -> list[str]:
    """Run `recipe` in every fixture; one line per fixture where it misses the engine's root."""
    problems = []
    for label, (project_file, pyproject) in FIXTURES.items():
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            repo = base / "app"
            card = repo / ".game-of-cards" / "deck" / "some-bug"
            card.mkdir(parents=True)
            (repo / ".git").mkdir()
            if project_file:
                (repo / project_file).write_text("{}\n", encoding="utf-8")
            if pyproject:
                where = repo if pyproject == "repo" else base
                (where / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
            script = card / "reproduce.py"
            script.write_text(recipe + "\nprint(_repo_root())\n", encoding="utf-8")
            run = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True)
            crash = (run.stderr.strip().splitlines() or ["no stderr"])[-1]
            got = run.stdout.strip() if run.returncode == 0 else f"crash: {crash}"
            expected = str(_walk_to_deck_root(card))
            if got != expected:
                problems.append(f"{label}: recipe says {got.replace(str(base), '<tmp>')}, engine root is <tmp>/app")
    return problems


class ShippedRecipeTest(unittest.TestCase):
    def test_template_recipe_resolves_the_engine_root(self) -> None:
        self.assertEqual(recipe_problems(recipe_from(TEMPLATE)), [])

    def test_every_shipped_copy_carries_the_template_recipe(self) -> None:
        expected = recipe_from(TEMPLATE)
        for copy in SHIPPED_COPIES:
            with self.subTest(copy=str(copy.relative_to(ROOT))):
                self.assertEqual(recipe_from(copy), expected)


class PreFixRecipeFiresTest(unittest.TestCase):
    def test_pyproject_recipe_misses_the_root_outside_a_plain_python_repo(self) -> None:
        problems = recipe_problems(PRE_FIX_RECIPE)
        self.assertEqual([p.split(":")[0] for p in problems], ["JS repo", "Go repo", "repo in a pyproject workspace"])
        self.assertIn("repo in a pyproject workspace: recipe says <tmp>, engine root is <tmp>/app", problems)


if __name__ == "__main__":
    unittest.main()
