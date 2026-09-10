"""Regression guard: the deck README "Workflow-hook stubs" table must list
every shipped hook stub.

The README's hook-point catalogue is the documented index of extension points
a consumer scans to discover where project-local workflow hooks plug in. When
a new `hooks/<skill>.md` stub ships (and is `!cat`-injected by its skill) but
the catalogue is not updated, the index silently rots: an author looking to
customize that hook scans the table, does not see it, and concludes the
hook-point does not exist.

This test pins the table to the shipped `goc/templates/game_of_cards/hooks/*.md`
set so the next added hook can't drift the catalogue. It also checks the
dogfood copy at `.game-of-cards/README.md`, which is not auto-synced from the
template and so must be kept in step by hand.

The row's other two columns are checked as well, because an author acts on them
just as directly as on the stub name:

* **`Loaded by`** must name a skill whose `SKILL.md` really `!cat`s the stub. A
  row pointing at a skill that never reads the file sends the author to write
  content nothing loads.
* **`Workflow point`** is free prose, but where it cites a numbered section
  (`Phase N` / `Step N`) that section must exist as a heading in that skill.
  The catalogue shipped a `Phase 0` anchor for `audit-deck` that no skill ever
  had, so an author looking for it found phases starting at 1.

Both checks derive from the skill tree rather than restating the catalogue, so a
newly added row is covered without editing this file.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `hooks/<stem>.md` reference inside a markdown table cell.
_HOOK_REF = re.compile(r"`hooks/([a-z0-9][a-z0-9-]*)\.md`")

# A full catalogue row: `| \`hooks/<stem>.md\` | \`<skill>\` | <workflow point> |`.
_CATALOGUE_ROW = re.compile(
    r"^\|\s*`hooks/([a-z0-9][a-z0-9-]*)\.md`\s*\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|\s*(.+?)\s*\|\s*$",
    re.MULTILINE,
)

# A numbered section anchor a "Workflow point" cell promises the reader.
_SECTION_ANCHOR = re.compile(r"\b(Phase|Step)\s+(\d+)\b")

# Markdown heading text, any level.
_HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def _shipped_hook_stems() -> set[str]:
    hooks_dir = ROOT / "goc" / "templates" / "game_of_cards" / "hooks"
    return {p.stem for p in hooks_dir.glob("*.md")}


def _hook_table(readme: Path) -> str:
    """The README's 'Workflow-hook stubs' section, up to the next `## ` heading."""
    text = readme.read_text()
    start = text.index("## Workflow-hook stubs")
    rest = text[start + len("## Workflow-hook stubs"):]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def _catalogued_hook_stems(readme: Path) -> set[str]:
    """Hook stems listed in the README's 'Workflow-hook stubs' table."""
    return set(_HOOK_REF.findall(_hook_table(readme)))


def _catalogue_rows(readme: Path) -> list[tuple[str, str, str]]:
    """`(hook stem, "Loaded by" skill, "Workflow point" cell)` per table row."""
    return _CATALOGUE_ROW.findall(_hook_table(readme))


def _skill_body(skill: str) -> str:
    return (ROOT / "goc" / "templates" / "skills" / skill / "SKILL.md").read_text()


def _skill_headings(skill: str) -> list[str]:
    return _HEADING.findall(_skill_body(skill))


class ReadmeHookCatalogueParityTest(unittest.TestCase):
    def test_template_readme_catalogues_every_shipped_hook(self) -> None:
        shipped = _shipped_hook_stems()
        catalogued = _catalogued_hook_stems(
            ROOT / "goc" / "templates" / "game_of_cards" / "README.md"
        )
        self.assertEqual(
            shipped,
            catalogued,
            msg=(
                "The 'Workflow-hook stubs' table in "
                "goc/templates/game_of_cards/README.md is out of sync with the "
                "shipped hooks/*.md set.\n"
                f"  shipped but not catalogued: {sorted(shipped - catalogued)}\n"
                f"  catalogued but not shipped: {sorted(catalogued - shipped)}"
            ),
        )

    def test_dogfood_readme_catalogues_every_shipped_hook(self) -> None:
        dogfood = ROOT / ".game-of-cards" / "README.md"
        if not dogfood.exists():
            self.skipTest("no dogfood .game-of-cards/README.md in this checkout")
        shipped = _shipped_hook_stems()
        catalogued = _catalogued_hook_stems(dogfood)
        self.assertEqual(
            shipped,
            catalogued,
            msg=(
                "The 'Workflow-hook stubs' table in .game-of-cards/README.md is "
                "out of sync with the shipped hooks/*.md set (this copy is not "
                "auto-synced from the template; update it by hand).\n"
                f"  shipped but not catalogued: {sorted(shipped - catalogued)}\n"
                f"  catalogued but not shipped: {sorted(catalogued - shipped)}"
            ),
        )




class HookCatalogueRowAccuracyTest(unittest.TestCase):
    """The `Loaded by` and `Workflow point` cells must describe the real skill."""

    readmes = (
        ("goc/templates/game_of_cards/README.md", ROOT / "goc" / "templates" / "game_of_cards" / "README.md"),
        (".game-of-cards/README.md", ROOT / ".game-of-cards" / "README.md"),
    )

    def test_every_shipped_hook_has_a_parseable_row(self) -> None:
        """Guard the guard: the row regex must see every catalogued stub."""
        for label, readme in self.readmes:
            if not readme.exists():
                continue
            with self.subTest(readme=label):
                self.assertEqual(
                    _catalogued_hook_stems(readme),
                    {stem for stem, _, _ in _catalogue_rows(readme)},
                    msg=(
                        f"A row in {label}'s 'Workflow-hook stubs' table does not "
                        "match the expected three-column shape, so the accuracy "
                        "checks below would silently skip it."
                    ),
                )

    def test_loaded_by_skill_actually_injects_the_stub(self) -> None:
        for label, readme in self.readmes:
            if not readme.exists():
                continue
            for stem, skill, _ in _catalogue_rows(readme):
                with self.subTest(readme=label, hook=stem):
                    injection = f"!`cat .game-of-cards/hooks/{stem}.md"
                    # assertTrue, not assertIn: the haystack is a whole SKILL.md
                    # and dumping it buries the one line that matters.
                    self.assertTrue(
                        injection in _skill_body(skill),
                        msg=(
                            f"{label} says `hooks/{stem}.md` is loaded by the "
                            f"`{skill}` skill, but "
                            f"goc/templates/skills/{skill}/SKILL.md contains no "
                            f"{injection!r} injection. Content authored into that "
                            "stub would never reach an agent."
                        ),
                    )

    def test_workflow_point_anchors_exist_in_the_skill(self) -> None:
        for label, readme in self.readmes:
            if not readme.exists():
                continue
            for stem, skill, point in _catalogue_rows(readme):
                headings = _skill_headings(skill)
                for kind, num in _SECTION_ANCHOR.findall(point):
                    anchor = f"{kind} {num}"
                    with self.subTest(readme=label, hook=stem, anchor=anchor):
                        self.assertTrue(
                            any(re.match(rf"{anchor}\b", h) for h in headings),
                            msg=(
                                f"{label} row `hooks/{stem}.md` promises {anchor!r} "
                                f"in the `{skill}` skill, but "
                                f"goc/templates/skills/{skill}/SKILL.md has no such "
                                f"heading. Its headings are: {', '.join(headings)}"
                            ),
                        )


if __name__ == "__main__":
    unittest.main()
