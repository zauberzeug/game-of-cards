#!/usr/bin/env python3
"""Range cites the citation-repair recipe left incoherent.

A range cite (`file.py:120-140`) names a block of code.  The recipe in
`goc/templates/skills/refine-deck/reference.md` § "Citation anchor check"
maps its two endpoints as independent single-line lookups, so nothing
requires the repaired pair to still bound a block.  This script finds every
range cite in the deck that no longer does, and blames the commit that
broke it.

Exits 0 when the deck holds no incoherent range cite.
"""
import re
import subprocess
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
DECK = ROOT / ".game-of-cards" / "deck"

# A range cite: <path>:<start>-<end>, optionally with the "~about here" marker.
RANGE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|ts|json|yaml|yml|sh|toml|js|cfg|txt|ini))"
    r":(~?)(\d+)-(\d+)(?![0-9])"
)

# A block wider than this is not a block; the two endpoints have come apart.
MAX_PLAUSIBLE_SPAN = 500


def incoherent(start: int, end: int) -> str | None:
    if start > end:
        return "start past end"
    if end - start > MAX_PLAUSIBLE_SPAN:
        return f"span {end - start} lines"
    return None


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def blame(card: str, token: str) -> str:
    """Newest commit at which `token` turned from absent to present in the card."""
    for rel in (f".game-of-cards/deck/{card}/README.md", f"deck/{card}/README.md"):
        commits = git("log", "--follow", "--format=%H", "--", rel).split()
        if not commits:
            continue
        pat = re.compile(r"(?<![A-Za-z0-9_./-])" + re.escape(token) + r"(?![0-9])")
        culprit, prev = None, False
        for commit in reversed(commits):
            text = git("show", f"{commit}:{rel}")
            present = bool(pat.search(text))
            if present and not prev:
                culprit = commit
            prev = present
        if culprit:
            subject = git("log", "-1", "--format=%h %ad %s", "--date=short", culprit)
            return subject.strip()
    return "(unknown)"


def main() -> int:
    findings = []
    for readme in sorted(DECK.glob("*/README.md")):
        card = readme.parent.name
        for lineno, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
            for m in RANGE.finditer(line):
                start, end = int(m.group(3)), int(m.group(4))
                why = incoherent(start, end)
                if why:
                    findings.append((card, m.group(0), lineno, why))

    print(f"scanned {len(list(DECK.glob('*/README.md')))} cards")
    print(f"incoherent range cites: {len(findings)}\n")
    for card, token, lineno, why in findings:
        print(f"  {token}  ({why})")
        print(f"    card    : {card}  (README:{lineno})")
        print(f"    written : {blame(card, token)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
