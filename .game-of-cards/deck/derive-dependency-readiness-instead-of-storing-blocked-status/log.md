## 2026-05-26T05:33:15Z — Closure

- **What changed**: `goc/engine.py` — added `dependency_blocked`, `dependency_blockers`, `card_is_ready` predicates near `TERMINAL_STATUSES`; threaded an optional `by_title` lookup through `filter_cards`, `render_table`, `render_json`, `render_board` so filtered subsets evaluate the derived state against the full deck; added a `--ready` CLI flag; surfaced `blocked by:` lines (`-v` table), a `⛓` marker (board), and `dependency_blocked` / `blocked_by` / `ready` keys (JSON).
- **Verification**: `uv run python .game-of-cards/deck/derive-dependency-readiness-instead-of-storing-blocked-status/reproduce.py` exits 0 — dependent-card is derived-blocked while upstream-prereq is open, self-clears to ready the moment upstream flips to done, no manual status edit on the dependent.
- **Audit**: PASS — no rubric configured; binds to the epic's literature-anchored "derived vs stored" principle (Anderson kanban / CPM forward pass) recorded in the parent card.
- **Project impact**: n/a
- **Tests**: no pytest suite — `uv run goc validate` clean after `python scripts/sync_plugin_assets.py`.
- **Bundled with**: none

## Closure verification (2026-05-26T05:33:28Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

## 2026-05-26T05:40:57Z — Post-close amendment — closure-vs-readiness asymmetry handoff

The decision card
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
resolved (Option E) that `advanced-by-closed` is *correct* — every true
`advanced_by` edge ⇔ the card's value chain includes that upstream ⇔ the
card is not done while the upstream is open. The loose/strict
distinction is real but governs **start ordering, not closure**.

Consequence for this (closed) card: the `dependency_blocked` predicate
landed inheriting the closure reading (True for any non-terminal
`advanced_by`), which over-blocks *starting* on loose edges — exactly
the over-read the original contributor flagged. The README's "Open
consideration" section captures the three resolution options (block on
all; route loose impediments to the `waiting_on` overlay; introduce a
strict/loose signal). A follow-up card files the actual predicate
refactor; this entry just records that the readiness half is
acknowledged as live work, not closed by the parent's decision.
