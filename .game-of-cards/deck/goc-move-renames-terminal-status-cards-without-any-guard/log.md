## 2026-06-01T05:26:39Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The cluster of unguarded mutation verbs has three documented fix shapes (see the sibling cards' decision sections). For `_cmd_move` specifically:

- **(a) Verb-level error**: `_cmd_move` loads the card via `load_card_or_exit`, checks `t.status in TERMINAL_STATUSES`, and rejects with a clear message pointing to the supersede workflow. Matches the post-fix `_cmd_decide` shape — fail loudly. Cost: a `goc move` on a closed card during a legitimate batch retitle (e.g. a deck-wide slug normalization) becomes a per-card override.
- **(b) Verb-level warning + `--force`**: `_cmd_move` warns when the target is terminal but proceeds, with a `--force` flag to silence the warning. Cost: defaulting to `proceed` keeps the silent-mutation hazard; the warning lives only in the operator's terminal scrollback.
- **(c) Verb-level error with `--force` escape hatch**: `_cmd_move` rejects on terminal status by default and accepts `--force` to bypass. Combines (a)'s defense-in-depth with (b)'s ergonomic escape for the deck-wide-rename case. Matches the `goc done` shape (`--force` bypasses DoD-checkbox enforcement for free-form DoD cards).

Recommendation: **(c)** — reject by default with `--force` to bypass. The kanban record-axis defaults to immutability; deliberate retitles of closed cards (slug normalization sweeps, post-hoc clarifications) are rare enough that an explicit `--force` per call is the right ergonomic. Aligns with the `goc done --force` precedent for the orthogonal DoD-enforcement bypass.

Independent of (a/b/c), record the chosen shape's interaction with the quality-pass subprocess (DoD step 4): does the new guard surface back through the subprocess exit code, and does `_apply_verdict_interactive`'s `r.returncode == 0` check at engine.py:4733 already DTRT (printing the failure to stderr and skipping the title-applied bookkeeping) or does it need its own log line clarifying that the closed-card path is the intended rejection rather than a generic move failure?


## 2026-10-22T05:17:58Z: decision recorded

Decided via parent terminal-status-guard-missing-across-mutation-verbs: (c) — reject terminal targets by default with a --force escape hatch; the quality-pass move subprocess inherits the rejection via the exit code — The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards. Gate decision → none.
