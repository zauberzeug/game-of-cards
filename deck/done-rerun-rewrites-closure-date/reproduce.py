from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def _write_done_card(deck: Path) -> Path:
    card = deck / "already-done-card"
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        "title: already-done-card\n"
        "summary: already closed\n"
        "status: done\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-01-01\n"
        "closed_at: 2026-01-02\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [x] already complete\n"
        "---\n\n"
        "# already-done-card\n"
    )
    (card / "log.md").write_text("")
    return card


def _frontmatter_line(readme: Path, key: str) -> str:
    prefix = f"{key}:"
    for line in readme.read_text().splitlines():
        if line.startswith(prefix):
            return line
    raise RuntimeError(f"{key} not found")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        deck.mkdir()
        card = _write_done_card(deck)
        readme = card / "README.md"
        before = _frontmatter_line(readme, "closed_at")

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "done", "already-done-card"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        after = _frontmatter_line(readme, "closed_at")

    print(f"exit={result.returncode}")
    print(f"stdout={result.stdout.strip()}")
    print(f"before={before}")
    print(f"after={after}")
    if result.returncode != 0:
        print(result.stderr.strip())
        return 1
    if after != before:
        print("defect present: rerunning goc done rewrites closed_at")
        return 1
    print("ok: rerunning goc done leaves closed_at unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
