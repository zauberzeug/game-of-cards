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


def _write_card(deck: Path, title: str) -> None:
    card = deck / title
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
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
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card / "log.md").write_text("")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / "deck"
        deck.mkdir()
        _write_card(deck, "first-open-card")
        _write_card(deck, "second-open-card")
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--board", "--max-rows", "-1", "--no-color"],
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
        print("defect present: negative --max-rows leaks a traceback")
        return 1
    if result.returncode == 0:
        print("defect present: negative --max-rows was accepted")
        return 1
    print("ok: negative --max-rows fails as CLI usage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
