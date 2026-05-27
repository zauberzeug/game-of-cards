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


if __name__ == "__main__":
    unittest.main()
