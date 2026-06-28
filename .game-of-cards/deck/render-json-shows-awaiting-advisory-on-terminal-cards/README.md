---
title: render-json-shows-awaiting-advisory-on-terminal-cards
summary: "The `--json` full-record renderer emitted the dependency 'you may start' advisory (`awaiting` / `dependency_awaiting`) on terminal cards, contradicting the table and board renderers which suppress it on cards that cannot start. Fixed at `goc/engine.py:2764`; the per-renderer liveness gate was later centralized in `engine.dependency_advisory`."
status: done
stage: null
contribution: medium
created: "2026-06-20T04:36:38Z"
closed_at: "2026-06-20T04:40:14Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — no terminal card in `goc --status all --json` carries a non-empty `awaiting` or `dependency_awaiting: true`
  - [x] TDD: a regression test asserts `render_json` gates `awaiting`/`dependency_awaiting` on `status not in TERMINAL_STATUSES`, while a live card with the same open prereq still reports it
  - [x] MECHANICAL: the JSON full record mirrors the table renderer's liveness gate (`engine.py` ~2764-2765); `ready` already correct via `card_is_ready`
worker: {who: "claude[bot]", where: main}
---

# render-json-shows-awaiting-advisory-on-terminal-cards

> Later: the per-renderer liveness gate this card patched is now
> centralized in `engine.dependency_advisory` — see
> [renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/)
> (the meta-fix consolidating board / table / json).

The `--json` full-record renderer emits the dependency "you may start"
advisory (`awaiting` + `dependency_awaiting`) on terminal cards (done /
disproved / superseded), contradicting both the table and board
renderers, which suppress it on cards that cannot start.

## Location

`goc/engine.py:2764-2765`, inside `render_json`'s non-slim record
builder:

```python
"dependency_awaiting": dependency_blocked(t, by_title),
"awaiting": dependency_blockers(t, by_title),
"ready": card_is_ready(t, by_title),
```

## What's broken

`dependency_blockers` (`engine.py:2055`) returns the non-terminal
`advanced_by` prereqs of a card **regardless of that card's own
status** — its docstring and `isinstance` guard concern the prereqs,
not the card. So the caller owns the liveness check. The **table**
renderer does that (`engine.py:2680-2684`):

```python
# Mirror the board renderer's liveness gate (see `card_cell`):
# the dependency advisory is a "you may start" hint, which is
# meaningless on a terminal card. Only live cards show it.
blockers = (
    dependency_blockers(t, by_title)
    if t.status not in TERMINAL_STATUSES
    else []
)
```

`render_json` omits this guard, so a closed card that still references a
non-terminal `advanced_by` prereq is reported as `"awaiting": [...]`,
`"dependency_awaiting": true`. The `"ready"` key is already correct
because `card_is_ready` returns `False` for any card whose
`status != "open"` (`engine.py:2102`); only the two advisory keys leak.

This is the JSON sibling of the table-only fix
[verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards](../verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards/)
(done), whose fix never extended to the machine-readable surface.

## Empirical evidence

Run against this repo's own deck:

```
$ uv run goc --status all --json | <filter terminal cards with non-empty awaiting>
terminal cards with stale awaiting advisory: 2
('provide-openclaw-plugin-for-skills-and-hooks', 'done', ['openclaw-subagent-spawn-doesnt-project-plugin-tools'], True)
('design-claim-protocol-with-branch-and-author-metadata', 'done', ['parallel-agents-double-close-cards-because-claim-protections-are-disabled'], True)
```

Both cards are `done` yet JSON tells a consumer they are still
"awaiting a prereq you may start." The same cards in `goc -v` (table)
print no `awaiting:` line.

## Why it matters

`--json` is the surface automation and agents consume — `next-card` /
`pull-card` tooling, dashboards, and any external integration read it
rather than parsing the human table. A consumer that trusts `awaiting`
/ `dependency_awaiting` to mean "live work with an open prereq" will
mis-classify closed cards as in-flight. The advisory contradicts the
table/board on the same deck, so the three surfaces disagree.

Reachability: every terminal card with a non-terminal `advanced_by`
edge produces this — two such cards exist in the shipping deck right
now (see evidence). The shape is produced by normal use: close a child
whose prereq is still open.

## Fix

Mirror the table renderer's liveness gate at the JSON site
(`engine.py:2764-2765`):

```python
"dependency_awaiting": (
    dependency_blocked(t, by_title)
    if t.status not in TERMINAL_STATUSES
    else False
),
"awaiting": (
    dependency_blockers(t, by_title)
    if t.status not in TERMINAL_STATUSES
    else []
),
"ready": card_is_ready(t, by_title),
```

`ready` is left unchanged (already correct). The slim record does not
carry these keys, so no change there.
