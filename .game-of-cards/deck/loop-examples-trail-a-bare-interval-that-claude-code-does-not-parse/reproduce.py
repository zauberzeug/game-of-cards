#!/usr/bin/env python3
"""Reproduce loop-examples-trail-a-bare-interval-that-claude-code-does-not-parse.

Claude Code's /loop grammar takes an interval either as a leading bare token
(`/loop 30m /pull-card`) or as a trailing clause (`every 2 hours`). This
scans every shipped template for backticked `/loop ...` examples whose first
argument is not an interval while a bare interval token (`30m`) trails it.

Exit 0: no such example (defect gone). Exit 1: offending examples listed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
TEMPLATES = ROOT / "goc" / "templates"
LOOP = re.compile(r"`/loop ([^`]+)`")
INTERVAL = re.compile(r"^\d+[smhd]$")


def offenders() -> list[str]:
    found = []
    for path in sorted(TEMPLATES.rglob("*")):
        if path.suffix not in {".md", ".yaml"} or not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in LOOP.finditer(line):
                tokens = match.group(1).split()
                if tokens and not INTERVAL.match(tokens[0]) and any(
                    INTERVAL.match(t) for t in tokens[1:]
                ):
                    rel = path.relative_to(ROOT)
                    found.append(f"{rel}:{lineno}: {match.group(0)}")
    return found


def main() -> int:
    found = offenders()
    for item in found:
        print(f"trailing bare interval: {item}")
    if found:
        print(f"CONFIRMED: {len(found)} /loop example(s) outside the documented grammar")
        return 1
    print("every shipped /loop example leads with its interval or has none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
