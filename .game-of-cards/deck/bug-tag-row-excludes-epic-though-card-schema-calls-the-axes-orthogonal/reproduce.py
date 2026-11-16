#!/usr/bin/env python3
"""Show the `bug` row contradicting the schema reference, and what it does to the deck.

Reads three shipped statements and one deck census:

  1. the `bug` row of the card-schema tag table (`goc/templates/skills/
     card-schema/SKILL.md`), which excludes `epic`;
  2. the schema reference's `epic` paragraph, which calls `epic` orthogonal
     to the bug-or-story question;
  3. `tests/test_canonical_tag_rows.py`, which lists "bug carrying epic" as
     an offender the `bug` scorer must reject;
  4. every `meta-fix` card whose closure two or more `advanced_by` instances
     block — the cards the `epic` row describes — grouped by which of
     `bug` / `epic` they carry.

Exits 1 while the row still excludes `epic` and the reference still calls the
axes orthogonal (the two statements cannot both hold), 0 once they agree.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


ROOT = _repo_root()
SKILL = ROOT / "goc" / "templates" / "skills" / "card-schema" / "SKILL.md"
REFERENCE = ROOT / "goc" / "templates" / "skills" / "card-schema" / "reference.md"
TEST = ROOT / "tests" / "test_canonical_tag_rows.py"


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def main() -> int:
    row = next((ln for ln in SKILL.read_text(encoding="utf-8").splitlines()
                if ln.startswith("| `bug` |")), "")
    row_excludes_epic = "not `epic`" in row
    ref = flat(REFERENCE)
    ref_orthogonal = bool(re.search(r"whether the card coordinates others\.\*\* Orthogonal", ref))
    test_offender = '("bug carrying epic", "bug"' in TEST.read_text(encoding="utf-8")

    print(f"card-schema SKILL.md bug row      : {row.strip()}")
    print(f"  excludes epic                   : {row_excludes_epic}")
    print(f"reference calls epic orthogonal   : {ref_orthogonal}")
    print(f"test pins 'bug carrying epic' bad : {test_offender}")

    cards = json.loads(subprocess.run(
        ["uv", "run", "--project", str(ROOT), "goc", "--status", "all", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        tags = set(c.get("tags") or [])
        if "meta-fix" in tags and len(c.get("advanced_by") or []) >= 2:
            key = "bug" if "bug" in tags else ("epic" if "epic" in tags else "neither")
            groups[key].append(f"{c['title']} ({c['status']}, {len(c['advanced_by'])} instances)")
    total = sum(len(v) for v in groups.values())
    print(f"\nmeta-fix cards with >=2 advanced_by (the epic row fires on each): {total}")
    for key in ("bug", "epic", "neither"):
        print(f"  tagged {key:<8}: {len(groups[key])}")
        for title in sorted(groups[key]):
            print(f"      {title}")

    if row_excludes_epic and ref_orthogonal:
        print("\nCONTRADICTION: the bug row forbids epic while the reference makes the two")
        print("axes independent, so a bug-family umbrella has no consistent tagging.")
        return 1
    print("\nPASS: the bug row and the reference agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
