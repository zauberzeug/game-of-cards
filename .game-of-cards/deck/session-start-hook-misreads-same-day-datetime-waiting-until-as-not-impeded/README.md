---
title: session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded
summary: "SessionStart hook `_is_impeded` compares `waiting_until` at date-level coarseness (`date.fromisoformat(until[:10]) > date.today()`), but the engine's `waiting_impedes` compares at full timestamp precision since the datetime-shape extension. For a card with `waiting_on` set and `waiting_until: <today>THH:MM:SSZ` still in the future (same-day datetime), the engine reports impeded (card hidden from `goc --ready`) but the hook reports not-impeded — the agent is told to `resume or close before starting new work` on a card `pull-card` cannot pull. The OpenClaw TypeScript port duplicates the same date-level comparison. Sibling-sweep finding on top of just-closed `session-start-hook-impeded-check-ignores-elapsed-waiting-until` — that fix mirrored engine semantics for the elapsed case at date level; this card refutes the docstring claim that date-level coarseness suffices, since the engine honors datetime-shape values at full precision."
status: done
stage: null
contribution: high
created: "2026-05-29T09:50:13Z"
closed_at: "2026-05-29T09:58:40Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by:
  - session-start-hook-impeded-check-ignores-elapsed-waiting-until
tags: [bug, infra]
definition_of_done: |
  - [x] MECHANICAL: `_is_impeded` in `goc/templates/hooks/deck_session_start.py` compares `waiting_until` at full timestamp precision (matches `engine.waiting_impedes` / `_waiting_until_instant` semantics) — a same-day datetime `YYYY-MM-DDTHH:MM:SSZ` whose instant is still in the future is reported impeded; one in the past is not.
  - [x] TDD: a regression test in `tests/test_session_start_hook.py` exercises the cell `waiting_on: external, waiting_until: <today>THH:MM:SSZ` (HH:MM:SS strictly after the comparison instant) on a `status: active, human_gate: none` card and asserts the hook returns True (impeded). A second case at `<today>T00:00:00Z` (elapsed instant within today) asserts the hook returns False (resurfaces). The test pins `today=` via a freezable clock or by injecting both sides of the boundary so it doesn't rot at midnight.
  - [x] MECHANICAL: all four file copies updated in lockstep (source-of-truth + auto-synced mirrors): `goc/templates/hooks/deck_session_start.py`, `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, `codex-plugin/hooks/deck_session_start.py`. The byte-for-byte mirror tripwire in CI catches drift if any are missed.
  - [x] MECHANICAL: the OpenClaw TypeScript port in `openclaw-plugin/index.ts` (`isImpeded` / `parseIsoDate`) is updated to match — full timestamp precision, not UTC-midnight coarseness. The misleading comment `UTC midnight comparison — matches the Python hook's date-level coarseness` is removed; the new comment names the engine contract being mirrored.
  - [x] MECHANICAL: the docstring claim in `_is_impeded` that "a date-level comparison suffices" is corrected — it does NOT suffice for datetime-shape values, only for date-shape ones.
  - [x] PROCESS: `uv run goc validate` passes; `uv run python -m unittest discover -s tests` passes.
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook `_is_impeded` misreads a same-day datetime `waiting_until` as not impeded

## Location

`goc/templates/hooks/deck_session_start.py:85-116` — the post-c191410 `_is_impeded` helper. The contract it claims to mirror: `goc/engine.py:1752-1798` (`waiting_impedes`) and the underlying `goc/engine.py:724-751` (`_waiting_until_instant`).

The duplicated bug: `openclaw-plugin/index.ts:120` (`ISO_DATE_RE`), `openclaw-plugin/index.ts:137-147` (`parseIsoDate`), `openclaw-plugin/index.ts:149-159` (`isImpeded`).

## What's broken

The hook strips the time component before comparing:

```python
# goc/templates/hooks/deck_session_start.py:85-116
def _is_impeded(readme: Path) -> bool:
    """Card carries an active impediment overlay.

    Mirrors `goc.engine.waiting_impedes` across the four-cell
    `waiting_on` × `waiting_until` matrix at date-level coarseness:

    - `waiting_on` set, no `waiting_until` → impeded (open-ended wait).
    - `waiting_on` set, future `waiting_until` → impeded.
    - `waiting_on` set, elapsed `waiting_until` → NOT impeded
      (elapsed wait resurfaces the card; engine contract).
    - no `waiting_on`, future `waiting_until` → impeded (deferred wait).
    - no `waiting_on`, elapsed `waiting_until` → NOT impeded.

    The engine compares at full timestamp precision; this hook only
    needs an active-yes/no bucket so a date-level comparison suffices.
    """
    reason = _card_waiting_on(readme)
    until = _card_waiting_until(readme)
    until_parsed = False
    until_future = False
    if until and _ISO_DATE_RE.match(until):
        try:
            until_future = date.fromisoformat(until[:10]) > date.today()  # ← truncates HH:MM:SS
            until_parsed = True
        except ValueError:
            pass
    if reason in _IMPEDED_WAITING_ON:
        if until_parsed and not until_future:
            return False
        return True
    return until_future
```

The engine compares at full precision via `_waiting_until_instant`, which honors the datetime shape:

