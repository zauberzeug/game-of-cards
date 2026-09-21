"""Regression guard: generated agent guidance must not claim `goc done` auto-commits.

The shipped `done` command is a non-committing state flip (status + closed_at).
Any guidance surface that says "close + commit" in a single step contradicts the
implementation and misleads autonomous agents into believing a commit has landed.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import re
import sys
import tokenize
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


def _agents_schema_bullet() -> str:
    """Return the `goc/schema.yaml` bullet of AGENTS.md's architecture section.

    The bullet list ends at the first blank line, so slicing to the next
    `\\n\\n` yields the bullet alone — the prose paragraph that follows the
    list never leaks in.
    """
    section = _agents_architecture_section()
    start = section.index("**`goc/schema.yaml`**")
    end = section.index("\n\n", start)
    return section[start:end]


# Top-level keys of goc/schema.yaml. Read from the file so a future key is
# covered on the day it lands, rather than enumerated here and left to rot —
# the failure mode `schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen`
# already caught once in the sibling parity guard.
SKILL_TEMPLATES = ROOT / "goc" / "templates" / "skills"
_SCHEMA_TOP_LEVEL_KEYS = tuple(
    line.split(":", 1)[0]
    for line in (ROOT / "goc" / "schema.yaml").read_text().splitlines()
    if line[:1].isalpha() and ":" in line
)


def _agents_cli_bullet() -> str:
    """Return the `goc/cli.py` bullet of AGENTS.md's architecture section."""
    section = _agents_architecture_section()
    start = section.index("**`goc/cli.py`**")
    end = section.index("**`goc/engine.py`**")
    return section[start:end]


def _engine_subcommands() -> set[str]:
    """Every subcommand the engine's argparse parser registers."""
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("no subparsers found on engine parser")


def _engine_registers_version() -> bool:
    """True iff the engine parser owns the `--version` action."""
    from goc.engine import _build_parser

    return any("--version" in a.option_strings for a in _build_parser()._actions)


CLI_PY = ROOT / "goc" / "cli.py"


def _cli_tree() -> ast.Module:
    return ast.parse(CLI_PY.read_text(encoding="utf-8"), filename=str(CLI_PY))


def _cli_calls(name: str) -> bool:
    """True iff `goc/cli.py` calls `name(...)` anywhere.

    An import alone is not a call — the distinction the stale bullet lost.
    """
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(_cli_tree())
    )


def _cli_registers_version() -> bool:
    """True iff `goc/cli.py` itself calls `.add_argument("--version", ...)`."""
    for node in ast.walk(_cli_tree()):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue
        if any(isinstance(a, ast.Constant) and a.value == "--version" for a in node.args):
            return True
    return False


