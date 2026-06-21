---
title: session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded
summary: "The session-start hook re-implementations of `waiting_impedes` (Python `goc/templates/hooks/deck_session_start.py:_is_impeded` and TS `openclaw-plugin/index.ts:isImpeded`) drifted from the engine's malformed-`waiting_until` safety backstop. For a bare deferral (no `waiting_on`) with an unparseable `waiting_until`, the engine reports impeded=True (err on the side of hiding) while both hook helpers report False, so the session-start announcement frames such cards as resumable while the queue has already deferred them. Same root-cause as `waiting-impedes-treats-malformed-waiting-until-as-no-impediment` (done), which only patched the engine."
status: done
stage: null
contribution: medium
created: "2026-05-29T23:09:40Z"
closed_at: "2026-05-29T23:23:29Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` constructs a card with no `waiting_on` and `waiting_until: "not-a-date"`, then shows that `engine.waiting_impedes` returns True while `deck_session_start._is_impeded` (and the TS `isImpeded` predicate translated to a unit test) returns False — fails before fix, passes after.
  - [x] TDD: fix in `goc/templates/hooks/deck_session_start.py` `_is_impeded` mirrors the engine's `until_unparseable` backstop: when `until` is present-but-unparseable and `reason is None`, return True (treat as impeded) instead of falling through to `until_future` (which is False).
  - [x] TDD: same fix ported into `openclaw-plugin/index.ts` `isImpeded` so the TS twin matches the engine. Add a Node unit test covering the bare-deferral malformed-date case.
  - [x] TDD: no behavior change for valid future/elapsed dates, the bare-reason path, the reason-plus-future path, the reason-plus-elapsed path, or the reason-plus-malformed-date path (which already returns True correctly in both hooks via the `IMPEDED_WAITING_ON` branch).
  - [x] PROCESS: pre-commit `sync-plugin-assets` regenerates the Claude-Code / Codex plugin mirrors of `deck_session_start.py` from the template; CI parity stays green.
worker: {who: "claude[bot]", where: main}
---

# Session-start hook treats malformed bare `waiting_until` as not-impeded

## Location

- `goc/templates/hooks/deck_session_start.py:113-142` — `_is_impeded`.
- `openclaw-plugin/index.ts:162-174` — `isImpeded`.
- Engine reference (the contract these helpers MUST mirror): `goc/engine.py:1773-1797` — `waiting_impedes`.

## What's broken

The engine and the two hook re-implementations disagree on a single
matrix cell: bare deferral (`waiting_on: null`) plus an unparseable
`waiting_until`.

### Engine (post-fix, the contract)

`goc/engine.py:1778-1797`:

```python
if until is not None:
    until_dt = _waiting_until_instant(until)
    if until_dt is None:
        # Malformed date: a present-but-unparseable waiting_until signals
        # deferral intent we cannot evaluate. Err on the side of impeding
        # so the card is not silently un-deferred — for a bare deferral
        # (no reason) as well as alongside a waiting_on. `goc validate`
        # is the upstream net (rejects calendar-impossible shapes); this
        # is the read-time backstop for pre-validate / hand-edited decks.
        until_unparseable = True
if reason is None and until_dt is None:
    return until_unparseable
```

### Python hook (drifted)

`goc/templates/hooks/deck_session_start.py:133-142`:

```python
reason = _card_waiting_on(readme)
until = _card_waiting_until(readme)
until_dt = _parse_waiting_until(until) if until else None
until_future = until_dt is not None and until_dt > datetime.now(tz=timezone.utc)
if reason in _IMPEDED_WAITING_ON:
    if until_dt is not None and not until_future:
        return False
    return True
return until_future          # <-- drops the unparseable signal.
```

The docstring at line 116 explicitly claims to "Mirror
`goc.engine.waiting_impedes`":

> Mirrors `goc.engine.waiting_impedes` across the four-cell
> `waiting_on` × `waiting_until` matrix at full UTC timestamp
> precision

That claim is currently false for the (no-reason, unparseable-date)
cell.

### TS hook (same drift)

`openclaw-plugin/index.ts:162-174`:

