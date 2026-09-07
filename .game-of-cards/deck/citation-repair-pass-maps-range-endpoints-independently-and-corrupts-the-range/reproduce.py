#!/usr/bin/env python3
"""Range cites the citation-repair recipe left incoherent.

A range cite (`file.py:120-140`) names a block of code.  The recipe in
`goc/templates/skills/refine-deck/reference.md` § "Citation anchor check"
maps its two endpoints as independent single-line lookups, so nothing
requires the repaired pair to still bound a block.  This script finds every
range cite in the deck that no longer does, and blames the commit that
broke it.

This card's OWN README is skipped.  It is the catalogue of the corruption —
a compounding trace of what each past pass wrote, plus a transcript of this
script's pre-fix run — so every range cite it carries is a dated record of a
number some commit once emitted, which the recipe's scope rule
(`reference.md` § Citation anchor check) already puts out of repair scope.
Scanning it would make the guard fail on its own evidence, and rewriting
that evidence would cost the card the thing it was filed to carry.  Every
other card in the deck is scanned.

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
    own_card = Path(__file__).resolve().parent
    for readme in sorted(DECK.glob("*/README.md")):
        if readme.parent.resolve() == own_card:
            continue  # this card's evidence — see the module docstring
        card = readme.parent.name
        for lineno, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
            for m in RANGE.finditer(line):
                start, end = int(m.group(3)), int(m.group(4))
                why = incoherent(start, end)
                if why:
                    findings.append((card, m.group(0), lineno, why))

    scanned = sum(
        1 for r in DECK.glob("*/README.md") if r.parent.resolve() != own_card
    )
    print(f"scanned {scanned} cards")
    print(f"incoherent range cites: {len(findings)}\n")
    for card, token, lineno, why in findings:
        print(f"  {token}  ({why})")
        print(f"    card    : {card}  (README:{lineno})")
        print(f"    written : {blame(card, token)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