class AgentsArchitectureAccuracyTest(unittest.TestCase):
    def test_cli_bullet_does_not_mention_click(self) -> None:
        self.assertNotRegex(
            _agents_cli_bullet(),
            re.compile(r"click", re.IGNORECASE),
            msg="AGENTS.md goc/cli.py bullet still mentions Click; the package uses argparse.",
        )

    def test_entry_point_wiring_is_what_the_cli_bullet_describes(self) -> None:
        """The behavioural half: the three facts the doc assertions below rest on.

        Deriving them from the tree — rather than restating them in prose —
        means the day somebody really does move the parser build, the verb
        registration, or `--version` into `goc/cli.py`, this test fails first
        and points the editor at the bullet, instead of the doc guards below
        silently pinning a claim that has become false in the other direction.
        Regression guard for
        `agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does`,
        which is how all three clauses came to be false at once.
        """
        self.assertFalse(
            _cli_calls("_build_parser"),
            msg=(
                "goc/cli.py now calls `_build_parser` itself; the engine parser "
                "used to be built inside `engine.cli()`. Re-derive the AGENTS.md "
                "goc/cli.py bullet and the doc assertions below it."
            ),
        )
        self.assertEqual(
            sorted(_engine_subcommands() & {"install", "upgrade"}),
            [],
            msg=(
                "install/upgrade are now engine subcommands; they used to be "
                "intercepted on argv[0] before argparse. Re-derive the AGENTS.md "
                "goc/cli.py bullet — and revisit the open card "
                "`goc-help-omits-install-and-upgrade-subcommands`, whose premise "
                "is that they never reach that parser."
            ),
        )
        self.assertFalse(
            _cli_registers_version(),
            msg=(
                "goc/cli.py now registers `--version` itself; it used to be an "
                "action on the engine parser. Re-derive the AGENTS.md goc/cli.py "
                "bullet and the doc assertion below it."
            ),
        )
        self.assertTrue(
            _engine_registers_version(),
            msg=(
                "the engine parser no longer registers `--version`; the AGENTS.md "
                "goc/cli.py bullet attributes it there."
            ),
        )

    def test_cli_bullet_does_not_attribute_the_parser_build_to_cli_py(self) -> None:
        bullet = _agents_cli_bullet()
        self.assertNotRegex(
            bullet,
            re.compile(r"[Bb]uilds\s+the\s+engine's\s+argparse\s+parser", re.DOTALL),
            msg=(
                "AGENTS.md goc/cli.py bullet says cli.py builds the engine's "
                "argparse parser. It imports nothing of the sort at call time — "
                "`engine.cli()` builds it (goc/engine.py). Name the delegate, not "
                "a composition step that does not happen."
            ),
        )
        self.assertIn(
            "engine.cli()",
            bullet,
            msg=(
                "AGENTS.md goc/cli.py bullet does not name `engine.cli()`. That "
                "delegate is where the parser is built and where every global "
                "flag is handled; without it the bullet leaves an agent looking "
                "for a parser object cli.py does not hold."
            ),
        )

    def test_cli_bullet_does_not_claim_install_and_upgrade_are_registered(self) -> None:
        bullet = _agents_cli_bullet()
        self.assertNotRegex(
            bullet,
            re.compile(r"bolts\s+on", re.IGNORECASE | re.DOTALL),
            msg=(
                "AGENTS.md goc/cli.py bullet says install/upgrade are bolted onto "
                "the engine parser. They are intercepted on argv[0] before "
                "argparse and routed to standalone parsers — which is exactly why "
                "`goc --help` omits them."
            ),
        )
        self.assertIn(
            "argv[0]",
            bullet,
            msg=(
                "AGENTS.md goc/cli.py bullet does not name the argv[0] "
                "interception. It is the mechanism an agent has to change to fix "
                "`goc --help`, and the bullet is the map that agent reads first."
            ),
        )

    def test_cli_bullet_does_not_attribute_version_to_cli_py(self) -> None:
        self.assertNotRegex(
            _agents_cli_bullet(),
            re.compile(r"adds\s+`--version`", re.DOTALL),
            msg=(
                "AGENTS.md goc/cli.py bullet says cli.py adds `--version`. It is "
                "registered by `engine._build_parser`, as cli.py's own comment "
                "states — attribute it to the engine parser."
            ),
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

    def test_skill_body_really_carries_no_inlined_schema(self) -> None:
        """The behavioural half: assert what the doc bullet is allowed to say.

        The two doc assertions below only hold while the schema genuinely
        ships as a sibling asset. Deriving that from the file — rather than
        restating it — means the day someone implements real inlining, this
        test fails first and points the editor at the bullet, instead of the
        doc guard silently pinning a claim that has become false again.
        """
        body = (SKILL_TEMPLATES / "card-schema" / "SKILL.md").read_text()
        inlined = [key for key in _SCHEMA_TOP_LEVEL_KEYS if key in body]
        self.assertEqual(
            inlined,
            [],
            msg=(
                "card-schema/SKILL.md now contains schema key(s) "
                f"{inlined} — the schema may really be inlined into the skill "
                "body. Re-derive the AGENTS.md `goc/schema.yaml` bullet and the "
                "two doc assertions below it."
            ),
        )

    def test_schema_bullet_does_not_claim_inlining(self) -> None:
        self.assertNotRegex(
            _agents_schema_bullet(),
            re.compile(r"inlin", re.IGNORECASE),
            msg=(
                "AGENTS.md goc/schema.yaml bullet claims the schema is inlined "
                "into the card-schema skill body. `goc install` copies skill "
                "assets verbatim (`_iter_skill_assets`); the schema lands as a "
                "sibling file next to SKILL.md. The word is banned outright "
                "rather than matched in its affirmative form only: state the "
                "mechanism that exists ('ships as a sibling file'), not a "
                "denial of the one that does not."
            ),
        )

    def test_schema_bullet_names_the_second_checked_in_copy(self) -> None:
        self.assertIn(
            "goc/templates/skills/card-schema/schema.yaml",
            _agents_schema_bullet(),
            msg=(
                "AGENTS.md goc/schema.yaml bullet does not name the second "
                "checked-in copy. No script syncs it from goc/schema.yaml, so "
                "an agent that edits only the engine schema turns "
                "tests/test_skill_schema_yaml_parity.py red with no pointer to "
                "the file that also has to move."
            ),
        )


# Comments that tell an editor where to re-derive a mirrored CLI surface must
# name the framework goc actually uses. The package dropped Click for argparse,
# so a lingering `click` mention sends that editor grepping for a command group
# the repo does not contain.
_CLI_FRAMEWORK_POINTER_FILES = [
    ROOT / "openclaw-plugin" / "index.ts",
]


class CliFrameworkPointerAccuracyTest(unittest.TestCase):
    def test_mirror_comments_do_not_name_click(self) -> None:
        for path in _CLI_FRAMEWORK_POINTER_FILES:
            self.assertNotRegex(
                path.read_text(encoding="utf-8"),
                re.compile(r"click", re.IGNORECASE),
                msg=(
                    f"{path.relative_to(ROOT)} names Click as goc's CLI framework; "
                    "the engine builds its subparsers with argparse in "
                    "`_build_parser` (goc/engine.py)."
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


class ClaudeSettingsOwnershipAccuracyTest(unittest.TestCase):
    """`.claude/settings.json` is the Claude Code hook-registration manifest that
    `goc install` / `goc upgrade` merge `GOC_CLAUDE_HOOKS` into (and that the
    plugin-mode cleanup strips those entries back out of) — a shared-ownership
    merge target, not a per-repo file goc leaves alone. AGENTS.md used to call it
    a "project-specific permission allow-list", which is wrong twice over: goc
    writes no `permissions` key anywhere, and the file is not hands-off. Both
    guards derive the truth from the tree so the claim cannot rot again."""

    # Every surface that tells a reader which files they may hand-edit.
    _OWNERSHIP_DOCS = ("AGENTS.md", "goc.md", "CONTRIBUTING.md")

    def test_no_doc_calls_settings_json_a_permission_allow_list(self) -> None:
        offenders = []
        for rel in self._OWNERSHIP_DOCS:
            path = ROOT / rel
            if not path.exists():
                continue
            # Collapse wrapping: the claim spanned three source lines.
            flat = re.sub(r"\s+", " ", path.read_text())
            for phrase in ("permission allow-list", "permission allowlist"):
                if phrase in flat and ".claude/settings.json" in flat:
                    window = flat[
                        max(0, flat.index(phrase) - 120) : flat.index(phrase) + 60
                    ]
                    if ".claude/settings.json" in window:
                        offenders.append(f"{rel}: ...{window}...")
        self.assertFalse(
            offenders,
            msg=(
                "`.claude/settings.json` holds hook registrations, not permissions. "
                "goc has never written a `permissions` key; describe the file as the "
                "hook-registration manifest whose GoC entries come from "
                "GOC_CLAUDE_HOOKS in goc/install.py.\n" + "\n".join(offenders)
            ),
        )

    def test_engine_writes_no_permissions_key(self) -> None:
        """The premise the guard above rests on: if goc ever *does* start writing a
        permissions block, this test fails and the docs must be revisited together
        with it — rather than the doc claim silently becoming true again."""
        for rel in ("goc/install.py", "goc/engine.py"):
            with self.subTest(module=rel):
                self.assertNotIn(
                    "permissions",
                    (ROOT / rel).read_text(),
                    msg=(
                        f"{rel} now references `permissions`. If goc writes a "
                        f"permission allow-list, update the "
                        f"`.claude/settings.json` ownership paragraph in AGENTS.md "
                        f"and relax the guard above in the same change."
                    ),
                )

    def test_agents_md_names_the_hook_registration_constant(self) -> None:
        """The corrected paragraph must point at the real edit site, so a
        contributor changes `GOC_CLAUDE_HOOKS` instead of the generated file."""
        flat = re.sub(r"\s+", " ", (ROOT / "AGENTS.md").read_text())
        anchor = ".claude/settings.json` is the"
        self.assertIn(
            anchor,
            flat,
            msg=(
                "AGENTS.md no longer explains what `.claude/settings.json` is. The "
                "dogfood-sync section must say it is the Claude Code "
                "hook-registration manifest goc merges GOC_CLAUDE_HOOKS into."
            ),
        )
        start = flat.index(anchor)
        paragraph = flat[start : start + 900]
        for expected in ("GOC_CLAUDE_HOOKS", "goc/install.py"):
            self.assertIn(
                expected,
                paragraph,
                msg=(
                    f"AGENTS.md's `.claude/settings.json` ownership paragraph no "
                    f"longer names {expected}; a reader cannot tell where the "
                    f"hook registrations actually come from."
                ),
            )


class CardLanguageGuardAccuracyTest(unittest.TestCase):
    """AGENTS.md § "Card authoring rules" now tells the reader that the
    English-only rule is guarded, names the script, the pre-commit hook id and
    the test module that enforce it, and states which fields are scanned. Those
    are five prose restatements of tree state, which is exactly the family
    `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
    catalogues: a claim added without a pin, found stale later by a human. Each
    assertion below derives the truth from the tree instead, so deleting the
    hook, renaming the script or changing the scanned-field set fails here
    rather than turning AGENTS.md into a lie."""

    _GUARD_SCRIPT = "scripts/check_card_language.py"
    _GUARD_TEST = "tests/test_card_authoring_rules.py"
    _HOOK_ID = "card-language"

    def _english_only_bullet(self) -> str:
        flat = re.sub(r"\s+", " ", (ROOT / "AGENTS.md").read_text())
        anchor = "**English only.**"
        self.assertIn(
            anchor,
            flat,
            msg="AGENTS.md no longer states the English-only card-authoring rule.",
        )
        start = flat.index(anchor)
        return flat[start : start + 900]

    def test_named_enforcement_files_exist(self) -> None:
        bullet = self._english_only_bullet()
        for rel in (self._GUARD_SCRIPT, self._GUARD_TEST):
            with self.subTest(path=rel):
                self.assertIn(
                    rel,
                    bullet,
                    msg=(
                        f"AGENTS.md's English-only bullet no longer names {rel}; a "
                        f"reader cannot tell what enforces the rule."
                    ),
                )
                self.assertTrue(
                    (ROOT / rel).exists(),
                    msg=(
                        f"AGENTS.md says the English-only rule is guarded by {rel}, "
                        f"but that file does not exist. Either restore it or drop "
                        f"the claim — the rule is unenforced without it."
                    ),
                )

    def test_named_precommit_hook_is_registered(self) -> None:
        bullet = self._english_only_bullet()
        self.assertIn(
            f"`{self._HOOK_ID}` pre-commit hook",
            bullet,
            msg="AGENTS.md no longer names the pre-commit hook that runs the guard.",
        )
        config = (ROOT / ".pre-commit-config.yaml").read_text()
        # Anchor the whole line: a plain substring check would accept a renamed or
        # disabled hook (`id: card-language-DISABLED` contains `id: card-language`).
        self.assertRegex(
            config,
            re.compile(rf"^\s*-\s*id:\s*{re.escape(self._HOOK_ID)}\s*$", re.MULTILINE),
            msg=(
                f"AGENTS.md claims a `{self._HOOK_ID}` pre-commit hook enforces the "
                f"English-only rule, but .pre-commit-config.yaml registers no such "
                f"hook. Filing-time enforcement is gone; fix the wiring or the claim."
            ),
        )
        self.assertIn(
            "check_card_language.py",
            config,
            msg=(
                f"the `{self._HOOK_ID}` pre-commit hook no longer invokes "
                f"check_card_language.py."
            ),
        )

    def test_claimed_scanned_fields_match_the_guard(self) -> None:
        """The bullet lists the fields the guard covers. Derive that list from the
        guard itself so widening or narrowing its scope cannot silently diverge
        from what AGENTS.md promises."""
        spec = importlib.util.spec_from_file_location(
            "_goc_card_language_guard_doccheck", ROOT / self._GUARD_SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        bullet = self._english_only_bullet()
        for field in module.SCANNED_FIELDS:
            with self.subTest(field=field):
                self.assertIn(
                    f"`{field}`",
                    bullet,
                    msg=(
                        f"{self._GUARD_SCRIPT} scans `{field}`, but AGENTS.md's "
                        f"English-only bullet does not list it. A reader would "
                        f"under-estimate the guard's reach."
                    ),
                )
        # The inverse: the bullet must not advertise coverage the guard lacks.
        # Bodies are the field the guard deliberately skips, and the bullet says so.
        self.assertNotIn(
            "body",
            module.SCANNED_FIELDS,
            msg=(
                "the guard now scans card bodies. AGENTS.md's English-only bullet "
                "says it does not — update the bullet in the same change."
            ),
        )

    def test_common_commands_block_lists_a_runnable_guard_invocation(self) -> None:
        """AGENTS.md § "Common commands" advertises the guard as a command a
        contributor can run. Pin the referenced path so the recipe cannot rot."""
        commands = (ROOT / "AGENTS.md").read_text()
        self.assertIn(
            f"python {self._GUARD_SCRIPT}",
            commands,
            msg=(
                "AGENTS.md's Common commands block no longer offers a way to run "
                "the card-language guard by hand."
            ),
        )


class UpgradeNoOpGuardParagraphAccuracyTest(unittest.TestCase):
    """AGENTS.md § "Code architecture" tells the reader that `upgrade()`'s
    "nothing to do" verdict is derived from the write plan, and closes by
    accounting for the terms that sit *beside* the plan in the short-circuit.

    That closing sentence is the reader's check on the paragraph's load-bearing
    claim (do not add a `pending_*` term for a new write). It drifted once — it
    said two terms, all non-write, while `upgrade()` carried three and the third
    gated a write to `.game-of-cards/config.yaml`
    (`agents-md-miscounts-the-upgrade-no-op-guard-terms-and-mislabels-them-non-write`).
    Derive both the count and which terms write from the source so the next term
    added turns the build red instead of re-opening that card silently.
    """

    _SENTENCE_RE = re.compile(
        r"The (\w+) remaining terms? next to the plan[^.]*\.", re.DOTALL
    )
    _NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}

    def _upgrade_fn(self) -> ast.FunctionDef:
        tree = ast.parse((ROOT / "goc" / "install.py").read_text())
        fn = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
            ),
            None,
        )
        self.assertIsNotNone(fn, msg="goc/install.py no longer defines `upgrade()`")
        return fn

    def _guard_terms(self, fn: ast.FunctionDef) -> list[str]:
        """The `pending_*` work signals negated into `upgrade()`'s short-circuit.

        Scoped to the `pending_*` prefix because that is the register the
        sentence counts. The guard's other negated operands (`agents_explicit`,
        `keep_local_skills`) are caller-flag overrides, not answers to "is there
        work?", so they are outside what the sentence describes.
        """
        for node in ast.walk(fn):
            if not isinstance(node, ast.If) or not isinstance(node.test, ast.BoolOp):
                continue
            names = [
                operand.operand.id
                for operand in node.test.values
                if isinstance(operand, ast.UnaryOp)
                and isinstance(operand.op, ast.Not)
                and isinstance(operand.operand, ast.Name)
            ]
            if "plan_has_effect" in names:
                return [name for name in names if name.startswith("pending_")]
        self.fail(
            "no short-circuit in `upgrade()` negates `plan_has_effect`. The "
            "plan-derived no-op verdict AGENTS.md describes is gone or renamed; "
            "rewrite the paragraph and this guard together."
        )

    def _writing_terms(self, fn: ast.FunctionDef) -> dict[str, str]:
        """`pending_*` terms that gate a write, mapped to the executor they probe.

        A term assigned from a call carrying `probe=True` is asking that
        executor whether it would change a file, so it is true exactly when the
        real call writes — the repo-wide convention the same paragraph names.
        Derived, not listed, so a new probing term joins the set without a
        hand-maintained register. A term that gates a write *without* probing is
        not detected here; the count assertion is what catches that shape.
        """
        found: dict[str, str] = {}
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or not target.id.startswith("pending_"):
                continue
            for call in ast.walk(node.value):
                if isinstance(call, ast.Call) and any(
                    kw.arg == "probe" and getattr(kw.value, "value", None) is True
                    for kw in call.keywords
                ):
                    found[target.id] = ast.unparse(call.func)
        return found

    def _sentence(self) -> tuple[int, str]:
        match = self._SENTENCE_RE.search((ROOT / "AGENTS.md").read_text())
        self.assertIsNotNone(
            match,
            msg=(
                "AGENTS.md no longer accounts for the terms beside the write plan "
                "in `upgrade()`'s short-circuit. That sentence is what stops a "
                "contributor from reading the paragraph as 'every write is in the "
                "plan'; restore it rather than dropping it."
            ),
        )
        word = match.group(1).lower()
        self.assertIn(
            word,
            self._NUMBER_WORDS,
            msg=f"unparseable count word in AGENTS.md's remaining-terms sentence: {word!r}",
        )
        return self._NUMBER_WORDS[word], " ".join(match.group(0).split())

    def test_sentence_count_matches_the_guard(self) -> None:
        terms = self._guard_terms(self._upgrade_fn())
        count, sentence = self._sentence()
        self.assertEqual(
            count,
            len(terms),
            msg=(
                f"AGENTS.md says {count} terms sit beside the write plan in "
                f"`upgrade()`'s short-circuit, but it ANDs {len(terms)}: "
                f"{', '.join(terms)}. Update the sentence in the same change that "
                f"added or removed the term — and prefer planning the work as a "
                f"`PlannedWrite` over adding another `pending_*` term."
            ),
        )

    def test_sentence_does_not_call_a_writing_term_non_write(self) -> None:
        fn = self._upgrade_fn()
        terms = self._guard_terms(fn)
        writers = {k: v for k, v in self._writing_terms(fn).items() if k in terms}
        _, sentence = self._sentence()
        if not writers:
            return
        self.assertNotIn(
            "non-write",
            sentence,
            msg=(
                "AGENTS.md characterizes the terms beside the plan as non-write "
                "work, but " + ", ".join(sorted(writers)) + " probes "
                + ", ".join(sorted(writers.values()))
                + " and is true exactly when that executor would write. Say what "
                "the terms are — work the plan does not model — not that they "
                "never write."
            ),
        )

    def test_sentence_names_every_writing_term(self) -> None:
        fn = self._upgrade_fn()
        terms = self._guard_terms(fn)
        writers = {k: v for k, v in self._writing_terms(fn).items() if k in terms}
        _, sentence = self._sentence()
        for term in sorted(writers):
            # The prose names the pin by its config key (`skills_source`), not by
            # the local variable, so match on the `pending_` prefix stripped off.
            with self.subTest(term=term):
                self.assertIn(
                    term.removeprefix("pending_"),
                    sentence,
                    msg=(
                        f"{term} gates a write (it probes {writers[term]}), but "
                        f"AGENTS.md's remaining-terms sentence never names it. A "
                        f"reader cannot tell which of the terms writes, which is "
                        f"the one thing the sentence exists to disambiguate."
                    ),
                )


# ── A guidance surface may not recommend a deprecated `goc status` target ──
#
# `purge-blocked-status-from-skills-and-docs` soft-deprecated `status: blocked`
# across the skill bodies, but its scope named only the skills and the AGENTS
# files — so `goc.md`, the CLI reference published at game-of-cards.com/goc/,
# kept offering the value as one of five unmarked target states and never named
# the `goc wait` overlay that replaced it. See deck card
# `cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay`.
#
# The deprecated set is DERIVED from the skill bodies rather than pinned to the
# word `blocked`, for two reasons: a future deprecation is covered the moment
# the skills announce it, and when the enum removal drops the value from
# `MUTABLE_STATUS_VALUES` the set empties and these guards retire themselves.

_STATUS_GUIDANCE_FILES = [
    GOC_MD,
    ROOT / "goc" / "templates" / "AGENTS_GOC.md",
    ROOT / "AGENTS.md",
]

# The overlay the skills point a legacy `blocked` card at. Only asserted while
# something is actually deprecated.
_OVERLAY_TOKENS = ("goc wait", "waiting_on")

_DEPRECATION_MARKER = re.compile(r"deprecat|\blegacy\b|being removed", re.IGNORECASE)

# "`<v>` is deprecated" / "legacy `status: <v>`". The value has to sit adjacent
# to the marker, so an unrelated status named later in the same sentence — say
# the `open` a migration instruction tells you to drop to — is not swept in.
_DEPRECATION_BINDINGS = (
    re.compile(r"`(?:status:\s*)?(?P<value>[a-z]+)`[^`]{0,40}?\bis deprecated\b"),
    re.compile(
        r"\b(?:deprecated|legacy)\b[^`]{0,40}?`(?:status:\s*)?(?P<value>[a-z]+)`"
    ),
)


def _deprecated_status_values() -> set[str]:
    """Target states of `goc status` that the shipped skill bodies deprecate.

    The skills are the authoritative surface — they are what the purge card
    rewrote — so whatever they bind to a deprecation marker is what no other
    guidance surface may recommend. Intersected with the verb's real choices so
    prose about a value the CLI no longer accepts cannot resurrect the guard.
    """
    from goc.engine import MUTABLE_STATUS_VALUES

    accepted = set(MUTABLE_STATUS_VALUES)
    found: set[str] = set()
    for path in sorted(SKILL_TEMPLATES.rglob("*.md")):
        body = path.read_text()
        for pattern in _DEPRECATION_BINDINGS:
            found.update(
                m.group("value") for m in pattern.finditer(body)
            )
    return found & accepted


class DeprecatedStatusGuidanceTest(unittest.TestCase):
    def test_skill_bodies_still_announce_a_deprecation(self) -> None:
        """The behavioural half: assert the derivation has something to find.

        Both guards below are vacuous if this set is empty. An empty set is
        legitimate exactly once — after the enum removal lands — and at that
        point `MUTABLE_STATUS_VALUES` no longer carries the value either, so
        assert the two agree instead of silently passing.
        """
        from goc.engine import MUTABLE_STATUS_VALUES

        deprecated = _deprecated_status_values()
        if deprecated:
            return
        self.assertNotIn(
            "blocked",
            set(MUTABLE_STATUS_VALUES),
            msg=(
                "No skill body binds a `goc status` target to a deprecation "
                "marker, yet the verb still accepts `blocked`. Either the "
                "skills lost their deprecation notice (restore it) or the "
                "binding patterns in _DEPRECATION_BINDINGS no longer match "
                "how they word it (re-derive them)."
            ),
        )

    def test_no_guidance_surface_offers_a_deprecated_status_unmarked(self) -> None:
        deprecated = _deprecated_status_values()
        for path in _STATUS_GUIDANCE_FILES:
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                if "goc status" not in line:
                    continue
                offered = sorted(
                    v
                    for v in deprecated
                    if re.search(rf"`[^`]*\b{re.escape(v)}\b[^`]*`", line)
                )
                if not offered or _DEPRECATION_MARKER.search(line):
                    continue
                rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                self.fail(
                    f"{rel}:{lineno} presents deprecated "
                    f"`goc status` target state(s) {offered} with no "
                    f"deprecation marker:\n  {line.strip()}\n"
                    "The skill bodies call these deprecated; a reader "
                    "following this line produces a card that validates OK "
                    "yet drops out of every `status: open` query with no "
                    "reason recorded. Mark it on the same line, or drop it "
                    "and point at `goc wait`."
                )

    def test_cli_reference_documents_the_overlay_that_replaced_them(self) -> None:
        """Marking the value deprecated is only half the fix — the reference has
        to name what to use instead, on the page the reader is already on."""
        if not _deprecated_status_values():
            self.skipTest("nothing deprecated; the overlay needs no signposting")
        text = GOC_MD.read_text()
        missing = [t for t in _OVERLAY_TOKENS if t not in text]
        self.assertEqual(
            [],
            missing,
            msg=(
                f"goc.md never mentions {missing}, so a reader who finds the "
                "deprecated status marked has no way to learn the replacement "
                "from the CLI reference itself."
            ),
        )


# ---------------------------------------------------------------------------
# CONTRIBUTING.md — the contributor on-ramp
# ---------------------------------------------------------------------------
#
# Every other surface in this file is read by an agent or an existing
# contributor, who can route around a stale sentence. CONTRIBUTING.md is what
# GitHub links from the issue form, the pull-request form and the repository
# sidebar, so it is the first file an outside contributor opens — and until
# `contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions`
# no guard had ever swept it. Seven of its claim groups restate tree state, and
# every one of them had drifted.
#
# The checks below take the guide's text as an argument instead of reading the
# file, so the same logic can be run against the pre-fix wording
# (`_HISTORICAL_CONTRIBUTING`) to prove none of them is vacuous.

CONTRIBUTING = ROOT / "CONTRIBUTING.md"

_NUMBER_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}

