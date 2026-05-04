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


def _write_open_card(deck: Path) -> None:
    card = deck / "open-card"
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        "title: open-card\n"
        "summary: Open card\n"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-04\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] still open\n"
        "---\n\n"
        "# open-card\n"
    )
    (card / "log.md").write_text("")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        deck.mkdir()
        _write_open_card(deck)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--since", "2026-05-04"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    combined = f"{result.stdout}\n{result.stderr}"
    print(f"exit={result.returncode}")
    print(f"open_card_rendered={'open-card' in result.stdout}")
    if "Traceback" in combined:
        print("defect present: bare --since leaks a traceback")
        return 1
    if result.returncode == 0 and "open-card" not in result.stdout:
        print("defect present: bare --since silently hides the open queue")
        return 1
    print("ok: bare --since no longer silently hides open cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