```ts
function isImpeded(waitingOn: string, waitingUntil: string, now: Date): boolean {
  // Mirrors goc.engine.waiting_impedes across the four-cell waiting_on ×
  // waiting_until matrix at full UTC timestamp precision (matching
  // engine._waiting_until_instant). An elapsed waiting_until resurfaces
  // the card even when waiting_on is also set (engine contract).
  const untilDt = waitingUntil !== "" ? parseWaitingUntil(waitingUntil) : null;
  const untilFuture = untilDt !== null && untilDt.getTime() > now.getTime();
  if (IMPEDED_WAITING_ON.has(waitingOn)) {
    if (untilDt !== null && !untilFuture) return false;
    return true;
  }
  return untilFuture;
}
```

Identical shape, identical comment promising engine-parity, identical
drift.

## Empirical evidence

`uv run python .game-of-cards/deck/<this-card>/reproduce.py`:

```
engine.waiting_impedes  -> True
hook._is_impeded        -> False

DEFECT FIRES: engine hides the card from queues, hook announces it as resumable.
```

The card under test carries `waiting_on: null` and
`waiting_until: "2026-99-99"` (calendar-impossible, mimics a hand
edit). The engine fires its `until_unparseable` backstop; both hooks
fall through to `return until_future` (False).

## Why it matters

`waiting_impedes` is the read-time guard the engine uses to hide cards
from `pull-card` / `next-card` queues. The session-start hooks announce
*active* cards as resumable, with an impediment overlay subtracted off
the resumable set. When a hand-edited or mid-write card lands with a
malformed `waiting_until` and no reason:

- the engine hides the card from the autonomous queue (deferral intent
  honored — `waiting_impedes → True`);
- the session-start hook shows the card as a plain active card the
  agent should resume (impediment subtraction missed — `_is_impeded →
  False`).

The agent then attempts to resume a card the engine has already
deferred. The validator (`engine.py:1238` rejects non-ISO
`waiting_until`) is the upstream net, but the engine fix card
(`waiting-impedes-treats-malformed-waiting-until-as-no-impediment`,
done 2026-05-26) was filed precisely because `waiting_impedes` runs on
pre-validate / hand-edited decks. The session-start hook runs in the
same pre-validate regime — both invocations precede any explicit
`goc validate` — so the same backstop applies.

The reachability path:

1. Author hand-edits a card to `waiting_until: 2026-99-99` (no
   `waiting_on`) to mean "deferred indefinitely, will pick a real date
   later".
2. Session boots. Python hook reads the card via
   `deck_session_start.py`, computes `_is_impeded → False`, frames the
   card under "Active card(s): ... — resume or close before starting
   new work."
3. Agent resumes the card. The engine, on the next `goc` query, hides
   it from queues. Now the announcement and the queue disagree on the
   card's state.

## Meta-fix angle

Three places implement the same predicate (engine Python, hook Python,
plugin TS). Two of them already drifted from the engine fix shipped
2026-05-26. The pattern matches `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
and similar meta-fix families: per-consumer guard fixes will keep
spawning until the predicate has one source of truth (or each consumer
is covered by a parity test that fails on drift). This card patches
the two known drifts; a follow-up may extract the predicate or add a
mirror-parity test, but is out of scope here.

## Fix

Mirror the engine's `until_unparseable` flag in both hooks.

Python hook (`goc/templates/hooks/deck_session_start.py:133-142`):

```python
reason = _card_waiting_on(readme)
until = _card_waiting_until(readme)
until_unparseable = False
until_dt: datetime | None = None
if until:
    until_dt = _parse_waiting_until(until)
    if until_dt is None:
        until_unparseable = True
until_future = until_dt is not None and until_dt > datetime.now(tz=timezone.utc)
if reason in _IMPEDED_WAITING_ON:
    if until_dt is not None and not until_future:
        return False
    return True
if reason is None and until_dt is None:
    return until_unparseable
return until_future
```

TS hook (`openclaw-plugin/index.ts:162-174`): same shape, returning
`untilUnparseable` on the bare-deferral branch.

Add the porter / sync-plugin-assets check so the regenerated mirrors
under `claude-plugin/hooks/`, `codex-plugin/hooks/`, and
`.claude/hooks/` all pick up the patched template; CI's parity tests
fail on any drift.
