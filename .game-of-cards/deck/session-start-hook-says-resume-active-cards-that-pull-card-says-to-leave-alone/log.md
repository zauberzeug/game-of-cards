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
