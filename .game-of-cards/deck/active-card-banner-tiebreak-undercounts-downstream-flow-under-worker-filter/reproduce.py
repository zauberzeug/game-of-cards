#!/usr/bin/env python3
"""Reproduce: the active-card banner's tiebreak undercounts downstream flow
under a --worker filter.

`render_active_notice` builds its `sort_default` tiebreak lookup from the
card list it is handed. `_cmd_default` passes a worker-scoped SUBSET under
`--worker`, so live downstream cards owned by other workers are absent from
that lookup and count as zero unblocked flow. Two equal-value active cards
then fall through to the `created` tiebreak (oldest-first) instead of
ranking the higher-live-flow card first.

Exits 0 when the banner ranks the higher-live-flow card first (fixed);
exits 1 while the bug is present.
"""
import sys
from pathlib import Path

from goc import engine
from goc.engine import Card, compute_values, render_active_notice


def mk(title, status, contrib, advances, worker, created):
    fm = {
        "title": title, "status": status, "contribution": contrib,
        "advances": advances, "advanced_by": [], "human_gate": "none",
        "created": created, "worker": {"who": worker},
    }
    return Card(title=title, path=Path("."), frontmatter=fm, body="",
                dod_open=0, dod_done=0)


def main() -> int:
    cards = [
        # alice's two active cards tie at value; a1 unblocks two live
        # downstream cards, a2 unblocks one and is older.
        mk("a1-active-two-live", "active", "medium",
           ["d1-open", "d2-open"], "alice", "2026-06-02T00:00:00Z"),
        mk("a2-active-one-live", "active", "medium",
           ["d1-open"], "alice", "2026-06-01T00:00:00Z"),
        # downstream live cards owned by a DIFFERENT worker, so a
        # --worker=alice scope drops them from the banner's lookup.
        mk("d1-open", "open", "medium", [], "bob", "2026-06-01T00:00:00Z"),
        mk("d2-open", "open", "medium", [], "bob", "2026-06-01T00:00:00Z"),
    ]
    full_values = compute_values(cards)
    full_by_title = {t.title: t for t in cards}

    # Simulate `goc --worker alice`: _cmd_default scopes notice_cards to the
    # worker's cards before handing them to render_active_notice.
    notice_cards = [
        t for t in cards
        if "alice" in engine._worker_who(t.frontmatter.get("worker")).lower()
    ]

    # The fix gives render_active_notice a by_title parameter. Probe whether
    # threading the full-deck lookup is honored; fall back to the current
    # signature so this script runs against both pre- and post-fix engines.
    try:
        banner = render_active_notice(
            notice_cards, values=full_values, by_title=full_by_title
        )
    except TypeError:
        banner = render_active_notice(notice_cards, values=full_values)

    print("values:", {k: round(v[0], 1) for k, v in full_values.items()})
    print("banner:", banner)

    a1_pos = banner.find("a1-active-two-live")
    a2_pos = banner.find("a2-active-one-live")
    assert a1_pos != -1 and a2_pos != -1, "both active cards must appear"

    if a1_pos < a2_pos:
        print("PASS: higher-live-flow card (a1, 2 downstream) ranked first")
        return 0
    print("FAIL: a2 (1 downstream) ranked ahead of a1 (2) — tiebreak "
          "undercounts downstream flow hidden by the --worker subset")
    return 1


if __name__ == "__main__":
    sys.exit(main())
