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

## 2026-09-16T05:05:53Z — New instance wired: a caller outside Python

Commit 6e021a5d (closing
`standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay`)
added a seventh hand-inlined copy of this liveness gate, now wired as an
`advanced_by` instance. The README caller table and the new
"A caller no helper can reach" section carry the detail.

Why it is worth a journal entry rather than just a table row: every
caller listed before it is a Python call site inside `goc/engine.py`,
so Option A and Option B both retire it by construction. This one is a
shell pipeline in a skill body that runs with no installed package and
cannot import the engine at all, so no helper shape reaches it. The
SessionStart hook is a second non-importer of the same kind. The open
question the decision should now also answer is whether those surfaces
are in scope, and if so whether the rule for them is "call
`goc --waiting --json`" rather than "re-derive from the JSON payload".

No status or gate change — the helper shape is still the human's call.
