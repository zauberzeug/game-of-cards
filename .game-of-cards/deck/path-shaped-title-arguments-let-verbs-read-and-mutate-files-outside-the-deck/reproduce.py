"""Prove that path-shaped title arguments escape DECK_DIR.

Builds a throwaway git repo with a deck (auto_commit on) plus a card
directory OUTSIDE it, then drives the engine as a subprocess:

1. `goc show /tmp/.../outside-card` reads the foreign file (exit 0).
2. `goc wait /tmp/.../outside-card --reason external` MUTATES the
   foreign README (writes `waiting_on: external`) and then crashes
   with an unhandled ValueError in `_git_auto_commit`
   (`p.relative_to(DECK_ROOT)`), i.e. the on-disk write lands but the
   documented atomic-commit contract is broken.
3. `goc new /tmp/evil` refuses the path-shaped title — the guard
   exists only on the creation verbs, not on resolution.

Exits 0 while the defect fires (each leg observed), 1 once fixed.
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


REPO = _repo_root()

CARD = """---
title: outside-card
status: open
contribution: medium
human_gate: none
tags: [bug]
advances: []
advanced_by: []
supersedes: []
superseded_by: []
summary: a card that lives outside any deck
---

# outside-card

## Definition of Done
- [ ] something
"""


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "consumer-repo"
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        (repo / ".game-of-cards" / "config.yaml").write_text(
            "workflow:\n  auto_commit: true\n"
        )
        subprocess.run(["git", "init", "-q", str(repo)], check=True)

        outside = tmp_path / "outside-card"
        outside.mkdir()
        (outside / "README.md").write_text(CARD)

        defect = True

        r = goc(repo, "show", str(outside))
        show_escaped = r.returncode == 0 and "outside-card" in r.stdout
        print(f"goc show <abs-path-outside-deck>: exit {r.returncode} "
              f"({'read the foreign file' if show_escaped else 'refused'})")

        r = goc(repo, "wait", str(outside), "--reason", "external")
        mutated = "waiting_on: external" in (outside / "README.md").read_text()
        crashed = "ValueError" in r.stderr and "is not in the subpath of" in r.stderr
        print(f"goc wait <abs-path-outside-deck>: exit {r.returncode} "
              f"(foreign file mutated: {mutated}; "
              f"unhandled ValueError after the write: {crashed})")

        r = goc(repo, "new", "/tmp/evil")
        new_refused = r.returncode != 0 and not Path("/tmp/evil").exists()
        print(f"goc new <abs-path>: exit {r.returncode} "
              f"({'refused (guard exists only at creation)' if new_refused else 'NOT refused'})")

        defect = show_escaped and mutated and crashed

    if defect:
        print("DEFECT CONFIRMED: title arguments resolve outside DECK_DIR; "
              "mutation lands on the foreign file, then auto-commit crashes.")
        return 0
    print("defect no longer fires (fixed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
