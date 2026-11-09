"""Reproduce: the closed_at backfill stamps a card's latest edit date, not its closure date.

Builds a throwaway git repo holding one card and three commits with pinned
dates:

  T0 2026-01-01  card filed (status: open)
  T1 2026-02-01  card closed (status: superseded) — the closure
  T2 2026-03-01  a later body edit (a cross-reference rewrite)

`closed_at` stays null throughout, the legacy shape the script exists to
backfill. A copy of this checkout's `scripts/backfill_terminal_closed_at.py`
(copied at run time, so the probe always tests the current script) is then
run with `--apply` inside the throwaway repo, against the engine from this
source tree, and the written `closed_at` is read back through the engine's
frontmatter parser.

Expected (after a fix): closed_at == T1, the closure commit.
Defect:                 closed_at == T2, the latest README edit.

Exit codes: 0 = defect no longer fires (T1 written), 1 = defect fires (T2
written), 2 = the harness or a precondition is broken — git missing, the
script failing, no card reported, or any other value written. This repo's
own deck is never touched.

Run with:  uv run python .game-of-cards/deck/backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date/reproduce.py
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
        if (p / ".game-of-cards").is_dir() and (p / "goc" / "engine.py").is_file():
            return p
        p = p.parent
    raise RuntimeError("goc source tree not found")


REPO = _repo_root()
SCRIPT = REPO / "scripts" / "backfill_terminal_closed_at.py"
TITLE = "old-card"
T0, T1, T2 = "2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z", "2026-03-01T00:00:00Z"

CARD = """---
title: old-card
summary: A card that a later card superseded.
status: {status}
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
supersedes: []
superseded_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: placeholder
---

# Old card

{body}
"""


def _git(cwd: Path, *args: str, date: str | None = None) -> None:
    env = os.environ.copy()
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(
        ["git", "-c", "user.name=probe", "-c", "user.email=probe@example.invalid",
         "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
        cwd=cwd, env=env, check=True, capture_output=True, text=True,
    )


def main() -> int:
    if shutil.which("git") is None:
        print("PRECONDITION: git not on PATH")
        return 2
    if not SCRIPT.is_file():
        print(f"PRECONDITION: {SCRIPT.relative_to(REPO)} missing")
        return 2
    sys.path.insert(0, str(REPO))
    from goc.engine import parse_frontmatter

    with tempfile.TemporaryDirectory() as tmp_name:
        repo = Path(tmp_name) / "consumer"
        card = repo / ".game-of-cards" / "deck" / TITLE / "README.md"
        card.parent.mkdir(parents=True)
        (repo / "scripts").mkdir()
        shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
        try:
            _git(repo, "init", "-q")
            card.write_text(CARD.format(status="open", body="Filed."))
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "file card", date=T0)
            card.write_text(CARD.format(status="superseded", body="Filed."))
            _git(repo, "commit", "-q", "-am", "close card (superseded)", date=T1)
            card.write_text(CARD.format(status="superseded", body="Filed. See [new-card](../new-card/)."))
            _git(repo, "commit", "-q", "-am", "rewrite a cross-reference", date=T2)
        except subprocess.CalledProcessError as exc:
            print(f"HARNESS BROKEN: git {exc.args[1]} failed: {exc.stderr.strip()}")
            return 2

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)
        res = subprocess.run(
            [sys.executable, str(repo / "scripts" / SCRIPT.name), "--apply"],
            cwd=repo, env=env, capture_output=True, text=True,
        )
        print(f"$ backfill_terminal_closed_at.py --apply   (exit {res.returncode})")
        for line in (res.stdout + res.stderr).strip().splitlines():
            print(f"  {line}")
        if res.returncode != 0 or f"applied: {TITLE}" not in res.stdout:
            print("HARNESS BROKEN: the script did not report writing the card")
            return 2

        fm, _body = parse_frontmatter(card.read_text())
        written = fm.get("closed_at")

    print(f"\nclosure commit (T1) : {T1}")
    print(f"latest edit    (T2) : {T2}")
    print(f"closed_at written   : {written}")
    if written == T2:
        print("\nDEFECT PRESENT: --apply stamped the latest README edit (T2), not the closure (T1).")
        return 1
    if written == T1:
        print("\nDefect no longer fires: --apply stamped the closure commit (T1).")
        return 0
    print("\nHARNESS BROKEN: closed_at is neither T1 nor T2")
    return 2


if __name__ == "__main__":
    sys.exit(main())
