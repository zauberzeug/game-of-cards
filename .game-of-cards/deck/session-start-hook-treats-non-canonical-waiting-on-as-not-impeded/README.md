---
title: session-start-hook-treats-non-canonical-waiting-on-as-not-impeded
summary: "The session-start hook re-implementations of `waiting_impedes` (Python `goc/templates/hooks/deck_session_start.py:_is_impeded` and TS `openclaw-plugin/index.ts:isImpeded`) gate impediment on enum membership (`waiting_on in {external, resource, deferred}`) where the engine gates on `reason is not None`. A hand-edited card with a typo'd or invented reason (e.g. `waiting_on: externl`) plus no `waiting_until` is reported impeded by the engine but resumable by both hooks. Same drift class as the just-closed `session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded`; this is the sibling matrix cell."
status: done
stage: null
contribution: medium
created: "2026-05-29T23:49:14Z"
closed_at: "2026-05-29T23:56:19Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` constructs a card with `waiting_on: externl` (any non-canonical reason) and no `waiting_until`, then shows that `engine.waiting_impedes` returns True while `deck_session_start._is_impeded` returns False — fails before fix, passes after.
  - [x] TDD: same reproducer covers the `waiting_on: <non-canonical>` + unparseable `waiting_until` cell (engine True, Python hook False) so both drifted cells are pinned by the test.
  - [x] TDD: fix in `goc/templates/hooks/deck_session_start.py` `_is_impeded` mirrors the engine: when `reason is not None` (any non-None value, not just `_IMPEDED_WAITING_ON` members), treat as impeded unless `waiting_until` is elapsed.
  - [x] TDD: same fix ported into `openclaw-plugin/index.ts` `isImpeded` — `IMPEDED_WAITING_ON.has(waitingOn)` widens to `waitingOn !== ""` (any non-empty reason).
  - [x] TDD: no behavior change for canonical reasons (external / resource / deferred), bare-`until` paths, elapsed-`until` resurfacing, the `until_unparseable` backstop with no reason, or the all-empty cell.
  - [x] PROCESS: pre-commit `sync-plugin-assets` regenerates the Claude-Code / Codex plugin mirrors of `deck_session_start.py` from the template; CI parity stays green.
worker: {who: "claude[bot]", where: main}
---

# Session-start hook treats non-canonical `waiting_on` as not-impeded

## Location

- `goc/templates/hooks/deck_session_start.py:113-152` — `_is_impeded`.
- `openclaw-plugin/index.ts:162-184` — `isImpeded`.
- Engine reference (the contract these helpers MUST mirror): `goc/engine.py:1751-1797` — `waiting_impedes`.

## What's broken

The engine and the two hook re-implementations disagree on two
adjacent matrix cells: a non-canonical `waiting_on` reason (any string
outside the canonical enum `{external, resource, deferred}`) paired
with either no `waiting_until` or an unparseable `waiting_until`.

### Engine (the contract)

`goc/engine.py:1773-1797`:

```python
now = _now_instant(today)
reason = card.waiting_on
until = card.waiting_until
until_dt: datetime | None = None
until_unparseable = False
if until is not None:
    until_dt = _waiting_until_instant(until)
    if until_dt is None:
        # ...err on the side of impeding...
        until_unparseable = True
if reason is None and until_dt is None:
    return until_unparseable
if until_dt is None:
    # Reason set, no date — open-ended wait; hide from queue.
    return True
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

The engine gates on `reason is None` — any non-None reason (canonical
*or* not) with no parseable `waiting_until` falls through to line 1793
and returns True.

### Python hook (drifted)

`goc/templates/hooks/deck_session_start.py:136-152`:

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
if reason in _IMPEDED_WAITING_ON:          # <-- enum-only check
    if until_dt is not None and not until_future:
        return False
    return True
if reason is None and until_dt is None:
    return until_unparseable
return until_future                         # <-- falls through for non-canonical reasons
```

The docstring at `deck_session_start.py:116` explicitly claims to
"Mirror `goc.engine.waiting_impedes` across the four-cell
`waiting_on` × `waiting_until` matrix". That claim is false for the
two cells where `reason` is set but not a member of `_IMPEDED_WAITING_ON`:

| `waiting_on` | `waiting_until` | engine | Python hook | TS hook |
| --- | --- | --- | --- | --- |
| `externl` (typo) | (absent) | **True** | **False** | **False** |
| `externl` (typo) | `not-a-date` | **True** | **False** | **False** |

