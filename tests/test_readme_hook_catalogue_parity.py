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
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `hooks/<stem>.md` reference inside a markdown table cell.
_HOOK_REF = re.compile(r"`hooks/([a-z0-9][a-z0-9-]*)\.md`")


def _shipped_hook_stems() -> set[str]:
    hooks_dir = ROOT / "goc" / "templates" / "game_of_cards" / "hooks"
    return {p.stem for p in hooks_dir.glob("*.md")}


def _catalogued_hook_stems(readme: Path) -> set[str]:
    """Hook stems listed in the README's 'Workflow-hook stubs' table."""
    text = readme.read_text()
    # Slice from the "Workflow-hook stubs" heading to the next "## " heading.
    start = text.index("## Workflow-hook stubs")
    rest = text[start + len("## Workflow-hook stubs"):]
    end = rest.find("\n## ")
    section = rest if end == -1 else rest[:end]
    return set(_HOOK_REF.findall(section))


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


if __name__ == "__main__":
    unittest.main()
