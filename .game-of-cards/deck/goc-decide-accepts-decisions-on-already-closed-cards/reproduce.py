"""Reproduce: `goc decide` accepts decisions on already-closed cards.

Today (defect present): `goc decide` exits 0 on a `status: done` card whose
`human_gate` is `decision`, appends a `## Decision` block to the closed
README, lowers the gate, and prints "any agent can now claim this card."

After the guard lands: `goc decide` must exit non-zero on a terminal-status
card; the README and log.md must be unchanged.

Run with: uv run python .game-of-cards/deck/goc-decide-accepts-decisions-on-already-closed-cards/reproduce.py
"""

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
GOC = REPO / ".venv" / "bin" / "goc"
if not GOC.exists():
    GOC = "goc"


CARD_README = """\
---
title: closed-fixture
summary: "Closed fixture for terminal-status guard repro."
status: done
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] one
---

# closed-fixture

Original body.
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        card_dir = root / ".game-of-cards" / "deck" / "closed-fixture"
        card_dir.mkdir(parents=True)
        readme = card_dir / "README.md"
        readme.write_text(CARD_README)
        before = readme.read_text()

        result = subprocess.run(
            [
                str(GOC), "decide", "closed-fixture",
                "--decision", "go",
                "--because", "irrelevant on a closed card",
                "--no-commit",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            env={**os.environ, "GOC_COMMIT": "0"},
        )

        after = readme.read_text()
        readme_mutated = before != after
        log_created = (card_dir / "log.md").exists()

        print("--- goc decide stdout ---")
        print(result.stdout, end="")
        print("--- goc decide stderr ---")
        print(result.stderr, end="")
        print("--- summary ---")
        print(f"exit_code={result.returncode}")
        print(f"readme_mutated={readme_mutated}")
        print(f"log_created={log_created}")

        defect_present = (
            result.returncode == 0
            and readme_mutated
            and "any agent can now claim this card" in result.stdout
        )
        if defect_present:
            print("VERDICT: defect present — `goc decide` mutated a closed card and "
                  "claimed it as pullable")
            return 1
        if result.returncode != 0 and not readme_mutated:
            print("VERDICT: guard works — `goc decide` refused the terminal card "
                  "and left the README intact")
            return 0
        print("VERDICT: partial — neither the original defect nor the expected guard")
        return 2


if __name__ == "__main__":
    sys.exit(main())
