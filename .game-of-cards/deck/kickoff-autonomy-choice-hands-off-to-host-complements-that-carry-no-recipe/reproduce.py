#!/usr/bin/env python3
"""Reproduce kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe.

Kickoff Stage 6 records an `autonomy:` mode and hands the user to the host's
kickoff complement for the setup recipe. This scans every shipped host
complement (`goc/templates/skills/*-kickoff/`) for an autonomy section with
one `- **`<mode>`**` entry per mode Stage 6 records, `manual` excepted (it
needs no setup).

Exit 0: every complement covers every mode (hypothesis disproved / fixed).
Exit 1: some complement lacks an entry (hypothesis confirmed).
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
SKILLS = ROOT / "goc" / "templates" / "skills"


def offered_modes() -> list[str]:
    text = (SKILLS / "kickoff" / "SKILL.md").read_text(encoding="utf-8")
    stage6 = text.split("## Stage 6", 1)[1]
    match = re.search(r"`autonomy:` key with one of these values:(.+?)\.\s", stage6, re.S)
    if match is None:
        sys.exit("kickoff Stage 6 no longer lists the recorded autonomy values")
    return [m for m in re.findall(r"`([a-z]+)`", match.group(1)) if m != "manual"]


def recipe_modes(skill_md: Path) -> set[str]:
    text = skill_md.read_text(encoding="utf-8")
    section = re.search(r"^## [^\n]*[Aa]utonomy[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if section is None:
        return set()
    return set(re.findall(r"^- \*\*`([a-z]+)`\*\*", section.group(1), re.M))


def main() -> int:
    modes = offered_modes()
    complements = sorted(SKILLS.glob("*-kickoff/SKILL.md"))
    print(f"kickoff Stage 6 modes needing setup: {modes}")
    missing = 0
    for path in complements:
        have = recipe_modes(path)
        lacking = [m for m in modes if m not in have]
        missing += len(lacking)
        verdict = "OK" if not lacking else f"MISSING {lacking}"
        print(f"  {path.parent.name}: {verdict}")
    if not complements:
        print("no host complements found")
        return 1
    if missing:
        print(f"CONFIRMED: {missing} mode recipe(s) missing across host complements")
        return 1
    print("every host complement covers every offered autonomy mode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