# Sections that must name every sync-owned plugin payload. Each tells the reader
# something actionable about the set — what the surface area is, what the
# byte-mirrors are, what never to hand-edit — so a payload missing from any one
# of them reads as "that one is not a mirror". `codex-plugin/` was absent from
# all three, and from the whole file, while CI failed on its drift like the rest.
_PAYLOAD_ROSTER_SECTIONS = (
    "## About the project",
    "## Setting up your environment",
    "## For maintainers",
)

# Words allowed in a `pre-commit run --all-files` comment beside the hook ids.
# Deliberately tiny: the comment's job is to be the registered roster verbatim,
# because that is the string `pre-commit run <id>` takes. Prose in its place is
# what let one copy claim a formatter the hook set has never contained.
_PRECOMMIT_COMMENT_CONNECTORS = frozenset({"and"})

# The instruction shape the card found, not one day's phrasing of it: `goc
# upgrade` offered as the way to refresh a mirror. It is the *consuming*-repo
# verb and plans no write into any payload here.
_UPGRADE_AS_REFRESH = re.compile(
    r"(?:re-)?run\s+`goc upgrade`\s+(?:rather than|instead of)"
)

_CONTRIBUTING_CHECKS = (
    "conventions-pointer",
    "source-file-count",
    "payload-roster",
    "precommit-hook-set",
    "mirror-refresh-mechanism",
    "release-rewrite-targets",
    "quote-style",
)


