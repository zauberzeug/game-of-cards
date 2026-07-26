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


class DocstringCitationAccuracyTest(unittest.TestCase):
    """`sort_default`'s docstring must cite the value walk by symbol, not by a
    hardcoded `engine.py:NNNN` line that rots as surrounding code shifts."""

    def test_sort_default_docstring_has_no_hardcoded_engine_line(self) -> None:
        from goc.engine import sort_default

        doc = sort_default.__doc__ or ""
        stale = re.findall(r"engine\.py:\d+", doc)
        self.assertFalse(
            stale,
            msg=(
                "sort_default docstring cites a hardcoded line number "
                f"({stale}); cite the symbol instead so it cannot drift."
            ),
        )
        self.assertIn(
            "value_for",
            doc,
            msg=(
                "sort_default docstring should name `value_for` (the value "
                "walk's dangling-edge drop) it cross-references."
            ),
        )


class CreateCardScaffoldClaimAccuracyTest(unittest.TestCase):
    """`goc new` (engine._cmd_new) writes exactly README.md + log.md. Any skill
    description that advertises a reproduce.py *stub* as a scaffold deliverable
    overstates the tool — reproduce.py is hand-authored in create-card Step 6."""

    # The stale promise: reproduce.py named as a scaffolded stub.
    _STALE_STUB = re.compile(r"reproduce\.py\s+stub", re.IGNORECASE)
    _DESCRIPTION_FILES = [
        ROOT / "goc" / "templates" / "skills" / "create-card" / "SKILL.md",
        ROOT / "goc" / "templates" / "skills" / "deck" / "SKILL.md",
        ROOT / ".claude" / "skills" / "create-card" / "SKILL.md",
        ROOT / ".claude" / "skills" / "deck" / "SKILL.md",
    ]

    def test_no_skill_advertises_reproduce_py_stub_scaffold(self) -> None:
        for path in self._DESCRIPTION_FILES:
            if not path.exists():
                continue
            matches = self._STALE_STUB.findall(path.read_text())
            self.assertFalse(
                matches,
                msg=(
                    f"{path.relative_to(ROOT)}: advertises a 'reproduce.py stub' "
                    f"({len(matches)} occurrence(s)), but `goc new` never writes one. "
                    "reproduce.py is hand-authored in create-card Step 6; reword the claim."
                ),
            )

    def test_goc_new_writes_only_readme_and_log(self) -> None:
        """Pin the actual scaffold contract the descriptions must not overstate."""
        import tempfile

        import goc.engine as engine

        saved = (engine.DECK_DIR, engine.DECK_ROOT, engine.REPO_ROOT)
        try:
            with tempfile.TemporaryDirectory() as td:
                deck = Path(td) / "deck"
                deck.mkdir()
                engine.DECK_DIR = deck
                engine.DECK_ROOT = Path(td)
                engine.REPO_ROOT = Path(td)
                title = "scaffold-contract-probe-card"
                args = argparse.Namespace(
                    title=title,
                    summary=None,
                    contribution="low",
                    gate="none",
                    tags=["bug"],
                    worker=None,
                    allow_jargon=False,
                    commit=False,
                    no_commit=True,
                    advances_wire=[],
                    advanced_by_wire=[],
                )
                engine._cmd_new(args)
                written = sorted(p.name for p in (deck / title).iterdir())
        finally:
            engine.DECK_DIR, engine.DECK_ROOT, engine.REPO_ROOT = saved
        self.assertEqual(
            written,
            ["README.md", "log.md"],
            msg="goc new's file set changed; revisit the skill descriptions that document it.",
        )


GOC_MD = ROOT / "goc.md"


def _skill_dir_count(rel: str) -> int:
    return sum(1 for p in (ROOT / rel).iterdir() if p.is_dir())