The closed sibling card
[session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded](../session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded/)
patched the `(reason=None, until=unparseable)` cell. The two cells
above are the next sibling-cells in the same matrix, and they share
the same root cause: the hook is too narrow about which `reason`
values count.

## Empirical evidence

`uv run python .game-of-cards/deck/<this-card>/reproduce.py`:

```
waiting_impedes drift across engine and session-start hook
----------------------------------------------------------------

Case: non-canonical reason, no waiting_until
  engine.waiting_impedes        = True
  deck_session_start._is_impeded = False
  DRIFT                          = True

Case: non-canonical reason, unparseable waiting_until
  engine.waiting_impedes        = True
  deck_session_start._is_impeded = False
  DRIFT                          = True

FAIL: hook and engine disagree on at least one cell — the hook
reports such cards as resumable while the engine treats them as
impeded. Pre-validate / hand-edited decks would hit this gap (see
card README).
```

(The TS twin in `openclaw-plugin/index.ts` shares the structure
identically; a Node unit test added during fix should pin the same
two cells.)

### TS hook (drifted identically)

`openclaw-plugin/index.ts:171-184`:

```ts
let untilDt: Date | null = null;
let untilUnparseable = false;
if (waitingUntil !== "") {
  untilDt = parseWaitingUntil(waitingUntil);
  if (untilDt === null) untilUnparseable = true;
}
const untilFuture = untilDt !== null && untilDt.getTime() > now.getTime();
if (IMPEDED_WAITING_ON.has(waitingOn)) {        // <-- enum-only check
  if (untilDt !== null && !untilFuture) return false;
  return true;
}
if (waitingOn === "" && untilDt === null) return untilUnparseable;
return untilFuture;                              // <-- falls through for non-canonical reasons
```

Same shape, same drift: `IMPEDED_WAITING_ON.has(waitingOn)` only
matches the canonical enum; anything else flows past the
`untilUnparseable` backstop and returns `untilFuture` (false when no
`untilDt`).

## Why it matters

The engine loader validates `waiting_on ∈ {external, resource,
deferred}` at `engine.py:1232-1235`, so a fully-validated deck never
exposes the drift. The hooks, however, read `README.md` directly with
their own mini-frontmatter parsers — they bypass the loader entirely
and run **before** the user has had a chance to run `goc validate`.

The reachability path matches the just-closed
[session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded](../session-start-hook-treats-malformed-bare-waiting-until-as-not-impeded/)
card:

> `goc validate` is the upstream net (rejects calendar-impossible
> shapes); this is the read-time backstop for pre-validate /
> hand-edited decks.

Concrete scenarios that hit the drift:

1. A human hand-edits a card to `waiting_on: customer-call` (an
   invented reason) and saves before running validate. The next
   session-start announces the card as resumable — the agent picks it
   up — while the *next* `goc validate` would refuse the card.
2. A typo: `waiting_on: externl`. Same shape: announced as resumable
   until validate is run.
3. A migration script writes a deprecated reason value. Same shape.

The engine's design choice is "any non-None reason → impeded" so the
read-time backstop catches pre-validate / hand-edited decks. The hook
is supposed to be that backstop and currently isn't.

## Fix

Replace the `reason in _IMPEDED_WAITING_ON` gate with the engine's
"any non-None reason" gate.

**Python (`deck_session_start.py`):**

```python
# before
if reason in _IMPEDED_WAITING_ON:
    if until_dt is not None and not until_future:
        return False
    return True
if reason is None and until_dt is None:
    return until_unparseable
return until_future

# after
if reason is not None:
    if until_dt is not None and not until_future:
        return False
    return True
if until_dt is None:
    return until_unparseable
return until_future
```

The `_IMPEDED_WAITING_ON` constant can stay (no other consumer right
now, but it's a useful piece of cross-host documentation) or be
removed; either is fine. Update the docstring to match.

**TypeScript (`openclaw-plugin/index.ts`):**

```ts
// before
if (IMPEDED_WAITING_ON.has(waitingOn)) {
  if (untilDt !== null && !untilFuture) return false;
  return true;
}
if (waitingOn === "" && untilDt === null) return untilUnparseable;
return untilFuture;

// after
if (waitingOn !== "") {
  if (untilDt !== null && !untilFuture) return false;
  return true;
}
if (untilDt === null) return untilUnparseable;
return untilFuture;
```

After the fix, the docstring claim "Mirrors `goc.engine.waiting_impedes`
across the four-cell `waiting_on` × `waiting_until` matrix" becomes
true for **all six cells** (the two non-canonical-reason cells join
the four documented ones).
