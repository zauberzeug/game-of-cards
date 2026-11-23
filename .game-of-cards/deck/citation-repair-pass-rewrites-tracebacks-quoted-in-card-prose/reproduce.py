#!/usr/bin/env python3
"""Reproduce: a traceback quoted in card PROSE has no record test.

The refine-deck citation scope rule (SKILL.md § "Defunct file:line
citations") puts a dated record — pasted grep output, a reproduce.py
transcript, a quoted error — out of scope, but its only mechanical test
is for fenced blocks: a fenced cite is a record unless a `#` / `//`
comment marker precedes it. Outside a fence every cite reads as an
assertion about current code, so a pass relocates it.

This script does two things:

1. Scans every live (open/active) card's body OUTSIDE fenced blocks and
   blockquotes for a cite in a quoted-output shape: a traceback frame
   chain (`path:N → N`) or a line that says "traceback". Those cites are
   records the rule cannot see.
2. Replays the history of the known instance: every commit that changed
   the quoted frame's number, and whether the scope rule (eae2bea9,
   2026-09-01) had already shipped at that commit.

Exit 1 while any live card carries such a prose cite; 0 once none does.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"
CITE = re.compile(r"[\w./-]+\.(?:py|md|ya?ml|json|ts|sh|toml|txt):\d+(?:-\d+)?")
FENCE = re.compile(r"^\s*(```|~~~)")
FRAME_CHAIN = re.compile(r"\s*(?:→|->)\s*`?\d")
STATUS = re.compile(r"^status:\s*(\S+)", re.M)
INSTANCE = "repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field"
FRAME = re.compile(r"traceback ending .*? at `engine\.py:(\d+) → (\d+)`")
RULE_COMMIT = "eae2bea9"  # fix(refine-deck): scope a cite by what it claims


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def split(text: str) -> tuple[str, str]:
    m = re.match(r"(---\n.*?\n---[ \t]*\n)(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def prose_records(text: str) -> list[tuple[int, str, str]]:
    head, body = split(text)
    offset = head.count("\n")
    hits, in_fence = [], False
    for i, line in enumerate(body.split("\n"), start=offset + 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith(">"):
            continue
        for m in CITE.finditer(line):
            rest = line[m.end():].lstrip("`")
            if FRAME_CHAIN.match(rest) or "traceback" in line.lower():
                hits.append((i, m.group(0), line.strip()))
    return hits


def scan() -> int:
    live = 0
    found = []
    for readme in sorted(DECK.glob("*/README.md")):
        text = readme.read_text(encoding="utf-8")
        head, _ = split(text)
        status = STATUS.search(head)
        if not status or status.group(1) not in ("open", "active"):
            continue
        live += 1
        for line_no, token, line in prose_records(text):
            found.append((readme.parent.name, line_no, token, line))
    print(f"Live cards scanned: {live}")
    print(
        "Cites inside a quoted traceback or frame chain, in prose "
        f"(outside fences and blockquotes): {len(found)}"
    )
    for card, line_no, token, line in found:
        print(f"  {card} L{line_no}: {token}")
        print(f"      {line[:110]}")
    return len(found)


def replay() -> None:
    readme = f".game-of-cards/deck/{INSTANCE}/README.md"
    log = git("log", "--follow", "--format=%H %h %cs", "--", readme).splitlines()
    log.reverse()
    print(f"\nHistory of the frame quoted on {INSTANCE}")
    print(f"(first number of `engine.py:N → M`; scope rule = {RULE_COMMIT}):")
    previous = filed = None
    after_rule = 0
    for row in log:
        full, short, day = row.split()
        version = git("show", f"{full}:{readme}")
        m = FRAME.search(version)
        if m is None:
            continue
        number = m.group(1)
        if number == previous:
            continue
        shipped = subprocess.run(
            ["git", "merge-base", "--is-ancestor", RULE_COMMIT, full],
            cwd=ROOT, capture_output=True,
        ).returncode == 0
        if previous is None:
            note = "as filed"
            filed = number
        elif number == filed:
            note = "restored to the filed number by hand"
        elif shipped:
            note = "rewritten AFTER the scope rule shipped"
            after_rule += 1
        else:
            note = "rewritten before the scope rule"
        print(f"  {short} {day}  {number:>5} → {m.group(2)}  {note}")
        previous = number
    print(f"Rewrites after the rule shipped: {after_rule}")


def main() -> int:
    live_hits = scan()
    replay()
    if live_hits:
        print(
            "\nDEFECT PRESENT: a record quoted in prose is indistinguishable "
            "from a cite about current code under the scope rule's only test, "
            "so the next pass that does not read the line rewrites it."
        )
        return 1
    print("\nOK: no live card quotes a traceback or frame chain outside a fence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
