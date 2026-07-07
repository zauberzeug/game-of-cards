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

# Bytes of SKILL.md (frontmatter + body). The capped set is the hot path:
# the per-card-cycle verbs plus the cross-referenced schema skill.
BODY_CAPS = {
    "create-card": 10_000,
    "finish-card": 10_000,
    "advance-card": 10_000,
    "decide-card": 10_000,
    "next-card": 10_000,
    "pull-card": 10_000,
    "card-schema": 12_000,
}


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


if __name__ == "__main__":
    unittest.main()
