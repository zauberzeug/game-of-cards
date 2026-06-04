#!/usr/bin/env python3
"""Reproduce strict host-loader failures in GoC skill frontmatter."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOTS = (
    ROOT / "goc" / "templates" / "skills",
    ROOT / "claude-plugin" / "skills",
    ROOT / "codex-plugin" / "skills",
    ROOT / ".claude" / "skills",
    ROOT / ".codex" / "skills",
    ROOT / "openclaw-plugin" / "skills",
)

NESTED_MAPPING_COLON = re.compile(r":(?:[ \t]|$)")


def frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    try:
        _before, fm, _body = text.split("---", 2)
    except ValueError:
        return None
    return fm


def is_quoted_or_structured(value: str) -> bool:
    return value.startswith(('"', "'", "|", ">", "[", "{")) or value in {"", "null"}


def hazards() -> list[str]:
    out: list[str] = []
    for root in SKILL_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            fm = frontmatter(path.read_text(encoding="utf-8"))
            if fm is None:
                continue
            for lineno, line in enumerate(fm.splitlines(), start=1):
                if not line or line.startswith((" ", "\t", "#")):
                    continue
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip()
                if is_quoted_or_structured(value):
                    continue
                if NESTED_MAPPING_COLON.search(value):
                    rel = path.relative_to(ROOT)
                    out.append(f"{rel}:{lineno}: {key} contains unquoted ': '")
    return out


def main() -> int:
    found = hazards()
    if found:
        print("FAIL — strict skill-loader frontmatter hazards found:")
        for item in found:
            print(f"  {item}")
        return 1
    print("OK — shipped skill frontmatter avoids unquoted nested mapping-colon scalars.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