class GocMdPluginReferenceAccuracyTest(unittest.TestCase):
    """`goc.md` is the plugin reference linked from README.md, ABOUT.md,
    CONTRIBUTING.md and the website. Its Claude section was authored against the
    pre-0.0.6 payload — symlinks into `goc/templates/`, a separately-installed
    `goc` binary — and its OpenClaw section against a 13-skill port. Each guard
    below derives the truth from the tree rather than restating a number, so a
    payload change turns the build red instead of rotting the doc again."""

    def _claude_section(self, start: str, end: str) -> str:
        text = GOC_MD.read_text()
        return text[text.index(start) : text.index(end)]

    def test_no_doc_calls_payload_assets_symlinks(self) -> None:
        """The marketplace install extracts only the `./claude-plugin` subtree, so
        an outside-pointing symlink vanishes on consumer install. The payload has
        been real files since `1df38953`; no doc may say otherwise."""
        symlinks = sorted(
            str(p.relative_to(ROOT))
            for base in ("claude-plugin/skills", "claude-plugin/hooks")
            for p in (ROOT / base).rglob("*")
            if p.is_symlink()
        )
        self.assertEqual(
            symlinks,
            [],
            msg=(
                "plugin payload contains symlink(s); marketplace install extracts "
                "only the ./claude-plugin subtree, so these disappear on consumer "
                "install. Re-run scripts/sync_plugin_assets.py."
            ),
        )
        self.assertNotRegex(
            GOC_MD.read_text(),
            re.compile(r"\*\*symlinks\*\*\s+into\s+`goc/templates/`"),
            msg=(
                "goc.md calls the plugin payload assets symlinks into "
                "goc/templates/, but the tree holds real byte-for-byte copies. "
                "The claim misdirects contributors into editing the mirror, whose "
                "edits the next sync-plugin-assets run silently overwrites."
            ),
        )

    def test_claude_skill_count_matches_payload(self) -> None:
        m = re.search(
            r"\*\*(\d+) GoC skills\*\* \(same as `goc install --agents claude`\)",
            GOC_MD.read_text(),
        )
        self.assertIsNotNone(m, msg="goc.md lost its Claude plugin skill-count bullet.")
        self.assertEqual(
            int(m.group(1)),
            _skill_dir_count("claude-plugin/skills"),
            msg="goc.md's Claude skill count disagrees with claude-plugin/skills/.",
        )

    def test_openclaw_skill_count_matches_payload(self) -> None:
        text = GOC_MD.read_text()
        m = re.search(r"\*\*(\d+) GoC skills\*\* as workspace-tier", text)
        self.assertIsNotNone(m, msg="goc.md lost its OpenClaw plugin skill-count bullet.")
        self.assertEqual(
            int(m.group(1)),
            _skill_dir_count("openclaw-plugin/skills"),
            msg="goc.md's OpenClaw skill count disagrees with openclaw-plugin/skills/.",
        )
        # `b30853e6` ported `kickoff` to OpenClaw; the section used to say it was
        # deferred to host-specific complements.
        if (ROOT / "openclaw-plugin" / "skills" / "kickoff").is_dir():
            self.assertNotIn(
                "`kickoff` skill is deferred",
                text,
                msg=(
                    "goc.md says the OpenClaw port defers the kickoff skill, but "
                    "openclaw-plugin/skills/kickoff/ ships."
                ),
            )

    def test_claude_prerequisites_do_not_demand_a_separate_cli_install(self) -> None:
        """`claude-plugin/bin/goc` runs the vendored engine, so Python 3.10+ is the
        only host prerequisite (AGENTS.md § "Plugin runs goc from a vendored
        engine")."""
        wrapper = (ROOT / "claude-plugin" / "bin" / "goc").read_text()
        self.assertIn("-m goc.cli", wrapper, msg="claude-plugin/bin/goc no longer runs the bundled engine.")
        self.assertTrue(
            (ROOT / "claude-plugin" / "goc" / "engine.py").exists(),
            msg="claude-plugin/goc/engine.py missing; the payload no longer vendors the engine.",
        )
        prereq = self._claude_section("### Prerequisites", "### Install from the marketplace")
        self.assertNotRegex(
            prereq,
            re.compile(r"shells to the `goc` CLI|install it first", re.IGNORECASE),
            msg=(
                "goc.md's Claude Prerequisites section demands a prior `goc` CLI "
                "install, but the plugin bundles the engine and bin/goc runs it. "
                "Python 3.10+ is the only host prerequisite."
            ),
        )

    def test_no_doc_promises_an_unimplemented_skill_dir_bootstrap_rewrite(self) -> None:
        """The bootstrap-path fix shipped as a `[ -f ]` guard with a bare-`goc`
        fallback, not the `${CLAUDE_SKILL_DIR}` rewrite goc.md promised. Guard
        against re-promising a fix no shipped skill uses."""
        used = any(
            "CLAUDE_SKILL_DIR" in p.read_text()
            for p in (ROOT / "goc" / "templates" / "skills").rglob("SKILL.md")
        )
        if not used:
            self.assertNotIn(
                "CLAUDE_SKILL_DIR",
                GOC_MD.read_text(),
                msg=(
                    "goc.md promises a ${CLAUDE_SKILL_DIR} bootstrap rewrite that "
                    "no shipped skill uses; the fix taken was a `[ -f ]` guard with "
                    "a bare-`goc` fallback (tests/test_skill_preamble_blocks.py)."
                ),
            )

    def test_claude_provides_list_names_every_registered_hook(self) -> None:
        """Every event in claude-plugin/hooks/hooks.json must appear in goc.md's
        "What the plugin provides" list — the Stop hook was missing from it."""
        import json

        registered = sorted(
            json.loads((ROOT / "claude-plugin" / "hooks" / "hooks.json").read_text())["hooks"]
        )
        provides = self._claude_section("### What the plugin provides", "### Prerequisites")
        missing = [event for event in registered if f"**{event} hook**" not in provides]
        self.assertFalse(
            missing,
            msg=(
                f"goc.md's Claude 'What the plugin provides' list omits hook "
                f"event(s) {missing} that claude-plugin/hooks/hooks.json registers."
            ),
        )


if __name__ == "__main__":
    unittest.main()
