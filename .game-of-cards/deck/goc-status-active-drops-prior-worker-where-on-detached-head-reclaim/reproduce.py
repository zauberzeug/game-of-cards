"""Reproduce: `goc status … active` drops prior `worker.where` on detached HEAD.

Scaffolds an isolated git repo with a single open card carrying
`worker: {who: alice, where: feature/x}`, detaches HEAD, then runs
`goc status … active`. The bug: the worker field is silently rewritten
to bare-string `worker: alice` — the prior `where: feature/x` record
is destroyed even though no explicit `--worker-where` override was
given.

Exit codes:
  0  — defect did NOT fire (prior `where` preserved or transition refused)
  2  — defect FIRED (prior `where` silently dropped)
"""

from __future__ import annotations

import os
import re
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
GOC = [sys.executable, "-m", "goc.cli"]


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=30)


CARD_FRONTMATTER = """---
title: demo-card
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (replace with real criteria)
worker: {who: alice, where: feature/x}
---

# demo-card

(body)
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # Bootstrap an isolated git repo with the minimum goc layout.
        _run(["git", "init", "-q", "-b", "main"], tmp)
        _run(["git", "config", "user.email", "bob@example.com"], tmp)
        _run(["git", "config", "user.name", "bob"], tmp)
        (tmp / ".game-of-cards" / "deck" / "demo-card").mkdir(parents=True)
        (tmp / ".game-of-cards" / "deck" / "demo-card" / "README.md").write_text(CARD_FRONTMATTER)
        (tmp / ".game-of-cards" / "deck" / "demo-card" / "log.md").write_text("")
        _run(["git", "add", "."], tmp)
        _run(["git", "commit", "-qm", "seed"], tmp)

        # Detach HEAD so `git rev-parse --abbrev-ref HEAD` returns "HEAD".
        head_sha = _run(["git", "rev-parse", "HEAD"], tmp).stdout.strip()
        _run(["git", "checkout", "-q", "--detach", head_sha], tmp)

        # Sanity: confirm we are actually detached.
        abbrev = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], tmp).stdout.strip()
        print(f"abbrev-ref HEAD before claim: {abbrev!r}")

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)

        # Re-claim the card.
        r = _run([*GOC, "status", "demo-card", "active", "--no-commit"], tmp, env=env)
        if r.returncode != 0:
            print(f"goc status returned non-zero ({r.returncode}); refusal is option 2 — defect did NOT fire")
            print(f"  stderr: {r.stderr.strip()}")
            return 0

        body = (tmp / ".game-of-cards" / "deck" / "demo-card" / "README.md").read_text()
        worker_match = re.search(r"^worker:.*$", body, re.MULTILINE)
        worker_line = worker_match.group(0) if worker_match else "<no worker line>"
        print(f"worker field after detached-HEAD reclaim: {worker_line}")

        if "where: feature/x" in worker_line:
            print("RESULT: prior `where` preserved — defect did NOT fire.")
            return 0

        print("RESULT: prior `where: feature/x` was silently dropped — defect FIRED.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
