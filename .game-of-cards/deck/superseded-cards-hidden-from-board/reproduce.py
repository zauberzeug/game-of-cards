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


def _write_card(deck: Path) -> None:
    card = deck / "superseded-card"
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        "title: superseded-card\n"
        "summary: Hidden on board\n"
        "status: superseded\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-04\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [x] obsolete\n"
        "---\n\n"
        "# superseded-card\n"
    )
    (card / "log.md").write_text("")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "deck").mkdir()
        _write_card(cwd / "deck")
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--board", "--no-color"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    print(f"exit={result.returncode}")
    print(f"has_superseded_column={'SUPERSEDED' in result.stdout}")
    print(f"has_superseded_card={'superseded-card' in result.stdout}")
    if result.returncode != 0:
        print(result.stderr.strip())
        return 1
    if "SUPERSEDED" not in result.stdout or "superseded-card" not in result.stdout:
        print("defect present: superseded cards are hidden from goc --board")
        return 1
    print("ok: superseded cards appear on goc --board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
