"""The hidden-draft clause counts drafts the query would reject anyway.

`_cmd_default` narrows the card list in three stages: `filter_cards`, then the
`--closed-since` window, then `--waiting`'s `live_impeded` gate. The zero-match
recount that produces `hidden_drafts` replays only the first stage, so it
answers "what would `filter_cards` have matched with drafts included?" instead
of "what would this query have matched?".

Two decks make that visible. Each holds exactly one draft that the *reported*
filter excludes on its own merits:

  A. `--waiting --status open` over a draft with no `waiting_on` and no
     `waiting_until` at all.
  B. `--closed-since 1h --status done` over a draft closed months ago.

In both cases clearing `draft: true` reveals nothing — the card still fails the
named filter — yet the line tells the reader `goc publish <title>` will surface
it. A third deck (C) is the control: a draft that the query really is hiding,
where the clause is correct and must survive the fix.

Exits 1 while the defect stands, 0 once the count reflects the whole query.
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


def _card(deck: Path, title: str, *, extra: str = "", status: str = "open",
          closed_at: str = "null", draft: bool = True) -> None:
    """Write an *authored* card (real DoD, real body) that is optionally a draft.

    Authored on purpose: `card_is_draft` also fires on a surviving placeholder
    scaffold, and the point here is the explicit `draft: true` flag alone.
    """
    card = deck / title
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f'summary: "Authored card used as a {"draft" if draft else "published"} fixture."\n'
        f"status: {status}\n"
        "stage: null\n"
        "contribution: high\n"
        'created: "2026-01-01T00:00:00Z"\n'
        f"closed_at: {closed_at}\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        + ("draft: true\n" if draft else "")
        + extra
        + "definition_of_done: |\n"
        "  - [ ] MECHANICAL: a real criterion, so this is authored, not a scaffold.\n"
        "---\n"
        f"\n# {title}\n\nA real body, so `is_placeholder_scaffold` does not fire.\n"
    )
    (card / "log.md").write_text("")


def _queue_output(deck: Path, **argkw) -> str:
    engine.DECK_DIR = deck
    engine.DECK_ROOT = deck.parent.parent
    buf = io.StringIO()
    with redirect_stdout(buf):
        engine._cmd_default(_Args(**argkw))
    return buf.getvalue().strip()


CLAUSE = "unauthored draft scaffold"


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        # A. --waiting over a draft carrying no impediment overlay whatsoever.
        deck_a = root / "a" / ".game-of-cards" / "deck"
        deck_a.mkdir(parents=True)
        _card(deck_a, "no-overlay-draft")

        # B. --closed-since over a draft closed far outside the window.
        deck_b = root / "b" / ".game-of-cards" / "deck"
        deck_b.mkdir(parents=True)
        _card(deck_b, "long-closed-draft", status="done",
              closed_at='"2026-01-02T00:00:00Z"')

        # C. Control: --waiting over a draft that IS actively impeded, so the
        #     draft flag really is the only thing hiding it.
        deck_c = root / "c" / ".game-of-cards" / "deck"
        deck_c.mkdir(parents=True)
        _card(deck_c, "impeded-draft", extra="waiting_on: external\n")

        out_a = _queue_output(deck_a, waiting=True, status_flag="open")
        out_b = _queue_output(deck_b, closed_since="1h", status_flag="done")
        out_c = _queue_output(deck_c, waiting=True, status_flag="open")

        print("A. goc --waiting --status open   (draft has NO waiting_on/waiting_until)")
        print(f"   {out_a}")
        print(f"   claims a draft is hidden : {CLAUSE in out_a}")
        print("   publishing it would show it: False  (live_impeded needs an overlay)")
        print()
        print("B. goc --closed-since 1h --status done   (draft closed 2026-01-02)")
        print(f"   {out_b}")
        print(f"   claims a draft is hidden : {CLAUSE in out_b}")
        print("   publishing it would show it: False  (closed far outside the window)")
        print()
        print("C. control — goc --waiting --status open, draft IS impeded (waiting_on: external)")
        print(f"   {out_c}")
        print(f"   claims a draft is hidden : {CLAUSE in out_c}")
        print("   publishing it would show it: True   (clause is correct here)")
        print()

        false_positives = [
            name for name, out in (("A", out_a), ("B", out_b)) if CLAUSE in out
        ]
        control_ok = CLAUSE in out_c

        if false_positives:
            print(
                f"FAIL: deck(s) {', '.join(false_positives)} report hidden drafts that "
                "publishing would not surface — the recount replays filter_cards only, "
                "skipping the --closed-since and --waiting conjuncts applied after it."
            )
            return 1
        if not control_ok:
            print(
                "FAIL: the control deck lost its clause — the count must still fire "
                "when the draft flag really is what hides the card."
            )
            return 1
        print(
            "PASS: the count reflects the whole query — no clause on A/B, clause kept on C."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
