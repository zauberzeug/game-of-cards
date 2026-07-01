## 2026-07-01T02:45:00Z — Second instance connected

Wired [`waiting-filter-surfaces-draft-scaffolds-as-active-impediments`](../waiting-filter-surfaces-draft-scaffolds-as-active-impediments/)
(done) into `advanced_by`. It is a second drift of this exact rule at
the same `--waiting` call site: the hand-inlined gate copied only the
terminal-status half of the board's `card_cell` gate and dropped the
`card_is_draft` half, so draft scaffolds with an overlay leaked into
`--waiting`. Fixed there by adding `and not card_is_draft(t)`.

This widens the meta-fix scope: the live "shows `⏳`" variant of the
centralized helper must exclude `card_is_draft` in addition to
terminal-status, or `--waiting` / `card_cell` will still hand-inline the
draft clause and can drift a third time. Updated the summary, the
"## Why it matters" section, and the MECHANICAL/TDD DoD items to record
the draft axis. No decision made — the card stays parked at
`human_gate: decision` pending the helper-shape choice.
