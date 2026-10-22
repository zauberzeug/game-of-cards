#!/usr/bin/env python3
"""Prove the deck README's Workflow-hook stubs table cites a section no skill has.

The table's third column ("Workflow point") tells a consumer WHERE in the named
skill their `.game-of-cards/hooks/<stem>.md` content is injected. Where that cell
names a numbered section (`Phase N` / `Step N`), the section must exist as a
heading in that skill's `SKILL.md` — otherwise an author scans the skill for the
promised anchor and finds nothing.

Exits 0 when every catalogued anchor resolves, 1 while any is a phantom.
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

# `| `hooks/<stem>.md` | `<skill>` | <workflow point> |`
_ROW = re.compile(
    r"^\|\s*`hooks/([a-z0-9-]+)\.md`\s*\|\s*`([a-z0-9-]+)`\s*\|\s*(.+?)\s*\|\s*$",
    re.MULTILINE,
)
# A numbered section anchor the cell promises the reader will find in the skill.
_ANCHOR = re.compile(r"\b(Phase|Step)\s+(\d+)\b")


def _hook_table(readme: Path) -> str:
    text = readme.read_text()
    start = text.index("## Workflow-hook stubs")
    rest = text[start:]
    end = rest.find("\n## ", 1)
    return rest if end == -1 else rest[:end]


def _headings(skill: str) -> list[str]:
    body = (SKILLS / skill / "SKILL.md").read_text()
    return re.findall(r"^#{1,6}\s+(.*)$", body, re.MULTILINE)


def check(readme: Path) -> list[str]:
    failures: list[str] = []
    for stem, skill, point in _ROW.findall(_hook_table(readme)):
        headings = _headings(skill)
        for kind, num in _ANCHOR.findall(point):
            anchor = f"{kind} {num}"
            if not any(re.match(rf"{anchor}\b", h) for h in headings):
                failures.append(
                    f"{readme.relative_to(ROOT)}: row `hooks/{stem}.md` promises "
                    f"{anchor!r} in the `{skill}` skill, but "
                    f"goc/templates/skills/{skill}/SKILL.md has no such heading. "
                    f"Its headings are: {', '.join(headings)}"
                )
    return failures


def main() -> int:
    readmes = [
        ROOT / "goc" / "templates" / "game_of_cards" / "README.md",
        ROOT / ".game-of-cards" / "README.md",
    ]
    failures: list[str] = []
    for readme in readmes:
        failures.extend(check(readme))

    for f in failures:
        print(f"[FAIL] {f}")
    if failures:
        print(f"\n{len(failures)} phantom anchor(s) in the Workflow-hook stubs catalogue.")
        return 1
    print(f"[OK] every numbered anchor in the Workflow-hook stubs catalogue resolves "
          f"({len(readmes)} README copies checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
