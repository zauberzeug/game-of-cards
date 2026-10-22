#!/usr/bin/env python3
"""Reproduce board-done-column-and-closed-views-sort-by-scheduler-value-hiding-recent-closures.

Builds a scratch deck holding 21 `high` cards closed in May (one more than
the board's default 20-row cap) plus three cards closed in the last three
days. The recent three carry contributions that run against their recency
(the newest is `low`, the oldest `high`), so an order keyed on value and
an order keyed on `closed_at` disagree about every one of them. Then it
asks the real CLI three questions:

1. Does `goc --board` show the three recent closures in its DONE column?
2. Does `goc --closed-since 7d` list them most-recent-first?
3. Does `goc --done --json` lead with the most recent closure?

Exit 0: every answer is yes — recent closures lead every closed-card view
(hypothesis disproved, or the fix landed).
Exit 1: some closed-card view buries recent closures (hypothesis confirmed).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

CARD = """---
title: {title}
summary: "Fixture card {title}."
status: done
stage: null
contribution: {contribution}
created: "{created}"
closed_at: "{closed_at}"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: fixture
---

# {title}
"""


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_deck(root: Path) -> list[str]:
    """Write the fixture deck; return the recent titles, newest first."""
    deck = root / ".game-of-cards" / "deck"
    for i in range(21):
        title = f"may-closure-{i:02d}"
        (deck / title).mkdir(parents=True)
        (deck / title / "README.md").write_text(CARD.format(
            title=title, contribution="high", created="2026-04-01T00:00:00Z",
            closed_at=_stamp(datetime(2026, 5, 1 + i, 12, tzinfo=timezone.utc)),
        ))
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    recent = [("recent-low", "low", 1), ("recent-medium", "medium", 2),
              ("recent-high", "high", 3)]
    for title, contribution, days_ago in recent:
        (deck / title).mkdir(parents=True)
        (deck / title / "README.md").write_text(CARD.format(
            title=title, contribution=contribution,
            created="2026-09-01T00:00:00Z",
            closed_at=_stamp(now - timedelta(days=days_ago)),
        ))
    return [title for title, _, _ in recent]


def run_goc(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"goc {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def done_column(board: str) -> list[str]:
    lines = board.splitlines()
    header = [cell.strip() for cell in lines[0].split(" | ")]
    i = header.index("DONE")
    cells = []
    for line in lines[2:]:
        row = line.split(" | ")
        if i < len(row) and row[i].strip():
            cells.append(row[i].strip().split(" ")[0])
    return cells


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        recent = build_deck(root)

        column = done_column(run_goc(root, "--board", "--no-color"))
        shown = [t for t in recent if t in column]
        print(f"1. board DONE column (top 3): {column[:3]}; recent shown: {shown}")
        if shown != recent:
            failures.append(f"board DONE column hides {sorted(set(recent) - set(shown))}")

        window = [c["title"] for c in json.loads(
            run_goc(root, "--closed-since", "7d", "--json", "--slim"))]
        print(f"2. --closed-since 7d order: {window}")
        if window != recent:
            failures.append(f"--closed-since 7d lists {window}, not newest-first {recent}")

        done = [c["title"] for c in json.loads(run_goc(root, "--done", "--json", "--slim"))]
        print(f"3. --done --json leads with: {done[0]} (rank of {recent[0]}: "
              f"{done.index(recent[0]) + 1} of {len(done)})")
        if done[0] != recent[0]:
            failures.append(f"--done leads with {done[0]}, not the newest closure {recent[0]}")

    if failures:
        for failure in failures:
            print(f"CONFIRMED: {failure}")
        return 1
    print("recent closures lead every closed-card view")
    return 0


if __name__ == "__main__":
    sys.exit(main())
