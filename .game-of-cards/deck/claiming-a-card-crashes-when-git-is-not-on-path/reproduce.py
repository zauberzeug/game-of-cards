"""Prove `_auto_populate_worker` raises FileNotFoundError when git is absent.

Strips git from PATH, then calls the claim verb's worker auto-population.
Before the fix: prints the DEFECT line and exits 1. After the fix: the call
returns the card text unchanged and the script exits 0.
"""

import os
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD_TEXT = (
    "---\n"
    "title: demo-card\n"
    "summary: demo-card\n"
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    "created: 2026-07-05\n"
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] PROCESS: test card\n"
    "---\n\n"
    "# demo\n"
)


def main() -> int:
    fm, _ = engine.parse_frontmatter(CARD_TEXT)
    card = type("C", (), {"frontmatter": fm})()

    # Empty dir on PATH: any `git ...` subprocess raises FileNotFoundError.
    with tempfile.TemporaryDirectory() as empty:
        old_path = os.environ.get("PATH")
        os.environ["PATH"] = empty
        print("PATH stripped of git; calling _auto_populate_worker ...")
        try:
            out = engine._auto_populate_worker(CARD_TEXT, card, None, None)
        except FileNotFoundError as e:
            print(f"DEFECT: FileNotFoundError raised: {e}")
            return 1
        finally:
            if old_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old_path

    assert out == CARD_TEXT, "git-less claim must leave the card text unchanged"
    print("OK: git-less claim degrades gracefully (card text unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
