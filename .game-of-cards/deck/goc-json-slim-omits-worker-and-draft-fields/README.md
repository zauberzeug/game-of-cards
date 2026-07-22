---
title: goc-json-slim-omits-worker-and-draft-fields
summary: "`goc --json --slim` omits `worker` and `draft`, both of which the full `--json` record emits. A machine consumer composing the documented `--worker <X>` / `GOC_WORKER` runner-queue filter with slim output gets records that lack the very field the filter matched on, and draft scaffolds are indistinguishable from pullable cards. Same defect shape as the fixed [goc-status-json-slim-omits-waiting-until](../goc-status-json-slim-omits-waiting-until/)."
status: done
stage: null
contribution: medium
created: "2026-07-22T01:20:24Z"
closed_at: "2026-07-22T01:26:41Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — slim records for a claimed card and a draft scaffold carry `worker` and `draft` with the same values as the full record, and `SLIM_JSON_KEYS` lists both.
  - [x] TDD: a regression test in `tests/` asserts `render_json(..., slim=True)` emits `worker` and `draft` (claimed card round-trips its `{who, where}` mapping; unclaimed non-draft card emits `worker: null`, `draft: false`).
  - [x] MECHANICAL: `SLIM_JSON_KEYS` (`goc/engine.py:3071`) gains `draft` and `worker`; the slim record dict in `render_json` emits both. Plugin mirrors synced; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc --json --slim` omits `worker` and `draft` from slim records

## Location

`goc/engine.py:3071` (`SLIM_JSON_KEYS` tuple) and `goc/engine.py:3094-3108`
(the slim record dict in `render_json`).

## What's broken

The slim JSON record emits exactly the nine `SLIM_JSON_KEYS` fields:

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
    "waiting_until",
)
```

The full record (same function, a few lines below) additionally emits the
two overlays a queue consumer needs:

```python
"draft": card_is_draft(t),
"worker": t.worker,
```

`AGENTS.md` documents `worker` as the runner-queue routing field:

> Filter with `goc --worker <X>` or set `GOC_WORKER` env var for
> runner-specific queue views.

So the natural machine composition — `goc --worker alice --json --slim` —
returns records that omit the field the query filtered on: the consumer
cannot attribute the claim, confirm the branch context (`where`), or
distinguish its own claims from another runner's when it widens the filter.
Likewise `draft` is the engine's single "scaffolded but not yet authored —
do not pull" overlay (rendered `✎` on the board, excluded from `--ready`);
a slim consumer scanning `--status open --json --slim` sees draft scaffolds
as ordinary pullable cards.

The `--slim` help text is generated from `SLIM_JSON_KEYS`, so help and
behavior agree — this is a contract *gap* in the slim field set, the same
shape the closed card
[goc-status-json-slim-omits-waiting-until](../goc-status-json-slim-omits-waiting-until/)
established as a defect when the slim record carried `waiting_on` but not
`waiting_until`: slim trims verbose body-ish fields (summary, edges, DoD
counters) for token cost, not scheduling-relevant overlays.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-json-slim-omits-worker-and-draft-fields/reproduce.py`
printed this before the fix:

```
slim record keys: ['closed_at', 'contribution', 'human_gate', 'status', 'tags', 'title', 'value', 'waiting_on', 'waiting_until']
[FAIL] slim record omits `worker` (full record has {'who': 'alice', 'where': 'feature/x'})
[FAIL] slim record omits `draft` (full record has True)
```

and exits zero after it:

```
slim record keys: ['closed_at', 'contribution', 'draft', 'human_gate', 'status', 'tags', 'title', 'value', 'waiting_on', 'waiting_until', 'worker']
[OK] slim records expose worker and draft, matching the full record
```

## Why it matters

Slim JSON exists precisely for autonomous/scripted consumers (it was added
to trim token cost of autonomous cycles). Those are the consumers that use
the `--worker` routing filter and must respect the draft overlay's
"not yet real" contract — the two fields slim drops. The reachability path
is any claimed card (`goc status <t> active` auto-populates `worker`) or
any `goc new` scaffold (born `draft: true`) rendered through
`goc --json --slim`.

## Fix (applied)

`SLIM_JSON_KEYS` gained `draft` and `worker`, and the slim record dict in
`render_json` emits `"draft": card_is_draft(t)` and `"worker": t.worker`,
mirroring the full record. The `--slim` help text derives from the tuple,
so it picked up the new fields with no separate edit. Regression coverage
lives in `tests/test_json_overlay.py` (claimed-card round-trip, draft
scaffold, null/false defaults, and the `SLIM_JSON_KEYS` contract itself);
plugin mirrors were re-synced via `scripts/sync_plugin_assets.py`.
