"""`goc migrate-list-style` must not report a canonicalization as list-style drift —
regression guard for
`migrate-list-style-reports-and-rewrites-far-more-than-list-style`.

The verb picks cards with `emit_frontmatter(fm, body=body) != original`, i.e.
whole-card canonical equality, while its help, docstring and no-op line used to
name only the four relation-edge list fields as the scope. On the dogfood deck
that reported 10 cards, none of which had relation-list drift: 8 were bare
`summary` lines the emitter now quotes and 2 were a missing blank line before
the body. The card list was bare names, so the reader could not tell the two
apart.

Both directions are pinned here so the fix cannot regress to either
"report nothing" (which would delete the only bulk re-emit path) or
"report everything unlabelled".
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goc import engine  # noqa: E402

# Canonical relation lists; a bare `summary` carrying a `: ` the emitter quotes.
QUOTING_DRIFT = """---
title: card-alpha
summary: the board hard-caps a label: eight characters is a vestige
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# card-alpha
"""

# Canonical everywhere the emitter cares about except the blank line before
# the body.
SPACING_DRIFT = """---
title: card-beta
summary: canonical everywhere except the blank line before the body
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---
# card-beta
"""

# The migration's own target: an inline-flow relation-edge list.
LIST_DRIFT = """---
title: card-gamma
summary: "an inline-flow advances list, which is real block-style drift"
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: [card-alpha]
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# card-gamma
"""

CANONICAL = """---
title: card-delta
summary: "already exactly what the emitter would write"
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# card-delta
"""


class _Args:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run


class MigrateListStyleReportScopeTest(unittest.TestCase):
    """The report names which part of each card a re-emit would rewrite."""

    def _deck(self, cards: dict) -> Path:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        deck = Path(tmp.name) / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for name, text in cards.items():
            card = deck / name
            card.mkdir()
            (card / "README.md").write_text(text)
        prev = engine.DECK_DIR
        engine.DECK_DIR = deck
        self.addCleanup(setattr, engine, "DECK_DIR", prev)
        return deck

    @staticmethod
    def _run(dry_run: bool = True) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            engine._cmd_migrate_list_style(_Args(dry_run=dry_run))
        return buf.getvalue()

    def _reason(self, out: str, card: str) -> str:
        """The reason the report gives for picking `card`."""
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.startswith(card):
                self.assertIn(
                    "—", line,
                    f"{card} was reported with no reason: {line!r}",
                )
                return line.split("—", 1)[1].strip()
        self.fail(f"{card} was not reported at all:\n{out}")

    # ---- drift outside the relation-edge lists must be named as such ----

    def test_summary_requote_is_reported_as_summary(self) -> None:
        self._deck({"card-alpha": QUOTING_DRIFT})
        reason = self._reason(self._run(), "card-alpha")
        self.assertEqual("summary", reason)

    def test_body_spacing_drift_is_reported_as_spacing(self) -> None:
        self._deck({"card-beta": SPACING_DRIFT})
        reason = self._reason(self._run(), "card-beta")
        self.assertEqual("body spacing", reason)

    def test_non_relation_drift_is_never_blamed_on_a_relation_field(self) -> None:
        """The defect's core: neither card has relation-list drift."""
        self._deck({"card-alpha": QUOTING_DRIFT, "card-beta": SPACING_DRIFT})
        out = self._run()
        for card in ("card-alpha", "card-beta"):
            reason = self._reason(out, card)
            for field in engine._BLOCK_LIST_FIELDS:
                self.assertNotIn(field, reason)

    # ---- the other direction: real list-style drift is still migrated ----

    def test_relation_list_drift_is_still_reported_and_named(self) -> None:
        self._deck({"card-gamma": LIST_DRIFT})
        reason = self._reason(self._run(), "card-gamma")
        self.assertIn("advances", reason)

    def test_apply_path_rewrites_the_inline_flow_list(self) -> None:
        deck = self._deck({"card-gamma": LIST_DRIFT})
        self._run(dry_run=False)
        text = (deck / "card-gamma" / "README.md").read_text()
        self.assertIn("advances:\n  - card-alpha\n", text)

    def test_dry_run_writes_nothing(self) -> None:
        deck = self._deck({"card-gamma": LIST_DRIFT})
        self._run(dry_run=True)
        self.assertEqual(LIST_DRIFT, (deck / "card-gamma" / "README.md").read_text())

    # ---- the no-op line must claim only what it verified ----

    def test_no_op_line_claims_canonical_form_not_block_style_only(self) -> None:
        # Canonical by construction: hand-written text cannot be trusted to be
        # a fixed point of the emitter.
        fm, body = engine.parse_frontmatter(CANONICAL)
        self._deck({"card-delta": engine.emit_frontmatter(fm, body=body)})
        out = self._run()
        self.assertIn("canonical", out.lower())
        self.assertNotIn("Would rewrite", out)
        self.assertNotIn(
            "All cards already use block-style", out,
            "the no-op line under-claims: the comparison verified full "
            "canonical equality, not just relation-list rendering",
        )
        # The two contracts coexist: `engine-docs-name-advances-advanced-by-as-
        # scope-but-cover-all-four-relation-fields` requires the line to name
        # all four relation fields (pinned in `test_repair_edges.py`), and this
        # card requires it to claim canonical form rather than block style only.
        for field in engine._BLOCK_LIST_FIELDS:
            self.assertIn(field, out)

    # ---- the CLI's own description of its scope ----

    def test_help_and_docstring_describe_the_real_predicate(self) -> None:
        parser = engine._build_parser()
        subcommands = next(
            action for action in parser._actions
            if getattr(action, "choices", None) and "migrate-list-style" in action.choices
        )
        listed = next(
            choice.help for choice in subcommands._choices_actions
            if choice.dest == "migrate-list-style"
        )
        self.assertIn("canonical", listed.lower())
        self.assertNotIn(
            "to block-style", listed,
            "the subcommand help must not present block-style as the scope",
        )
        self.assertIn("canonical", engine._cmd_migrate_list_style.__doc__.lower())


if __name__ == "__main__":
    unittest.main()
