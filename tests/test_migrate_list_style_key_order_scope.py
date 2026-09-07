"""`goc migrate-list-style` must not advertise key-order normalisation — regression
guard for
`migrate-list-style-help-promises-key-order-normalisation-the-emitter-never-does`.

The verb's subparser help and docstring listed "key order" among what a
canonical re-emit normalises. `emit_frontmatter` walks `fm.items()`, i.e. the
mapping `parse_frontmatter` filled top-down, so the authored file's key order is
carried straight through — a card whose only drift is a swapped key pair
re-emits byte-identically and is correctly reported as already canonical. The
one listed part the per-card changed-part report could never name was the one
part the emitter does not own.

Both halves are pinned so the pair cannot drift apart again: the behaviour (key
order preserved) and the strings that describe it (no undenied key-order claim).
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

# Canonical in every respect the emitter owns, except that `status` precedes
# `summary` — the reverse of the order `_cmd_new` writes.
KEY_ORDER_DRIFT = """---
title: card-alpha
status: open
summary: canonical everywhere except the key order
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

# Wording that puts key order OUTSIDE the normalised set. A sentence naming key
# order clears only when it carries one of these.
DENIALS = ("not", "carried over", "carried straight through")


def _promises_key_order(text: str) -> bool:
    """True when `text` lists key order among what a canonical re-emit normalises.

    Sentence-scoped, not substring-scoped: the corrected docstring still names
    key order — to say it is preserved — so only an *undenied* mention counts as
    a promise. Mirrors `_promises_key_order` in the card's `reproduce.py`.
    """
    flat = " ".join((text or "").split())
    for sentence in flat.replace("—", ".").split("."):
        low = sentence.lower()
        if "key order" in low and not any(d in low for d in DENIALS):
            return True
    return False


def _subparser_help() -> str:
    parser = engine._build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if choices and "migrate-list-style" in choices:
            for sub in action._choices_actions:
                if sub.dest == "migrate-list-style":
                    return sub.help or ""
    raise AssertionError("migrate-list-style subparser not found")


class _Args:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run


class MigrateListStyleKeyOrderScopeTest(unittest.TestCase):
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

    # ---- the behaviour: key order is carried over, never canonicalised ----

    def test_emit_preserves_authored_key_order(self) -> None:
        fm, body = engine.parse_frontmatter(KEY_ORDER_DRIFT)
        self.assertEqual(
            ["title", "status", "summary"], list(fm)[:3],
            "the parser must hand the emitter the authored order",
        )
        self.assertEqual(
            KEY_ORDER_DRIFT, engine.emit_frontmatter(fm, body=body),
            "emit_frontmatter must round-trip a key-reordered card byte-identically",
        )

    def test_key_order_only_drift_is_reported_as_canonical(self) -> None:
        self._deck({"card-alpha": KEY_ORDER_DRIFT})
        out = self._run()
        self.assertIn("nothing to do", out)
        self.assertNotIn("card-alpha", out)

    def test_key_order_only_drift_survives_the_apply_path(self) -> None:
        deck = self._deck({"card-alpha": KEY_ORDER_DRIFT})
        self._run(dry_run=False)
        self.assertEqual(
            KEY_ORDER_DRIFT, (deck / "card-alpha" / "README.md").read_text(),
            "a real run must leave a key-reordered card untouched",
        )

    # ---- the strings: neither may promise what the emitter does not do ----

    def test_subparser_help_does_not_promise_key_order_normalisation(self) -> None:
        self.assertFalse(
            _promises_key_order(_subparser_help()),
            "goc migrate-list-style --help lists key order among what it normalises",
        )

    def test_docstring_does_not_promise_key_order_normalisation(self) -> None:
        self.assertFalse(
            _promises_key_order(engine._cmd_migrate_list_style.__doc__ or ""),
            "_cmd_migrate_list_style's docstring lists key order among what it normalises",
        )

    def test_no_op_line_and_help_enumerate_the_same_scope(self) -> None:
        """The two scope strings disagreed once — the no-op line omitted key
        order while the help promised it. Pin that they agree."""
        self._deck({"card-alpha": KEY_ORDER_DRIFT})
        self.assertFalse(_promises_key_order(self._run()))

    # ---- the guard itself must be able to fail ----

    def test_promise_detector_catches_the_original_wording(self) -> None:
        self.assertTrue(
            _promises_key_order(
                "normalises everything emit_frontmatter owns — scalar quoting, "
                "block scalars, key order, the blank line before the body."
            )
        )
        self.assertFalse(
            _promises_key_order("Key order is carried over, not canonicalised.")
        )


if __name__ == "__main__":
    unittest.main()