def _load_repo_script(stem: str):
    """Import `scripts/<stem>.py` without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        f"_goc_doccheck_{stem}", ROOT / "scripts" / f"{stem}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(text: str, heading: str) -> str:
    """The body of one `## ` section, or "" if the heading is gone."""
    start = text.find(heading)
    if start == -1:
        return ""
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def _package_source_files() -> list[str]:
    """The `goc/` package's own modules — the template payload is not source."""
    return sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "goc").rglob("*.py")
        if "templates" not in p.relative_to(ROOT / "goc").parts
    )


def _sync_owned_payloads() -> list[str]:
    """Root-level `*-plugin/` payloads `scripts/sync_plugin_assets.py` regenerates."""
    sync = _load_repo_script("sync_plugin_assets")
    roots = {dst.relative_to(ROOT).parts[0] for _src, dst, _ex, _keep in sync.SYNC_PAIRS}
    return sorted(r for r in roots if r.endswith("-plugin"))


def _precommit_hook_ids() -> list[str]:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    return re.findall(r"^\s+- id: (\S+)$", config, re.MULTILINE)


def _release_rewrite_targets() -> list[str]:
    """Every repo path `scripts/release_rewrite_versions.py` writes a version into.

    Read as `ROOT / "a" / "b"` path chains rather than a hand-kept list, so a
    sixth manifest is covered the day it is added. Only maximal chains count —
    `ast.walk` also yields the inner `ROOT / "a"` of every longer path.
    """
    src = ROOT / "scripts" / "release_rewrite_versions.py"
    tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
    divs = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]
    nested = {id(n.left) for n in divs}
    targets: set[str] = set()
    for node in divs:
        if id(node) in nested:
            continue
        parts: list[str] = []
        cur: ast.expr = node
        while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
            if not isinstance(cur.right, ast.Constant) or not isinstance(cur.right.value, str):
                parts = []
                break
            parts.insert(0, cur.right.value)
            cur = cur.left
        if parts and isinstance(cur, ast.Name) and cur.id == "ROOT":
            targets.add("/".join(parts))
    return sorted(targets)