```python
# goc/engine.py:1767-1772
`waiting_until` is compared at full timestamp precision: a datetime
shape (`YYYY-MM-DDTHH:MM:SSZ`) clears at its named instant, not at
the start of its civil day. A bare date `YYYY-MM-DD` is midnight UTC,
so date-only deferrals clear exactly as before.

# goc/engine.py:1797-1798
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

The hook's docstring claim — "the engine compares at full timestamp precision; this hook only needs an active-yes/no bucket so a date-level comparison suffices" — is false for the same-day datetime case. When `waiting_until: 2026-05-29T23:59:59Z` is set at 09:00Z on 2026-05-29:

- Engine: `until_dt (23:59:59Z) > now (09:00Z)` → True → impeded → card hidden from `goc --ready`.
- Hook: `date(2026-05-29) > date.today() (2026-05-29)` → False → `until_future = False` → with `waiting_on` set, the elapsed-clause fires `return False` → not impeded.

The two now disagree on a cell the engine considers active.

## Empirical evidence

`uv run python deck/session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded/reproduce.py`:

```
Case A: waiting_on=external, waiting_until=<today>T23:59:59Z (FUTURE, same civil day)
  hook  _is_impeded     : False
  engine waiting_impedes: True
  DIVERGED               : True

Case B: waiting_on=external, waiting_until=<today>T00:00:00Z (ELAPSED, midnight already passed)
  hook  _is_impeded     : False
  engine waiting_impedes: False
  DIVERGED               : False

Case C: waiting_until=<today>T23:59:59Z only (deferred, FUTURE same civil day)
  hook  _is_impeded     : False
  engine waiting_impedes: True
  DIVERGED               : True
```

Cases A and C diverge — both have a same-day future datetime — and they are the new shapes the datetime-precision engine extension introduced. The OpenClaw TypeScript port has the same divergence: `parseIsoDate` in `openclaw-plugin/index.ts:137-147` parses only the leading date and compares against UTC midnight today, identical coarseness, with the comment "matches the Python hook's date-level coarseness" replicating the bug rather than the engine contract.

## Why it matters

Reachability is unambiguous and growing. Two paths produce same-day datetime `waiting_until` values:

1. **The engine emitter itself.** `goc wait <title> --until <iso>` accepts a datetime-shape `--until`; the validator at `goc/engine.py:1238-1241` accepts both `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SSZ`. Any operator (human or agent) who runs `goc wait foo --reason external --until 2026-05-29T17:00:00Z` from a same-day morning lands directly in Case A.
2. **One-shot authored cards.** Hand-edited or LLM-authored frontmatter routinely emits ISO datetimes — every `created:` / `closed_at:` field in the deck is already a datetime; copying that shape for `waiting_until:` is the obvious-looking choice.

When the agent's session starts in this state, the SessionStart hook prints the card under

```
[GoC] Active card(s) (resume or close before starting new work): <title>
```

even though `goc --ready` won't list it and `pull-card` cannot pull it. The agent then opens the card, tries to resume, and discovers the impediment overlay — the same "stand down on work you're authorized to do" / "resume work you can't pick up" inversion the just-closed predecessor card fixed for the elapsed-date case, repeated for the same-day-datetime case.

The defect is the same conceptual matrix (`waiting_on` × `waiting_until` × instant comparison) handled inconsistently across the two re-implementations of the same predicate. The just-closed sibling `session-start-hook-impeded-check-ignores-elapsed-waiting-until` taught us the docstring-then-implement-three-of-four-cells pattern; this card refutes the broader "date-level coarseness suffices" assumption that the c191410 fix carried forward. The structural fix would be to expose `waiting_impedes` (or `_waiting_until_instant`) as a public engine helper the hook imports — but the hook is intentionally dependency-free so it runs from any working tree shape, and the engine has YAML / dataclass dependencies. The minimal fix is to port the datetime-aware comparison into the hook directly, matching the engine's logic line-for-line.

## Fix

Replace the date-level comparison with a timestamp-level one. The hook already detects the leading 10 chars via `_ISO_DATE_RE`; extend it to optionally consume the `THH:MM:SSZ` suffix and compare at full UTC precision:

```python
# goc/templates/hooks/deck_session_start.py
from datetime import datetime, timezone

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_ISO_DATETIME_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _parse_waiting_until(value: str) -> datetime | None:
    """Parse `waiting_until` into a UTC instant.

    Bare date `YYYY-MM-DD` is midnight UTC; datetime
    `YYYY-MM-DDTHH:MM:SSZ` is honored at full precision. Mirrors
    `goc.engine._waiting_until_instant`.
    """
    if _ISO_DATETIME_UTC_RE.match(value):
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if _ISO_DATE_RE.match(value):
        try:
            d = date.fromisoformat(value[:10])
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _is_impeded(readme: Path) -> bool:
    reason = _card_waiting_on(readme)
    until = _card_waiting_until(readme)
    until_dt = _parse_waiting_until(until) if until else None
    until_future = until_dt is not None and until_dt > datetime.now(tz=timezone.utc)
    if reason in _IMPEDED_WAITING_ON:
        if until_dt is not None and not until_future:
            return False
        return True
    return until_future
```

Same shape applies to `openclaw-plugin/index.ts`: replace `parseIsoDate`'s UTC-midnight comparison with full-precision Date parsing of the `Z`-suffixed datetime, and update `isImpeded` to use it. The misleading comment ("matches the Python hook's date-level coarseness") is replaced with a citation to the engine contract being mirrored.

The four-mirror invariant from the predecessor card carries forward: `goc/templates/hooks/deck_session_start.py` is the source of truth; the pre-commit sync script regenerates `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, and `codex-plugin/hooks/deck_session_start.py` byte-for-byte. The OpenClaw port is hand-edited (and a CI test enforces parity via the porter's drift check).
