#!/usr/bin/env python3
"""Replay refine-deck's citation-repair recipe over this repo's own deck.

The skill specifies the anchor as "that line's text at the card's creating
commit" (`goc/templates/skills/refine-deck/reference.md`, section
"Citation anchor check"). That is correct exactly once. After a repair pass
rewrites a cite's line number, the number was authored by the *repair*
commit, so reading it at the *creating* commit yields whatever unrelated
code happened to sit at that offset back then — and the recipe then
"relocates" the cite to wherever that unrelated text lives now.

This script computes, for every `file:line` cite on every open card:

  SHIPPED   anchor = cited_file @ card's creating commit  [line]
  CORRECTED anchor = cited_file @ commit that INTRODUCED this cite [line]

and reports the cites where the two disagree. The corrected anchor
degenerates to the creating commit for a cite no pass has ever touched, so
the two recipes agree on a virgin deck; they diverge only on repaired ones.

Exit 1 while the defect is present, 0 once the shipped recipe matches the
corrected one.
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
DECK = ROOT / ".game-of-cards" / "deck"

CITE_RE = re.compile(
    r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
    r"\.(?:py|md|ts|json|yaml|yml|sh|toml))[:#]L?(\d+)(?:\s*[-–]\s*L?(\d+))?(?![\w.])"
)
MIRROR = (
    "claude-plugin/",
    "codex-plugin/",
    "openclaw-plugin/",
    ".claude/",
    ".codex/",
    "goc/_vendor/",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout


def git_ok(*args: str):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


TRACKED = git("ls-files").splitlines()
TRACKED_SET = set(TRACKED)
BY_BASE = defaultdict(list)
for _p in TRACKED:
    BY_BASE[os.path.basename(_p)].append(_p)


def resolve(path: str):
    """Cards write `engine.py:N` for `goc/engine.py:N`; prefer a non-mirror match."""
    if path in TRACKED_SET:
        return path
    cands = BY_BASE.get(os.path.basename(path), [])
    pool = [p for p in cands if p.endswith("/" + path)] or cands
    pool = [p for p in pool if not p.startswith(MIRROR)] or pool
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    pool.sort(key=lambda p: (p.count("/"), len(p)))
    if pool[0].count("/") == pool[1].count("/") and len(pool[0]) == len(pool[1]):
        return None
    return pool[0]


_BLOB: dict = {}


def blob(commit: str, path: str):
    key = (commit, path)
    if key not in _BLOB:
        out = git_ok("show", f"{commit}:{path}")
        _BLOB[key] = out.split("\n") if out is not None else None
    return _BLOB[key]


_HEAD: dict = {}


def head_lines(path: str):
    if path not in _HEAD:
        try:
            _HEAD[path] = (ROOT / path).read_text(
                encoding="utf-8", errors="replace"
            ).split("\n")
        except OSError:
            _HEAD[path] = None
    return _HEAD[path]


def relocate(anchor: str, cur: list):
    """The skill's rule: rewrite only on a unique match of a non-trivial line."""
    if anchor is None or len(anchor.strip()) < 12:
        return None
    hits = [i + 1 for i, l in enumerate(cur) if l == anchor]
    if len(hits) != 1:
        stripped = anchor.strip()
        hits = [i + 1 for i, l in enumerate(cur) if l.strip() == stripped]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    deck_json = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "all", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    ).stdout
    cards = [c for c in json.loads(deck_json) if c["status"] in ("open", "active")]

    corrupts_correct = []   # shipped moves a cite that is right today
    wrong_target = []       # shipped moves a cite to a different line than corrected
    missed = 0              # shipped declines a cite the corrected recipe repairs
    agree = 0
    total = 0

    for card in cards:
        title = card["title"]
        readme = DECK / title / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        cites = [
            (m.group(0), m.group(1), int(m.group(2)))
            for m in CITE_RE.finditer(text)
        ]
        if not cites:
            continue

        rel = f".game-of-cards/deck/{title}/README.md"
        hist = git("log", "--format=%H", "--follow", "--", rel).split()
        if not hist:
            hist = git(
                "log", "--format=%H", "--follow", "--", f"deck/{title}/README.md"
            ).split()
        if not hist:
            continue
        hist.reverse()  # oldest first
        creating = hist[0]

        contents = []
        for c in hist:
            t = git_ok("show", f"{c}:{rel}")
            if t is None:
                t = git_ok("show", f"{c}:deck/{title}/README.md")
            contents.append(t or "")

        for raw, path, line in cites:
            target = resolve(path)
            if target is None:
                continue
            cur = head_lines(target)
            if cur is None:
                continue
            total += 1

            # CORRECTED anchor: the commit that introduced this exact cite token.
            intro, prev = None, False
            for c, body in zip(hist, contents):
                here = raw in body
                if here and not prev:
                    intro = c
                prev = here
            intro = intro or creating

            def anchor_of(commit):
                src = blob(commit, target)
                if src is None or line > len(src):
                    return None
                return src[line - 1]

            shipped_anchor = anchor_of(creating)
            corrected_anchor = anchor_of(intro)

            cur_line = cur[line - 1] if line <= len(cur) else None
            corrected_ok = cur_line is not None and cur_line == corrected_anchor
            shipped_ok = cur_line is not None and cur_line == shipped_anchor

            shipped_move = None if shipped_ok else relocate(shipped_anchor, cur)
            corrected_move = None if corrected_ok else relocate(corrected_anchor, cur)

            if shipped_move is not None and corrected_ok:
                corrupts_correct.append((title, raw, shipped_move))
            elif shipped_move is not None and shipped_move != corrected_move:
                wrong_target.append((title, raw, shipped_move, corrected_move))
            elif shipped_move is None and corrected_move is not None:
                missed += 1
            else:
                agree += 1

    print(f"open-card cites replayed: {total}\n")
    print("Shipped recipe (anchor at the card's CREATING commit) vs")
    print("corrected recipe (anchor at the commit that INTRODUCED the cite):\n")
    print(f"  moves a cite that is CORRECT today : {len(corrupts_correct)}")
    print(f"  moves a cite to the WRONG line     : {len(wrong_target)}")
    print(f"  declines a cite it should repair   : {missed}")
    print(f"  agrees with the corrected recipe   : {agree}")

    if corrupts_correct:
        print("\n  sample — correct cites the shipped recipe would move:")
        for title, raw, to in corrupts_correct[:3]:
            print(f"    {raw} in {title}")
            print(f"      -> would be rewritten to line {to}")
    if wrong_target:
        print("\n  sample — cites the shipped recipe would misplace:")
        for title, raw, got, want in wrong_target[:3]:
            print(f"    {raw} in {title}")
            print(f"      shipped -> {got}   corrected -> {want}")

    broken = len(corrupts_correct) + len(wrong_target) + missed
    if broken:
        print(
            f"\nDEFECT PRESENT: the shipped recipe disagrees with the corrected "
            f"anchor on {broken} of {total} cites. Running the documented pass a "
            f"second time rewrites correct citations onto unrelated code."
        )
        return 1
    print("\nPASS: the shipped recipe and the corrected anchor agree on every cite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