def _package_quote_counts() -> tuple[int, int]:
    """(single, double) non-docstring string literals under `goc/`."""
    single = double = 0
    for path in (ROOT / "goc").rglob("*.py"):
        if "templates" in path.relative_to(ROOT / "goc").parts:
            continue
        for tok in tokenize.tokenize(io.BytesIO(path.read_bytes()).readline):
            if tok.type != tokenize.STRING:
                continue
            body = tok.string.lstrip("rbfuRBFU")
            if body.startswith(('"""', "'''")):
                continue
            if body.startswith('"'):
                double += 1
            elif body.startswith("'"):
                single += 1
    return single, double


def _contributing_findings(text: str) -> dict[str, str]:
    """Grade the guide's tree-derived claims. Returns {check-id: what's wrong}."""
    out: dict[str, str] = {}

    # --- 1. the documents the guide routes readers to ---------------------
    unreadable: list[str] = []
    for target in re.findall(r"\]\((?!https?://|#)([^)\s]+)\)", text):
        path = ROOT / target.split("#", 1)[0]
        if not path.exists():
            unreadable.append(f"{target} (no such file)")
        elif path.suffix == ".md" and not [
            ln
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("@")
        ]:
            unreadable.append(f"{target} (no prose — a bare `@` import)")
    if unreadable:
        out["conventions-pointer"] = (
            "CONTRIBUTING.md links " + "; ".join(unreadable) + " as documents to "
            "read. An `@`-import is expanded by exactly one of the four runtimes "
            "this project ships for; a human, a browser and every non-Claude agent "
            "get the literal line and no content. Link the file that carries the "
            "prose, not the shim that imports it."
        )

    # --- 2. "(N source files under `goc/`)" -------------------------------
    sources = _package_source_files()
    about = _section(text, "## About the project")
    claimed = re.search(r"\((\d+) source files under `goc/`\)", about)
    if not claimed or int(claimed.group(1)) != len(sources):
        out["source-file-count"] = (
            f"§ About the project claims {claimed.group(1) if claimed else 'no'} "
            f"source file(s) under `goc/`; the package has {len(sources)}: "
            + ", ".join(sources)
        )

    # --- 3. the plugin-payload roster -------------------------------------
    payloads = _sync_owned_payloads()
    roster: list[str] = []
    for heading in _PAYLOAD_ROSTER_SECTIONS:
        absent = [p for p in payloads if f"{p}/" not in _section(text, heading)]
        if absent:
            roster.append(f"§ {heading.lstrip('# ')} omits {', '.join(absent)}")
    counted = re.search(r"the (\w+) plugin payloads", text)
    if counted and counted.group(1) != _NUMBER_WORDS.get(len(payloads)):
        roster.append(
            f"it calls them 'the {counted.group(1)} plugin payloads'"
        )
    if roster:
        out["payload-roster"] = (
            f"the sync hook regenerates {len(payloads)} payloads ("
            + ", ".join(f"{p}/" for p in payloads)
            + ") and CI fails on any of their drift, but "
            + "; ".join(roster)
            + ". A payload the guide never names reads as one a contributor may hand-edit."
        )

    # --- 4. what `pre-commit run --all-files` runs -------------------------
    hook_ids = _precommit_hook_ids()
    comments = [
        (i, ln.split("#", 1)[1].strip())
        for i, ln in enumerate(text.splitlines(), 1)
        if "pre-commit run --all-files" in ln and "#" in ln
    ]
    hooks: list[str] = []
    if not comments:
        hooks.append("no `pre-commit run --all-files` line names the hook set at all")
    for lineno, comment in comments:
        absent = [h for h in hook_ids if h not in comment]
        stray = [
            tok
            for tok in re.findall(r"[A-Za-z][A-Za-z-]*", comment)
            if tok not in hook_ids and tok not in _PRECOMMIT_COMMENT_CONNECTORS
        ]
        if absent:
            hooks.append(f"line {lineno} omits {', '.join(absent)}")
        if stray:
            hooks.append(f"line {lineno} says {comment!r}, which is not the roster")
    if hooks:
        out["precommit-hook-set"] = (
            ".pre-commit-config.yaml registers " + ", ".join(hook_ids) + ", but "
            + "; ".join(hooks)
            + ". Name the ids verbatim — they are what `pre-commit run <id>` takes, "
            "and the card hooks among them fire on `goc new --commit` too, so a "
            "contributor meets them while filing, not only in CI."
        )

    # --- 5. what refreshes the mirrors ------------------------------------
    conventions = _section(text, "## Coding conventions")
    mechanism: list[str] = []
    for token, present in (
        ("scripts/sync_plugin_assets.py", (ROOT / "scripts" / "sync_plugin_assets.py").exists()),
        ("sync-plugin-assets", "sync-plugin-assets" in hook_ids),
    ):
        if not present:
            mechanism.append(f"{token} is gone from the tree")
        elif token not in conventions:
            mechanism.append(f"§ Coding conventions never names {token}")
    if _UPGRADE_AS_REFRESH.search(text):
        mechanism.append("it still offers `goc upgrade` as the way to refresh a mirror")
    if mechanism:
        out["mirror-refresh-mechanism"] = (
            "; ".join(mechanism)
            + ". The `sync-plugin-assets` pre-commit hook is what regenerates every "
            "mirror in this tree; `goc upgrade` writes into a *consuming* repo and "
            "plans no write into any payload here, so a contributor who runs it "
            "expecting a refreshed mirror gets an unchanged one and fails CI."
        )

    # --- 6. what the release rewrites -------------------------------------
    release = _section(text, "## Release process")
    targets = _release_rewrite_targets()
    manifests = [t for t in targets if t.endswith(".json")]
    rewrite: list[str] = []
    counted = re.search(r"the\s+(\w+)\s+plugin manifests", release)
    if not counted or counted.group(1) != _NUMBER_WORDS.get(len(manifests)):
        rewrite.append(
            f"it calls them '{counted.group(1) if counted else 'no'} plugin "
            f"manifests'; the script rewrites {len(manifests)}"
        )
    unnamed = [t for t in targets if t not in release]
    if unnamed:
        rewrite.append("it never names " + ", ".join(unnamed))
    if rewrite:
        out["release-rewrite-targets"] = (
            "scripts/release_rewrite_versions.py rewrites " + ", ".join(targets)
            + ", but " + "; ".join(rewrite)
            + ". The paragraph below this list describes the tripwire that fails a "
            "release on a human commit touching those files, so an undercount tells "
            "a contributor some of them are still theirs to edit."
        )

    # --- 7. the stated quote convention -----------------------------------
    single, double = _package_quote_counts()
    majority = "double" if double > single else "single"
    stated = re.search(r"\b(Single|Double) quotes for strings", conventions)
    if not stated or stated.group(1).lower() != majority:
        total = single + double
        out["quote-style"] = (
            "§ Coding conventions states "
            + (f"'{stated.group(1)} quotes for strings'" if stated else "no quote rule")
            + f", but {max(single, double)} of {total} string literals under `goc/` "
            f"({max(single, double) / total:.0%}) are {majority}-quoted. A style rule "
            "the package does not follow makes a contributor's first diff look wrong "
            "in review."
        )

    return out


