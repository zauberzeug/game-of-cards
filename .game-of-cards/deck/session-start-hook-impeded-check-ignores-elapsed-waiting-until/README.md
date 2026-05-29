---
title: session-start-hook-impeded-check-ignores-elapsed-waiting-until
summary: "SessionStart hook `_is_impeded` returns True whenever `waiting_on` is in {external, resource, deferred}, without consulting `waiting_until`. The engine's `waiting_impedes` returns False for the same card if `waiting_until` is in the past — the documented contract is that an elapsed `waiting_until` re-surfaces the card. A `status: active, human_gate: none, waiting_on: external, waiting_until: <past>` card is therefore framed under `Impeded active card(s) — agent cannot resume` even though `pull-card` / `goc --ready` consider it workable. Sibling-sweep finding on top of just-closed `session-start-hook-frames-waiting-on-active-cards-as-resumable`."
status: done
stage: null
contribution: medium
created: "2026-05-29T09:34:55Z"
closed_at: "2026-05-29T09:41:13Z"
human_gate: none
advances:
  - session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] MECHANICAL: `_is_impeded` in `goc/templates/hooks/deck_session_start.py` mirrors `engine.waiting_impedes` semantics for the four-cell `waiting_on` × `waiting_until` matrix. Specifically, a `waiting_on` reason alongside an elapsed (past) `waiting_until` is NOT impeded — it resurfaces.
  - [x] TDD: a regression test in `tests/test_session_start_hook.py` exercises the cell `waiting_on: external, waiting_until: <past>` on a `status: active, human_gate: none` card and asserts the hook does NOT print the `Impeded active card(s)` line for it. (The existing matrix test only covers `waiting_until` alone and future `waiting_until` + `waiting_on`.)
  - [x] MECHANICAL: all four file copies updated in lockstep (source-of-truth + auto-synced mirrors): `goc/templates/hooks/deck_session_start.py`, `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, `codex-plugin/hooks/deck_session_start.py`. The byte-for-byte mirror tripwire in CI catches drift if any are missed.
  - [x] MECHANICAL: the OpenClaw TypeScript port in `openclaw-plugin/index.ts` is updated to match — same elapsed-`waiting_until` semantics. (Hand-ported, not auto-synced; verify by re-reading `index.ts` after the change.)
  - [x] PROCESS: `uv run goc validate` passes; `uv run python -m unittest discover -s tests` passes.
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook `_is_impeded` ignores elapsed `waiting_until` when `waiting_on` is set

## Location

`goc/templates/hooks/deck_session_start.py:85-103` — the `_is_impeded` helper introduced by commit `10e7843` ("fix(hook): session-start partitions active cards by waiting_on impediment").

The contract being mirrored: `goc/engine.py:1752-1798` (`waiting_impedes`).

## What's broken

`_is_impeded` short-circuits on `waiting_on` set without ever looking at `waiting_until`:

```python
# goc/templates/hooks/deck_session_start.py:85-103
def _is_impeded(readme: Path) -> bool:
    """Card carries an active impediment overlay.

    True iff `waiting_on` ∈ {external, resource, deferred}, OR
    `waiting_until` parses as a date strictly after today (UTC). Mirrors
    the read-time wait predicate in `goc.engine.waiting_impedes` at the
    coarseness this line-based parser can afford — the engine compares at
    full timestamp precision, but the hook only needs an active-yes/no
    bucket so a date-level comparison is sufficient.
    """
    if _card_waiting_on(readme) in _IMPEDED_WAITING_ON:
        return True                              # ← returns before checking waiting_until
    until = _card_waiting_until(readme)
    if until and _ISO_DATE_RE.match(until):
        try:
            return date.fromisoformat(until[:10]) > date.today()
        except ValueError:
            return False
    return False
```

That contradicts the engine's documented contract (`goc/engine.py:1763-1765`):

> When `waiting_until` is in the past (elapsed), the card RE-ENTERS the
> queue with no manual action — the elapsed-wait is then surfaced
> separately by `validate_waiting_overlay` as an SLE escalation signal.

The engine implementation honors that:

```python
# goc/engine.py:1792-1798
if reason is None and until_dt is None:
    return until_unparseable
if until_dt is None:
    # Reason set, no date — open-ended wait; hide from queue.
    return True
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

When `reason` is set AND `until_dt` is in the past, the engine returns `False`. The hook returns `True`. The hook's docstring even claims to "mirror" the engine — but the implementation only mirrors three of the four matrix cells.

## Empirical evidence

`uv run python deck/session-start-hook-impeded-check-ignores-elapsed-waiting-until/reproduce.py`:

```
Case A: waiting_on=external, waiting_until=2000-01-01 (ELAPSED)
  hook  _is_impeded     : True
  engine waiting_impedes: False
  DIVERGED               : True

Case B: waiting_on=external, waiting_until=2099-01-01 (FUTURE) [agree=True]
  hook  _is_impeded     : True
  engine waiting_impedes: True
  DIVERGED               : False

Case C: waiting_on=external only [agree=True]
  hook  _is_impeded     : True
  engine waiting_impedes: True
  DIVERGED               : False

Case D: waiting_until=2000-01-01 only (ELAPSED) [agree=False (both not impeded)]
  hook  _is_impeded     : False
  engine waiting_impedes: False
  DIVERGED               : False
```

Three of four cells agree; Case A diverges.

## Why it matters

Reachability is unambiguous: any active card whose `waiting_on` reason was set alongside a `waiting_until` date that has since elapsed lands in Case A. This happens organically — an operator runs `goc wait <card> --reason external --until 2026-05-15` and the date passes without manual clearing. At the next session-start the agent sees:

```
[GoC] Impeded active card(s) (waiting_on): <card> — agent cannot resume.
```

But the engine considers the card ready: `goc --ready` lists it, `pull-card` would happily claim it, `waiting_impedes` returns False. The hook tells the agent to stand down on work the agent is actually authorized to do.

This is also the same root cause shape (`waiting_on` × `waiting_until` matrix incompletely handled) flagged by the open unverified card `goc-wait-does-not-clear-stale-elapsed-waiting-until`, but in a different module. That card is about `goc wait` not refreshing the date; this card is about the session-start hook misclassifying the resulting state. Both want the same conceptual matrix to be respected in two different sites.

## Fix

Make `_is_impeded` consult both fields together. One-shape implementation matching the engine:

```python
def _is_impeded(readme: Path) -> bool:
    reason = _card_waiting_on(readme)
    until = _card_waiting_until(readme)
    until_future = False
    if until and _ISO_DATE_RE.match(until):
        try:
            until_future = date.fromisoformat(until[:10]) > date.today()
        except ValueError:
            until_future = False  # malformed; engine treats as impeded, but goc validate catches it
    if reason in _IMPEDED_WAITING_ON:
        # Elapsed waiting_until resurfaces even with a reason set.
        if until and _ISO_DATE_RE.match(until) and not until_future:
            return False
        return True
    return until_future
```

The four file copies (source-of-truth + three mirrors) plus the OpenClaw TS port all need updating; the regression test must add the missing Case A row to keep the matrix honest.
