#!/usr/bin/env python3
"""The queue table hides the impediment overlay at every verbosity.

Builds a two-card deck — one plainly pullable, one carrying an active
`waiting_on: external` + future `waiting_until` overlay — and renders it
through every human-facing surface. The board marks the impeded card `⏳`
and `--json` carries the overlay fields, but `render_table` prints nothing
that distinguishes the two cards, including under `goc --waiting`.

Pass/fail is scoped to the **detail-line levels** (`-v` / `-vv`), where
every other per-card field already lives (`summary`, `awaiting`, `worker`).
The terse verbose-0 table prints one row per card and carries no detail
line for any field, so its rows are reported for context but are not part
of the contract — see the README's "Scope boundary".

Exits 0 once the detail-line views name the impediment; exits 1 while the
defect stands.
"""

import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

CARD = """---
title: {title}
summary: "{summary}"
status: open
stage: null
contribution: high
created: "2026-07-01T00:00:00Z"
closed_at: null
human_gate: none
waiting_on: {waiting_on}
waiting_until: {waiting_until}
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [ ] TDD: a criterion
---

# {title}

Body.
"""

REASON = "external"
UNTIL = "2099-01-01"


def _write_deck(root: Path) -> None:
    deck = root / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    for title, summary, reason, until in (
        ("plain-pullable-card", "Ready to pull", "null", "null"),
        ("impeded-card", "Blocked on upstream", REASON, f'"{UNTIL}"'),
    ):
        (deck / title).mkdir()
        (deck / title / "README.md").write_text(
            CARD.format(title=title, summary=summary, waiting_on=reason, waiting_until=until)
        )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_deck(root)

        import goc.engine as engine

        engine.REPO_ROOT = root
        engine.DECK_ROOT = root
        engine.DECK_DIR = root / ".game-of-cards" / "deck"

        cards = engine.load_all_cards()
        by_title = {c.title: c for c in cards}
        impeded = by_title["impeded-card"]

        print("=== waiting_impedes (the predicate --ready / --waiting / the board use) ===")
        for c in sorted(cards, key=lambda c: c.title):
            print(f"  {c.title:<22} impedes={engine.waiting_impedes(c)}")

        print("\n=== render_board OPEN column ===")
        for line in engine.render_board(cards, max_rows=20, no_color=True).splitlines():
            print(f"  {line.split('|')[0].rstrip()}")

        print("\n=== render_json ===")
        import json

        payload = {
            c["title"]: (c.get("waiting_on"), c.get("waiting_until"))
            for c in json.loads(engine.render_json(cards, by_title=by_title))
        }
        for title, pair in sorted(payload.items()):
            print(f"  {title:<22} waiting_on={pair[0]!r} waiting_until={pair[1]!r}")

        waiting_set = [
            c
            for c in cards
            if c.status not in engine.TERMINAL_STATUSES
            and not engine.card_is_draft(c)
            and engine.waiting_impedes(c)
        ]

        print("\n=== render_table ===")
        failures = []
        views = (
            ("goc", 0, cards, False),
            ("goc -v", 1, cards, True),
            ("goc -vv", 2, cards, True),
            ("goc --waiting", 0, waiting_set, False),
            ("goc -v --waiting", 1, waiting_set, True),
            ("goc -vv --waiting", 2, waiting_set, True),
        )
        for label, verbose, subset, in_contract in views:
            out = engine.render_table(subset, verbose=verbose, no_color=True, by_title=by_title)
            shown = REASON in out or UNTIL in out
            scope = "" if in_contract else "   (terse view — context only, not in contract)"
            print(f"  --- {label} --- overlay named: {shown}{scope}")
            for line in out.splitlines():
                print(f"      {line}")
            if in_contract and not shown:
                failures.append(label)

        print("\n=== verdict ===")
        if failures:
            print(
                "DEFECT: the impediment overlay is invisible in "
                f"{len(failures)} detail-line view(s): {', '.join(failures)}"
            )
            print(
                "  the board marks it ⏳ and --json carries the fields, "
                "but no table view names the reason or the date"
            )
            return 1
        print("OK: every detail-line table view names the impediment overlay")
        return 0


if __name__ == "__main__":
    sys.exit(main())
