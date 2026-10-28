# Log

## 2026-06-24 — closed (done)

Surfaced by an audit-deck hunt during an empty-queue pull-card run.

`sort_default`'s near-term-flow tiebreak (`live_direct`, engine.py:2637)
incremented its counter once per element of `advances`, so a duplicated
edge (`advances: [B, B]`) scored 2 — tying a card that unblocks two
genuinely distinct downstream cards. Validator never rejects duplicate
relationship-list entries (engine.py:1573-1582), so the offending deck
state passes `goc validate` cleanly; reachable via hand-authored
frontmatter or repeated `goc advance`.

Fix: count distinct workable target titles via a `set` instead of a raw
per-element increment. The docstring already described the intended
"distinct downstream cards" semantics, so this is a drift correction,
not a behavior change. Value axis was unaffected (compute_values takes a
max over descendants); only the tiebreak ordering was wrong.

Evidence: `reproduce.py` (a-dup vs a-two, equal value) — exits 1 before,
0 after. Regression test added to
`tests/test_sort_default_full_deck_tiebreak.py`
(`test_duplicate_advances_edge_counts_once`). Plugin engine mirrors
re-synced. Full suite (563 tests) green; `goc validate` clean.

## 2026-10-28 — Forward pointer: repeated `goc advance` never wrote a duplicate

The README's reachability list and the closure entry above name repeated
`goc advance` as a second way to reach a duplicated `advances` entry. It was
not one: `_add_to_list_field` returns early when the title is already listed,
so a re-run rewrote both cards byte-identical. Since
`goc-advance-claims-success-when-adding-an-already-existing-edge` closed on
2026-10-28, a re-run exits 2 with nothing written. Hand-authored frontmatter
remains the reachability path; the tiebreak fix here is unaffected.
