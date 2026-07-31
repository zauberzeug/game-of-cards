#!/usr/bin/env python3
"""Prove `render_leverage_line` suppresses the Andon advisory on an empty queue.

Builds a synthetic deck of three cards — one low-value pullable card and two
high-value cards parked behind a human gate — and renders the leverage line
twice: once with the pullable card present, once with it removed. The advisory
that names the parked high-value card appears in the first render and vanishes
in the second, even though the parked cards (the thing the advisory exists to
surface) are identical in both.

Then repeats the measurement against this repo's live deck.

Exit status:
    1 — defect present (the advisory disappears when nothing is pullable)
    0 — defect fixed
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


def _card(title: str, *, status: str, gate: str, contribution: str) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/nonexistent/{title}"),
        frontmatter={
            "title": title,
            "status": status,
            "human_gate": gate,
            "contribution": contribution,
            "created": "2026-01-01",
            "advances": [],
            "advanced_by": [],
            "tags": [],
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    parked_high = _card(
        "epic-nobody-can-start-until-a-human-picks",
        status="open", gate="session", contribution="high",
    )
    parked_medium = _card(
        "second-card-waiting-on-a-decision",
        status="open", gate="decision", contribution="medium",
    )
    pullable_low = _card(
        "tiny-mechanical-cleanup",
        status="open", gate="none", contribution="low",
    )

    deck = [parked_high, parked_medium, pullable_low]
    values = engine.compute_values(deck)
    by_title = {t.title: t for t in deck}

    print("=== synthetic deck ===")
    for t in deck:
        print(
            f"  {t.title:45} status={t.status:6} gate={t.human_gate:8} "
            f"value={values[t.title][0]:.1f} "
            f"pullable={engine.card_is_ready(t, by_title)}"
        )
    print()

    ready = [t for t in deck if engine.card_is_ready(t, by_title)]
    with_one = engine.render_leverage_line(ready, deck, values=values)
    print("one card pullable  -> leverage line:")
    print(f"  {with_one or '(none)'}")

    # Same deck, same parked cards — only the single low-value pullable card
    # is gone. This is the state a drained queue reaches.
    drained = [parked_high, parked_medium]
    drained_values = engine.compute_values(drained)
    without = engine.render_leverage_line([], drained, values=drained_values)
    print("zero cards pullable -> leverage line:")
    print(f"  {without or '(none)'}")
    print()

    print("=== this repo's live deck ===")
    live = engine.load_all_cards()
    live_values = engine.compute_values(live)
    live_by_title = {t.title: t for t in live}
    live_ready = [t for t in live if engine.card_is_ready(t, live_by_title)]
    live_gated = [
        t for t in live
        if t.status == "open"
        and not engine.card_is_draft(t)
        and t.human_gate in ("decision", "session")
        and not engine.waiting_impedes(t)
    ]
    top = engine.sort_default(live_gated, values=live_values, by_title=live_by_title)
    print(f"  cards in deck            : {len(live)}")
    print(f"  pullable (goc --ready)   : {len(live_ready)}")
    print(f"  open cards behind a gate : {len(live_gated)}")
    if top:
        print(
            f"  highest gated card       : {top[0].title} "
            f"(value {live_values[top[0].title][0]:.1f}, gate {top[0].human_gate})"
        )
    live_line = engine.render_leverage_line(live_ready, live, values=live_values)
    print(f"  leverage line            : {live_line or '(none)'}")
    print()

    defect = bool(with_one) and not without
    if defect:
        print(
            "[FAIL] The advisory names the parked high-value card while one low-value\n"
            "       card is still pullable, and disappears entirely once the queue\n"
            "       drains — the parked cards are unchanged. The signal is present at\n"
            "       one ready card and absent at zero."
        )
        return 1
    print("[OK] The advisory survives a drained queue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
