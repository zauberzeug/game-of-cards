"""Regression guard: shipped SKILL.md frontmatter must be strict-YAML safe."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from goc.install import _frontmatter_value


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOTS = (
    ROOT / "goc" / "templates" / "skills",
    ROOT / "claude-plugin" / "skills",
    ROOT / "codex-plugin" / "skills",
    ROOT / ".claude" / "skills",
    ROOT / ".codex" / "skills",
    ROOT / "openclaw-plugin" / "skills",
)
NESTED_MAPPING_COLON = re.compile(r":(?:[ \t]|$)")


def _frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    try:
        _before, fm, _body = text.split("---", 2)
    except ValueError:
        return None
    return fm


def _is_quoted_or_structured(value: str) -> bool:
    return value.startswith(('"', "'", "|", ">", "[", "{")) or value in {"", "null"}


def _quoted_scalar_hazard(value: str) -> str | None:
    """Flag an opening-quoted value that is not one complete quoted scalar."""
    if not value or value[0] not in {'"', "'"}:
        return None
    quote = value[0]
    i = 1
    while i < len(value):
        ch = value[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            if quote == "'" and value[i + 1 : i + 2] == "'":
                i += 2
                continue
            if value[i + 1 :].strip():
                return "content after closing quote"
            return None
        i += 1
    return "quoted scalar never closes"


def _strict_yaml_hazards() -> list[str]:
    out: list[str] = []
    for root in SKILL_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            fm = _frontmatter(path.read_text(encoding="utf-8"))
            if fm is None:
                continue
            for lineno, line in enumerate(fm.splitlines(), start=1):
                if not line or line.startswith((" ", "\t", "#")):
                    continue
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                value = value.strip()
                if _is_quoted_or_structured(value):
                    hazard = _quoted_scalar_hazard(value)
                    if hazard:
                        rel = path.relative_to(ROOT)
                        out.append(f"{rel}:{lineno}: {key} has {hazard}")
                    continue
                if NESTED_MAPPING_COLON.search(value):
                    rel = path.relative_to(ROOT)
                    out.append(f"{rel}:{lineno}: {key} contains unquoted ': '")
    return out


class SkillFrontmatterStrictYamlTest(unittest.TestCase):
    def test_shipped_skill_frontmatter_avoids_unquoted_mapping_colons(self) -> None:
        hazards = _strict_yaml_hazards()
        self.assertEqual([], hazards)

    def test_quoted_scalar_hazard_flags_content_after_closing_quote(self) -> None:
        broken = '"Pull the \\"queue\\" card." If the path is unreadable, use "skill".'
        self.assertEqual("content after closing quote", _quoted_scalar_hazard(broken))
        fixed = '"Pull the \\"queue\\" card. If the path is unreadable, use \\"skill\\"."'
        self.assertIsNone(_quoted_scalar_hazard(fixed))
        self.assertEqual("quoted scalar never closes", _quoted_scalar_hazard('"open'))
        self.assertIsNone(_quoted_scalar_hazard("'it''s quoted'"))

    def test_frontmatter_value_unescapes_double_quoted_scalars(self) -> None:
        frontmatter = 'description: "Say \\"hello\\" before loading `human_gate: none`"'
        self.assertEqual(
            'Say "hello" before loading `human_gate: none`',
            _frontmatter_value(frontmatter, "description"),
        )


if __name__ == "__main__":
    unittest.main()
