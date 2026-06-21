"""Regression guard: generated agent guidance must not claim `goc done` auto-commits.

The shipped `done` command is a non-committing state flip (status + closed_at).
Any guidance surface that says "close + commit" in a single step contradicts the
implementation and misleads autonomous agents into believing a commit has landed.
"""

from __future__ import annotations

import argparse
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Phrase that must NOT appear as a single-step "goc done" description.
_STALE_PATTERN = re.compile(r"close \+ commit", re.IGNORECASE)

# Files that ship guidance read by agents (templates + generated consumer copies).
_GUIDANCE_FILES = [
    ROOT / "goc" / "templates" / "AGENTS_GOC.md",
    ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py",
    ROOT / "goc" / "templates" / "skills" / "pull-card" / "SKILL.md",
    ROOT / "AGENTS.md",
    ROOT / ".claude" / "hooks" / "deck_prompt_router.py",
    ROOT / ".claude" / "skills" / "pull-card" / "SKILL.md",
]


class GuidanceAccuracyTest(unittest.TestCase):
    def test_no_guidance_surface_claims_done_autocommits(self) -> None:
        for path in _GUIDANCE_FILES:
            if not path.exists():
                continue
            text = path.read_text()
            matches = _STALE_PATTERN.findall(text)
            self.assertFalse(
                matches,
                msg=(
                    f"{path.relative_to(ROOT)}: found stale 'close + commit' phrase "
                    f"({len(matches)} occurrence(s)). `goc done` does not auto-commit; "
                    "update the wording to separate closure from the commit step."
                ),
            )


def _agents_architecture_section() -> str:
    """Return the `## Code architecture` section body of AGENTS.md."""
    text = (ROOT / "AGENTS.md").read_text()
    start = text.index("## Code architecture")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def _engine_subcommands() -> set[str]:
    """Every subcommand the engine's argparse parser registers."""
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("no subparsers found on engine parser")


class AgentsArchitectureAccuracyTest(unittest.TestCase):
    def test_cli_bullet_does_not_mention_click(self) -> None:
        section = _agents_architecture_section()
        cli_bullet = section[section.index("**`goc/cli.py`**"):section.index("**`goc/engine.py`**")]
        self.assertNotRegex(
            cli_bullet,
            re.compile(r"click", re.IGNORECASE),
            msg="AGENTS.md goc/cli.py bullet still mentions Click; the package uses argparse.",
        )

    def test_cli_source_has_no_click(self) -> None:
        self.assertNotRegex(
            (ROOT / "goc" / "cli.py").read_text(),
            re.compile(r"click", re.IGNORECASE),
            msg="goc/cli.py references Click; it should be pure argparse.",
        )

    def test_all_engine_verbs_listed_in_architecture_section(self) -> None:
        section = _agents_architecture_section()
        # install/upgrade live in install.py, not the engine; they are documented
        # in their own bullet.
        verbs = _engine_subcommands() - {"install", "upgrade"}
        missing = sorted(v for v in verbs if f"`{v}`" not in section)
        self.assertFalse(
            missing,
            msg=(
                "AGENTS.md `## Code architecture` section omits engine verb(s) "
                f"{missing}; the goc/engine.py bullet claims an exhaustive list."
            ),
        )


def _board_legend_row(path: Path) -> str:
    """Return the `goc --board` legend row from a deck SKILL.md table."""
    for line in path.read_text().splitlines():
        if "`goc --board`" in line and line.lstrip().startswith("|"):
            return line
    raise AssertionError(f"{path}: no `goc --board` legend row found")


# The deck skill's board legend is the one place agents learn what the `⏳`
# glyph means. The engine paints `⏳` on three axes (`render_board`), but only
# two of them hide a card from the pull queue (`card_is_ready` ignores
# `dependency_blocked`). A legend that claims `⏳` ⇒ unpullable, or that omits
# the `human_gate` axis, misleads autonomous pullers.
_DECK_SKILL_FILES = [
    ROOT / "goc" / "templates" / "skills" / "deck" / "SKILL.md",
    ROOT / ".claude" / "skills" / "deck" / "SKILL.md",
]
# The false biconditional the old legend shipped.
_STALE_BICONDITIONAL = re.compile(r"No\s+`?⏳`?\s*⇒\s*pullable", re.IGNORECASE)


class DeckBoardLegendAccuracyTest(unittest.TestCase):
    def test_board_legend_names_human_gate_axis(self) -> None:
        for path in _DECK_SKILL_FILES:
            if not path.exists():
                continue
            row = _board_legend_row(path)
            self.assertIn(
                "human_gate",
                row,
                msg=(
                    f"{path.relative_to(ROOT)}: board legend omits the "
                    "`human_gate` axis, but `render_board` paints `⏳` on it."
                ),
            )

    def test_board_legend_does_not_claim_dependency_block_unpullable(self) -> None:
        for path in _DECK_SKILL_FILES:
            if not path.exists():
                continue
            row = _board_legend_row(path)
            self.assertNotRegex(
                row,
                _STALE_BICONDITIONAL,
                msg=(
                    f"{path.relative_to(ROOT)}: board legend asserts the false "
                    "biconditional 'No ⏳ ⇒ pullable'. A dependency-blocked card "
                    "carries `⏳` yet `card_is_ready` reports it pullable."
                ),
            )
            self.assertIn(
                "still pullable",
                row,
                msg=(
                    f"{path.relative_to(ROOT)}: board legend should state that a "
                    "dependency-block leaves the card still pullable (advisory only)."
                ),
            )


if __name__ == "__main__":
    unittest.main()
