---
title: goc-status-json-slim-omits-waiting-until
summary: "`goc --json --slim` emits `waiting_on` but never `waiting_until`, so a machine consumer of slim records sees a card is impeded without learning whether the wait is bare/elapsed (surfaced as an SLE escalation) or future-dated (hides the card from queues). The full `--json` record was fixed by [goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields](../goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields/); the slim variant — added shortly after to trim token cost of autonomous cycles — copied only half of the overlay."
status: active
stage: null
contribution: medium
created: "2026-05-29T21:02:02Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — slim record for a card with `waiting_until` set includes the field with the stored value.
  - [ ] TDD: a regression test in `tests/` asserts that `render_json(..., slim=True)` emits both `waiting_on` and `waiting_until` (and that a card without the overlay emits them as `null`).
  - [ ] MECHANICAL: `SLIM_JSON_KEYS` (`goc/engine.py:2286`) gains `waiting_until`; the slim record dict (`goc/engine.py:2309`) emits `"waiting_until": t.waiting_until`. Plugin mirrors synced; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc --json --slim` omits `waiting_until` from the impediment overlay

## Location

`goc/engine.py:2286-2295` (`SLIM_JSON_KEYS` tuple) and `goc/engine.py:2308-2321` (the slim record dict in `render_json`).

## What's broken

The impediment overlay is a **pair** of fields per the three-axis stuck model documented in `AGENTS.md` and `goc/templates/skills/advance-card/SKILL.md`:

> The **impediment overlay** (`waiting_on` + `waiting_until`) is the stored part of the three-axis stuck model.

The semantics of one field depend on the other:

- A future `waiting_until` (or a reason with no date) hides the card from `--ready` queues.
- An elapsed `waiting_until` is surfaced by `goc validate` as an SLE escalation.

The full `--json` record exposes both halves at `goc/engine.py:2333-2334`:

```python
"human_gate": t.human_gate,
"waiting_on": t.waiting_on,
"waiting_until": t.waiting_until,
```

But the slim path emits only one:

```python
SLIM_JSON_KEYS = (
    "title",
    "status",
    "human_gate",
    "contribution",
    "value",
    "tags",
    "closed_at",
    "waiting_on",
)
...
if slim:
    records = [
        {
            "title": t.title,
            "status": t.status,
            "human_gate": t.human_gate,
            "contribution": t.contribution,
            "value": values.get(t.title, (0.0, []))[0],
            "tags": t.tags,
            "closed_at": str(t.closed_at) if t.closed_at else None,
            "waiting_on": t.waiting_on,
        }
        for t in cards
    ]
```

`SLIM_JSON_KEYS` is also stringified into the `--slim` help text at `goc/engine.py:2547` (`help=f"With --json: emit only {', '.join(SLIM_JSON_KEYS)}."`), so the documented contract and the implementation agree with each other and both omit `waiting_until` — i.e. this is a real gap, not a render bug.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/goc-status-json-slim-omits-waiting-until/reproduce.py
slim record for openclaw-subagent-plugin-tools-alsoallow-ignored:
  keys:           ['closed_at', 'contribution', 'human_gate', 'status', 'tags', 'title', 'value', 'waiting_on']
  waiting_on:     'external'
  waiting_until:  <MISSING>
full record (same card):
  waiting_on:     'external'
  waiting_until:  None
FAIL: slim record drops waiting_until; full record keeps it
```

## Why it matters

The slim path was added in commit `0c1421a` (`feat(engine,skills): trim token cost of autonomous card cycles`) to give skills a smaller cards-JSON dump than the full record. The skills that drive `pull-card` and `next-card` need the impediment overlay to reason about queue-eligibility — exactly the same reason the full `--json` was patched in `goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields`. The slim variant copied `waiting_on` but stopped one field short, so any skill or external tool that switches to `--slim` for cost reasons silently loses the timing half of the overlay and cannot tell `external` (open-ended) from `deferred until 2026-09-01` (a future-dated wait that auto-hides from queues) from `deferred until 2024-01-01` (elapsed; SLE-escalation signal).

Reachability: trigger by running `goc --json --slim` (or `goc --status all --json --slim`) on any deck where at least one card carries a `waiting_until` value. The omission is at the emitter, so every consumer of slim JSON observes it.

## Fix

1. Add `"waiting_until"` to the `SLIM_JSON_KEYS` tuple at `goc/engine.py:2286-2295` (immediately after `"waiting_on"`, mirroring the order in the full record).
2. Add `"waiting_until": t.waiting_until,` to the slim record dict at `goc/engine.py:2309-2321` (immediately after the `waiting_on` line).
3. Regression test: extend whatever test in `tests/` covers `render_json` slim mode (or add one) — assert both keys present on a card with the overlay set and both `None` on a card without.
4. Re-sync plugin mirrors via the pre-commit hook (`sync_plugin_assets.py`).
