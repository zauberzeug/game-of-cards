from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


class TableWaitingOverlayLineTest(unittest.TestCase):
    """The verbose queue table must name a card's live impediment overlay.

    `card_is_ready` hides an impeded card from `goc --ready`, the board
    marks it `⏳`, and `--json` carries `waiting_on` / `waiting_until` — but
    `render_table` used to print nothing, so an impeded card read exactly
    like a pullable one and `goc --waiting` could not say what any listed
    card was waiting on. See
    `deck/queue-table-omits-the-waiting-on-and-waiting-until-impediment-overlay/`.
    """

    def card(
        self,
        title: str,
        *,
        status: str = "open",
        waiting_on: str | None = None,
        waiting_until: str | None = None,
        draft: bool = False,
    ) -> engine.Card:
        fm: dict = {
            "title": title,
            "summary": title,
            "status": status,
            "stage": None,
            "contribution": "low",
            "created": "2026-05-04",
            "closed_at": "2026-06-01" if status in engine.TERMINAL_STATUSES else None,
            "human_gate": "none",
            "advances": [],
            "advanced_by": [],
            "tags": [],
            "definition_of_done": "- [ ] test card\n",
        }
        if waiting_on is not None:
            fm["waiting_on"] = waiting_on
        if waiting_until is not None:
            fm["waiting_until"] = waiting_until
        if draft:
            fm["draft"] = True
        return engine.Card(
            title=title,
            path=Path("/nonexistent") / title,
            frontmatter=fm,
            body=f"\n# {title}\n\nBody.\n",
            dod_open=1,
            dod_done=0,
        )

    def detail_lines(self, *cards: engine.Card, verbose: int = 1) -> list[str]:
        out = engine.render_table(
            list(cards),
            verbose=verbose,
            no_color=True,
            by_title={c.title: c for c in cards},
        )
        return [line.strip() for line in out.splitlines() if line.startswith("    ")]

    def overlay_lines(self, *cards: engine.Card, verbose: int = 1) -> list[str]:
        return [
            line
            for line in self.detail_lines(*cards, verbose=verbose)
            if line.startswith(("waiting_on:", "waiting_until:"))
        ]

    # --- the three renderable shapes -------------------------------------

    def test_reason_and_until(self) -> None:
        card = self.card("blocked", waiting_on="external", waiting_until="2099-01-01")
        self.assertEqual(
            ["waiting_on: external (until 2099-01-01)"], self.overlay_lines(card)
        )

    def test_reason_only(self) -> None:
        card = self.card("blocked", waiting_on="external")
        self.assertEqual(["waiting_on: external"], self.overlay_lines(card))

    def test_bare_until_deferral(self) -> None:
        """A `waiting_until` with no reason is a deferral — impeding per
        `waiting_impedes`, so the table must name the date."""
        card = self.card("deferred", waiting_until="2099-01-01")
        self.assertEqual(["waiting_until: 2099-01-01"], self.overlay_lines(card))

    def test_datetime_until_is_not_flattened_to_a_date(self) -> None:
        card = self.card(
            "blocked", waiting_on="external", waiting_until="2099-01-01T13:45:00Z"
        )
        self.assertEqual(
            ["waiting_on: external (until 2099-01-01T13:45:00Z)"],
            self.overlay_lines(card),
        )

    def test_malformed_until_is_echoed_verbatim_not_truncated(self) -> None:
        """`waiting_impedes` treats an unparseable `waiting_until` as
        impeding. Rendering it through `_date_part`'s 10-char slice would
        present `2099-01-01xx` as the clean date `2099-01-01`; the line
        must echo the stored value and say it is malformed."""
        card = self.card("blocked", waiting_on="external", waiting_until="2099-01-01xx")
        self.assertEqual(
            ["waiting_on: external (until 2099-01-01xx — malformed)"],
            self.overlay_lines(card),
        )

    # --- when no line may be emitted -------------------------------------

    def test_no_line_for_a_card_without_an_overlay(self) -> None:
        self.assertEqual([], self.overlay_lines(self.card("plain")))

    def test_no_line_for_an_elapsed_wait(self) -> None:
        """An elapsed `waiting_until` resurfaces the card with no manual
        action, so it is no longer an impediment to report."""
        card = self.card("resurfaced", waiting_on="external", waiting_until="2020-01-01")
        self.assertEqual([], self.overlay_lines(card))

    def test_no_line_at_verbosity_zero(self) -> None:
        """The terse table is one row per card and carries no detail line
        for any field; the overlay follows `summary` / `awaiting` /
        `worker` and appears from `-v` upward."""
        card = self.card("blocked", waiting_on="external")
        self.assertEqual([], self.overlay_lines(card, verbose=0))

    def test_line_present_at_verbosity_two(self) -> None:
        card = self.card("blocked", waiting_on="external")
        self.assertEqual(["waiting_on: external"], self.overlay_lines(card, verbose=2))

    # --- liveness gate matches the `--waiting` filter ---------------------

    def test_no_line_for_terminal_card_with_stale_overlay(self) -> None:
        """Closing never clears the overlay, so every terminal card keeps a
        stale one. It is not an actionable wait and must stay silent —
        matching the `--waiting` filter and the board's ⏳."""
        for status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=status):
                card = self.card("closed-card", status=status, waiting_on="external")
                self.assertEqual([], self.overlay_lines(card))

    def test_no_line_for_draft_scaffold_with_overlay(self) -> None:
        card = self.card("scaffold", waiting_on="external", draft=True)
        self.assertEqual([], self.overlay_lines(card))

    def test_gate_agrees_with_the_waiting_filter_predicate(self) -> None:
        """The table line and `goc --waiting` must select the same cards.
        Both route through `live_impeded`; this pins the coupling across
        the full {status} x {draft} x {overlay} grid so a future edit to
        one cannot silently diverge from the other.
        """
        overlays = (
            ("clear", None, None),
            ("reason", "external", None),
            ("bare-until", None, "2099-01-01"),
            ("elapsed", "external", "2020-01-01"),
            ("malformed", None, "2099-01-01xx"),
        )
        for status in ("open", "active", *sorted(engine.TERMINAL_STATUSES)):
            for draft in (False, True):
                for name, reason, until in overlays:
                    with self.subTest(status=status, draft=draft, overlay=name):
                        card = self.card(
                            f"{status}-{name}",
                            status=status,
                            waiting_on=reason,
                            waiting_until=until,
                            draft=draft,
                        )
                        self.assertEqual(
                            engine.live_impeded(card),
                            bool(self.overlay_lines(card)),
                            "table overlay line and --waiting must agree",
                        )

    # --- ordering ---------------------------------------------------------

    def test_overlay_sorts_above_the_awaiting_advisory(self) -> None:
        """`awaiting:` is the *advisory* dependency axis and says
        "(you may start)". The hard impediment must read first, or the only
        waiting-shaped text on an impeded card contradicts its state."""
        prereq = self.card("prereq")
        blocked = self.card("blocked", waiting_on="external")
        blocked.frontmatter["advanced_by"] = ["prereq"]

        lines = self.detail_lines(blocked, prereq)
        overlay_idx = lines.index("waiting_on: external")
        awaiting_idx = next(i for i, line in enumerate(lines) if line.startswith("awaiting:"))
        self.assertLess(overlay_idx, awaiting_idx)


if __name__ == "__main__":
    unittest.main()