# The seven claim groups exactly as CONTRIBUTING.md carried them before
# `contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions`
# (commit 79de4b8d), under their real headings. Feeding this to the same checks
# is what proves each one fires — a derive-from-tree assertion that happens to
# agree with a rewritten file, and would agree with anything, is the failure
# mode this family already hit once
# (`agents-md-miscounts-the-upgrade-no-op-guard-terms-and-mislabels-them-non-write`).
_HISTORICAL_CONTRIBUTING = '''# Contributing to Game of Cards

This page is the short version — the long-form context lives in
[`README.md`](README.md) (methodology), [`AGENTS.md`](AGENTS.md) (deck workflow),
[`CLAUDE.md`](CLAUDE.md) (project conventions), and the header comment of
[`.github/workflows/release.yml`](.github/workflows/release.yml) (release machinery).

## About the project

The Python package is small (4 source files under `goc/`); most of the surface
area is in the `goc/templates/` payload that `goc install` ships into
consuming repos, and in the two plugin payloads (`claude-plugin/`,
`openclaw-plugin/`) that mirror it.

## Setting up your environment

```bash
pre-commit run --all-files                     # sync plugin assets + goc validate
```

The plugin payloads (`claude-plugin/`, `openclaw-plugin/`) are
**byte-for-byte mirrors** of `goc/` and `goc/templates/`. A pre-commit
hook regenerates them on every commit; CI fails the build if they
drift. **Always edit the source under `goc/templates/` — never the
mirrors directly.** Details in [`CLAUDE.md`](CLAUDE.md).

## Coding conventions

Project-specific conventions (template/mirror dogfooding, version
literals, marker-bounded merges, etc.) are documented in
[`CLAUDE.md`](CLAUDE.md). Read it before non-trivial changes — most
"surprises" in the codebase are dogfooding side effects that the file
already explains.

General style:

- Python 3.10+, type hints where they aid readability (not religiously).
- Single quotes for strings; f-strings preferred.
- Edit `goc/templates/...` and re-run `goc upgrade` rather than
  editing `.claude/skills/...` directly (the latter is a consumer
  copy of the former and gets overwritten on upgrade).

## Before submitting a pull request

```bash
pre-commit run --all-files     # formats, mirrors plugin assets, runs goc validate
```

## Release process

1. Rewrites the version literals in `goc/__init__.py` and the four
   plugin manifests.

## For maintainers

- **Plugin asset mirrors** — auto-synced by `scripts/sync_plugin_assets.py`
  via the pre-commit hook; CI fails on drift. Don't edit
  `claude-plugin/` or `openclaw-plugin/goc/` directly.
'''


