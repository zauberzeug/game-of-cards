#!/usr/bin/env python3
"""Prove that five of the six shipped content stubs have no injection point.

Every stub under `goc/templates/game_of_cards/*.md` (excluding `README.md`)
carries a header asserting it is "injected into goc-shipped skill bodies via
`!`cat .game-of-cards/<name>.md`` at documented insertion points". This script
grep the whole shipped skill tree for that injection and reports, per stub,
whether the promise holds.

It also checks the deck README's own "Content stubs" catalogue: a row whose
"Inlined into" cell names a skill is a second, independent claim that an
injection point exists.

Exit code: 0 when every stub that claims injection actually has one (i.e. the
defect is fixed), 1 while the defect stands.
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
STUB_DIR = ROOT / "goc" / "templates" / "game_of_cards"
SKILLS_DIR = ROOT / "goc" / "templates" / "skills"

# The header sentence every scaffolded stub carries.
_CLAIMS_INJECTION = "injected into goc-shipped skill bodies via"

# A `!`cat .game-of-cards/<name>.md ...`` line in a skill body.
_INJECTION = re.compile(r"!`cat \.game-of-cards/([A-Za-z0-9./_-]+\.md)")

# A "Content stubs" catalogue row: | `<file>` | <inlined into> | <what> |
_ROW = re.compile(r"^\|\s*`([a-z0-9-]+\.(?:md|yaml))`\s*\|\s*([^|]*?)\s*\|")


def injected_paths() -> set[str]:
    """Every `.game-of-cards/...` path any shipped skill `!cat`-injects."""
    found: set[str] = set()
    for path in sorted(SKILLS_DIR.rglob("*.md")):
        found.update(_INJECTION.findall(path.read_text(encoding="utf-8")))
    return found


def catalogue_rows() -> dict[str, str]:
    """`{stub filename: 'Inlined into' cell}` from the README's Content stubs table."""
    text = (STUB_DIR / "README.md").read_text(encoding="utf-8")
    start = text.index("## Content stubs")
    section = text[start:]
    end = section.find("\n## ")
    if end != -1:
        section = section[:end]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        m = _ROW.match(line)
        if m and m.group(1) != "config.yaml":
            rows[m.group(1)] = m.group(2)
    return rows


def main() -> int:
    injected = injected_paths()
    rows = catalogue_rows()
    stubs = sorted(p.name for p in STUB_DIR.glob("*.md") if p.name != "README.md")

    print(f"shipped content stubs:            {len(stubs)}")
    print(f"`!cat` injections in skill tree:  {len(injected)}")
    print()
    header = f"{'stub':<32} {'header claims':<14} {'injected':<9} catalogue 'Inlined into'"
    print(header)
    print("-" * len(header))

    header_liars: list[str] = []
    catalogue_liars: list[str] = []
    for name in stubs:
        claims = _CLAIMS_INJECTION in (STUB_DIR / name).read_text(encoding="utf-8")
        is_injected = name in injected
        cell = rows.get(name, "<no catalogue row>")
        print(f"{name:<32} {str(claims):<14} {str(is_injected):<9} {cell}")
        if claims and not is_injected:
            header_liars.append(name)
        if not is_injected and "reserved" not in cell.lower():
            catalogue_liars.append(name)

    print()
    print(f"[FAIL] stub headers promising an injection that does not exist: "
          f"{len(header_liars)}/{len(stubs)}")
    for name in header_liars:
        print(f"          {name}")
    print(f"[FAIL] catalogue rows naming a skill that does not inject: "
          f"{len(catalogue_liars)}")
    for name in catalogue_liars:
        print(f"          {name} -> {rows.get(name)!r}")

    # The prose pointer audit-deck uses instead of an injection.
    audit = (SKILLS_DIR / "audit-deck" / "SKILL.md").read_text(encoding="utf-8")
    for i, line in enumerate(audit.splitlines(), 1):
        if "tooling-conventions.md" in line:
            print()
            print(f"audit-deck/SKILL.md:{i}: {line.strip()}")
            print("          ^ a prose pointer, not the `!`cat`` injection the "
                  "catalogue documents")

    return 0 if not header_liars and not catalogue_liars else 1


if __name__ == "__main__":
    sys.exit(main())
