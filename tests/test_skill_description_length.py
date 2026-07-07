"""Regression guard: skill catalog descriptions stay lean.

Skill hosts (Claude Code, Codex, OpenClaw) inject every installed skill's
``name`` + ``description`` into the system prompt of every session, so
consumers pay for the full catalog on every API call and every
prompt-cache re-write. The description's only functional job there is
routing the "when to load this skill" decision — one sentence of purpose
plus the strongest 2-4 AUTO-INVOKE cues. Exhaustive trigger enumerations
belong in the SKILL.md body, which hosts load on demand.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from goc.install import _frontmatter_value


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SKILLS = ROOT / "goc" / "templates" / "skills"

DESCRIPTION_CAP = 300


class SkillDescriptionLengthTest(unittest.TestCase):
    def test_template_skill_descriptions_fit_the_catalog_cap(self) -> None:
        over_cap: list[str] = []
        for path in sorted(TEMPLATE_SKILLS.glob("*/SKILL.md")):
            try:
                _before, frontmatter, _body = path.read_text(
                    encoding="utf-8"
                ).split("---", 2)
            except ValueError:
                continue
            description = _frontmatter_value(frontmatter, "description")
            if len(description) > DESCRIPTION_CAP:
                rel = path.relative_to(ROOT)
                over_cap.append(f"{rel}: {len(description)} > {DESCRIPTION_CAP}")
        self.assertEqual([], over_cap)

    def test_template_skills_were_found(self) -> None:
        self.assertGreater(len(list(TEMPLATE_SKILLS.glob("*/SKILL.md"))), 0)


if __name__ == "__main__":
    unittest.main()
