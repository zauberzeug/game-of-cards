

## 2026-07-13 — Deck hygiene pass

Wired the meta-fix family roster surfaced by the orphaned-dependency sub-check (zero edges despite the body's five-card instance table): `advanced_by +=` the five closed per-flag guard cards (invalid-status-filter, invalid-tag-filter, invalid-since-date, done-shortcut-overrides-status-filter, since-filter-without-done).

## 2026-08-04 — the output half is opt-in per flag too (post-close generalization check)

Follow-up to the eddb9941 entry, from closing
`empty-result-line-reports-a-drained-ready-queue-that-still-has-cards`
(already wired as `advanced_by` at filing time, so this is a naming pass,
not a new edge).

That closure found the output half of this contract reproducing this
card's own thesis inside itself: `render_empty_query_line` names filters
from a hand-maintained list parallel to `filter_cards`' parameter list,
so a flag appears in a zero-match message only if someone added a branch
for it. It had already drifted — `--ready` was coded as replacing the
status clause rather than adding to it.

Two constraints recorded on the body as a new
"### The output half is opt-in per flag too" subsection, beside the
instance table where a decision-maker reads it:

1. Option A's contract table should be the single source for BOTH halves
   (validator + zero-match naming), or the next flag gets a validator and
   still goes unnamed on empty output. B and C leave the output
   enumeration hand-maintained with no fail-closed property.
2. The output half can be *wrong*, not just absent. Every earlier
   instance here fails silently at exit 0; this one asserted a false
   claim about deck state (a drained ready queue that still had cards).
   So "legible" is not merely a weaker tier than "impossible" — an
   unguarded output half has a distinct failure mode that is worse than
   silence.

No new card filed: the root exists, the instance was already connected,
and a second umbrella would be the redundant-root anti-pattern.

## 2026-08-11T05:05:00Z — Third output-half instance connected

[empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/)
closed today; its `advances` edge was wired at filing time. Amended this
card's body with the instance because the edge alone claimed more than the
body could carry: every row in the instance table named a *flag*, and this
instance has none.

What it adds beyond a row: `render_empty_query_line`'s enumeration is
parallel to `filter_cards`' parameter list, so it can only describe conjuncts
that have a parameter. The draft exclusion is applied unconditionally inside
`filter_cards` (and again inside `card_is_ready`), with no flag to mirror —
the dual of the `--worker` case, where a flag exists but no input-side
contract can cover it. Recorded as third consequence for the decision: a
per-flag contract table (option A) is structurally blind to this class, so
the output-half enumeration should be driven by the predicate actually
applied rather than by the flag list.

Gate and DoD untouched — this is evidence for the open decision, not a
resolution of it.

No new card filed: the root exists and the instance is connected to it;
a second umbrella would be the redundant-root anti-pattern.
