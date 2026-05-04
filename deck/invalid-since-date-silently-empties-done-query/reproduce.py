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


def _write_done_card(deck: Path) -> None:
    card = deck / "closed-card"
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        "title: closed-card\n"
        "summary: Closed card\n"
        "status: done\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-01\n"
        "closed_at: 2026-05-04\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [x] closed\n"
        "---\n\n"
        "# closed-card\n"
    )
    (card / "log.md").write_text("")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        deck.mkdir()
        _write_done_card(deck)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--done", "--since", "nope"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    combined = f"{result.stdout}\n{result.stderr}"
    print(f"exit={result.returncode}")
    print(f"traceback={'Traceback' in combined}")
    if "Traceback" in combined:
        print("defect present: invalid --since leaks a traceback")
        return 1
    if result.returncode == 0:
        print("defect present: invalid --since was accepted")
        return 1
    print("ok: invalid --since fails as CLI usage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
