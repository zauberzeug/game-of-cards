---
title: goc-json-omits-the-waiting-on-and-waiting-until-impediment-fields
summary: "`goc --json` (render_json) exposes the status, human_gate, dependency (`awaiting`/`dependency_awaiting`), and derived `ready` axes, but omits the raw impediment-overlay fields `waiting_on` and `waiting_until`. A machine consumer sees `ready: false` with no way to learn whether a card is gated, dependency-awaiting, or impeded — nor the overlay's reason or expected clear-date. The board human-surface already got its overlay marker; the JSON record was never updated to match."
status: open
stage: null
contribution: medium
created: "2026-05-27T11:49:13Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `render_json` emits both `waiting_on` and `waiting_until`.
  - [ ] TDD: a regression test in `tests/` asserts the JSON record for a card with an active overlay contains `waiting_on` and `waiting_until` with the stored values (and that a card without the overlay emits them as `null`).
  - [ ] MECHANICAL: `render_json` (`goc/engine.py`) adds the two keys; the value matches the card's stored frontmatter (use `t.waiting_on` / `t.waiting_until`). Plugin mirrors synced; `uv run goc validate` clean.
---

# goc --json omits the waiting_on and waiting_until impediment fields

## Location

`goc/engine.py:2158-2188` — the `render_json` record dict.

## What's missing

A card's readiness is governed by **three axes** (the model built out by
[add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/)
and the `blocked`-status decomposition):

1. `status` / `human_gate`
2. the dependency graph (`advances` edges)
3. the **stored impediment overlay** — `waiting_on` (reason: external /
   resource / deferred) plus optional `waiting_until` (expected clear
   date), evaluated as a read-time guard by `waiting_impedes`.

`render_json` represents axes 1 and 2 fully — it emits `status`,
`human_gate`, `awaiting`, `dependency_awaiting`, and the composite
`ready` — but **drops axis 3 entirely**. The record dict has no
`waiting_on` or `waiting_until` key:

```python
return json.dumps(
    [
        {
            "title": t.title,
            ...
            "human_gate": t.human_gate,
            ...
            "dependency_awaiting": dependency_blocked(t, by_title),
            "awaiting": dependency_blockers(t, by_title),
            "ready": card_is_ready(t, by_title),
            "worker": t.worker,
            "dod_open": t.dod_open,
            "dod_done": t.dod_done,
            "dod_freeform": t.dod_freeform,
        }
        for t in cards
    ],
    ...
)
```

So a consumer reading `goc --json` sees `ready: false` but has **no way
to learn why**: the gate is visible, the dependency wait is visible, but
whether the card carries an impediment overlay — and what its reason or
expected clear-date is — is invisible. The overlay is a first-class,
schema-declared field (`goc/schema.yaml:19-27`: `waiting_on` /
`waiting_until` are optional fields with `waiting_on_values: [external,
resource, deferred]`) and the `Card` dataclass exposes both as
properties (`engine.py:531-541`), so this is a pure render-time omission,
not a parse gap.

## Why it matters

The overlay's other surfaces were all wired up, but the JSON record was
left behind:

- The human table/board renders the `⏳` overlay marker
  ([board-omits-marker-for-cards-with-active-waiting-overlay](../board-omits-marker-for-cards-with-active-waiting-overlay/), done).
- The precedent for what belongs in the JSON record is explicit:
  [closed-card-relationship-edges-stay-first-class-in-the-deck-graph](../closed-card-relationship-edges-stay-first-class-in-the-deck-graph/)
  (done) added `supersedes` / `superseded_by` to `render_json` precisely
  so "a reader (human or `--json` consumer)" could navigate that axis
  without parsing prose. The same argument applies verbatim to the
  impediment overlay.

Any tool consuming `goc --json` to build a queue view — a runner-specific
filter, a dashboard, the SaaS host explored in
[explore-saas-deck-hosting-with-optional-tracker-sync](../explore-saas-deck-hosting-with-optional-tracker-sync/) —
cannot reconstruct *why* a card is impeded or *when* it is expected to
clear. It can only see the binary `ready` flag.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` (exits 1 while the defect is present):

```
card.waiting_on    = 'external'
card.waiting_until = '2099-01-01'
card_is_ready      = False

render_json keys:
  advanced_by
  advances
  awaiting
  closed_at
  contribution
  created
  dependency_awaiting
  dod_done
  dod_freeform
  dod_open
  human_gate
  ready
  stage
  status
  summary
  superseded_by
  supersedes
  tags
  title
  value
  value_path
  worker

'waiting_on' present in JSON?    False
'waiting_until' present in JSON? False
'human_gate' present in JSON?    True
'ready' present in JSON?         True
'awaiting' present in JSON?      True

FAIL: JSON exposes the gate + dependency + ready axes but DROPS the
impediment overlay (waiting_on / waiting_until). A consumer sees
ready=false with no way to read the overlay reason or clear-date.
```

## Fix (do not apply here)

In `render_json` (`goc/engine.py:2158-2188`), add two keys to the record
dict alongside `human_gate`, mirroring how `worker` and the relationship
edges are emitted:

```python
"waiting_on": t.waiting_on,
"waiting_until": t.waiting_until,
```

`t.waiting_on` already normalizes to `None` for absent/empty values, and
`t.waiting_until` returns the stored value or `None`, so cards without an
overlay emit explicit nulls — symmetric with `closed_at`. No consumer
contract beyond the added keys; this is an additive change. Add a
regression test pinning both keys (none exists today — `grep render_json
tests/` is empty), since the JSON record is otherwise an unguarded
contract.
