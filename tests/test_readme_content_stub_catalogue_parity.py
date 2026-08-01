"""Regression guard: a content stub claims an injection point only if one exists.

Two surfaces tell a consumer where a `.game-of-cards/` content stub is
delivered to an agent, and both used to be able to rot silently:

1. **The stub's own header.** `goc install` scaffolds each stub with a comment
   block; for an injected stub it reads "injected into goc-shipped skill bodies
   via ``!`cat .game-of-cards/<name>.md``` at documented insertion points".
   A consumer opening the file to author content reads that sentence first.
2. **The deck README's "Content stubs" catalogue.** Its "Inlined into" column
   either names the skill that injects the stub, or says the stub is reserved.

The ground truth for both is the shipped skill tree: a stub is delivered iff
some `goc/templates/skills/**/*.md` body carries the ``!`cat`` line. This test
derives that set and holds both surfaces to it, in both the template and the
dogfood copy.

Sibling to `tests/test_readme_hook_catalogue_parity.py`, which pins the
*workflow-hook* table against the shipped `hooks/*.md` set. That guard proves a
shipped hook has a catalogue row; this one proves a catalogued injection point
actually exists — the direction that let five of six content stubs ship a header
promising an inlining no skill performed (see deck card
`five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs`).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB_DIR = ROOT / "goc" / "templates" / "game_of_cards"
SKILLS_DIR = ROOT / "goc" / "templates" / "skills"

# The sentence an injected stub's header carries.
_CLAIMS_INJECTION = "injected into goc-shipped skill bodies via"

# A `!`cat .game-of-cards/<path>` ...` injection inside a skill body.
_INJECTION = re.compile(r"!`cat \.game-of-cards/([A-Za-z0-9./_-]+\.md)")

# A "Content stubs" catalogue row: | `<file>` | <inlined into> | <what goes here> |
_ROW = re.compile(r"^\|\s*`([a-z0-9-]+\.(?:md|yaml))`\s*\|\s*([^|]*?)\s*\|")


def _stub_names() -> set[str]:
    """Shipped content-stub filenames (the catalogue's root-level `*.md` set)."""
    return {p.name for p in STUB_DIR.glob("*.md") if p.name != "README.md"}


def _injected_names() -> set[str]:
    """Every `.game-of-cards/…` path any shipped skill body `!cat`-injects."""
    found: set[str] = set()
    for path in sorted(SKILLS_DIR.rglob("*.md")):
        found.update(_INJECTION.findall(path.read_text(encoding="utf-8")))
    return found


def _catalogue_rows(readme: Path) -> dict[str, str]:
    """`{stub filename: "Inlined into" cell}` from the README's Content stubs table."""
    text = readme.read_text(encoding="utf-8")
    start = text.index("## Content stubs")
    section = text[start:]
    end = section.find("\n## ")
    if end != -1:
        section = section[:end]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        m = _ROW.match(line)
        # `config.yaml` shares the table but is engine-read, not `!cat`-injected.
        if m and m.group(1) != "config.yaml":
            rows[m.group(1)] = m.group(2)
    return rows


class ContentStubHeaderParityTest(unittest.TestCase):
    def test_header_claims_injection_only_when_one_exists(self) -> None:
        injected = _injected_names()
        liars, silent = [], []
        for name in sorted(_stub_names()):
            claims = _CLAIMS_INJECTION in (STUB_DIR / name).read_text(encoding="utf-8")
            if claims and name not in injected:
                liars.append(name)
            elif not claims and name in injected:
                silent.append(name)
        self.assertEqual(
            ([], []),
            (liars, silent),
            msg=(
                "Content-stub headers disagree with the shipped skill tree.\n"
                f"  header promises an injection that does not exist: {liars}\n"
                f"    -> either add `!`cat .game-of-cards/<stub>` to the skill "
                "that should read it, or reword the header as reserved\n"
                f"  injected but the header does not say so: {silent}\n"
                f"  stubs a skill actually injects: "
                f"{sorted(injected & _stub_names())}"
            ),
        )


class ContentStubCatalogueParityTest(unittest.TestCase):
    def _assert_catalogue(self, readme: Path, label: str) -> None:
        injected = _injected_names()
        stubs = _stub_names()
        rows = _catalogue_rows(readme)

        self.assertEqual(
            stubs,
            set(rows),
            msg=(
                f"The 'Content stubs' table in {label} is out of sync with the "
                "shipped stub set.\n"
                f"  shipped but not catalogued: {sorted(stubs - set(rows))}\n"
                f"  catalogued but not shipped: {sorted(set(rows) - stubs)}"
            ),
        )

        overclaimed = sorted(
            name
            for name, cell in rows.items()
            if name not in injected and "reserved" not in cell.lower()
        )
        underclaimed = sorted(
            name
            for name, cell in rows.items()
            if name in injected and "reserved" in cell.lower()
        )
        self.assertEqual(
            ([], []),
            (overclaimed, underclaimed),
            msg=(
                f"The 'Content stubs' table in {label} disagrees with the "
                "shipped skill tree.\n"
                f"  row names a delivery point but no skill injects the stub: "
                f"{overclaimed}\n"
                f"  row says 'reserved' but a skill does inject the stub: "
                f"{underclaimed}\n"
                f"  stubs a skill actually injects: {sorted(injected & stubs)}"
            ),
        )

    def test_template_readme_catalogue_matches_the_skill_tree(self) -> None:
        self._assert_catalogue(
            STUB_DIR / "README.md", "goc/templates/game_of_cards/README.md"
        )

    def test_dogfood_readme_catalogue_matches_the_skill_tree(self) -> None:
        dogfood = ROOT / ".game-of-cards" / "README.md"
        if not dogfood.exists():
            self.skipTest("no dogfood .game-of-cards/README.md in this checkout")
        self._assert_catalogue(dogfood, ".game-of-cards/README.md")


class DogfoodStubHeaderParityTest(unittest.TestCase):
    """The dogfood `.game-of-cards/` stubs are user-owned and not auto-synced.

    An *authored* stub is expected to diverge — the README's authoring
    guidelines say to replace the header with real instructions. Only a stub
    still carrying the scaffold header is held to the template's wording, so
    this repo's own copies cannot keep a stale injection promise.
    """

    def test_unauthored_dogfood_stubs_match_the_template_header(self) -> None:
        stale = []
        for name in sorted(_stub_names()):
            local = ROOT / ".game-of-cards" / name
            if not local.exists():
                continue
            text = local.read_text(encoding="utf-8")
            if _CLAIMS_INJECTION not in text:
                continue
            if name not in _injected_names():
                stale.append(name)
        self.assertEqual(
            [],
            stale,
            msg=(
                "Dogfood .game-of-cards/ stubs still promise an injection no "
                f"shipped skill performs: {stale}\n"
                "  These copies are user-owned (goc upgrade preserves them), so "
                "refresh them by hand from goc/templates/game_of_cards/."
            ),
        )


if __name__ == "__main__":
    unittest.main()
