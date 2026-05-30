"""Reproduce: `_emit_worker` silently drops unknown sub-keys.

Run: `uv run python .game-of-cards/deck/emit-frontmatter-silently-strips-unknown-worker-sub-keys/reproduce.py`

Constructs a card whose `worker:` mapping carries the documented `who` and
`where` plus two forward-looking sub-keys (`since`, `role`), invokes the real
`goc wait` verb (which round-trips frontmatter through `emit_frontmatter`),
and prints the before/after `worker:` line.

Exit code: 0 when the bug fires (extra keys dropped), 1 when the round-trip
preserves them.
"""

from __future__ import annotations

import os
import shutil
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
PYTHON = REPO / ".venv" / "bin" / "python"

CARD = "test-extra-worker"
README = f"""---
title: {CARD}
status: open
human_gate: none
contribution: low
tags: []
worker: {{who: alice, where: feat/x, since: "2026-01-01", role: lead}}
created: "2026-05-30"
closed_at: null
advances: []
advanced_by: []
supersedes: []
superseded_by: []
definition_of_done: |
  - [ ] thing
summary: t
---
body
"""


def _worker_line(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("worker:"):
            return line
    return "(no worker line)"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-worker-strip-"))
    try:
        card_dir = tmp / ".game-of-cards" / "deck" / CARD
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(README)
        (card_dir / "log.md").write_text("")

        before = (card_dir / "README.md").read_text()
        print("before:", _worker_line(before))

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO)
        # Drive the real verb via the source-tree engine. `--no-commit`
        # because the tempdir is not a git repo and we only care about the
        # frontmatter rewrite.
        result = subprocess.run(
            [str(PYTHON), "-m", "goc.cli", "wait", CARD, "--reason", "external", "--no-commit"],
            cwd=str(tmp),
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("goc wait failed:", result.stderr, file=sys.stderr)
            return 2

        after = (card_dir / "README.md").read_text()
        print("after: ", _worker_line(after))

        import re

        def keys(line: str) -> set[str]:
            inside = re.search(r"\{(.*)\}", line)
            if not inside:
                return set()
            return {pair.split(":", 1)[0].strip() for pair in inside.group(1).split(",") if ":" in pair}

        dropped = sorted(keys(_worker_line(before)) - keys(_worker_line(after)))
        if dropped:
            print(f"DROPPED KEYS: {dropped}")
            return 0
        print("no keys dropped — bug appears fixed")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