class ContributorGuideAccuracyTest(unittest.TestCase):
    """CONTRIBUTING.md restates seven groups of tree state, and GitHub puts it in
    front of every outside contributor. Derive each claim from the tree here so
    the on-ramp cannot rot silently the way it did for four months.

    What stays unguarded, deliberately: how the guide *describes* AGENTS.md (a
    prose judgement no derivation reaches) and whether the CLAUDE.md shim is
    explained or merely unlinked. The link-target check below pins the part that
    is mechanical — that every document the guide sends a reader to has
    something on the page.
    """

    def test_contributing_md_agrees_with_the_tree(self) -> None:
        findings = _contributing_findings(CONTRIBUTING.read_text(encoding="utf-8"))
        self.assertEqual(
            {},
            findings,
            msg=(
                "CONTRIBUTING.md has drifted from the tree it describes:\n\n"
                + "\n\n".join(f"[{k}] {v}" for k, v in sorted(findings.items()))
            ),
        )

    def test_every_check_fires_on_the_wording_the_card_found(self) -> None:
        fired = sorted(_contributing_findings(_HISTORICAL_CONTRIBUTING))
        self.assertEqual(
            sorted(_CONTRIBUTING_CHECKS),
            fired,
            msg=(
                "fed the pre-fix CONTRIBUTING.md verbatim, the guard reported "
                f"{fired} instead of every check. A check that stays quiet on the "
                "exact wording it was written for is pinning nothing — re-derive "
                "it rather than deleting this fixture."
            ),
        )


if __name__ == "__main__":
    unittest.main()
