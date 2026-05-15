"""Regression guard: skill SKILL.md files must not contain executable fences with placeholders.

The Claude Code host auto-executes inline backtick fences prefixed with `!`. When
such a fence contains a literal angle-bracket placeholder (e.g. `!`goc show <title>``),
the shell parses `<title>` as a redirection and the skill load aborts before reaching
its user-facing flow. Use prose ("run `goc show <title>` yourself") or a non-executed
fence form when documenting commands that need an unbound argument.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Matches an inline executable fence (!`...`) whose contents include a `<word>` placeholder.
_BAD_FENCE = re.compile(r"!`[^`]*<[a-zA-Z][a-zA-Z0-9_-]*>[^`]*`")


class SkillTemplateFenceSafetyTest(unittest.TestCase):
    def test_no_executable_fence_contains_angle_bracket_placeholder(self) -> None:
        skills_dir = ROOT / "goc" / "templates" / "skills"
        offenders: list[str] = []
        for skill_md in skills_dir.rglob("SKILL.md"):
            for lineno, line in enumerate(skill_md.read_text().splitlines(), start=1):
                if _BAD_FENCE.search(line):
                    offenders.append(f"{skill_md.relative_to(ROOT)}:{lineno}: {line.strip()}")
        self.assertFalse(
            offenders,
            msg=(
                "Found executable `!`...`` fence(s) containing an angle-bracket placeholder. "
                "The host evaluates these in zsh at skill load time and the shell parses "
                "`<placeholder>` as a redirect, aborting the skill. Use prose ('run "
                "`goc show <title>` yourself') instead.\n  " + "\n  ".join(offenders)
            ),
        )


if __name__ == "__main__":
    unittest.main()
