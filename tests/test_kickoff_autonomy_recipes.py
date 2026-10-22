"""Regression guard: kickoff's autonomy hand-off must land on a recipe.

Kickoff Stage 6 records an `autonomy:` mode in `.game-of-cards/config.yaml`
and sends the user to the host's kickoff complement to wire it. No goc command
reads the key, so a complement without an entry for the chosen mode leaves the
choice recorded and nothing set up — the state the card
`kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe`
found in all three complements. Every complement carries one
`- **`<mode>`**` entry per mode under its autonomy section; an entry may say
the host has no recipe, but it may not be missing.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "goc" / "templates" / "skills"


def _stage6() -> str:
    text = (SKILLS / "kickoff" / "SKILL.md").read_text(encoding="utf-8")
    return text.split("## Stage 6", 1)[1]


def _offered_modes() -> list[str]:
    match = re.search(
        r"`autonomy:` key with one of these values:(.+?)\.\s", _stage6(), re.S
    )
    assert match is not None, "kickoff Stage 6 no longer lists the autonomy values"
    # `manual` needs no setup, so no complement owes it a recipe.
    return [m for m in re.findall(r"`([a-z]+)`", match.group(1)) if m != "manual"]


def _recipe_modes(skill_md: Path) -> set[str]:
    text = skill_md.read_text(encoding="utf-8")
    section = re.search(
        r"^## [^\n]*[Aa]utonomy[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M
    )
    if section is None:
        return set()
    return set(re.findall(r"^- \*\*`([a-z]+)`\*\*", section.group(1), re.M))


COMPLEMENTS = sorted(SKILLS.glob("*-kickoff/SKILL.md"))


class KickoffAutonomyRecipesTest(unittest.TestCase):
    def test_complements_exist(self) -> None:
        self.assertTrue(COMPLEMENTS, "no host kickoff complements found")

    def test_every_complement_covers_every_offered_mode(self) -> None:
        modes = _offered_modes()
        self.assertTrue(modes)
        for path in COMPLEMENTS:
            with self.subTest(complement=path.parent.name):
                missing = [m for m in modes if m not in _recipe_modes(path)]
                self.assertEqual([], missing)

    def test_stage6_hand_off_names_every_complement(self) -> None:
        stage6 = _stage6()
        for path in COMPLEMENTS:
            with self.subTest(complement=path.parent.name):
                self.assertIn(f"`{path.parent.name}`", stage6)


if __name__ == "__main__":
    unittest.main()
