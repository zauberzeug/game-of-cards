"""Regression guard: hot-path skill bodies stay lean.

Skill bodies load into the conversation on every invocation and persist
for the rest of the session, so their size is a per-invocation tax on
every consuming repo (measured downstream: 31% of a project's session
usage went to this plugin, finish-card alone 15%). The workhorse skills
are restructured for progressive disclosure — the happy path lives in
SKILL.md, edge-case material in a sibling ``reference.md`` that the
model reads only when the situation arises. This guard keeps future
edits from re-fattening the hot path: new edge-case prose belongs in
the sibling, not the core.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SKILLS = ROOT / "goc" / "templates" / "skills"

# Bytes of SKILL.md (frontmatter + body). The capped set is the hot path
# (the per-card-cycle verbs plus the cross-referenced schema skill) and the
# occasional skills that got the same progressive-disclosure split later.
# kickoff's cap is higher because its body is mostly verbatim dialog text
# delivered to the user, which cannot move to the reference sibling.
BODY_CAPS = {
    "create-card": 10_000,
    "finish-card": 10_000,
    "advance-card": 10_000,
    "decide-card": 10_000,
    "next-card": 10_000,
    "pull-card": 10_000,
    "card-schema": 12_000,
    "deck": 10_000,
    "refine-deck": 10_000,
    "kickoff": 11_000,
    "audit-deck": 10_000,
}


# Bytes of the marker-bounded briefing block template injected into every
# consumer's AGENTS.md / CLAUDE.md. Consumers' bootstrap files have hard
# char budgets (OpenClaw trims at bootstrapMaxChars, default 20k), so the
# goc-owned block must stay a pointer surface: discovery signal, skill
# list, one-line rules. Methodology prose belongs in the skills.
BRIEFING_CAP = 2_500
BRIEFING_TEMPLATE = ROOT / "goc" / "templates" / "AGENTS_GOC.md"


class SkillBodySizeTest(unittest.TestCase):
    def test_hot_path_skill_bodies_fit_their_caps(self) -> None:
        over_cap: list[str] = []
        for name, cap in sorted(BODY_CAPS.items()):
            path = TEMPLATE_SKILLS / name / "SKILL.md"
            size = path.stat().st_size
            if size > cap:
                rel = path.relative_to(ROOT)
                over_cap.append(f"{rel}: {size} > {cap}")
        self.assertEqual([], over_cap)

    def test_capped_skills_exist(self) -> None:
        for name in BODY_CAPS:
            self.assertTrue(
                (TEMPLATE_SKILLS / name / "SKILL.md").is_file(),
                f"capped skill vanished: {name}",
            )


class BriefingBlockSizeTest(unittest.TestCase):
    def test_briefing_template_fits_its_cap(self) -> None:
        size = BRIEFING_TEMPLATE.stat().st_size
        self.assertLessEqual(
            size,
            BRIEFING_CAP,
            f"{BRIEFING_TEMPLATE.relative_to(ROOT)}: {size} > {BRIEFING_CAP}; "
            "the marker block is always-loaded in every consumer — move new "
            "prose into a skill and leave a one-line pointer.",
        )


if __name__ == "__main__":
    unittest.main()
