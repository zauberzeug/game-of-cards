"""Reproduce: `goc repair-edges` dry-run exits 0 even when the deck carries a
structural (unfixable) half-edge, while `--apply` exits 1 on the same deck.

Builds a throwaway deck with two reciprocal `advances` half-edges (each side
declares `advances` on the other but neither carries the reverse
`advanced_by`). Completing either reverse half would close a 2-cycle in the
advances graph, so both half-edges classify as *structural* — no verb can
auto-fix them. Then it runs the dry-run preview and `--apply` as subprocesses
and compares exit codes.

Before the fix: dry-run exits 0, apply exits 1 (the two modes disagree).
After the fix: both exit 1.
"""

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


REPO_ROOT = _repo_root()


def _card(title: str, advances: str) -> str:
    return f"""---
title: {title}
summary: ""
status: open
stage: null
contribution: medium
created: "2026-06-29T00:00:00Z"
closed_at: null
human_gate: none
advances:
  - {advances}
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (placeholder)
---

# {title}
"""


def _run(deck_root: Path, *args: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(deck_root),
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    return proc.returncode


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # A minimal repo marker so deck resolution is unambiguous.
        (root / "pyproject.toml").write_text("[project]\nname = 'tmp'\n")
        deck = root / ".game-of-cards" / "deck"
        for title, other in (("cyc-a", "cyc-b"), ("cyc-b", "cyc-a")):
            d = deck / title
            d.mkdir(parents=True)
            (d / "README.md").write_text(_card(title, other))
            (d / "log.md").write_text("")

        dry = _run(root, "repair-edges")
        apply = _run(root, "repair-edges", "--apply")

        print(f"dry-run exit code: {dry}")
        print(f"--apply  exit code: {apply}")
        print()
        if dry == apply:
            print(f"PASS: both modes agree (exit {dry}) on structural half-edges")
            return 0
        print(
            f"FAIL: dry-run exits {dry} but --apply exits {apply} on the same "
            "deck — the read-only preview hides the unfixable structural "
            "half-edge that --apply treats as a hard failure"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
