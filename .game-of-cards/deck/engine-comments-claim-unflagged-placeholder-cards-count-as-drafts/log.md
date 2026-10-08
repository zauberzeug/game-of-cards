# log — engine-comments-claim-unflagged-placeholder-cards-count-as-drafts

## 2026-10-08T05:40:20Z — Filed

Surfaced while closing
[queue-table-renders-draft-cards-identically-to-authored-ones](../queue-table-renders-draft-cards-identically-to-authored-ones/),
which edited `card_is_draft`'s docstring and the board's draft mark.
Reading `card_is_draft` next to `is_placeholder_scaffold` showed that
two docstrings in the same file contradict each other. `git log -S` puts
both in commit `e861360e`, and that commit's message settles which one
is the design. Filed at `human_gate: none` because the flag-only rule is
already decided, so the fix is to correct the comments and nothing needs
choosing. It qualifies for fix-through in the session that found it: one
source file, with the code already loaded.
