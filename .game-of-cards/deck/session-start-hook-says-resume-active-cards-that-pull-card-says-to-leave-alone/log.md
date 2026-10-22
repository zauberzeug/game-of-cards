# log — session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone

## 2026-10-09T04:50:42Z — Filed

Surfaced while resuming the orphaned claim on
[engine-comments-claim-unflagged-placeholder-cards-count-as-drafts](../engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/).
At session start the hook said to resume or close that card, while the
`pull-card` body said to treat it as a soft lock unless the user asked to
continue it. The skill's own soft-lock table never listed the card,
because the table was cut at 20 lines. This session followed the hook and
the deck's two earlier precedents, and wrote its reasons in that card's
log. Filed at `human_gate: decision` rather than fixed through: the
options differ in schema, config and ownership, and choosing among them
is a policy call, not a mechanical fix. Deduped against
`skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json`,
which owns the truncation half and not the contradiction, and against the
three closed session-start-hook resumability cards, which fixed the
closed, gated and impeded buckets but not this one.

## 2026-10-09T04:54:45Z — Pattern check: adjacent to the hook-drift roots, not an instance

The two META-FIX roots for the hook,
`session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting`
and `openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`,
catalogue copies of engine predicates that already exist (the wait
overlay, frontmatter scalars) and drift from them. This card has no
engine predicate to drift from: the engine has no notion of who may
resume a claim. So no `advances` edge was added. Option 3 would create
such a predicate and with it a new copy for those roots to guard, so the
Decision section cross-references both roots. No other root covers two
shipped surfaces giving contradictory instructions about the same card.

## 2026-10-17T04:36:00Z — Fourth orphaned claim, resolved by hand a day late

[reproduce-py-recipe-crashes-in-repos-without-a-pyproject-toml](../reproduce-py-recipe-crashes-in-repos-without-a-pyproject-toml/)
was claimed at 2026-10-16T04:56:06Z (530ac5f5). The run that claimed it had
already closed one card and filed two fix-through cards, and the Pull Card
job's `timeout-minutes: 30` killed it seconds after the claim. No work had
landed, and the timeout also skipped the re-trigger step. The next day's
first run got the same two instructions this card describes. The hook said
resume, and `pull-card` said leave it alone. It resumed and closed the card
(b457bd8e) using the same CI-only facts as the three earlier cases: the
same `who`, `origin/main` still at the claim commit, and Pull Card's single
concurrency group.

This repeats the third case's truncation. The orphan was the seventh active
card, and six verbose rows fill the soft-lock block's `head -20`, so
`pull-card`'s table did not show it. Only the hook named it. The README's
count and instance table are updated in place. The new cause is datum for
option 2's staleness window: a timeout orphans a claim when a run spends its
budget on earlier cards and claims a fix-through card late. That is
ordinary pull-card behaviour, not a crash, so orphans will keep arriving at
about this rate until a rule lands.
