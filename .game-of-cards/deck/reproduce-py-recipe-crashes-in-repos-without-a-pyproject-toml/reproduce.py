"""Run create-card's shipped reproduce.py repo-root recipe in fixture repos.

The recipe is extracted verbatim from the source-of-truth template
(`goc/templates/skills/create-card/SKILL.md`, the python block after
"parent-walk pattern"), written into each fixture as
`.game-of-cards/deck/some-bug/reproduce.py`, and executed. Its answer is
compared with the engine's own project-root walk (`_walk_to_deck_root`),
which every goc verb uses to find the same repo.

Exits 0 when the recipe resolves the engine's root in every fixture.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError("repo root (.game-of-cards/) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc.engine import _walk_to_deck_root  # noqa: E402

TEMPLATE = ROOT / "goc" / "templates" / "skills" / "create-card" / "SKILL.md"


def _recipe() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    tail = text[text.index("**parent-walk pattern**"):]
    match = re.search(r"```python\n(.*?)```", tail, re.S)
    assert match is not None, "create-card no longer ships a python recipe block"
    return match.group(1) + "\nprint(_repo_root())\n"


def _fixture(base: Path, *, pyproject: str | None, marker: str | None) -> Path:
    """A git repo `base/app` holding a deck, plus an optional project marker.

    `pyproject` places a pyproject.toml at the repo root (`"repo"`), at the
    enclosing workspace (`"workspace"`), or nowhere (None).
    """
    repo = base / "app"
    (repo / ".game-of-cards" / "deck" / "some-bug").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if marker:
        (repo / marker).write_text("{}\n", encoding="utf-8")
    if pyproject is not None:
        where = {"repo": repo, "workspace": base}[pyproject]
        (where / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return repo


def _run_recipe(repo: Path) -> str:
    script = repo / ".game-of-cards" / "deck" / "some-bug" / "reproduce.py"
    script.write_text(_recipe(), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True)
    if r.returncode != 0:
        return "CRASH: " + (r.stderr.strip().splitlines() or ["?"])[-1]
    return r.stdout.strip()


def main() -> int:
    cases = [
        ("JS repo (package.json, no pyproject.toml)", dict(pyproject=None, marker="package.json")),
        ("Go repo (go.mod, no pyproject.toml)", dict(pyproject=None, marker="go.mod")),
        ("repo nested in a workspace whose root has pyproject.toml", dict(pyproject="workspace", marker="package.json")),
        ("Python repo (pyproject.toml at the repo root)", dict(pyproject="repo", marker=None)),
    ]
    failures = 0
    for label, spec in cases:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            repo = _fixture(base, **spec)
            engine_root = _walk_to_deck_root(repo / ".game-of-cards" / "deck" / "some-bug")
            got = _run_recipe(repo)
            ok = got == str(engine_root)
            failures += not ok
            shown = got.replace(str(base), "<tmp>")
            print(f"[{'OK' if ok else 'FAIL'}] {label}")
            print(f"       engine root : {str(engine_root).replace(str(base), '<tmp>')}")
            print(f"       recipe says : {shown}")
    print()
    print(f"{failures} of {len(cases)} fixtures: the shipped recipe disagrees with the engine's root")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
