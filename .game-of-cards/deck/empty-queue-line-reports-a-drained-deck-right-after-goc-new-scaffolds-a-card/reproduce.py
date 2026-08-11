"""The zero-match queue line cannot tell a drained deck from a deck of drafts.

Builds two decks that differ in the only way that matters — one genuinely
empty, one holding two `goc new` scaffolds — and renders the table path for
each. `filter_cards` drops drafts from every status filter except `all`, but
`render_empty_query_line` enumerates only the user-supplied filters, so both
decks print the same sentence.

Exits 1 while the defect stands (the two messages are byte-identical), 0 once
the message names the draft exclusion on the second deck.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


class _Args:
    """Stand-in for the argparse namespace `_cmd_default` reads."""

    def __init__(self, **kw):
        defaults = dict(
            done_flag=False, status_flag=None, closed_since=None, waiting=False,
            board=False, as_json=False, slim=False, since=None, stage_flag=None,
            contribution=None, human_gate=None, tags=[], advances=None,
            advanced_by=None, worker=None, ready=False, verbose=0,
            no_color=True, max_rows=20,
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


def _scaffold(deck: Path, title: str) -> None:
    """Write exactly what `goc new` writes: an unauthored draft scaffold."""
    card = deck / title
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        'summary: "Scaffolded, not yet authored."\n'
        "status: open\n"
        "stage: null\n"
        "contribution: medium\n"
        'created: "2026-08-11T00:00:00Z"\n'
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] (replace with real criteria)\n"
        "draft: true\n"
        "---\n"
        f"\n# {title}\n\n(write the design doc here)\n"
    )
    (card / "log.md").write_text("")


def _queue_output(deck: Path) -> str:
    engine.DECK_DIR = deck
    engine.DECK_ROOT = deck.parent.parent
    buf = io.StringIO()
    with redirect_stdout(buf):
        engine._cmd_default(_Args())
    return buf.getvalue().strip()


def main() -> int:
    with TemporaryDirectory() as tmp:
        empty_deck = Path(tmp) / "empty" / ".game-of-cards" / "deck"
        empty_deck.mkdir(parents=True)

        draft_deck = Path(tmp) / "drafts" / ".game-of-cards" / "deck"
        draft_deck.mkdir(parents=True)
        _scaffold(draft_deck, "alpha-card")
        _scaffold(draft_deck, "beta-card")

        drained = _queue_output(empty_deck)
        with_drafts = _queue_output(draft_deck)

        # The same two cards ARE visible one flag over, so the deck is not empty.
        engine.DECK_DIR = draft_deck
        engine.DECK_ROOT = draft_deck.parent.parent
        all_cards = engine.load_all_cards()

        print("deck A — no card directories at all")
        print(f"  goc  -> {drained!r}")
        print()
        print("deck B — two `goc new` scaffolds, both `status: open`")
        print(f"  cards on disk       : {[c.title for c in all_cards]}")
        print(f"  their status values : {sorted({c.title: c.status for c in all_cards}.items())}")
        print(f"  card_is_draft       : {[engine.card_is_draft(c) for c in all_cards]}")
        print(f"  goc  -> {with_drafts!r}")
        print()
        print(f"messages identical: {drained == with_drafts}")

        if drained == with_drafts:
            print(
                "\nFAIL: a deck with two open cards prints the drained-deck sentence "
                "verbatim; the draft conjunct that emptied the result is never named."
            )
            return 1
        print("\nPASS: the draft exclusion is named, so the two states are distinguishable.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
