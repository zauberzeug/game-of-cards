"""Reproduce: `goc --advanced-by X` / `--advances X` apply the open-only
status default, so a relationship endpoint that has since closed (done /
disproved / superseded) vanishes from the result.

The deck-as-record contract (AGENTS.md "Deck as scheduler vs deck as
record") says closed-card relationship edges are first-class and a cold
reader must be able to walk them to reconstruct history. An explicit
edge filter is the natural way to ask "what is connected to X" — but it
silently truncates to *open* endpoints.

Run: uv run python deck/<title>/reproduce.py
Exit status: 0 when the defect FIRES (open-only result drops the closed
endpoint), 1 once the fix lands (edge filters span every status).
"""

import json
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


REPO = _repo_root()

PARENT = "synthetic-closed-parent-card"
CHILD = "synthetic-closed-child-card"

PARENT_MD = f"""---
title: {PARENT}
status: done
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: "2026-01-02T00:00:00Z"
human_gate: none
advances: []
advanced_by:
- {CHILD}
tags: [bug]
definition_of_done: |
  - [x] done
---

# parent
"""

CHILD_MD = f"""---
title: {CHILD}
status: done
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: "2026-01-03T00:00:00Z"
human_gate: none
advances:
- {PARENT}
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] done
---

# child
"""


def _run(cwd: Path, *args: str) -> list:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env["NO_COLOR"] = "1"
    out = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--json"],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"goc {args} failed: {out.stderr}")
    return json.loads(out.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck = root / ".game-of-cards" / "deck"
        (deck / PARENT).mkdir(parents=True)
        (deck / CHILD).mkdir(parents=True)
        (deck / PARENT / "README.md").write_text(PARENT_MD)
        (deck / PARENT / "log.md").write_text("")
        (deck / CHILD / "README.md").write_text(CHILD_MD)
        (deck / CHILD / "log.md").write_text("")

        # The child is `advanced_by` the parent and `advances` the parent's
        # inverse — both are CLOSED. Ask the deck "what advances the parent?"
        default = {c["title"] for c in _run(root, "--advances", PARENT)}
        explicit_all = {c["title"] for c in _run(root, "--advances", PARENT, "--status", "all")}

        print(f"--advances {PARENT}              -> {sorted(default)}")
        print(f"--advances {PARENT} --status all -> {sorted(explicit_all)}")

        # Same question via the inverse edge filter.
        default_by = {c["title"] for c in _run(root, "--advanced-by", CHILD)}
        explicit_by = {c["title"] for c in _run(root, "--advanced-by", CHILD, "--status", "all")}
        print(f"--advanced-by {CHILD}              -> {sorted(default_by)}")
        print(f"--advanced-by {CHILD} --status all -> {sorted(explicit_by)}")

        defect_fires = (CHILD not in default and CHILD in explicit_all) or (
            PARENT not in default_by and PARENT in explicit_by
        )
        if defect_fires:
            print(
                "\nDEFECT FIRES: an explicit edge filter dropped a CLOSED "
                "relationship endpoint that --status all surfaces."
            )
            return 0
        print("\nFixed: edge filters surface closed relationship endpoints by default.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
