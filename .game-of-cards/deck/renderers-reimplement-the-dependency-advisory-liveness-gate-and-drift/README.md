---
title: renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift
status: active
stage: null
contribution: medium
created: "2026-06-20T04:42:57Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [ ] TDD: a single helper (e.g. `dependency_advisory(card, by_title) -> tuple[list[str], bool]`) returns `([], False)` for terminal-status cards and the live blockers otherwise; unit test covers both
  - [ ] MECHANICAL: all three renderers — board `card_cell`, `render_table`, `render_json` — call the helper instead of inlining the `status not in TERMINAL_STATUSES` guard
  - [ ] TDD: existing regressions (`test_verbose_table_awaiting_liveness`, `test_json_awaiting_liveness`, board tests) still pass against the centralized helper
  - [ ] PROCESS: the two instance cards are cross-referenced; no behavior change, pure consolidation
worker: {who: "claude[bot]", where: main}
---

# renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift

The "dependency advisory is meaningless on a terminal card" rule —
`dependency_blockers(card)` should be suppressed when
`card.status in TERMINAL_STATUSES` — is reimplemented independently in
each of goc's three card renderers. It has already drifted once into a
shipping bug.

## The duplicated rule

The advisory ("awaiting: X — you may start") is a *liveness-gated*
display of `dependency_blockers` / `dependency_blocked`. Those two
functions (`goc/engine.py:2055`, `:2074`) deliberately do NOT gate on
the card's own status — they answer "which prereqs are non-terminal,"
and leave the "should this card show it" decision to each caller. So
every caller must re-apply the same `status not in TERMINAL_STATUSES`
guard:

- **board** — `card_cell` gates it (correct from the start).
- **table** — `render_table` (`engine.py:2680-2684`) gates it, but only
  after the fix in
  [verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards](../verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards/)
  (done) — it was missing originally.
- **json** — `render_json` (`engine.py:2764`) gates it, but only after
  [render-json-shows-awaiting-advisory-on-terminal-cards](../render-json-shows-awaiting-advisory-on-terminal-cards/)
  (done) — it too was missing, and two `done` cards leaked the advisory
  in shipping JSON.

Three copies of the same guard, two of which were wrong at some point.
This is the same "N callers reimplement one engine rule and drift"
shape already catalogued for other seams (e.g.
[goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits](../goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/),
[standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/),
[dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting](../dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting/)).

## Why it matters

Each new surface that wants to show "awaiting" (a future export format,
a `goc why`-style trace, an MCP tool) must remember to re-apply the
liveness gate or it reintroduces the bug. The two instance fixes patched
the symptom per renderer; nothing prevents the next renderer from
drifting again. Centralizing the rule into one helper makes the gate
impossible to forget — the renderers consume a pre-gated result.

## Fix

Introduce one helper next to `dependency_blockers` /
`dependency_blocked`, e.g.:

```python
def dependency_advisory(card, by_title):
    """Liveness-gated dependency advisory: ([], False) for terminal
    cards, else (blockers, bool(blockers))."""
    if card.status in TERMINAL_STATUSES:
        return [], False
    blockers = dependency_blockers(card, by_title)
    return blockers, bool(blockers)
```

Then call it from `card_cell`, `render_table`, and `render_json`,
deleting the three inline ternaries. Pure consolidation — no behavior
change; the existing regression tests for table and json liveness plus
the board tests must all stay green.

This is the meta-fix; the two per-renderer instance cards are already
closed. Filed by the pattern-generalization check after the json
instance fix on 2026-06-20.
